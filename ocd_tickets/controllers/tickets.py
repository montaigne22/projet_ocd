"""The pages of OCD Tickets for the public (design OcdTickets): the events, an event and its kinds
of tickets, buy (a number per kind, the name, the WhatsApp number), « My tickets » (the payment,
then one QR per person, the PDF, « Give this ticket »), the page of one ticket."""
from urllib.parse import urlencode

from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.http.stream import content_disposition

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live.controllers import common
from odoo.addons.ocd_live.controllers.payment import OcdLivePayment
from odoo.addons.ocd_live_shop.controllers.vendor_follow import visitor_partner

# Under this number of tickets left, the kind says « Only 12 left »
LOW_LEFT = 20


def event_or_404(slug):
    event = request.env["event.event"].sudo().search([("ocd_slug", "=", slug), ("ocd_ticketing", "=", True)], limit=1)
    if not event or not event._ocd_public():
        raise request.not_found()
    return event


def pdf_response(pdf, name):
    return request.make_response(pdf, headers=[
        ("Content-Type", "application/pdf"),
        ("Content-Length", len(pdf)),
        ("Content-Disposition", content_disposition(name)),
        ("Cache-Control", "private, no-store"),
        ("X-Robots-Tag", "noindex"),
    ])


def tickets_pdf(registrations):
    lang = registrations[:1].partner_id.lang or request.env.lang
    report = request.env.ref("ocd_tickets.action_report_tickets").sudo().with_context(lang=request.env.lang or lang)
    pdf, _report_type = report._render_qweb_pdf(report.report_name, registrations.ids)
    return pdf


