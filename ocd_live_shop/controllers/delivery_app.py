from urllib.parse import urlencode

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.ocd_live.controllers import common

OPEN_STAGES = ("to_prepare", "ready", "picked", "on_the_way", "problem")


class OcdDeliveryApp(http.Controller):
    """Delivery app on the phone: the vendor prepares and delivers the parcels, the OCD
    courier picks them up and delivers them. Each one only sees the parcels assigned."""

    def _partner(self, token):
        Partner = request.env["res.partner"].sudo()
        if token and token != "moi":
            partner = Partner._ocd_find_by_space_token(token)
            if partner.ocd_is_courier:
                return partner
            if partner.ocd_is_vendor and common.company().ocd_vendor_login == "link":
                request.session[common.SESSION_VENDOR] = partner.id
                return partner
            raise request.not_found()
        partner = common.current_vendor()
        if not partner:
            raise request.not_found()
        return partner

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
            order="ocd_delivered_at desc", limit=10,
        )
        return mine, done

    def _payment_qr(self, parcel):
        """Return the QR code that opens the payment page of the parcel on the phone of the
        customer, and the link itself."""
        url = parcel._ocd_payment_url()
        query = urlencode({"barcode_type": "QR", "value": url, "width": 280, "height": 280})
        return {"url": url, "src": f"/report/barcode?{query}"}

    def _render(self, token, partner, message=None, error=None):
        mine, done = self._parcels(partner)
        return request.render("ocd_live_shop.delivery_app", common.page_values(
            "livrer",
            partner=partner,
            token=token,
            parcels=mine,
            done=done,
            payment_qr=self._payment_qr,
            message=message,
            error=error,
        ))

    @http.route("/ocd/livrer/<string:token>", type="http", auth="public", website=True, methods=["GET"], sitemap=False)
    def app(self, token, **kwargs):
        return self._render(token, self._partner(token))

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
                message = request.env._("Parcel picked up.")
            elif action == "leave" and delivers:
                parcel.action_ocd_leave()
                message = request.env._("Good delivery! The customer received the code.")
            elif action == "code" and delivers:
                delivered, left = parcel._ocd_check_code(post.get("code"))
                if delivered:
                    message = request.env._("Delivered. Thank you!")
                elif left:
                    raise UserError(request.env._("Wrong code. Attempts left: %s.", left))
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
            else:
                raise request.not_found()
        except UserError as error:
            return self._render(token, partner, error=error.args[0])
        return self._render(token, partner, message=message)
