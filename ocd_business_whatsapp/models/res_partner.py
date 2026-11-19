from odoo import models

from odoo.addons.ocd_live import tools

TEMPLATES = {
    "paid": "ocd_business_whatsapp.template_business_paid",
    "soon": "ocd_business_whatsapp.template_business_ending",
    "last_call": "ocd_business_whatsapp.template_business_ending",
    "ended": "ocd_business_whatsapp.template_business_ended",
    "launch": "ocd_business_whatsapp.template_business_launch",
}


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _ocd_business_tell(self, event):
        """Override of `ocd_business`: the vendor is told on WhatsApp."""
        super()._ocd_business_tell(event)
        if event in TEMPLATES:
            self._ocd_whatsapp_send(TEMPLATES[event], self)

    def _ocd_business_until_text(self, lang=None):
        """« mercredi 17 février »: the end of the formula, in `lang` when it is installed (the
        language of a WhatsApp template)."""
        self.ensure_one()
        if lang and lang != self.env.lang and self.env["res.lang"]._ocd_is_active(lang):
            return self.with_context(lang=lang)._ocd_business_until_text()
        if not self.ocd_business_until:
            return ""
        return tools.day_text(self.env, self.ocd_business_until, "EEEE d MMMM")

    def _ocd_business_launch_text(self, lang=None):
        """« 2 mois »: the months offered at the launch."""
        self.ensure_one()
        if lang and lang != self.env.lang and self.env["res.lang"]._ocd_is_active(lang):
            return self.with_context(lang=lang)._ocd_business_launch_text()
        months = (self.company_id or self.env.company).ocd_business_launch_months
        return self.env._("1 month") if months == 1 else self.env._("%s months", months)
