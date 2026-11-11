import re

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_date


class OcdLiveWaitlist(models.Model):
    """A vendor who wants to know when an hour of a full day becomes free."""

    _name = "ocd.live.waitlist"
    _description = "Waiting List Of A Day"
    _order = "day, create_date, id"
    _check_company_auto = True

    partner_id = fields.Many2one(comodel_name="res.partner", string="Contact", required=True, index=True)
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    day = fields.Date(required=True, index=True)
    mode = fields.Selection(
        selection=[("studio", "At the studio in Lome"), ("remote", "Remote")], required=True, default="studio"
    )
    state = fields.Selection(
        selection=[("waiting", "Waiting"), ("notified", "Notified"), ("cancelled", "Cancelled")],
        required=True,
        default="waiting",
        index=True,
    )
    notified_at = fields.Datetime(readonly=True)

    _unique_waiting = models.UniqueIndex(
        "(partner_id, day, mode) WHERE state = 'waiting'",
        "This contact already waits for this day.",
    )

    @api.model
    def _ocd_register(self, phone, day, mode, partner=None):
        """Put the contact of `phone` (or `partner`) on the waiting list of `day`."""
        Partner = self.env["res.partner"].sudo()
        if not partner:
            digits = re.sub(r"\D", "", phone or "")
            if len(digits) < 8:
                raise UserError(self.env._("Type your WhatsApp number."))
            partner = Partner._ocd_find_vendor_by_phone(phone) or Partner.search([("phone", "=", phone)], limit=1)
            if not partner:
                partner = Partner.create({"name": phone, "phone": phone})
        existing = self.sudo().search(
            [("partner_id", "=", partner.id), ("day", "=", day), ("mode", "=", mode), ("state", "=", "waiting")],
            limit=1,
        )
        return existing or self.sudo().create({"partner_id": partner.id, "day": day, "mode": mode})

    @api.model
    def _ocd_notify_free(self, company, day, mode):
        """An hour of `day` became free: tell the contacts who wait for it."""
        modes = ("studio", "remote") if company.ocd_calendar_mode == "shared" else (mode,)
        waiting = self.sudo().search([
            ("company_id", "=", company.id),
            ("day", "=", day),
            ("mode", "in", modes),
            ("state", "=", "waiting"),
        ])
        if not waiting:
            return
        for entry in waiting:
            entry._ocd_send_free_slot()
        waiting.write({"state": "notified", "notified_at": fields.Datetime.now()})

    def _ocd_send_free_slot(self):
        """Send the news of the free hour. Extended by ocd_live_whatsapp."""
        return False

    def _ocd_day_label(self):
        """The day waited for, as in a message: "mercredi 2 décembre"."""
        self.ensure_one()
        return format_date(self.env, self.day, date_format="EEEE d MMMM")

    def _ocd_booking_path(self):
        """Path of the page of the day, to choose the free hour."""
        self.ensure_one()
        return f"reserver/{self.mode}/{self.day:%Y-%m-%d}"

    @api.model
    def _cron_clean(self):
        """Forget the waiting lists of the past days."""
        self.search([("state", "=", "waiting"), ("day", "<", fields.Date.context_today(self))]).write(
            {"state": "cancelled"}
        )
