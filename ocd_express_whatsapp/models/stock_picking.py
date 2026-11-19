from odoo import models

# The events of a parcel of OCD Express told to its sender
SENDER_EVENTS = {"delivered", "problem", "returned", "handed_back", "not_for_me", "refused", "claim", "not_taken"}


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _ocd_express_recipient_values(self, values):
        """Override of `ocd_express`: the customer agreed, through the sender, to the messages of
        OCD Express about their delivery."""
        values = super()._ocd_express_recipient_values(values)
        agreed = not values.get("ocd_express_optout")
        return dict(values, ocd_whatsapp_optin=agreed, whatsapp_opt_in=agreed, whatsapp_opt_out=not agreed)

    def _ocd_express_notify(self, event):
        super()._ocd_express_notify(event)
        Partner = self.env["res.partner"]
        for parcel in self:
            if event == "created" and not parcel.partner_id.ocd_express_optout:
                Partner._ocd_whatsapp_send("ocd_express_whatsapp.template_express_announced", parcel)
            elif event in SENDER_EVENTS:
                Partner._ocd_whatsapp_send("ocd_express_whatsapp.template_express_state", parcel)

    def _ocd_express_not_for_me(self):
        result = super()._ocd_express_not_for_me()
        # No message of OCD Live either goes to this number any more
        self.partner_id.sudo().whatsapp_opt_out = True
        return result

    def _ocd_send_code(self):
        """Override of `ocd_live_shop_whatsapp`: the customer of OCD Express receives their own
        message, with their page (the code is on it, never in the message)."""
        express = self.filtered("ocd_express")
        super(StockPicking, self - express)._ocd_send_code()
        # At a relay point: the customer is told when the relay point has counted the parcel
        for parcel in express.filtered(lambda p: not p.partner_id.ocd_express_optout and not p.ocd_relay_id):
            self.env["res.partner"]._ocd_whatsapp_send("ocd_express_whatsapp.template_express_on_the_way", parcel)

    def _ocd_relay_notify(self, event):
        """Override of `ocd_live_shop_whatsapp`: the customer of OCD Express hears about the relay
        point from the number of OCD Express, with their page."""
        express = self.filtered("ocd_express")
        super(StockPicking, self - express)._ocd_relay_notify(event)
        if event in ("relay_arrived", "relay_reminder"):
            for parcel in express.filtered(lambda p: not p.partner_id.ocd_express_optout):
                self.env["res.partner"]._ocd_whatsapp_send("ocd_express_whatsapp.template_express_relay", parcel)

    def _ocd_notify_customer(self, event):
        """Override of `ocd_live_shop_whatsapp`: nothing else goes to the customer of OCD Express."""
        express = self.filtered("ocd_express")
        return super(StockPicking, self - express)._ocd_notify_customer(event)
