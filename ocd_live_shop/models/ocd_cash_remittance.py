from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import format_amount


class OcdCashRemittance(models.Model):
    """Cash handed over by a courier at the end of the day, compared to what was collected."""

    _name = "ocd.cash.remittance"
    _description = "Cash Handed Over By A Courier"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True, default=lambda self: self.env._("New")
    )
    courier_id = fields.Many2one(
        comodel_name="res.partner",
        string="Courier",
        required=True,
        index=True,
        domain=[("ocd_is_courier", "=", True)],
    )
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    date = fields.Datetime(required=True, default=fields.Datetime.now)
    picking_ids = fields.One2many(
        comodel_name="stock.picking", inverse_name="ocd_remittance_id", string="Parcels"
    )
    amount_expected = fields.Monetary(string="Collected", compute="_compute_amounts", store=True)
    amount_received = fields.Monetary(string="Handed Over", tracking=True)
    difference = fields.Monetary(compute="_compute_amounts", store=True)
    state = fields.Selection(
        selection=[("draft", "To count"), ("done", "Counted")],
        required=True,
        default="draft",
        tracking=True,
    )
    note = fields.Text()
    shortfall = fields.Monetary(
        string="Missing", compute="_compute_shortfall", store=True,
        help="Cash missing once counted: a debt of the courier until it is settled.",
    )
    shortfall_settled = fields.Boolean(string="Missing Cash Settled", tracking=True, copy=False)
    shortfall_note = fields.Char(string="How It Was Settled", tracking=True, copy=False)

    @api.depends("picking_ids.ocd_cod_collected_amount", "amount_received")
    def _compute_amounts(self):
        for remittance in self:
            remittance.amount_expected = sum(remittance.picking_ids.mapped("ocd_cod_collected_amount"))
            remittance.difference = remittance.amount_received - remittance.amount_expected

    @api.depends("state", "difference")
    def _compute_shortfall(self):
        for remittance in self:
            missing = -remittance.difference if remittance.state == "done" else 0.0
            remittance.shortfall = max(remittance.currency_id.round(missing) if remittance.currency_id else missing, 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        default_name = self.env._("New")
        for vals in vals_list:
            if vals.get("name", default_name) == default_name:
                vals["name"] = self.env["ir.sequence"].next_by_code("ocd.cash.remittance") or default_name
        return super().create(vals_list)

    @api.model
    def _ocd_open_for(self, courier):
        """Return the remittance to count of `courier`, with the cash parcels not handed over."""
        parcels = self.env["stock.picking"].search([
            ("ocd_cod_collected_by_id", "=", courier.id),
            ("ocd_cod_state", "=", "collected"),
            ("ocd_cod_method", "=", "cash"),
            ("ocd_remittance_id", "=", False),
        ])
        remittance = self.search([("courier_id", "=", courier.id), ("state", "=", "draft")], limit=1)
        if not remittance:
            remittance = self.create({"courier_id": courier.id})
        parcels.write({"ocd_remittance_id": remittance.id})
        return remittance

    def action_done(self):
        for remittance in self:
            if remittance.state != "draft":
                continue
            if not remittance.picking_ids:
                raise UserError(self.env._("There is no cash to count for %s.", remittance.courier_id.name))
            remittance.picking_ids.write({"ocd_cod_state": "remitted"})
            remittance.state = "done"
            if not remittance.currency_id.is_zero(remittance.difference):
                remittance.message_post(
                    body=self.env._(
                        "Difference of %(amount)s between the cash collected and the cash handed over by %(courier)s.",
                        amount=remittance.difference,
                        courier=remittance.courier_id.name,
                    )
                )
            if remittance.currency_id.compare_amounts(remittance.shortfall, 0.0) > 0:
                # A missing amount is a debt of the courier, settled later by the manager
                remittance._ocd_alert_shortfall()
            remittance.picking_ids._ocd_cash_remitted()
        return True

    def _ocd_alert_shortfall(self):
        self.ensure_one()
        company = self.company_id
        user = company.ocd_live_responsible_id or self.env.ref("base.user_admin", raise_if_not_found=False)
        self.sudo().activity_schedule(
            "mail.mail_activity_data_todo",
            summary=self.env._("Cash missing: %s", self.courier_id.name),
            note=self.env._(
                "%(amount)s missing in the cash handed over by %(courier)s: a debt of the courier until it is settled.",
                amount=format_amount(self.env, self.shortfall, self.currency_id),
                courier=self.courier_id.name,
            ),
            user_id=user.id if user else self.env.uid,
        )

    def action_ocd_settle_shortfall(self):
        """The courier paid back the cash missing (or the manager withheld it)."""
        if not self.env.user.has_group("ocd_live.group_ocd_live_manager"):
            raise AccessError(self.env._("Only a manager can settle the cash missing of a courier."))
        for remittance in self.filtered(lambda r: r.shortfall and not r.shortfall_settled):
            remittance.shortfall_settled = True
            remittance.activity_feedback(["mail.mail_activity_data_todo"])
        return True
