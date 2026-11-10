{
    "name": "OCD Live: Demo Data",
    "summary": "Vendors, lives, directory links, shop orders and parcels to show OCD Live. "
    "Uninstall the module to remove them all.",
    "description": """
OCD Live demo data
==================

Everything needed to show OCD Live, in one module that can be removed:

- Vendors in Togo, Cameroon, Benin, Ivory Coast and Senegal, with their category,
  sale mode and delivery mode, customers and an OCD courier in Douala.
- Hosts of the remote lives, prices of the hours (Saturday evening +25 %,
  Monday morning -15 %).
- Lives: a paid live at the studio, a package with a live placed and one to
  place, a slot held during the payment, a past live with its replay and the
  products shown.
- Directory: passes and live links, online during the checking window.
- Shop: products of the vendors, two orders and their parcels at different
  steps.
- The Mobile Money checked by the team is enabled with example numbers.

The dates are set from the day of the installation. Uninstalling the module
cancels and removes all these records; the Mobile Money checked by the team is
archived again.
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
