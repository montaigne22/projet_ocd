"""The page of the customer who receives a parcel of OCD Express (design OcdExpress, « My
parcel »): opened from the WhatsApp message, without an account. The code to give to the courier,
the amount to pay, « I confirm », « Not there? » (another time), « Send my position », « Not
for me », and a problem reported within the hours of the settings."""
from datetime import timedelta

from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.ocd_live import tools
from odoo.addons.ocd_live.controllers import common

from .sender import money

STEPS = ("confirmed", "on_the_way", "door", "delivered")


class OcdExpressTracking(http.Controller):

    def _parcel(self, picking_id, token):
        parcel = request.env["stock.picking"].sudo().browse(picking_id).exists()
        if not parcel or not parcel._ocd_express_check_token(token):
            raise request.not_found()
        return parcel

    def _moments(self, parcel):
        """The times the customer may choose: the next parts of the days, within 3 days."""
        env = request.env
        company = parcel.company_id
        today = company._ocd_local_today()
        hour = company._ocd_to_local(fields.Datetime.now()).hour
        labels = {"morning": env._("morning"), "afternoon": env._("afternoon"), "evening": env._("evening")}
        moments = []
        day = today
        while len(moments) < 5 and day <= today + timedelta(days=4):
            if company._ocd_express_working_day(day):
                for part, start in (("morning", 8), ("afternoon", 12), ("evening", 17)):
                    if day == today and hour >= start - 1:
                        continue
                    when = env._("this %s", labels[part]) if day == today else (
                        env._("tomorrow %s", labels[part]) if day == today + timedelta(days=1)
                        else f"{common.day_text(day, 'EEEE')} {labels[part]}")
                    moments.append({"value": f"{day.isoformat()}_{part}", "label": when})
            day += timedelta(days=1)
        return moments[:5]

    def _render(self, parcel, token, message=None, error=None):
        env = request.env
        sender = parcel.ocd_express_sender_id
        courier = parcel.ocd_courier_id
        stage = parcel.ocd_stage
        relay = parcel.ocd_relay_id
        reached = {"to_prepare": 0, "ready": 0, "picked": 0, "on_the_way": 1, "at_relay": 2, "problem": 1,
                   "delivered": 3}.get(stage, -1)
        if parcel.ocd_express_confirm == "waiting" and reached == 0:
            reached = -1
        labels = [env._("Confirmed"), env._("On the way"),
                  env._("At the relay point") if relay else env._("At your door"), env._("Delivered")]
        steps = [{"label": label, "state": "on" if index < reached or index == reached == 3 else
                  "now" if index == reached else ""} for index, label in enumerate(labels)]
        to_pay = parcel.ocd_cod_amount if parcel.ocd_cod_state == "to_collect" else 0.0
        pay_url = False
        if to_pay and stage in ("on_the_way", "at_relay") and parcel.company_id.ocd_cod_online:
            try:
                pay_url = parcel._ocd_payment_url()
            except UserError:
                pay_url = False
        phone = "".join(char for char in (courier.phone or "") if char.isdigit())
        open_parcel = parcel._ocd_express_customer_open()
        return request.render("ocd_express.tracking_page", common.page_values(
            False,
            header_brand=True,
            parcel=parcel,
            token=token,
            base=f"/express/suivi/{parcel.id}/{token}",
            sender=sender,
            customer=parcel.partner_id,
            steps=steps,
            to_pay=money(to_pay) if to_pay else "",
            paid=parcel.ocd_cod_state in ("collected", "remitted"),
            code=parcel.sudo().ocd_delivery_code if stage == ("at_relay" if relay else "on_the_way") else "",
            relay=self._relay_values(parcel) if relay else False,
            relays=[{"id": place.id, "label": place._ocd_relay_line(), "name": place.name}
                    for place in parcel._ocd_express_relay_points()] if not relay and open_parcel else [],
            relay_fee=self._relay_fee(parcel) if not relay and open_parcel else "",
            courier_name=(courier.name or "").split(" ")[0]
            if courier and stage in ("picked", "on_the_way") and not relay else "",
            courier_phone=phone,
            pay_url=pay_url,
            moments=self._moments(parcel) if open_parcel and stage != "on_the_way" and not relay else [],
            can_confirm=open_parcel and not relay and parcel.ocd_express_confirm == "waiting",
            can_answer=open_parcel,
            claim_open=parcel._ocd_express_claim_open(),
            claim_hours=parcel.company_id.ocd_express_claim_hours,
            when_line=self._when_line(parcel),
            title=env._("Parcel of %s", sender.name),
            sub_line=" · ".join(part for part in (
                parcel.name, parcel.ocd_express_content,
                env._("for %(customer)s, %(district)s", customer=parcel.partner_id.name,
                      district=parcel.partner_id.district_id.name) if parcel.partner_id.district_id
                else env._("for %s", parcel.partner_id.name),
            ) if part),
            call_label=env._("Call %s", (courier.name or "").split(" ")[0])
            if courier and phone and stage in ("picked", "on_the_way") and not relay else "",
            claim_line=env._("Within %s hours of the delivery. The team of OCD Live calls you back.",
                             parcel.company_id.ocd_express_claim_hours),
            claim_state=self._claim_state(parcel),
            message=message,
            error=error,
        ))

    def _claim_state(self, parcel):
        """The problem the customer reported after the delivery, when they come back to the page."""
        env = request.env
        if parcel.ocd_express_claim_state == "open":
            return env._("You reported a problem: the team of OCD Live calls you back.")
        if parcel.ocd_express_claim_state:
            return env._("The team of OCD Live checked the problem you reported.")
        return ""

    def _relay_values(self, parcel):
        """The relay point where the customer picks the parcel up (chantier 10)."""
        env = request.env
        relay = parcel.ocd_relay_id
        phone = "".join(char for char in (relay._ocd_phone() or "") if char.isdigit())
        waiting = parcel.ocd_stage == "at_relay"
        return {
            "name": relay.name,
            "line": relay._ocd_relay_line(),
            "deadline": env._("Pick it up before %s", parcel._ocd_relay_deadline_text()) if waiting else "",
            "directions": relay._ocd_directions_url(),
            "phone": phone if len(phone) >= 8 else "",
            "qr": tools.qr_data_uri(parcel._ocd_relay_qr_text(), box_size=6) if waiting else False,
        }

    def _relay_fee(self, parcel):
        """What the customer pays for the delivery at a relay point, when they pay it."""
        relays = parcel._ocd_express_relay_points()
        if not relays or parcel.ocd_express_fee_by != "customer":
            return ""
        try:
            _rate, fee = parcel._ocd_express_relay_rate(parcel.ocd_express_sender_id, relays[:1])
        except UserError:
            return ""
        return request.env._("Delivery at a relay point: %s instead of %s", money(fee), money(parcel.ocd_express_fee))

    def _when_line(self, parcel):
        env = request.env
        if parcel.ocd_stage == "delivered":
            return env._("Delivered. Thank you!")
        if parcel.ocd_stage == "at_relay":
            return env._("Waits for you at the relay point %s.", parcel.ocd_relay_id.name)
        if parcel.ocd_stage == "on_the_way" and parcel.ocd_relay_id:
            return env._("On its way to the relay point %s.", parcel.ocd_relay_id.name)
        if parcel.ocd_stage in ("returned", "cancelled"):
            return env._("This parcel goes back to %s.", parcel.ocd_express_sender_id.name)
        if parcel.ocd_stage == "on_the_way":
            return env._("The courier is on the way.")
        day, part = parcel.ocd_express_deliver_on, parcel.ocd_express_deliver_part
        if not day:
            return ""
        labels = {"morning": env._("morning"), "afternoon": env._("afternoon"), "evening": env._("evening")}
        today = parcel.company_id._ocd_local_today()
        when = env._("this %s", labels.get(part, "")) if day == today else (
            env._("tomorrow %s", labels.get(part, "")) if day == today + timedelta(days=1)
            else f"{common.day_text(day, 'EEEE d MMMM')} {labels.get(part, '')}")
        return env._("Arrives %s.", when)

    @http.route("/express/suivi/<int:picking_id>/<string:token>", type="http", auth="public", website=True,
                methods=["GET"], sitemap=False)
    def page(self, picking_id, token, **kwargs):
        return self._render(self._parcel(picking_id, token), token)

    @http.route("/express/suivi/<int:picking_id>/<string:token>/<string:action>", type="http", auth="public",
                website=True, methods=["POST"], sitemap=False)
    def act(self, picking_id, token, action, **post):
        parcel = self._parcel(picking_id, token)
        env = request.env
        try:
            if action == "confirmer":
                parcel._ocd_express_confirm()
                message = env._("Thank you: the courier knows you are there.")
            elif action == "moment":
                day, _sep, part = (post.get("moment") or "").partition("_")
                try:
                    day = fields.Date.to_date(day)
                except ValueError:
                    day = None
                if not day:
                    raise UserError(env._("Choose a time."))
                parcel._ocd_express_move_to(day, part)
                message = env._("Noted: the courier comes at this time.")
            elif action == "pas_pour_moi":
                parcel._ocd_express_not_for_me()
                message = env._("Noted: you will receive no more message from OCD Express.")
            elif action == "position":
                try:
                    latitude, longitude = float(post.get("latitude")), float(post.get("longitude"))
                except (TypeError, ValueError):
                    raise UserError(env._("The position of the phone could not be read.")) from None
                parcel._ocd_express_set_position(latitude, longitude)
                message = env._("Thank you: the courier sees where you are.")
            elif action == "relais":
                relay = env["ocd.vendor.place"].sudo().browse(int(post.get("relay_id") or 0)).exists()
                parcel._ocd_express_to_relay(relay)
                message = env._("Noted: your parcel waits for you at the relay point %s.", relay.name)
            elif action == "souci":
                parcel._ocd_express_report_claim(common.clean_text(post.get("note"), 500))
                message = env._("Noted: the team of OCD Live calls you back.")
            else:
                raise request.not_found()
        except UserError as exc:
            return self._render(parcel, token, error=exc.args[0])
        return self._render(parcel, token, message=message)
