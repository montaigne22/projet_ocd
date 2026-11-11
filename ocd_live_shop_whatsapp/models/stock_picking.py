from odoo import models

# Messages of whatsapp_cloud_sale (by name at Meta) and the parcels of OCD Live:
# - "order shipped" goes when a transfer is validated, i.e. when a parcel of OCD Live is
#   delivered, after "your parcel is delivered": not for the parcels;
# - the satisfaction message: once per order, after its last parcel.
REPLACED_FOR_PARCELS = ("order_shipped", "order_ready_for_pickup")
ONCE_PER_ORDER = ("delivery_feedback",)

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

    def _ocd_whatsapp_keep(self, template):
        """The transfers to which the message of `template` still goes."""
        if template.template_name in REPLACED_FOR_PARCELS:
            return self.filtered(lambda picking: not picking.ocd_is_parcel)
        if template.template_name in ONCE_PER_ORDER:
            return self.filtered(lambda picking: not picking.ocd_is_parcel or picking._ocd_is_last_parcel())
        return self

    def _ocd_is_last_parcel(self):
        """Whether every parcel of the order is over and this one was delivered last."""
        self.ensure_one()
        parcels = self.sale_id.picking_ids.filtered("ocd_is_parcel")
        if any(parcel.state not in ("done", "cancel") for parcel in parcels):
            return False
        done = parcels.filtered(lambda parcel: parcel.state == "done")
        last = max(done, key=lambda parcel: (parcel.date_done or parcel.write_date, parcel.id), default=None)
        return last == self
