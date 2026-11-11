from odoo import models


class ResLang(models.Model):
    _inherit = "res.lang"

    def write(self, vals):
        activated = self.filtered(lambda lang: not lang.active) if vals.get("active") else self.browse()
        result = super().write(vals)
        if activated:
            # the WhatsApp customers can choose the new language in the welcome menu
            self.env["whatsapp.account"].sudo().with_context(active_test=False).search([])._ensure_lang_options()
        return result
