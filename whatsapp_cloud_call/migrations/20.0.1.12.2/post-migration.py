from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """The messages left before 20.0.1.12.2 were a file to download in the conversation, their
    line in the language of the customer: they become voice messages, played in the conversation,
    their line in the language of the team."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["whatsapp.call"]._voicemail_repair()
