from odoo import api, models


class OcdLiveVerification(models.AbstractModel):
    """OCD Express on the board of the checks (« To check »): the requests of the senders, the
    parcels held (above the limit, identity, first day), the problems reported by the customers."""

    _inherit = "ocd.live.verification"

    @api.model
    def _ocd_columns(self):
        columns = super()._ocd_columns()
        columns.append({
            "key": "express",
            "label": self.env._("OCD Express"),
            "empty": self.env._("Nothing waiting for OCD Express."),
            "items": self._ocd_express_items(),
        })
        return columns

    @api.model
    def _ocd_express_items(self):
        _ = self.env._
        Dashboard = self.env["ocd.live.dashboard"]
        Pickup = self.env["ocd.express.pickup"]
        reasons = self._ocd_reasons("express")
        items = []
        for sender in self.env["res.partner"].search([("ocd_express_state", "=", "requested")], order="write_date"):
            items.append({
                "key": f"express_sender_{sender.id}",
                "kind": "express_sender",
                "id": sender.id,
                "tag": _("New sender"),
                "title": sender.name,
                "photo": "",
                "sub": " · ".join(part for part in (
                    sender.phone, sender.ocd_express_social, sender.district_id.name, sender.delivery_landmark,
                ) if part),
                "detail": _("Already a vendor of OCD Live.") if sender.ocd_is_vendor else "",
                "open_label": _("See the sender"),
                "open_action": Dashboard._ocd_record_action(sender),
                "ok_label": _("Open the account"),
                "reasons": reasons,
            })
        parcels = self.env["stock.picking"].search(
            [("ocd_express", "=", True), ("ocd_express_check", "=", "to_check"), ("ocd_stage", "!=", "cancelled")],
            order="create_date",
        )
        for parcel in parcels:
            items.append({
                "key": f"express_parcel_{parcel.id}",
                "kind": "express_parcel",
                "id": parcel.id,
                "tag": _("Parcel held"),
                "title": f"{parcel.name} · {parcel.ocd_express_sender_id.name}",
                "photo": "",
                "sub": " · ".join(part for part in (
                    parcel.partner_id.name, parcel.partner_id.district_id.name or parcel.partner_id.city_id.name,
                    _("to collect %s", Pickup._ocd_money(parcel.ocd_cod_amount)) if parcel.ocd_cod_amount else _("already paid"),
                ) if part),
                "detail": parcel.ocd_express_check_reason or "",
                "open_label": _("See the parcel"),
                "open_action": Dashboard._ocd_record_action(parcel),
                "ok_label": _("Let it leave"),
                "reasons": reasons,
            })
        claims = self.env["stock.picking"].search(
            [("ocd_express", "=", True), ("ocd_express_claim_state", "=", "open")], order="ocd_express_claim_at")
        for parcel in claims:
            items.append({
                "key": f"express_claim_{parcel.id}",
                "kind": "express_claim",
                "id": parcel.id,
                "tag": _("Problem reported"),
                "title": f"{parcel.name} · {parcel.ocd_express_sender_id.name}",
                "photo": "",
                "sub": " · ".join(part for part in (
                    parcel.partner_id.name, Pickup._ocd_money(parcel.ocd_goods_amount) if parcel.ocd_goods_amount else "",
                ) if part),
                "detail": parcel.ocd_express_claim_note or "",
                "open_label": _("See the parcel"),
                "open_action": Dashboard._ocd_record_action(parcel),
                "ok_label": _("The sender is right"),
                "refuse_label": _("The customer is right"),
                # The reason chosen is not sent: the customer is paid back, the sender is told
                "reasons": reasons,
            })
        return items

    @api.model
    def _ocd_models(self):
        return {**super()._ocd_models(), "express_sender": "res.partner", "express_parcel": "stock.picking",
                "express_claim": "stock.picking"}

    @api.model
    def ocd_approve(self, kind, record_id, values=None):
        if kind == "express_sender":
            return self._ocd_record(kind, record_id).action_ocd_express_approve()
        if kind == "express_parcel":
            return self._ocd_record(kind, record_id).action_ocd_express_approve()
        if kind == "express_claim":
            return self._ocd_record(kind, record_id).action_ocd_express_claim_sender()
        return super().ocd_approve(kind, record_id, values)

    @api.model
    def ocd_refuse(self, kind, record_id, reason_id):
        reason = self.env["ocd.listing.refuse.reason"].browse(reason_id).exists() if reason_id else None
        if kind == "express_sender":
            return self._ocd_record(kind, record_id).action_ocd_express_refuse(reason)
        if kind == "express_parcel":
            return self._ocd_record(kind, record_id).action_ocd_express_refuse(reason)
        if kind == "express_claim":
            return self._ocd_record(kind, record_id).action_ocd_express_claim_customer()
        return super().ocd_refuse(kind, record_id, reason_id)
