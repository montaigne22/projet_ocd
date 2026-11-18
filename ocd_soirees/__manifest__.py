{
    "name": "OCD Live: Big Events Of Several Vendors",
    "summary": "Big events of OCD Live (Black Friday, Christmas, Valentine's Day, Tabaski), an evening or "
    "several days: the vendors of the countries invited do a live during the event and put their promos of the event",
    "description": """
Big events of OCD Live
======================

- The team creates an event: its name, an evening, a day or several days in
  a row (a setting caps the length), its countries, its image, the discount
  at most, the end of the registrations.
- Opening the registrations invites the checked vendors of these countries
  (WhatsApp and their space). A vendor joins with a live during the event
  (the usual booking) and their promos of the event; the team checks each
  participation.
- The page of the event: the countdown, its programme day by day, its
  promos by category, « Tell me on WhatsApp ». The programme of the lives
  shows the event on each of its days.
- The promos of the event are promo prices of the products, valid only
  during its hours, without a break; then the products take back their
  price (or the promo running before).
""",
    "version": "20.0.1.1.0",
    "category": "Website/Website",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["ocd_live_shop"],
    "data": [
        "security/ir.access.csv",
        "data/ocd_refuse_reason_data.xml",
        "data/ir_cron_data.xml",
        "data/ocd_automation_data.xml",
        "views/ocd_evening_views.xml",
        "views/ocd_soirees_menus.xml",
        "views/ocd_soirees_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "ocd_soirees/static/src/scss/ocd_soirees.scss",
        ],
    },
    "installable": True,
    "application": False,
}
