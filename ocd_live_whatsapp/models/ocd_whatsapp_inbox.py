import logging
import re
from collections import defaultdict
from datetime import timedelta
from urllib.parse import urlencode

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import html2plaintext, plaintext2html
from odoo.tools.misc import format_date, format_datetime

from odoo.addons.whatsapp_cloud.const import WINDOW_URGENT_MINUTES

_logger = logging.getLogger(__name__)

# The conversations shown at first, and added by « Show more », up to LIST_MAX
LIST_LIMIT = 80
LIST_MAX = 2000
LIST_FILTERS = ("all", "waiting", "mine")
MESSAGE_LIMIT = 60
# The secret of a message sent by a template (a delivery code, a login code): hidden from the team
SECRET_RE = re.compile(r"(?<![\w])\d{4,6}(?![\w])")
# Line added by whatsapp_cloud under a template shown in a conversation
TEMPLATE_LINE_RE = re.compile(r"\n*\s*(Template|Modèle)\s*:[^\n]*\s*$")
STATUS_ORDER = ["failed", "skipped", "queued", "sent", "delivered", "read", "received"]
# The calls of a conversation (with whatsapp_cloud_call): the customer did not reach the team
CALL_MISSED_STATES = ("missed", "voicemail", "lost", "failed")
CALL_LAST = 5


