import math
from urllib.parse import urlencode

from odoo import http
from odoo.http import request
from odoo.http.stream import content_disposition
from odoo.tools import consteq

from odoo.addons.payment.controllers.payment_status import PaymentStatus
from odoo.addons.sale.controllers.portal import CustomerPortal

from .. import tools
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
            # No payment method for the country, the currency or the amount: the team helps,
            # instead of a page without a way out
            values["no_method"] = not (values.get("payment_methods_sudo") or values.get("tokens_sudo"))
            if values["no_method"]:
                values.update(
                    no_method_title=env._(
                        "Paying online is not open yet in your country: %s.", order.partner_id.country_id.name or "-"
                    ),
                    help_asked=bool(order.ocd_payment_help_date),
                    help_url=f"/ocd/payer/{order.id}/aide",
                    help_whatsapp=tools.whatsapp_url(common.company().phone, env._(
                        "Hello, I want to pay my order %(order)s (%(total)s) from %(country)s.",
                        order=order.name, total=total, country=order.partner_id.country_id.name or "",
                    )),
                )
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

    @http.route("/ocd/payer/<int:order_id>/envoye", type="http", auth="public", website=True, sitemap=False, methods=["POST"])
    def pay_announced(self, order_id, access_token=None, reference=None, **post):
        """« I paid »: the vendor says the payment checked by the team (Mobile Money to the number
        of OCD) was sent. The hour stays held while the team checks it; without this, it is
        offered again to the others after the time given to pay."""
        order = self._order(order_id, access_token)
        last = order.transaction_ids.sorted("id")[-1:]
        if order._ocd_payment_state() == "waiting" and last.state == "pending" and last.provider_code == "custom":
            order._ocd_announce_payment(common.clean_text(reference, 60))
        return request.redirect(self._url(order))

    @http.route("/ocd/payer/<int:order_id>/aide", type="http", auth="public", website=True, sitemap=False, methods=["POST"])
    def pay_help(self, order_id, access_token=None, **post):
        """No payment method fits the country of the vendor: the team is asked to help."""
        order = self._order(order_id, access_token)
        if order._ocd_payment_state() in ("form", "failed"):
            order._ocd_ask_payment_help()
        return request.redirect(self._url(order))

    @http.route("/ocd/payer/<int:order_id>/statut", type="jsonrpc", auth="public", website=True)
    def pay_status(self, order_id, access_token=None):
        """Polled by the page while a payment is in progress: the provider confirms it."""
        order = self._order(order_id, access_token)
        return {"state": order._ocd_payment_state()}

    def _when(self, booking):
        """Line of the live, e.g. "Tue 1 Dec · 10:00 to 11:30 · studio of Lomé", in the time
        zone of the vendor."""
        env = request.env
        local = common.to_viewer(booking.start_datetime)
        end = common.to_viewer(booking.end_datetime)
        where = env._("studio of %s", common.studio_city()) if booking.mode == "studio" else env._("remote")
        return env._(
            "%(day)s · %(start)s to %(end)s · %(where)s",
            day=common.short_day(local.date(), capital=True),
            start=f"{local:%H:%M}",
            end=f"{end:%H:%M}",
            where=where,
        )

    def _hold(self, booking):
        if not booking or booking.state != "draft":
            return False
        minutes = max(1, math.ceil((booking._ocd_hold_end() - common.now()).total_seconds() / 60))
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

    def _token_query(self, access_token):
        return f"?access_token={access_token}" if access_token else ""

    @http.route("/ocd/ticket/<int:booking_id>", type="http", auth="public", website=True, sitemap=False, methods=["GET"])
    def ticket(self, booking_id, access_token=None, envoye=None, deplace=None, **kwargs):
        booking = self._ticket_booking(booking_id, access_token)
        order = booking.sale_order_id
        if booking.state == "draft" and order:
            return request.redirect(self._url(order))
        env = request.env
        company = booking.company_id
        tz_name = common.viewer_tz()
        ticket = booking.with_context(lang=env.lang)._ocd_ticket_values(tz_name)
        movable = booking.state == "confirmed" and (
            booking.start_datetime - common.now()
        ).total_seconds() > company.ocd_move_limit_hours * 3600
        query = self._token_query(access_token)
        announce = booking.with_context(lang=env.lang)._ocd_announce_values(tz_name)
        return request.render("ocd_live.ticket", common.page_values(
            "ticket",
            booking=booking,
            access_token=access_token,
            ticket=ticket,
            day=common.short_day(tools.to_tz(booking.start_datetime, tz_name).date(), capital=True),
            place_line=(
                env._("Address and map sent on WhatsApp")
                if booking.mode == "studio"
                else env._("The link of the live and the host arrive on WhatsApp")
            ),
            who=" · ".join(filter(None, [ticket["vendor"], ticket["category"]])),
            package_line=" · ".join(filter(None, [ticket["package"], ticket["need"]])),
            code_line=(
                env._("Show this ticket at the door of the studio.")
                if booking.mode == "studio"
                else env._("Give its number to the team when asked.")
            ),
            movable=movable,
            move_url=f"/ocd/deplacer/{booking.id}{query}",
            receipt_url=order.get_portal_url(report_type="pdf", download=True) if order else False,
            pdf_url=f"/ocd/ticket/{booking.id}/pdf{query}",
            announce=announce,
            announce_url=f"/ocd/ticket/{booking.id}/annonce{query}",
            sent=envoye,
            moved=bool(deplace),
            send_url=f"/ocd/ticket/{booking.id}/whatsapp{query}",
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

    @http.route("/ocd/ticket/<int:booking_id>/pdf", type="http", auth="public", website=True, sitemap=False, methods=["GET"])
    def ticket_pdf(self, booking_id, access_token=None, **kwargs):
        """The ticket as a PDF: personal, for the vendor only (never cached by a proxy)."""
        booking = self._ticket_booking(booking_id, access_token)
        if booking.state not in ("confirmed", "done"):
            return request.redirect(f"/ocd/ticket/{booking.id}{self._token_query(access_token)}")
        pdf, name = booking._ocd_ticket_pdf(lang=request.env.lang, tz_name=common.viewer_tz())
        return request.make_response(pdf, headers=[
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(pdf)),
            ("Content-Disposition", content_disposition(name)),
            ("Cache-Control", "private, no-store"),
            ("X-Robots-Tag", "noindex"),
        ])

    @http.route("/ocd/ticket/<int:booking_id>/annonce", type="http", auth="public", website=True, sitemap=False, methods=["GET"])
    def ticket_announce(self, booking_id, access_token=None, telecharger=None, **kwargs):
        """The image that announces the live to the friends of the vendor: no personal
        information on it (no number, no ticket). Opened only by the vendor."""
        booking = self._ticket_booking(booking_id, access_token)
        if booking.state not in ("confirmed", "done"):
            raise request.not_found()
        tz_name = common.viewer_tz()
        booking = booking.with_context(lang=request.env.lang)
        name = booking._ocd_announce_values(tz_name)["file_name"]
        png = booking._ocd_announce_png(tz_name)
        return request.make_response(png, headers=[
            ("Content-Type", "image/png"),
            ("Content-Length", len(png)),
            ("Content-Disposition", content_disposition(name, "attachment" if telecharger else "inline")),
            ("Cache-Control", "private, max-age=600"),
            ("X-Robots-Tag", "noindex"),
        ])

    # === CHECK AT THE ENTRY === #

    def _check_state(self, booking):
        """What the check of a ticket answers: ok, used, other_day, over, unpaid, cancelled."""
        if booking.state == "cancelled":
            return "cancelled"
        if booking.state == "draft":
            return "unpaid"
        if booking.state == "done" or booking.end_datetime <= common.now():
            return "over"
        if booking.ticket_checked_in:
            return "used"
        company = booking.company_id
        if company._ocd_to_local(booking.start_datetime).date() != company._ocd_local_today():
            return "other_day"
        return "ok"

    @http.route(
        "/ocd/ticket/verifier/<int:booking_id>/<string:signature>",
        type="http", auth="public", website=True, sitemap=False, methods=["GET"],
    )
    def ticket_check(self, booking_id, signature, entre=None, **kwargs):
        """The QR code of the ticket opens this page. Anyone sees whether the ticket is valid;
        the team also sees who it is for, and lets the vendor in once."""
        booking = request.env["ocd.live.booking"].sudo().browse(booking_id).exists()
        valid = bool(booking) and booking._ocd_ticket_check(signature)
        user = request.env.user
        team = not user._is_public() and user.has_group("ocd_live.group_ocd_live_user")
        state = self._check_state(booking) if valid else "invalid"
        if entre and state == "used" and team and booking.ticket_checked_in_by == user:
            state = "entered"  # this person just let the vendor in
        env = request.env
        values = {"state": state, "team": team, "entered": bool(entre), "signature": signature}
        if valid:
            # The team reads the hours of the studio; the vendor, their own
            tz_name = common.studio_tz() if team else common.viewer_tz()
            ticket = booking.with_context(lang=env.lang)._ocd_ticket_values(tz_name)
            values.update(
                booking=booking,
                ticket=ticket,
                when=f"{ticket['day']} · {ticket['hours']}",
                let_in_url=f"/ocd/ticket/verifier/{booking.id}/{signature}/entree",
                let_in_label=env._("Let in") if booking.mode == "studio" else env._("Validate the ticket"),
                checked_line=env._(
                    "Entered at %(hour)s, let in by %(name)s.",
                    hour=f"{tools.to_tz(booking.ticket_checked_in, tz_name):%H:%M}",
                    name=booking.ticket_checked_in_by.name or "",
                ) if booking.ticket_checked_in else "",
                login_url="/web/login?redirect=" + request.httprequest.path,
            )
        return request.render("ocd_live.ticket_check", common.page_values(False, **values))

    @http.route(
        "/ocd/ticket/verifier/<int:booking_id>/<string:signature>/entree",
        type="http", auth="user", website=True, sitemap=False, methods=["POST"],
    )
    def ticket_let_in(self, booking_id, signature, **post):
        """The team lets the vendor in: the ticket is used from now on."""
        if not request.env.user.has_group("ocd_live.group_ocd_live_user"):
            raise request.not_found()
        booking = request.env["ocd.live.booking"].browse(booking_id).exists()
        if not booking or not booking._ocd_ticket_check(signature):
            raise request.not_found()
        if self._check_state(booking) == "ok":
            booking._ocd_let_in()
        return request.redirect(f"/ocd/ticket/verifier/{booking.id}/{signature}?entre=1")


class OcdLivePaymentStatus(PaymentStatus):
    """While Odoo processes the payment of a live or of a pass, its waiting page wears the
    look of OCD Live, then sends the vendor back to the payment page of OCD Live."""

    def get_payment_status_template_xmlid(self, tx):
        orders = tx.sudo().sale_order_ids if tx else request.env["sale.order"]
        if orders.filtered(lambda order: order.ocd_booking_ids or order.ocd_pass_ids):
            return "ocd_live.payment_status"
        return super().get_payment_status_template_xmlid(tx)
