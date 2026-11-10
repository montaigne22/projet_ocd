from odoo import fields, models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    ocd_picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="OCD Parcel",
        copy=False,
        index="btree_not_null",
        readonly=True,
    )

    def _post_process(self):
        """Override of `payment` to mark the parcel as paid once the Mobile Money request sent
        at the door is confirmed by the provider."""
        super()._post_process()
        for transaction in self.filtered(lambda t: t.ocd_picking_id and t.state == "done"):
            picking = transaction.ocd_picking_id
            if picking.ocd_cod_state == "to_collect":
                picking._ocd_collect(
                    "momo_campay",
                    picking.ocd_courier_id,
                    reference=transaction.provider_reference or transaction.reference,
                )
