from datetime import UTC, datetime

from markupsafe import Markup

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.whatsapp_cloud.models.whatsapp_account import WhatsAppApiError
from odoo.addons.whatsapp_cloud_call.models.whatsapp_call import format_duration


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    whatsapp_call_ids = fields.One2many(
        comodel_name="whatsapp.call", inverse_name="channel_id", string="WhatsApp Calls"
    )
    # The customer allows the company to call them on WhatsApp (Meta: asked in the
    # conversation, or given for 7 days when they call the company).
    whatsapp_call_permission = fields.Selection(
        selection=[
            ("none", "Not asked"),
            ("requested", "Asked"),
            ("temporary", "Allowed for a while"),
            ("permanent", "Allowed"),
            ("refused", "Refused"),
        ],
        string="Call Permission", default="none", readonly=True,
    )
    whatsapp_call_permission_until = fields.Datetime(string="Call Permission until", readonly=True)
    whatsapp_call_permission_asked = fields.Datetime(string="Call Permission Asked on", readonly=True)
    # the last answer read (Meta sends a notification again when it was not acknowledged)
    whatsapp_call_permission_reply_id = fields.Char(readonly=True, copy=False)

    # === CALL PERMISSION === #

    def _whatsapp_call_allowed(self):
        """Whether the company may call the customer now."""
        self.ensure_one()
        if self.whatsapp_call_permission == "permanent":
            return True
        return bool(
            self.whatsapp_call_permission == "temporary"
            and self.whatsapp_call_permission_until
            and self.whatsapp_call_permission_until > fields.Datetime.now()
        )

    def _whatsapp_call_permission_text(self):
        self.ensure_one()
        until = self.whatsapp_call_permission_until and fields.Datetime.context_timestamp(
            self, self.whatsapp_call_permission_until
        ).strftime("%d/%m/%Y %H:%M")
        if self.whatsapp_call_permission == "permanent":
            return _("The customer allows the company to call them on WhatsApp.")
        if self._whatsapp_call_allowed():
            return _("The customer allows the company to call them on WhatsApp until %s.", until)
        if self.whatsapp_call_permission == "refused":
            return _("The customer does not want to be called on WhatsApp.")
        if self.whatsapp_call_permission == "requested":
            return _("Permission to call asked, no answer yet.")
        return _("The company may not call the customer on WhatsApp yet: ask them first.")

    def _whatsapp_call_permission_recipient(self):
        self.ensure_one()
        if self.whatsapp_number:
            return {"user_wa_id": self.whatsapp_number}
        return {"recipient": self.whatsapp_user_ref}

    def _whatsapp_call_permission_read(self):
        """The permission and the limits at Meta (GET call_permissions): the permission noted
        on the conversation; returns the answer of Meta."""
        self.ensure_one()
        account = self.whatsapp_account_id
        data = account._api_request(
            "GET", f"{account.phone_number_id}/call_permissions",
            params=self._whatsapp_call_permission_recipient(),
        )
        permission = data.get("permission") or {}
        status = permission.get("status")
        expiration = permission.get("expiration_time") or permission.get("expiration")
        if status == "permanent":
            self.whatsapp_call_permission = "permanent"
        elif status == "temporary" and str(expiration or "").isdigit():
            self.write({
                "whatsapp_call_permission": "temporary",
                "whatsapp_call_permission_until": datetime.fromtimestamp(int(expiration), UTC).replace(tzinfo=None),
            })
        elif status == "no_permission" and self._whatsapp_call_allowed():
            self.whatsapp_call_permission = "none"
        return data

    def whatsapp_action_call_permission_request(self):
        """Ask the customer, in the conversation, whether the company may call them (message of
        Meta with the buttons Allow and Decline; within 24 hours of their last message)."""
        self._whatsapp_check_agent()
        self.ensure_one()
        channel = self.sudo()
        account = channel.whatsapp_account_id
        if not account.call_enabled:
            raise UserError(_("The calls are not enabled on this WhatsApp account (Calls tab)."))
        if not channel._whatsapp_is_window_open():
            raise UserError(_(
                "More than 24 hours since the last message of the customer: the permission to call "
                "can only be asked in the 24 hours after a message of the customer."
            ))
        try:
            data = channel._whatsapp_call_permission_read()
        except WhatsAppApiError as error:
            raise UserError(_("Meta does not answer: %s", account._get_error_text(error))) from error
        if channel._whatsapp_call_allowed():
            channel._whatsapp_notify(channel._whatsapp_call_permission_text())
            return True
        action = next(
            (a for a in data.get("actions") or [] if a.get("action_name") == "send_call_permission_request"),
            {},
        )
        if action and not action.get("can_perform_action", True):
            raise UserError(_(
                "Meta allows 1 request to call a customer per 24 hours, and 2 per 7 days: try "
                "again later (the limits restart after a call between the customer and the company)."
            ))
        lang = channel._whatsapp_get_lang()
        text = channel.with_context(lang=lang).env._(
            "May %(company)s call you on WhatsApp? It is about your request.",
            company=account.company_id.name,
        )
        message = channel.with_context(whatsapp_skip_send=True).message_post(
            author_id=self.env.user.partner_id.id,
            body=Markup("<p>%s</p>") % text,
            message_type="whatsapp_message",
            subtype_xmlid="mail.mt_comment",
        )
        channel._whatsapp_send_mail_message(message, text=text, interactive={
            "type": "call_permission_request",
            "action": {"name": "call_permission_request"},
            "body": {"text": text},
        })
        channel.write({
            "whatsapp_call_permission": "requested",
            "whatsapp_call_permission_asked": fields.Datetime.now(),
        })
        return True

    def _whatsapp_call_permission_reply(self, account, data):
        """The answer of the customer to a request to call them, or the permission given
        when they call the company (Meta: interactive "call_permission_reply")."""
        number = data.get("from") or ""
        user_ref = data.get("from_user_id") or ""
        channel = self.sudo()._whatsapp_find(account, number, user_ref)
        if not channel:
            Partner = self.env["res.partner"].sudo()
            partner = Partner._whatsapp_find(number, user_ref) or Partner._whatsapp_create_unknown(
                number, user_ref, {}, account
            )
            channel = self.sudo()._whatsapp_get_or_create(account, number, user_ref, partner)
        if data.get("id") and channel.whatsapp_call_permission_reply_id == data["id"]:
            return channel
        channel.whatsapp_call_permission_reply_id = data.get("id") or False
        reply = (data.get("interactive") or {}).get("call_permission_reply") or {}
        automatic = reply.get("response_source") == "automatic"
        if reply.get("response") == "accept":
            expiration = str(reply.get("expiration_timestamp") or "")
            channel.write({
                "whatsapp_call_permission": "permanent" if reply.get("is_permanent") else "temporary",
                "whatsapp_call_permission_until": (
                    datetime.fromtimestamp(int(expiration), UTC).replace(tzinfo=None)
                    if expiration.isdigit() else False
                ),
            })
        elif reply.get("response") == "reject":
            channel.write({"whatsapp_call_permission": "refused", "whatsapp_call_permission_until": False})
        else:
            return channel
        channel = channel.with_context(lang=account._get_team_lang())
        text = channel._whatsapp_call_permission_text()
        if automatic and reply.get("response") == "reject":
            text = channel.env._("WhatsApp withdrew the permission to call the customer (calls not answered).")
        elif automatic:
            text = channel.env._("The customer called: %s", text)
        channel._whatsapp_notify(text)
        return channel

    # === CALLING THE CUSTOMER === #

    def whatsapp_action_call(self):
        """Call the customer through WhatsApp from the phone of the top bar (a call of the
        company, paid): Meta must allow it (permission of the customer, limits). The call is
        prepared here, the phone of the agent places it, the call server checks it with Odoo."""
        self._whatsapp_check_agent()
        self.ensure_one()
        user = self.env.user
        channel = self.sudo()
        account = channel.whatsapp_account_id
        if not account.call_enabled or not account.sudo().call_sip_password:
            raise UserError(_("The calls are not enabled on this WhatsApp account (Calls tab)."))
        if user.sudo()._whatsapp_call_softphone() is None:
            raise UserError(_("You do not take the WhatsApp calls of this account (Team tab)."))
        if not channel.whatsapp_number:
            raise UserError(_(
                "The customer hides their number behind a WhatsApp username: the company cannot "
                "call them."
            ))
        try:
            data = channel._whatsapp_call_permission_read()
        except WhatsAppApiError as error:
            raise UserError(_("Meta does not answer: %s", account._get_error_text(error))) from error
        start = next((a for a in data.get("actions") or [] if a.get("action_name") == "start_call"), {})
        if not start.get("can_perform_action"):
            if not channel._whatsapp_call_allowed():
                raise UserError(_(
                    "The customer did not allow the company to call them on WhatsApp: ask them "
                    "first (Ask to call them)."
                ))
            raise UserError(_(
                "Meta does not allow more calls to this customer for now (limit of calls): try "
                "again later."
            ))
        call = self.env["whatsapp.call"].sudo().create({
            "account_id": account.id,
            "direction": "outbound",
            "channel_id": channel.id,
            "partner_id": channel.whatsapp_partner_id.id,
            "number": channel.whatsapp_number,
            "user_ref": channel.whatsapp_user_ref or False,
            "user_id": user.id,
            "in_hours": account._is_open(),
        })
        return {
            "type": "ir.actions.client",
            "tag": "whatsapp_call_dial",
            "params": {
                "call_id": call.id,
                "name": channel.whatsapp_partner_id.display_name or f"+{channel.whatsapp_number}",
                "number": f"+{channel.whatsapp_number}",
            },
        }

    # === INFORMATION PANEL === #

    def _whatsapp_get_info_sections(self):
        """The permission to call the customer, and their last calls, next to the conversation."""
        sections = super()._whatsapp_get_info_sections()
        if self.whatsapp_account_id.call_enabled:
            sections.append({
                "title": _("Calling the Customer"),
                "items": [],
                "empty": self._whatsapp_call_permission_text(),
                "buttons": [{
                    "method": "whatsapp_action_call",
                    "name": _("Call through WhatsApp"),
                }] if self._whatsapp_call_allowed() else [{
                    "method": "whatsapp_action_call_permission_request",
                    "name": _("Ask to call them"),
                }],
            })
        calls = self.env["whatsapp.call"].sudo().search([("channel_id", "=", self.id)], limit=5)
        if calls:
            states = dict(calls._fields["state"]._description_selection(self.env))
            sections.append({
                "title": _("Calls"),
                "items": [
                    {
                        "name": "%s · %s" % (
                            fields.Datetime.context_timestamp(self, call.start_date).strftime("%d/%m %H:%M"),
                            states.get(call.state),
                        ),
                        "detail": " · ".join(filter(None, [
                            call.user_id.name,
                            format_duration(self.env, call.duration) if call.duration else "",
                        ])),
                        "model": "whatsapp.call",
                        "id": call.id,
                    }
                    for call in calls
                ],
            })
        return sections
