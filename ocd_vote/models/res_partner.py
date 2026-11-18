from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    ocd_vote_organizer = fields.Boolean(
        string="Organiser Of Contests",
        help="Logs in with their number on /vote/organisateur, like the vendors: their contests and candidates.",
    )
    ocd_vote_organizer_verified = fields.Boolean(
        string="Organiser Checked",
        help="The team checked the identity and the number of the organiser: « Checked organiser » on their contests.",
    )
    ocd_vote_contest_ids = fields.One2many(
        comodel_name="ocd.vote.contest", inverse_name="organizer_id", string="Contests"
    )

    @api.model
    def _ocd_find_organizer_by_phone(self, phone):
        """The organiser whose number ends like `phone`, for the login page."""
        return self._ocd_find_by_phone(phone, [("ocd_vote_organizer", "=", True)])

    def action_ocd_view_contests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Contests of %s", self.name),
            "res_model": "ocd.vote.contest",
            "view_mode": "list,form",
            "domain": [("organizer_id", "=", self.id)],
            "context": {"default_organizer_id": self.id},
        }
