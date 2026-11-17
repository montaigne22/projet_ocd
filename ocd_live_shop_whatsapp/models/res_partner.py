from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _ocd_send_delivery_link(self, url):
        """Override of `ocd_live_shop` to send the link of the delivery app on WhatsApp (asked
        by the vendor or the courier, or sent by the team when they start)."""
        return self._ocd_whatsapp_send("ocd_live_shop_whatsapp.template_delivery_link", self, requested=True)

    @api.model
    def _ocd_link_templates(self):
        """Override of `ocd_live_whatsapp`: the link of the delivery app and the one of the
        people of a team, for their login pages."""
        return {
            **super()._ocd_link_templates(),
            "livrer": "ocd_live_shop_whatsapp.template_delivery_link",
            # The people of the team of a vendor (chantier 22)
            "magasin": "ocd_live_shop_whatsapp.template_team_link",
        }

    def _ocd_tell_week_summary(self, summary):
        """Override of `ocd_live_shop`: the summary of the week on WhatsApp (ocd_resume_semaine).
        The vendor asked for it in « My figures »; never after STOP."""
        super()._ocd_tell_week_summary(summary)
        Figures = self.env["ocd.vendor.figures"]
        for vendor in self:
            # Switching it on is the consent to this message: only STOP stops it
            if vendor.whatsapp_opt_out:
                continue
            french, english = (Figures._ocd_week_values(vendor, summary, lang) for lang in ("fr_FR", "en_US"))
            self._ocd_whatsapp_send(
                "ocd_live_shop_whatsapp.template_week_summary", vendor, requested=True,
                ocd_first_name=(vendor.name or "").split()[0] if vendor.name else "",
                ocd_week_pieces=summary["pieces"], ocd_week_visits=summary["visits"],
                ocd_week_amount_fr=french["amount"], ocd_week_amount_en=english["amount"],
                ocd_week_trend_fr=french["trend"], ocd_week_trend_en=english["trend"],
                ocd_week_best_fr=french["best"], ocd_week_best_en=english["best"],
            )
