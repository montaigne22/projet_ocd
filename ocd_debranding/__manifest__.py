{
    "name": "OCD Live: No Odoo Branding",
    "summary": "The team, the vendors and the customers see OCD Live, never Odoo: website, "
    "login, portal, back office, error messages, e-mails",
    "description": """
No Odoo branding
================

What the team, the vendors and the customers see says OCD Live, not Odoo:

- website, login page and customer portal: no "Powered by Odoo", no generator tag;
- back office: tab title and icon of OCD Live, no odoo.com link in the user menu, no
  "Apps" and "Updates" menus, no update notifier (module disable_odoo_online of the OCA,
  server-brand repository, required);
- error windows: "Server error", "Error in the page", "Connection lost", "Session
  expired", without Odoo;
- e-mails (notifications, digest): no "Powered by Odoo";
- the robot of the messages is named OCD Live, and it does not send its welcome chat
  that presents Odoo.

The addresses of the back office keep /odoo: the web client of Odoo builds them.
""",
    "version": "20.0.1.1.0",
    "category": "Hidden",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["web", "website", "portal", "mail", "mail_bot", "digest", "disable_odoo_online"],
    "data": [
        "views/web_templates.xml",
        "views/mail_templates.xml",
        "data/ocd_debranding_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ocd_debranding/static/src/error_dialogs.js",
            "ocd_debranding/static/src/error_dialogs.xml",
        ],
        "web.assets_frontend": [
            "ocd_debranding/static/src/error_dialogs.js",
            "ocd_debranding/static/src/error_dialogs.xml",
            "ocd_debranding/static/src/public/error_notifications.js",
        ],
    },
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
}
