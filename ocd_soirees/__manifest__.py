{
    "name": "OCD Live: Big Evenings Of Several Vendors",
    "summary": "Big evenings of OCD Live (Black Friday, Christmas, Valentine's Day, Tabaski): the vendors "
    "of the countries invited do a live during the evening and put their promos of the evening",
    "description": """
Big evenings of OCD Live
========================

- The team creates an evening: its name, its day and its hours, its
  countries, its image, the discount at most, the end of the registrations.
- Opening the registrations invites the checked vendors of these countries
  (WhatsApp and their space). A vendor joins with a live during the evening
  (the usual booking) and their promos of the evening; the team checks each
  participation.
- The page of the evening: the countdown, the programme of the evening, the
  promos of the evening by category, « Tell me on WhatsApp ». The programme
  of the lives shows the evening on its day.
- The promos of the evening are the promo prices of the products, valid only
  during the hours of the evening; then the products take back their price
  (or the promo running before).
""",
    "version": "20.0.1.0.0",
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
