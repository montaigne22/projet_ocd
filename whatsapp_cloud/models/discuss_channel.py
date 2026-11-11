import json
import logging
from datetime import timedelta

from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.fields import Command, Domain

from odoo.addons.mail.tools.discuss import Store
from odoo.addons.whatsapp_cloud import const
from odoo.addons.whatsapp_cloud.tools import html_to_whatsapp, normalize_keyword, whatsapp_to_html

_logger = logging.getLogger(__name__)

# The away message is sent at most once in this time to a customer.
AWAY_INTERVAL = timedelta(hours=12)
# A question of the automatic answers (city for the delivery fees...) waits this long for
# its answer.
STEP_TIMEOUT = timedelta(hours=2)
# A resolved conversation that the customer continues within this time goes back to the
# agents directly; later, it starts again with the welcome menu.
REOPEN_INTERVAL = timedelta(hours=12)
# Template messages shown in a new conversation (what the customer may answer to).
BACKFILL_DAYS = 7
BACKFILL_LIMIT = 10


def is_whatsapp(channel):
    return channel.channel_type == "whatsapp"


class DiscussChannel(models.Model):
    """A WhatsApp conversation: one per customer and WhatsApp account, shown in Discuss
    to the agents, who answer from it."""

    _inherit = "discuss.channel"

    channel_type = fields.Selection(
        selection_add=[("whatsapp", "WhatsApp Conversation")],
        ondelete={"whatsapp": "cascade"},
    )
    whatsapp_account_id = fields.Many2one(
        comodel_name="whatsapp.account", string="WhatsApp Account", readonly=True,
        index="btree_not_null", ondelete="cascade",
    )
    whatsapp_number = fields.Char(
        string="WhatsApp Number", readonly=True,
        help="Number of the customer in international format, without +.",
    )
    whatsapp_user_ref = fields.Char(
        string="WhatsApp User ID", readonly=True,
        help="ID of the customer for the company at WhatsApp (BSUID).",
    )
    whatsapp_partner_id = fields.Many2one(
        comodel_name="res.partner", string="Customer", readonly=True,
        index="btree_not_null", ondelete="set null",
    )
    whatsapp_to_identify = fields.Boolean(
        related="whatsapp_partner_id.whatsapp_to_identify", string="Customer to Identify"
    )
    whatsapp_user_id = fields.Many2one(
        comodel_name="res.users", string="Assigned to", index="btree_not_null",
        ondelete="set null", domain=[("share", "=", False)],
    )
    whatsapp_assigned_date = fields.Datetime(string="Assigned on", readonly=True)
    whatsapp_state = fields.Selection(
        selection=[("new", "New"), ("open", "In progress"), ("done", "Resolved")],
        string="Conversation Status",
        default="new",
        index="btree_not_null",
    )
    whatsapp_last_inbound_date = fields.Datetime(
        string="Last Message of the Customer", readonly=True
    )
    whatsapp_channel_valid_until = fields.Datetime(
        string="Answers Allowed until",
        compute="_compute_whatsapp_channel_valid_until",
        store=True,
        help="Free-form answers are allowed for 24 hours after the last message of the "
        "customer; a template is required after.",
    )
    whatsapp_waiting_since = fields.Datetime(
        string="Waiting for an Answer since", readonly=True, index="btree_not_null",
        help="The customer waits for an answer of the team since this date.",
    )
    whatsapp_alert_level = fields.Integer(readonly=True)
    whatsapp_bot_state = fields.Selection(
        selection=[("menu", "Welcome menu"), ("agent", "With the team")],
        string="Automatic Answers",
        readonly=True,
    )
    whatsapp_away_date = fields.Datetime(readonly=True)
    # question of the automatic answers waiting for the answer of the customer
    whatsapp_bot_step = fields.Char(string="Waiting Question", readonly=True)
    whatsapp_bot_step_data = fields.Json(string="Waiting Question Data", readonly=True)
    whatsapp_bot_step_date = fields.Datetime(string="Question Date", readonly=True)
    whatsapp_tag_ids = fields.Many2many(comodel_name="whatsapp.tag", string="Tags")
    whatsapp_message_ids = fields.One2many(
        comodel_name="whatsapp.message", inverse_name="channel_id", string="WhatsApp Messages"
    )

    _whatsapp_number_uniq = models.UniqueIndex(
        "(whatsapp_account_id, whatsapp_number) WHERE whatsapp_number IS NOT NULL",
        "There is already a conversation with this number.",
    )
    _whatsapp_user_ref_uniq = models.UniqueIndex(
        "(whatsapp_account_id, whatsapp_user_ref) WHERE whatsapp_user_ref IS NOT NULL "
        "AND whatsapp_number IS NULL",
        "There is already a conversation with this WhatsApp user.",
    )

    @api.depends("whatsapp_last_inbound_date")
    def _compute_whatsapp_channel_valid_until(self):
        for channel in self:
            channel.whatsapp_channel_valid_until = (
                channel.whatsapp_last_inbound_date + const.SERVICE_WINDOW
                if channel.whatsapp_last_inbound_date else False
            )

    # === STORE (DISCUSS) === #

    def _whatsapp_store_values(self):
        """Values of the conversation shown in Discuss to the users."""
        self.ensure_one()
        return {
            "whatsapp_account_name": self.whatsapp_account_id.name,
            "whatsapp_number": self.whatsapp_number or False,
            "whatsapp_partner_id": self.whatsapp_partner_id.id,
            "whatsapp_to_identify": self.whatsapp_to_identify,
            "whatsapp_user_id": self.whatsapp_user_id.id,
            "whatsapp_user_name": self.whatsapp_user_id.name or False,
            "whatsapp_state": self.whatsapp_state,
            "whatsapp_channel_valid_until": self.whatsapp_channel_valid_until,
            "whatsapp_waiting_since": self.whatsapp_waiting_since,
            "whatsapp_bot_state": self.whatsapp_bot_state or False,
            "whatsapp_tags": [
                {"id": tag.id, "name": tag.name, "color": tag.color}
                for tag in self.whatsapp_tag_ids
            ],
        }

    def _sync_field_names(self, res):
        super()._sync_field_names(res)
        for fname in self._whatsapp_store_fnames():
            res["internal_users"].attr(
                fname,
                lambda channel, fname=fname: channel._whatsapp_store_values()[fname],
                predicate=is_whatsapp,
            )

    def _store_channel_fields(self, res: Store.FieldList):
        super()._store_channel_fields(res)
        if res.is_for_internal_users():
            for fname in self._whatsapp_store_fnames():
                res.attr(
                    fname,
                    lambda channel, fname=fname: channel._whatsapp_store_values()[fname],
                    predicate=is_whatsapp,
                )

    @api.model
    def _whatsapp_store_fnames(self):
        return [
            "whatsapp_account_name", "whatsapp_number", "whatsapp_partner_id",
            "whatsapp_to_identify", "whatsapp_user_id", "whatsapp_user_name", "whatsapp_state",
            "whatsapp_channel_valid_until", "whatsapp_waiting_since", "whatsapp_bot_state",
            "whatsapp_tags",
        ]

    # === CONVERSATION === #

    @api.model
    def _whatsapp_find(self, account, number, user_ref=None):
        """The conversation of a customer with the account (with several accounts: the one
        where the customer wrote last): by number, else by WhatsApp user ID."""
        domain = Domain("channel_type", "=", "whatsapp") & Domain(
            "whatsapp_account_id", "in", account.ids
        )
        order = "whatsapp_last_inbound_date desc nulls last, id desc"
        channel = self.browse()
        if number:
            channel = self.search(
                domain & Domain("whatsapp_number", "=", number), order=order, limit=1
            )
        if not channel and user_ref:
            channel = self.search(
                domain & Domain("whatsapp_user_ref", "=", user_ref), order=order, limit=1
            )
        return channel

    @api.model
    def _whatsapp_get_or_create(self, account, number, user_ref, partner):
        """The conversation of a customer with the account, created at their first message."""
        channel = self._whatsapp_find(account, number, user_ref)
        if channel and number and not channel.whatsapp_number:
            channel.whatsapp_number = number
        if channel:
            if user_ref and channel.whatsapp_user_ref != user_ref:
                channel.whatsapp_user_ref = user_ref
            if not channel.whatsapp_partner_id:
                channel._whatsapp_set_partner(partner)
            return channel
        channel = self.create({
            "name": partner.display_name or f"+{number}",
            "channel_type": "whatsapp",
            "whatsapp_account_id": account.id,
            "whatsapp_number": number or False,
            "whatsapp_user_ref": user_ref or False,
            "whatsapp_partner_id": partner.id,
            "channel_member_ids": [Command.create({"partner_id": partner.id})],
        })
        # Discuss adds the creator (OdooBot for the webhook): only the customer to start with
        channel.channel_member_ids.filtered(lambda member: member.partner_id != partner).unlink()
        channel._whatsapp_backfill()
        return channel

    def _whatsapp_set_partner(self, partner):
        """The customer of the conversation (after its identification)."""
        for channel in self:
            old = channel.whatsapp_partner_id
            if old == partner:
                continue
            if old:
                channel.channel_member_ids.filtered(
                    lambda member: member.partner_id == old
                ).sudo().unlink()
            if partner not in channel.channel_member_ids.partner_id:
                channel.channel_member_ids = [Command.create({"partner_id": partner.id})]
            channel.write({"whatsapp_partner_id": partner.id, "name": partner.display_name})

    def _whatsapp_backfill(self):
        """Show in a new conversation the last templates sent to the customer: what they
        may be answering to."""
        self.ensure_one()
        domain = [
            ("account_id", "=", self.whatsapp_account_id.id),
            ("direction", "=", "outgoing"),
            ("state", "not in", ("skipped", "queued")),
            ("mail_message_id", "=", False),
            ("create_date", ">", fields.Datetime.now() - timedelta(days=BACKFILL_DAYS)),
        ]
        if self.whatsapp_number:
            domain.append(("phone", "=", self.whatsapp_number))
        else:
            domain.append(("user_ref", "=", self.whatsapp_user_ref))
        messages = self.env["whatsapp.message"].search(domain, order="id desc", limit=BACKFILL_LIMIT)
        for message in messages.sorted("id"):
            self._whatsapp_post_outgoing(message)

    def _whatsapp_get_lang(self):
        """Language of the answers sent to the customer."""
        self.ensure_one()
        return (
            self.whatsapp_partner_id.lang
            or self.whatsapp_account_id.company_id.partner_id.lang
            or self.env.lang
        )

    def _whatsapp_is_window_open(self):
        self.ensure_one()
        return bool(
            self.whatsapp_channel_valid_until
            and self.whatsapp_channel_valid_until > fields.Datetime.now()
        )

    # === RECEIVING === #

    def _whatsapp_receive(self, wa_message, content):
        """A message of the customer: posted in the conversation, then the automatic answers
        and the team."""
        self.ensure_one()
        if reaction := content.get("reaction"):
            self._whatsapp_receive_reaction(wa_message, *reaction)
            return
        if content.get("system"):
            self._whatsapp_receive_system(wa_message, content["system"])
            return
        now = fields.Datetime.now()
        vals = {"whatsapp_last_inbound_date": now}
        if self.whatsapp_state == "done":
            vals["whatsapp_state"] = "new" if not self.whatsapp_user_id else "open"
            recent = self.whatsapp_last_inbound_date and (
                self.whatsapp_last_inbound_date > now - REOPEN_INTERVAL
            )
            vals["whatsapp_bot_state"] = "agent" if recent else False
        self.write(vals)
        mail_message = self._whatsapp_post_incoming(wa_message, content)
        if referral := content.get("referral"):
            self._whatsapp_notify(_(
                "The customer comes from the ad: %(headline)s %(url)s",
                headline=referral.get("headline") or referral.get("body") or "",
                url=referral.get("source_url") or "",
            ))
        if self._whatsapp_handle_subscription(wa_message):
            return
        if self._whatsapp_bot_process(wa_message, content):
            return
        self._whatsapp_route_to_agents(mail_message)

    def _whatsapp_post_incoming(self, wa_message, content):
        """Post the message of the customer in the conversation."""
        self.ensure_one()
        parent = wa_message.parent_id.mail_message_id
        message = self.with_context(whatsapp_skip_send=True).message_post(
            author_id=wa_message.partner_id.id,
            body=whatsapp_to_html(wa_message.body),
            attachment_ids=content.get("attachment") and content["attachment"].ids or [],
            parent_id=parent.id if parent and parent.res_id == self.id else False,
            message_type="whatsapp_message",
            subtype_xmlid="mail.mt_comment",
        )
        wa_message.mail_message_id = message
        return message

    def _whatsapp_receive_reaction(self, wa_message, emoji, reacted_id):
        """A reaction of the customer, shown on the message they reacted to."""
        self.ensure_one()
        reacted = self.env["whatsapp.message"].search([
            ("account_id", "=", self.whatsapp_account_id.id), ("wa_message_id", "=", reacted_id),
        ], limit=1).mail_message_id
        if not reacted:
            return
        partner = wa_message.partner_id
        guest = self.env["mail.guest"]
        Reaction = self.env["mail.message.reaction"].sudo()
        for reaction in Reaction.search([
            ("message_id", "=", reacted.id), ("partner_id", "=", partner.id),
        ]):
            reacted.sudo()._message_reaction(reaction.content, "remove", partner, guest)
        if emoji:
            reacted.sudo()._message_reaction(emoji, "add", partner, guest)

    def _whatsapp_receive_system(self, wa_message, system):
        """The customer changed their number or their WhatsApp user ID."""
        self.ensure_one()
        partner = wa_message.partner_id
        new_number = system.get("wa_id")
        new_ref = system.get("user_id")
        vals = {}
        if new_ref:
            vals["whatsapp_user_ref"] = new_ref
            partner.sudo().whatsapp_user_ref = new_ref
        if new_number and new_number != self.whatsapp_number:
            if not self.search_count([
                ("whatsapp_account_id", "=", self.whatsapp_account_id.id),
                ("whatsapp_number", "=", new_number),
            ], limit=1):
                vals["whatsapp_number"] = new_number
            if partner and partner._whatsapp_number() == self.whatsapp_number:
                partner.sudo().phone = f"+{new_number}"
        if vals:
            self.write(vals)
        self._whatsapp_notify(
            system.get("body") or _("The customer changed their WhatsApp number.")
        )

    def _whatsapp_handle_subscription(self, wa_message):
        """STOP: no more notifications; START: notifications again. True when handled."""
        self.ensure_one()
        keyword = wa_message.partner_id._whatsapp_apply_subscription_keyword(wa_message.body)
        if not keyword:
            return False
        self._whatsapp_confirm_subscription(keyword == "start")
        return True

    def _whatsapp_set_subscription(self, subscribe):
        """The customer stops or resumes the notifications (option of the menu)."""
        self.ensure_one()
        partner = self.whatsapp_partner_id.sudo()
        if partner:
            partner.whatsapp_opt_in = subscribe
        self._whatsapp_confirm_subscription(subscribe)

    def _whatsapp_confirm_subscription(self, subscribe):
        self.ensure_one()
        account = self.whatsapp_account_id.with_context(lang=self._whatsapp_get_lang())
        if subscribe:
            self._whatsapp_notify(_("The customer receives the WhatsApp notifications again (START)."))
            if account.start_message:
                self._whatsapp_send_bot_text(account.start_message)
        else:
            self._whatsapp_notify(_("The customer no longer receives the WhatsApp notifications (STOP)."))
            if account.stop_message:
                self._whatsapp_send_bot_text(account.stop_message)

    def _whatsapp_set_lang(self, lang):
        """The customer chose a language: the answers, menus and notifications follow it."""
        self.ensure_one()
        partner = self.whatsapp_partner_id.sudo()
        if partner and lang in dict(self.env["res.lang"].get_installed()):
            partner.lang = lang
            self._whatsapp_notify(_(
                "The customer chose the language %s.", self.env["res.lang"]._lang_get(lang).name
            ))
        self._whatsapp_send_menu()

    # === AUTOMATIC ANSWERS === #

    def _whatsapp_bot_process(self, wa_message, content):
        """Automatic answers to the message of the customer; True when the message needs no
        agent (answered by the welcome menu or one of its options)."""
        self.ensure_one()
        account = self.whatsapp_account_id
        reply_id = content.get("reply_id") or ""
        if reply_id.startswith("whatsapp_option_"):
            option = self.env["whatsapp.bot.option"].browse(
                int(reply_id.removeprefix("whatsapp_option_") or 0)
            ).exists().filtered(lambda option: option.account_id == account)
            if option:
                self._whatsapp_clear_step()
                option._run(self, wa_message)
                return True
        if reply_id == const.MENU_REPLY_ID:
            self._whatsapp_clear_step()
            return self._whatsapp_send_menu()
        if reply_id == const.HANDOVER_REPLY_ID:
            self._whatsapp_clear_step()
            self._whatsapp_handover()
            return True
        if self._whatsapp_handle_reply(wa_message, content):
            return True
        if not account.bot_enabled:
            return False
        keyword = normalize_keyword(wa_message.body)
        if keyword in const.HANDOVER_KEYWORDS:
            self._whatsapp_clear_step()
            self._whatsapp_handover()
            return True
        if keyword in const.MENU_KEYWORDS:
            self._whatsapp_clear_step()
            return self._whatsapp_send_menu()
        if self.whatsapp_bot_step and self._whatsapp_handle_step(wa_message, content):
            return True
        if self._whatsapp_bot_answer(wa_message, content):
            return True
        if self.whatsapp_bot_state == "agent":
            return False
        if not self.whatsapp_bot_state:
            return self._whatsapp_send_menu(welcome=True)
        # the menu was sent but the message is something else: a question for the team, who
        # already has it
        self._whatsapp_handover(invite=False)
        return True

    def _whatsapp_handle_reply(self, wa_message, content):
        """Hook: answer to a button of a template (rating...). True when handled."""
        return False

    def _whatsapp_bot_answer(self, wa_message, content):
        """Hook: automatic answer to a known request (order number...). True when handled."""
        return False

    def _whatsapp_get_bot_options(self, parent=None):
        """Options of the welcome menu (or of a sub-menu) offered to the customer."""
        self.ensure_one()
        options = parent.child_ids if parent else self.whatsapp_account_id.bot_option_ids
        options = options.filtered("active").with_context(lang=self._whatsapp_get_lang())
        return options.filtered(lambda option: option._is_available(self))

    def _whatsapp_send_menu(self, welcome=False, parent=None):
        """The welcome message with the options of the menu (or the text of a sub-menu with
        its options and "Main menu"), as buttons (3 at most) or as a list. True when the menu
        answers the customer; False without options: the welcome message is sent and the
        message of the customer goes to the team."""
        self.ensure_one()
        lang = self._whatsapp_get_lang()
        account = self.whatsapp_account_id.with_context(lang=lang)
        env = self.with_context(lang=lang).env
        options = self._whatsapp_get_bot_options(parent)
        if parent:
            parent = parent.with_context(lang=lang)
            text = (parent.answer or "").strip() or parent.name
        else:
            text = (account.welcome_message or "").strip() or env._("How can we help you?")
        if not options:
            if parent:
                return self._whatsapp_send_menu()
            self._whatsapp_send_bot_text(text)
            self.whatsapp_bot_state = "agent"
            return False
        entries = [(option._get_reply_id(), option.name, option.description) for option in options]
        if parent:
            entries = entries[:const.MAX_LIST_ROWS - 1] + [(const.MENU_REPLY_ID, env._("Main menu"), None)]
        self._whatsapp_send_choices(text, entries, env._("See the options"))
        self.whatsapp_bot_state = "menu"
        return True

    def _whatsapp_send_choices(self, text, entries, list_button, force_list=False):
        """Send a text with choices: buttons (3 at most), else a list (10 at most; also when
        the descriptions of the choices matter). Each entry is (reply ID, title, description);
        WhatsApp sends back the reply ID of the choice."""
        self.ensure_one()
        body = text[:const.MAX_INTERACTIVE_BODY]
        if len(entries) <= const.MAX_REPLY_BUTTONS and not force_list:
            interactive = {
                "type": "button",
                "body": {"text": body},
                "action": {"buttons": [{
                    "type": "reply",
                    "reply": {"id": reply_id, "title": title[:const.MAX_BUTTON_TITLE]},
                } for reply_id, title, _description in entries]},
            }
        else:
            interactive = {
                "type": "list",
                "body": {"text": body},
                "action": {
                    "button": list_button[:const.MAX_BUTTON_TITLE],
                    "sections": [{"rows": [{
                        "id": reply_id,
                        "title": title[:const.MAX_ROW_TITLE],
                        **({"description": description[:const.MAX_ROW_DESCRIPTION]}
                           if description else {}),
                    } for reply_id, title, description in entries[:const.MAX_LIST_ROWS]]}],
                },
            }
        shown = "\n".join([text, *(f"• {title}" for _reply_id, title, _d in entries)])
        return self._whatsapp_send_bot_text(shown, interactive=interactive)

    def _whatsapp_get_follow_up_choices(self):
        """Choices under an automatic answer, to go on without writing."""
        self.ensure_one()
        env = self.with_context(lang=self._whatsapp_get_lang()).env
        return [
            (const.MENU_REPLY_ID, env._("Main menu"), None),
            (const.HANDOVER_REPLY_ID, env._("Talk to an advisor"), None),
        ]

    def _whatsapp_send_answer(self, text, follow_up=True):
        """An automatic answer to the customer, with the choices to go on ("Main menu",
        "Talk to an advisor") under it, or under a short message after it when it is too
        long for a message with buttons."""
        self.ensure_one()
        if not follow_up:
            return self._whatsapp_send_bot_text(text)
        choices = self._whatsapp_get_follow_up_choices()
        if len(text) <= const.MAX_INTERACTIVE_BODY:
            return self._whatsapp_send_choices(text, choices, choices[0][1])
        self._whatsapp_send_bot_text(text)
        return self._whatsapp_send_follow_up()

    def _whatsapp_send_follow_up(self):
        """The choices to go on, after automatic answers sent as several messages."""
        self.ensure_one()
        env = self.with_context(lang=self._whatsapp_get_lang()).env
        choices = self._whatsapp_get_follow_up_choices()
        return self._whatsapp_send_choices(env._("Anything else?"), choices, choices[0][1])

    # === QUESTIONS OF THE AUTOMATIC ANSWERS === #

    def _whatsapp_ask(self, step, text, data=None, choices=None, list_button=None,
                      force_list=False):
        """Ask the customer a question (with choices, if any): their next message is handled
        by the handler of the step (see _whatsapp_get_step_handlers)."""
        self.ensure_one()
        if choices:
            self._whatsapp_send_choices(text, choices, list_button or text, force_list=force_list)
        else:
            self._whatsapp_send_bot_text(text)
        self.write({
            "whatsapp_bot_step": step,
            "whatsapp_bot_step_data": data or {},
            "whatsapp_bot_step_date": fields.Datetime.now(),
            "whatsapp_bot_state": "menu",
        })

    def _whatsapp_get_step_handlers(self):
        """Hook: {step: method(wa_message, content, data)} of the questions of the automatic
        answers; the method answers the customer and returns True when it handled the
        message."""
        return {}

    def _whatsapp_handle_step(self, wa_message, content):
        """The answer of the customer to the question asked, if it is still waiting."""
        self.ensure_one()
        step, data, date = (
            self.whatsapp_bot_step, self.whatsapp_bot_step_data, self.whatsapp_bot_step_date
        )
        self._whatsapp_clear_step()
        if not date or date < fields.Datetime.now() - STEP_TIMEOUT:
            return False
        handler = self._whatsapp_get_step_handlers().get(step)
        return bool(handler and handler(wa_message, content, data or {}))

    def _whatsapp_clear_step(self):
        self.ensure_one()
        if self.whatsapp_bot_step:
            self.write({
                "whatsapp_bot_step": False,
                "whatsapp_bot_step_data": False,
                "whatsapp_bot_step_date": False,
            })

    def _whatsapp_send_bot_text(self, text, interactive=None, attachment=None, location=None):
        """An automatic answer: shown in the conversation as OdooBot, and sent."""
        self.ensure_one()
        message = self.with_context(whatsapp_skip_send=True).message_post(
            author_id=self.env.ref("base.partner_root").id,
            body=whatsapp_to_html(text),
            message_type="whatsapp_message",
            subtype_xmlid="mail.mt_comment",
            silent=True,
        )
        return self._whatsapp_send_mail_message(
            message, interactive=interactive, attachments=attachment, text=text, location=location
        )

    def _whatsapp_send_location(self, latitude, longitude, name, address=""):
        """A place (a store...) as a location: the customer opens it in their maps."""
        self.ensure_one()
        text = "\n".join(filter(None, [
            f"📍 {name}", address, f"https://maps.google.com/?q={latitude},{longitude}",
        ]))
        location = {"latitude": latitude, "longitude": longitude, "name": name}
        if address:
            location["address"] = address
        return self._whatsapp_send_bot_text(text, location=location)

    def _whatsapp_send_away_message(self):
        """The away message when the team does not work now; True when sent."""
        self.ensure_one()
        account = self.whatsapp_account_id.with_context(lang=self._whatsapp_get_lang())
        now = fields.Datetime.now()
        if (
            not account.away_message_enabled
            or not (account.away_message or "").strip()
            or account._is_open(now)
            or (self.whatsapp_away_date and self.whatsapp_away_date > now - AWAY_INTERVAL)
        ):
            return False
        self._whatsapp_send_bot_text(account.away_message)
        self.whatsapp_away_date = now
        return True

    def _whatsapp_handover(self, invite=True):
        """The conversation goes to the team. ``invite``: the customer asked for a person
        without saying what they need yet, they are invited to write it (else they are told
        that an advisor will answer)."""
        self.ensure_one()
        account = self.whatsapp_account_id.with_context(lang=self._whatsapp_get_lang())
        already = self.whatsapp_bot_state == "agent"
        self.whatsapp_bot_state = "agent"
        away = self._whatsapp_send_away_message()
        if not already:
            if invite and account.handover_invite_message:
                self._whatsapp_send_bot_text(account.handover_invite_message)
            elif not away and account.handover_message:
                self._whatsapp_send_bot_text(account.handover_message)
        self._whatsapp_route_to_agents(handover=True)

    # === TEAM === #

    def _whatsapp_route_to_agents(self, mail_message=None, handover=False):
        """The message needs an answer of the team: the assigned agent, or the agent chosen
        by the account (salesperson, each agent in turn), or all the agents."""
        self.ensure_one()
        if not handover:
            self._whatsapp_send_away_message()
        vals = {}
        if not self.whatsapp_waiting_since:
            vals.update(whatsapp_waiting_since=fields.Datetime.now(), whatsapp_alert_level=0)
        if self.whatsapp_bot_state != "agent":
            vals["whatsapp_bot_state"] = "agent"
        if vals:
            self.write(vals)
        account = self.whatsapp_account_id
        agents = account._get_agents()
        separator = mail_message.id if mail_message else None
        user = self.whatsapp_user_id
        if user and user.active and not user.share:
            self._whatsapp_add_users(user, separator)
            return
        user = self._whatsapp_get_preferred_user(agents)
        if not user and account.assignment_mode == "round_robin":
            user = account._pick_agent(agents)
        if user:
            self._whatsapp_assign(user, separator=separator)
        elif agents:
            new = self._whatsapp_add_users(agents, separator)
            if new:
                self._whatsapp_notify(
                    _("New WhatsApp conversation of %s: take it to answer.",
                      self.whatsapp_partner_id.display_name or self.name),
                    partners=new.partner_id,
                )

    def _whatsapp_get_preferred_user(self, agents):
        """Hook: the agent who should handle the conversation (e.g. salesperson)."""
        return self.env["res.users"]

    def _whatsapp_add_users(self, users, separator=None):
        """Add the users to the conversation (it then shows in their Discuss, with the new
        messages as unread); return the users added."""
        self.ensure_one()
        users = users.filtered(lambda user: user.active and not user.share)
        new_users = users.filtered(lambda user: user.partner_id not in self.channel_member_ids.partner_id)
        if new_users:
            params = {"new_message_separator": separator} if separator else None
            self._add_members(
                users=new_users, post_joined_message=False, create_member_params=params
            )
        # unhide the conversation for the members who hid it
        self.channel_member_ids.filtered(
            lambda member: member.partner_id in users.partner_id and member.unpin_dt
        ).write({"unpin_dt": False})
        return new_users

    def _whatsapp_assign(self, user, separator=None, notify=True):
        """Give the conversation to an agent: the other agents leave it."""
        self.ensure_one()
        previous = self.whatsapp_user_id
        if previous == user:
            self._whatsapp_add_users(user, separator)
            return
        self.write({
            "whatsapp_user_id": user.id,
            "whatsapp_assigned_date": fields.Datetime.now(),
            "whatsapp_state": "open" if self.whatsapp_state == "new" else self.whatsapp_state,
        })
        self._whatsapp_add_users(user, separator)
        keep = user.partner_id | self.whatsapp_partner_id
        if self.whatsapp_alert_level >= 2:
            keep |= self.whatsapp_account_id._get_escalation_users().partner_id
        self.channel_member_ids.filtered(
            lambda member: member.partner_id
            and member.partner_id not in keep
            and member.partner_id.user_ids
            and not member.partner_id.partner_share
        ).sudo().unlink()
        if notify:
            text = _("Conversation assigned to %s.", user.name)
            partners = user.partner_id if user != self.env.user else None
            self._whatsapp_notify(text, partners=partners)

    def _whatsapp_notify(self, text, partners=None):
        """A notice in the conversation, for the team only; the given partners are notified
        in their inbox."""
        self.ensure_one()
        body = Markup('<div class="o_mail_notification o_whatsapp_notice">%s</div>') % text
        partner_ids = (partners & self.channel_member_ids.partner_id).ids if partners else []
        return self.with_context(whatsapp_skip_send=True).message_post(
            body=body,
            message_type="notification",
            subtype_xmlid="mail.mt_important_notification" if partner_ids else "mail.mt_comment",
            partner_ids=partner_ids,
        )

    @api.model
    def _cron_whatsapp_check_delays(self):
        """Remind the agents of the messages waiting too long for an answer, then alert the
        managers (opening hours only)."""
        now = fields.Datetime.now()
        channels = self.search([
            ("channel_type", "=", "whatsapp"),
            ("whatsapp_waiting_since", "!=", False),
            ("whatsapp_state", "!=", "done"),
            ("whatsapp_alert_level", "<", 2),
            ("whatsapp_account_id.company_id.whatsapp_answer_reminders", "=", True),
        ])
        for channel in channels:
            channel = channel.with_context(lang=channel.whatsapp_account_id._get_team_lang())
            account = channel.whatsapp_account_id
            minutes = account._get_working_minutes(channel.whatsapp_waiting_since, now)
            if account.escalation_delay and minutes >= account.escalation_delay:
                channel._whatsapp_escalate(minutes)
            elif (
                account.response_delay and minutes >= account.response_delay
                and channel.whatsapp_alert_level < 1
            ):
                channel._whatsapp_remind(minutes)

    def _whatsapp_remind(self, minutes):
        self.ensure_one()
        users = self.whatsapp_user_id or self.whatsapp_account_id._get_agents()
        self._whatsapp_add_users(users)
        self.whatsapp_alert_level = 1
        self._whatsapp_notify(
            _("The customer has been waiting for an answer for %s minutes.", int(minutes)),
            partners=users.partner_id,
        )

    def _whatsapp_escalate(self, minutes):
        self.ensure_one()
        managers = self.whatsapp_account_id._get_escalation_users()
        self._whatsapp_add_users(managers)
        self.whatsapp_alert_level = 2
        self._whatsapp_notify(
            _("Escalation: the customer has been waiting for an answer for %s minutes.",
              int(minutes)),
            partners=managers.partner_id | self.whatsapp_user_id.partner_id,
        )

    # === SENDING === #

    def _whatsapp_queue_read_receipt(self, typing=False):
        """Mark the last message of the customer as read at WhatsApp (the earlier ones
        too), with "typing..." when an agent writes."""
        self.ensure_one()
        WaMessage = self.env["whatsapp.message"].sudo()
        last = WaMessage.search([
            ("channel_id", "=", self.id),
            ("direction", "=", "incoming"),
            ("wa_message_id", "!=", False),
        ], order="id desc", limit=1)
        if not last or (not typing and last.read_receipt):
            return
        last.read_receipt = "typing" if typing else "todo"
        WaMessage._trigger_send()

    def message_post(self, *, message_type="notification", **kwargs):
        """An agent writes in a WhatsApp conversation: the message is sent to the customer."""
        if (
            len(self) != 1
            or self.channel_type != "whatsapp"
            or message_type != "comment"
            or self.env.context.get("whatsapp_skip_send")
        ):
            return super().message_post(message_type=message_type, **kwargs)
        if self.env.user._is_public() or self.env.user.share:
            raise AccessError(_("Only the team can write in a WhatsApp conversation."))
        if not self._whatsapp_is_window_open():
            raise UserError(_(
                "More than 24 hours since the last message of the customer: WhatsApp allows "
                "only an approved template now (Send a template)."
            ))
        if kwargs.get("body"):
            kwargs["body"] = self._whatsapp_render_placeholders(kwargs["body"])
        message = super().message_post(message_type="whatsapp_message", **kwargs)
        self._whatsapp_send_mail_message(message)
        self._whatsapp_after_agent_message()
        return message

    def _whatsapp_after_agent_message(self):
        """An agent answered: the customer no longer waits, the agent handles the
        conversation (if nobody did) and the automatic answers stop."""
        self.ensure_one()
        vals = {}
        if self.whatsapp_waiting_since:
            vals.update(whatsapp_waiting_since=False, whatsapp_alert_level=0)
        if self.whatsapp_bot_state != "agent":
            vals["whatsapp_bot_state"] = "agent"
        if self.whatsapp_state != "open":
            vals["whatsapp_state"] = "open"
        if vals:
            self.sudo().write(vals)
        user = self.env.user
        if not self.whatsapp_user_id and user.has_group("whatsapp_cloud.group_whatsapp_user"):
            self.sudo()._whatsapp_assign(user)

    def _whatsapp_get_placeholder_values(self):
        """Values of the placeholders that the agents (and the canned responses) can use."""
        self.ensure_one()
        partner = self.whatsapp_partner_id
        name = partner.name or ""
        first_name = name.split(" ")[0] if name else ""
        values = {
            "name": name, "nom": name,
            "first_name": first_name, "prenom": first_name, "prénom": first_name,
            "agent": self.env.user.name, "conseiller": self.env.user.name,
            "company": self.whatsapp_account_id.company_id.name,
            "societe": self.whatsapp_account_id.company_id.name,
            "société": self.whatsapp_account_id.company_id.name,
        }
        return values

    def _whatsapp_render_placeholders(self, body):
        """Replace {name}, {first_name}, {agent}... in the message of an agent."""
        if "{" not in str(body):
            return body
        is_markup = isinstance(body, Markup)
        text = str(body)
        for key, value in self._whatsapp_get_placeholder_values().items():
            text = text.replace("{%s}" % key, str(escape(value)) if is_markup else value)
        return Markup(text) if is_markup else text

    def _whatsapp_send_mail_message(self, message, interactive=None, attachments=None, text=None,
                                    location=None):
        """Send to the customer a message posted in the conversation: its text and its files
        (one WhatsApp message each; a single image, video or document carries the text as
        caption)."""
        self.ensure_one()
        WaMessage = self.env["whatsapp.message"].sudo()
        account = self.whatsapp_account_id
        text = text if text is not None else html_to_whatsapp(message.body)
        attachments = (attachments or self.env["ir.attachment"]) | message.attachment_ids
        attachments = attachments.sudo().sorted("id")
        parent = WaMessage.search(
            [("mail_message_id", "=", message.parent_id.id)], limit=1
        ) if message.parent_id else WaMessage
        context_id = parent.wa_message_id or None
        common = {
            "account_id": account.id,
            "direction": "outgoing",
            "state": "queued",
            "channel_id": self.id,
            "mail_message_id": message.id,
            "partner_id": self.whatsapp_partner_id.id,
            "phone": self.whatsapp_number,
            "user_ref": self.whatsapp_user_ref,
            "model": "discuss.channel",
            "res_id": self.id,
            "parent_id": parent.id,
        }
        number, user_ref = self.whatsapp_number, self.whatsapp_user_ref
        vals_list = []
        caption = None
        if (
            text and len(attachments) == 1 and not interactive
            and WaMessage._get_media_type(attachments) in const.CAPTION_TYPES
            and len(text) <= const.MAX_CAPTION
        ):
            caption, text = text, ""
        if location:
            vals_list.append({**common, "message_type": "location", "body": text,
                              "payload": WaMessage._prepare_free_payload(
                                  number, user_ref, location=location, context_id=context_id)})
        elif interactive:
            vals_list.append({**common, "message_type": "interactive", "body": text,
                              "payload": WaMessage._prepare_free_payload(
                                  number, user_ref, interactive=interactive, context_id=context_id)})
        elif text:
            vals_list.append({**common, "message_type": "text", "body": text,
                              "payload": WaMessage._prepare_free_payload(
                                  number, user_ref, text=text, context_id=context_id)})
        for attachment in attachments:
            media_type = WaMessage._get_media_type(attachment)
            vals_list.append({
                **common,
                "message_type": media_type,
                "body": caption or attachment.name,
                "attachment_id": attachment.id,
                "payload": WaMessage._prepare_free_payload(
                    number, user_ref, attachment=attachment, caption=caption,
                    context_id=None if vals_list else context_id,
                ),
            })
        for vals in vals_list:
            vals["payload"] = json.dumps(vals["payload"])
        messages = WaMessage.create(vals_list)
        if messages:
            WaMessage._trigger_send()
        return messages

    def _whatsapp_post_outgoing(self, wa_message):
        """Show in the conversation a template sent to the customer elsewhere (automation,
        document, template sent from the conversation)."""
        self.ensure_one()
        user = self.env.user
        author = user.partner_id if not user._is_superuser() and not user.share else (
            self.env.ref("base.partner_root")
        )
        body = whatsapp_to_html(wa_message.body or "")
        if wa_message.template_id:
            body = Markup("%s<br/><i>%s</i>") % (
                body, _("Template: %s", wa_message.template_id.name)
            )
        message = self.with_context(whatsapp_skip_send=True).message_post(
            author_id=author.id,
            body=body,
            message_type="whatsapp_message",
            subtype_xmlid="mail.mt_comment",
            date=wa_message.create_date,
            silent=True,
        )
        wa_message.write({"mail_message_id": message.id, "channel_id": self.id})
        if wa_message.state != "queued":
            wa_message._bus_send_status()
        return message

    # === COMMANDS AND ACTIONS (Discuss) === #

    def execute_command_note(self, body="", **kwargs):
        """/note text: an internal note in the conversation, never sent to the customer."""
        self.ensure_one()
        text = (body or "").strip()
        text = text.removeprefix("/note").strip()
        if not text or self.channel_type != "whatsapp" or self.env.user.share:
            return
        self.with_context(whatsapp_skip_send=True).message_post(
            body=Markup("<p>🔒 <b>%s</b> %s</p>") % (_("Internal note:"), text),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
            author_id=self.env.user.partner_id.id,
        )

    def _whatsapp_check_agent(self):
        self.check_access("read")
        if not self.env.user.has_group("whatsapp_cloud.group_whatsapp_user"):
            raise AccessError(_("Only the WhatsApp agents can handle the conversations."))
        if any(channel.channel_type != "whatsapp" for channel in self):
            raise UserError(_("This is not a WhatsApp conversation."))

    def whatsapp_action_take(self):
        """The current user handles the conversation."""
        self._whatsapp_check_agent()
        for channel in self.sudo():
            channel._whatsapp_assign(self.env.user)

    def whatsapp_action_resolve(self):
        self._whatsapp_check_agent()
        for channel in self.sudo():
            channel.write({
                "whatsapp_state": "done",
                "whatsapp_waiting_since": False,
                "whatsapp_alert_level": 0,
            })
            channel._whatsapp_notify(_("Conversation resolved by %s.", self.env.user.name))

    def whatsapp_action_reopen(self):
        self._whatsapp_check_agent()
        for channel in self.sudo():
            channel.whatsapp_state = "open" if channel.whatsapp_user_id else "new"
            channel._whatsapp_notify(_("Conversation reopened by %s.", self.env.user.name))

    def whatsapp_action_transfer(self):
        self._whatsapp_check_agent()
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Transfer the Conversation"),
            "res_model": "whatsapp.conversation.assign",
            "view_mode": "form",
            "target": "new",
            "context": {"default_channel_id": self.id},
        }

    def whatsapp_action_send_template(self):
        self._whatsapp_check_agent()
        self.ensure_one()
        partner = self.whatsapp_partner_id
        if not partner:
            raise UserError(_("The conversation has no customer."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Send a Template"),
            "res_model": "whatsapp.composer",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_res_model": "res.partner",
                "default_res_ids": partner.ids,
                "whatsapp_channel_id": self.id,
            },
        }

    def whatsapp_action_link_partner(self):
        self._whatsapp_check_agent()
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Identify the Customer"),
            "res_model": "whatsapp.link.partner",
            "view_mode": "form",
            "target": "new",
            "context": {"default_channel_id": self.id},
        }

    def whatsapp_action_confirm_partner(self):
        self._whatsapp_check_agent()
        self.sudo().whatsapp_partner_id.action_whatsapp_confirm_contact()

    def whatsapp_action_open_partner(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": self.whatsapp_partner_id.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def whatsapp_action_set_tags(self, tag_ids):
        self._whatsapp_check_agent()
        self.sudo().whatsapp_tag_ids = [Command.set(tag_ids)]

    def whatsapp_action_open(self):
        """Open the conversation in Discuss."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "mail.action_discuss",
            "params": {"active_id": f"discuss.channel_{self.id}"},
        }

    def whatsapp_get_info(self):
        self.ensure_one()
        self._whatsapp_check_agent()
        return self.sudo()._whatsapp_get_info()

    def _whatsapp_get_info(self):
        """Information on the customer shown next to the conversation."""
        self.ensure_one()
        partner = self.whatsapp_partner_id
        return {
            "partner": partner and {
                "id": partner.id,
                "name": partner.display_name,
                "phone": partner.phone or "",
                "email": partner.email or "",
                "username": partner.whatsapp_username or "",
                "opt_in": partner.whatsapp_opt_in,
                "to_identify": partner.whatsapp_to_identify,
            },
            "account": self.whatsapp_account_id.name,
            "sections": self._whatsapp_get_info_sections(),
            "tags": [{"id": t.id, "name": t.name, "color": t.color} for t in self.whatsapp_tag_ids],
            "all_tags": [
                {"id": t.id, "name": t.name, "color": t.color}
                for t in self.env["whatsapp.tag"].search([])
            ],
        }

    def _whatsapp_get_info_sections(self):
        """Hook: lists shown in the information panel, e.g. the orders of the customer:
        [{"title": str, "items": [{"name", "detail", "model", "id"}]}]."""
        return []
