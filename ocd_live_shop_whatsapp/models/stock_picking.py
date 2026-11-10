from odoo import models

EVENT_TEMPLATES = {
    "failed": "ocd_live_shop_whatsapp.template_parcel_failed",
    "delivered": "ocd_live_shop_whatsapp.template_parcel_delivered",
    "returned": "ocd_live_shop_whatsapp.template_parcel_returned",
}


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _ocd_send(self, xmlid):
        return self.env["res.partner"]._ocd_whatsapp_send(xmlid, self)

    def _ocd_notify_new_parcel(self):
        """Override of `ocd_live_shop`: the vendor prepares the parcel, except from the stock."""
        super()._ocd_notify_new_parcel()
        if self.ocd_vendor_id and self.ocd_delivery_mode in ("vendor", "pickup"):
            self._ocd_send("ocd_live_shop_whatsapp.template_parcel_to_prepare")

    def _ocd_send_code(self):
        """Override of `ocd_live_shop` to send the code of the parcel to the customer."""
        super()._ocd_send_code()
        self._ocd_send("ocd_live_shop_whatsapp.template_parcel_on_the_way")

    def _ocd_remind_vendor(self):
        """Override of `ocd_live_shop` to remind the vendor on WhatsApp."""
        super()._ocd_remind_vendor()
        self._ocd_send("ocd_live_shop_whatsapp.template_parcel_reminder")

    def _ocd_notify_customer(self, event):
        super()._ocd_notify_customer(event)
        if event in EVENT_TEMPLATES:
            self._ocd_send(EVENT_TEMPLATES[event])
