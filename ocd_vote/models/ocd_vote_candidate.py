from odoo import api, fields, models
from odoo.exceptions import UserError

BIO_MAX = 200


class OcdVoteCandidate(models.Model):
    """A candidate of a contest, with her number. Added by the organiser (or the team); checked
    with the contest before the opening, one by one after it: a new candidate is shown once
    checked, a new photo or a new sentence of a candidate shown waits beside the old one."""

    _name = "ocd.vote.candidate"
    _description = "Candidate Of A Contest"
    _order = "contest_id, number"

    contest_id = fields.Many2one(comodel_name="ocd.vote.contest", required=True, index=True, ondelete="cascade")
    number = fields.Integer(required=True, readonly=True, help="Given in order: never given again in the contest.")
    name = fields.Char(required=True)
    photo = fields.Image(max_width=1024, max_height=1024)
    bio = fields.Char(string="A Sentence", help="An age, a district, why the candidate takes part.")
    city = fields.Char(string="District Or City")
    state = fields.Selection(
        selection=[("to_check", "To check"), ("approved", "Shown"), ("refused", "Refused")],
        required=True, default="to_check", index=True,
    )
    pending_photo = fields.Image(string="New Photo To Check", max_width=1024, max_height=1024, copy=False)
    pending_bio = fields.Char(string="New Sentence To Check", copy=False)
    has_pending = fields.Boolean(compute="_compute_has_pending", store=True)
    refuse_reason = fields.Char(readonly=True, copy=False)
    vote_ids = fields.One2many(comodel_name="ocd.vote", inverse_name="candidate_id", string="Payments")
    vote_count = fields.Integer(string="Votes", compute="_compute_vote_count")

    _unique_number = models.UniqueIndex("(contest_id, number)", "Each candidate has their own number in the contest.")

    @api.depends("pending_photo", "pending_bio")
    def _compute_has_pending(self):
        for candidate in self:
            candidate.has_pending = bool(candidate.pending_photo or candidate.pending_bio)

    @api.depends("vote_ids.state", "vote_ids.votes")
    def _compute_vote_count(self):
        counts = self._ocd_vote_counts()
        for candidate in self:
            candidate.vote_count = counts.get(candidate._origin.id, 0)

    def _ocd_vote_counts(self):
        """{candidate id: paid votes} in one query."""
        if not self.ids:
            return {}
        groups = self.env["ocd.vote"].sudo()._read_group(
            [("candidate_id", "in", self._origin.ids), ("state", "=", "paid")], ["candidate_id"], ["votes:sum"],
        )
        return {candidate.id: votes for candidate, votes in groups}

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            contest = self.env["ocd.vote.contest"].browse(vals["contest_id"])
            last = self.sudo().with_context(active_test=False).search(
                [("contest_id", "=", contest.id)], order="number desc", limit=1,
            )
            vals["number"] = (last.number or 0) + 1
            if "state" not in vals and contest.state == "draft":
                vals["state"] = "to_check"
            vals["bio"] = (vals.get("bio") or "").strip()[:BIO_MAX] or False
        return super().create(vals_list)

    def _ocd_shown(self):
        self.ensure_one()
        return self.state == "approved"

    def _ocd_public_path(self):
        self.ensure_one()
        return f"/vote/{self.contest_id.slug}/{self.number}"

    def _ocd_photo_url(self, field="photo"):
        self.ensure_one()
        stamp = (self.write_date or self.create_date).strftime("%Y%m%d%H%M%S")
        return f"/vote/photo/{self.id}?v={stamp}" if self.photo else False

    def _ocd_label(self):
        """« N° 12 Aïcha Mbappe »."""
        self.ensure_one()
        return f"N° {self.number} {self.name}"

    # === CHANGED BY THE ORGANISER === #

    def _ocd_organizer_change(self, values):
        """The organiser changes a candidate: before the opening, at once (checked with the
        contest); after it, a new photo or sentence waits for the team, the name stays (the
        voters know her by it)."""
        self.ensure_one()
        contest = self.contest_id
        if contest.state in ("closed", "done", "cancelled"):
            raise UserError(self.env._("The votes are closed: the candidates no longer change."))
        candidate = self.sudo()
        if contest.state in ("draft", "to_check") or candidate.state == "to_check":
            candidate.write({key: value for key, value in values.items() if key in ("name", "photo", "bio", "city")})
            return
        pending = {}
        if values.get("photo"):
            pending["pending_photo"] = values["photo"]
        bio = (values.get("bio") or "").strip()[:BIO_MAX]
        if bio and bio != candidate.bio:
            pending["pending_bio"] = bio
        if values.get("city") is not None:
            candidate.city = values["city"]
        if pending:
            candidate.write(pending)

    # === THE CHECK OF THE TEAM === #

    def action_ocd_approve(self):
        for candidate in self.sudo():
            values = {"state": "approved", "refuse_reason": False, "pending_photo": False, "pending_bio": False}
            if candidate.pending_photo:
                values["photo"] = candidate.pending_photo
            if candidate.pending_bio:
                values["bio"] = candidate.pending_bio
            candidate.write(values)
        return True

    def action_ocd_refuse(self, reason=None):
        """A new candidate is refused; a change of a candidate shown is dropped (she stays as she was)."""
        text = (reason.message or reason.name) if reason else False
        for candidate in self.sudo():
            if candidate.state == "to_check":
                candidate.write({"state": "refused", "refuse_reason": text})
            else:
                candidate.write({"pending_photo": False, "pending_bio": False, "refuse_reason": text})
        return True
