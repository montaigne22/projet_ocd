import re
from datetime import timedelta
from urllib.parse import urlencode

import werkzeug.exceptions

from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live.controllers import common

from .delivery_login import current_courier, remember_courier

OPEN_STAGES = ("to_prepare", "ready", "picked", "on_the_way", "problem")
# Label and colour of the step of a parcel, as in the design
PILLS = {
    "to_prepare": "prep",
    "ready": "ready",
    "picked": "picked",
    "on_the_way": "route",
    "delivered": "done",
    "problem": "problem",
}


class OcdDeliveryApp(http.Controller):
    """Delivery app on the phone (designs Livrer and Tournee): the vendor prepares and
    delivers the parcels, the OCD courier picks them up and delivers them. Each one only sees
    the parcels assigned."""

    def _partner(self, token):
        """The courier or the vendor of the app: from its personal link (link mode), or opened on
        this phone (link or code). Otherwise the page of the number."""
        Partner = request.env["res.partner"].sudo()
        if token and token != "moi":
            partner = Partner._ocd_find_by_space_token(token)
            if not (partner.ocd_is_courier or partner.ocd_is_vendor):
                raise request.not_found()
            if common.company().ocd_vendor_login != "link":
                # Code or password: a personal link does not open the app, the number does
                werkzeug.exceptions.abort(request.redirect("/ocd/livrer"))
            # The personal link opens the app on this phone for the next times
            if partner.ocd_is_courier:
                remember_courier(partner)
            else:
                common.remember_vendor(partner)
            return partner
        partner = current_courier() or common.current_vendor()
        if not partner:
            werkzeug.exceptions.abort(request.redirect("/ocd/livrer"))
        return partner

    def _header_link(self, partner):
        if partner.ocd_is_courier:
            return {"href": "/ocd/livrer/deconnexion", "post": True, "label": request.env._("Log out")}
        return common.vendor_header_link(common.current_vendor_and_source()[1])

    def _parcels(self, partner):
        Picking = request.env["stock.picking"].sudo()
        domain = [("ocd_is_parcel", "=", True), ("ocd_stage", "in", OPEN_STAGES)]
        if partner.ocd_is_courier:
            mine = Picking.search(domain + [("ocd_courier_id", "=", partner.id)], order="create_date, id")
        else:
            mine = Picking.search(
                domain + ["|", ("ocd_vendor_id", "=", partner.id), ("ocd_courier_id", "=", partner.id)],
                order="create_date, id",
            )
        done = Picking.search(
            [("ocd_is_parcel", "=", True), ("ocd_stage", "=", "delivered"),
             "|", ("ocd_courier_id", "=", partner.id), ("ocd_vendor_id", "=", partner.id)],
            order="ocd_delivered_at desc", limit=20,
        )
        return mine, done

    def _payment_qr(self, parcel):
        """Return the QR code that opens the payment page of the parcel on the phone of the
        customer, and the link itself."""
        url = parcel._ocd_payment_url()
        query = urlencode({"barcode_type": "QR", "value": url, "width": 280, "height": 280})
        return {"url": url, "src": f"/report/barcode?{query}"}

    # === WHAT THE APP SHOWS === #

    def _hour(self, parcel, value):
        return parcel.company_id._ocd_to_local(value).strftime("%H:%M") if value else ""

    def _first_name(self, partner):
        return (partner.name or "").split()[0] if partner.name else ""

    def _items(self, parcel):
        rows = []
        for move in parcel.move_ids:
            qty = int(move.product_uom_qty) if move.product_uom_qty == int(move.product_uom_qty) else move.product_uom_qty
            rows.append(f"{move.product_id.name} × {qty}" if qty != 1 else move.product_id.name)
        return ", ".join(rows)

    def _place(self, parcel):
        return " · ".join(part for part in (parcel.ocd_district_id.name or parcel.partner_id.city, parcel.ocd_landmark) if part)

    def _pill(self, parcel):
        if parcel.ocd_code_locked:
            return "locked", request.env._("Locked")
        key = PILLS.get(parcel.ocd_stage, "ready")
        labels = {
            "prep": request.env._("To prepare"),
            "ready": request.env._("Ready"),
            "picked": request.env._("Picked up"),
            "route": request.env._("On the way"),
            "done": request.env._("Delivered"),
            "problem": request.env._("Problem"),
        }
        return key, labels[key]

    def _payment(self, parcel, delivers):
        """Chip of the payment: paid online (green) or the money to collect (yellow)."""
        if parcel.ocd_cod_state == "to_collect":
            amount = common.money(parcel.ocd_cod_amount, parcel.ocd_currency_id)
            if parcel.ocd_fee_amount:
                return "collect", request.env._("To collect: %s, delivery included", amount)
            return "collect", request.env._("To collect: %s", amount)
        if parcel.ocd_cod_state in ("collected", "remitted"):
            return "paid", request.env._("Paid at the door: %s", common.money(parcel.ocd_cod_collected_amount, parcel.ocd_currency_id))
        if delivers:
            return "paid", request.env._("Paid online: you collect nothing")
        return "paid", request.env._("Paid online")

    def _when(self, parcel):
        """Line of the time and of the reference of the parcel."""
        reference = parcel.name
        if parcel.ocd_stage == "to_prepare" and parcel.ocd_vendor_id:
            deadline = parcel.create_date + timedelta(hours=parcel.ocd_vendor_id._ocd_prep_hours())
            return request.env._("To prepare before %(hour)s · %(ref)s", hour=self._hour(parcel, deadline), ref=reference)
        if parcel.ocd_stage == "ready" and parcel.ocd_ready_at:
            return request.env._("Ready at %(hour)s · %(ref)s", hour=self._hour(parcel, parcel.ocd_ready_at), ref=reference)
        if parcel.ocd_stage == "on_the_way" and parcel.ocd_left_at:
            return request.env._("Left at %(hour)s · %(ref)s", hour=self._hour(parcel, parcel.ocd_left_at), ref=reference)
        return reference

    def _problem_line(self, parcel):
        reasons = dict(parcel._fields["ocd_problem_reason"]._description_selection(request.env))
        return request.env._(
            "Reported: %(reason)s. The OCD team calls you back and offers a new time to %(customer)s.",
            reason=(reasons.get(parcel.ocd_problem_reason) or "").lower(),
            customer=self._first_name(parcel.partner_id),
        )

    def _card(self, parcel, partner):
        prepares = parcel.ocd_vendor_id == partner
        delivers = parcel.ocd_courier_id == partner
        # The courier still has to pick the parcel up at the vendor (or at the stock)
        to_pick = delivers and parcel.ocd_delivery_mode != "vendor" and parcel.ocd_stage in ("to_prepare", "ready")
        pill, pill_label = self._pill(parcel)
        pay, pay_label = self._payment(parcel, delivers)
        customer = self._first_name(parcel.partner_id)
        courier = parcel.ocd_courier_id
        other_courier = courier if courier and courier != partner else False
        phone = re.sub(r"\D", "", parcel.ocd_customer_phone or "")
        return {
            "parcel": parcel,
            "prepares": prepares,
            "delivers": delivers,
            "to_pick": to_pick,
            "pill": pill,
            "pill_label": pill_label,
            "place": self._place(parcel),
            "items": self._items(parcel),
            "pay": pay,
            "pay_label": pay_label,
            "when": self._when(parcel),
            "customer": customer,
            "phone": phone,
            "whatsapp": f"https://wa.me/{phone}" if len(phone) >= 8 else False,
            "other_courier": other_courier,
            "other_initials": common.initials(other_courier.name) if other_courier else "",
            "other_line": request.env._(
                "%(courier)s, OCD courier, picks it up · %(ref)s",
                courier=self._first_name(other_courier), ref=parcel.name,
            ) if other_courier else "",
            "ready_line": request.env._(
                "Ready. %s is told. Give them the parcel when they arrive.", self._first_name(other_courier)
            ) if other_courier else "",
            "picked_line": request.env._(
                "Picked up by %(courier)s at %(hour)s. Not them? Tell the OCD team right away.",
                courier=self._first_name(other_courier), hour=self._hour(parcel, parcel.ocd_picked_at),
            ) if other_courier and parcel.ocd_picked_at else "",
            "leave_note": request.env._("%s receives the code on WhatsApp when you leave.", customer),
            "code_label": request.env._("Code given by %s", customer),
            "problem_line": self._problem_line(parcel) if parcel.ocd_stage == "problem" else "",
            "methods": self._methods(parcel, partner) if delivers and parcel.ocd_cod_state == "to_collect" else [],
            "pay_question": request.env._("How does %s pay?", customer),
            "pickup_title": request.env._("Pick up at %s", parcel.ocd_vendor_id.name) if parcel.ocd_vendor_id
            else request.env._("Pick up at the OCD stock"),
            "pickup_place": self._place_of(parcel.ocd_vendor_id) if parcel.ocd_vendor_id else "",
            "pickup_note": request.env._(
                "%s receives a WhatsApp: if it is not you, they report it.", self._first_name(parcel.ocd_vendor_id)
            ) if parcel.ocd_vendor_id else "",
            "deliver_title": request.env._(
                "Take to the travel agency for %s", parcel.partner_id.city_id.name or parcel.partner_id.city or "-"
            ) if parcel.ocd_by_agency else request.env._("Deliver to %s", parcel.partner_id.name),
            "agency_line": request.env._(
                "Through a travel agency to %(city)s, for %(customer)s. Give the parcel to the agency with the "
                "name and the WhatsApp of the customer: the team validates it when the customer has it.",
                city=parcel.partner_id.city_id.name or parcel.partner_id.city or "-",
                customer=parcel.partner_id.name,
            ) if parcel.ocd_by_agency else "",
            "for_title": request.env._("For %s", parcel.partner_id.name),
            "first_pick": request.env._("First pick the parcel up at %s.", parcel.ocd_vendor_id.name or request.env._("the OCD stock")),
        }

    def _methods(self, parcel, partner):
        """Payment methods at the door. A vendor who does not take the money can still show the
        payment on the phone of the customer: the provider confirms it, not the vendor."""
        methods = parcel._ocd_allowed_cod_methods(partner)
        if not methods and parcel.company_id.ocd_cod_online:
            methods = ["online"]
        return methods

    def _place_of(self, partner):
        return " · ".join(part for part in (partner.district_id.name or partner.city, partner.delivery_landmark) if part)

    def _done_row(self, parcel):
        when = parcel.company_id._ocd_to_local(parcel.ocd_delivered_at) if parcel.ocd_delivered_at else None
        day = ""
        if when:
            today = parcel.company_id._ocd_local_today()
            day = request.env._("today, %s", when.strftime("%H:%M")) if when.date() == today else \
                tools.day_text(request.env, when.date(), "EEE d MMM")
        return {
            "parcel": parcel,
            "who": parcel.partner_id.name,
            "detail": " · ".join(part for part in (day, parcel.ocd_district_id.name, self._items(parcel)) if part),
            "forced": bool(parcel.ocd_forced_by_id),
        }

    def _payout_line(self, partner):
        """What the vendor receives at the next payout, when OCD sells for them."""
        if partner.ocd_is_courier or partner.ocd_sale_mode != "ocd":
            return False
        moves = request.env["account.move"].sudo().search([
            ("partner_id", "=", partner.id),
            ("move_type", "in", ("in_invoice", "in_refund")),
            ("state", "=", "posted"),
            ("payment_state", "in", ("not_paid", "partial")),
            ("ocd_picking_id", "!=", False),
        ])
        amount = sum(m.amount_residual if m.move_type == "in_invoice" else -m.amount_residual for m in moves)
        if amount <= 0:
            return False
        day = request.env["ocd.live.dashboard"].sudo()._ocd_next_payout_day()
        money = common.money(amount, common.company().currency_id)
        if partner.ocd_payout_momo:
            return request.env._(
                "%(day)s, you receive %(amount)s on your Mobile Money",
                day=tools.day_text(request.env, day, "EEEE", capital=True), amount=money,
            )
        return request.env._(
            "%(day)s, you receive %(amount)s",
            day=tools.day_text(request.env, day, "EEEE", capital=True), amount=money,
        )

    def _tour_steps(self, cards):
        """Steps of the tour of the courier: pick up, then deliver, numbered."""
        steps = []
        for card in cards:
            if card["to_pick"]:
                steps.append({"kind": "pickup", "card": card})
            steps.append({"kind": "deliver", "card": card})
        for number, step in enumerate(steps, start=1):
            step["number"] = number
        return steps

    def _render(self, token, partner, message=None, error=None, parcel_id=None, tab=None):
        mine, done = self._parcels(partner)
        cards = [self._card(parcel, partner) for parcel in mine]
        if parcel_id and parcel_id not in mine.ids:
            # The parcel left the list (delivered, returned): the message goes to the top
            parcel_id = None
        company = common.company()
        today = company._ocd_local_today()
        values = {
            "partner": partner,
            "token": token,
            "base": f"/ocd/livrer/{token}",
            "cards": cards,
            "done_rows": [self._done_row(parcel) for parcel in done],
            "payment_qr": self._payment_qr,
            "message": message if not parcel_id else None,
            "error": error if not parcel_id else None,
            "card_message": message if parcel_id else None,
            "card_error": error if parcel_id else None,
            "card_id": parcel_id,
            "tab": "done" if tab == "livres" else "todo",
            "header_name": request.env._("OCD courier") if partner.ocd_is_courier else request.env._("My parcels"),
            "header_link": self._header_link(partner),
            "nav": False if partner.ocd_is_courier else "me",
        }
        if request.httprequest.method == "POST":
            # After an action, reloading the page shows the app (not the address of the action)
            values["replace_url"] = f"/ocd/livrer/{token}"
        if partner.ocd_is_courier:
            delivered_today = done.filtered(
                lambda p: p.ocd_delivered_at and company._ocd_to_local(p.ocd_delivered_at).date() == today
            )
            steps = self._tour_steps(cards)
            phone = re.sub(r"\D", "", company.phone or "")
            values.update({
                "steps": steps,
                "tour_line": " · ".join(part for part in (
                    self._first_name(partner),
                    tools.day_text(request.env, today, "EEE d MMM"),
                    partner.city,
                ) if part),
                "left_label": request.env._("%s steps left", len(steps)) if len(steps) != 1 else request.env._("1 step left"),
                "cash": common.money(partner.ocd_cash_on_hand, partner.currency_id or company.currency_id),
                "last_done": [self._done_row(parcel) | {
                    "title": request.env._("Delivered to %s", parcel.partner_id.name),
                    "line": request.env._(
                        "%(district)s · %(hour)s · code checked",
                        district=parcel.ocd_district_id.name or "", hour=self._hour(parcel, parcel.ocd_delivered_at),
                    ),
                } for parcel in delivered_today[:3]],
                "end_line": request.env._("End of the tour: hand over the cash to the dispatch before %s.", tools.hour_text(company.ocd_cash_deadline))
                if partner.ocd_cash_on_hand else request.env._("End of the tour when all the steps are done."),
                "dispatch_phone": phone,
                "call_label": request.env._("Call the dispatch"),
            })
            template = "ocd_live_shop.delivery_tour"
        else:
            values.update({
                "hello": request.env._("Hello %s", self._first_name(partner)),
                "payout_line": self._payout_line(partner),
                "todo_label": request.env._("To do · %s", len(cards)),
                "done_label": request.env._("Delivered · %s", len(done)),
            })
            template = "ocd_live_shop.delivery_app"
        return request.render(template, common.page_values("livrer", **values))

    @http.route("/ocd/livrer/<string:token>", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def app(self, token, vue=None, **kwargs):
        return self._render(token, self._partner(token), tab=vue)

    @http.route("/ocd/livrer/<string:token>/service", type="http", auth="public", website=True,
                methods=["POST"], sitemap=False)
    def on_duty(self, token, **post):
        """The courier starts or ends the service: only couriers on duty get new parcels."""
        partner = self._partner(token)
        if not partner.ocd_is_courier:
            raise request.not_found()
        partner.ocd_courier_available = not partner.ocd_courier_available
        return request.redirect(f"/ocd/livrer/{token}")

    @http.route(
        "/ocd/livrer/<string:token>/colis/<int:picking_id>/<string:action>",
        type="http", auth="public", website=True, methods=["POST"], sitemap=False,
    )
    def act(self, token, picking_id, action, **post):
        partner = self._partner(token)
        parcel = request.env["stock.picking"].sudo().browse(picking_id).exists()
        prepares = parcel and parcel.ocd_vendor_id == partner
        delivers = parcel and parcel.ocd_courier_id == partner
        if not parcel or not parcel.ocd_is_parcel or not (prepares or delivers):
            raise request.not_found()
        message = None
        try:
            if action == "ready" and prepares:
                parcel.action_ocd_ready()
                message = request.env._("Thank you: the parcel is ready.")
            elif action == "pickup" and delivers:
                parcel.action_ocd_pick_up()
                message = request.env._("Picked up at %s.", self._hour(parcel, fields.Datetime.now()))
            elif action == "leave" and delivers:
                parcel.action_ocd_leave()
                message = request.env._("Good delivery! The customer received the code.")
            elif action == "code" and delivers:
                if parcel.ocd_cod_state == "to_collect":
                    # The money is never left behind: paid first, then the code
                    raise UserError(request.env._("Collect the payment first, then type the code of the customer."))
                delivered, left = parcel._ocd_check_code(post.get("code"))
                if delivered:
                    message = request.env._("Delivered. Thank you!")
                elif left:
                    raise UserError(request.env._("This is not the right code. Attempts left: %s.", left))
                else:
                    raise UserError(request.env._("Wrong code: the parcel is locked. Call the team."))
            elif action == "collect" and delivers:
                parcel._ocd_collect(post.get("method"), partner, reference=post.get("reference"))
                message = request.env._("Payment saved.")
            elif action == "problem" and delivers:
                reason = post.get("reason")
                if reason not in dict(parcel._fields["ocd_problem_reason"].selection):
                    raise UserError(request.env._("Choose what happened."))
                parcel._ocd_report_problem(reason, common.clean_text(post.get("note"), 300))
                message = request.env._("Problem saved: the team is alerted.")
            elif action == "retry" and delivers:
                reasons = dict(parcel._fields["ocd_problem_reason"]._description_selection(request.env))
                reason = reasons.get(parcel.ocd_problem_reason) or ""
                parcel.action_ocd_retry()
                # Traced on the parcel: who resumed, after which problem
                parcel.message_post(body=request.env._(
                    "Delivery resumed by %(who)s from the delivery app, after: %(reason)s",
                    who=partner.name, reason=reason,
                ))
                message = request.env._("Delivery resumed.")
            else:
                raise request.not_found()
        except UserError as exc:
            return self._render(token, partner, error=exc.args[0], parcel_id=parcel.id)
        return self._render(token, partner, message=message, parcel_id=parcel.id)
