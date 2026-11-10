from datetime import timedelta

from odoo import api, fields, models


class OcdLiveBooking(models.Model):
    _inherit = "ocd.live.booking"

    ocd_reminder_sent = fields.Boolean(string="Reminder Sent", copy=False)

    def _ocd_confirm(self):
        """Override of `ocd_live` to send the confirmation of the live on WhatsApp."""
        confirmed = super()._ocd_confirm()
        if confirmed:
            self.env["res.partner"]._ocd_whatsapp_send("ocd_live_whatsapp.template_live_confirmed", confirmed)
        return confirmed

    @api.model
    def _cron_send_reminders(self):
        """Remind the vendors of their live: the evening before from 18:00 (time of the
        studio), or at least 12 hours before when the reminder could not go earlier."""
        now = fields.Datetime.now()
        bookings = self.search([
            ("state", "=", "confirmed"),
            ("ocd_reminder_sent", "=", False),
            ("start_datetime", ">", now),
            ("start_datetime", "<=", now + timedelta(hours=30)),
        ])
        to_remind = bookings.filtered(
            lambda b: (
                b.company_id._ocd_to_local(now).hour >= 18
                and b.company_id._ocd_to_local(b.start_datetime).date() == b.company_id._ocd_to_local(now).date() + timedelta(days=1)
            )
            or b.start_datetime - now <= timedelta(hours=12)
        )
        if to_remind:
            self.env["res.partner"]._ocd_whatsapp_send("ocd_live_whatsapp.template_live_reminder", to_remind)
            to_remind.ocd_reminder_sent = True
