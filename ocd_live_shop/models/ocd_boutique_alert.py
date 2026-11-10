import re

from odoo import api, fields, models
from odoo.exceptions import UserError


class OcdBoutiqueAlert(models.Model):
    """A visitor of a boutique who wants a WhatsApp message when the vendor goes live
    ("Tell me on WhatsApp")."""

    _name = "ocd.boutique.alert"
    _description = "Alert When A Vendor Goes Live"
    _order = "id desc"
    _check_company_auto = True

    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Contact", required=True, index=True, ondelete="cascade"
    )
    vendor_id = fields.Many2one(
        comodel_name="res.partner", string="Vendor", required=True, index=True, ondelete="cascade"
    )
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    state = fields.Selection(
        selection=[("waiting", "Waiting"), ("sent", "Sent"), ("cancelled", "Cancelled")],
        required=True,
        default="waiting",
        index=True,
    )
    booking_id = fields.Many2one(
        comodel_name="ocd.live.booking", string="Live", readonly=True, help="The live the contact was told about."
    )
    sent_at = fields.Datetime(readonly=True)

    _unique_waiting = models.UniqueIndex(
        "(partner_id, vendor_id) WHERE state = 'waiting'",
        "This contact is already told about the next live of this vendor.",
    )

    @api.model
    def _ocd_register(self, vendor, phone=None, partner=None):
        """Tell the contact of `phone` (or `partner`) when `vendor` goes live."""
        Partner = self.env["res.partner"].sudo()
        if not partner:
            if len(re.sub(r"\D", "", phone or "")) < 8:
                raise UserError(self.env._("Type your WhatsApp number."))
            partner = Partner._ocd_find_vendor_by_phone(phone) or Partner.search([("phone", "=", phone)], limit=1)
            if not partner:
                partner = Partner.create({"name": phone, "phone": phone})
        # sudo: public page, the contact only gives a number
        existing = self.sudo().search(
            [("partner_id", "=", partner.id), ("vendor_id", "=", vendor.id), ("state", "=", "waiting")], limit=1
        )
        return existing or self.sudo().create({"partner_id": partner.id, "vendor_id": vendor.id})

    @api.model
    def _ocd_send_due(self):
        """Send the alerts of the vendors whose live just started."""
        now = fields.Datetime.now()
        waiting = self.search([("state", "=", "waiting")])
        if not waiting:
            return
        lives = self.env["ocd.live.booking"].search([
            ("partner_id", "in", waiting.vendor_id.ids),
            ("state", "=", "confirmed"),
            ("start_datetime", "<=", now),
            ("end_datetime", ">", now),
        ])
        live_by_vendor = {live.partner_id: live for live in lives}
        for alert in waiting:
            live = live_by_vendor.get(alert.vendor_id)
            if live:
                alert._ocd_send_live_started(live)
                alert.write({"state": "sent", "sent_at": now, "booking_id": live.id})

    def _ocd_send_live_started(self, booking):
        """Send the news that the vendor is live. Extended by ocd_live_shop_whatsapp."""
        return False
