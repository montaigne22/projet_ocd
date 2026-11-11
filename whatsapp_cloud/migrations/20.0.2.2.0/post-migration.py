from odoo import SUPERUSER_ID, api

ACTIONS = {"stop", "start"}


def migrate(cr, version):
    """New actions of the welcome menu: their options, ready to be enabled on the accounts."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    for account in env["whatsapp.account"].with_context(active_test=False).search([]):
        missing = ACTIONS - set(account.bot_option_ids.mapped("action"))
        if missing:
            account._create_default_bot_options(actions=missing)
        account._ensure_lang_options()
