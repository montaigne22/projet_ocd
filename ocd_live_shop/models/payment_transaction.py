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
        """Override of `payment` to mark the parcel as paid once the payment made on the phone
        of the customer at the door is confirmed by the provider."""
        super()._post_process()
        self._ocd_mark_parcels_paid()

    def _ocd_mark_parcels_paid(self):
        for transaction in self.filtered(lambda t: t.ocd_picking_id and t.state == "done"):
            picking = transaction.ocd_picking_id
            if picking.ocd_cod_state == "to_collect":
                picking._ocd_collect(
                    "online",
                    picking.ocd_courier_id,
                    reference=transaction.provider_reference or transaction.reference,
                )
