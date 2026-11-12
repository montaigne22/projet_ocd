{
    "name": "OCD Live: Demo Data",
    "summary": "Vendors in 8 countries, lives kept on the days around today, directory links, shop "
    "orders and parcels to show OCD Live. Uninstall the module to remove them all.",
    "description": """
OCD Live demo data
==================

Everything needed to present OCD Live, in one module that can be removed:

- 15 vendors in Togo, Cameroon, Ivory Coast, Senegal, Benin, Ghana, Nigeria and in
  Paris (the diaspora), each with a coherent story: their city, category, products
  with pictures, live link and hours; customers; three OCD couriers in Douala, one
  off duty.
- Lives kept current by a scheduled action, whatever the day of the presentation:
  the lives of the directory in the checking window of the moment (the dishes in the
  morning, phones and beauty at midday, home and fabrics in the afternoon, clothes in
  the evening; one link waits for the check of the team), the week of the studio in
  Lome (the vendors of Lome at the studio, the others from home with a host;
  Saturday full with a waiting list; a remote live without host), the replays of the
  last week with the products shown, a live held while the team checks a Mobile
  Money payment, a package with a live left to place.
- Two more checking windows (midday, afternoon): the directory has lives from 8:00 to
  21:00. The bookings have no opening date (the lives of the last week took place).
- The shop of Douala, kept current too: the orders of each day, each parcel along
  its story (paid cash or on the phone, a customer absent, a vendor late, a vendor
  who delivers herself), parcels at every step, the cash handed over by the couriers
  each evening, the payouts of the vendors prepared and paid every day; a dress in 2
  colours and 4 sizes whose stock stays at its level, delivery prices (OCD couriers,
  agencies, prices of a vendor).
- WhatsApp: the conversations of the day about the orders and the parcels, on an
  archived account; no WhatsApp message is ever sent to the contacts of the demo
  (ocd_live_demo_whatsapp).
- Payment: the Mobile Money checked by the team with example numbers, and the
  payment at the door.

Uninstalling the module cancels and removes all these records, and puts the payment
methods and the opening date of the bookings back as they were.
""",
    "version": "20.0.1.3.0",
    "category": "Hidden",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["ocd_live", "ocd_live_shop"],
    "data": [
        "security/ir.access.csv",
        "data/ocd_live_demo_data.xml",
        "data/ir_cron_data.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
}
