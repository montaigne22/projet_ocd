{
    "name": "OCD Live: No WhatsApp To The Demo Contacts",
    "summary": "The vendors, customers and couriers of the demo have example numbers: no WhatsApp "
    "message is sent to them, even when a real WhatsApp account is connected.",
    "description": """
No WhatsApp message to the contacts of the demo
===============================================

The demo of OCD Live books lives, sells passes and moves parcels every day for its
vendors, customers and couriers, whose numbers are examples. When a real WhatsApp
account is connected (for example on a server used for presentations), the tickets,
reminders and parcel messages of these contacts would go to strangers.

This module, installed with the demo when WhatsApp is there, keeps every WhatsApp
template away from the contacts of the demo: no message is queued for them, and the
sending window of WhatsApp tells why. The other contacts are not concerned.

It is removed with the demo.
""",
    "version": "20.0.1.0.0",
    "category": "Hidden",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["ocd_live_demo", "whatsapp_cloud"],
    "auto_install": True,
    "installable": True,
}
