"""OCD Express in the tour of the courier (design OcdExpress, « My tour »): one step for all the
parcels of a sender to pick up (tick, photo of the parcels closed, « not taken » with the reason,
« the sender is absent »), the deliveries as the parcels of the shop (no Mobile Money « declared
»), then the returns given back against the return code of the sender."""
from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import BinaryBytes

from odoo.addons.ocd_live.controllers import common
from odoo.addons.ocd_live_shop.controllers.delivery_app import OcdDeliveryApp

PHOTO_MAX = 8 * 1024 * 1024


class OcdExpressDeliveryApp(OcdDeliveryApp):

    def _items(self, parcel):
        if parcel.ocd_express:
            return parcel.ocd_express_content or ""
        return super()._items(parcel)

    def _card(self, parcel, partner):
        card = super()._card(parcel, partner)
        if not parcel.ocd_express:
            return card
        env = request.env
        sender = parcel.ocd_express_sender_id
        card.update({
            "express": True,
            "pickup_title": env._("Pick up at %s", sender.name),
            "first_pick": env._("First the pick-up at %s.", sender.name),
            "open_line": env._("They may open the parcel before paying.") if parcel.ocd_express_can_open
            else env._("The sender asks not to open the parcel before paying."),
            "position_url": f"https://www.google.com/maps/search/?api=1&query={parcel.ocd_express_latitude},"
                            f"{parcel.ocd_express_longitude}" if parcel.ocd_express_latitude else False,
            "confirm_line": env._("Confirmed by the customer") if parcel.ocd_express_confirm == "confirmed" else "",
        })
        return card

    def _tour_step_list(self, cards, partner=None):
        """The pick-ups of OCD Express first (one per sender and part of the day), the deliveries,
        then the returns to give back."""
        if not partner or not partner.ocd_is_courier:
            return super()._tour_step_list(cards, partner)
        company = common.company()
        today = company._ocd_local_today()
        later = [card for card in cards if card["parcel"].ocd_express and card["to_pick"]
                 and card["parcel"].ocd_express_pickup_id.date and card["parcel"].ocd_express_pickup_id.date > today]
        cards = [card for card in cards if card not in later]
        steps = []
        pickups = request.env["ocd.express.pickup"].sudo().search([
            ("courier_id", "=", partner.id), ("state", "=", "planned"), ("date", "<=", today),
        ], order="date, part, id")
        for pickup in pickups:
            parcels = pickup.parcel_ids.filtered(lambda p: p.ocd_stage == "ready")
            if parcels:
                steps.append(self._pickup_step(pickup, parcels))
        for step in super()._tour_step_list(cards, partner):
            if step["kind"] == "pickup" and step["card"]["parcel"].ocd_express:
                continue
            steps.append(step)
        returns = request.env["stock.picking"].sudo().search([
            ("ocd_express", "=", True), ("ocd_express_return_state", "=", "to_return"),
            ("ocd_courier_id", "=", partner.id),
        ], order="ocd_express_sender_id, id")
        for sender, parcels in returns.grouped("ocd_express_sender_id").items():
            steps.append(self._return_step(sender, parcels))
        return steps

    def _sender_place(self, sender):
        return " · ".join(part for part in (sender.district_id.name or sender.city, sender.delivery_landmark,
                                            sender.street) if part)

    def _pickup_step(self, pickup, parcels):
        env = request.env
        sender = pickup.sender_id
        company = pickup.company_id
        count = len(parcels)
        free = count >= company.ocd_express_pickup_free_from or not company.ocd_express_pickup_fee
        phone = "".join(char for char in (sender.phone or "") if char.isdigit())
        return {
            "kind": "express_pickup",
            "template": "ocd_express.tour_pickup",
            "pickup": pickup,
            "parcels": parcels,
            "title": env._("Pick up at %s", sender.name),
            "place": self._sender_place(sender),
            "count_line": env._("%s parcels", count) if count != 1 else env._("1 parcel"),
            "fee_line": env._("Free pick-up") if free else env._(
                "Pick-up of %(count)s parcels: %(amount)s for the sender", count=count,
                amount=common.money(company.ocd_express_pickup_fee, company.currency_id)),
            "phone": phone,
            "check_line": "" if sender.ocd_express_place_checked else env._(
                "First pick-up at this sender: check the place exists."),
        }

    def _return_step(self, sender, parcels):
        env = request.env
        return {
            "kind": "express_return",
            "template": "ocd_express.tour_return",
            "sender": sender,
            "parcels": parcels,
            "title": env._("Give back to %s", sender.name),
            "place": self._sender_place(sender),
            "labels": {parcel.id: env._("%(parcel)s · %(customer)s: return code", parcel=parcel.name,
                                        customer=parcel.partner_id.name) for parcel in parcels},
            "hint": env._("Ask %s for their return code of each parcel: without it, keep the parcel.",
                          (sender.name or "").split(" ")[0]),
        }

    def _courier(self, token):
        partner = self._partner(token)
        if not partner.ocd_is_courier:
            raise request.not_found()
        return partner

    @http.route("/ocd/livrer/<string:token>/express/ramassage/<int:pickup_id>/<string:action>",
                type="http", auth="public", website=True, methods=["POST"], sitemap=False)
    def express_pickup(self, token, pickup_id, action, **post):
        partner = self._courier(token)
        pickup = request.env["ocd.express.pickup"].sudo().browse(pickup_id).exists()
        if not pickup or pickup.courier_id != partner:
            raise request.not_found()
        env = request.env
        try:
            if action == "fait":
                Picking = env["stock.picking"].sudo()
                ids = {int(value) for value in request.httprequest.form.getlist("taken") if value.isdigit()}
                taken = Picking.browse(list(ids)) & pickup.parcel_ids
                not_taken = {
                    parcel: common.clean_text(post.get(f"reason_{parcel.id}"), 120) or env._("Not given to the courier")
                    for parcel in pickup.parcel_ids - taken
                }
                photo = None
                upload = request.httprequest.files.get("photo")
                if upload and upload.filename:
                    data = upload.read(PHOTO_MAX + 1)
                    if len(data) > PHOTO_MAX:
                        raise UserError(env._("The photo is too big."))
                    photo = BinaryBytes(data)
                pickup._ocd_done(taken, not_taken=not_taken, photo=photo)
                message = env._("Picked up at %(hour)s: %(count)s parcels.",
                                hour=common.to_viewer(fields.Datetime.now()).strftime("%H:%M"), count=len(taken))
            elif action == "absent":
                pickup._ocd_missed(common.clean_text(post.get("note"), 120))
                message = env._("Noted: the parcels wait for the next passage.")
            else:
                raise request.not_found()
        except UserError as exc:
            return self._render(token, partner, error=exc.args[0])
        return self._render(token, partner, message=message)

    @http.route("/ocd/livrer/<string:token>/express/retour/<int:picking_id>", type="http", auth="public",
                website=True, methods=["POST"], sitemap=False)
    def express_return(self, token, picking_id, code=None, **post):
        partner = self._courier(token)
        parcel = request.env["stock.picking"].sudo().browse(picking_id).exists()
        if not parcel or not parcel.ocd_express or parcel.ocd_courier_id != partner:
            raise request.not_found()
        env = request.env
        try:
            given, left = parcel._ocd_express_hand_back((code or "").strip(), partner)
        except UserError as exc:
            return self._render(token, partner, error=exc.args[0])
        if given:
            return self._render(token, partner, message=env._("Given back to %s. Thank you!",
                                                              parcel.ocd_express_sender_id.name))
        if left:
            return self._render(token, partner, error=env._("This is not the return code. Attempts left: %s.", left))
        return self._render(token, partner, error=env._("Wrong return code: the return is blocked. Call the team."))
