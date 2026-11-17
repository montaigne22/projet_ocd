from odoo import models


class OcdVendorFollower(models.Model):
    """Follow a vendor (chantier 1): the WhatsApp at each live (the template of the lives, sent
    before to the visitors who asked « Tell me ») and the news of the vendor (A.8, Marketing at
    Meta). Following is the consent to them: a contact who answered STOP gets nothing."""

    _inherit = "ocd.vendor.follower"

    def _ocd_tell_live(self, live):
        super()._ocd_tell_live(live)
        return self.env["res.partner"]._ocd_whatsapp_send("ocd_live_shop_whatsapp.template_vendor_live", self)

    def _ocd_tell_news(self, products):
        super()._ocd_tell_news(products)
        return self.env["res.partner"]._ocd_whatsapp_send(
            "ocd_live_shop_whatsapp.template_vendor_news", self,
            ocd_news_fr=self._ocd_news_list(products, "fr_FR"),
            ocd_news_en=self._ocd_news_list(products, "en_US"),
        )


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _ocd_agree_by_following(self):
        """Override of `ocd_live_shop`: the consent of WhatsApp too (needed when the account asks
        for it), never after STOP."""
        for partner in self.sudo().filtered(lambda partner: not partner.whatsapp_opt_out):
            if not partner.ocd_whatsapp_optin or not partner.whatsapp_opt_in:
                partner.write({"ocd_whatsapp_optin": True, "whatsapp_opt_in": True})
