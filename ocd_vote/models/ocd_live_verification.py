from odoo import api, models


class OcdLiveVerification(models.AbstractModel):
    """The contests sent by the organisers, the candidates added or changed after the opening, on
    the board of the checks (« To check »)."""

    _inherit = "ocd.live.verification"

    @api.model
    def _ocd_columns(self):
        columns = super()._ocd_columns()
        columns.append({
            "key": "vote",
            "label": self.env._("Contests"),
            "empty": self.env._("No contest waiting."),
            "items": self._ocd_vote_items(),
        })
        return columns

    @api.model
    def _ocd_vote_items(self):
        _ = self.env._
        Dashboard = self.env["ocd.live.dashboard"]
        reasons = self._ocd_reasons("vote")
        items = []
        for contest in self.env["ocd.vote.contest"].search([("state", "=", "to_check")], order="write_date"):
            candidates = contest.candidate_ids.filtered(lambda candidate: candidate.state != "refused")
            items.append({
                "key": f"vote_contest_{contest.id}",
                "kind": "vote_contest",
                "id": contest.id,
                "tag": _("New contest"),
                "title": contest.name,
                "photo": f"/web/image/ocd.vote.contest/{contest.id}/image/256" if contest.image else "",
                "sub": " · ".join(part for part in (
                    contest.organizer_id.name or _("OCD Live"),
                    _("%s candidates", len(candidates)),
                    _("closes %s", contest._ocd_close_text()),
                ) if part),
                "detail": contest.rules or _("No rules written."),
                "open_label": _("See the contest"),
                "open_action": Dashboard._ocd_record_action(contest),
                "ok_label": _("Check and open"),
                "reasons": reasons,
            })
        candidates = self.env["ocd.vote.candidate"].search([
            ("contest_id.state", "in", ("approved", "closed")),
            "|", ("state", "=", "to_check"), ("has_pending", "=", True),
        ], order="write_date")
        for candidate in candidates:
            new = candidate.state == "to_check"
            photo = candidate.pending_photo or candidate.photo
            items.append({
                "key": f"vote_candidate_{candidate.id}",
                "kind": "vote_candidate",
                "id": candidate.id,
                "tag": _("New candidate") if new else _("Candidate changed"),
                "title": f"{candidate._ocd_label()} · {candidate.contest_id.name}",
                "photo": f"/web/image/ocd.vote.candidate/{candidate.id}/"
                         f"{'pending_photo' if candidate.pending_photo else 'photo'}/256" if photo else "",
                "sub": candidate.pending_bio or candidate.bio or "",
                "detail": _("New photo, the old one stays shown until then.") if candidate.pending_photo and not new else "",
                "open_label": False,
                "ok_label": _("Show") if new else _("Accept the change"),
                "reasons": reasons,
            })
        return items

    @api.model
    def _ocd_models(self):
        return {**super()._ocd_models(), "vote_contest": "ocd.vote.contest", "vote_candidate": "ocd.vote.candidate"}

    @api.model
    def ocd_approve(self, kind, record_id, values=None):
        if kind in ("vote_contest", "vote_candidate"):
            return self._ocd_record(kind, record_id).action_ocd_approve()
        return super().ocd_approve(kind, record_id, values)

    @api.model
    def ocd_refuse(self, kind, record_id, reason_id):
        if kind in ("vote_contest", "vote_candidate"):
            reason = self.env["ocd.listing.refuse.reason"].browse(reason_id).exists()
            return self._ocd_record(kind, record_id).action_ocd_refuse(reason)
        return super().ocd_refuse(kind, record_id, reason_id)
