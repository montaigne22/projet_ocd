from odoo import fields, models
from odoo.addons.ocd_live.models.ocd_automation import WEEK


class OcdAutomation(models.Model):
    """The runs of the automations of the shop over 7 days, from the parcels and the bills."""

    _inherit = "ocd.automation"

    def _ocd_parcels(self, domain):
        return self.env["stock.picking"].sudo().search([("ocd_is_parcel", "=", True), *domain])

    def _ocd_since(self):
        return fields.Datetime.now() - WEEK

    def _ocd_runs_parcel_split(self):
        parcels = self._ocd_parcels([("create_date", ">=", self._ocd_since())])
        return self._ocd_runs_of(parcels, "create_date", lambda parcel: f"{parcel.name}, {parcel.ocd_vendor_id.name or ''}".strip(", "))

    def _ocd_runs_code_sent(self):
        parcels = self._ocd_parcels([("ocd_code_sent_at", ">=", self._ocd_since())])
        return self._ocd_runs_of(parcels, "ocd_code_sent_at", lambda parcel: parcel.name)

    def _ocd_runs_code_locked(self):
        parcels = self._ocd_parcels([("ocd_code_locked", "=", True), ("write_date", ">=", self._ocd_since())])
        return self._ocd_runs_of(parcels, "write_date", lambda parcel: parcel.name)

    def _ocd_runs_failed_return(self):
        parcels = self._ocd_parcels([("ocd_stage", "=", "returned"), ("write_date", ">=", self._ocd_since())])
        return self._ocd_runs_of(parcels, "write_date", lambda parcel: parcel.name)

    def _ocd_runs_vendor_share(self):
        bills = self.env["account.move"].sudo().search([
            ("move_type", "in", ("in_invoice", "in_refund")),
            ("ocd_picking_id", "!=", False),
            ("create_date", ">=", self._ocd_since()),
        ])
        return self._ocd_runs_of(bills, "create_date", lambda bill: bill.partner_id.name or "")

    def _ocd_runs_delivered_message(self):
        parcels = self._ocd_parcels([("ocd_delivered_at", ">=", self._ocd_since())])
        return self._ocd_runs_of(parcels, "ocd_delivered_at", lambda parcel: parcel.name)
