from odoo.http import request

from odoo.addons.ocd_live_shop.controllers import shop_common
from odoo.addons.ocd_live_shop.controllers.boutique import OcdBoutique


class OcdTicketsBoutique(OcdBoutique):
    """A ticket on screen during a live (design OcdTickets): the boutique leads to the page of the
    event, at the live price."""

    def _product_card(self, product):
        ticket = request.env["event.event.ticket"].sudo().search([
            ("product_id.product_tmpl_id", "=", product.id), ("event_id.ocd_ticketing", "=", True),
        ], limit=1)
        if not ticket:
            return super()._product_card(product)
        event = ticket.event_id
        price = ticket._ocd_price()
        return {
            "product": product,
            "url": f"{event._ocd_public_path()}/acheter?q_{ticket.id}=1",
            "price": request.env._("%(price)s · price of the live", price=event._ocd_money(price))
            if price < ticket.price else event._ocd_money(price),
            "image": shop_common.image_url(product),
            "out": False,
            "low": False,
            "by": event._ocd_organizer_line(),
            "ocd": True,
            "mode": request.env._("Ticket of OCD Tickets"),
        }
