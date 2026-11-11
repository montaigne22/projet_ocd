from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Messages received before the types of messages: texts. Accounts created before the
    automatic answers: default texts and menu."""
    cr.execute("""
        UPDATE whatsapp_message
           SET message_type = 'text'
         WHERE direction = 'incoming' AND message_type = 'template'
    """)
    env = api.Environment(cr, SUPERUSER_ID, {})
    accounts = env["whatsapp.account"].with_context(active_test=False).search([])
    accounts._set_default_texts()
    accounts.filtered(lambda account: not account.bot_option_ids)._create_default_bot_options()
