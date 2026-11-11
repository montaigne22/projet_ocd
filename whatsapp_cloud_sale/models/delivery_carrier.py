from odoo import fields, models
from odoo.exceptions import UserError


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    def _whatsapp_get_price(self):
        """Price of the delivery method announced on WhatsApp, before the free delivery:
        (price, minimum) where minimum is True when the price depends on the order (rules on
        the weight or the amount: the lowest one); (None, False) when only the order gives
        it (carriers with their own prices)."""
        self.ensure_one()
        carrier = self.sudo()
        if carrier.delivery_type == "fixed":
            price, minimum = carrier.fixed_price, False
        elif carrier.delivery_type == "in_store":
            price, minimum = carrier.product_id.list_price, False
        elif carrier.delivery_type == "base_on_rule":
            try:
                price = carrier._get_price_from_picking(0.0, 0.0, 0.0, 0.0)
            except UserError:
                prices = carrier.price_rule_ids.mapped("list_base_price")
                price = min(prices) if prices else None
            minimum = True
        else:
            return None, False
        if price is None:
            return None, False
        company = carrier.company_id or self.env.company
        price = carrier.product_id._get_tax_included_unit_price(
            company,
            company.currency_id,
            fields.Date.context_today(carrier),
            "sale",
            product_price_unit=carrier._apply_margins(price),
            product_currency=company.currency_id,
        )
        return company.currency_id.round(price), minimum
