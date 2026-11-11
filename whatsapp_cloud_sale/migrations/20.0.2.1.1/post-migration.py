from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """The default options created by the migration of whatsapp_cloud (accounts created from
    their form) miss the "Track my order" option, which this module adds."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    for account in env["whatsapp.account"].with_context(active_test=False).search([]):
        if not account.bot_option_ids.filtered(lambda option: option.action == "order_status"):
            account._create_default_bot_options(actions={"order_status"})
