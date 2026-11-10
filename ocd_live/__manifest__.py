{
    "name": "OCD Live: Bookings and Live Directory",
    "summary": "Book lives at the studio in Lome or remotely, packages and credits, "
    "hosts for remote lives, live directory with checked links and monthly pass",
    "description": """
OCD Live
========

- Live bookings at the studio in Lome or remotely: 1 h 30 slots on one shared
  calendar, no double booking (unique index on every reserved slot), slot held
  during the payment and released when the payment does not come.
- Six packages sold as products: the lives of a package become credits that
  the vendor places later. The 4-hour live takes consecutive slots.
- Payment through the Odoo payment page of the order (Campay in Cameroon, a
  payment confirmed by the team elsewhere): the booking is confirmed when the
  order is confirmed by the payment provider, never by the browser.
- A host (employee) for each remote live, with a reminder when none is chosen.
- The team is notified in the "Lives" channel for every confirmed booking.
- Live directory: the vendor sends the link of the live, the team checks it
  during the checking windows (8:00 to 11:00 and 18:00 to 21:00 by default),
  links are published by country and category and removed at the end of the
  window. A prepaid pass of 30 days (5,000 F) is required to send links.
- Personal link without password for each vendor (sent on WhatsApp by
  ocd_live_whatsapp) to reach their space.
""",
    "version": "20.0.1.0.0",
    "category": "Sales/Sales",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["sale", "website", "hr"],
    "data": [
        "security/ocd_live_security.xml",
        "security/ir.access.csv",
        "data/ir_sequence_data.xml",
        "data/ocd_live_category_data.xml",
        "data/ocd_directory_window_data.xml",
        "data/ocd_listing_refuse_reason_data.xml",
        "data/product_data.xml",
        "data/discuss_channel_data.xml",
        "data/ir_cron_data.xml",
        "data/ocd_voice_data.xml",
        "data/website_menu_data.xml",
        "views/ocd_live_booking_views.xml",
        "views/ocd_live_credit_views.xml",
        "views/ocd_directory_listing_views.xml",
        "views/ocd_directory_pass_views.xml",
        "views/ocd_directory_window_views.xml",
        "views/ocd_live_category_views.xml",
        "views/ocd_listing_refuse_reason_views.xml",
        "views/res_partner_views.xml",
        "views/hr_employee_views.xml",
        "views/product_template_views.xml",
        "views/ocd_voice_views.xml",
        "views/res_config_settings_views.xml",
        "views/ocd_live_templates.xml",
        "wizard/ocd_directory_listing_refuse_views.xml",
        "views/ocd_live_menus.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "ocd_live/static/src/scss/ocd_live.scss",
            "ocd_live/static/src/interactions/voice.js",
        ],
    },
    "installable": True,
    "application": True,
}
