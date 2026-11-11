{
    "name": "OCD Live: WhatsApp Messages",
    "summary": "WhatsApp messages of OCD Live: personal link, login code, ticket, confirmed "
    "live, reminder the day before, free hour, pass that ends, directory links",
    "description": """
OCD Live on WhatsApp
====================

Sends the messages of OCD Live with the module whatsapp_cloud, through the
templates of this module (to create at Meta with the same names and texts):

- personal link of the vendor space, login code (6 digits, valid 10 minutes),
  link to choose a password;
- live confirmed after the payment, ticket sent again, reminder the day before;
- free hour of a full day, to the contacts of its waiting list;
- directory pass that ends in a few days;
- directory: link received (and when it is checked), opening of the checking window
  for the contacts who asked, link online, or refused with the reason.

One consent: the box of OCD Live (booking, vendor space, checkout) and the consent of
WhatsApp (also changed by STOP and START) are kept the same. The messages asked by the
contact (code, link, ticket, alert) go even without the consent to the notifications;
the others never go to a contact who refused.

The texts are editable in WhatsApp > Templates.
""",
    "version": "20.0.1.4.0",
    "category": "Marketing/WhatsApp",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["ocd_live", "whatsapp_cloud"],
    "data": [
        "security/ocd_live_whatsapp_security.xml",
        "data/whatsapp_template_data.xml",
        "data/ir_cron_data.xml",
        "data/ocd_automation_data.xml",
        "views/res_partner_views.xml",
        "views/ocd_live_whatsapp_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ocd_live_whatsapp/static/src/inbox/*",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
}
