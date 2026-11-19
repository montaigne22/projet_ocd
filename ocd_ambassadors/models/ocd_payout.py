from odoo import api, models


class OcdPayout(models.Model):
    """The gains of the ambassadors are paid with the payouts of the shop, every week: never a
    balance below zero, nor below the minimum of the ambassadors, nor to an account paused or to
    check, nor on a new number before its hours, nor above the gains of the settings without an
    identity seen."""

    _inherit = "ocd.payout"

    @api.model
    def _ocd_may_pay(self, vendor, net, company, force=False):
        if vendor.ocd_ambassador_state and not vendor.ocd_is_vendor and not force:
            currency = company.currency_id
            if currency.compare_amounts(net, 0.0) <= 0:
                return False
            if currency.compare_amounts(net, company.ocd_ambassador_min_payout) < 0:
                return False
            if vendor._ocd_ambassador_payout_blocks():
                return False
            return True
        return super()._ocd_may_pay(vendor, net, company, force=force)

    def _ocd_breakdown_bills(self):
        """The gains of an ambassador are no sales of a vendor."""
        return super()._ocd_breakdown_bills().filtered(lambda move: not move.ocd_ambassador_kind)

    def _ocd_after_paid(self):
        result = super()._ocd_after_paid()
        for payout in self.filtered(lambda p: p.move_ids.filtered("ocd_ambassador_kind")):
            payout._ocd_ambassador_paid()
        return result

    def _ocd_ambassador_paid(self):
        """The payout of an ambassador was made (extended by the WhatsApp module)."""
