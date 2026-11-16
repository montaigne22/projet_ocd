from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """The stock per place (chantier 18): the places added before it get their location of stock,
    and the first place of each vendor receives the pieces they had in the stock of the shop."""
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    places = env["ocd.vendor.place"].search([("location_id", "=", False)], order="vendor_id, sequence, id")
    for vendor in places.vendor_id:
        stock_places = vendor._ocd_stock_places()
        main = vendor._ocd_main_stock_place()
        if main:
            main._ocd_take_stock(receive=True)
        for place in stock_places - main:
            place._ocd_location()
