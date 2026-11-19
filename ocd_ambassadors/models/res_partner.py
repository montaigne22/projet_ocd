import re
import secrets
import unicodedata
from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

STATES = [
    ("new", "Number to check"),
    ("requested", "Asked"),
    ("active", "Active"),
    ("to_check", "To check"),
    ("paused", "Paused"),
    ("closed", "Closed"),
]
# The ambassadors who open their space (a paused one sees why, gains kept)
SPACE_STATES = ("active", "to_check", "paused")
# The links of these ambassadors still lead to the page (a closed one leads there too, without gain)
CODE_LETTERS = 6
# The outcomes of the last parcels that make the rate of returns
RETURN_WINDOW_DAYS = 90


def digits(number):
    return re.sub(r"\D", "", number or "")


def same_number(first, second):
    """Whether two numbers are the same phone: the same last digits, 8 at least (the numbers of
    the site keep their country code, the typed ones do not always)."""
    first, second = digits(first), digits(second)
    size = min(len(first), len(second))
    return size >= 8 and first[-size:] == second[-size:]


class ResPartner(models.Model):
    """An ambassador of OCD Live (chantier 11, design Ambassadeurs): a contact of their own,
    found by their WhatsApp number among the ambassadors only (a customer, a vendor or a courier
    who becomes an ambassador keeps their other contact: the checks compare the numbers). Paid
    every week on their Mobile Money, with the payouts of the shop."""

    _inherit = "res.partner"

    ocd_ambassador_state = fields.Selection(
        selection=STATES, string="Ambassador", copy=False, index="btree_not_null", tracking=True,
    )
    ocd_ambassador_code = fields.Char(
        string="Code Of The Links", copy=False, readonly=True,
        help="In the personal links of the ambassador: ocdlive.com/a/GRACE7.",
    )
    ocd_ambassador_since = fields.Date(string="Ambassador Since", copy=False)
    ocd_ambassador_charter_at = fields.Datetime(string="Charter Accepted At", copy=False, readonly=True)
    ocd_ambassador_momo_since = fields.Datetime(
        string="Payout Number Since", copy=False, readonly=True,
        help="A new payout number waits the hours of the settings before the first payout.",
    )
    ocd_ambassador_id_checked = fields.Boolean(string="Identity Seen (Ambassador)", copy=False, tracking=True)
    ocd_ambassador_note = fields.Char(
        string="Why", copy=False, tracking=True, help="Why the account is to check, paused or closed.",
    )
    ocd_ambassador_told_on = fields.Date(string="Gains Of The Day Told On", copy=False, readonly=True)
    ocd_ambassador_gain_ids = fields.One2many(
        comodel_name="ocd.ambassador.gain", inverse_name="ambassador_id", string="Gains Of The Ambassador",
    )
    ocd_ambassador_visit_count = fields.Integer(string="Visits (30 Days)", compute="_compute_ocd_ambassador_figures")
    ocd_ambassador_order_count = fields.Integer(string="Orders (30 Days)", compute="_compute_ocd_ambassador_figures")
    ocd_ambassador_delivered_count = fields.Integer(
        string="Delivered (30 Days)", compute="_compute_ocd_ambassador_figures",
    )
    ocd_ambassador_return_count = fields.Integer(string="Returns (30 Days)", compute="_compute_ocd_ambassador_figures")
    ocd_ambassador_month_amount = fields.Monetary(
        string="Gains This Month", compute="_compute_ocd_ambassador_figures", currency_field="currency_id",
    )
    ocd_ambassador_to_pay = fields.Monetary(
        string="To Pay", compute="_compute_ocd_ambassador_money", currency_field="currency_id",
        help="Gains confirmed and not paid yet, minus the returns taken back.",
    )
    ocd_ambassador_earned_total = fields.Monetary(
        string="Earned Since The Start", compute="_compute_ocd_ambassador_money", currency_field="currency_id",
    )

    _unique_ocd_ambassador_code = models.UniqueIndex(
        "(ocd_ambassador_code) WHERE ocd_ambassador_code IS NOT NULL", "Another ambassador has this code."
    )

    # === FIGURES === #

    def _compute_ocd_ambassador_figures(self):
        ambassadors = self.filtered("ocd_ambassador_state")
        (self - ambassadors).update({
            "ocd_ambassador_visit_count": 0, "ocd_ambassador_order_count": 0, "ocd_ambassador_delivered_count": 0,
            "ocd_ambassador_return_count": 0, "ocd_ambassador_month_amount": 0.0,
        })
        if not ambassadors:
            return
        now = fields.Datetime.now()
        since = now - timedelta(days=30)
        Gain = self.env["ocd.ambassador.gain"].sudo()
        orders = {partner: count for partner, count in Gain._read_group(
            [("ambassador_id", "in", ambassadors.ids), ("create_date", ">=", since), ("state", "!=", "refused")],
            ["ambassador_id"], ["order_id:count_distinct"])}
        delivered = {partner: count for partner, count in Gain._read_group(
            [("ambassador_id", "in", ambassadors.ids), ("delivered_at", ">=", since)],
            ["ambassador_id"], ["__count"])}
        returned = {partner: count for partner, count in Gain._read_group(
            [("ambassador_id", "in", ambassadors.ids), ("write_date", ">=", since), ("bad_outcome", "=", True)],
            ["ambassador_id"], ["__count"])}
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        months = {partner: amount for partner, amount in Gain._read_group(
            [("ambassador_id", "in", ambassadors.ids), ("delivered_at", ">=", month_start),
             ("state", "in", ("delivered", "held", "confirmed"))],
            ["ambassador_id"], ["amount:sum"])}
        Count = self.env["ocd.vendor.count"].sudo()
        first = fields.Date.context_today(self) - timedelta(days=29)
        visits = {vendor: count for vendor, count in Count._read_group(
            [("vendor_id", "in", ambassadors.ids), ("kind", "=", "ambassador_visit"), ("day", ">=", first)],
            ["vendor_id"], ["count:sum"])}
        for partner in ambassadors:
            partner.update({
                "ocd_ambassador_visit_count": visits.get(partner, 0),
                "ocd_ambassador_order_count": orders.get(partner, 0),
                "ocd_ambassador_delivered_count": delivered.get(partner, 0),
                "ocd_ambassador_return_count": returned.get(partner, 0),
                "ocd_ambassador_month_amount": months.get(partner, 0.0),
            })

    def _compute_ocd_ambassador_money(self):
        """From the bills and the credit notes of the gains: the money is counted where it is
        written, never from a counter of its own."""
        ambassadors = self.filtered("ocd_ambassador_state")
        (self - ambassadors).update({"ocd_ambassador_to_pay": 0.0, "ocd_ambassador_earned_total": 0.0})
        if not ambassadors:
            return
        Move = self.env["account.move"].sudo()
        to_pay = dict.fromkeys(ambassadors.ids, 0.0)
        earned = dict.fromkeys(ambassadors.ids, 0.0)
        for partner, move_type, payment_state, total in Move._read_group(
            [("partner_id", "in", ambassadors.ids), ("ocd_ambassador_kind", "!=", False), ("state", "=", "posted")],
            ["partner_id", "move_type", "payment_state"], ["amount_total:sum"],
        ):
            sign = 1 if move_type == "in_invoice" else -1
            earned[partner.id] += sign * total
            if payment_state in ("not_paid", "partial"):
                to_pay[partner.id] += sign * total
        for partner in ambassadors:
            partner.ocd_ambassador_to_pay = to_pay[partner.id]
            partner.ocd_ambassador_earned_total = earned[partner.id]

    # === WHO IS WHO === #

    def _ocd_ambassador_numbers(self):
        """The numbers of this contact that make « the same person »: their WhatsApp, their
        Mobile Money."""
        self.ensure_one()
        return [number for number in (self.phone, self.ocd_payout_momo) if number]

    def _ocd_ambassador_same_person(self, other):
        """Whether `other` (a customer, a vendor) is this ambassador: the same contact, or one of
        their numbers."""
        self.ensure_one()
        other = other.sudo()
        if not other:
            return False
        if other == self or other.commercial_partner_id == self.commercial_partner_id:
            return True
        others = [number for number in (other.phone, other.ocd_payout_momo) if number]
        return any(same_number(mine, theirs) for mine in self._ocd_ambassador_numbers() for theirs in others)

    @api.model
    def _ocd_find_ambassador_by_phone(self, phone, states=SPACE_STATES + ("new",)):
        return self.sudo()._ocd_find_by_phone(phone, [("ocd_ambassador_state", "in", list(states))])

    @api.model
    def _ocd_ambassador_by_code(self, code):
        code = re.sub(r"[^A-Z0-9]", "", (code or "").upper())[:12]
        if not code:
            return self.browse()
        return self.sudo().search([("ocd_ambassador_code", "=", code), ("ocd_ambassador_state", "!=", False)], limit=1)

    @api.model
    def _ocd_new_ambassador_code(self, name):
        """« GRACE7 »: the first letters of the first name, then digits, never taken."""
        word = (name or "").split()[0] if (name or "").split() else ""
        letters = re.sub(r"[^A-Z]", "", unicodedata.normalize("NFKD", word).encode("ascii", "ignore").decode().upper())
        letters = (letters or "OCD")[:CODE_LETTERS]
        for size in (1, 1, 2, 2, 3, 4):
            code = f"{letters}{secrets.randbelow(10 ** size - 1) + 1}"
            if not self.sudo().search_count([("ocd_ambassador_code", "=", code)]):
                return code
        return f"{letters}{secrets.token_hex(3).upper()}"

    # === SIGN UP, OPEN, MOBILE MONEY === #

    @api.model
    def _ocd_ambassador_signup(self, name, phone, country, momo, lang=None):
        """A person asks to become an ambassador from /ambassadeurs (the charter ticked). Return
        the contact: new (the number is checked by the code on WhatsApp), or asked (the team
        opens it). An ambassador who already has this number keeps their account."""
        _ = self.env._
        company = self.env.company
        if company.ocd_ambassador_open == "closed":
            raise UserError(_("The program of the ambassadors is closed for now."))
        name = (name or "").strip()
        if len(name) < 2:
            raise UserError(_("Write your name."))
        existing = self._ocd_find_ambassador_by_phone(phone, states=[state for state, _label in STATES])
        if existing:
            if existing.ocd_ambassador_state == "closed":
                raise UserError(_("This number can no longer open an account of ambassador: write to OCD Live."))
            return existing
        partner = self.sudo().create({
            "name": name,
            "phone": phone,
            "country_id": country.id if country else False,
            "lang": lang or self.env.lang or "en_US",
            "company_id": False,
            "ocd_ambassador_state": "requested" if company.ocd_ambassador_open == "invited" else "new",
            "ocd_ambassador_code": self._ocd_new_ambassador_code(name),
            "ocd_ambassador_charter_at": fields.Datetime.now(),
            "ocd_payout_momo": momo,
            "ocd_payout_frequency": "weekly",
        })
        partner.message_post(body=_("Asked to become an ambassador on the site."))
        return partner

    def _ocd_ambassador_open_account(self):
        """The number is checked (the code on WhatsApp) or the team opens the account: active,
        or to check when their Mobile Money is the one of another ambassador."""
        for partner in self.sudo():
            if partner.ocd_ambassador_state not in ("new", "requested"):
                continue
            partner.write({"ocd_ambassador_state": "active", "ocd_ambassador_since": fields.Date.context_today(partner)})
            partner._ocd_ambassador_check_momo()
            partner._ocd_ambassador_opened()
        return True

    def _ocd_ambassador_opened(self):
        """The account just opened (extended by the WhatsApp module: the messages it agreed to)."""

    def _ocd_ambassador_other_momo(self):
        """Another ambassador (not closed) whose Mobile Money or number is this Mobile Money."""
        self.ensure_one()
        if not self.ocd_payout_momo:
            return self.browse()
        others = self.sudo().search([
            ("ocd_ambassador_state", "in", ("active", "to_check", "paused", "requested")), ("id", "!=", self.id),
        ])
        return others.filtered(lambda other: any(
            same_number(self.ocd_payout_momo, number) for number in (other.ocd_payout_momo, other.phone) if number
        ))[:1]

    def _ocd_ambassador_check_momo(self):
        """One Mobile Money per person: shared with another ambassador, the account goes to « To
        check » (its gains are kept, paid once the team accepts it)."""
        for partner in self.sudo():
            other = partner._ocd_ambassador_other_momo()
            if other and partner.ocd_ambassador_state == "active":
                partner.write({
                    "ocd_ambassador_state": "to_check",
                    "ocd_ambassador_note": self.env._("Their Mobile Money is the one of %s.", other.name),
                })

    def _ocd_ambassador_set_momo(self, number):
        """The ambassador changes their payout number: it waits the hours of the settings before a
        payout, the number of the account is told (if it is not them, they stop it)."""
        self.ensure_one()
        partner = self.sudo()
        if same_number(partner.ocd_payout_momo, number):
            return False
        old = partner.ocd_payout_momo
        partner.write({"ocd_payout_momo": number, "ocd_ambassador_momo_since": fields.Datetime.now()})
        partner.message_post(body=self.env._("New payout number: %(new)s (was %(old)s).", new=number, old=old or "-"))
        partner._ocd_ambassador_check_momo()
        partner._ocd_ambassador_momo_changed(old)
        return True

    def _ocd_ambassador_momo_changed(self, old_number):
        """Extended by the WhatsApp module: the number of the account is told."""

    def _ocd_ambassador_tell_delivered(self, gains):
        """Tell the ambassador the parcels of `gains` delivered since the last message (extended by
        the WhatsApp module). Return whether it was told."""
        return False

    def _ocd_ambassador_momo_wait_until(self):
        """Until when a new payout number waits (False: it does not)."""
        self.ensure_one()
        hours = (self.company_id or self.env.company).ocd_ambassador_momo_hold_hours
        if not self.ocd_ambassador_momo_since or not hours:
            return False
        until = self.ocd_ambassador_momo_since + timedelta(hours=hours)
        return until if until > fields.Datetime.now() else False

    # === WHAT HOLDS THE PAYOUT === #

    def _ocd_ambassador_payout_blocks(self):
        """Why the gains of this ambassador wait ([text]): never a payout to a paused account, to
        an account to check, without a Mobile Money, on a new number, or above the gains of the
        settings without an identity seen."""
        self.ensure_one()
        _ = self.env._
        company = self.company_id or self.env.company
        blocks = []
        if self.ocd_ambassador_state == "paused":
            blocks.append(_("Your account is paused: the team calls you."))
        elif self.ocd_ambassador_state == "to_check":
            blocks.append(_("Your account is checked by the team before the payout."))
        elif self.ocd_ambassador_state not in ("active", "closed"):
            blocks.append(_("Your account is not open yet."))
        if not self.ocd_payout_momo:
            blocks.append(_("Give your Mobile Money number."))
        wait = self._ocd_ambassador_momo_wait_until()
        if wait:
            blocks.append(_("Your new number waits until %s.", fields.Datetime.context_timestamp(self, wait).strftime(
                "%d/%m %H:%M")))
        if company.ocd_ambassador_id_above and not self.ocd_ambassador_id_checked \
                and company.currency_id.compare_amounts(self.ocd_ambassador_earned_total, company.ocd_ambassador_id_above) > 0:
            blocks.append(_("The team sees your identity document once before the payout."))
        return blocks

    # === RETURNS WATCHED === #

    def _ocd_ambassador_check_returns(self):
        """Above the rate of returns of the settings, on the last parcels (at least the number of
        the settings), the account pauses itself: its links still work, nothing is earned, the
        gains due are kept until the team decides."""
        Gain = self.env["ocd.ambassador.gain"].sudo()
        since = fields.Datetime.now() - timedelta(days=RETURN_WINDOW_DAYS)
        for partner in self.sudo().filtered(lambda p: p.ocd_ambassador_state in ("active", "to_check")):
            company = partner.company_id or self.env.company
            rate, minimum = company.ocd_ambassador_pause_rate, max(company.ocd_ambassador_pause_min, 1)
            if not rate:
                continue
            outcomes = Gain.search([
                ("ambassador_id", "=", partner.id), ("write_date", ">=", since), "|",
                ("delivered_at", "!=", False), ("bad_outcome", "=", True),
            ])
            bad = len(outcomes.filtered("bad_outcome"))
            if len(outcomes) >= minimum and bad * 100 >= rate * len(outcomes):
                partner.write({
                    "ocd_ambassador_state": "paused",
                    "ocd_ambassador_note": self.env._(
                        "%(bad)s parcels refused or returned on %(count)s: paused by itself.",
                        bad=bad, count=len(outcomes)),
                })
                partner.activity_schedule(
                    "mail.mail_activity_data_todo",
                    summary=self.env._("Ambassador paused: too many returns"),
                    note=partner.ocd_ambassador_note,
                    user_id=(company.ocd_live_responsible_id or self.env.user).id,
                )

    # === ACTIONS OF THE TEAM === #

    def _ocd_ambassador_check_team(self):
        if not self.env.user.has_group("ocd_live.group_ocd_live_user"):
            raise AccessError(self.env._("Only the team of OCD Live manages the ambassadors."))

    def action_ocd_ambassador_open(self):
        """Open an account asked (program on invitation), or accept an account to check."""
        self._ocd_ambassador_check_team()
        for partner in self.sudo():
            if partner.ocd_ambassador_state == "requested":
                partner._ocd_ambassador_open_account()
            elif partner.ocd_ambassador_state in ("to_check", "paused"):
                partner.write({"ocd_ambassador_state": "active", "ocd_ambassador_note": False})
            partner.message_post(body=self.env._("Account of ambassador opened by %s.", self.env.user.name))
        return True

    def action_ocd_ambassador_pause(self, note=None):
        self._ocd_ambassador_check_team()
        self.sudo().filtered(lambda p: p.ocd_ambassador_state in ("active", "to_check")).write({
            "ocd_ambassador_state": "paused",
            "ocd_ambassador_note": note or self.env._("Paused by the team."),
        })
        return True

    def action_ocd_ambassador_close(self, note=None):
        """Close the account: no new gain; the gains due are paid a last time."""
        self._ocd_ambassador_check_team()
        self.sudo().filtered("ocd_ambassador_state").write({
            "ocd_ambassador_state": "closed",
            "ocd_ambassador_note": note or self.env._("Closed by the team."),
        })
        return True

    def action_ocd_ambassador_id_checked(self):
        self._ocd_ambassador_check_team()
        self.sudo().write({"ocd_ambassador_id_checked": True})
        return True

    def action_ocd_ambassador_view_gains(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Gains of %s", self.name),
            "res_model": "ocd.ambassador.gain",
            "view_mode": "list,form",
            "domain": [("ambassador_id", "=", self.id)],
        }

    def action_ocd_ambassador_view_space(self):
        """Open the pages of the ambassador as they see them, in a new tab (help on the phone)."""
        self.ensure_one()
        self._ocd_ambassador_check_team()
        if self.ocd_ambassador_state not in SPACE_STATES:
            raise UserError(self.env._("The account of ambassador of %s is not open.", self.display_name))
        signature = self._ocd_team_view_signature(self.env.uid)
        return {"type": "ir.actions.act_url", "url": f"/ambassadeur/equipe/{self.id}?signature={signature}",
                "target": "new"}

    # === CRON === #

    @api.model
    def _cron_ocd_ambassadors_forget(self):
        """The accounts asked from the site whose number was never checked (7 days): removed, so
        that a number typed by someone else leaves nothing."""
        old = self.sudo().search([
            ("ocd_ambassador_state", "=", "new"), ("create_date", "<", fields.Datetime.now() - timedelta(days=7)),
            ("ocd_ambassador_gain_ids", "=", False),
        ])
        for partner in old:
            try:
                with self.env.cr.savepoint():
                    partner.unlink()
            except (UserError, IntegrityError):
                # A contact used elsewhere is kept, only closed
                partner.write({"ocd_ambassador_state": "closed", "ocd_ambassador_note": self.env._("Number never checked.")})
