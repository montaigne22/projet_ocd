from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """The permissions to call given when the customer called, shown "This message has been
    deleted" before 20.0.1.6.0, become the notice of the permission."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["discuss.channel"]._whatsapp_call_permission_repair()
