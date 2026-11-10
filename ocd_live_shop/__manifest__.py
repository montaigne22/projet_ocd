{
    "name": "OCD Live: Shop, Parcels and Vendor Payouts",
    "summary": "Shop of the vendors: sale mode and delivery chosen by the team for each "
    "vendor, one parcel per vendor, delivery code, dispatch, cash of the couriers, "
    "vendor payouts, product shown during the live",
    "description": """
OCD Live shop and deliveries
============================

- For each vendor, the team chooses how the customers buy (direct contact on
  WhatsApp, or sold by OCD) and, when sold by OCD, who delivers: the vendor,
  an OCD courier who picks the parcel up at the vendor, or the OCD stock.
- An order gives one parcel per vendor (one transfer per vendor).
- Parcel steps: to prepare, ready, picked up, on the way, delivered or
  problem. The customer receives a 4-digit code when the parcel leaves: no
  parcel is delivered without it, 3 wrong codes lock the parcel, a manager can
  validate without code with a reason and a photo.
- A vendor who is not ready is reminded, then the dispatch is alerted and can
  give the parcel to an OCD courier. A customer outside the zones of the
  vendor gets an OCD courier.
- After the failed attempts allowed, the parcel goes back to the vendor.
- Payment at the door: the options are chosen by the team: cash, payment on
  the phone of the customer (the courier shows a QR code; the customer pays
  with the payment methods Odoo offers for the country, whatever the
  provider), Mobile Money declared by the courier and checked by the team.
- Cash of the couriers counted every evening.
- A vendor bill for the share of the vendor is created when the code is
  checked; a credit note when the vendor collected the money. The payouts
  are prepared at the rhythm chosen by the team for each vendor.
- Live control room: the product shown during the live, and the moments of
  the replay.
""",
    "version": "20.0.1.0.0",
    "category": "Website/eCommerce",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": [
        "ocd_live",
        "website_sale",
        "sale_stock",
        "delivery",
        "delivery_cameroon",
    ],
    "data": [
        "security/ocd_live_shop_security.xml",
        "security/ir.access.csv",
        "data/ir_sequence_data.xml",
        "data/product_data.xml",
        "data/discuss_channel_data.xml",
        "data/mail_activity_type_data.xml",
        "data/ir_cron_data.xml",
        "data/ocd_voice_data.xml",
        "data/ocd_refuse_reason_data.xml",
        "views/stock_picking_views.xml",
        "views/res_partner_views.xml",
        "views/product_template_views.xml",
        "views/ocd_payout_views.xml",
        "views/ocd_cash_remittance_views.xml",
        "views/ocd_live_booking_views.xml",
        "views/res_config_settings_views.xml",
        "wizard/ocd_parcel_problem_views.xml",
        "wizard/ocd_parcel_force_views.xml",
        "wizard/ocd_parcel_code_views.xml",
        "views/ocd_live_shop_templates.xml",
        "views/ocd_live_shop_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ocd_live_shop/static/src/regie/*",
            "ocd_live_shop/static/src/dispatch/*",
            "ocd_live_shop/static/src/orders/*",
            "ocd_live_shop/static/src/payouts/*",
            "ocd_live_shop/static/src/couriers/*",
        ],
        "web.assets_frontend": [
            "ocd_live_shop/static/src/scss/ocd_live_shop.scss",
            "ocd_live_shop/static/src/interactions/boutique_live.js",
        ],
    },
    "installable": True,
}
