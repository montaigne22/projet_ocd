"""OCD Vote (chantier 4 of the roadmap, design OcdVote): paid votes for contests (miss, awards,
talents, schools). A contest of an organiser checked by the team, or of OCD Live; numbered
candidates; the public buys votes (one, a pack, or another number) and pays with the payment form
of OCD Live. Only the paid votes count, each one linked to its payment (ocd.vote)."""
import re
import secrets
import time
import unicodedata
from datetime import timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.modules import module as odoo_module
from odoo.tools.misc import format_amount, formatLang, hmac

from odoo.addons.ocd_live import tools

STATES = [
    ("draft", "Being prepared"),
    ("to_check", "To check"),
    ("approved", "Checked"),
    ("closed", "Votes closed"),
    ("done", "Results"),
    ("cancelled", "Cancelled"),
]
# A contest is « open » between its opening and its end, once checked by the team
PAYOUT_STATES = [("none", "Not yet"), ("to_pay", "To pay"), ("paid", "Paid")]
# The organiser is paid this many days after the results
PAYOUT_DAYS = 3
# « Votes » in the menu: {database: (until, shown)}
_menu_cache = {}


def slugify(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:60] or "concours"


class OcdVoteContest(models.Model):
    _name = "ocd.vote.contest"
    _description = "Contest Of OCD Vote"
    _inherit = ["mail.thread"]
    _order = "date_close desc, id desc"
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    slug = fields.Char(
        string="Address", required=True, copy=False, index=True,
        help="The end of the address of its page: /vote/<address>.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    organizer_id = fields.Many2one(
        comodel_name="res.partner", string="Organiser", index=True, tracking=True,
        help="Empty: a contest of OCD Live. The organiser logs in with their number and adds the candidates.",
    )
    organizer_verified = fields.Boolean(related="organizer_id.ocd_vote_organizer_verified")
    country_id = fields.Many2one(comodel_name="res.country", string="Country", required=True,
                                 default=lambda self: self.env.company.country_id)
    city = fields.Char()
    tz = fields.Char(string="Time Zone", compute="_compute_tz", help="The hours of the contest are shown at this hour.")
    image = fields.Image(string="Banner", max_width=1600, max_height=900)
    description = fields.Text(help="What the contest is, in a few words.")
    prize = fields.Char(string="Prize", help="« The crown, 1,000,000 F and a contract of a year ».")
    rules = fields.Text(
        string="Rules",
        help="The rules the voters read: the price of a vote, the end, how the winner is chosen. Nothing drawn by "
        "lot, nothing to win for the voters.",
    )
    state = fields.Selection(selection=STATES, required=True, default="draft", tracking=True, index=True)
    date_open = fields.Datetime(string="Votes Open At", required=True, tracking=True)
    date_close = fields.Datetime(string="Votes Close At", required=True, tracking=True)
    vote_price = fields.Monetary(
        string="Price Of A Vote", required=True, tracking=True, default=lambda self: self.env.company.ocd_vote_price,
    )
    pack_ids = fields.One2many(comodel_name="ocd.vote.pack", inverse_name="contest_id", string="Packs", copy=True)
    organizer_share = fields.Float(
        string="Share Of The Organiser (%)", tracking=True,
        default=lambda self: self.env.company.ocd_vote_organizer_share,
    )
    hide_hours = fields.Integer(
        string="Ranking Hidden The Last Hours", tracking=True,
        default=lambda self: self.env.company.ocd_vote_hide_hours,
        help="The order stays, the numbers of votes are hidden until the results. 0: always shown.",
    )
    final_at = fields.Datetime(string="Final At", help="The live of the final, announced on the page.")
    final_url = fields.Char(string="Live Of The Final", help="Where the final is watched (TikTok, Facebook...).")
    final_told_at = fields.Datetime(readonly=True, copy=False)
    candidate_ids = fields.One2many(comodel_name="ocd.vote.candidate", inverse_name="contest_id", string="Candidates")
    vote_ids = fields.One2many(comodel_name="ocd.vote", inverse_name="contest_id", string="Payments")
    vote_count = fields.Integer(string="Votes", compute="_compute_totals")
    voter_count = fields.Integer(string="Voters", compute="_compute_totals")
    amount_total = fields.Monetary(string="Collected", compute="_compute_totals")
    organizer_amount = fields.Monetary(string="Share Of The Organiser", compute="_compute_totals")
    payment_count = fields.Integer(string="Payments", compute="_compute_totals")
    results_at = fields.Datetime(string="Results Published At", readonly=True, copy=False)
    payout_state = fields.Selection(selection=PAYOUT_STATES, string="Payout", default="none", tracking=True, copy=False)
    payout_due = fields.Date(string="Payout Before", readonly=True, copy=False)
    payout_momo = fields.Char(string="Mobile Money Of The Organiser", tracking=True)
    payout_reference = fields.Char(string="Transfer Reference", tracking=True, copy=False)
    payout_date = fields.Date(string="Paid On", tracking=True, copy=False)
    access_secret = fields.Char(copy=False, groups="base.group_system")

    _unique_slug = models.UniqueIndex("(slug)", "Another contest has this address.")

    # === COMPUTE === #

    @api.depends("country_id")
    def _compute_tz(self):
        for contest in self:
            zones = pytz.country_timezones.get((contest.country_id.code or "").upper()) or []
            contest.tz = zones[0] if zones else (contest.company_id.ocd_studio_tz or "Africa/Lome")

    @api.depends("vote_ids.state", "vote_ids.votes", "vote_ids.amount_company", "organizer_share")
    def _compute_totals(self):
        Vote = self.env["ocd.vote"].sudo()
        groups = {
            contest: (votes, amount, count)
            for contest, votes, amount, count in Vote._read_group(
                [("contest_id", "in", self.ids), ("state", "=", "paid")], ["contest_id"],
                ["votes:sum", "amount_company:sum", "__count"],
            )
        }
        voters = dict(Vote._read_group(
            [("contest_id", "in", self.ids), ("state", "=", "paid")], ["contest_id"], ["partner_id:count_distinct"],
        ))
        for contest in self:
            votes, amount, count = groups.get(contest._origin, (0, 0.0, 0))
            contest.vote_count = votes
            contest.amount_total = amount
            contest.payment_count = count
            contest.voter_count = voters.get(contest._origin, 0)
            contest.organizer_amount = contest.currency_id.round(amount * contest.organizer_share / 100)

    @api.constrains("date_open", "date_close")
    def _check_dates(self):
        for contest in self:
            if contest.date_close <= contest.date_open:
                raise ValidationError(self.env._("The votes close after they open."))

    @api.constrains("vote_price", "organizer_share")
    def _check_price(self):
        for contest in self:
            if contest.vote_price <= 0:
                raise ValidationError(self.env._("A vote has a price: there are no free votes."))
            if not 0 <= contest.organizer_share <= 100:
                raise ValidationError(self.env._("The share of the organiser is between 0 and 100 %."))

    # === CREATE === #

    @api.model_create_multi
    def create(self, vals_list):
        company = self.env.company
        for vals in vals_list:
            vals["slug"] = self._ocd_free_slug(vals.get("slug") or vals.get("name"))
            if "pack_ids" not in vals:
                vals["pack_ids"] = [
                    fields.Command.create({"votes": votes, "price": price})
                    for votes, price in company._ocd_vote_default_packs()
                ]
        return super().create(vals_list)

    def write(self, vals):
        if "slug" in vals:
            vals["slug"] = self._ocd_free_slug(vals["slug"], exclude=self)
        locked = {"vote_price", "pack_ids", "date_close", "date_open", "organizer_share"} & set(vals)
        if locked and not self.env.context.get("ocd_vote_force"):
            for contest in self:
                if contest.state in ("closed", "done") or (contest.state == "approved" and contest._ocd_started()):
                    raise UserError(self.env._(
                        "The votes of %s are open: the price, the packs, the dates and the share no longer change "
                        "(the voters saw them in the rules).", contest.name
                    ))
        return super().write(vals)

    @api.model
    def _ocd_free_slug(self, text, exclude=None):
        base = slugify(text)
        slug, index = base, 1
        domain = [("id", "not in", exclude.ids)] if exclude else []
        while self.sudo().with_context(active_test=False).search_count(domain + [("slug", "=", slug)]):
            index += 1
            slug = f"{base}-{index}"
        return slug

    # === STATE === #

    @api.model
    def _ocd_menu_shown(self):
        """Whether « Votes » is in the menu: a contest checked, not over for long. Read again at most
        once a minute by each worker (every page asks)."""
        now = time.monotonic()
        key = self.env.cr.dbname
        cached = _menu_cache.get(key)
        if cached and cached[0] > now and not odoo_module.current_test:
            return cached[1]
        shown = bool(self.sudo().search_count([
            ("state", "in", ("approved", "closed", "done")),
            ("date_close", ">", fields.Datetime.now() - timedelta(days=7)),
        ], limit=1))
        _menu_cache[key] = (now + 60, shown)
        return shown

    def _ocd_started(self, now=None):
        self.ensure_one()
        return (now or fields.Datetime.now()) >= self.date_open

    def _ocd_is_open(self, now=None):
        """Whether the public may vote now: checked by the team, between the opening and the end."""
        self.ensure_one()
        now = now or fields.Datetime.now()
        return self.state == "approved" and self.date_open <= now < self.date_close

    def _ocd_public(self):
        """Whether the page of the contest is shown: checked, closed or with its results."""
        self.ensure_one()
        return self.state in ("approved", "closed", "done")

    def _ocd_hidden(self, now=None):
        """The numbers of votes are hidden: the last hours before the end (setting), until the
        results. The order stays."""
        self.ensure_one()
        now = now or fields.Datetime.now()
        if self.state == "done" or not self.hide_hours:
            return False
        return now >= self.date_close - timedelta(hours=self.hide_hours)

    def action_ocd_send_to_check(self):
        """The organiser sends the contest and its candidates to the team."""
        for contest in self:
            if contest.state != "draft":
                continue
            if not contest.candidate_ids:
                raise UserError(self.env._("Add the candidates first."))
            contest.state = "to_check"
            contest.message_post(body=self.env._("Sent to OCD Live to check."))
        return True

    def action_ocd_approve(self):
        """« Check and open »: the contest and its candidates waiting are shown, the votes open at
        the opening date."""
        for contest in self:
            if contest.state not in ("draft", "to_check"):
                continue
            if not contest.candidate_ids.filtered(lambda candidate: candidate.state != "refused"):
                raise UserError(self.env._("A contest without candidates cannot open."))
            contest.candidate_ids.filtered(lambda candidate: candidate.state == "to_check").write({"state": "approved"})
            contest.state = "approved"
            contest.message_post(body=self.env._("Checked by %s: the votes open on the date of the contest.",
                                                 self.env.user.name))
        return True

    def action_ocd_refuse(self, reason=None):
        for contest in self:
            contest.state = "draft"
            contest.message_post(body=self.env._("Sent back to the organiser: %s",
                                                 reason.message or reason.name if reason else "-"))
        self._ocd_tell_organizer_refused(reason)
        return True

    def _ocd_tell_organizer_refused(self, reason):
        """Hook: tell the organiser why their contest was sent back (ocd_vote_whatsapp)."""

    def action_ocd_close(self):
        """« Close now »: no vote any more (the payments started later are refunded)."""
        now = fields.Datetime.now()
        for contest in self.filtered(lambda contest: contest.state == "approved"):
            values = {"state": "closed"}
            if contest.date_close > now:
                values["date_close"] = now
            contest.with_context(ocd_vote_force=True).write(values)
            contest.message_post(body=self.env._("Votes closed."))
        return True

    def action_ocd_publish_results(self):
        """« Certified results »: the ranking is final and shown with its numbers; the payout of the
        organiser is due a few days after."""
        for contest in self:
            if contest.state != "closed":
                raise UserError(self.env._("Close the votes of %s first.", contest.name))
            contest.write({
                "state": "done",
                "results_at": fields.Datetime.now(),
                "payout_state": "to_pay" if contest.organizer_id and contest.organizer_amount > 0 else "none",
                "payout_due": fields.Date.context_today(contest) + timedelta(days=PAYOUT_DAYS),
            })
            contest.message_post(body=self.env._("Results published: %s.", contest._ocd_winner_text() or "-"))
        return True

    def action_ocd_print_results(self):
        self.ensure_one()
        if self.state != "done":
            raise UserError(self.env._("The results are certified once published."))
        return self.env.ref("ocd_vote.action_report_results").report_action(self)

    def action_ocd_payout_paid(self):
        for contest in self:
            if contest.payout_state != "to_pay":
                continue
            if not contest.payout_reference:
                raise UserError(self.env._("Write the reference of the transfer first."))
            contest.write({"payout_state": "paid", "payout_date": fields.Date.context_today(contest)})
        return True

    def action_ocd_cancel(self):
        for contest in self:
            if contest.vote_ids.filtered(lambda vote: vote.state == "paid"):
                raise UserError(self.env._("%s has paid votes: close it instead.", contest.name))
            contest.state = "cancelled"
        return True

    def action_ocd_view_votes(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Payments of %s", self.name),
            "res_model": "ocd.vote",
            "view_mode": "list,form",
            "domain": [("contest_id", "=", self.id)],
            "context": {"search_default_paid": 1},
        }

    def action_ocd_open_page(self):
        self.ensure_one()
        return {"type": "ir.actions.act_url", "url": f"/vote/{self.slug}", "target": "new"}

    def action_ocd_open_band(self):
        self.ensure_one()
        return {"type": "ir.actions.act_url", "url": self._ocd_band_path(), "target": "new"}

    # === SCHEDULED TASK === #

    @api.model
    def _cron_ocd_vote(self):
        """Every few minutes: the contests whose end passed are closed; the votes not paid in time
        are cancelled; the people who asked are told that the final starts."""
        now = fields.Datetime.now()
        Automation = self.env["ocd.automation"]
        if Automation._ocd_enabled("vote_close"):
            self.sudo().search([("state", "=", "approved"), ("date_close", "<=", now)]).action_ocd_close()
        self.env["ocd.vote"].sudo()._ocd_cancel_unpaid(now)
        if Automation._ocd_enabled("vote_final"):
            finals = self.sudo().search([
                ("state", "=", "approved"), ("final_at", "!=", False), ("final_at", "<=", now + timedelta(minutes=10)),
                ("final_at", ">", now - timedelta(hours=1)), ("final_told_at", "=", False),
            ])
            for contest in finals:
                contest.final_told_at = now
                alerts = self.env["ocd.vote.alert"].sudo().search([("contest_id", "=", contest.id)])
                if alerts:
                    alerts._ocd_tell_final()

    # === PRICES === #

    def _ocd_price(self, votes):
        """The price of `votes` votes: the one of a pack of this number, else the price of a vote."""
        self.ensure_one()
        pack = self.pack_ids.filtered(lambda pack: pack.votes == votes)[:1]
        return pack.price if pack else votes * self.vote_price

    def _ocd_choices(self):
        """The choices of the page of a candidate: 1 vote, then the packs."""
        self.ensure_one()
        _ = self.env._
        rows = [{"votes": 1, "price": self.vote_price, "label": _("1 vote"), "offered": False}]
        for pack in self.pack_ids.sorted("votes"):
            offered = pack._ocd_offered()
            rows.append({
                "votes": pack.votes, "price": pack.price, "label": _("%s votes", pack.votes),
                "offered": (_("1 offered") if offered == 1 else _("%s offered", offered)) if offered else False,
            })
        for row in rows:
            row["price_text"] = self._ocd_money(row["price"])
        return rows

    # === TEXTS AND ADDRESSES === #

    def _ocd_local(self, value):
        self.ensure_one()
        return tools.to_tz(value, self.tz)

    def _ocd_close_text(self):
        """« Saturday 28 November at 20:00 », at the hour of the contest."""
        self.ensure_one()
        local = self._ocd_local(self.date_close)
        return self.env._("%(day)s at %(hour)s", day=tools.day_text(self.env, local.date(), "EEEE d MMMM"),
                          hour=self._ocd_hour(local))

    def _ocd_hour(self, local):
        if (self.env.lang or "").startswith("fr"):
            return f"{local.hour} h {local.minute:02d}" if local.minute else f"{local.hour} h"
        return f"{local:%H:%M}"

    def _ocd_left_text(self, now=None):
        """« 10 d 4 h », « 1 h 12 », « 12 min » before the end."""
        self.ensure_one()
        seconds = max(int((self.date_close - (now or fields.Datetime.now())).total_seconds()), 0)
        days, rest = divmod(seconds, 86400)
        hours, rest = divmod(rest, 3600)
        minutes = rest // 60
        if days:
            return self.env._("%(days)s d %(hours)s h", days=days, hours=hours)
        if hours:
            return f"{hours} h {minutes:02d}"
        return self.env._("%s min", minutes)

    def _ocd_money(self, amount):
        self.ensure_one()
        return format_amount(self.env, amount, self.currency_id)

    def _ocd_number(self, value):
        return formatLang(self.env, value, digits=0)

    def _ocd_secret(self):
        self.ensure_one()
        contest = self.sudo()
        if not contest.access_secret:
            contest.access_secret = secrets.token_urlsafe(12)
        return contest.access_secret

    def _ocd_band_path(self):
        """The band for the live software: an address of its own, not guessed from the name."""
        self.ensure_one()
        return f"/vote/{self.slug}/bandeau/{self._ocd_secret()}"

    def _ocd_signature(self):
        """The signature of the certified results: the votes of each candidate, signed by the
        server; the page of the results shows it again for anyone to compare."""
        self.ensure_one()
        rows = ",".join(f"{row['candidate'].number}:{row['votes']}" for row in self._ocd_ranking(now=self.results_at))
        message = f"{self.id}:{self.slug}:{fields.Datetime.to_string(self.date_close)}:{rows}"
        return hmac(self.env(su=True), "ocd_vote.results", message)[:16].upper()

    def _ocd_report_texts(self):
        """The sentences of the certified results (PDF)."""
        self.ensure_one()
        _ = self.env._
        return {
            "head": _("Certified results of OCD Live · %(organizer)s · votes closed on %(close)s",
                      organizer=self.organizer_id.name or "OCD Live", close=self._ocd_close_text()),
            "count": _("%(votes)s votes paid by %(voters)s people. Only the paid votes count, each one linked to its "
                       "payment; the refunded payments and the payments started after the end are not counted.",
                       votes=self._ocd_number(self.vote_count), voters=self._ocd_number(self.voter_count)),
            "signature": _("Signature: %(signature)s. The same signature is on the page of the results: %(url)s",
                           signature=self._ocd_signature(), url=f"{self.get_base_url()}/vote/{self.slug}/resultats"),
        }

    # === THE RANKING === #

    def _ocd_ranking(self, now=None):
        """The candidates shown, the most votes first: [{candidate, votes, rank, width}]. Equal
        votes: the same rank, the smaller number first."""
        self.ensure_one()
        candidates = self.candidate_ids.filtered(lambda candidate: candidate._ocd_shown())
        counts = candidates._ocd_vote_counts()
        ordered = candidates.sorted(lambda candidate: (-counts.get(candidate.id, 0), candidate.number))
        top = max(counts.values() or [0])
        rows, rank, previous = [], 0, None
        for index, candidate in enumerate(ordered):
            votes = counts.get(candidate.id, 0)
            if votes != previous:
                rank, previous = index + 1, votes
            rows.append({
                "candidate": candidate,
                "votes": votes,
                "rank": rank,
                "width": round(votes * 100 / top) if top else 0,
            })
        return rows

    def _ocd_rank_label(self, rank):
        """« 1st », « 2nd » (« 1re », « 2e » in French: the candidates of a miss)."""
        _ = self.env._
        if rank == 1:
            return _("1st")
        if rank == 2:
            return _("2nd")
        if rank == 3:
            return _("3rd")
        return _("%sth", rank)

    def _ocd_winner_text(self):
        self.ensure_one()
        ranking = self._ocd_ranking()
        if not ranking or not ranking[0]["votes"]:
            return False
        return f"N° {ranking[0]['candidate'].number} {ranking[0]['candidate'].name}"


