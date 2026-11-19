from datetime import timedelta

from odoo import api, fields, models


class OcdVendorFigures(models.AbstractModel):
    """« Sold thanks to the ambassadors » in « My figures » of a vendor (design Ambassadeurs): how
    much, how many orders and ambassadors, the products they sold most. Never who they are (their
    name and number stay with OCD Live)."""

    _inherit = "ocd.vendor.figures"

    @api.model
    def _ocd_ambassador_figures(self, vendor, days, now=None):
        """The sales of the last `days` days whose order counted for an ambassador; False without."""
        vendor = vendor.sudo()
        if not vendor:
            return False
        now = now or fields.Datetime.now()
        lines = self._ocd_lines(vendor, now - timedelta(days=days), now).filtered(
            lambda line: line.order_id.ocd_ambassador_rate > 0)
        if not lines:
            return False
        _ = self.env._
        currency = self._ocd_currency(vendor)
        sums = self._ocd_sums(lines, currency)
        ambassadors = len(lines.order_id.ocd_ambassador_id)
        by_product = {}
        for line in lines:
            product = line.product_id.product_tmpl_id
            pieces, people = by_product.get(product, (0, set()))
            by_product[product] = (pieces + int(line.product_uom_qty), people | {line.order_id.ocd_ambassador_id.id})
        rows = []
        for product, (pieces, people) in sorted(by_product.items(), key=lambda item: (-item[1][0], item[0].name or ""))[:5]:
            rows.append({
                "name": product.name,
                "pieces": _("1 sold") if pieces == 1 else _("%s sold", pieces),
                "by": _("by 1 ambassador") if len(people) == 1 else _("by %s ambassadors", len(people)),
            })
        orders = _("1 order") if sums["orders"] == 1 else _("%s orders", sums["orders"])
        shared = _("your products shared by 1 ambassador") if ambassadors == 1 else _(
            "your products shared by %s ambassadors", ambassadors)
        return {
            "amount": self._ocd_money(sums["amount"], currency),
            "line": f"{orders} · {shared}",
            "rows": rows,
        }
