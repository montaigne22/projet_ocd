{
    "name": "OCD Live: WhatsApp Messages Of The Parcels",
    "summary": "Parcel to prepare and reminder to the vendor, parcel on the way with its "
    "code, failed attempt, delivered or returned parcel to the customer",
    "version": "20.0.1.2.0",
    "category": "Marketing/WhatsApp",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["ocd_live_shop", "ocd_live_whatsapp"],
    "data": ["data/whatsapp_template_data.xml", "data/ocd_automation_data.xml"],
    "post_init_hook": "post_init_hook",
    "auto_install": True,
    "installable": True,
}
