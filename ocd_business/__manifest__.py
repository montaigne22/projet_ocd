{
    "name": "OCD Live: OCD Business",
    "summary": "The monthly formula of the organised vendors: several stores and their stock, their team, "
    "their figures in detail, their news every week, OCD Express; paid in advance, never debited",
    "description": """
OCD Business
============

- The formula is a chain of periods: paid (one per paid line of an order, unique
  in the database), offered by the team (with a reason), offered at the launch.
  « Until » is read from them, never typed; a new period starts the day after
  the last one, or today when the formula ended: no day is lost. The vendor is
  locked while the dates are computed.
- Bought from the space of the vendor (1, 3 or 12 months, prices in the settings,
  in the currency of each country) with the payment of OCD Live; the duration and
  the price are the ones of the order. One invoice per payment.
- A Mobile Money checked by the team: « I paid » keeps the features 3 days after
  the end, the time of the check; checked, the days start at the end of the
  formula.
- A refund takes back the days not passed yet, never backwards; the periods
  after it come closer.
- Reminders 7 days before and the day before, at the hour of the vendor, once per
  date of end; the end told. Nothing is erased at the end: the store the parcels
  leave from stays shown, the team pauses, the detailed figures hide.
- The launch: the vendors who use the features receive the months of the
  settings once, before the features offered to all stop.
- « My space » › OCD Business, the line before and after the end, the way to the
  formula from each feature it keeps, the page /business, the back office.
""",
    "version": "20.0.1.1.0",
    "category": "Website/Website",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["ocd_live_shop"],
    "data": [
        "security/ir.access.csv",
        "data/product_data.xml",
        "data/ir_cron_data.xml",
        "data/ocd_automation_data.xml",
        "views/ocd_business_views.xml",
        "views/ocd_business_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "ocd_business/static/src/scss/ocd_business.scss",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
