{
    "name": "OCD Live: WhatsApp Messages",
    "summary": "WhatsApp messages of OCD Live: personal link, login code, confirmed live, "
    "reminder the day before, pass that ends, directory link online or refused",
    "description": """
OCD Live on WhatsApp
====================

Sends the messages of OCD Live with the module whatsapp_cloud, through the
templates of this module (to create at Meta with the same names and texts):

- personal link of the vendor space, login code (6 digits, valid 10 minutes),
  link to choose a password;
- live confirmed after the payment, reminder the day before;
- directory pass that ends in a few days;
- directory link online, or refused with the reason.

The texts are editable in WhatsApp > Templates.
""",
    "version": "20.0.1.0.0",
    "category": "Marketing/WhatsApp",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["ocd_live", "whatsapp_cloud"],
    "data": [
        "data/whatsapp_template_data.xml",
        "data/ir_cron_data.xml",
    ],
    "installable": True,
}
