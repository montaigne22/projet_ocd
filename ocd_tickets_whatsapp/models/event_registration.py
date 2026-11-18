from odoo import models

from odoo.addons.ocd_live import tools


class EventRegistration(models.Model):
    _inherit = "event.registration"

    def _ocd_whatsapp_tickets(self, xmlid):
        """One message per holder (the first ticket of each holder and each order), never after
        STOP; they asked for their tickets."""
        Partner = self.env["res.partner"]
        for registration in self.sudo().filtered(lambda registration: not registration.partner_id.whatsapp_opt_out):
            Partner._ocd_whatsapp_send(xmlid, registration, requested=True)

    def _ocd_tell_ready(self):
        """Override of `ocd_tickets`: the tickets are paid or given (ocd_billets_prets)."""
        super()._ocd_tell_ready()
        self._ocd_whatsapp_tickets("ocd_tickets_whatsapp.template_tickets_ready")

    def _ocd_tell_reminder(self):
        """Override of `ocd_tickets`: the reminder the day before (ocd_billets_rappel)."""
        super()._ocd_tell_reminder()
        self._ocd_whatsapp_tickets("ocd_tickets_whatsapp.template_tickets_reminder")

    def _ocd_tell_changed(self, change):
        """Override of `ocd_tickets`: the event cancelled (ocd_billets_annule) or moved
        (ocd_billets_deplace)."""
        super()._ocd_tell_changed(change)
        xmlid = {
            "cancelled": "ocd_tickets_whatsapp.template_tickets_cancelled",
            "moved": "ocd_tickets_whatsapp.template_tickets_moved",
        }.get(change)
        if xmlid:
            self._ocd_whatsapp_tickets(xmlid)

    # === VALUES OF THE MESSAGES === #

    def _ocd_whatsapp_path(self):
        """The end of the address of the button « My tickets »."""
        self.ensure_one()
        return self._ocd_holder_path().lstrip("/")

    def _ocd_whatsapp_refund_day(self):
        """The last day to ask for a refund after a move: « Wednesday 25 November »."""
        self.ensure_one()
        event = self.event_id
        until = event._ocd_refund_until()
        if not until:
            return ""
        return tools.day_text(self.env, event._ocd_local(until).date(), "EEEE d MMMM")
