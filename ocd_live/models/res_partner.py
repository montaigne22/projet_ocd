import secrets

from odoo import api, fields, models
from odoo.tools import consteq


class ResPartner(models.Model):
    _inherit = "res.partner"

    ocd_is_vendor = fields.Boolean(string="OCD Vendor", index=True)
    ocd_business = fields.Char(string="Business", help="What the vendor sells, in a few words.")
    ocd_category_id = fields.Many2one(
        comodel_name="ocd.live.category", string="Live Category", index="btree_not_null"
    )
    ocd_vendor_state = fields.Selection(
        selection=[("to_check", "To check"), ("approved", "Approved"), ("refused", "Refused")],
        string="Vendor Status",
        default="to_check",
        tracking=True,
        help="A vendor is shown on the website once approved by the team.",
    )
    ocd_space_token = fields.Char(
        string="Space Token",
        copy=False,
        groups="base.group_system",
        index="btree_not_null",
        help="Secret of the personal link of the vendor. Changing it disables the old link.",
    )
    ocd_booking_ids = fields.One2many(
        comodel_name="ocd.live.booking", inverse_name="partner_id", string="Lives"
    )
    ocd_booking_count = fields.Integer(string="Booked Lives", compute="_compute_ocd_booking_count")
    ocd_credit_ids = fields.One2many(
        comodel_name="ocd.live.credit", inverse_name="partner_id", string="Live Credits"
    )
    ocd_lives_remaining = fields.Integer(
        string="Lives To Place", compute="_compute_ocd_lives_remaining"
    )
    ocd_pass_ids = fields.One2many(
        comodel_name="ocd.directory.pass", inverse_name="partner_id", string="Directory Passes"
    )
    ocd_pass_end_date = fields.Date(string="Pass Valid Until", compute="_compute_ocd_pass")
    ocd_pass_active = fields.Boolean(string="Active Pass", compute="_compute_ocd_pass")
    ocd_listing_ids = fields.One2many(
        comodel_name="ocd.directory.listing", inverse_name="partner_id", string="Directory Links"
    )

    def _compute_ocd_booking_count(self):
        counts = {
            partner.id: count
            for partner, count in self.env["ocd.live.booking"]._read_group(
                [("partner_id", "in", self.ids), ("state", "!=", "cancelled")],
                ["partner_id"],
                ["__count"],
            )
        }
        for partner in self:
            partner.ocd_booking_count = counts.get(partner.id, 0)

    def _compute_ocd_lives_remaining(self):
        credits = self.env["ocd.live.credit"].search(
            [("partner_id", "in", self.ids), ("state", "=", "active")]
        )
        remaining = dict.fromkeys(self.ids, 0)
        for credit in credits:
            remaining[credit.partner_id.id] += credit.remaining
        for partner in self:
            partner.ocd_lives_remaining = remaining.get(partner.id, 0)

    def _compute_ocd_pass(self):
        # Dates are read directly so that the result is right even before the daily cron
        # updates the states of the passes.
        today = fields.Date.context_today(self)
        passes = self.env["ocd.directory.pass"].search(
            [
                ("partner_id", "in", self.ids),
                ("state", "in", ("scheduled", "active")),
                ("date_end", ">=", today),
            ]
        )
        end_by_partner = {}
        active_partner_ids = set()
        for directory_pass in passes:
            partner_id = directory_pass.partner_id.id
            end_by_partner[partner_id] = max(
                end_by_partner.get(partner_id, directory_pass.date_end), directory_pass.date_end
            )
            if directory_pass.date_start <= today:
                active_partner_ids.add(partner_id)
        for partner in self:
            partner.ocd_pass_end_date = end_by_partner.get(partner.id, False)
            partner.ocd_pass_active = partner.id in active_partner_ids

    # === SPACE LINK === #

    def _ocd_get_space_token(self):
        """Return the secret of the personal link of the vendor, created on first use."""
        self.ensure_one()
        # sudo: the token is restricted to administrators, the link is only built server side
        partner_sudo = self.sudo()
        if not partner_sudo.ocd_space_token:
            partner_sudo.ocd_space_token = secrets.token_urlsafe(24)
        return partner_sudo.ocd_space_token

    def _ocd_get_space_url(self):
        self.ensure_one()
        return f"{self.get_base_url()}/ocd/espace/{self._ocd_get_space_token()}"

    @api.model
    def _ocd_find_by_space_token(self, token):
        """Return the vendor whose personal link carries `token`, or an empty recordset."""
        if not token or len(token) < 16:
            return self.browse()
        # sudo: public route, the token is the credential and is compared in constant time
        partner_sudo = self.sudo().search([("ocd_space_token", "=", token)], limit=1)
        if partner_sudo and consteq(partner_sudo.ocd_space_token, token):
            return partner_sudo
        return self.browse()

    def action_ocd_reset_space_link(self):
        """Give the vendor a new personal link: the old one stops working."""
        for partner in self:
            partner.sudo().ocd_space_token = secrets.token_urlsafe(24)
            partner.message_post(body=self.env._("A new personal link was created. The old one no longer works."))
        return True

    def action_ocd_view_bookings(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("ocd_live.ocd_live_booking_action")
        action["domain"] = [("partner_id", "=", self.id)]
        action["context"] = {"default_partner_id": self.id}
        return action

    def action_ocd_view_credits(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("ocd_live.ocd_live_credit_action")
        action["domain"] = [("partner_id", "=", self.id)]
        action["context"] = {"default_partner_id": self.id}
        return action

    def action_ocd_approve_vendor(self):
        self.write({"ocd_vendor_state": "approved"})
        return True

    def action_ocd_refuse_vendor(self):
        self.write({"ocd_vendor_state": "refused"})
        return True
