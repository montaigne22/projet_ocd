from datetime import timedelta

from odoo import api, fields, models


class OcdLiveBooking(models.Model):
    _inherit = "ocd.live.booking"

    ocd_reminder_sent = fields.Boolean(string="Reminder Sent", copy=False)

    def _ocd_confirm(self):
        """Override of `ocd_live`: once paid, the ticket of the live goes on WhatsApp with its
        PDF. When the ticket cannot go (its template waits for Meta, or is paused by the
        team), the confirmation of the live goes instead: the vendor always knows."""
        confirmed = super()._ocd_confirm()
        Partner = self.env["res.partner"]
        for booking in confirmed:
            if not Partner._ocd_whatsapp_send("ocd_live_whatsapp.template_ticket", booking):
                Partner._ocd_whatsapp_send("ocd_live_whatsapp.template_live_confirmed", booking)
        return confirmed

    def _ocd_send_ticket(self):
        """Override of `ocd_live`: the vendor asked for the ticket on WhatsApp (ticket page)."""
        self.ensure_one()
        sent = self.env["res.partner"]._ocd_whatsapp_send("ocd_live_whatsapp.template_ticket", self, requested=True)
        return sent or super()._ocd_send_ticket()

    def _ocd_ticket_changed(self):
        """Override of `ocd_live`: the live moved, its former ticket is refused at the entry;
        the new one goes on WhatsApp."""
        sent = False
        for booking in self.filtered(lambda b: b.state == "confirmed"):
            sent = self.env["res.partner"]._ocd_whatsapp_send("ocd_live_whatsapp.template_ticket", booking) or sent
        return sent or super()._ocd_ticket_changed()

    @api.model
    def _cron_send_reminders(self):
        """Remind the vendors of their live: the evening before from 18:00 (in the time zone
        of the vendor), or at least 12 hours before when the reminder could not go earlier."""
        now = fields.Datetime.now()
        bookings = self.search([
            ("state", "=", "confirmed"),
            ("ocd_reminder_sent", "=", False),
            ("start_datetime", ">", now),
            ("start_datetime", "<=", now + timedelta(hours=40)),
        ])

        def evening_before(booking):
            vendor = booking.partner_id
            local_now = vendor._ocd_to_local(now)
            return local_now.hour >= 18 and vendor._ocd_to_local(booking.start_datetime).date() == local_now.date() + timedelta(days=1)

        to_remind = bookings.filtered(lambda b: evening_before(b) or b.start_datetime - now <= timedelta(hours=12))
        if to_remind:
            self.env["res.partner"]._ocd_whatsapp_send("ocd_live_whatsapp.template_live_reminder", to_remind)
            to_remind.ocd_reminder_sent = True
