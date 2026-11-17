"""Follow a vendor (chantier 1 of the roadmap, design SuivreVendeur) and their news (A.8 of the
plan of « My products »).

A follower gives their WhatsApp number once (or is known on this browser) and gets a WhatsApp
message at each live of the vendor (2 at most a day per vendor, setting), and, if they want, the
news of the vendor on Friday (setting): the products put on sale since the last news, once a
month for every vendor, each week with OCD Business; nothing new, nothing sent. « Follow »
replaces « Tell me on WhatsApp » of the next live only: the alerts waiting are follows now (lives
only: they never asked for the news). The vendor sees how many follow them, never their numbers.
Following is the consent to these messages; STOP on WhatsApp stops them like the others."""
import secrets
from datetime import timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import consteq

from odoo.addons.ocd_live import tools

# The vendors whose news leave in one run of the scheduled task: the others the next hour
NEWS_BATCH = 200
# The products named in the message of the news
NEWS_NAMED = 2
# A product put on sale in the last days is « New » on the boutique
NEW_DAYS = 7
# The news are sent from this local hour on the day chosen
NEWS_HOUR = 10


class OcdVendorFollower(models.Model):
    _name = "ocd.vendor.follower"
    _description = "Follower Of A Vendor"
    _order = "id desc"
    _check_company_auto = True

    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Contact", required=True, index=True, ondelete="cascade"
    )
    vendor_id = fields.Many2one(
        comodel_name="res.partner", string="Vendor", required=True, index=True, ondelete="cascade",
        domain="[('ocd_is_vendor', '=', True)]",
    )
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    active = fields.Boolean(default=True, help="No longer followed: kept for the history of the vendor.")
    lives = fields.Boolean(string="At Each Live", default=True, help="A WhatsApp message when the vendor goes live.")
    news = fields.Boolean(
        string="Their News", default=True,
        help="A WhatsApp message on Friday with the products the vendor put on sale.",
    )
    source = fields.Selection(
        selection=[
            ("boutique", "Boutique"), ("feed", "Lives"), ("product", "Product"), ("replay", "Replay"),
            ("alert", "Tell me (before)"), ("team", "OCD Live team"),
        ],
        string="Followed From", default="boutique",
    )
    followed_at = fields.Datetime(string="Followed At", default=fields.Datetime.now, readonly=True)
    live_told_at = fields.Datetime(string="Last Live Told", readonly=True, copy=False)
    news_told_at = fields.Datetime(string="Last News Told", readonly=True, copy=False)
    access_token = fields.Char(copy=False, groups="base.group_system")

    _unique_follow = models.UniqueIndex("(partner_id, vendor_id)", "This contact already follows this vendor.")

    @api.depends("partner_id", "vendor_id")
    def _compute_display_name(self):
        for follower in self:
            follower.display_name = self.env._(
                "%(contact)s follows %(vendor)s", contact=follower.partner_id.name, vendor=follower.vendor_id.name
            )

    # === FOLLOW === #

    @api.model
    def _ocd_contact(self, phone):
        """The contact of the WhatsApp number `phone` (normalized), created when unknown."""
        Partner = self.env["res.partner"].sudo()
        partner = Partner._ocd_find_vendor_by_phone(phone) or Partner.search([("phone", "=", phone)], limit=1)
        return partner or Partner.create({"name": phone, "phone": phone})

    @api.model
    def _ocd_follow(self, vendor, partner, lives=True, news=True, source="boutique"):
        """`partner` follows `vendor` (again): return the follower. Following is the consent to
        these messages: the consent of the contact is noted, unless they answered STOP."""
        vendor, partner = vendor.sudo(), partner.sudo()
        if not vendor.ocd_is_vendor or vendor.ocd_vendor_state != "approved" or not vendor.active:
            raise UserError(self.env._("This vendor cannot be followed."))
        if partner == vendor:
            raise UserError(self.env._("This is your boutique: your customers follow it."))
        if not (lives or news):
            raise UserError(self.env._("Choose the lives, the news, or both."))
        follower = self.sudo().with_context(active_test=False).search(
            [("partner_id", "=", partner.id), ("vendor_id", "=", vendor.id)], limit=1
        )
        values = {"lives": bool(lives), "news": bool(news)}
        if follower:
            if not follower.active:
                values.update(active=True, followed_at=fields.Datetime.now(), source=source)
            follower.write(values)
        else:
            follower = self.sudo().create({
                **values, "partner_id": partner.id, "vendor_id": vendor.id, "source": source,
                "company_id": (vendor.company_id or self.env.company).id,
            })
        partner._ocd_agree_by_following()
        return follower

    def _ocd_set(self, lives, news):
        """What the follower receives; nothing left: no longer followed."""
        for follower in self.sudo():
            if lives or news:
                follower.write({"lives": bool(lives), "news": bool(news), "active": True})
            else:
                follower.active = False

    def _ocd_unfollow(self):
        self.sudo().write({"active": False})

    def _ocd_link_token(self):
        """The secret of the links of its messages: they open the boutique on its phone, known."""
        self.ensure_one()
        follower = self.sudo()
        if not follower.access_token:
            follower.access_token = secrets.token_urlsafe(18)
        return follower.access_token

    def _ocd_check_token(self, token):
        self.ensure_one()
        stored = self.sudo().access_token or ""
        return bool(stored and token and consteq(stored, str(token)))

    def _ocd_link_path(self, news=False):
        """The address of the button of its messages (without the first /)."""
        self.ensure_one()
        path = f"ocd/abonne/{self.id}/{self._ocd_link_token()}"
        return f"{path}?vers=nouveautes" if news else path

    # === AT EACH LIVE === #

    @api.model
    def _ocd_send_lives(self):
        """The lives that started: their followers are told once (2 lives at most a day per
        vendor, setting). A live already told is never told again; a follower who arrives
        during the live is not told of it (they are on the boutique)."""
        now = fields.Datetime.now()
        lives = self.env["ocd.live.booking"].sudo().search([
            ("state", "=", "confirmed"), ("start_datetime", "<=", now), ("end_datetime", ">", now),
            ("ocd_followers_told_at", "=", False),
        ], order="start_datetime")
        for live in lives:
            vendor = live.partner_id
            live.ocd_followers_told_at = now
            company = live.company_id or vendor.company_id or self.env.company
            if not self._ocd_lives_left_today(vendor, company, now, live):
                live.message_post(body=self.env._("The followers were not told: %s lives told today already.",
                                                  company.ocd_live_messages_per_day))
                continue
            followers = self.sudo().search([
                ("vendor_id", "=", vendor.id), ("lives", "=", True), ("followed_at", "<", live.start_datetime),
            ])
            if followers:
                followers._ocd_tell_live(live)
                followers.write({"live_told_at": now})

    @api.model
    def _ocd_lives_left_today(self, vendor, company, now, live):
        """Whether the followers of `vendor` may still be told of a live today (their day)."""
        per_day = company.ocd_live_messages_per_day
        if per_day <= 0:
            return False
        tz = pytz.timezone(vendor._ocd_tz_name())
        local = pytz.utc.localize(now).astimezone(tz)
        start = local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc).replace(tzinfo=None)
        told = self.env["ocd.live.booking"].sudo().search_count([
            ("partner_id", "=", vendor.id), ("id", "!=", live.id), ("ocd_followers_told_at", ">=", start),
            ("ocd_followers_skipped", "=", False),
        ])
        if told >= per_day:
            live.ocd_followers_skipped = True
            return False
        return True

    def _ocd_tell_live(self, live):
        """Tell the followers the vendor is live (ocd_live_shop_whatsapp)."""

    # === THE NEWS (A.8) === #

    @api.model
    def _ocd_send_news(self, now=None):
        """On the day of the news (Friday by default), from 10:00 at the hour of the vendor: the
        products put on sale since the last news, to the followers who want them. Once a month
        (the first such day of the month) for every vendor, each week with OCD Business."""
        now = now or fields.Datetime.now()
        vendors = self.sudo().search([("news", "=", True)]).vendor_id
        sent = 0
        for vendor in vendors.sorted("id"):
            if sent >= NEWS_BATCH:
                break
            if not vendor._ocd_news_due(now):
                continue
            products = vendor._ocd_news_products()
            if not products:
                continue
            followers = self.sudo().search([("vendor_id", "=", vendor.id), ("news", "=", True)])
            followers._ocd_tell_news(products)
            followers.write({"news_told_at": now})
            vendor.sudo().write({"ocd_news_sent_at": now, "ocd_news_product_ids": [fields.Command.set(products.ids)]})
            sent += 1

    def _ocd_tell_news(self, products):
        """Tell the followers the news of the vendor (ocd_live_shop_whatsapp)."""

    @api.model
    def _ocd_news_list(self, products, lang=None):
        """« Robe en wax, Sac en raphia and 3 more »: the first products named, in `lang` when it
        is installed (the language of a WhatsApp template)."""
        env = self.with_context(lang=lang).env if lang and self.env["res.lang"]._ocd_is_active(lang) else self.env
        names = products[:NEWS_NAMED].mapped("name")
        others = len(products) - len(names)
        text = ", ".join(names)
        if others == 1:
            return env._("%s and 1 more", text)
        if others > 1:
            return env._("%(names)s and %(count)s more", names=text, count=others)
        return text


