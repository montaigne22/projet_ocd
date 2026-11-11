from odoo import models


class WhatsappTemplate(models.Model):
    _inherit = "whatsapp.template"

    def _get_skip_reason(self, account, partner, number):
        """Override of `whatsapp_cloud`: a message the contact asks for right now (login code,
        personal link, ticket, alert they registered for) goes even without the consent to the
        notifications: the request is the consent to this very message."""
        if self.env.context.get("ocd_whatsapp_requested") and account and account.require_opt_in:
            account = account.new({"require_opt_in": False}, origin=account)
        return super()._get_skip_reason(account, partner, number)
