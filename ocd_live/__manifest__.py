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
- Payment page with the standard payment form: it offers the providers that
  take the country, the currency and the amount of the order, as configured by
  the team (Campay in Cameroon today, Mobile Money checked by the team
  elsewhere, any connector added later). The prices come from the pricelist
  of the country of the vendor. The booking is confirmed when the payment
  confirms the order, never by the browser.
- A host (employee) for each remote live, with a reminder when none is chosen.
- The team is notified in the "Lives" channel for every confirmed booking.
- Live directory: the vendor sends the link of the live, the team checks it
  during the checking windows (8:00 to 11:00 and 18:00 to 21:00 by default),
  links are published by country and category and removed at the end of the
  window. A prepaid pass of 30 days (5,000 F) is required to send links.
- Personal link without password for each vendor (sent on WhatsApp by
  ocd_live_whatsapp) to reach their space.
""",
    "version": "20.0.1.1.0",
    "category": "Sales/Sales",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["sale", "website", "hr", "payment_custom"],
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
        "data/ocd_live_dashboard_data.xml",
        "data/ocd_automation_data.xml",
        "data/payment_provider_data.xml",
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
        "views/ocd_live_price_rule_views.xml",
        "views/res_config_settings_views.xml",
        "views/webclient_templates.xml",
        "views/ocd_booking_templates.xml",
        "views/ocd_directory_templates.xml",
        "views/ocd_space_templates.xml",
        "views/website_templates.xml",
        "wizard/ocd_directory_listing_refuse_views.xml",
        "views/ocd_live_menus.xml",
        "views/ir_cron_views.xml",
    ],
    "assets": {
        # The colours of OCD Live, read by the website and by the back office
        "web._assets_primary_variables": [
            ("prepend", "ocd_live/static/src/scss/ocd_tokens.scss"),
            ("after", "ocd_live/static/src/scss/ocd_tokens.scss", "ocd_live/static/src/backend/primary_variables.scss"),
        ],
        "web.assets_backend": [
            "ocd_live/static/src/dashboard/*",
            "ocd_live/static/src/planning/*",
            "ocd_live/static/src/verification/*",
            "ocd_live/static/src/settings/*",
            "ocd_live/static/src/automations/*",
            "ocd_live/static/src/backend/navbar.js",
            "ocd_live/static/src/backend/navbar.xml",
            "ocd_live/static/src/backend/theme.scss",
            "ocd_live/static/src/backend/choice_cards/*",
        ],
        "web.assets_frontend": [
            "ocd_live/static/src/scss/ocd_app.scss",
            "ocd_live/static/src/interactions/*.js",
        ],
    },
    "installable": True,
    "application": True,
    "post_init_hook": "post_init_hook",
}
