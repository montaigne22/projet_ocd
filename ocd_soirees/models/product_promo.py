from odoo import api, fields, models


class OcdProductPromo(models.Model):
    """A promo of a big event: valid only during its hours, shown once the participation of the
    vendor is accepted."""

    _inherit = "ocd.product.promo"

    source = fields.Selection(selection_add=[("evening", "Big event")], ondelete={"evening": "cascade"})
    evening_id = fields.Many2one(comodel_name="ocd.evening", string="Big Event", index="btree_not_null",
                                 ondelete="cascade")
    participation_id = fields.Many2one(comodel_name="ocd.evening.participation", string="Participation",
                                       index="btree_not_null", ondelete="cascade")

    @api.model
    def _ocd_same_domain(self, values):
        """Override of `ocd_live_shop`: a promo of an event replaces the one of the same product in
        the same participation only."""
        domain = super()._ocd_same_domain(values)
        if values.get("participation_id"):
            domain = [*domain, ("participation_id", "=", values["participation_id"])]
        return domain
