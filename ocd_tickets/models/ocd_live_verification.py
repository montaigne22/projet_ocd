from odoo import api, models


class OcdLiveVerification(models.AbstractModel):
    """The events sent by the organisers, on the board of the checks (« To check »)."""

    _inherit = "ocd.live.verification"

    @api.model
    def _ocd_columns(self):
        columns = super()._ocd_columns()
        columns.append({
            "key": "ticket",
            "label": self.env._("Events"),
            "empty": self.env._("No event waiting."),
            "items": self._ocd_ticket_items(),
        })
        return columns

    @api.model
    def _ocd_ticket_items(self):
        _ = self.env._
        Dashboard = self.env["ocd.live.dashboard"]
        reasons = self._ocd_reasons("ticket")
        items = []
        events = self.env["event.event"].search([("ocd_ticketing", "=", True), ("ocd_state", "=", "to_check")],
                                                order="write_date")
        for event in events:
            kinds = " · ".join(f"{ticket.name} {event._ocd_money(ticket.price)}" for ticket in event.event_ticket_ids)
            items.append({
                "key": f"ticket_event_{event.id}",
                "kind": "ticket_event",
                "id": event.id,
                "tag": _("New event"),
                "title": event.name,
                "photo": f"/web/image/event.event/{event.id}/ocd_poster/256" if event.ocd_poster else "",
                "sub": " · ".join(part for part in (
                    event.ocd_organizer_id.name or _("OCD Live"),
                    event._ocd_when_text(),
                    event._ocd_place_text(),
                ) if part),
                "detail": "\n".join(part for part in (kinds, event.ocd_about) if part),
                "open_label": _("See the event"),
                "open_action": Dashboard._ocd_record_action(event),
                "ok_label": _("Check and put on sale"),
                "reasons": reasons,
            })
        return items

    @api.model
    def _ocd_models(self):
        return {**super()._ocd_models(), "ticket_event": "event.event"}

    @api.model
    def ocd_approve(self, kind, record_id, values=None):
        if kind == "ticket_event":
            return self._ocd_record(kind, record_id).action_ocd_approve()
        return super().ocd_approve(kind, record_id, values)

    @api.model
    def ocd_refuse(self, kind, record_id, reason_id):
        if kind == "ticket_event":
            reason = self.env["ocd.listing.refuse.reason"].browse(reason_id).exists()
            return self._ocd_record(kind, record_id).action_ocd_refuse(reason)
        return super().ocd_refuse(kind, record_id, reason_id)
