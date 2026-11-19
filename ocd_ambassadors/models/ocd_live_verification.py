from odoo import api, models


class OcdLiveVerification(models.AbstractModel):
    """The ambassadors on the board of the checks (« To check », design Ambassadeurs): an account
    asked (program on invitation), a Mobile Money shared with another account, an account paused
    by its returns, an identity to see before the payout, a return asked on a gain."""

    _inherit = "ocd.live.verification"

    @api.model
    def _ocd_columns(self):
        columns = super()._ocd_columns()
        columns.append({
            "key": "ambassadors",
            "label": self.env._("Ambassadors"),
            "empty": self.env._("Nothing waiting for the ambassadors."),
            "items": self._ocd_ambassador_items(),
        })
        return columns

    @api.model
    def _ocd_ambassador_items(self):
        _ = self.env._
        Dashboard = self.env["ocd.live.dashboard"]
        reasons = self._ocd_reasons("ambassador")
        Partner = self.env["res.partner"]
        items = []
        tags = {"requested": _("Account asked"), "to_check": _("To check"), "paused": _("Paused")}
        oks = {"requested": _("Open the account"), "to_check": _("Accept"), "paused": _("Open again")}
        for partner in Partner.search([("ocd_ambassador_state", "in", ("requested", "to_check", "paused"))],
                                      order="write_date"):
            items.append({
                "key": f"ambassador_{partner.id}",
                "kind": "ambassador",
                "id": partner.id,
                "tag": tags[partner.ocd_ambassador_state],
                "title": partner.name,
                "photo": "",
                "sub": " · ".join(part for part in (partner.phone, partner.ocd_payout_momo and _(
                    "Mobile Money %s", partner.ocd_payout_momo)) if part),
                "detail": partner.ocd_ambassador_note or "",
                "open_label": _("See the ambassador"),
                "open_action": Dashboard._ocd_record_action(partner),
                "ok_label": oks[partner.ocd_ambassador_state],
                "refuse_label": _("Close the account"),
                "reasons": reasons,
            })
        company = self.env.company
        if company.ocd_ambassador_id_above:
            totals = {}
            for partner, move_type, total in self.env["account.move"].sudo()._read_group(
                [("ocd_ambassador_kind", "!=", False), ("state", "=", "posted"),
                 ("partner_id.ocd_ambassador_id_checked", "=", False),
                 ("partner_id.ocd_ambassador_state", "in", ("active", "closed"))],
                ["partner_id", "move_type"], ["amount_total:sum"],
            ):
                totals[partner] = totals.get(partner, 0.0) + (total if move_type == "in_invoice" else -total)
            money = Dashboard._ocd_money
            for partner, total in totals.items():
                if company.currency_id.compare_amounts(total, company.ocd_ambassador_id_above) <= 0:
                    continue
                items.append({
                    "key": f"ambassador_identity_{partner.id}",
                    "kind": "ambassador_identity",
                    "id": partner.id,
                    "tag": _("Identity to see"),
                    "title": partner.name,
                    "photo": "",
                    "sub": _("%s earned since the start", money(total)),
                    "detail": _("See an identity document in their name before the next payout (once)."),
                    "open_label": _("See the ambassador"),
                    "open_action": Dashboard._ocd_record_action(partner),
                    "ok_label": _("Identity seen"),
                    "reasons": reasons,
                })
        gains = self.env["ocd.ambassador.gain"].search(
            [("return_asked", "=", True), ("state", "in", ("held", "confirmed"))], order="write_date")
        for gain in gains:
            items.append({
                "key": f"ambassador_return_{gain.id}",
                "kind": "ambassador_return",
                "id": gain.id,
                "tag": _("Return asked"),
                "title": f"{gain.ambassador_id.name} · {gain.order_id.name}",
                "photo": "",
                "sub": " · ".join(part for part in (gain.products_label, Dashboard._ocd_money(gain.amount)) if part),
                "detail": _("Already paid: taken from the next payout if the return is made.")
                if gain.state == "confirmed" else _("Not confirmed: it waits for the return."),
                "open_label": _("See the order"),
                "open_action": Dashboard._ocd_record_action(gain.order_id),
                "ok_label": _("Return made: no gain"),
                "refuse_label": _("No return: keep the gain"),
                "reasons": reasons,
            })
        return items

    @api.model
    def _ocd_models(self):
        return {**super()._ocd_models(), "ambassador": "res.partner", "ambassador_identity": "res.partner",
                "ambassador_return": "ocd.ambassador.gain"}

    @api.model
    def ocd_approve(self, kind, record_id, values=None):
        if kind == "ambassador":
            return self._ocd_record(kind, record_id).action_ocd_ambassador_open()
        if kind == "ambassador_identity":
            return self._ocd_record(kind, record_id).action_ocd_ambassador_id_checked()
        if kind == "ambassador_return":
            return self._ocd_record(kind, record_id).action_ocd_return_done()
        return super().ocd_approve(kind, record_id, values)

    @api.model
    def ocd_refuse(self, kind, record_id, reason_id):
        if kind in ("ambassador", "ambassador_identity"):
            reason = self.env["ocd.listing.refuse.reason"].browse(reason_id).exists() if reason_id else None
            return self._ocd_record(kind, record_id).action_ocd_ambassador_close(note=reason.name if reason else None)
        if kind == "ambassador_return":
            return self._ocd_record(kind, record_id).action_ocd_return_refused()
        return super().ocd_refuse(kind, record_id, reason_id)
