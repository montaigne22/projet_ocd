from odoo import api, models
from odoo.tools.misc import format_amount


class OcdLiveDashboard(models.AbstractModel):
    _inherit = "ocd.live.dashboard"

    @api.model
    def _ocd_sections(self):
        sections = super()._ocd_sections()
        start, end = self._ocd_day_bounds()
        currency = self.env.company.currency_id
        dispatch = "ocd_live_shop.stock_picking_action_ocd_dispatch"
        parcel = [("ocd_is_parcel", "=", True)]
        cash = sum(
            self.env["stock.picking"].search(
                [("ocd_cod_state", "=", "collected"), ("ocd_cod_method", "=", "cash")]
            ).mapped("ocd_cod_collected_amount")
        )
        orders_domain = [
            ("state", "=", "sale"),
            ("date_order", ">=", start),
            ("date_order", "<", end),
            ("picking_ids.ocd_is_parcel", "=", True),
        ]
        orders = self.env["sale.order"].search(orders_domain)
        sections.append({
            "key": "shop",
            "title": self.env._("Shop and deliveries"),
            "tiles": [
                self._ocd_tile(
                    "orders", self.env._("Orders today: %s", format_amount(self.env, sum(orders.mapped("amount_total")), currency)),
                    "sale.order", orders_domain, "sale.action_orders",
                ),
                self._ocd_tile("prepare", self.env._("Parcels to prepare"), "stock.picking",
                               parcel + [("ocd_stage", "=", "to_prepare")], dispatch),
                self._ocd_tile("way", self.env._("Parcels on the way"), "stock.picking",
                               parcel + [("ocd_stage", "=", "on_the_way")], dispatch),
                self._ocd_tile("late", self.env._("Late parcels"), "stock.picking",
                               parcel + [("ocd_escalated_at", "!=", False), ("ocd_stage", "in", ("to_prepare", "ready"))],
                               dispatch, alert=True),
                self._ocd_tile("problem", self.env._("Delivery problems"), "stock.picking",
                               parcel + [("ocd_stage", "=", "problem")], dispatch, alert=True),
                self._ocd_tile("locked", self.env._("Locked codes"), "stock.picking",
                               parcel + [("ocd_code_locked", "=", True), ("ocd_stage", "=", "on_the_way")], dispatch, alert=True),
                self._ocd_tile("collect", self.env._("Parcels to be paid at the door"), "stock.picking",
                               parcel + [("ocd_cod_state", "=", "to_collect")], dispatch),
                self._ocd_tile("cash", self.env._("Cash to hand over: %s", format_amount(self.env, cash, currency)),
                               "stock.picking", [("ocd_cod_state", "=", "collected"), ("ocd_cod_method", "=", "cash")],
                               dispatch),
                self._ocd_tile("payouts", self.env._("Payouts to check"), "ocd.payout",
                               [("state", "=", "draft")], "ocd_live_shop.ocd_payout_action"),
            ],
        })
        return sections
