from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class OcdPayout(models.Model):
    """Money paid back to a vendor sold by OCD for the parcels confirmed by the code of the
    customer, minus the money the vendor already collected at the door."""

    _name = "ocd.payout"
    _description = "Vendor Payout"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True, default=lambda self: self.env._("New")
    )
    vendor_id = fields.Many2one(
        comodel_name="res.partner", string="Vendor", required=True, index=True, tracking=True
    )
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    move_ids = fields.One2many(
        comodel_name="account.move", inverse_name="ocd_payout_id", string="Bills And Credit Notes"
    )
    amount_bills = fields.Monetary(string="Sales And Deliveries", compute="_compute_amounts", store=True)
    amount_refunds = fields.Monetary(string="Already Collected", compute="_compute_amounts", store=True)
    amount = fields.Monetary(string="Balance", compute="_compute_amounts", store=True, tracking=True)
    momo = fields.Char(related="vendor_id.ocd_payout_momo", string="Mobile Money")
    state = fields.Selection(
        selection=[
            ("draft", "To check"),
            ("validated", "To pay"),
            ("paid", "Paid"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="draft",
        tracking=True,
        index=True,
    )
    payment_ids = fields.Many2many(comodel_name="account.payment", string="Payments", copy=False, readonly=True)
    payment_reference = fields.Char(
        string="Transfer Reference",
        tracking=True,
        help="Reference of the Mobile Money transfer made from the account of OCD.",
    )

    @api.depends("move_ids.amount_total", "move_ids.move_type")
    def _compute_amounts(self):
        for payout in self:
            bills = sum(payout.move_ids.filtered(lambda m: m.move_type == "in_invoice").mapped("amount_total"))
            refunds = sum(payout.move_ids.filtered(lambda m: m.move_type == "in_refund").mapped("amount_total"))
            payout.amount_bills = bills
            payout.amount_refunds = refunds
            payout.amount = bills - refunds

    @api.model_create_multi
    def create(self, vals_list):
        default_name = self.env._("New")
        for vals in vals_list:
            if vals.get("name", default_name) == default_name:
                vals["name"] = self.env["ir.sequence"].next_by_code("ocd.payout") or default_name
        return super().create(vals_list)

    # === PREPARATION === #

    @api.model
    def _ocd_is_due(self, vendor, day):
        company = vendor.company_id or self.env.company
        frequency = vendor.ocd_payout_frequency or company.ocd_default_payout_frequency
        weekday = int(company.ocd_payout_weekday or 0)
        if frequency == "daily":
            return True
        if frequency == "weekly":
            return day.weekday() == weekday
        if frequency == "biweekly":
            return day.weekday() == weekday and day.isocalendar()[1] % 2 == 0
        if frequency == "monthly":
            return day.day == 1
        return False

    @api.model
    def _ocd_prepare(self, vendors=None, day=None, force=False):
        """Gather the posted and unpaid bills and credit notes of the parcels of each vendor
        whose payout is due on `day`, in one draft payout per vendor."""
        day = day or fields.Date.context_today(self)
        domain = [
            ("move_type", "in", ("in_invoice", "in_refund")),
            ("state", "=", "posted"),
            ("payment_state", "in", ("not_paid", "partial")),
            ("ocd_picking_id", "!=", False),
            ("ocd_payout_id", "=", False),
        ]
        if vendors is not None:
            domain.append(("partner_id", "in", vendors.ids))
        moves = self.env["account.move"].search(domain)
        payouts = self.browse()
        for vendor, vendor_moves in moves.grouped("partner_id").items():
            if not force and not self._ocd_is_due(vendor, day):
                continue
            company = vendor_moves[:1].company_id
            net = sum(
                m.amount_total if m.move_type == "in_invoice" else -m.amount_total for m in vendor_moves
            )
            if not force and company.currency_id.compare_amounts(abs(net), company.ocd_payout_min_amount) < 0:
                continue
            payout = self.create({"vendor_id": vendor.id, "company_id": company.id, "date": day})
            vendor_moves.write({"ocd_payout_id": payout.id})
            payouts |= payout
        return payouts

    @api.model
    def _cron_prepare(self):
        self._ocd_prepare()

    # === ACTIONS === #

    def _ocd_check_manager(self):
        if not self.env.user.has_group("ocd_live.group_ocd_live_manager"):
            raise AccessError(self.env._("Only a manager can validate or pay a payout."))

    def action_validate(self):
        self._ocd_check_manager()
        self.filtered(lambda p: p.state == "draft").write({"state": "validated"})
        return True

    def action_register_payment(self):
        """Register the transfer made to the vendor: the bills and credit notes are paid."""
        self._ocd_check_manager()
        for payout in self:
            if payout.state != "validated":
                raise UserError(self.env._("Validate the payout %s first.", payout.name))
            moves = payout.move_ids.filtered(lambda m: m.payment_state in ("not_paid", "partial"))
            if not moves:
                payout.state = "paid"
                continue
            journal = payout.company_id.ocd_payout_journal_id or self.env["account.journal"].search(
                [("type", "=", "bank"), ("company_id", "=", payout.company_id.id)], limit=1
            )
            if not journal:
                raise UserError(self.env._("Choose the journal of the payouts in the settings."))
            # sudo: the managers of OCD Live register the payment without being accountants
            wizard = self.env["account.payment.register"].sudo().with_context(
                active_model="account.move", active_ids=moves.ids
            ).create({
                "journal_id": journal.id,
                "payment_date": fields.Date.context_today(self),
                "group_payment": True,
                "communication": payout.payment_reference or payout.name,
            })
            payments = wizard._create_payments()
            payout.write({"state": "paid", "payment_ids": [fields.Command.set(payments.ids)]})
        return True

    def action_cancel(self):
        self._ocd_check_manager()
        for payout in self:
            if payout.state == "paid":
                raise UserError(self.env._("A paid payout cannot be cancelled."))
            payout.move_ids.write({"ocd_payout_id": False})
        self.write({"state": "cancelled"})
        return True
