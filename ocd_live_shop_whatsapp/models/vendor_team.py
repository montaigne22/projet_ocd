from odoo import models


class OcdVendorMember(models.Model):
    """The team of a vendor (chantier 22): her link on WhatsApp (asked by the vendor or on the
    page of the number: sent even without the consent to the notifications), then the news of her
    store when she agreed to them (« My store »)."""

    _inherit = "ocd.vendor.member"

    def _ocd_link_sent(self):
        super()._ocd_link_sent()
        return self.env["res.partner"]._ocd_whatsapp_send(
            "ocd_live_shop_whatsapp.template_team_link", self, requested=True
        )

    def _ocd_tell_parcel(self, parcel):
        super()._ocd_tell_parcel(parcel)
        customer = (parcel.partner_id.name or "").split()[0] if parcel.partner_id.name else "-"
        self.env["res.partner"]._ocd_whatsapp_send(
            "ocd_live_shop_whatsapp.template_team_parcel", self, ocd_customer=customer
        )

    def _ocd_tell_hold(self, hold):
        super()._ocd_tell_hold(hold)
        name = hold.partner_id.name or ""
        self.env["res.partner"]._ocd_whatsapp_send(
            "ocd_live_shop_whatsapp.template_team_hold", self,
            ocd_customer=name if name.startswith("+") else (name.split()[0] if name else "-"),
            ocd_product=hold.product_id.display_name,
            ocd_until_fr=hold._ocd_deadline_text("fr_FR"),
            ocd_until_en=hold._ocd_deadline_text("en_US"),
        )
