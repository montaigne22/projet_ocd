import json
import logging
from datetime import UTC, datetime

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.whatsapp_cloud.models.whatsapp_account import WhatsAppApiError
from odoo.addons.whatsapp_cloud_call.models.whatsapp_call import format_duration

_logger = logging.getLogger(__name__)


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
        # first Meta: a customer who called the company already allows it (7 days), nothing to ask
        try:
            data = channel._whatsapp_call_permission_read()
        except WhatsAppApiError as error:
            raise UserError(_("Meta does not answer: %s", account._get_error_text(error))) from error
        if channel._whatsapp_call_allowed():
            channel._whatsapp_notify(channel._whatsapp_call_permission_text())
            return True
        if not channel._whatsapp_is_window_open():
            raise UserError(_(
                "More than 24 hours since the last message of the customer: the permission to call "
                "can only be asked in the 24 hours after a message of the customer."
            ))
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
        values = self._whatsapp_call_permission_values(reply)
        if not values:
            return channel
        channel.write(values)
        channel = channel.with_context(lang=account._get_team_lang())
        channel._whatsapp_notify(channel._whatsapp_call_permission_reply_text(reply, values))
        return channel

    def _whatsapp_call_permission_values(self, reply):
        """The permission given by an answer "call_permission_reply" (None: not an answer)."""
        if reply.get("response") == "accept":
            expiration = str(reply.get("expiration_timestamp") or "")
            return {
                "whatsapp_call_permission": "permanent" if reply.get("is_permanent") else "temporary",
                "whatsapp_call_permission_until": (
                    datetime.fromtimestamp(int(expiration), UTC).replace(tzinfo=None)
                    if expiration.isdigit() else False
                ),
            }
        if reply.get("response") == "reject":
            return {"whatsapp_call_permission": "refused", "whatsapp_call_permission_until": False}
        return None

    def _whatsapp_call_permission_reply_text(self, reply, values):
        """The notice of an answer, as it was given (not as it is now: the notice stays)."""
        self.ensure_one()
        automatic = reply.get("response_source") == "automatic"
        permission = values["whatsapp_call_permission"]
        until = values["whatsapp_call_permission_until"]
        if automatic and permission == "refused":
            return self.env._("WhatsApp withdrew the permission to call the customer (calls not answered).")
        if permission == "permanent":
            text = self.env._("The customer allows the company to call them on WhatsApp.")
        elif permission == "temporary" and until:
            text = self.env._(
                "The customer allows the company to call them on WhatsApp until %s.",
                fields.Datetime.context_timestamp(self, until).strftime("%d/%m/%Y %H:%M"),
            )
        elif permission == "refused":
            text = self.env._("The customer does not want to be called on WhatsApp.")
        else:
            text = self._whatsapp_call_permission_text()
        return self.env._("The customer called: %s", text) if automatic else text

    @api.model
    def _whatsapp_call_permission_repair(self):
        """Before 20.0.1.6.0, the answer "call_permission_reply" (sent by Meta when the customer
        calls the company) was posted as a message of the customer without text, shown "This
        message has been deleted". Each of them, found in the notifications of Meta still kept,
        becomes the notice of the permission, at its place; the permission is kept on the
        conversation unless a later answer was read. Return the number of messages repaired."""
        Message = self.env["whatsapp.message"].sudo()
        events = self.env["whatsapp.webhook.event"].sudo().search(
            [("field", "=", "messages"), ("payload", "like", "call_permission_reply")], order="id"
        )
        # conversations where a later answer was read (by this version): their permission stays
        answered = self.sudo().search([("whatsapp_call_permission_reply_id", "!=", False)])
        author = self.env.ref("base.partner_root")
        repaired = 0
        for event in events:
            try:
                value = json.loads(event.payload)
            except ValueError:
                continue
            for data in value.get("messages") or []:
                interactive = data.get("interactive") or {}
                if interactive.get("type") != "call_permission_reply" or not data.get("id"):
                    continue
                wa_message = Message.search([
                    ("account_id", "=", event.account_id.id),
                    ("wa_message_id", "=", data["id"]),
                    ("direction", "=", "incoming"),
                ], limit=1)
                mail = wa_message.mail_message_id
                if not wa_message.channel_id or not mail or mail.message_type == "notification":
                    continue
                reply = interactive.get("call_permission_reply") or {}
                values = self._whatsapp_call_permission_values(reply)
                if not values:
                    continue
                channel = wa_message.channel_id.with_context(lang=event.account_id._get_team_lang())
                if channel not in answered and (
                    channel.whatsapp_call_permission in ("none", False)
                    or values["whatsapp_call_permission"] == "permanent"
                    or (values["whatsapp_call_permission_until"] or datetime.min) > fields.Datetime.now()
                ):
                    channel.write(dict(values, whatsapp_call_permission_reply_id=data["id"]))
                text = channel._whatsapp_call_permission_reply_text(reply, values)
                mail.sudo().write({
                    "body": Markup('<div class="o_mail_notification o_whatsapp_notice">%s</div>') % text,
                    "message_type": "notification",
                    "author_id": author.id,
                })
                wa_message.body = text
                repaired += 1
        if repaired:
            _logger.info("WhatsApp calls: %s permission(s) to call shown as deleted messages, repaired", repaired)
        return repaired

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
