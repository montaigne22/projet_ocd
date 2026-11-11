from odoo import SUPERUSER_ID, api

from odoo.addons.ocd_live_whatsapp.hooks import archive_english_templates


def migrate(cr, version):
    """OCD Live writes in French: the English versions of the templates of the WhatsApp modules
    are archived."""
    archive_english_templates(api.Environment(cr, SUPERUSER_ID, {}))
