from odoo import api, models


class OcdPayout(models.Model):
    """The payouts of the senders of OCD Express, on the same screen as those of the vendors:
    every working day, the money that reached OCD minus the fees; the money of a parcel with a
    problem reported waits; a new payout number waits; what a sender owes waits for the money
    of their next parcels."""

    _inherit = "ocd.payout"

    @api.model
    def _ocd_prepare_domain(self):
        domain = super()._ocd_prepare_domain()
        # What a sender paid has no parcel
        domain = [term for term in domain if term != ("ocd_picking_id", "!=", False)]
        return ["|", ("ocd_picking_id", "!=", False), ("ocd_express_kind", "!=", False), *domain]

    @api.model
    def _ocd_is_due(self, vendor, day):
        if vendor.ocd_express_state:
            return (vendor.company_id or self.env.company)._ocd_express_working_day(day)
        return super()._ocd_is_due(vendor, day)

    @api.model
    def _ocd_payable_moves(self, vendor, moves, day, force=False):
        moves = super()._ocd_payable_moves(vendor, moves, day, force=force)
        if not vendor.ocd_express_state:
            return moves
        if not force and vendor._ocd_express_momo_held():
            return moves.browse()
        return moves.filtered(lambda move: move.ocd_picking_id.ocd_express_claim_state != "open")

    @api.model
    def _ocd_may_pay(self, vendor, net, company, force=False):
        if vendor.ocd_express_state and not force and company.currency_id.compare_amounts(net, 0.0) <= 0:
            return False
        return super()._ocd_may_pay(vendor, net, company, force=force)

    def _ocd_after_paid(self):
        super()._ocd_after_paid()
        if self.vendor_id.ocd_express_state:
            self._ocd_express_notify_paid()

    def _ocd_express_notify_paid(self):
        """Tell the sender their money left (extended by ocd_express_whatsapp)."""
