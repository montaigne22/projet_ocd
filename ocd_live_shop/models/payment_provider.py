from odoo import api, models

from odoo.addons.payment import utils as payment_utils


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    @api.model
    def _find_available_providers(self, company_id, partner_id, amount, *args, sale_order_id=None, report=None, **kwargs):
        """Override of `delivery`: with the delivery of OCD Live, the payment at the door is
        offered only when every parcel of the order allows it (never through a travel agency,
        nor towards another country)."""
        providers = super()._find_available_providers(
            company_id, partner_id, amount, *args, sale_order_id=sale_order_id, report=report, **kwargs
        )
        order = sale_order_id and self.env["sale.order"].sudo().browse(sale_order_id).exists()
        if order and order.carrier_id.delivery_type == "ocd" and not order._ocd_cod_allowed():
            cod = providers.filtered(lambda provider: provider.custom_mode == "cash_on_delivery")
            if cod:
                providers -= cod
                payment_utils.add_to_report(
                    report, cod, available=False,
                    reason=self.env._("A parcel of the order cannot be paid at the door"),
                )
        return providers
