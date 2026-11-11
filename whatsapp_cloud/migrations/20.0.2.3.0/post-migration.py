from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """New automatic answer: the invitation to write what the customer needs."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["whatsapp.account"].with_context(active_test=False).search([])._set_default_texts()
