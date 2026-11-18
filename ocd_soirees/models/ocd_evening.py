"""The big evenings of OCD Live (chantier 7, design ProgrammeSoirees): Black Friday, Christmas,
Valentine's Day, Tabaski. The team creates the evening; the checked vendors of its countries are
invited, and join with a live during the evening and their promos of the evening (prices of the
products valid only during its hours)."""
import re
import time
import unicodedata
from datetime import timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.modules import module as odoo_module
from odoo.tools.misc import formatLang

from odoo.addons.ocd_live import tools

STATES = [("draft", "Being prepared"), ("open", "Registrations open"), ("cancelled", "Cancelled")]
# « Big evenings » on the programme: {database: (until, ids)}
_shown_cache = {}


def slugify(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:60] or "soiree"


class OcdEvening(models.Model):
    _name = "ocd.evening"
    _description = "Big Evening Of OCD Live"
    _inherit = ["mail.thread"]
    _order = "date_start desc, id desc"
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True, help="« Black Friday », « Christmas of OCD Live ».")
    slug = fields.Char(string="Address Of The Page", required=True, copy=False, index=True,
                       help="The end of the address of its page: /soirees/<address>.")
    company_id = fields.Many2one(comodel_name="res.company", required=True, index=True,
                                 default=lambda self: self.env.company)
    state = fields.Selection(selection=STATES, required=True, default="draft", tracking=True, index=True)
    image = fields.Image(string="Image", max_width=1600, max_height=900)
    description = fields.Text(help="What the evening is, in a sentence or two.")
    country_ids = fields.Many2many(comodel_name="res.country", string="Countries",
                                   help="The vendors of these countries are invited; its hours are the ones of the first.")
    date_start = fields.Datetime(string="Starts At", required=True, tracking=True)
    date_end = fields.Datetime(string="Ends At", required=True, tracking=True)
    registration_end = fields.Datetime(
        string="Registrations Until", tracking=True,
        help="The vendors join until then. Empty: a few days before the evening (setting).",
    )
    max_discount = fields.Integer(
        string="Discount At Most (%)", default=lambda self: self.env.company.ocd_promo_max_discount or 50,
        help="Of the price struck through of each product (its lowest price of the last days).",
    )
    tz = fields.Char(string="Time Zone", compute="_compute_tz")
    participation_ids = fields.One2many(comodel_name="ocd.evening.participation", inverse_name="evening_id",
                                        string="Participations")
    alert_ids = fields.One2many(comodel_name="ocd.evening.alert", inverse_name="evening_id", string="Tell Me")
    promo_ids = fields.One2many(comodel_name="ocd.product.promo", inverse_name="evening_id", string="Promos Of The Evening",
                                context={"active_test": False})
    invited_at = fields.Datetime(string="Vendors Invited At", readonly=True, copy=False)
    told_at = fields.Datetime(string="Start Told At", readonly=True, copy=False)
    vendor_count = fields.Integer(string="Vendors", compute="_compute_counts")
    promo_count = fields.Integer(string="Promos", compute="_compute_counts")
    to_check_count = fields.Integer(string="To Check", compute="_compute_counts")
    alert_count = fields.Integer(string="Told", compute="_compute_counts")

    _unique_slug = models.UniqueIndex("(slug)", "Another big evening has this address.")

    @api.depends("country_ids")
    def _compute_tz(self):
        for evening in self:
            code = (evening.country_ids[:1].code or "").upper()
            zones = pytz.country_timezones.get(code) or []
            evening.tz = zones[0] if zones else (evening.company_id.ocd_studio_tz or "Africa/Lome")

    def _compute_counts(self):
        for evening in self:
            approved = evening.participation_ids.filtered(lambda participation: participation.state == "approved")
            evening.vendor_count = len(approved)
            evening.promo_count = len(approved.promo_ids)
            evening.to_check_count = len(evening.participation_ids.filtered(lambda p: p.state == "to_check"))
            evening.alert_count = len(evening.alert_ids)

    @api.constrains("date_start", "date_end", "registration_end", "max_discount")
    def _check_dates(self):
        for evening in self:
            if evening.date_end <= evening.date_start:
                raise ValidationError(self.env._("The evening ends after it starts."))
            if evening.date_end - evening.date_start > timedelta(hours=24):
                raise ValidationError(self.env._("A big evening lasts a day at most."))
            if evening.registration_end and evening.registration_end > evening.date_start:
                raise ValidationError(self.env._("The registrations close before the evening."))
            if not 1 <= evening.max_discount <= 90:
                raise ValidationError(self.env._("The discount at most is between 1 and 90 %."))

    # === CREATE === #

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["slug"] = self._ocd_free_slug(vals.get("slug") or vals.get("name"))
        evenings = super().create(vals_list)
        for evening in evenings.filtered(lambda evening: not evening.registration_end):
            days = evening.company_id.ocd_evening_registration_days
            evening.registration_end = max(evening.date_start - timedelta(days=days), fields.Datetime.now())
        return evenings

    def write(self, vals):
        if vals.get("slug"):
            vals["slug"] = self._ocd_free_slug(vals["slug"], exclude=self)
        moved = {"date_start", "date_end"} & set(vals)
        result = super().write(vals)
        if moved:
            # The promos of the evening follow its hours
            for evening in self:
                evening.with_context(active_test=False).promo_ids.filtered(
                    lambda promo: not promo.stopped_at
                ).write({"date_start": evening.date_start, "date_end": evening.date_end})
        return result

    @api.model
    def _ocd_free_slug(self, text, exclude=None):
        base = slugify(text)
        slug, index = base, 1
        domain = [("id", "not in", exclude.ids)] if exclude else []
        while self.sudo().search_count(domain + [("slug", "=", slug)]):
            index += 1
            slug = f"{base}-{index}"
        return slug

    # === STATE === #

    def _ocd_public(self):
        self.ensure_one()
        return self.state == "open"

    def _ocd_running(self, now=None):
        self.ensure_one()
        now = now or fields.Datetime.now()
        return self.state == "open" and self.date_start <= now < self.date_end

    def _ocd_passed(self, now=None):
        self.ensure_one()
        return (now or fields.Datetime.now()) >= self.date_end

    def _ocd_registration_open(self, now=None):
        """Whether a vendor joins now: registrations open and not closed."""
        self.ensure_one()
        now = now or fields.Datetime.now()
        return self.state == "open" and now < (self.registration_end or self.date_start)

    @api.model
    def _ocd_shown(self):
        """The big evenings open whose end did not pass (the programme, the space of the vendors).
        Read again at most once a minute by each worker (every page of the programme asks)."""
        moment = time.monotonic()
        key = self.env.cr.dbname
        cached = _shown_cache.get(key)
        if cached and cached[0] > moment and not odoo_module.current_test:
            return self.sudo().browse(cached[1]).exists()
        evenings = self.sudo().search([("state", "=", "open"), ("date_end", ">", fields.Datetime.now())],
                                      order="date_start")
        _shown_cache[key] = (moment + 60, evenings.ids)
        return evenings

    def _ocd_invited_vendors(self):
        """The vendors invited: checked, of the countries of the evening."""
        self.ensure_one()
        domain = [("ocd_is_vendor", "=", True), ("ocd_vendor_state", "=", "approved")]
        if self.country_ids:
            domain.append(("country_id", "in", self.country_ids.ids))
        return self.env["res.partner"].sudo().search(domain)

    def _ocd_invites(self, vendor):
        """Whether `vendor` is invited to this evening."""
        self.ensure_one()
        return (
            vendor.ocd_is_vendor and vendor.ocd_vendor_state == "approved"
            and (not self.country_ids or vendor.country_id in self.country_ids)
        )

    def action_ocd_open(self):
        """« Open the registrations »: the evening is shown, its vendors are invited (once)."""
        for evening in self:
            if evening.state != "draft":
                continue
            if evening.date_end <= fields.Datetime.now():
                raise UserError(self.env._("This evening is over."))
            evening.state = "open"
            evening.message_post(body=self.env._("Registrations opened by %s.", self.env.user.name))
            if not evening.invited_at and self.env["ocd.automation"]._ocd_enabled("evening_invite"):
                vendors = evening._ocd_invited_vendors()
                evening.invited_at = fields.Datetime.now()
                if vendors:
                    evening._ocd_tell_invited(vendors)
        return True

    def action_ocd_cancel(self):
        """The evening no longer takes place: its promos stop, the vendors keep their lives."""
        for evening in self:
            evening.state = "cancelled"
            evening.promo_ids._ocd_stop(self.env._("The big evening is cancelled."))
            evening.message_post(body=self.env._("Cancelled by %s.", self.env.user.name))
        return True

    def action_ocd_view_participations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Participations of %s", self.name),
            "res_model": "ocd.evening.participation",
            "view_mode": "list,form",
            "domain": [("evening_id", "=", self.id)],
            "context": {"default_evening_id": self.id},
        }

    def action_ocd_view_promos(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Promos of %s", self.name),
            "res_model": "ocd.product.promo",
            "view_mode": "list",
            "domain": [("evening_id", "=", self.id)],
            "context": {"active_test": False},
        }

    def action_ocd_open_page(self):
        self.ensure_one()
        return {"type": "ir.actions.act_url", "url": f"/soirees/{self.slug}", "target": "new"}

    # === MESSAGES (ocd_soirees_whatsapp) === #

    def _ocd_tell_invited(self, vendors):
        """Hook: invite `vendors` to the evening."""

    def _ocd_tell_alerts(self):
        """Hook: tell the people who asked that the evening starts."""

    @api.model
    def _cron_ocd_evenings(self):
        """Every 5 minutes: the people who asked are told a little before the start (setting)."""
        if not self.env["ocd.automation"]._ocd_enabled("evening_alert"):
            return
        now = fields.Datetime.now()
        for evening in self.sudo().search([("state", "=", "open"), ("told_at", "=", False),
                                            ("date_end", ">", now)]):
            minutes = evening.company_id.ocd_evening_alert_minutes
            if evening.date_start - timedelta(minutes=minutes) <= now:
                evening.told_at = now
                if evening.alert_ids:
                    evening._ocd_tell_alerts()

    # === TEXTS === #

    def _ocd_local(self, value, tz_name=None):
        self.ensure_one()
        return tools.to_tz(value, tz_name or self.tz)

    def _ocd_hour(self, local):
        if (self.env.lang or "").startswith("fr"):
            return f"{local.hour} h {local.minute:02d}" if local.minute else f"{local.hour} h"
        return f"{local:%H:%M}"

    def _ocd_hours_text(self, tz_name=None):
        """« 18:00 – 23:00 »."""
        self.ensure_one()
        return f"{self._ocd_hour(self._ocd_local(self.date_start, tz_name))} – {self._ocd_hour(self._ocd_local(self.date_end, tz_name))}"

    def _ocd_when_text(self, tz_name=None, pattern="EEEE d MMMM"):
        """« Friday 27 November · 18:00 – 23:00 »."""
        self.ensure_one()
        local = self._ocd_local(self.date_start, tz_name)
        return self.env._("%(day)s · %(hours)s", day=tools.day_text(self.env, local.date(), pattern, capital=True),
                          hours=self._ocd_hours_text(tz_name))

    def _ocd_when_sentence(self, tz_name=None):
        """« Friday 27 November from 18:00 to 23:00 », for the messages."""
        self.ensure_one()
        local = self._ocd_local(self.date_start, tz_name)
        return self.env._("%(day)s from %(start)s to %(end)s",
                          day=tools.day_text(self.env, local.date(), "EEEE d MMMM"),
                          start=self._ocd_hour(local), end=self._ocd_hour(self._ocd_local(self.date_end, tz_name)))

    def _ocd_registration_day(self, tz_name=None):
        self.ensure_one()
        local = self._ocd_local(self.registration_end or self.date_start, tz_name)
        return tools.day_text(self.env, local.date(), "EEEE d MMMM")

    def _ocd_left_text(self, now=None):
        """« 9 d 4 h », « 2 h 10 », « 12 min » before the start."""
        self.ensure_one()
        seconds = max(int((self.date_start - (now or fields.Datetime.now())).total_seconds()), 0)
        days, rest = divmod(seconds, 86400)
        hours, rest = divmod(rest, 3600)
        if days:
            return self.env._("%(days)s d %(hours)s h", days=days, hours=hours)
        if hours:
            return f"{hours} h {rest // 60:02d}"
        return self.env._("%s min", rest // 60)

    def _ocd_countries_text(self):
        self.ensure_one()
        return " · ".join(self.country_ids.mapped("name")) or self.env._("Every country")

    def _ocd_number(self, value):
        return formatLang(self.env, value, digits=0)

    def _ocd_public_path(self):
        self.ensure_one()
        return f"/soirees/{self.slug}"

    def _ocd_image_url(self):
        self.ensure_one()
        if not self.image:
            return False
        return f"/soirees/image/{self.id}?v={self.write_date:%Y%m%d%H%M%S}"

    def _ocd_lives(self):
        """The lives of the evening: the confirmed lives of the vendors who joined, during its hours."""
        self.ensure_one()
        vendors = self.participation_ids.filtered(lambda participation: participation.state == "approved").vendor_id
        if not vendors:
            return self.env["ocd.live.booking"]
        return self.env["ocd.live.booking"].sudo().search([
            ("partner_id", "in", vendors.ids), ("state", "=", "confirmed"),
            ("start_datetime", "<", self.date_end), ("end_datetime", ">", self.date_start),
        ], order="start_datetime, id")

    def _ocd_best_discount(self, vendor=None):
        """The biggest discount of the promos of the evening (of `vendor`): « up to -40 % »."""
        self.ensure_one()
        promos = self.promo_ids.filtered(
            lambda promo: promo.active and (not vendor or promo.vendor_id == vendor)
        )
        return max(promos.mapped("discount") or [0])


class OcdEveningAlert(models.Model):
    """« Tell me on WhatsApp » of a big evening: a message a little before its start."""

    _name = "ocd.evening.alert"
    _description = "Big Evening: Tell Me"

    evening_id = fields.Many2one(comodel_name="ocd.evening", required=True, index=True, ondelete="cascade")
    partner_id = fields.Many2one(comodel_name="res.partner", required=True, index=True, ondelete="cascade")

    _unique_alert = models.UniqueIndex("(evening_id, partner_id)", "This contact is already told of this evening.")
