{
    "name": "OCD Express: Deliveries For The Vendors Of The Social Networks",
    "summary": "The delivery with a code and the payment at the door of OCD Live, for any vendor of "
    "WhatsApp, TikTok or Instagram: parcels without an order, pick-ups, money paid the next "
    "working day, returns, problems reported, tracking page for the customer",
    "description": """
OCD Express
===========

- A sender (any vendor with a WhatsApp number, even without a shop on OCD Live)
  logs in with their number and a code on WhatsApp. First invited by the team,
  then open to all (setting).
- « New parcel »: the customer (name, WhatsApp, district, landmark) and their
  consent to the messages, the content, the money to collect or the value of a
  parcel already paid, who pays the delivery, opening before paying, pick-up at
  the sender or drop-off at the OCD point. The price is the rate « OCD courier »
  of the city; collecting at the door costs a share (1.5 %, 150 F at least).
- Two waves (created before 10 h: delivered in the afternoon; before 15 h: the
  next morning), the capacity of the couriers, a pick-up passage for all the
  parcels of a sender (free from 3 parcels).
- The courier picks up (photo of the parcels closed), delivers against the
  money and the code (no Mobile Money « declared »), gives a return back against
  the return code of the sender. Cash capped on a courier.
- The money of the sender: paid the next working day, once it reached OCD (cash
  counted at the cash desk, or the payment confirmed by the provider), minus
  the fees; what the sender owes is withheld, capped; a problem reported by the
  customer within 48 h holds the money of the parcel; a new payout number waits
  48 h. Never an advance.
- Caps per parcel, team checks, return rate alert, data of the customers erased
  after 6 months.
""",
    "version": "20.0.1.2.0",
    "category": "Inventory/Delivery",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["ocd_live_shop"],
    "data": [
        "security/ir.access.csv",
        "data/product_data.xml",
        "data/ir_sequence_data.xml",
        "data/stock_data.xml",
        "data/ir_cron_data.xml",
        "data/ocd_automation_data.xml",
        "data/ocd_refuse_reason_data.xml",
        "views/stock_picking_views.xml",
        "views/res_partner_views.xml",
        "views/res_company_views.xml",
        "views/ocd_express_pickup_views.xml",
        "views/ocd_express_menus.xml",
        "views/ocd_express_templates.xml",
        "views/ocd_express_sender_templates.xml",
        "views/ocd_express_tracking_templates.xml",
        "views/ocd_express_courier_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "ocd_express/static/src/scss/ocd_express.scss",
            "ocd_express/static/src/interactions/*.js",
        ],
    },
    "installable": True,
    "application": False,
}
