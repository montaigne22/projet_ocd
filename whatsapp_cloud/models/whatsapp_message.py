import json
import logging
import mimetypes
from datetime import UTC, datetime

from markupsafe import Markup

from odoo import Command, _, api, fields, models

from odoo.addons.mail.tools.discuss import Store
from odoo.addons.whatsapp_cloud import const
from odoo.addons.whatsapp_cloud.models.whatsapp_account import WhatsAppApiError

_logger = logging.getLogger(__name__)


class WhatsappMessage(models.Model):
    _name = "whatsapp.message"
    _description = "WhatsApp Message"
    _order = "id desc"
    _rec_name = "phone"

    account_id = fields.Many2one(
        comodel_name="whatsapp.account", string="Account", required=True, index=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(related="account_id.company_id", store=True)
    template_id = fields.Many2one(
        comodel_name="whatsapp.template", string="Template", index="btree_not_null",
        ondelete="set null",
    )
    direction = fields.Selection(
        selection=[("outgoing", "Sent"), ("incoming", "Received")],
        required=True,
        default="outgoing",
    )
    message_type = fields.Selection(
        selection=[
            ("template", "Template"),
            ("text", "Text"),
            ("image", "Image"),
            ("audio", "Audio"),
            ("video", "Video"),
            ("document", "Document"),
            ("sticker", "Sticker"),
            ("location", "Location"),
            ("contacts", "Contacts"),
            ("reaction", "Reaction"),
            ("interactive", "Interactive"),
            ("button", "Button"),
            ("order", "Order"),
            ("system", "System"),
            ("unsupported", "Not supported"),
        ],
        string="Type",
        default="template",
        required=True,
    )
    state = fields.Selection(
        selection=[
            ("queued", "To send"),
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("read", "Read"),
            ("failed", "Failed"),
            ("skipped", "Not sent"),
            ("received", "Received"),
        ],
        required=True,
        default="queued",
        index=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Contact", index="btree_not_null", ondelete="set null"
    )
    phone = fields.Char(string="Number", help="Number in international format, without +.")
    user_ref = fields.Char(
        string="WhatsApp User ID",
        help="ID of the customer for the company at WhatsApp (BSUID), given by Meta also when "
        "the customer hides their number behind a WhatsApp username.",
    )
    model = fields.Char(string="Document Model", index=True)
    res_id = fields.Many2oneReference(string="Document", model_field="model", index=True)
    record_name = fields.Char(string="Document Name", compute="_compute_record_name")
    channel_id = fields.Many2one(
        comodel_name="discuss.channel", string="Conversation", index="btree_not_null",
        ondelete="set null",
    )
    mail_message_id = fields.Many2one(
        comodel_name="mail.message", string="Discussion Message", index="btree_not_null",
        ondelete="set null",
    )
    parent_id = fields.Many2one(
        comodel_name="whatsapp.message", string="Reply to", index="btree_not_null",
        ondelete="set null",
    )
    body = fields.Text(string="Message")
    payload = fields.Text(groups="base.group_system")
    attachment_id = fields.Many2one(comodel_name="ir.attachment", ondelete="set null")
    wa_message_id = fields.Char(string="WhatsApp ID", readonly=True)
    error = fields.Text(readonly=True)
    error_code = fields.Integer(readonly=True)
    error_help = fields.Char(string="What to Do", compute="_compute_error_help")
    attempts = fields.Integer(readonly=True)
    sent_date = fields.Datetime(readonly=True)
    delivered_date = fields.Datetime(readonly=True)
    read_date = fields.Datetime(readonly=True)
    pricing_category = fields.Char(
        readonly=True, help="Pricing category of the message at Meta (utility, marketing, service...)."
    )
    read_receipt = fields.Selection(
        selection=[("todo", "To send"), ("typing", "To send, typing"), ("done", "Sent")],
        readonly=True,
        index="btree_not_null",
        help="Read receipt of a received message, sent to the customer when an agent reads it.",
    )

    _wa_message_id_uniq = models.UniqueIndex(
        "(account_id, wa_message_id) WHERE wa_message_id IS NOT NULL",
        "This WhatsApp message already exists.",
    )

    @api.depends("model", "res_id")
    def _compute_record_name(self):
        for message in self:
            record = message._get_record()
            message.record_name = record.display_name if record else False

    @api.depends("error_code")
    def _compute_error_help(self):
        for message in self:
            text = const.ERROR_HELP.get(message.error_code)
            message.error_help = str(text) if text else False

    def _get_record(self):
        self.ensure_one()
        if not self.model or not self.res_id or self.model not in self.env:
            return None
        return self.env[self.model].sudo().browse(self.res_id).exists() or None

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)
        messages.filtered(
            lambda m: m.direction == "outgoing" and m.state == "queued" and not m.mail_message_id
        )._post_in_conversation()
        return messages

    # === SENDING === #

    @api.model
    def _cron_send_queued(self, batch_size=50):
        """Send the queued messages and read receipts, oldest first, committing after each."""
        receipts = self.search([("read_receipt", "in", ("todo", "typing"))], order="id", limit=100)
        for message in receipts:
            message._send_read_receipt()
            self.env["ir.cron"]._commit_progress()
        messages = self.search([("state", "=", "queued")], order="id", limit=batch_size)
        self.env["ir.cron"]._commit_progress(remaining=len(messages))
        for message in messages:
            message._send()
            if not self.env["ir.cron"]._commit_progress(1):
                break
        if self.search_count([
            "|", ("read_receipt", "in", ("todo", "typing")),
            "&", ("state", "=", "queued"), ("attempts", "=", 0),
        ], limit=1):
            self._trigger_send()

    @api.model
    def _trigger_send(self):
        self.env.ref("whatsapp_cloud.ir_cron_send_queued_messages").sudo()._trigger()

    def _send(self):
        """Send the message to Meta (after uploading its media, if any)."""
        self.ensure_one()
        if self.state != "queued":
            return
        account = self.account_id
        payload = json.loads(self.sudo().payload or "{}")
        if payload.get("type") == "template" and not self._make_header_document():
            return
        try:
            if self.attachment_id and payload.get("type") == "template":
                media_id = account._upload_media(self.attachment_id.sudo())
                header = {
                    "type": "header",
                    "parameters": [{
                        "type": "document",
                        "document": {"id": media_id, "filename": self.attachment_id.name},
                    }],
                }
                payload["template"]["components"] = [
                    header, *payload["template"].get("components", [])
                ]
            elif self.attachment_id and payload.get("type") in const.MEDIA_TYPES:
                media_type = payload["type"]
                payload[media_type]["id"] = account._upload_media(self.attachment_id.sudo())
            result = account._api_request(
                "POST", f"{account.phone_number_id}/messages", json=payload
            )
        except WhatsAppApiError as error:
            attempts = self.attempts + 1
            if error.retryable and attempts < const.MAX_ATTEMPTS:
                self.write({"attempts": attempts, "error": str(error), "error_code": error.code})
            else:
                self.write({
                    "attempts": attempts, "state": "failed", "error": str(error),
                    "error_code": error.code,
                })
                self._notify_failure()
            return
        self.write({
            "attempts": self.attempts + 1,
            "state": "sent",
            "error": False,
            "error_code": False,
            "sent_date": fields.Datetime.now(),
            "wa_message_id": result.get("messages", [{}])[0].get("id"),
        })
        self._bus_send_status()
        if not self.channel_id and self.model != "discuss.channel":
            self._log_on_record(_("WhatsApp message sent to +%s:", self.phone), self.body)

    def _make_header_document(self):
        """Make the PDF of the header of the template (quotation, ticket...) just before
        sending it: the business flows never wait for the PDF engine. Return False when it
        cannot be made now: the message says why, is tried again by the next sending, then
        fails and the users are told."""
        self.ensure_one()
        template = self.template_id
        if self.attachment_id or template.header_type != "document" or not template.header_report_id:
            return True
        record = self._get_record()
        if record is None:
            error = _("The document of the message no longer exists.")
        else:
            try:
                with self.env.cr.savepoint():
                    attachment = template._render_document(record)
            except Exception as exc:  # noqa: BLE001 - the PDF engine fails in many ways
                _logger.warning("WhatsApp: PDF of the message %s not made: %s", self.id, exc)
                error = _("The PDF of the message could not be made: %s", exc)
            else:
                self.attachment_id = attachment
                if self.mail_message_id and self.channel_id:
                    # The team sees in the conversation the PDF that the customer receives
                    attachment.write({"res_model": "discuss.channel", "res_id": self.channel_id.id})
                    self.mail_message_id.attachment_ids = [Command.link(attachment.id)]
                return True
        attempts = self.attempts + 1
        if record is not None and attempts < const.MAX_ATTEMPTS:
            self.write({"attempts": attempts, "error": error})
        else:
            self.write({"attempts": attempts, "state": "failed", "error": error})
            self._notify_failure()
        return False

    def _notify_failure(self):
        """Tell the users that the message did not reach the customer, and why."""
        for message in self:
            reason = message.error or ""
            if message.error_help:
                reason = f"{reason} {message.error_help}".strip()
            message._bus_send_status()
            if message.channel_id:
                message.channel_id._whatsapp_notify(
                    _("Message not delivered to the customer: %s", reason)
                )
            if message.model != "discuss.channel":
                message._log_on_record(_("WhatsApp message not sent: %s", reason))

    def _send_read_receipt(self):
        """Blue ticks for the customer (and "typing..." while the agent writes)."""
        self.ensure_one()
        typing = self.read_receipt == "typing"
        self.read_receipt = "done"
        if not self.wa_message_id:
            return
        try:
            self.account_id._send_read_receipt(self.wa_message_id, typing=typing)
        except WhatsAppApiError as error:
            _logger.info("WhatsApp: read receipt of %s not sent: %s", self.wa_message_id, error)

    def _log_on_record(self, title, body=None):
        """Note in the chatter of the document (or of the contact)."""
        self.ensure_one()
        record = self._get_record()
        if record is None or not hasattr(record, "message_post") or record._name == "discuss.channel":
            record = self.partner_id.sudo()
        if not record:
            return
        content = Markup("<p>%s</p>") % title
        if body:
            content += Markup("<p>%s</p>") % Markup("<br/>").join(body.splitlines())
        record.message_post(body=content, message_type="comment", subtype_xmlid="mail.mt_note")

    def _post_in_conversation(self):
        """Show the sent templates in the conversation of the customer, when there is one."""
        Channel = self.env["discuss.channel"].sudo()
        context_channel = Channel.browse(self.env.context.get("whatsapp_channel_id")).exists()
        for message in self:
            channel = message.channel_id
            if not channel and context_channel and context_channel.whatsapp_partner_id == message.partner_id:
                channel = context_channel
            if not channel and (message.phone or message.user_ref):
                channel = Channel.search([
                    ("channel_type", "=", "whatsapp"),
                    ("whatsapp_account_id", "=", message.account_id.id),
                    ("whatsapp_number", "=", message.phone) if message.phone
                    else ("whatsapp_user_ref", "=", message.user_ref),
                ], limit=1)
            if channel:
                channel._whatsapp_post_outgoing(message)

    def action_retry(self):
        self.filtered(lambda m: m.state == "failed" and m.direction == "outgoing").write({
            "state": "queued", "attempts": 0, "error": False, "error_code": False,
        })
        self._trigger_send()

    def action_open_record(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.model,
            "res_id": self.res_id,
            "view_mode": "form",
        }

    # === DISCUSS === #

    def _get_discuss_status(self):
        """Status shown on the message in the conversation."""
        self.ensure_one()
        if self.direction == "incoming":
            return False
        return self.state

    def _status_rank(self):
        """Progress of the message, to show the least advanced one of a group."""
        self.ensure_one()
        order = ["failed", "skipped", "queued", "sent", "delivered", "read", "received"]
        return order.index(self.state) if self.state in order else 0

    def _bus_send_status(self):
        """Update the ticks of the messages in the open conversations."""
        for mail_message in self.filtered(lambda m: m.channel_id).mail_message_id:
            siblings = self.sudo().search([("mail_message_id", "=", mail_message.id)])
            message = min(siblings, key=lambda m: m._status_rank()) if siblings else None
            if not message:
                continue
            Store(bus_channel=message.channel_id).add(
                mail_message,
                lambda res, message=message: (
                    res.attr("whatsapp_status", message._get_discuss_status()),
                    res.attr("whatsapp_error", message.error_help or message.error or False),
                ),
            )

    # === WEBHOOK === #

    @api.model
    def _process_status(self, account, status):
        """Update a sent message with a receipt of the webhook (sent, delivered, read, failed)."""
        message = self.search([
            ("account_id", "=", account.id), ("wa_message_id", "=", status.get("id")),
        ], limit=1)
        if not message:
            return
        state = const.STATUS_ALIASES.get(status.get("status"), status.get("status"))
        if (user_ref := status.get("recipient_user_id")) and not message.user_ref:
            message.user_ref = user_ref
            if message.partner_id and not message.partner_id.whatsapp_user_ref:
                message.partner_id.sudo().whatsapp_user_ref = user_ref
        timestamp = int(status.get("timestamp") or 0)
        date = (
            datetime.fromtimestamp(timestamp, UTC).replace(tzinfo=None) if timestamp
            else fields.Datetime.now()
        )
        vals = {}
        if pricing := status.get("pricing") or {}:
            vals["pricing_category"] = " / ".join(filter(None, [
                pricing.get("category"), pricing.get("type"),
            ]))
        if state == "failed":
            error = (status.get("errors") or [{}])[0]
            details = (error.get("error_data") or {}).get("details")
            reason = " ".join(filter(None, [error.get("title") or error.get("message"), details]))
            message.write({**vals, "state": "failed", "error": reason,
                           "error_code": error.get("code") or 0})
            message._notify_failure()
        elif state in const.STATUS_ORDER:
            if state in ("sent", "delivered", "read"):
                vals[f"{state}_date"] = date
            # The receipts can come in any order: never go back (read, then delivered).
            if (
                message.state in const.STATUS_ORDER
                and const.STATUS_ORDER.index(state) > const.STATUS_ORDER.index(message.state)
            ):
                vals["state"] = state
            message.write(vals)
            if "state" in vals:
                message._bus_send_status()

    @api.model
    def _process_incoming(self, account, data, contacts):
        """Store a message of a customer and post it in their conversation."""
        wa_message_id = data.get("id")
        if wa_message_id and self.search_count([
            ("account_id", "=", account.id), ("wa_message_id", "=", wa_message_id),
        ], limit=1):
            return self.browse()  # already received: Meta sends again what was not acknowledged
        # the number is missing when a customer with a WhatsApp username hides it: the
        # BSUID (business-scoped user ID) always identifies them
        number = data.get("from") or ""
        user_ref = data.get("from_user_id") or ""
        profile = next(
            (contact.get("profile") or {} for contact in contacts
             if (number and contact.get("wa_id") == number)
             or (user_ref and contact.get("user_id") == user_ref)),
            {},
        )
        Partner = self.env["res.partner"].sudo()
        Channel = self.env["discuss.channel"].sudo()
        if not account.company_id.whatsapp_conversations:
            return self._process_incoming_without_conversation(account, data, number, user_ref)
        # the customer of the conversation, once known (several contacts can share a number)
        partner = Channel._whatsapp_find(account, number, user_ref).whatsapp_partner_id
        if not partner.active:
            partner = Partner._whatsapp_find(number, user_ref) or Partner._whatsapp_create_unknown(
                number, user_ref, profile, account
            )
        if user_ref and not partner.whatsapp_user_ref:
            partner.whatsapp_user_ref = user_ref
        channel = Channel._whatsapp_get_or_create(account, number, user_ref, partner)
        msg_type = data.get("type") or "unsupported"
        content = self._parse_incoming(account, data, channel)
        parent = self.search([
            ("account_id", "=", account.id),
            ("wa_message_id", "=", (data.get("context") or {}).get("id")),
        ], limit=1) if (data.get("context") or {}).get("id") else self.browse()
        message = self.create({
            "account_id": account.id,
            "direction": "incoming",
            "state": "received",
            "message_type": msg_type if msg_type in dict(self._fields["message_type"].selection)
            else "unsupported",
            "partner_id": partner.id,
            "phone": number,
            "user_ref": user_ref,
            "body": content["text"],
            "wa_message_id": wa_message_id,
            "parent_id": parent.id,
            "channel_id": channel.id,
            "attachment_id": content.get("attachment") and content["attachment"].id,
            "model": parent.model if parent.model and parent.model != "discuss.channel" else False,
            "res_id": parent.res_id if parent.model and parent.model != "discuss.channel" else False,
        })
        channel._whatsapp_receive(message, content)
        record = parent._get_record() if parent else None
        if record is not None and record._name != "discuss.channel" and hasattr(record, "message_post"):
            message._log_on_record(
                _("WhatsApp reply of %(name)s (+%(number)s):",
                  name=partner.display_name, number=number or user_ref),
                content["text"],
            )
        return message

    @api.model
    def _process_incoming_without_conversation(self, account, data, number, user_ref):
        """WhatsApp conversations disabled: the message of the customer is only kept and
        noted on the document they answer, or on their contact. STOP and START still work,
        as required by WhatsApp."""
        partner = self.env["res.partner"].sudo()._whatsapp_find(number, user_ref)
        msg_type = data.get("type") or "unsupported"
        content = self._parse_incoming(account, data, partner or None)
        context_id = (data.get("context") or {}).get("id")
        parent = self.search([
            ("account_id", "=", account.id), ("wa_message_id", "=", context_id),
        ], limit=1) if context_id else self.browse()
        model = parent.model if parent.model and parent.model != "discuss.channel" else False
        message = self.create({
            "account_id": account.id,
            "direction": "incoming",
            "state": "received",
            "message_type": msg_type if msg_type in dict(self._fields["message_type"].selection)
            else "unsupported",
            "partner_id": partner.id,
            "phone": number,
            "user_ref": user_ref,
            "body": content["text"],
            "wa_message_id": data.get("id"),
            "parent_id": parent.id,
            "attachment_id": content.get("attachment") and content["attachment"].id,
            "model": model or ("res.partner" if partner else False),
            "res_id": parent.res_id if model else partner.id,
        })
        if not partner:
            _logger.info("WhatsApp: message of the unknown number %s kept.", number or user_ref)
            return message
        message._log_on_record(
            _("WhatsApp message of %(name)s (+%(number)s):",
              name=partner.display_name, number=number or user_ref),
            content["text"],
        )
        if keyword := partner._whatsapp_apply_subscription_keyword(content["text"]):
            partner.message_post(
                body=_("The contact no longer receives the WhatsApp notifications (STOP).")
                if keyword == "stop"
                else _("The contact receives the WhatsApp notifications again (START)."),
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )
        return message

    @api.model
    def _parse_incoming(self, account, data, channel):
        """What a received message contains, whatever its type.

        :return: dict with ``text`` (readable text of the message), ``attachment`` (the
            downloaded media, if any), ``reply_id`` (ID of the chosen option of an
            interactive message or payload of a template button), ``reaction`` (emoji and
            reacted message ID), ``system`` (change of number) and ``referral`` (ad).
        :rtype: dict
        """
        msg_type = data.get("type")
        content = {"text": "", "attachment": None, "reply_id": None}
        if msg_type == "text":
            content["text"] = (data.get("text") or {}).get("body") or ""
        elif msg_type in const.MEDIA_TYPES:
            media = data.get(msg_type) or {}
            content["text"] = media.get("caption") or ""
            content["attachment"], error = self._download_attachment(
                account, msg_type, media, channel
            )
            if error:
                content["text"] = "\n".join(filter(None, [content["text"], _(
                    "(The %(type)s sent by the customer could not be downloaded: %(error)s)",
                    type=msg_type, error=error,
                )]))
        elif msg_type == "location":
            location = data.get("location") or {}
            link = (
                f"https://maps.google.com/?q={location.get('latitude')},{location.get('longitude')}"
            )
            content["text"] = "\n".join(filter(None, [
                _("📍 Location"), location.get("name"), location.get("address"), link,
            ]))
        elif msg_type == "contacts":
            lines = [_("👤 Contact card")]
            for contact in data.get("contacts") or []:
                name = (contact.get("name") or {}).get("formatted_name") or ""
                phones = ", ".join(phone.get("phone", "") for phone in contact.get("phones") or [])
                lines.append(" ".join(filter(None, [name, phones and f"({phones})"])))
            content["text"] = "\n".join(lines)
        elif msg_type == "reaction":
            reaction = data.get("reaction") or {}
            content["reaction"] = (reaction.get("emoji") or "", reaction.get("message_id"))
            content["text"] = reaction.get("emoji") or _("(reaction removed)")
        elif msg_type == "interactive":
            interactive = data.get("interactive") or {}
            reply = interactive.get(interactive.get("type")) or {}
            content["reply_id"] = reply.get("id")
            content["text"] = reply.get("title") or reply.get("body") or ""
        elif msg_type == "button":
            button = data.get("button") or {}
            content["reply_id"] = button.get("payload")
            content["text"] = button.get("text") or ""
        elif msg_type == "order":
            order = data.get("order") or {}
            lines = [_("🛒 Order from the catalogue")]
            for item in order.get("product_items") or []:
                lines.append(_(
                    "%(quantity)s x %(product)s (%(price)s %(currency)s)",
                    quantity=item.get("quantity"), product=item.get("product_retailer_id"),
                    price=item.get("item_price"), currency=item.get("currency"),
                ))
            if order.get("text"):
                lines.append(order["text"])
            content["text"] = "\n".join(lines)
        elif msg_type == "system":
            system = data.get("system") or {}
            content["system"] = system
            content["text"] = system.get("body") or _("(change of number)")
        else:
            errors = data.get("errors") or [{}]
            content["text"] = _(
                "(Message not supported by WhatsApp Cloud API: %s)",
                errors[0].get("title") or errors[0].get("message") or msg_type,
            )
        if referral := data.get("referral"):
            content["referral"] = referral
        return content

    @api.model
    def _download_attachment(self, account, msg_type, media, channel):
        """The media of a received message as an attachment; (attachment, error)."""
        if not media.get("id"):
            return None, _("no media")
        try:
            raw, mimetype = account._download_media(media["id"], url=media.get("url"))
        except WhatsAppApiError as error:
            return None, str(error)
        mimetype = (mimetype or media.get("mime_type") or "").split(";")[0].strip()
        name = media.get("filename")
        if not name:
            extension = mimetypes.guess_extension(mimetype) or ""
            if mimetype == "audio/ogg":
                extension = ".ogg"
            prefix = _("Voice message") if msg_type == "audio" and media.get("voice") else msg_type
            name = f"{prefix}-{fields.Datetime.now():%Y%m%d-%H%M%S}{extension}"
        attachment = self.env["ir.attachment"].sudo().create({
            "name": name,
            "raw": raw,
            "mimetype": mimetype or "application/octet-stream",
            "res_model": channel._name if channel else "whatsapp.message",
            "res_id": channel.id if channel else 0,
        })
        return attachment, None

    # === OUTGOING FREE-FORM MESSAGES === #

    @api.model
    def _prepare_free_payload(self, number, user_ref=None, *, text=None, attachment=None,
                              caption=None, context_id=None, interactive=None, location=None):
        """Body of the request for a message that is not a template (customer service
        window): text, media, interactive message or location (latitude, longitude, name,
        address)."""
        payload = {
            "messaging_product": "whatsapp", "recipient_type": "individual",
            **self._get_recipient_vals(number, user_ref),
        }
        if location:
            payload.update(type="location", location=location)
        elif interactive:
            payload.update(type="interactive", interactive=interactive)
        elif attachment:
            media_type = self._get_media_type(attachment)
            media = {"id": False}
            if media_type == "document":
                media["filename"] = attachment.name
            if caption and media_type in const.CAPTION_TYPES:
                media["caption"] = caption[:const.MAX_CAPTION]
            payload.update(type=media_type, **{media_type: media})
        else:
            payload.update(type="text", text={
                "body": text[:const.MAX_TEXT_BODY], "preview_url": "http" in text,
            })
        if context_id:
            payload["context"] = {"message_id": context_id}
        return payload

    @api.model
    def _get_recipient_vals(self, number, user_ref=None):
        """Recipient of a message: the number, with its "+" as advised by Meta (without it,
        the country code of the company's number may be added), else the BSUID."""
        if number:
            return {"to": f"+{number}"}
        return {"recipient": user_ref}

    @api.model
    def _get_media_type(self, attachment):
        """The WhatsApp type to send a file as: the documents for all that WhatsApp would refuse
        as image, audio or video (format, size)."""
        mimetype = (attachment.mimetype or "").split(";")[0]
        media_type = const.MEDIA_TYPE_BY_MIMETYPE.get(mimetype, "document")
        if (attachment.file_size or 0) > const.MAX_MEDIA_SIZE_BY_TYPE[media_type]:
            media_type = "document"
        return media_type
