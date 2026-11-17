from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _whatsapp_add_rating(self, value, partner):
        """Override of `whatsapp_cloud_sale`: the rating given on WhatsApp is also the review of
        each vendor whose parcel was delivered (chantier 2), the words written before kept."""
        rating = super()._whatsapp_add_rating(value, partner)
        self._ocd_review_parcels(value, "whatsapp")
        return rating