class ResPartner(models.Model):
    _inherit = "res.partner"

    ocd_follower_ids = fields.One2many(
        comodel_name="ocd.vendor.follower", inverse_name="vendor_id", string="Followers",
    )
    ocd_follower_count = fields.Integer(string="Followers Count", compute="_compute_ocd_follower_count")
    ocd_news_sent_at = fields.Datetime(string="News Sent At", readonly=True, copy=False)
    ocd_news_product_ids = fields.Many2many(
        comodel_name="product.template", relation="res_partner_ocd_news_product_rel", column1="partner_id",
        column2="product_id", string="Products Of The Last News", readonly=True, copy=False,
    )

    def _ocd_agree_by_following(self):
        """Following is the consent to its messages (extended by ocd_live_shop_whatsapp: never
        after STOP on WhatsApp)."""
        for partner in self.sudo().filtered(lambda partner: not partner.ocd_whatsapp_optin):
            partner.ocd_whatsapp_optin = True

    def _compute_ocd_follower_count(self):
        counts = dict(self.env["ocd.vendor.follower"].sudo()._read_group(
            [("vendor_id", "in", self.ids)], ["vendor_id"], ["__count"]
        ))
        for partner in self:
            partner.ocd_follower_count = counts.get(partner._origin, 0)

    def _ocd_follower_stats(self):
        """(followers, new in the last 7 days) of the vendor."""
        self.ensure_one()
        Follower = self.env["ocd.vendor.follower"].sudo()
        since = fields.Datetime.now() - timedelta(days=7)
        return (
            Follower.search_count([("vendor_id", "=", self.id)]),
            Follower.search_count([("vendor_id", "=", self.id), ("followed_at", ">=", since)]),
        )

    def _ocd_followers_card(self):
        """« My followers » in the space of the vendor: how many, the new ones this week, the next
        news and what they will show."""
        self.ensure_one()
        env = self.env
        count, new = self._ocd_follower_stats()
        products = self._ocd_news_products()
        names = env["ocd.vendor.follower"]._ocd_news_list(products)
        return {
            "count": count,
            "new": env._("+%s this week", new) if new else "",
            "news_title": env._("Next news: %s", tools.day_text(env, self._ocd_next_news_day(), "EEEE d MMMM")),
            "news_line": (env._("1 product put on sale since the last news: %s", names) if len(products) == 1
                          else env._("%(count)s products put on sale since the last news: %(names)s",
                                     count=len(products), names=names)) if products
            else env._("Nothing new since the last news: put a product on sale, your followers get it."),
            "rhythm": env._("Each week, with OCD Business.") if self._ocd_news_weekly()
            else env._("Once a month. With OCD Business: each week."),
            "share_url": f"{self.get_base_url()}/ocd/boutique/{self.id}",
        }

    def action_ocd_view_followers(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Followers of %s", self.name),
            "res_model": "ocd.vendor.follower",
            "view_mode": "list",
            "domain": [("vendor_id", "=", self.id)],
            "context": {"default_vendor_id": self.id},
        }

    # --- The news --- #

    def _ocd_news_weekly(self):
        """Each week with OCD Business, once a month otherwise."""
        self.ensure_one()
        return self._ocd_business()

    def _ocd_news_day(self, local_day):
        """Whether `local_day` is a day the news of the vendor leave."""
        self.ensure_one()
        company = self.company_id or self.env.company
        if local_day.weekday() != int(company.ocd_news_weekday or 4):
            return False
        return self._ocd_news_weekly() or local_day.day <= 7

    def _ocd_news_due(self, now):
        """Whether the news of the vendor leave now: their day, from 10:00 at their hour, not sent
        today already."""
        self.ensure_one()
        tz = pytz.timezone(self._ocd_tz_name())
        local = pytz.utc.localize(now).astimezone(tz)
        if local.hour < NEWS_HOUR or not self._ocd_news_day(local.date()):
            return False
        if self.ocd_news_sent_at:
            last = pytz.utc.localize(self.ocd_news_sent_at).astimezone(tz).date()
            if last == local.date():
                return False
        return True

    def _ocd_news_since(self):
        """From when the products are new for the next news: the last news, else a week (or a
        month without OCD Business)."""
        self.ensure_one()
        if self.ocd_news_sent_at:
            return self.ocd_news_sent_at
        return fields.Datetime.now() - timedelta(days=7 if self._ocd_news_weekly() else 31)

    def _ocd_news_products(self, since=None):
        """The products of the vendor put on sale since `since`, still on sale, the newest first."""
        self.ensure_one()
        since = since or self._ocd_news_since()
        return self.env["product.template"].sudo().search([
            ("ocd_vendor_id", "=", self.id), ("is_published", "=", True), ("sale_ok", "=", True),
            ("ocd_review_state", "=", "approved"), ("ocd_vendor_retired", "=", False),
            "|", ("ocd_review_date", ">", since), "&", ("ocd_review_date", "=", False), ("create_date", ">", since),
        ], order="ocd_review_date desc, id desc")

    def _ocd_next_news_day(self):
        """The next day the news of the vendor leave (at their hour)."""
        self.ensure_one()
        tz = pytz.timezone(self._ocd_tz_name())
        local = pytz.utc.localize(fields.Datetime.now()).astimezone(tz)
        day = local.date()
        if self.ocd_news_sent_at and pytz.utc.localize(self.ocd_news_sent_at).astimezone(tz).date() == day:
            day += timedelta(days=1)
        for _offset in range(40):
            if self._ocd_news_day(day):
                return day
            day += timedelta(days=1)
        return day


