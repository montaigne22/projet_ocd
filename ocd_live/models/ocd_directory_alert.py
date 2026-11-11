import re

from odoo import api, fields, models
from odoo.exceptions import UserError


class OcdDirectoryAlert(models.Model):
    """A visitor who wants a WhatsApp message when the next checking window of the directory
    opens ("Tell me at 18:00")."""

    _name = "ocd.directory.alert"
    _description = "Alert At The Opening Of The Directory"
    _order = "window_start desc, id desc"
    _check_company_auto = True

    partner_id = fields.Many2one(comodel_name="res.partner", string="Contact", required=True, index=True)
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    window_start = fields.Datetime(string="Window Opens At", required=True, index=True)
    state = fields.Selection(
        selection=[("waiting", "Waiting"), ("sent", "Sent"), ("cancelled", "Cancelled")],
        required=True,
        default="waiting",
        index=True,
    )
    sent_at = fields.Datetime(readonly=True)

    _unique_waiting = models.UniqueIndex(
        "(partner_id, window_start) WHERE state = 'waiting'",
        "This contact is already told about this window.",
    )

    @api.model
    def _ocd_register(self, phone=None, partner=None):
        """Tell the contact of `phone` (or `partner`) when the next window opens."""
        Partner = self.env["res.partner"].sudo()
        if not partner:
            if len(re.sub(r"\D", "", phone or "")) < 8:
                raise UserError(self.env._("Type your WhatsApp number."))
            partner = Partner._ocd_find_vendor_by_phone(phone) or Partner.search([("phone", "=", phone)], limit=1)
            if not partner:
                partner = Partner.create({"name": phone, "phone": phone})
        found = self.env["ocd.directory.window"].sudo()._ocd_find(company=self.env.company)
        if not found:
            raise UserError(self.env._("The directory has no checking window."))
        start = found[1]
        # sudo: public page, the contact only gives a number
        existing = self.sudo().search(
            [("partner_id", "=", partner.id), ("window_start", "=", start), ("state", "=", "waiting")], limit=1
        )
        return existing or self.sudo().create({"partner_id": partner.id, "window_start": start})

    @api.model
    def _ocd_send_due(self):
        """Send the alerts of the windows that just opened."""
        due = self.search([("state", "=", "waiting"), ("window_start", "<=", fields.Datetime.now())])
        for alert in due:
            alert._ocd_send_window_open()
        due.write({"state": "sent", "sent_at": fields.Datetime.now()})

    def _ocd_send_window_open(self):
        """Send the news of the opening. Extended by ocd_live_whatsapp."""
        return False

    def _ocd_window_end_label(self):
        """End of the window that opened, in the time of the studio ("21:00")."""
        self.ensure_one()
        found = self.env["ocd.directory.window"].sudo()._ocd_find(moment=self.window_start, company=self.company_id)
        return self.company_id._ocd_to_local(found[2]).strftime("%H:%M") if found else ""
