from odoo import api, models


class OcdLiveDispatch(models.AbstractModel):
    """The parcels of OCD Express on the dispatch, with those of the shop: the sender instead of
    the vendor, the content; giving a parcel still to pick up to a courier gives them its whole
    passage at the sender."""

    _inherit = "ocd.live.dispatch"

    @api.model
    def _ocd_search_domain(self, search):
        """A parcel of OCD Express is also found by its sender and its content."""
        domain = super()._ocd_search_domain(search)
        if domain:
            search = search.strip()
            domain = ["|", "|", ("ocd_express_sender_id.name", "ilike", search),
                      ("ocd_express_content", "ilike", search), *domain]
        return domain

    @api.model
    def _ocd_card(self, parcel):
        card = super()._ocd_card(parcel)
        if parcel.ocd_express:
            card.update({
                "vendor": self.env._("Express · %s", parcel.ocd_express_sender_id.name or ""),
                "items": parcel.ocd_express_content or "",
            })
            if parcel.ocd_express_check == "to_check":
                card.update({"tag": self.env._("To check"), "tone": "yellow", "can_assign": False})
        return card

    @api.model
    def ocd_assign(self, picking_id, courier_id):
        parcel = self._ocd_parcel(picking_id)
        pickup = parcel.ocd_express_pickup_id
        if parcel.ocd_express and pickup.state == "planned" and parcel.ocd_stage == "ready":
            courier = self.env["res.partner"].browse(courier_id).exists()
            if courier and not courier.ocd_is_courier:
                return super().ocd_assign(picking_id, courier_id)
            pickup.courier_id = courier
            return True
        return super().ocd_assign(picking_id, courier_id)
