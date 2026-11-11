from urllib.parse import quote

from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    whatsapp_number = fields.Char(
        string="WhatsApp Number",
        help="WhatsApp number of the shop, in international format (e.g. +237 6 99 00 00 00): "
        "used by the \"Order on WhatsApp\" button of the product pages and the WhatsApp links "
        "of the site. Empty: the number of the WhatsApp account, once checked at Meta.",
    )
    whatsapp_order_button = fields.Boolean(
        string="Order on WhatsApp",
        default=True,
        help="\"Order on WhatsApp\" button of the product pages: opens a conversation with the "
        "shop, with a message naming the product and the chosen options.",
    )
    whatsapp_checkout_consent = fields.Boolean(
        string="WhatsApp Consent at Checkout",
        default=True,
        help="\"Receive the follow-up of my orders on WhatsApp\" box of the checkout. The "
        "notifications are only sent to the customers who agreed.",
    )

    def _whatsapp_get_number(self):
        """Digits of the WhatsApp number of the shop, for the wa.me links."""
        self.ensure_one()
        number = self.whatsapp_number
        if not number:
            account = self.env["whatsapp.account"].sudo()._get_default_account(self.company_id)
            number = account.display_phone_number if account else ""
        return "".join(char for char in (number or "") if char.isdigit())

    def _whatsapp_get_link(self, text=None):
        """Link that opens a WhatsApp conversation with the shop, with a prefilled message."""
        self.ensure_one()
        number = self._whatsapp_get_number()
        if not number:
            return ""
        return f"https://wa.me/{number}" + (f"?text={quote(text)}" if text else "")
