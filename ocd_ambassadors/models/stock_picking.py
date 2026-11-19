from odoo import models


class StockPicking(models.Model):
    """The gains of the ambassadors follow their parcel: delivered with its code, or refused,
    returned, cancelled (whatever the way: the courier, the team, the relay point)."""

    _inherit = "stock.picking"

    def _ocd_deliver(self):
        result = super()._ocd_deliver()
        delivered = self.filtered(lambda p: p.ocd_is_parcel and p.ocd_stage == "delivered" and p.sale_id)
        if delivered:
            self.env["ocd.ambassador.gain"]._ocd_parcels_delivered(delivered)
        return result

    def write(self, vals):
        result = super().write(vals)
        stage = vals.get("ocd_stage")
        if stage in ("returned", "cancelled"):
            parcels = self.filtered(lambda p: p.ocd_is_parcel and p.sale_id)
            if parcels:
                self.env["ocd.ambassador.gain"]._ocd_parcels_failed(parcels, stage)
        return result
