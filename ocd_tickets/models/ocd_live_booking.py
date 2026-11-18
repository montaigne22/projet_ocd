from odoo import api, fields, models
from odoo.exceptions import UserError


class OcdLiveBooking(models.Model):
    """During a live selling the tickets of an event, the control room shows a kind of ticket like a
    product of the vendor; the boutique of the vendor then leads to the page of the event."""

    _inherit = "ocd.live.booking"

    ocd_ticket_event_ids = fields.Many2many(
        comodel_name="event.event", relation="event_event_ocd_live_booking_rel", column1="ocd_live_booking_id",
        column2="event_event_id", string="Events Whose Tickets Are Sold",
    )

    @api.depends("partner_id", "ocd_ticket_event_ids.event_ticket_ids.product_id")
    def _compute_vendor_product_ids(self):
        super()._compute_vendor_product_ids()
        for booking in self:
            tickets = booking._ocd_ticket_products()
            if tickets:
                booking.vendor_product_ids |= tickets

    def _ocd_ticket_products(self):
        """The products of the kinds of tickets of the events sold during this live, on sale."""
        self.ensure_one()
        events = self.sudo().ocd_ticket_event_ids.filtered(lambda event: event.ocd_state == "approved")
        return events.event_ticket_ids.product_id.product_tmpl_id

    def _ocd_show_product(self, product):
        if product in self._ocd_ticket_products():
            self.ensure_one()
            if self.state not in ("confirmed", "done"):
                raise UserError(self.env._("The live is not confirmed."))
            offset = max(int((fields.Datetime.now() - self.start_datetime).total_seconds()), 0)
            self.current_product_tmpl_id = product
            self.env["ocd.live.moment"].create({
                "booking_id": self.id,
                "product_tmpl_id": product.id,
                "offset_seconds": offset,
            })
            return
        return super()._ocd_show_product(product)
