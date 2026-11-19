"""The pages of OCD Business (chantier 12, design OcdBusiness).

- /ocd/espace/moi/business: the formula in the space of the vendor (what it adds, 1, 3 or 12 months
  paid with the payment of OCD Live, the formula running, renew, the payments and their invoices);
- /business: the page for the shops that do not do lives.

A formula is bought as the directory pass: an order of the vendor paid on /ocd/payer; the days are
added when the payment is confirmed (by its provider, or by the team for a Mobile Money checked by
hand), once. A payment already on its way, or an order left before paying, is taken again instead
of a second order."""
from odoo import Command, http
from odoo.http import request

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live.controllers import common

DURATIONS = (
    ("ocd_business.product_business_1", 1),
    ("ocd_business.product_business_3", 3),
    ("ocd_business.product_business_12", 12),
)
HOME = "/ocd/espace/moi/business"


class OcdBusiness(http.Controller):

    def _vendor(self):
        vendor = common.current_vendor()
        if not vendor:
            return None, request.redirect("/ocd/connexion")
        return vendor, None

    def _durations(self, vendor):
        """[{product, months, price, per_month, badge}] at the prices of the country of the vendor."""
        env = request.env
        prices = common.pricelist(vendor=vendor) if vendor else common.pricelist()
        rows = []
        monthly = None
        for xmlid, months in DURATIONS:
            product = env.ref(xmlid, raise_if_not_found=False)
            if not product or not product.sudo().sale_ok:
                continue
            variant = product.sudo().product_variant_id
            amount, currency = common.package_price(variant, prices)
            if months == 1:
                monthly = amount
            badge = ""
            if monthly and months > 1 and amount < monthly * months:
                saved = monthly * months - amount
                if months == 12 and saved >= monthly:
                    offered = int(round(saved / monthly))
                    badge = env._("1 month offered") if offered == 1 else env._("%s months offered", offered)
                else:
                    badge = f"−{round(saved * 100 / (monthly * months))} %"
            rows.append({
                "product": variant,
                "months": months,
                "label": env._("1 month") if months == 1 else env._("%s months", months),
                "days": env._("%s days", variant.ocd_business_days),
                "price": common.money(amount, currency),
                "per_month": env._("%s per month", common.money(amount / months, currency)) if months > 1 else "",
                "badge": badge,
            })
        return rows

    def _pending_order(self, vendor):
        """An order of OCD Business of the vendor with a payment on its way (not to be paid twice)."""
        orders = request.env["sale.order"].sudo().search([
            ("partner_id", "=", vendor.id), ("state", "in", ("draft", "sent")),
            ("order_line.product_id.ocd_product_kind", "=", "business"),
        ], order="id desc", limit=5)
        return orders.filtered(lambda order: order.transaction_ids.filtered(
            lambda tx: tx.state in ("pending", "authorized")))[:1]

    def _payments(self, vendor):
        env = request.env
        rows = []
        for period in vendor.sudo().ocd_business_period_ids.sorted(lambda p: (p.date_start, p.id), reverse=True)[:12]:
            if period.state == "cancelled":
                continue
            order = period.sale_order_id
            if period.kind == "paid":
                tx = order.transaction_ids.filtered(lambda t: t.state == "done")[:1]
                label = " · ".join(part for part in (
                    common.day_text(period.create_date.date(), "d MMM"),
                    env._("1 month") if period.days <= 31 else env._("%s days", period.days),
                    tx.provider_id.name or "",
                ) if part)
                amount = common.money(period.amount, period.currency_id) if period.currency_id else ""
            elif period.kind == "launch":
                label, amount = env._("Offered at the launch"), env._("%s days", period.days)
            else:
                label, amount = env._("Offered by the team"), env._("%s days", period.days)
            invoice = order.invoice_ids.filtered(lambda move: move.state == "posted")[:1]
            rows.append({
                "label": label,
                "amount": amount,
                "invoice_url": invoice.get_portal_url(report_type="pdf", download=True) if invoice else "",
            })
        return rows

    @http.route(HOME, type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def business(self, paye=None, **kwargs):
        vendor, answer = self._vendor()
        if answer:
            return answer
        env = request.env
        vendor_sudo = vendor.sudo()
        company = common.company()
        today = vendor_sudo._ocd_business_today()
        formula = vendor_sudo._ocd_business_formula()
        until = vendor_sudo.ocd_business_until
        Place = env["ocd.vendor.place"].sudo()
        places = Place.search_count([("vendor_id", "=", vendor.id), ("state", "=", "approved")])
        team = len(vendor_sudo.ocd_team_ids.filtered("active"))
        pending = self._pending_order(vendor_sudo)
        if formula and until and until >= today:
            until_title = env._("until %s", common.day_text(until, "EEEE d MMMM"))
        elif formula:
            until_title = env._("payment being checked")
        else:
            until_title = ""
        return request.render("ocd_business.business_page", common.page_values(
            False,
            space_page="business",
            back="/ocd/espace/moi",
            back_label=env._("Back to my space"),
            header_title=env._("OCD Business"),
            vendor=vendor,
            offered_all=company.ocd_business_offered_all,
            launch_line=env._("Offered to all until %s.", common.day_text(company.ocd_business_launch_date, "d MMMM"))
            if company.ocd_business_offered_all and company.ocd_business_launch_date else "",
            formula=formula,
            until_title=until_title,
            renew_line=env._("Renewing adds days after this date: no day is lost."),
            places_line=env._("%(count)s of %(max)s", count=places, max=vendor_sudo._ocd_places_allowed()),
            team_line=env._("1 person") if team == 1 else env._("%s people", team),
            durations=self._durations(vendor_sudo),
            payments=self._payments(vendor_sudo),
            pending_url=f"/ocd/payer/{pending.id}?access_token={pending._portal_ensure_token()}" if pending else "",
            note=vendor_sudo._ocd_business_space_note(),
            message=(env._("Paid: thank you. Your formula runs %s.", until_title) if formula else env._(
                "Thank you: your payment is on its way. Your formula is added as soon as it is confirmed.")) if paye else "",
        ))

    @http.route(HOME, type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def business_buy(self, duree=None, **post):
        """Buy a formula: an order of the vendor, paid on the payment page of OCD Live. A payment
        already on its way is taken again."""
        vendor, answer = self._vendor()
        if answer:
            return answer
        vendor = vendor.sudo()
        pending = self._pending_order(vendor)
        if pending:
            return request.redirect(f"/ocd/payer/{pending.id}?access_token={pending._portal_ensure_token()}")
        rows = {str(row["product"].id): row for row in self._durations(vendor)}
        row = rows.get(str(duree or ""))
        if not row:
            return request.redirect(HOME)
        # An order left before paying is taken again, with the duration chosen now
        draft = request.env["sale.order"].sudo().search([
            ("partner_id", "=", vendor.id), ("state", "=", "draft"), ("transaction_ids", "=", False),
            ("order_line.product_id.ocd_product_kind", "=", "business"),
        ], order="id desc", limit=1)
        if draft and len(draft.order_line) == 1:
            if draft.order_line.product_id != row["product"]:
                draft.order_line.product_id = row["product"]
            return request.redirect(f"/ocd/payer/{draft.id}?access_token={draft._portal_ensure_token()}")
        order = request.env["sale.order"].sudo().with_company(common.company()).create({
            "partner_id": vendor.id,
            "company_id": common.company().id,
            "require_signature": False,
            # A positive prepayment makes Odoo ask for the payment of the order
            "prepayment_percent": 1.0,
            "order_line": [Command.create({"product_id": row["product"].id, "product_uom_qty": 1})],
        })
        return request.redirect(f"/ocd/payer/{order.id}?access_token={order._portal_ensure_token()}")

    @http.route("/business", type="http", auth="public", website=True, methods=["GET"], sitemap=True)
    def business_public(self, **kwargs):
        """For the shops that do not do lives: a boutique on OCD Live, then the formula."""
        env = request.env
        durations = self._durations(common.current_vendor().sudo() if common.current_vendor() else None)
        monthly = next((row for row in durations if row["months"] == 1), None)
        company = common.company()
        return request.render("ocd_business.business_public", common.page_values(
            False,
            back="/",
            header_brand=True,
            price_line=env._("%s per month", monthly["price"]) if monthly else "",
            vendor=common.current_vendor(),
            whatsapp_url=tools.whatsapp_url(company.phone, env._("Hello, I want to open my boutique on OCD Live.")),
        ))
