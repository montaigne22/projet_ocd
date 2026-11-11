from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Every country of Africa and the best known of Europe, the Americas and Asia are offered
    in the forms (the 5 first countries of OCD Live before); the countries of the vendors
    already known stay offered."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["res.country"]._ocd_set_default_offered()
