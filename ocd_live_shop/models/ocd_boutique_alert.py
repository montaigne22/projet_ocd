import re

from odoo import api, fields, models
from odoo.exceptions import UserError


class OcdBoutiqueAlert(models.Model):
    """A visitor of a boutique who wants a WhatsApp message when the vendor is back from holiday
    ("Tell me when they are back"). The alerts of the next live ("Tell me on WhatsApp") became
    follows (ocd.vendor.follower, chantier 1): the ones of before stay for the history."""

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
    kind = fields.Selection(
        selection=[("live", "Next live"), ("back", "Back from holiday")],
        string="Told When",
        required=True,
        default="live",
        index=True,
    )
    booking_id = fields.Many2one(
        comodel_name="ocd.live.booking", string="Live", readonly=True, help="The live the contact was told about."
    )
    sent_at = fields.Datetime(readonly=True)

    _unique_waiting_kind = models.UniqueIndex(
        "(partner_id, vendor_id, kind) WHERE state = 'waiting'",
        "This contact is already told about this vendor.",
    )

    @api.model
    def _ocd_register(self, vendor, phone=None, partner=None, kind="back"):
        """Tell the contact of `phone` (or `partner`) when `vendor` is back from holiday. The next
        live: they follow the vendor (ocd.vendor.follower)."""
        Partner = self.env["res.partner"].sudo()
        if not partner:
            if len(re.sub(r"\D", "", phone or "")) < 8:
                raise UserError(self.env._("Type your WhatsApp number."))
            partner = Partner._ocd_find_vendor_by_phone(phone) or Partner.search([("phone", "=", phone)], limit=1)
            if not partner:
                partner = Partner.create({"name": phone, "phone": phone})
        # sudo: public page, the contact only gives a number
        existing = self.sudo().search([
            ("partner_id", "=", partner.id), ("vendor_id", "=", vendor.id), ("kind", "=", kind),
            ("state", "=", "waiting"),
        ], limit=1)
        return existing or self.sudo().create({"partner_id": partner.id, "vendor_id": vendor.id, "kind": kind})

    @api.model
    def _ocd_send_due(self):
        """Tell the followers of the vendors whose live just started (chantier 1: « Follow »
        replaced « Tell me on WhatsApp » of the next live; the scheduled task stays the same)."""
        self.env["ocd.vendor.follower"].sudo()._ocd_send_lives()

    @api.model
    def _ocd_send_vendors_back(self, vendors):
        """The vendors are back from holiday: tell the contacts who asked."""
        alerts = self.sudo().search([
            ("vendor_id", "in", vendors.ids), ("kind", "=", "back"), ("state", "=", "waiting"),
        ])
        for alert in alerts:
            alert._ocd_send_vendor_back()
        alerts.write({"state": "sent", "sent_at": fields.Datetime.now()})
        return alerts

    def _ocd_send_vendor_back(self):
        """Send the news that the vendor is back. Extended by ocd_live_shop_whatsapp."""
        return False

