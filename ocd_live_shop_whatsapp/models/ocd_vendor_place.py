from odoo import models


class OcdVendorPlace(models.Model):
    _inherit = "ocd.vendor.place"

    def _ocd_relay_notify_incoming(self, parcels):
        """Override of `ocd_live_shop`: the relay point learns the parcels its courier brings."""
        super()._ocd_relay_notify_incoming(parcels)
        courier = parcels.ocd_courier_id[:1]
        self.env["res.partner"]._ocd_whatsapp_send(
            "ocd_live_shop_whatsapp.template_relay_incoming", self,
            ocd_relay_count=len(parcels), ocd_relay_courier=(courier.name or "").split(" ")[0] if courier else "",
        )
