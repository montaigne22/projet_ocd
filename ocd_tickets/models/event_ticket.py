from odoo import api, fields, models


class EventEventTicket(models.Model):
    """A kind of ticket of an event (Standard, VIP, Table of 6): its price, its seats, its live price.
    On OCD Tickets, each kind has its own product, so that the control room shows it like a
    product during a live."""

    _inherit = "event.event.ticket"

    ocd_live_price = fields.Float(
        string="Live Price", digits="Product Price",
        help="During the lives selling the tickets, until the end of the live only. 0: the usual price.",
    )

    def _ocd_ensure_product(self):
        """A product of its own for each kind of ticket of an event of OCD Tickets (not shown in the
        shop: the tickets are bought on the page of the event)."""
        default = self.env.ref("event_product.product_product_event", raise_if_not_found=False)
        category = self.env.ref("event_product.product_category_events", raise_if_not_found=False)
        for ticket in self.sudo():
            if ticket.product_id and ticket.product_id != default:
                if ticket.product_id.list_price != ticket.price:
                    ticket.product_id.list_price = ticket.price
                continue
            product = self.env["product.product"].sudo().create({
                "name": f"{ticket.name} · {ticket.event_id.name}",
                "type": "service",
                "service_tracking": "event",
                "list_price": ticket.price,
                "sale_ok": True,
                "purchase_ok": False,
                "taxes_id": [fields.Command.clear()],
                "categ_id": category.id if category else False,
                "company_id": ticket.event_id.company_id.id,
                "image_1920": ticket.event_id.ocd_poster or False,
            })
            ticket.product_id = product

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super().create(vals_list)
        tickets.filtered(lambda ticket: ticket.event_id.ocd_ticketing)._ocd_ensure_product()
        return tickets

    def write(self, vals):
        result = super().write(vals)
        if "price" in vals or "name" in vals:
            for ticket in self.sudo().filtered(lambda ticket: ticket.event_id.ocd_ticketing and ticket.product_id):
                ticket.product_id.write({"list_price": ticket.price,
                                         "name": f"{ticket.name} · {ticket.event_id.name}"})
        return result

    def _ocd_price(self, live=None):
        """The price of one ticket now: the live price during a live selling it, else the price."""
        self.ensure_one()
        live = self.event_id._ocd_live_now() if live is None else live
        if live and self.ocd_live_price and 0 < self.ocd_live_price < self.price:
            return self.ocd_live_price
        return self.price
