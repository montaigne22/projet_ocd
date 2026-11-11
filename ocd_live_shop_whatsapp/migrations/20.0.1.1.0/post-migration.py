from odoo import api, SUPERUSER_ID

from odoo.addons.ocd_live_shop_whatsapp.hooks import align_shop_consent


def migrate(cr, version):
    align_shop_consent(api.Environment(cr, SUPERUSER_ID, {}))
