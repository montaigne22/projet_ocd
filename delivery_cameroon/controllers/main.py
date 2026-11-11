from odoo import http
from odoo.http import request


class CameroonAddressController(http.Controller):

    @http.route(
        "/delivery_cameroon/districts",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        website=True,
        readonly=True,
    )
    def city_districts(self, city_id):
        """Return the districts of a city to fill the address forms."""
        city = request.env["res.city"].sudo().browse(int(city_id)).exists()
        return city._get_districts_data() if city else []
