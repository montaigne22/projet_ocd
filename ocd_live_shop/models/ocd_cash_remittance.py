from odoo import api, fields, models
from odoo.exceptions import UserError


class OcdCashRemittance(models.Model):
    """Cash handed over by a courier at the end of the day, compared to what was collected."""

    _name = "ocd.cash.remittance"
    _description = "Cash Handed Over By A Courier"
    _inherit = ["mail.thread"]
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

    @api.depends("picking_ids.ocd_cod_collected_amount", "amount_received")
    def _compute_amounts(self):
        for remittance in self:
            remittance.amount_expected = sum(remittance.picking_ids.mapped("ocd_cod_collected_amount"))
            remittance.difference = remittance.amount_received - remittance.amount_expected

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
        return True
