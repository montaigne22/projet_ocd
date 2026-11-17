from odoo import http
from odoo.http import request


def watch_path(booking, source=""):
    """The address of « Watch » for a live booked at OCD Live: counted, then the live (chantier 3,
    « Opened from OCD » in the figures of the vendor)."""
    return f"/ocd/regarder/{booking.id}" + (f"?d={source}" if source else "")


class OcdWatch(http.Controller):
    """« Watch » of the cards of the feed, of the boutique and of the messages to the followers:
    the tap is counted for the vendor (« Opened from OCD »), then the live opens on its platform.
    Only the link of the live is ever opened, never an address given in the request."""

    @staticmethod
    def _external(url):
        return bool(url) and url.startswith(("https://", "http://"))

    @http.route("/ocd/regarder/<int:booking_id>", type="http", auth="public", website=True, sitemap=False)
    def watch_booking(self, booking_id, **kwargs):
        booking = request.env["ocd.live.booking"].sudo().browse(booking_id).exists()
        if not booking or booking.state not in ("confirmed", "done"):
            raise request.not_found()
        url = booking._ocd_watch_url()
        if not self._external(url):
            # No link to the platform: the boutique of the vendor (the product on screen)
            path = booking.partner_id._ocd_shop_path()
            if not path:
                raise request.not_found()
            return request.redirect(f"/{path}")
        request.env["ocd.vendor.count"]._ocd_add(booking.partner_id, "watch", booking.id)
        return request.redirect(url, local=False)

    @http.route("/ocd/regarder/annonce/<int:listing_id>", type="http", auth="public", website=True, sitemap=False)
    def watch_listing(self, listing_id, **kwargs):
        """A live of the directory (the link the vendor sent): counted for the vendor, on no live
        of OCD Live."""
        listing = request.env["ocd.directory.listing"].sudo().browse(listing_id).exists()
        if not listing or listing.state not in ("published", "ended") or not self._external(listing.url):
            raise request.not_found()
        request.env["ocd.vendor.count"]._ocd_add(listing.partner_id, "watch")
        return request.redirect(listing.url, local=False)
