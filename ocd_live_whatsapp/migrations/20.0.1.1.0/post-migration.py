from odoo import api, SUPERUSER_ID

from odoo.addons.ocd_live_whatsapp.hooks import align_whatsapp_consent


def migrate(cr, version):
    align_whatsapp_consent(api.Environment(cr, SUPERUSER_ID, {}))
