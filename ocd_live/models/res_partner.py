import re
import secrets
from datetime import timedelta

import pytz

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import consteq
from odoo.tools.misc import hmac

from .. import tools

LOGIN_CODE_MINUTES = 10
LOGIN_CODE_MAX_ATTEMPTS = 5


class ResPartner(models.Model):
    _inherit = "res.partner"

    ocd_is_vendor = fields.Boolean(string="OCD Vendor", index=True)
    ocd_business = fields.Char(string="Business", help="What the vendor sells, in a few words.")
    ocd_category_id = fields.Many2one(
        comodel_name="ocd.live.category", string="Live Category", index="btree_not_null"
    )
    ocd_vendor_checked_at = fields.Datetime(string="Vendor Checked At", copy=False, readonly=True)
    ocd_vendor_state = fields.Selection(
        selection=[("to_check", "To check"), ("approved", "Approved"), ("refused", "Refused")],
        string="Vendor Status",
        default="to_check",
        tracking=True,
        help="A vendor is shown on the website once approved by the team.",
    )
    ocd_phone_tz = fields.Char(
        string="Time Zone Of The Phone",
        readonly=True,
        copy=False,
        help="Time zone of the phone of the vendor or of the courier, read by the website: the "
        "hours of their pages and of their messages follow it.",
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
    ocd_whatsapp_optin = fields.Boolean(
        string="Messages On WhatsApp",
        default=True,
        help="The vendor receives the ticket, the reminders and the news on WhatsApp.",
    )
    ocd_login_code_hash = fields.Char(copy=False, groups="base.group_system")
    ocd_login_code_expiry = fields.Datetime(copy=False, groups="base.group_system")
    ocd_login_code_attempts = fields.Integer(copy=False, groups="base.group_system")
    # Last link asked with the number on a login page (one a minute at most)
    ocd_link_sent_at = fields.Datetime(copy=False, groups="base.group_system")

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

    # === WHATSAPP CONSENT === #

    def _ocd_whatsapp_consent(self):
        """Whether the contact agreed to the messages of OCD Live on WhatsApp (tickets,
        reminders, news). Extended by ocd_live_whatsapp, where the consent is the one of
        WhatsApp (also changed by STOP and START)."""
        self.ensure_one()
        return self.ocd_whatsapp_optin

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

    def _ocd_tz_name(self):
        """Time zone of the vendor or of the courier: the one of their phone (read by the
        website), else the one of their country, else the one written on the contact, else the
        one of the studio. Their hours are shown in it, on the pages and in the messages."""
        self.ensure_one()
        tz = tools.valid_tz(self.ocd_phone_tz)
        if tz:
            return tz
        code = (self.country_id.code or "").upper()
        if code and code in pytz.country_timezones:
            return pytz.country_timezones[code][0]
        company = self.company_id or self.env.company
        return tools.valid_tz(self.tz) or company.ocd_studio_tz or "Africa/Lome"

    def _ocd_to_local(self, value):
        """A naive UTC datetime, in the time zone of the contact (aware)."""
        self.ensure_one()
        return tools.to_tz(value, self._ocd_tz_name())

    def _ocd_zone_text(self):
        """Name of the time zone of the contact: "Heure : Cameroun"."""
        self.ensure_one()
        return tools.zone_text(self.env, self._ocd_tz_name())

    def _ocd_remember_tz(self, tz_name):
        """The phone of the contact gave its time zone (website): kept for the messages."""
        tz = tools.valid_tz(tz_name)
        for partner in self.filtered(lambda partner: tz and partner.ocd_phone_tz != tz):
            partner.sudo().ocd_phone_tz = tz

    def _ocd_shop_path(self):
        """The boutique of the vendor on the website (without the first "/"), or False.
        Extended by ocd_live_shop."""
        self.ensure_one()
        return False

    def _ocd_public_path(self):
        """Public page where friends find the lives of the vendor (without the first "/"): its
        boutique when it has one, else the lives of its country."""
        self.ensure_one()
        code = (self.country_id.code or "").lower()
        return self._ocd_shop_path() or (f"lives/{code}" if code else "lives")

    def _ocd_feed_image(self):
        """Image of the vendor in the lives of the website: its own picture (logo), or False.
        Extended by ocd_live_shop (a picture of its products)."""
        self.ensure_one()
        return f"/lives/image/{self.id}" if self.image_1920 else False

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
        """Give a new personal link: the old one stops working, and so do the phones where it was
        opened (they ask for the number again)."""
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

    @api.model
    def ocd_choice_descriptions(self, field_name):
        """Return what each choice of `field_name` means, for the choice cards of the forms."""
        return {}

    def _ocd_team_view_signature(self, user_id):
        """Signature of the link « See the space » of this vendor for the person `user_id`."""
        self.ensure_one()
        return hmac(self.env(su=True), "ocd_live.team_view", (user_id, self.id))

    def action_ocd_view_space(self):
        """Open the space of the vendor as the vendor sees it, in a new tab: the team sees the
        lives, the packages and the pass of the vendor, and can act for the vendor."""
        self.ensure_one()
        if not self.env.user.has_group("ocd_live.group_ocd_live_user"):
            raise AccessError(self.env._("Only the team of OCD Live can see the space of a vendor."))
        if not self.ocd_is_vendor:
            raise UserError(self.env._("%s is not a vendor: there is no space to see.", self.display_name))
        signature = self._ocd_team_view_signature(self.env.uid)
        return {
            "type": "ir.actions.act_url",
            "url": f"/ocd/espace/equipe/{self.id}?signature={signature}",
            "target": "new",
        }

    def action_ocd_open_whatsapp(self):
        """Open a WhatsApp conversation with the contact."""
        self.ensure_one()
        digits = re.sub(r"\D", "", self.phone or "")
        if not digits:
            raise UserError(self.env._("Add the WhatsApp number of %s first.", self.name))
        return {"type": "ir.actions.act_url", "url": f"https://wa.me/{digits}", "target": "new"}

    def action_ocd_approve_vendor(self):
        self.write({"ocd_vendor_state": "approved", "ocd_vendor_checked_at": fields.Datetime.now()})
        return True

    def action_ocd_refuse_vendor(self, reason=None):
        self.write({"ocd_vendor_state": "refused", "ocd_vendor_checked_at": fields.Datetime.now()})
        if reason:
            for vendor in self:
                vendor.message_post(body=self.env._("Vendor refused: %s", reason.name))
        return True

    # === LOGIN WITH A CODE OR A PASSWORD === #

    @api.model
    def _ocd_find_by_phone(self, phone, domain):
        """Return the contact of `domain` whose phone number ends like `phone` (8 digits at
        least), for the login pages."""
        typed = re.sub(r"\D", "", phone or "")
        if len(typed) < 8:
            return self.browse()
        # sudo: login page, the number is only compared, nothing is shown
        partners = self.sudo().search(domain + [("phone", "!=", False)])
        for partner in partners:
            stored = re.sub(r"\D", "", partner.phone)
            size = min(len(stored), len(typed))
            if size >= 8 and stored[-size:] == typed[-size:]:
                return partner
        return self.browse()

    @api.model
    def _ocd_find_vendor_by_phone(self, phone):
        """Return the vendor whose phone number ends like `phone` (8 digits at least)."""
        return self._ocd_find_by_phone(phone, [("ocd_is_vendor", "=", True), ("ocd_vendor_state", "!=", "refused")])

    def _ocd_may_send_link(self):
        """A link asked with the number on a login page goes at most once a minute: nobody can
        flood a number with messages (each one may be paid to WhatsApp)."""
        self.ensure_one()
        partner_sudo = self.sudo()
        now = fields.Datetime.now()
        if partner_sudo.ocd_link_sent_at and partner_sudo.ocd_link_sent_at > now - timedelta(minutes=1):
            return False
        partner_sudo.ocd_link_sent_at = now
        return True

    def _ocd_hash_login_code(self, code):
        self.ensure_one()
        return hmac(self.env(su=True), "ocd_live-login-code", f"{self.id}:{code}")

    def _ocd_send_login_code(self):
        """Create a 6-digit login code and send it to the vendor. Return False when a code was
        sent less than a minute ago or when it cannot be sent."""
        self.ensure_one()
        # sudo: the code fields are restricted to administrators
        partner_sudo = self.sudo()
        now = fields.Datetime.now()
        last_expiry = partner_sudo.ocd_login_code_expiry
        if last_expiry and last_expiry - timedelta(minutes=LOGIN_CODE_MINUTES) > now - timedelta(minutes=1):
            return False
        code = f"{secrets.randbelow(1000000):06d}"
        partner_sudo.write({
            "ocd_login_code_hash": self._ocd_hash_login_code(code),
            "ocd_login_code_expiry": now + timedelta(minutes=LOGIN_CODE_MINUTES),
            "ocd_login_code_attempts": 0,
        })
        return self._ocd_deliver_login_code(code)

    def _ocd_check_login_code(self, code):
        """Check a login code: valid 10 minutes, 5 attempts, used once."""
        self.ensure_one()
        partner_sudo = self.sudo()
        if (
            not partner_sudo.ocd_login_code_hash
            or not partner_sudo.ocd_login_code_expiry
            or partner_sudo.ocd_login_code_expiry < fields.Datetime.now()
            or partner_sudo.ocd_login_code_attempts >= LOGIN_CODE_MAX_ATTEMPTS
        ):
            return False
        if consteq(partner_sudo.ocd_login_code_hash, self._ocd_hash_login_code((code or "").strip())):
            partner_sudo.write({"ocd_login_code_hash": False, "ocd_login_code_expiry": False, "ocd_login_code_attempts": 0})
            return True
        partner_sudo.ocd_login_code_attempts += 1
        return False

    def _ocd_deliver_login_code(self, code):
        """Send the login code to the vendor. Return whether it was sent. Extended by
        ocd_live_whatsapp: without it, the login with a code is not possible."""
        return False

    def _ocd_send_space_link(self):
        """Send the personal link of the space to the vendor. Extended by ocd_live_whatsapp."""
        return False

    def _ocd_send_access_link(self, url):
        """Send the link to choose a password. Extended by ocd_live_whatsapp."""
        return False

    def action_ocd_create_password_access(self):
        """Give the vendor a login with the phone number and a password chosen by the vendor."""
        self.ensure_one()
        if not self.env.user.has_group("ocd_live.group_ocd_live_manager"):
            raise AccessError(self.env._("Only a manager can create the access of a vendor."))
        digits = re.sub(r"\D", "", self.phone or "")
        login = f"+{digits}" if len(digits) >= 8 else self.email
        if not login:
            raise UserError(self.env._("Add the WhatsApp number of the vendor first."))
        # sudo: a manager of OCD Live creates the portal access without being an administrator
        user = self.sudo().with_context(active_test=False).user_ids[:1]
        if not user:
            user = self.env["res.users"].sudo().with_context(no_reset_password=True).create({
                "name": self.name,
                "login": login,
                "partner_id": self.id,
                "group_ids": [Command.set(self.env.ref("base.group_portal").ids)],
            })
        self.sudo().signup_prepare(signup_type="reset")
        url = self.sudo()._get_signup_url()
        sent = self._ocd_send_access_link(url)
        message = (
            self.env._("The link to choose a password was sent on WhatsApp. Login: %s", user.login)
            if sent
            else self.env._("Send this link to the vendor to choose a password (login: %(login)s): %(url)s", login=user.login, url=url)
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"message": message, "type": "success", "sticky": True},
        }
