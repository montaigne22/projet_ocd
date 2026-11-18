from odoo import api, models


class OcdLiveVerification(models.AbstractModel):
    """The participations to the big evenings, on the board of the checks (« To check »)."""

    _inherit = "ocd.live.verification"

    @api.model
    def _ocd_columns(self):
        columns = super()._ocd_columns()
        columns.append({
            "key": "evening",
            "label": self.env._("Big evenings"),
            "empty": self.env._("No participation waiting."),
            "items": self._ocd_evening_items(),
        })
        return columns

    @api.model
    def _ocd_evening_items(self):
        _ = self.env._
        Dashboard = self.env["ocd.live.dashboard"]
        reasons = self._ocd_reasons("evening")
        items = []
        participations = self.env["ocd.evening.participation"].search([
            ("state", "=", "to_check"), ("evening_id.state", "=", "open"),
        ], order="write_date")
        for participation in participations:
            promos = participation.promo_ids.filtered(lambda promo: not promo.stopped_at)
            live = participation.booking_id
            evening = participation.evening_id
            items.append({
                "key": f"evening_participation_{participation.id}",
                "kind": "evening_participation",
                "id": participation.id,
                "tag": evening.name,
                "title": participation.vendor_id.name,
                "photo": "",
                "sub": " · ".join(part for part in (
                    _("Live at %s", evening._ocd_hour(evening._ocd_local(live.start_datetime))) if live
                    else _("No live in the evening"),
                    _("1 promo") if len(promos) == 1 else _("%s promos", len(promos)),
                ) if part),
                "detail": "\n".join(
                    f"{promo.product_tmpl_id.name} · {Dashboard._ocd_money(promo.reference_price, promo.currency_id)}"
                    f" → {Dashboard._ocd_money(promo.price, promo.currency_id)} ({promo._ocd_off_text()})"
                    for promo in promos
                ),
                "open_label": _("See the participation"),
                "open_action": Dashboard._ocd_record_action(participation),
                "ok_label": _("Accept"),
                "reasons": reasons,
            })
        return items

    @api.model
    def _ocd_models(self):
        return {**super()._ocd_models(), "evening_participation": "ocd.evening.participation"}

    @api.model
    def ocd_approve(self, kind, record_id, values=None):
        if kind == "evening_participation":
            return self._ocd_record(kind, record_id).action_ocd_approve()
        return super().ocd_approve(kind, record_id, values)

    @api.model
    def ocd_refuse(self, kind, record_id, reason_id):
        if kind == "evening_participation":
            reason = self.env["ocd.listing.refuse.reason"].browse(reason_id).exists()
            return self._ocd_record(kind, record_id).action_ocd_refuse(reason)
        return super().ocd_refuse(kind, record_id, reason_id)
