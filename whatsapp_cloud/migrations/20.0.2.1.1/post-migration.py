from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    # Meta refuses a variable glued to the domain name ("not a valid URI"): {base_url}/{{1}}
    cr.execute("""
        UPDATE whatsapp_template_button
           SET url = replace(url, '{base_url}{{', '{base_url}/{{')
         WHERE url LIKE '{base_url}{{%'
    """)
    # accounts created from their form got no option in their welcome menu
    env = api.Environment(cr, SUPERUSER_ID, {})
    accounts = env["whatsapp.account"].with_context(active_test=False).search([])
    accounts.filtered(
        lambda account: not account.with_context(active_test=False).bot_option_ids
    )._create_default_bot_options()
