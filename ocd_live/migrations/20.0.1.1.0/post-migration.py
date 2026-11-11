from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    # Sites installed before: the home of OCD Live on /, French, logo and name of OCD Live.
    api.Environment(cr, SUPERUSER_ID, {})["website"]._ocd_setup_site()