class OcdTicketsPages(http.Controller):

    # === THE EVENTS === #

    @http.route("/billets", type="http", auth="public", website=True, sitemap=True, ocd_cache=30)
    def events(self, **kwargs):
        now = common.now()
        events = request.env["event.event"].sudo().search([
            ("ocd_ticketing", "=", True), ("ocd_state", "=", "approved"), ("date_end", ">", now),
        ], order="date_begin", limit=40)
        rows = [{
            "event": event,
            "when": event._ocd_when_text("EEE d MMM"),
            "place": event._ocd_place_text(),
            "poster": event._ocd_poster_url(),
            "from": self._from_text(event),
            "open": event._ocd_on_sale(now),
        } for event in events]
        return request.render("ocd_tickets.events", common.page_values(
            False, nav="tickets", header_title=request.env._("Tickets"), rows=rows,
        ))

    def _from_text(self, event):
        prices = [ticket._ocd_price() for ticket in event.event_ticket_ids]
        if not prices:
            return ""
        return request.env._("From %s", event._ocd_money(min(prices)))

    def _kinds(self, event, quantities=None):
        """The kinds of tickets as the pages show them: price, live price, what is left."""
        env = request.env
        left = event._ocd_left()
        live = event._ocd_live_now()
        quantities = quantities or {}
        rows = []
        for ticket in event.event_ticket_ids.sorted("sequence"):
            available = left.get(ticket.id)
            out = available is not None and available <= 0
            price = ticket._ocd_price(live=live)
            rows.append({
                "ticket": ticket,
                "price": price,
                "price_text": event._ocd_money(price),
                "usual_text": event._ocd_money(ticket.price) if price < ticket.price else False,
                "each_text": env._("%s a ticket", event._ocd_money(price)),
                "note": ticket.description or "",
                "out": out,
                "low": env._("Only %s left", available) if available is not None and 0 < available <= LOW_LEFT else False,
                "max": min(available, 10) if available is not None else 10,
                "quantity": quantities.get(ticket.id, 0),
            })
        return rows

    def _event_values(self, event):
        env = request.env
        now = common.now()
        sold_line, left_line = event._ocd_seats_line()
        live = event._ocd_live_now(now)
        company = common.company()
        number = company.phone or ""
        if event.ocd_state == "cancelled":
            state_line = env._("This event is cancelled: every buyer is refunded on their number.")
        elif event._ocd_passed(now):
            state_line = env._("This event is over.")
        elif not event._ocd_on_sale(now):
            state_line = env._("The sale on the site is over: tickets at the door, if there are any left.") \
                if event.ocd_door_sale else env._("The sale on the site is over.")
        else:
            state_line = False
        return {
            "event": event,
            "on_sale": event._ocd_on_sale(now),
            "state_line": state_line,
            "poster": event._ocd_poster_url(),
            "kind_line": " · ".join(part for part in ("OCD Tickets", event.ocd_kind) if part),
            "when": event._ocd_when_text(),
            "doors": event._ocd_doors_text(),
            "place": event._ocd_place_text(),
            "district": event._ocd_district(),
            "route_url": event._ocd_route_url(),
            "sold_line": sold_line,
            "left_line": left_line,
            "organizer_line": event._ocd_organizer_line(),
            "live": live,
            "live_line": env._("Live price until the end of the live.") if live else False,
            "moved_line": env._("Moved: the tickets bought before stay valid.") if event.ocd_moved_at else False,
            "report_url": tools.whatsapp_url(number, env._("Hello, I report the event %s on OCD Tickets.", event.name)),
            "share_url": request.httprequest.url_root.rstrip("/") + event._ocd_public_path(),
        }

    @http.route("/billets/<string:slug>", type="http", auth="public", website=True, sitemap=False, ocd_cache=10)
    def event(self, slug, **kwargs):
        event = event_or_404(slug)
        values = self._event_values(event)
        kinds = self._kinds(event)
        # The − / + of the larger screens start at one ticket of the first kind left
        first = next((row for row in kinds if not row["out"]), None)
        if first:
            first["quantity"] = 1
        return request.render("ocd_tickets.event", common.page_values(
            False,
            nav="tickets",
            back="/billets",
            header_title=request.env._("Tickets"),
            header_share=values["share_url"],
            kinds=kinds,
            **values,
        ))

    # === BUY === #

    def _quantities(self, event, params):
        quantities = {}
        for ticket in event.event_ticket_ids:
            raw = str(params.get(f"q_{ticket.id}") or "0").strip()
            quantities[ticket.id] = int(raw) if raw.isdigit() else 0
        return quantities

    def _render_buy(self, event, error=None, values=None):
        env = request.env
        values = values or {}
        partner = visitor_partner()
        country = env["res.country"].sudo().browse(int(values.get("country_id") or 0)).exists() \
            or (partner.country_id if partner else None) or event.address_id.country_id or common.default_country()
        phone = values.get("phone")
        if phone is None and partner and partner.phone:
            phone = common.local_digits(country, partner.phone) if common.normalize_phone(country, partner.phone) else ""
        name = values.get("name")
        if name is None and partner and partner.name and not partner.name.startswith("+"):
            name = partner.name
        quantities = self._quantities(event, values)
        kinds = self._kinds(event, quantities)
        if not any(quantities.values()):
            first = next((row for row in kinds if not row["out"]), None)
            if first:
                first["quantity"] = 1
        most = max(common.company().ocd_ticket_max_per_order, 1)
        return request.render("ocd_tickets.buy", common.page_values(
            False,
            nav="tickets",
            back=event._ocd_public_path(),
            header_title=event.name,
            event=event,
            kinds=kinds,
            on_sale=event._ocd_on_sale(),
            most=most,
            most_line=env._("%s tickets at most per order.", most),
            dial_rows=common.dial_rows(country),
            phone_value=phone or "",
            name_value=name or "",
            currency_symbol=event.ocd_currency_id.symbol,
            error=error,
        ))

    @http.route("/billets/<string:slug>/acheter", type="http", auth="public", website=True, sitemap=False,
                methods=["GET"])
    def buy(self, slug, **kwargs):
        event = event_or_404(slug)
        if not event._ocd_on_sale():
            return request.redirect(event._ocd_public_path())
        return self._render_buy(event, values=kwargs)

    @http.route("/billets/<string:slug>/acheter", type="http", auth="public", website=True, sitemap=False,
                methods=["POST"])
    def buy_post(self, slug, phone=None, country_id=None, name=None, **post):
        event = event_or_404(slug)
        env = request.env
        values = dict(post, phone=phone, country_id=country_id, name=name)
        country = env["res.country"].sudo().browse(int(country_id or 0)).exists() or common.default_country()
        number = common.normalize_phone(country, phone)
        holder = common.clean_text(name, 60)
        if not holder:
            return self._render_buy(event, error=env._("Write your name: it is on the tickets."), values=values)
        if not number:
            return self._render_buy(event, error=common.phone_error(country), values=values)
        partner = env["ocd.vendor.follower"].sudo()._ocd_contact(number)
        if not partner.country_id:
            partner.country_id = country
        if partner.name == number:
            partner.name = holder
        tickets = event.event_ticket_ids
        quantities = {tickets.browse(ticket_id): count for ticket_id, count in self._quantities(event, post).items()}
        try:
            order = env["sale.order"].sudo()._ocd_ticket_create(event, quantities, partner, holder)
        except UserError as exc:
            return self._render_buy(event, error=exc.args[0], values=values)
        return request.redirect(order._ocd_tickets_path())

    # === MY TICKETS === #

    def _order(self, order_id, token):
        order = request.env["sale.order"].sudo().browse(order_id).exists()
        if not order or not order.ocd_ticket_event_id or not order._ocd_check_ticket_token(token):
            raise request.not_found()
        return order

    def _ticket_rows(self, registrations):
        return [{
            "ticket": registration,
            "index": registration._ocd_index_text(),
            "qr": registration._ocd_qr(),
            "path": registration._ocd_ticket_path(),
            "valid": registration._ocd_valid(),
            "entered": registration.state == "done",
            "entered_line": request.env._("Entered at %s", registration.event_id._ocd_hour(
                registration.event_id._ocd_local(registration.ocd_entered_at))) if registration.ocd_entered_at else False,
        } for registration in registrations]

    def _mine(self, order):
        """The tickets of the order still in the name of the buyer (not given)."""
        return order.ocd_ticket_registration_ids.filtered(
            lambda registration: registration.ocd_code and registration.state != "cancel"
            and registration.partner_id == order.partner_id and not registration.ocd_given_by_id
        ).sorted("id")

    @http.route("/billets/commande/<int:order_id>", type="http", auth="public", website=True, sitemap=False,
                methods=["GET"])
    def order_page(self, order_id, t=None, changer=None, donne=None, rembourse=None, erreur=None, **kwargs):
        order = self._order(order_id, t)
        env = request.env
        event = order.ocd_ticket_event_id
        state = order._ocd_payment_state()
        last = order.transaction_ids.sorted("id")[-1:]
        if changer and state == "waiting" and last.state == "pending":
            state = "form"
        total = common.money(order.amount_total, order.currency_id)
        mine = self._mine(order)
        count = int(sum(order.order_line.filtered("event_ticket_id").mapped("product_uom_qty")))
        values = {
            "order": order,
            "event": event,
            "state": state,
            "tx": last,
            "token": t,
            "total": total,
            "what": env._("1 ticket") if count == 1 else env._("%s tickets", count),
            "lines": [f"{int(line.product_uom_qty)} × {line.event_ticket_id.name}"
                      for line in order.order_line.filtered("event_ticket_id")],
            "status_url": f"/billets/commande/{order.id}/statut",
            "change_url": f"{order._ocd_tickets_path()}&changer=1",
            "rows": self._ticket_rows(mine),
            "message": env._("Given: the ticket left on the WhatsApp of %s with a new QR.", donne) if donne else False,
            "error": erreur,
            "refund_until": False,
            "dial_rows": common.dial_rows(order.partner_id.country_id or common.default_country()),
        }
        if state == "done":
            paid = len(mine)
            values["paid_title"] = env._("It is paid: 1 ticket") if paid == 1 else env._("It is paid: %s tickets", paid)
            values["refunded"] = order.ocd_ticket_registration_ids.filtered(
                lambda registration: registration.ocd_refund_state != "none" and registration.partner_id == order.partner_id)
            until = event._ocd_refund_until()
            if until and fields.Datetime.now() < until and not event._ocd_passed() and mine.filtered(
                    lambda registration: registration._ocd_valid() and registration.state == "open"):
                values["refund_until"] = env._("Moved to %(when)s. You cannot come? Ask for the refund before %(day)s.",
                                               when=event._ocd_when_sentence(),
                                               day=tools.day_text(env, event._ocd_local(until).date(), "EEEE d MMMM"))
            values["refund_noted"] = bool(rembourse)
        if state in ("form", "failed"):
            payment = OcdLivePayment()._payment_form_values(order, env._("Pay %s", total))
            payment["landing_route"] = order._ocd_tickets_path()
            values.update(payment)
            values["no_method"] = not (values.get("payment_methods_sudo") or values.get("tokens_sudo"))
            values["help_whatsapp"] = tools.whatsapp_url(common.company().phone, env._(
                "Hello, I want to pay my tickets %(order)s (%(total)s) from %(country)s.",
                order=order.name, total=total, country=order.partner_id.country_id.name or "",
            ))
            values["hold_line"] = env._("Your seats are held %s minutes.", common.company().ocd_ticket_hold_minutes)
        return request.render("ocd_tickets.order_page", common.page_values(
            False,
            nav="tickets",
            back=event._ocd_public_path() if state in ("form", "failed") else False,
            header_title=env._("My tickets"),
            **values,
        ))

    @http.route("/billets/commande/<int:order_id>/statut", type="jsonrpc", auth="public", website=True)
    def order_status(self, order_id, access_token=None):
        """Polled by the page while the payment is in progress."""
        return {"state": self._order(order_id, access_token)._ocd_payment_state()}

    @http.route("/billets/commande/<int:order_id>/envoye", type="http", auth="public", website=True, sitemap=False,
                methods=["POST"])
    def order_announced(self, order_id, t=None, reference=None, **post):
        """« I paid »: the Mobile Money checked by the team was sent."""
        order = self._order(order_id, t)
        last = order.transaction_ids.sorted("id")[-1:]
        if order._ocd_payment_state() == "waiting" and last.state == "pending" and last.provider_code == "custom":
            order._ocd_announce_payment(common.clean_text(reference, 60))
        return request.redirect(order._ocd_tickets_path())

    @http.route("/billets/commande/<int:order_id>/pdf", type="http", auth="public", website=True, sitemap=False,
                methods=["GET"])
    def order_pdf(self, order_id, t=None, **kwargs):
        order = self._order(order_id, t)
        mine = self._mine(order).filtered(lambda registration: registration._ocd_valid())
        if not mine:
            return request.redirect(order._ocd_tickets_path())
        return pdf_response(tickets_pdf(mine), f"Tickets {order.ocd_ticket_event_id.ocd_slug}.pdf")

    @http.route("/billets/commande/<int:order_id>/rembourser", type="http", auth="public", website=True,
                sitemap=False, methods=["POST"])
    def order_refund(self, order_id, t=None, **post):
        """After a move: the buyer cannot come and asks for the refund of the tickets not used."""
        order = self._order(order_id, t)
        event = order.ocd_ticket_event_id
        until = event._ocd_refund_until()
        if until and fields.Datetime.now() < until:
            tickets = self._mine(order).filtered(
                lambda registration: registration._ocd_valid() and registration.state == "open")
            tickets.write({"ocd_refund_state": "to_refund"})
            order.message_post(body=request.env._("The buyer cannot come at the new date: %s tickets to refund.",
                                                  len(tickets)))
        return request.redirect(f"{order._ocd_tickets_path()}&rembourse=1")

    # === ONE TICKET, GIVE IT === #

    def _ticket(self, registration_id, signature):
        registration = request.env["event.registration"].sudo().browse(registration_id).exists()
        if not registration or not registration.event_id.ocd_ticketing or not registration._ocd_check_signature(signature):
            raise request.not_found()
        return registration

    @http.route("/billets/billet/<int:registration_id>/<string:signature>", type="http", auth="public", website=True,
                sitemap=False, methods=["GET"])
    def ticket_page(self, registration_id, signature, erreur=None, **kwargs):
        registration = self._ticket(registration_id, signature)
        event = registration.event_id
        return request.render("ocd_tickets.ticket_page", common.page_values(
            False,
            nav="tickets",
            back=event._ocd_public_path() if event._ocd_public() else False,
            header_title=request.env._("My ticket"),
            event=event,
            rows=self._ticket_rows(registration),
            given_by=registration.ocd_given_by_id.name if registration.ocd_given_by_id else False,
            give_action=f"{registration._ocd_ticket_path()}/donner",
            pdf_url=f"{registration._ocd_ticket_path()}/pdf",
            error=erreur,
            dial_rows=common.dial_rows(registration.partner_id.country_id or common.default_country()),
        ))

    @http.route("/billets/billet/<int:registration_id>/<string:signature>/pdf", type="http", auth="public",
                website=True, sitemap=False, methods=["GET"])
    def ticket_pdf(self, registration_id, signature, **kwargs):
        registration = self._ticket(registration_id, signature)
        if not registration._ocd_valid():
            return request.redirect(registration._ocd_ticket_path())
        return pdf_response(tickets_pdf(registration), f"Ticket {registration.ocd_code}.pdf")

    @http.route("/billets/billet/<int:registration_id>/<string:signature>/donner", type="http", auth="public",
                website=True, sitemap=False, methods=["POST"])
    def ticket_give(self, registration_id, signature, phone=None, country_id=None, name=None, t=None, **post):
        """« Give this ticket »: the WhatsApp number of a friend; the ticket leaves with a new QR, the
        old one no longer works."""
        registration = self._ticket(registration_id, signature)
        env = request.env
        order = registration.sale_order_id
        back = order._ocd_tickets_path() if t and order._ocd_check_ticket_token(t) else registration._ocd_ticket_path()
        separator = "&" if "?" in back else "?"
        country = env["res.country"].sudo().browse(int(country_id or 0)).exists() or common.default_country()
        number = common.normalize_phone(country, phone)
        if not number:
            return request.redirect(f"{back}{separator}{urlencode({'erreur': common.phone_error(country)})}")
        friend = env["ocd.vendor.follower"].sudo()._ocd_contact(number)
        friend_name = common.clean_text(name, 60)
        if friend.name == number and friend_name:
            friend.name = friend_name
        if not friend.country_id:
            friend.country_id = country
        try:
            registration._ocd_give(friend, friend_name or friend.name)
        except UserError as exc:
            return request.redirect(f"{back}{separator}{urlencode({'erreur': exc.args[0]})}")
        if t and order._ocd_check_ticket_token(t):
            return request.redirect(f"{back}&{urlencode({'donne': friend_name or number})}")
        return request.redirect(f"{event_path(registration)}?donne=1")

    # === THE POSTER === #

    @http.route("/billets/image/<int:event_id>", type="http", auth="public", website=True, sitemap=False)
    def poster(self, event_id, v=None, **kwargs):
        event = request.env["event.event"].sudo().browse(event_id).exists()
        if not event or not event.ocd_poster or not event._ocd_public():
            raise request.not_found()
        stream = request.env["ir.binary"]._get_image_stream_from(event, "ocd_poster", width=1280, height=1280)
        return common.media_response(stream, True, version=v)


def event_path(registration):
    event = registration.event_id
    return event._ocd_public_path() if event._ocd_public() else "/billets"