class ResCompany(models.Model):
    _inherit = "res.company"

    ocd_news_weekday = fields.Selection(
        selection=[("0", "Monday"), ("1", "Tuesday"), ("2", "Wednesday"), ("3", "Thursday"), ("4", "Friday"),
                   ("5", "Saturday"), ("6", "Sunday")],
        string="Day Of The News To The Followers",
        default="4",
        help="Once a month (the first such day of the month) for every vendor, each week with OCD Business.",
    )
    ocd_live_messages_per_day = fields.Integer(
        string="Live Messages To The Followers Per Day At Most",
        default=2,
        help="Per vendor: the followers are told of their first lives of the day only. 0: never.",
    )


class OcdLiveBooking(models.Model):
    _inherit = "ocd.live.booking"

    ocd_followers_told_at = fields.Datetime(
        string="Followers Told At", readonly=True, copy=False,
        help="When the followers of the vendor were told this live started.",
    )
    ocd_followers_skipped = fields.Boolean(
        string="Followers Not Told", readonly=True, copy=False,
        help="Too many lives of the vendor today: the followers were not told of this one.",
    )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _ocd_is_new(self):
        """Put on sale in the last days: « New » on the boutique."""
        self.ensure_one()
        since = fields.Datetime.now() - timedelta(days=NEW_DAYS)
        return (self.ocd_review_date or self.create_date) >= since
