{
    "name": "OCD Live: Demo Data",
    "summary": "Vendors, lives, directory links, shop orders and parcels to show OCD Live. "
    "Uninstall the module to remove them all.",
    "description": """
OCD Live demo data
==================

Everything needed to show OCD Live, in one module that can be removed:

- Vendors in Togo, Cameroon, Benin, Ivory Coast and Senegal, with their category,
  sale mode and delivery mode; customers; three OCD couriers in Douala, one off duty.
- Hosts of the remote lives, prices of the hours (Saturday evening +25 %,
  Monday morning -15 %).
- Lives: a paid live at the studio, a package with a live placed and one to
  place, a slot held during the payment, a past live with its replay and the
  products shown, a waiting list.
- Directory: passes and live links, online during the checking window.
- Shop: products with pictures, a dress in 2 colours and 4 sizes with its
  stock, delivery prices (OCD couriers, agencies, prices of a vendor), parcels at
  every step (to prepare, ready, on the way, delivered, problem, late), cash
  with a courier, bills of the vendors and payouts to check.
- WhatsApp: conversations of customers and vendors (waiting for an answer, a
  parcel on the way, a conversation older than 24 hours), on an archived account:
  nothing is sent to Meta.
- Payment: the Mobile Money checked by the team with example numbers, and the
  payment at the door.

The dates are set from the day of the installation. Uninstalling the module
cancels and removes all these records, and puts the payment methods back as
they were.
""",
    "version": "20.0.1.0.0",
    "category": "Hidden",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["ocd_live", "ocd_live_shop"],
    "data": [
        "data/ocd_live_demo_data.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
}