class OcdVotePack(models.Model):
    _name = "ocd.vote.pack"
    _description = "Pack Of Votes"
    _order = "votes"

    contest_id = fields.Many2one(comodel_name="ocd.vote.contest", required=True, index=True, ondelete="cascade")
    currency_id = fields.Many2one(related="contest_id.currency_id")
    votes = fields.Integer(required=True)
    price = fields.Monetary(required=True)

    @api.constrains("votes", "price")
    def _check_pack(self):
        for pack in self:
            if pack.votes < 2 or pack.price <= 0:
                raise ValidationError(self.env._("A pack has 2 votes or more, and a price."))

    def _ocd_offered(self):
        """The votes the pack gives for free against the price of a vote: « 1 offered »."""
        self.ensure_one()
        price = self.contest_id.vote_price
        return max(int(round(self.votes - self.price / price)), 0) if price else 0


class OcdVoteAlert(models.Model):
    """« Tell me on WhatsApp » of the final: a message when its live starts."""

    _name = "ocd.vote.alert"
    _description = "Final Of A Contest: Tell Me"

    contest_id = fields.Many2one(comodel_name="ocd.vote.contest", required=True, index=True, ondelete="cascade")
    partner_id = fields.Many2one(comodel_name="res.partner", required=True, index=True, ondelete="cascade")

    _unique_alert = models.UniqueIndex("(contest_id, partner_id)", "This contact is already told of this final.")

    def _ocd_tell_final(self):
        """Tell them the final starts (ocd_vote_whatsapp)."""
