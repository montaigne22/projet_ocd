import re

from odoo import _, api, fields, models

from odoo.addons.whatsapp_cloud import const
from odoo.addons.whatsapp_cloud.tools import normalize_keyword


class ResPartner(models.Model):
    _inherit = "res.partner"

    whatsapp_opt_in = fields.Boolean(
        string="WhatsApp Notifications",
        tracking=True,
        help="The contact agreed to receive notifications (orders, deliveries...) on WhatsApp.",
    )
    whatsapp_opt_out = fields.Boolean(
        string="Refused WhatsApp Notifications",
        readonly=True,
        copy=False,
        help="The contact refused the WhatsApp notifications (box unticked, or STOP answered): "
        "the consent box is no longer ticked by default for them.",
    )
    whatsapp_user_ref = fields.Char(
        string="WhatsApp User ID",
        copy=False,
        index="btree_not_null",
        help="ID of the contact for the company at WhatsApp (BSUID), given by Meta: it "
        "identifies the contacts who hide their number behind a WhatsApp username.",
    )
    whatsapp_username = fields.Char(string="WhatsApp Username", copy=False)
    whatsapp_to_identify = fields.Boolean(
        string="WhatsApp Number to Identify",
        copy=False,
        help="Contact created for an unknown number that wrote on WhatsApp: associate it with "
        "the right contact, or confirm it.",
    )
    whatsapp_message_ids = fields.One2many(
        comodel_name="whatsapp.message", inverse_name="partner_id", string="WhatsApp Messages"
    )
    whatsapp_message_count = fields.Integer(compute="_compute_whatsapp_message_count")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "whatsapp_opt_in" in vals:
                vals["whatsapp_opt_out"] = not vals["whatsapp_opt_in"]
        return super().create(vals_list)

    def write(self, vals):
        if "whatsapp_opt_in" in vals:
            vals = {**vals, "whatsapp_opt_out": not vals["whatsapp_opt_in"]}
        return super().write(vals)

    def _compute_whatsapp_message_count(self):
        counts = dict(self.env["whatsapp.message"]._read_group(
            [("partner_id", "in", self.ids)], ["partner_id"], ["__count"]
        ))
        for partner in self:
            partner.whatsapp_message_count = counts.get(partner, 0)

    def action_open_whatsapp_messages(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("WhatsApp Messages"),
            "res_model": "whatsapp.message",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
        }

    def _whatsapp_number(self):
        """WhatsApp number of the contact: international format, digits only (2376...)."""
        self.ensure_one()
        country = (
            self.country_id or self.commercial_partner_id.country_id or self.env.company.country_id
        )
        for fname in ("phone", "mobile"):
            if fname in self._fields:
                if number := self._whatsapp_normalize_number(self[fname], country):
                    return number
        return False

    @api.model
    def _whatsapp_normalize_number(self, number, country=None):
        """International number, digits only, as expected by WhatsApp; False if not valid.

        Uses the ``phonenumbers`` library when installed; without it, a number with no
        country code gets the one of the country (670000000 in Cameroon: 237670000000).
        """
        if not number:
            return False
        number = number.strip()
        if country:
            number = self._phone_format_number(number, country, force_format="E164") or number
        digits = re.sub(r"\D", "", number)
        if not number.startswith("+") and digits.startswith("00"):
            digits = digits[2:]
        elif not number.startswith("+") and country and country.phone_code:
            code = str(country.phone_code)
            if not (digits.startswith(code) and len(digits) >= len(code) + 8):
                digits = code + digits.lstrip("0")
        return digits if 8 <= len(digits) <= 15 else False

    @api.model
    def _whatsapp_find_by_number(self, number):
        """The contact with this WhatsApp number: an active one first, the one who agreed
        first, else the latest."""
        if not number or len(number) < 8:
            return self.browse()
        partners = self.with_context(active_test=False).search(
            [("phone_mobile_search", "ilike", number[-8:])], order="id desc", limit=50
        ).filtered(lambda partner: partner._whatsapp_number() == number)
        partners = partners.filtered("active") or partners
        return (
            partners.filtered(lambda p: p.whatsapp_opt_in and not p.whatsapp_to_identify)
            or partners.filtered(lambda p: not p.whatsapp_to_identify)
            or partners
        )[:1]

    @api.model
    def _whatsapp_find(self, number, user_ref=None):
        """The contact of a WhatsApp customer: by their WhatsApp user ID, else by number."""
        if user_ref:
            partners = self.with_context(active_test=False).search(
                [("whatsapp_user_ref", "=", user_ref)], order="active desc, id desc", limit=1
            )
            if partners:
                return partners
        return self._whatsapp_find_by_number(number)

    @api.model
    def _whatsapp_create_unknown(self, number, user_ref, profile, account):
        """Contact for a customer who wrote on WhatsApp and matches no contact, named after
        their WhatsApp profile; to identify by the team."""
        username = (profile or {}).get("username")
        return self.sudo().create({
            "name": (profile or {}).get("name") or (f"+{number}" if number else username)
            or user_ref,
            "phone": f"+{number}" if number else False,
            "company_id": False,
            "whatsapp_user_ref": user_ref or False,
            "whatsapp_username": username or False,
            "whatsapp_to_identify": True,
            "lang": account.company_id.partner_id.lang or self.env.lang,
        })

    def _whatsapp_apply_subscription_keyword(self, text):
        """STOP: no more notifications; START: notifications again. Return "stop", "start"
        or None."""
        self.ensure_one()
        keyword = normalize_keyword(text)
        if keyword in const.STOP_KEYWORDS:
            self.sudo().whatsapp_opt_in = False
            return "stop"
        if keyword in const.START_KEYWORDS:
            self.sudo().whatsapp_opt_in = True
            return "start"
        return None

    def action_whatsapp_confirm_contact(self):
        """The contact created for an unknown number is the right one."""
        self.write({"whatsapp_to_identify": False})
