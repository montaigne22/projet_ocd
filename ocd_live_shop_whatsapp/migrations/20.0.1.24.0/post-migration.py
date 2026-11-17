"""Follow a vendor (chantier 1): the message « … is live now » goes to the followers now. Its
templates (kept by the database: noupdate) take the follower as their record and its link (the
button opens the boutique on the phone of the follower, known)."""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    model = env.ref("ocd_live_shop.model_ocd_vendor_follower")
    for xmlid in ("ocd_live_shop_whatsapp.template_vendor_live", "ocd_live_shop_whatsapp.template_vendor_live_en"):
        template = env.ref(xmlid, raise_if_not_found=False)
        if template:
            template.write({"model_id": model.id, "button_url_value": "{{ object._ocd_link_path() }}"})
