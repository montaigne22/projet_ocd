import re
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

SENDER_STATES = [
    ("requested", "Asked"),
    ("active", "Active"),
    ("suspended", "Suspended"),
    ("refused", "Refused"),
]
ACTIVITY_CHECK = "ocd_express.mail_activity_type_express_check"


def phone_digits(phone):
    return re.sub(r"\D", "", phone or "")


class ResPartner(models.Model):
    _inherit = "res.partner"

    # === SENDER === #

    ocd_express_state = fields.Selection(
        selection=SENDER_STATES, string="OCD Express", tracking=True, index="btree_not_null", copy=False,
    )
    ocd_express_social = fields.Char(string="Social Networks", help="Where they sell: Instagram, TikTok, WhatsApp…")
    ocd_express_since = fields.Date(string="Sender Since", copy=False)
    ocd_express_id_checked = fields.Boolean(
        string="Identity Checked", tracking=True, copy=False,
        help="The team saw an identity document: no daily limit of money to collect.",
    )
    ocd_express_place_checked = fields.Boolean(
        string="Pick-Up Place Checked", tracking=True, copy=False,
        help="A courier picked parcels up there: the place exists.",
    )
    ocd_express_momo_changed_at = fields.Datetime(string="Payout Number Changed At", copy=False, readonly=True)
    ocd_express_warned_at = fields.Datetime(string="Warned For The Returns At", copy=False, readonly=True)
    ocd_express_parcel_ids = fields.One2many(
        comodel_name="stock.picking", inverse_name="ocd_express_sender_id", string="Parcels Sent",
    )
    ocd_express_delivered_count = fields.Integer(string="Delivered", compute="_compute_ocd_express_figures")
    ocd_express_returned_count = fields.Integer(string="Returned", compute="_compute_ocd_express_figures")
    ocd_express_return_rate = fields.Float(
        string="Returned (30 Days, %)", compute="_compute_ocd_express_figures", digits=(5, 1),
    )
    ocd_express_claim_count = fields.Integer(string="Problems Open", compute="_compute_ocd_express_figures")
    ocd_express_balance = fields.Monetary(
        string="Balance Of The Sender", compute="_compute_ocd_express_balance", currency_field="currency_id",
        help="Money OCD owes the sender (positive) or the sender owes OCD (negative), not paid yet.",
    )
    ocd_express_max_cod = fields.Monetary(
        string="To Collect At Most", compute="_compute_ocd_express_max_cod", currency_field="currency_id",
    )

    # === CUSTOMER WHO RECEIVES === #

    ocd_express_recipient = fields.Boolean(string="Receives OCD Express Parcels", copy=False, index="btree_not_null")
    ocd_express_optout = fields.Boolean(
        string="No Message From OCD Express", copy=False,
        help="They said « Not for me » on a parcel: no message of OCD Express goes to this number any more.",
    )

    @api.depends("ocd_express_parcel_ids.ocd_stage", "ocd_express_parcel_ids.ocd_express_claim_state")
    def _compute_ocd_express_figures(self):
        Picking = self.env["stock.picking"].sudo()
        since = fields.Datetime.now() - timedelta(days=30)
        domain = [("ocd_express", "=", True), ("ocd_express_sender_id", "in", self.ids)]
        delivered = dict(Picking._read_group(
            domain + [("ocd_stage", "=", "delivered")], ["ocd_express_sender_id"], ["__count"]))
        returned = dict(Picking._read_group(
            domain + [("ocd_stage", "=", "returned")], ["ocd_express_sender_id"], ["__count"]))
        claims = dict(Picking._read_group(
            domain + [("ocd_express_claim_state", "=", "open")], ["ocd_express_sender_id"], ["__count"]))
        recent = domain + [("create_date", ">=", since), ("ocd_stage", "in", ("delivered", "returned"))]
        recent_all = dict(Picking._read_group(recent, ["ocd_express_sender_id"], ["__count"]))
        recent_returned = dict(Picking._read_group(
            recent + [("ocd_stage", "=", "returned")], ["ocd_express_sender_id"], ["__count"]))
        for partner in self:
            key = partner._origin or partner
            partner.ocd_express_delivered_count = delivered.get(key, 0)
            partner.ocd_express_returned_count = returned.get(key, 0)
            partner.ocd_express_claim_count = claims.get(key, 0)
            total = recent_all.get(key, 0)
            partner.ocd_express_return_rate = 100.0 * recent_returned.get(key, 0) / total if total else 0.0

    @api.depends("invoice_ids.amount_residual", "invoice_ids.state", "invoice_ids.payment_state")
    def _compute_ocd_express_balance(self):
        balances = dict.fromkeys(self.ids, 0.0)
        for partner_id, move_type, residual in self.env["account.move"].sudo()._read_group(
            [
                ("partner_id", "in", self.ids),
                ("ocd_express_kind", "!=", False),
                ("state", "=", "posted"),
                ("payment_state", "in", ("not_paid", "partial")),
            ],
            ["partner_id", "move_type"],
            ["amount_residual:sum"],
        ):
            sign = 1 if move_type == "in_invoice" else -1
            balances[partner_id.id] += sign * residual
        for partner in self:
            partner.ocd_express_balance = balances.get(partner.id, 0.0)

    def _compute_ocd_express_max_cod(self):
        for partner in self:
            company = partner.company_id or self.env.company
            confirmed = partner._ocd_express_confirmed_count() >= company.ocd_express_cap_after
            partner.ocd_express_max_cod = company.ocd_express_cap_confirmed if confirmed else company.ocd_express_cap_new

    def _ocd_express_confirmed_count(self):
        """Parcels delivered without a problem reported by the customer."""
        self.ensure_one()
        return self.env["stock.picking"].sudo().search_count([
            ("ocd_express", "=", True),
            ("ocd_express_sender_id", "=", self.id),
            ("ocd_stage", "=", "delivered"),
            ("ocd_express_claim_state", "in", (False, "sender_right")),
        ])

    def _ocd_express_debt(self):
        """What the sender owes OCD (0 when OCD owes them)."""
        self.ensure_one()
        return max(-self.ocd_express_balance, 0.0)

    def write(self, vals):
        if "ocd_payout_momo" in vals:
            # A new payout number of a sender: its first payout waits, the old number is told
            changed = self.filtered(
                lambda p: p.ocd_express_state and p.ocd_payout_momo
                and phone_digits(p.ocd_payout_momo) != phone_digits(vals["ocd_payout_momo"])
            )
            olds = {partner.id: partner.ocd_payout_momo for partner in changed}
            result = super().write(vals)
            if changed:
                super(ResPartner, changed).write({"ocd_express_momo_changed_at": fields.Datetime.now()})
                for partner in changed:
                    partner.message_post(body=self.env._(
                        "Payout number changed from %(old)s to %(new)s: the next payout waits.",
                        old=olds[partner.id], new=partner.ocd_payout_momo or "-",
                    ))
                    partner._ocd_express_notify_momo_changed(olds[partner.id])
            return result
        return super().write(vals)

    def _ocd_express_momo_held(self):
        """Whether the payouts of the sender wait after a new payout number."""
        self.ensure_one()
        hours = (self.company_id or self.env.company).ocd_express_momo_hold_hours
        changed = self.ocd_express_momo_changed_at
        return bool(hours and changed and changed > fields.Datetime.now() - timedelta(hours=hours))

    # === LOGIN === #

    @api.model
    def _ocd_find_express_sender_by_phone(self, phone):
        """The sender (active) whose number ends like `phone`, for the login page."""
        return self._ocd_find_by_phone(phone, [("ocd_express_state", "=", "active")])

    @api.model
    def _ocd_express_request(self, name, phone, country, district, landmark, social, vendor=None):
        """The request of a vendor to send parcels with OCD Express. Invited: the team opens the
        account; open to all: it is open at once (the number is checked by the code of the
        login). Return the sender."""
        company = self.env.company
        Partner = self.sudo()
        partner = vendor or Partner._ocd_find_by_phone(phone, [("ocd_express_state", "!=", False)]) \
            or Partner._ocd_find_vendor_by_phone(phone)
        state = "active" if company.ocd_express_open_to == "all" else "requested"
        vals = {
            "ocd_express_social": social or False,
            "district_id": district.id if district else False,
            "city_id": district.city_id.id if district else False,
            "delivery_landmark": landmark or False,
        }
        if partner:
            if partner.ocd_express_state in ("active", "suspended", "refused"):
                return partner
            # A request never changes what the contact already has (anyone may type a number)
            vals = {key: value for key, value in vals.items() if value and not partner[key]}
            partner.write(dict(vals, ocd_express_state=state))
        else:
            partner = Partner.create(dict(
                vals, name=name, phone=phone, country_id=country.id if country else False, ocd_express_state=state,
            ))
        if state == "active":
            partner.ocd_express_since = fields.Date.context_today(partner)
        else:
            partner._ocd_express_alert(
                self.env._("%(name)s asks to send parcels with OCD Express (%(social)s).",
                           name=partner.name, social=social or "-"))
        return partner

    # === THE TEAM === #

    def _ocd_express_check_manager(self):
        if not self.env.user.has_group("ocd_live.group_ocd_live_user"):
            raise AccessError(self.env._("Only the team of OCD Live opens the accounts of OCD Express."))

    def action_ocd_express_approve(self):
        """Open the account of the sender (or open it again after a suspension)."""
        self._ocd_express_check_manager()
        for partner in self:
            if not partner.phone:
                raise UserError(self.env._("%s has no WhatsApp number: add it first.", partner.name))
            first = partner.ocd_express_state != "suspended"
            partner.write({
                "ocd_express_state": "active",
                "ocd_express_since": partner.ocd_express_since or fields.Date.context_today(partner),
            })
            partner.activity_feedback([ACTIVITY_CHECK])
            if first:
                partner._ocd_express_notify_approved()
        return True

    def action_ocd_express_suspend(self):
        self._ocd_express_check_manager()
        self.filtered(lambda p: p.ocd_express_state == "active").write({"ocd_express_state": "suspended"})
        return True

    def action_ocd_express_refuse(self, reason=None):
        self._ocd_express_check_manager()
        for partner in self.filtered(lambda p: p.ocd_express_state == "requested"):
            partner.ocd_express_state = "refused"
            partner.activity_feedback([ACTIVITY_CHECK])
            if reason:
                partner.message_post(body=self.env._("Request of OCD Express refused: %s", reason.name))
        return True

    def action_ocd_express_view_parcels(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Parcels of %s", self.name),
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "views": [(self.env.ref("ocd_express.stock_picking_view_list_express").id, "list"), (False, "form")],
            "domain": [("ocd_express", "=", True), ("ocd_express_sender_id", "=", self.id)],
            "context": {"create": False},
        }

    def action_ocd_express_debt_paid(self, amount, reference):
        """The sender paid what they owe (Mobile Money to OCD, checked by the team or by the
        payment provider): a bill of the amount nets their credit notes."""
        self.ensure_one()
        company = self.company_id or self.env.company
        if company.currency_id.compare_amounts(amount, 0.0) <= 0:
            raise UserError(self.env._("Write the amount the sender paid."))
        if not (reference or "").strip():
            raise UserError(self.env._("Write the reference of the payment."))
        move = self.env["stock.picking"]._ocd_express_move(
            self, "in_invoice", "debt_paid", [("ocd_express.product_express_debt_paid", self.env._(
                "Paid by %(sender)s, reference %(ref)s", sender=self.name, ref=reference.strip()), amount)],
            ref=reference.strip(),
        )
        self.message_post(body=self.env._("Paid what they owed: %(amount)s, reference %(ref)s.",
                                          amount=amount, ref=reference.strip()))
        return move

    # === RETURNS === #

    def _ocd_express_check_returns(self):
        """A sender with too many returns on the last 30 days: a warning, then the suspension
        when it lasts a week after the warning."""
        for partner in self.filtered(lambda p: p.ocd_express_state == "active"):
            company = partner.company_id or self.env.company
            limit = company.ocd_express_return_alert
            if not limit:
                continue
            since = fields.Datetime.now() - timedelta(days=30)
            parcels = self.env["stock.picking"].sudo().search_count([
                ("ocd_express", "=", True), ("ocd_express_sender_id", "=", partner.id),
                ("create_date", ">=", since), ("ocd_stage", "in", ("delivered", "returned")),
            ])
            if parcels < 10 or partner.ocd_express_return_rate < limit:
                continue
            now = fields.Datetime.now()
            if not partner.ocd_express_warned_at or partner.ocd_express_warned_at < now - timedelta(days=30):
                partner.ocd_express_warned_at = now
                partner._ocd_express_alert(self.env._(
                    "%(sender)s: %(rate)s %% of their parcels came back in 30 days. They are warned.",
                    sender=partner.name, rate=round(partner.ocd_express_return_rate)))
                partner._ocd_express_notify_returns_warning()
            elif partner.ocd_express_warned_at < now - timedelta(days=7):
                partner.ocd_express_state = "suspended"
                partner._ocd_express_alert(self.env._(
                    "%(sender)s is suspended: still %(rate)s %% of returns a week after the warning.",
                    sender=partner.name, rate=round(partner.ocd_express_return_rate)))

    def _ocd_express_alert(self, body):
        """Alert the team: an activity on the sender, a message in the deliveries channel."""
        self.ensure_one()
        company = self.company_id or self.env.company
        channel = company.ocd_deliveries_channel_id
        if channel:
            channel.sudo().message_post(body=body, message_type="comment", subtype_xmlid="mail.mt_comment")
        user = company.ocd_live_responsible_id or self.env.ref("base.user_admin", raise_if_not_found=False)
        self.sudo().activity_schedule(ACTIVITY_CHECK, note=body, user_id=user.id if user else self.env.uid)

    # === NOTIFICATIONS (extended by ocd_express_whatsapp) === #

    def _ocd_express_notify_approved(self):
        """Tell the sender their account is open."""

    def _ocd_express_notify_momo_changed(self, old_number):
        """Tell the old payout number that the number changed."""

    def _ocd_express_notify_returns_warning(self):
        """Warn the sender about their returns."""


class OcdExpressDebtWizard(models.TransientModel):
    """The team notes what a sender paid of what they owed (Mobile Money to OCD)."""

    _name = "ocd.express.debt.wizard"
    _description = "OCD Express: Paid By The Sender"

    partner_id = fields.Many2one(comodel_name="res.partner", required=True, readonly=True)
    currency_id = fields.Many2one(comodel_name="res.currency", default=lambda self: self.env.company.currency_id)
    amount = fields.Monetary(required=True, default=lambda self: self._default_amount())
    reference = fields.Char(required=True)

    def _default_amount(self):
        partner = self.env["res.partner"].browse(self.env.context.get("default_partner_id")).exists()
        return partner._ocd_express_debt() if partner else 0.0

    def action_confirm(self):
        self.ensure_one()
        if not self.env.user.has_group("ocd_live.group_ocd_live_manager"):
            raise AccessError(self.env._("Only a manager of OCD Live settles the money of OCD Express."))
        self.partner_id.action_ocd_express_debt_paid(self.amount, self.reference)
        return {"type": "ir.actions.act_window_close"}
