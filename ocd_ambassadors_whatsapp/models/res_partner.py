from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _ocd_ambassador_opened(self):
        """Override of `ocd_ambassadors`: the ambassador agreed, when signing up, to the messages of
        their gains and their payouts."""
        super()._ocd_ambassador_opened()
        self.sudo().write({"ocd_whatsapp_optin": True})

    def _ocd_ambassador_tell_delivered(self, gains):
        """Override of `ocd_ambassadors`: the parcels delivered since the last message, in one
        message (how many, how much, confirmed in how many days)."""
        self.ensure_one()
        _ = self.env._
        count = len(gains.picking_id)
        amount = sum(gains.mapped("amount"))
        currency = (self.company_id or self.env.company).currency_id
        xmlid = "ocd_ambassadors_whatsapp.template_ambassador_delivered"
        partner = self.with_context(lang=self._ocd_whatsapp_lang(xmlid, self))
        return partner._ocd_whatsapp_send(
            xmlid, self,
            ocd_amb_count=partner.env._("1 parcel") if count == 1 else partner.env._("%s parcels", count),
            ocd_amb_amount=self.env["ocd.live.dashboard"]._ocd_money(amount, currency),
            ocd_amb_days=str((self.company_id or self.env.company).ocd_ambassador_confirm_days),
        ) or super()._ocd_ambassador_tell_delivered(gains)

    def _ocd_ambassador_momo_changed(self, old_number):
        """Override of `ocd_ambassadors`: the WhatsApp number of the account is told the new payout
        number (if it is not them, they stop it before the payout)."""
        super()._ocd_ambassador_momo_changed(old_number)
        self._ocd_whatsapp_send("ocd_ambassadors_whatsapp.template_ambassador_number", self, requested=True)
