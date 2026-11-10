from datetime import timedelta

from odoo import api, fields, models

from odoo.addons.ocd_live.tools import day_text, hour_text

from .stock_picking import OPEN_STAGES

PARCEL = [("ocd_is_parcel", "=", True)]
TODO_ROWS = 2


class OcdLiveDashboard(models.AbstractModel):
    """The shop on the dashboard of the team: orders, parcels, payouts, late parcels, problems,
    cash of the couriers, products to check and the money of the shop."""

    _inherit = "ocd.live.dashboard"

    # === FIGURES OF THE DAY === #

    @api.model
    def _ocd_tiles(self):
        tiles = super()._ocd_tiles()
        company = self.env.company
        currency = company.currency_id
        start, end = self._ocd_day_bounds()
        # Orders of the shop received today
        orders_domain = [
            ("company_id", "=", company.id),
            ("state", "=", "sale"),
            ("date_order", ">=", start),
            ("date_order", "<", end),
            ("picking_ids.ocd_is_parcel", "=", True),
        ]
        orders = self.env["sale.order"].search(orders_domain)
        total = sum(
            order.currency_id._convert(order.amount_total, currency, company, order.date_order) for order in orders
        )
        # Parcels of the day: still open, or delivered today
        parcels_domain = PARCEL + [
            ("company_id", "=", company.id),
            "|",
            ("ocd_stage", "in", OPEN_STAGES),
            "&",
            ("ocd_stage", "=", "delivered"),
            ("ocd_delivered_at", ">=", start),
        ]
        parcels = self.env["stock.picking"].search(parcels_domain)
        delivered = len(parcels.filtered(lambda parcel: parcel.ocd_stage == "delivered"))
        late = len(parcels.filtered("ocd_is_late"))
        problems = len(parcels.filtered(lambda parcel: parcel.ocd_stage == "problem"))
        # Payouts of the next payout day
        payouts_domain = [("company_id", "=", company.id), ("state", "in", ("draft", "validated"))]
        payouts = self.env["ocd.payout"].search(payouts_domain)
        to_pay = sum(payouts.filtered(lambda payout: payout.amount > 0).mapped("amount"))
        to_recover = -sum(payouts.filtered(lambda payout: payout.amount < 0).mapped("amount"))
        payout_sub = self.env._("%s vendors", len(payouts.vendor_id)) if len(payouts.vendor_id) != 1 \
            else self.env._("1 vendor")
        if to_recover:
            payout_sub = self.env._(
                "%(vendors)s · %(amount)s to recover", vendors=payout_sub, amount=self._ocd_money(to_recover, currency)
            )
        tiles += [
            {
                "key": "orders",
                "sequence": 30,
                "label": self.env._("Shop orders"),
                "value": str(len(orders)),
                "sub": self.env._("%s today", self._ocd_money(total, currency)),
                "tone": "",
                "action": self._ocd_action("sale.action_orders", orders_domain, self.env._("Shop orders of today")),
            },
            {
                "key": "parcels",
                "sequence": 40,
                "label": self.env._("Parcels to deliver today"),
                "value": str(len(parcels)),
                "sub": self.env._(
                    "%(delivered)s delivered · %(late)s late · %(problems)s problems",
                    delivered=delivered,
                    late=late,
                    problems=problems,
                ),
                "tone": "red" if late or problems else "",
                "action": self._ocd_action("ocd_live_shop.stock_picking_action_ocd_dispatch"),
            },
            {
                "key": "payouts",
                "sequence": 50,
                "label": self.env._("To pay out on %s", day_text(self.env, self._ocd_next_payout_day(), "EEEE")),
                "value": self._ocd_money(to_pay, currency),
                "sub": payout_sub,
                "tone": "",
                "action": self._ocd_action("ocd_live_shop.ocd_payout_action", payouts_domain, self.env._("Payouts")),
            },
        ]
        return tiles

    @api.model
    def _ocd_next_payout_day(self):
        company = self.env.company
        today = company._ocd_local_today()
        weekday = int(company.ocd_payout_weekday or 0)
        return today + timedelta(days=(weekday - today.weekday()) % 7)

    # === TO DO NOW === #

    @api.model
    def _ocd_todos(self):
        todos = super()._ocd_todos()
        company = self.env.company
        Picking = self.env["stock.picking"]
        late = Picking.search(
            PARCEL + [("company_id", "=", company.id), ("ocd_escalated_at", "!=", False),
                      ("ocd_stage", "in", ("to_prepare", "ready"))],
            order="ocd_escalated_at",
            limit=TODO_ROWS,
        )
        for parcel in late:
            todos.append({
                "key": f"late_{parcel.id}",
                "tag": self.env._("Late"),
                "tone": "red",
                "text": self.env._(
                    "%(parcel)s · %(vendor)s: parcel not ready, vendor reminded",
                    parcel=parcel.name,
                    vendor=parcel.ocd_vendor_id.name,
                ),
                "action": self._ocd_record_action(parcel),
            })
        problems = Picking.search(
            PARCEL + [("company_id", "=", company.id), ("ocd_stage", "=", "problem")],
            order="write_date desc",
            limit=TODO_ROWS,
        )
        reasons = dict(Picking._fields["ocd_problem_reason"]._description_selection(self.env))
        for parcel in problems:
            reason = reasons.get(parcel.ocd_problem_reason) or self.env._("problem")
            todos.append({
                "key": f"problem_{parcel.id}",
                "tag": self.env._("Problem"),
                "tone": "red",
                "text": self.env._("%(parcel)s · %(reason)s", parcel=parcel.name, reason=reason.lower()),
                "action": self._ocd_record_action(parcel),
            })
        couriers = self.env["res.partner"].search([("ocd_is_courier", "=", True)])
        holders = couriers.filtered(lambda courier: courier.ocd_cash_on_hand > 0)[:TODO_ROWS]
        for courier in holders:
            todos.append({
                "key": f"cash_{courier.id}",
                "tag": self.env._("Cash"),
                "tone": "grey",
                "text": self.env._(
                    "%(courier)s: %(amount)s of cash to hand over before %(hour)s",
                    courier=courier.name.split()[0],
                    amount=self._ocd_money(courier.ocd_cash_on_hand),
                    hour=hour_text(company.ocd_cash_deadline),
                ),
                "action": self._ocd_record_action(courier),
            })
        return todos

    @api.model
    def _ocd_check_parts(self):
        parts = super()._ocd_check_parts()
        domain = [("ocd_vendor_id", "!=", False), ("ocd_review_state", "=", "to_check")]
        products = self.env["product.template"].search_count(domain)
        parts.insert(1, (
            products,
            self.env._("%s products", products) if products > 1 else self.env._("1 product"),
            self._ocd_action("ocd_live_shop.product_template_action_ocd_to_check"),
        ))
        return parts

    # === MONEY RECEIVED === #

    @api.model
    def _ocd_revenue_rows(self):
        rows = super()._ocd_revenue_rows()
        company = self.env.company
        # sudo: totals only
        delivered = self.env["stock.picking"].sudo().search(
            PARCEL + [("company_id", "=", company.id), ("ocd_stage", "=", "delivered")]
        )
        commissions = fees = 0.0
        for parcel in delivered:
            currency = parcel.ocd_currency_id or company.currency_id
            date = parcel.ocd_delivered_at or fields.Datetime.now()
            vendor_delivers = parcel._ocd_vendor_delivers()
            goods_share = parcel.ocd_vendor_share - (parcel.ocd_fee_amount if vendor_delivers else 0.0)
            commissions += currency._convert(parcel.ocd_goods_amount - goods_share, company.currency_id, company, date)
            if not vendor_delivers:
                fees += currency._convert(parcel.ocd_fee_amount, company.currency_id, company, date)
        return rows + [
            {"key": "commissions", "label": self.env._("Shop commissions"), "amount": commissions},
            {"key": "fees", "label": self.env._("Delivery fees (OCD couriers)"), "amount": fees},
        ]
