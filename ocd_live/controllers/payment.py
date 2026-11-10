import math
from urllib.parse import urlencode

from odoo import http
from odoo.http import request
from odoo.tools import consteq

from odoo.addons.payment.controllers.payment_status import PaymentStatus
from odoo.addons.sale.controllers.portal import CustomerPortal

from . import common


class OcdLivePayment(http.Controller):
    """Payment page of OCD Live, then the ticket of the live. The page is reached with the
    access token of the order: the vendor has no account to log in.

    The page shows the payment form of Odoo: it offers the providers and the payment methods
    that take the country, the currency and the amount of the order, as configured by the team
    (Campay in Cameroon today, Mobile Money checked by the team elsewhere, any connector added
    later). Nothing here depends on a provider."""

    def _order(self, order_id, access_token):
        order = request.env["sale.order"].sudo().browse(order_id).exists()
        if (
            not order
            or not access_token
            or not order.access_token
            or not consteq(order.access_token, access_token)
            or not (order.ocd_booking_ids or order.ocd_pass_ids)
        ):
            raise request.not_found()
        return order

    def _url(self, order, **params):
        query = urlencode({"access_token": order._portal_ensure_token(), **params})
        return f"/ocd/payer/{order.id}?{query}"

    # === PAYMENT PAGE === #

    @http.route("/ocd/payer/<int:order_id>", type="http", auth="public", website=True, sitemap=False, methods=["GET"])
    def pay(self, order_id, access_token=None, changer=None, **kwargs):
        order = self._order(order_id, access_token)
        env = request.env
        state = order._ocd_payment_state()
        last = order.transaction_ids.sorted("id")[-1:]
        if changer and state == "waiting" and last.state == "pending":
            # The vendor gives up the payment in progress to pay another way
            state = "form"
        booking = order.ocd_booking_ids.sorted("start_datetime")[:1]
        total = common.money(order.amount_total, order.currency_id)
        values = {
            "order": order,
            "access_token": access_token,
            "state": state,
            "tx": last,
            "what": booking.product_id.name if booking else order.order_line[:1].product_id.name,
            "when": self._when(booking) if booking else False,
            "hold": self._hold(booking),
            "country": order.partner_id.country_id,
            "total": total,
            "ticket_url": f"/ocd/ticket/{booking.id}?access_token={access_token}" if booking else False,
            "change_url": self._url(order, changer=1),
            "status_url": f"/ocd/payer/{order.id}/statut",
        }
        if state in ("form", "failed"):
            values.update(self._payment_form_values(order, env._("Pay %s", total)))
        return request.render("ocd_live.pay", common.page_values(
            "pay",
            back=self._back(order, booking),
            step=5 if booking else False,
            step_label=env._("Step %(step)s of %(total)s", step=5, total=5),
            summary=False,
            **values,
        ))

    def _payment_form_values(self, order, label):
        """Return the values of the payment form of Odoo for this order, as on the portal page
        of the order; the vendor comes back to this page after the payment."""
        values = CustomerPortal()._get_payment_values(order)
        values.update({
            "landing_route": self._url(order),
            "submit_button_label": label,
            "show_amount_input": False,
            "sale_order": order,
        })
        return values

    @http.route("/ocd/payer/<int:order_id>/statut", type="jsonrpc", auth="public", website=True)
    def pay_status(self, order_id, access_token=None):
        """Polled by the page while a payment is in progress: the provider confirms it."""
        order = self._order(order_id, access_token)
        return {"state": order._ocd_payment_state()}

    def _when(self, booking):
        """Line of the live, e.g. "Tue 1 Dec · 10:00 to 11:30 · studio of Lomé"."""
        env = request.env
        local = booking.company_id._ocd_to_local(booking.start_datetime)
        end = booking.company_id._ocd_to_local(booking.end_datetime)
        where = env._("studio of %s", common.studio_city()) if booking.mode == "studio" else env._("remote")
        return env._(
            "%(day)s · %(start)s to %(end)s · %(where)s",
            day=common.short_day(local.date(), capital=True),
            start=f"{local:%H:%M}",
            end=f"{end:%H:%M}",
            where=where,
        )

    def _hold(self, booking):
        if not booking or booking.state != "draft" or not booking.hold_until:
            return False
        minutes = max(1, math.ceil((booking.hold_until - common.now()).total_seconds() / 60))
        if minutes > 120:
            return request.env._("Your hour is held %s hours.", round(minutes / 60))
        return request.env._("Your hour is held %s minutes.", minutes)

    def _back(self, order, booking):
        if not booking or order.state not in ("draft", "sent"):
            return False
        local = booking.company_id._ocd_to_local(booking.start_datetime)
        return f"/reserver/{booking.mode}/{local:%Y-%m-%d}/{local:%H%M}/{booking.product_id.id}"

    # === TICKET === #

    def _ticket_booking(self, booking_id, access_token):
        booking = request.env["ocd.live.booking"].sudo().browse(booking_id).exists()
        if not booking or booking.state == "cancelled":
            raise request.not_found()
        order = booking.sale_order_id
        vendor = common.current_vendor()
        by_token = access_token and order and order.access_token and consteq(order.access_token, access_token)
        if not by_token and not (vendor and booking.partner_id == vendor):
            raise request.not_found()
        return booking

    @http.route("/ocd/ticket/<int:booking_id>", type="http", auth="public", website=True, sitemap=False, methods=["GET"])
    def ticket(self, booking_id, access_token=None, envoye=None, deplace=None, **kwargs):
        booking = self._ticket_booking(booking_id, access_token)
        order = booking.sale_order_id
        if booking.state == "draft" and order:
            return request.redirect(self._url(order))
        env = request.env
        company = booking.company_id
        local = company._ocd_to_local(booking.start_datetime)
        end = company._ocd_to_local(booking.end_datetime)
        city = common.studio_city()
        needs = {
            "shelf": env._("a shelf waits for you at the studio"),
            "rack": env._("a clothes rack waits for you at the studio"),
            "table": env._("a table waits for you at the studio"),
        }
        package_line = booking.product_id.name
        if booking.mode == "studio" and booking.studio_need in needs:
            package_line = f"{package_line} · {needs[booking.studio_need]}"
        movable = booking.state == "confirmed" and (
            booking.start_datetime - common.now()
        ).total_seconds() > company.ocd_move_limit_hours * 3600
        token_query = f"?access_token={access_token}" if access_token else ""
        return request.render("ocd_live.ticket", common.page_values(
            "ticket",
            booking=booking,
            access_token=access_token,
            day=common.short_day(local.date(), capital=True),
            hours=f"{local:%H:%M} – {end:%H:%M}",
            tz_line=env._("Time of %s", city),
            place=env._("Studio OCD, %s", city) if booking.mode == "studio" else env._("From home, remote"),
            place_line=(
                env._("Address and map sent on WhatsApp")
                if booking.mode == "studio"
                else env._("The link of the live and the host arrive on WhatsApp")
            ),
            who=" · ".join(filter(None, [booking.partner_id.name, booking.partner_id.ocd_category_id.name])),
            package_line=package_line,
            code_line=(
                env._("Show this code at the door of the studio.")
                if booking.mode == "studio"
                else env._("Give this code to the team when asked.")
            ),
            movable=movable,
            move_url=f"/ocd/deplacer/{booking.id}{token_query}",
            receipt_url=order.get_portal_url(report_type="pdf", download=True) if order else False,
            sent=envoye,
            moved=bool(deplace),
            send_url=f"/ocd/ticket/{booking.id}/whatsapp{token_query}",
        ))

    @http.route(
        "/ocd/ticket/<int:booking_id>/whatsapp",
        type="http", auth="public", website=True, sitemap=False, methods=["POST"],
    )
    def ticket_send(self, booking_id, access_token=None, **post):
        booking = self._ticket_booking(booking_id, access_token)
        params = {"envoye": "1" if booking._ocd_send_ticket() else "0"}
        if access_token:
            params["access_token"] = access_token
        return request.redirect(f"/ocd/ticket/{booking.id}?{urlencode(params)}")


class OcdLivePaymentStatus(PaymentStatus):
    """While Odoo processes the payment of a live or of a pass, its waiting page wears the
    look of OCD Live, then sends the vendor back to the payment page of OCD Live."""

    def get_payment_status_template_xmlid(self, tx):
        orders = tx.sudo().sale_order_ids if tx else request.env["sale.order"]
        if orders.filtered(lambda order: order.ocd_booking_ids or order.ocd_pass_ids):
            return "ocd_live.payment_status"
        return super().get_payment_status_template_xmlid(tx)
