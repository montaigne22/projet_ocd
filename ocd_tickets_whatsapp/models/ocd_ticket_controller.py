from odoo import models


class OcdTicketController(models.Model):
    _inherit = "ocd.ticket.controller"

    def _ocd_tell_added(self):
        """Override of `ocd_tickets`: the organiser added them (ocd_billets_controleur)."""
        super()._ocd_tell_added()
        Partner = self.env["res.partner"]
        for control in self.sudo().filtered(lambda control: control.active and not control.partner_id.whatsapp_opt_out):
            Partner._ocd_whatsapp_send("ocd_tickets_whatsapp.template_tickets_controller", control, requested=True)

    def _ocd_whatsapp_organizer(self):
        self.ensure_one()
        return self.event_id.ocd_organizer_id.name or "OCD Live"
