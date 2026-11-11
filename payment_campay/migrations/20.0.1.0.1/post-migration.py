from datetime import timedelta

from odoo import SUPERUSER_ID, api
from odoo.tools import BinaryBytes
from odoo.tools.misc import file_open

# The former logo of the provider (the integrator's), as stored by Odoo.
OLD_LOGO_CHECKSUMS = {"5e589d5edf61122bba00676356ff3af78e9d56ba"}


def migrate(cr, version):
    """New logo of the provider (mobile money), unless it was replaced in the database:
    the provider record is "noupdate", its logo is not updated with the module."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    provider = env.ref("payment_campay.payment_provider_campay", raise_if_not_found=False)
    if not provider:
        return
    logo = env["ir.attachment"].sudo().search([
        ("res_model", "=", "payment.provider"),
        ("res_id", "=", provider.id),
        ("res_field", "=", "image_128"),
    ], limit=1)
    untouched = bool(logo) and logo.write_date - logo.create_date < timedelta(minutes=1)
    if logo.checksum in OLD_LOGO_CHECKSUMS or untouched:
        with file_open("payment_campay/static/description/icon.png", "rb") as icon:
            provider.image_128 = BinaryBytes(icon.read(), "icon.png")
