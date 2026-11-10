from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _ocd_whatsapp_send(self, xmlid, records, **context):
        """Queue the WhatsApp message of the template `xmlid` for `records`. Values that are
        not stored (a login code, a link) are given in `context` and read by the template
        with ctx.get(). Return whether a message was queued."""
        template = self.env.ref(xmlid, raise_if_not_found=False)
        if not template or not records:
            return False
        # sudo: the messages are sent by the system, also from the public pages
        return bool(template.sudo().with_context(**context)._send(records.sudo()))

    def _ocd_deliver_login_code(self, code):
        """Override of `ocd_live` to send the login code on WhatsApp."""
        return self._ocd_whatsapp_send("ocd_live_whatsapp.template_login_code", self, ocd_login_code=code)

    def _ocd_send_space_link(self):
        """Override of `ocd_live` to send the personal link on WhatsApp."""
        return self._ocd_whatsapp_send("ocd_live_whatsapp.template_space_link", self)

    def _ocd_send_access_link(self, url):
        """Override of `ocd_live` to send the link to choose a password on WhatsApp."""
        return self._ocd_whatsapp_send("ocd_live_whatsapp.template_access_link", self, ocd_access_url=url)