class OcdWhatsappInbox(models.AbstractModel):
    """The WhatsApp conversations of the team, as in the validated design (BoWhatsApp): the
    list (all, or waiting for an answer), the conversation with its automatic messages, the
    answers of the team and the internal notes, and the contact on the right with what OCD Live
    knows of them (their order and parcels, their live).

    Built on the conversations of whatsapp_cloud: answering, the 24-hour window, the notes,
    the templates, the consent and the assignment are theirs; the access is theirs too (an
    agent sees the conversations not taken and theirs, a manager all of them). Extended by
    ocd_live_shop_whatsapp (orders and parcels)."""

    _name = "ocd.whatsapp.inbox"
    _description = "WhatsApp Conversations Of OCD Live"

    # === PAGE === #

    @api.model
    def get_inbox(self, channel_id=None, options=None):
        """The page: the list (searched by name or number, filtered: all, waiting for an answer,
        mine; the first LIST_LIMIT, more with « Show more ») and the conversation shown.

        :param dict options: ``search``, ``filter`` (all, waiting, mine) and ``limit`` of the list
        """
        self._ocd_check_agent()
        options = self._ocd_list_options(options)
        Channel = self.env["discuss.channel"]
        domain = [("channel_type", "=", "whatsapp"), *self._ocd_search_domain(options["search"])]
        channels = Channel.search(
            domain + self._ocd_filter_domain(options["filter"]),
            order="last_interest_dt desc, id desc", limit=options["limit"] + 1,
        )
        has_more = len(channels) > options["limit"]
        channels = channels[:options["limit"]]
        last_messages = self._ocd_last_messages(channels)
        rows = [self._ocd_list_item(channel, last_messages.get(channel.id)) for channel in channels]
        rows.sort(key=lambda row: row["sort"], reverse=True)
        counts = {key: Channel.search_count(domain + self._ocd_filter_domain(key)) for key in LIST_FILTERS}
        current = channels.browse()
        if channel_id:
            # the conversation shown stays, even out of the list (another search, more than the limit)
            current = Channel.search([("id", "=", channel_id), ("channel_type", "=", "whatsapp")])
        if not current and rows:
            current = channels.browse(rows[0]["id"])
        return {
            "conversations": rows,
            "waiting": counts["waiting"],
            "counts": counts,
            "has_more": has_more,
            "options": options,
            "account": self._ocd_account_text(),
            "team_channels": self._ocd_team_channels(),
            "current": self._ocd_conversation(current) if current else False,
        }

    @api.model
    def _ocd_list_options(self, options):
        options = options or {}
        try:
            limit = int(options.get("limit") or LIST_LIMIT)
        except (TypeError, ValueError):
            limit = LIST_LIMIT
        return {
            "search": (options.get("search") or "").strip()[:80],
            "filter": options.get("filter") if options.get("filter") in LIST_FILTERS else "all",
            "limit": max(LIST_LIMIT, min(limit, LIST_MAX)),
        }

    @api.model
    def _ocd_search_domain(self, search):
        """The conversations of a contact by their name (or the name of the conversation), or by
        their number, written in any way: « 6 70 00 », « +237 670… »."""
        if not search:
            return []
        domain = ["|", ("whatsapp_partner_id.name", "ilike", search), ("name", "ilike", search)]
        digits = re.sub(r"\D", "", search)
        if len(digits) >= 3:
            domain = ["|", ("whatsapp_number", "ilike", digits), *domain]
        return domain

    @api.model
    def _ocd_filter_domain(self, key):
        if key == "waiting":
            return [("whatsapp_waiting_since", "!=", False), ("whatsapp_state", "!=", "done")]
        if key == "mine":
            return [("whatsapp_user_id", "=", self.env.uid)]
        return []

    @api.model
    def get_conversation(self, channel_id):
        """The conversation, marked as read by the agent who opens it (blue ticks)."""
        channel = self._ocd_channel(channel_id)
        member = channel.self_member_id
        last = channel.message_ids[:1]
        if member and last:
            member._set_last_seen_message(last, notify=False)
        return self._ocd_conversation(channel)

    @api.model
    def ocd_post(self, channel_id, body, note=False, attachment_ids=None, options=None):
        """An answer to the contact (within the 24-hour window), or an internal note, with the
        files added to it (photos, documents, voice messages: uploaded first, then sent)."""
        channel = self._ocd_channel(channel_id)
        text = (body or "").strip()
        attachments = self._ocd_pending_attachments(attachment_ids)
        if not text and not attachments:
            raise UserError(self.env._("Write the message or add a file first."))
        channel.message_post(
            body=plaintext2html(text) if text else "",
            message_type="comment",
            subtype_xmlid="mail.mt_note" if note else "mail.mt_comment",
            attachment_ids=attachments.ids,
        )
        return self.get_inbox(channel.id, options)

    @api.model
    def _ocd_pending_attachments(self, attachment_ids):
        """The files uploaded by the agent for their next message (not posted yet)."""
        Attachment = self.env["ir.attachment"].sudo()
        if not attachment_ids:
            return Attachment
        attachments = Attachment.browse(attachment_ids).exists()
        if len(attachments) != len(set(attachment_ids)) or any(
            attachment.create_uid != self.env.user or attachment.res_model != "mail.compose.message"
            for attachment in attachments
        ):
            raise UserError(self.env._("A file of the message is not available any more: add it again."))
        return attachments

    @api.model
    def ocd_take(self, channel_id, options=None):
        """« Take »: the agent handles the conversation (the other agents leave it)."""
        channel = self._ocd_channel(channel_id)
        channel.whatsapp_action_take()
        return self.get_inbox(channel.id, options)

    @api.model
    def ocd_resolve(self, channel_id, options=None):
        """« Mark as resolved »: nobody waits any more; a new message of the contact opens it again."""
        channel = self._ocd_channel(channel_id)
        channel.whatsapp_action_resolve()
        return self.get_inbox(channel.id, options)

    @api.model
    def ocd_reopen(self, channel_id, options=None):
        channel = self._ocd_channel(channel_id)
        channel.whatsapp_action_reopen()
        return self.get_inbox(channel.id, options)

    @api.model
    def ocd_send_template(self, channel_id, template_id, res_model, res_id, options=None):
        """A template approved by Meta, sent from the conversation (also out of the window)."""
        channel = self._ocd_channel(channel_id)
        choice = next(
            (
                choice for choice in self._ocd_template_choices(channel)
                if choice["template"].id == template_id
                and choice["record"]._name == res_model and choice["record"].id == res_id
            ),
            None,
        )
        if not choice:
            raise UserError(self.env._("This template cannot be sent from this conversation."))
        template = choice["template"].sudo().with_context(whatsapp_channel_id=channel.id)
        messages = template._send(choice["record"].sudo())
        if not messages:
            raise UserError(self.env._("No WhatsApp account is configured."))
        skipped = messages.filtered(lambda message: message.state == "skipped")
        if skipped:
            raise UserError(self.env._("Not sent: %s", skipped[0].error or ""))
        return self.get_inbox(channel.id, options)

    # === ACCESS === #

    @api.model
    def _ocd_check_agent(self):
        if not self.env.user.has_group("whatsapp_cloud.group_whatsapp_user"):
            raise AccessError(self.env._("Only the WhatsApp agents see the conversations."))

    @api.model
    def _ocd_channel(self, channel_id):
        self._ocd_check_agent()
        channel = self.env["discuss.channel"].browse(channel_id).exists()
        if not channel or channel.channel_type != "whatsapp":
            raise UserError(self.env._("This conversation does not exist any more."))
        channel.check_access("read")
        return channel

    # === LIST === #

    @api.model
    def _ocd_last_messages(self, channels):
        if not channels:
            return {}
        groups = self.env["mail.message"].sudo()._read_group(
            [("model", "=", "discuss.channel"), ("res_id", "in", channels.ids),
             ("message_type", "in", ("comment", "whatsapp_message"))],
            ["res_id"], ["id:max"],
        )
        messages = self.env["mail.message"].sudo().browse([message_id for _res_id, message_id in groups])
        return {message.res_id: message for message in messages}

    def _ocd_list_item(self, channel, message):
        partner = channel.whatsapp_partner_id
        name = partner.name or (f"+{channel.whatsapp_number}" if channel.whatsapp_number else channel.name)
        preview = ""
        if message:
            kind = self._ocd_message_kind(channel, message)
            text = self._ocd_message_text(channel, message, kind)
            if message.attachment_ids and text == ", ".join(message.attachment_ids.mapped("name")):
                text = self._ocd_files_preview(message.attachment_ids)
            prefix = {"out": self.env._("You: "), "auto": self.env._("You: "), "note": self.env._("Note: ")}.get(kind, "")
            preview = f"{prefix}{text}"
        date = message.date if message else channel.create_date
        return {
            "id": channel.id,
            "name": name,
            "initials": self._ocd_initials(name),
            "role": self._ocd_partner_role(partner) if partner else self.env._("Unknown number"),
            "vendor": bool(partner and partner.ocd_is_vendor),
            "preview": preview[:120],
            "time": self._ocd_time_label(date),
            "waiting": bool(channel.whatsapp_waiting_since) and channel.whatsapp_state != "done",
            "done": channel.whatsapp_state == "done",
            "mine": channel.whatsapp_user_id == self.env.user,
            # a contact who waits: the time left to answer for free (24-hour window)
            **self._ocd_window_left(channel, list_item=True),
            "sort": (fields.Datetime.to_string(date) if date else "", message.id if message else 0),
        }

    def _ocd_files_preview(self, attachments):
        """A message of files only, in the list: « 🎤 Voice message », « 📷 Photo », else their names."""
        _ = self.env._
        kinds = {(attachment.mimetype or "").split("/")[0] for attachment in attachments}
        if kinds == {"audio"}:
            return "🎤 " + (_("Voice message") if len(attachments) == 1 else _("%s voice messages", len(attachments)))
        if kinds == {"image"}:
            return "📷 " + (_("Photo") if len(attachments) == 1 else _("%s photos", len(attachments)))
        return "📎 " + ", ".join(attachments.mapped("name"))

    def _ocd_window_left(self, channel, list_item=False):
        """The time left to answer the contact for free (the 24-hour window after their last
        message, then only a paid template): « 2 h 15 » in the list for a contact who waits, « Free
        answer for 2 h 15 more (until 14:35) » in the conversation; urgent the last hour."""
        _ = self.env._
        channel = channel.sudo()
        minutes = channel._whatsapp_window_minutes_left()
        urgent = bool(minutes) and minutes < WINDOW_URGENT_MINUTES
        if list_item:
            shown = bool(minutes) and bool(channel.whatsapp_waiting_since)
            return {
                "window_left": channel._whatsapp_duration_text(minutes) if shown else "",
                "window_urgent": shown and urgent,
            }
        if not minutes and not channel._whatsapp_is_window_open():
            return {"window_text": "", "window_urgent": False}
        values = {
            "left": channel._whatsapp_duration_text(minutes),
            "time": channel._whatsapp_window_end_text(tz=self.env.user.tz),
        }
        return {
            "window_text": _("Only %(left)s left to answer for free (until %(time)s)", **values) if urgent
            else _("Free answer for %(left)s more (until %(time)s)", **values),
            "window_urgent": urgent,
        }

    # === CONVERSATION === #

    def _ocd_conversation(self, channel):
        channel = channel.sudo()
        _ = self.env._
        partner = channel.whatsapp_partner_id
        name = partner.name or (f"+{channel.whatsapp_number}" if channel.whatsapp_number else channel.name)
        is_open = channel._whatsapp_is_window_open()
        left = self._ocd_window_left(channel)
        if is_open:
            window = left["window_text"]
        else:
            first = name.split(" ")[0] if name else ""
            window = _("More than 24 hours without a message of %s: only an approved template", first)
        return {
            "id": channel.id,
            "name": name,
            "initials": self._ocd_initials(name),
            "phone": f"+{channel.whatsapp_number}" if channel.whatsapp_number else (partner.phone or ""),
            "role": self._ocd_partner_role(partner) if partner else _("Unknown number"),
            "vendor": bool(partner and partner.ocd_is_vendor),
            "place": self._ocd_partner_place(partner) if partner else "",
            "open": is_open,
            "window": window,
            "window_urgent": left["window_urgent"],
            "assigned": channel.whatsapp_user_id.name or "",
            "mine": channel.whatsapp_user_id == self.env.user,
            "state": channel.whatsapp_state or "new",
            "state_label": self._ocd_state_label(channel),
            "messages": self._ocd_messages(channel),
            "quick": self._ocd_quick_replies(),
            "templates": self._ocd_template_rows(channel),
            "consent": self._ocd_consent(partner),
            "calls": self._ocd_call_state(channel),
            "sections": (self._ocd_panel_sections(partner) if partner else []) + self._ocd_call_sections(channel),
            "partner_action": partner and {
                "type": "ir.actions.act_window",
                "res_model": "res.partner",
                "res_id": partner.id,
                "views": [[False, "form"]],
            },
        }

    def _ocd_state_label(self, channel):
        """« New · not taken », « Taken by Amina », « Resolved »."""
        _ = self.env._
        if channel.whatsapp_state == "done":
            return _("Resolved")
        if channel.whatsapp_user_id == self.env.user:
            return _("Taken by you")
        if channel.whatsapp_user_id:
            return _("Taken by %s", channel.whatsapp_user_id.name)
        return _("Not taken yet")

    def _ocd_messages(self, channel):
        messages = self.env["mail.message"].sudo().search([
            ("model", "=", "discuss.channel"), ("res_id", "=", channel.id),
            ("message_type", "in", ("comment", "whatsapp_message", "notification")),
        ], order="id desc", limit=MESSAGE_LIMIT)
        wa_messages = self.env["whatsapp.message"].sudo().search([("mail_message_id", "in", messages.ids)])
        by_message = defaultdict(lambda: self.env["whatsapp.message"])
        for wa_message in wa_messages:
            by_message[wa_message.mail_message_id.id] |= wa_message
        calls = self._ocd_message_calls(messages)
        rows = []
        for message in messages.sorted("id"):
            linked = by_message[message.id]
            kind = self._ocd_message_kind(channel, message, linked)
            template = linked.template_id[:1]
            text = self._ocd_message_text(channel, message, kind, template)
            files = [self._ocd_file(attachment) for attachment in message.attachment_ids]
            if files and text == ", ".join(file["name"] for file in files):
                text = ""  # a file alone: shown, not written
            rows.append({
                "id": message.id,
                "kind": kind,
                "tag": self._ocd_message_tag(kind, message, template),
                "text": text,
                "files": files,
                "call": calls.get(message.id, False),
                "time": self._ocd_time_label(message.date),
                "status": self._ocd_status(linked) if kind in ("out", "auto") else "",
                "failed": any(m.state in ("failed", "skipped") for m in linked),
            })
        return rows

    def _ocd_file(self, attachment):
        """A file of the conversation for the screen, shown like in WhatsApp: read with its own
        token (an agent who did not take the conversation reads it too), cached by its checksum."""
        token = attachment._get_raw_access_token()
        query = urlencode({"access_token": token, "unique": attachment.checksum or "", "filename": attachment.name or ""})
        url = f"/web/content/{attachment.id}?{query}"
        mimetype = (attachment.mimetype or "").split(";")[0]
        return {
            "id": attachment.id,
            "name": attachment.name or "",
            "mimetype": mimetype,
            "size": attachment.file_size or 0,
            "checksum": attachment.checksum or "",
            "access_token": token,
            "url": url,
            "downloadUrl": f"{url}&download=true",
            "viewable": mimetype.startswith(("image/", "video/", "audio/", "text/")) or mimetype == "application/pdf",
        }

    # === CALLS (with whatsapp_cloud_call) === #

    def _ocd_calls_enabled(self, channel):
        return "whatsapp.call" in self.env and bool(channel.whatsapp_account_id.call_enabled)

    def _ocd_message_calls(self, messages):
        """The calls behind the lines of the conversation (Missed call, Call of 2 min...): {message
        id: {id, state, inbound, missed, call_back, recording}}."""
        if "whatsapp.call" not in self.env or not messages:
            return {}
        manager = self.env.user.has_group("whatsapp_cloud.group_whatsapp_manager")
        calls = self.env["whatsapp.call"].sudo().search([("notice_message_id", "in", messages.ids)])
        return {
            call.notice_message_id.id: {
                "id": call.id,
                "state": call.state,
                "inbound": call.direction == "inbound",
                "missed": call.state in CALL_MISSED_STATES,
                "call_back": call.direction == "inbound" and call.state in CALL_MISSED_STATES,
                "recording": manager and bool(call.recording_id.attachment_id),
            }
            for call in calls
        }

    def _ocd_call_state(self, channel):
        """Calling the customer from the conversation: allowed by the customer, or ask them first
        (within 24 hours of their last message)."""
        if not self._ocd_calls_enabled(channel):
            return False
        allowed = channel._whatsapp_call_allowed()
        return {
            "allowed": allowed,
            "text": channel._whatsapp_call_permission_text(),
            "can_ask": not allowed and channel._whatsapp_is_window_open(),
        }

    def _ocd_call_sections(self, channel):
        """The last calls of the conversation, in the panel of the contact."""
        if not self._ocd_calls_enabled(channel):
            return []
        calls = self.env["whatsapp.call"].sudo().search([("channel_id", "=", channel.id)], limit=CALL_LAST)
        if not calls:
            return []
        _ = self.env._
        states = dict(calls._fields["state"]._description_selection(self.env))
        rows = []
        for call in calls:
            detail = [states.get(call.state, "")]
            if call.duration:
                minutes, seconds = divmod(call.duration, 60)
                detail.append(f"{minutes} min {seconds:02d} s" if minutes else f"{seconds} s")
            if call.user_id:
                detail.append(call.user_id.name)
            rows.append({
                "key": format_datetime(self.env, call.start_date, dt_format="dd/MM HH:mm"),
                "value": " · ".join(filter(None, detail)),
            })
        return [{
            "title": _("Calls"),
            "rows": rows,
            "links": [{"label": _("All the calls"), "action": {
                "type": "ir.actions.act_window",
                "name": _("Calls"),
                "res_model": "whatsapp.call",
                "views": [[False, "list"], [False, "form"]],
                "domain": [("channel_id", "=", channel.id)],
            }}],
        }]

    def _ocd_message_kind(self, channel, message, linked=None):
        if message.message_type == "notification":
            return "system"
        if message.subtype_id and message.subtype_id.internal:
            return "note"
        partner = channel.whatsapp_partner_id
        if partner and message.author_id == partner:
            return "in"
        if linked is None:
            linked = self.env["whatsapp.message"].sudo().search([("mail_message_id", "=", message.id)])
        if linked.template_id or message.author_id == self.env.ref("base.partner_root"):
            return "auto"
        return "out"

    def _ocd_message_tag(self, kind, message, template):
        _ = self.env._
        if kind == "note":
            return _("Internal note · not seen by the contact")
        if kind == "auto":
            return _("Automatic message · template %s", template.template_name) if template else _("Automatic answer")
        if kind == "out":
            return message.author_id.name or ""
        return ""

    def _ocd_message_text(self, channel, message, kind, template=None):
        text = html2plaintext(message.body or "").strip()
        if kind in ("out", "auto"):
            text = TEMPLATE_LINE_RE.sub("", text).strip()
        if kind == "note":
            text = re.sub(r"^\W*(Internal note|Note interne)\s*:\s*\**\s*", "", text)
        if template is None and kind == "auto":
            template = self.env["whatsapp.message"].sudo().search([("mail_message_id", "=", message.id)], limit=1).template_id
        if template and template.template_name in self._ocd_secret_templates():
            text = SECRET_RE.sub("••••", text)
        if not text and message.attachment_ids:
            text = ", ".join(message.attachment_ids.mapped("name"))
        return text

    @api.model
    def _ocd_secret_templates(self):
        """Names at Meta of the templates that carry a secret, hidden from the team."""
        return {"ocd_code_connexion"}

    def _ocd_status(self, linked):
        if not linked:
            return ""
        _ = self.env._
        worst = min(linked, key=lambda message: STATUS_ORDER.index(message.state) if message.state in STATUS_ORDER else 0)
        labels = {
            "queued": _("to send"), "sent": _("sent"), "delivered": _("delivered"), "read": _("read"),
            "failed": _("not delivered"), "skipped": _("not sent"),
        }
        label = labels.get(worst.state, "")
        if worst.state in ("failed", "skipped") and (worst.error_help or worst.error):
            label = f"{label}: {worst.error_help or worst.error}"
        return label

    @api.model
    def _ocd_quick_replies(self):
        """The canned responses of the agent (theirs and those shared with their groups)."""
        responses = self.env["mail.canned.response"].search([], order="last_used desc, id desc", limit=12)
        return [{"label": f"::{response.source}", "text": response.substitution or ""} for response in responses]

    def _ocd_template_rows(self, channel):
        """The templates to choose from; more than 24 hours after the last message of the contact,
        the follow-up template of the account first (chosen by default, the agent can change)."""
        rows = []
        choices = self._ocd_template_choices(channel)
        if not channel._whatsapp_is_window_open():
            follow_up = channel.sudo()._whatsapp_follow_up_template()
            choices.sort(key=lambda choice: not (
                choice["template"] == follow_up and choice["record"] == channel.whatsapp_partner_id
            ))
        for choice in choices:
            template, record = choice["template"], choice["record"]
            preview = self._ocd_preview(template, record)
            if preview is None:
                continue
            rows.append({
                "key": f"{template.id}-{record._name}-{record.id}",
                "template_id": template.id,
                "res_model": record._name,
                "res_id": record.id,
                "label": choice["label"],
                "name": template.template_name,
                "preview": preview,
            })
        return rows

    def _ocd_template_choices(self, channel):
        """The templates the agent can send from the conversation, each with its document:
        [{"template", "record", "label"}]: first those of the documents of the contact (their
        live, their order, their parcel), then those of the contact."""
        partner = channel.whatsapp_partner_id
        if not partner:
            return []
        choices = []
        for record in self._ocd_template_records(partner):
            choices += [
                {"template": template, "record": record, "label": f"{template.name} · {record.display_name}"}
                for template in self._ocd_templates_for(record._name)
                if template._get_recipient(record) == partner
            ]
        return choices + [
            {"template": template, "record": partner, "label": template.name}
            for template in self._ocd_templates_for("res.partner")
        ]

    def _ocd_template_records(self, partner):
        """The documents of the contact a template can be sent for: their next live and their
        pass here; their order and parcels in ocd_live_shop_whatsapp."""
        records = []
        booking = self.env["ocd.live.booking"].sudo().search([
            ("partner_id", "=", partner.id), ("state", "=", "confirmed"), ("start_datetime", ">=", fields.Datetime.now()),
        ], order="start_datetime", limit=1)
        if booking:
            records.append(booking)
        directory_pass = self.env["ocd.directory.pass"].sudo().search(
            [("partner_id", "=", partner.id), ("state", "=", "active")], order="date_end desc", limit=1
        )
        if directory_pass:
            records.append(directory_pass)
        return records

    @api.model
    def _ocd_templates_for(self, model):
        """Templates of `model` that can go now (approved, or not synchronised yet), without
        the ones that need a value given by the code (a login code...)."""
        templates = self.env["whatsapp.template"].sudo().search([
            ("model", "=", model), ("status", "in", ("approved", "unknown")), ("category", "!=", "authentication"),
        ])
        return templates.filtered(
            lambda template: "ctx" not in (template.button_url_value or "")
            and not any("ctx" in (variable.value or "") for variable in template.variable_ids)
        )

    def _ocd_preview(self, template, record):
        """The text the contact would receive; None when a value of the template cannot be
        computed for this document (« the clips of the live are ready » for a live still to
        come): not offered, it could not go, and the conversation opens all the same."""
        try:
            with self.env.cr.savepoint():
                values = {
                    variable._get_placeholder_key(): template._render(variable.value, record)[record.id]
                    for variable in template.variable_ids
                }
        except Exception:  # noqa: BLE001 - any error of an expression written in the template
            _logger.info("WhatsApp inbox: template %s not offered for %s, a value cannot be computed",
                         template.template_name, record, exc_info=True)
            return None
        text = template._fill_body(values)
        if template.template_name in self._ocd_secret_templates():
            text = SECRET_RE.sub("••••", text)
        return text

    # === CONTACT === #

    @api.model
    def _ocd_partner_role(self, partner):
        _ = self.env._
        role = _("Vendor") if partner.ocd_is_vendor else _("Contact")
        company_country = self.env.company.country_id
        if partner.country_id and partner.country_id != company_country:
            role = f"{role} · {partner.country_id.name}"
        return role

    @api.model
    def _ocd_partner_place(self, partner):
        return " · ".join(filter(None, [partner.city, partner.country_id.name if not partner.city else ""]))

    def _ocd_consent(self, partner):
        _ = self.env._
        if not partner:
            return {"text": _("Unknown number: identify the contact."), "tone": "yellow"}
        if partner.whatsapp_opt_out:
            return {"text": _("Refused the automatic messages (STOP or box unticked)."), "tone": "red"}
        if not partner.whatsapp_opt_in:
            return {"text": _("Did not agree yet to the automatic messages: answers within 24 hours only."), "tone": "yellow"}
        since = self._ocd_consent_date(partner)
        text = _("Accepts WhatsApp since %s", format_date(self.env, since, date_format="d MMM")) if since else _("Accepts WhatsApp")
        return {"text": text, "tone": "green"}

    def _ocd_consent_date(self, partner):
        """Day of the consent, when Odoo keeps the history of the values (module mail_tracking)."""
        if "mail.tracking.value" not in self.env:
            return False
        field = self.env["ir.model.fields"]._get("res.partner", "whatsapp_opt_in")
        tracking = self.env["mail.tracking.value"].sudo().search([
            ("field_id", "=", field.id),
            ("mail_message_id.model", "=", "res.partner"),
            ("mail_message_id.res_id", "=", partner.id),
            ("new_value_integer", "=", 1),
        ], order="id desc", limit=1)
        return tracking.mail_message_id.date.date() if tracking else False

    def _ocd_panel_sections(self, partner):
        """What OCD Live knows of the contact: [{"title", "rows": [{"key", "value"}],
        "links": [{"label", "action"}]}]. The next live of a vendor here; the orders and the
        parcels in ocd_live_shop_whatsapp."""
        _ = self.env._
        sections = []
        if partner.ocd_is_vendor:
            booking = self.env["ocd.live.booking"].sudo().search([
                ("partner_id", "=", partner.id), ("state", "=", "confirmed"),
                ("start_datetime", ">=", fields.Datetime.now() - timedelta(hours=2)),
            ], order="start_datetime", limit=1)
            if booking:
                day, start, end = booking._ocd_studio_labels()
                city = booking.company_id.ocd_studio_city or ""
                place = _("Studio OCD · %s", city) if booking.mode == "studio" else _("Remote")
                sections.append({
                    "title": _("Next live"),
                    "rows": [
                        {"key": _("Live"), "value": f"{day} · {start} – {end}"},
                        {"key": _("Place"), "value": place},
                        {"key": _("Package"), "value": booking.product_id.name or ""},
                    ],
                    "links": [{"label": _("Open the booking"), "action": self._ocd_form(booking)}],
                })
            sections.append({
                "title": _("Vendor"),
                "rows": [{"key": _("Pass"), "value": (
                    _("until %s", format_date(self.env, partner.ocd_pass_end_date)) if partner.ocd_pass_active else _("none")
                )}],
                "links": [{"label": _("Form of the vendor"), "action": self._ocd_form(partner)}],
            })
        return sections

    @api.model
    def _ocd_form(self, record):
        return {"type": "ir.actions.act_window", "res_model": record._name, "res_id": record.id, "views": [[False, "form"]]}

    # === AROUND === #

    @api.model
    def _ocd_account_text(self):
        account = self.env["whatsapp.account"].sudo().search([("company_id", "=", self.env.company.id)], limit=1)
        if not account:
            return {"text": self.env._("No WhatsApp number connected"), "tone": "red"}
        healthy = account.health_state in (False, "ok")
        name = account.verified_name or account.name
        return {
            "text": self.env._("%s · connected", name) if healthy else self.env._("%s · to check", name),
            "tone": "green" if healthy else "red",
        }

    @api.model
    def _ocd_team_channels(self):
        """The Discuss channels of the team, with their last news: [{"id", "name", "text",
        "tone"}]."""
        company = self.env.company
        rows = []
        for channel in company.ocd_lives_channel_id:
            rows.append(self._ocd_team_channel_row(channel))
        return rows

    @api.model
    def _ocd_team_channel_row(self, channel, text=None, tone=""):
        channel = channel.sudo()
        last = channel.message_ids[:1]
        if text is None:
            text = html2plaintext(last.body or "").strip()[:60] if last else self.env._("No message yet")
        return {
            "id": channel.id,
            "name": f"# {channel.name}",
            "text": text,
            "time": self._ocd_time_label(last.date) if last else "",
            "tone": tone,
        }

    # === HELPERS === #

    @api.model
    def _ocd_initials(self, name):
        words = [word for word in re.split(r"[\s+]+", name or "") if word]
        return "".join(word[0] for word in words[:2]).upper() or "?"

    @api.model
    def _ocd_time_label(self, value):
        """14:46 today, "sat. 10:12" this week, "26 nov." before."""
        if not value:
            return ""
        local = fields.Datetime.context_timestamp(self, value)
        today = fields.Datetime.context_timestamp(self, fields.Datetime.now()).date()
        if local.date() == today:
            return f"{local:%H:%M}"
        if local.date() > today - timedelta(days=6):
            return format_datetime(self.env, value, dt_format="EEE HH:mm")
        return format_date(self.env, local.date(), date_format="d MMM")
