import hashlib
import hmac
import logging
import re
import secrets
from datetime import UTC, timedelta
from zoneinfo import ZoneInfo

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL
from odoo.tools.urls import urljoin as url_join

from odoo.addons.whatsapp_cloud import const

_logger = logging.getLogger(__name__)


class WhatsAppApiError(Exception):
    """Error returned by the Graph API (or no answer from it)."""

    def __init__(self, message, code=None, retryable=False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable or code in const.RETRYABLE_ERROR_CODES


class WhatsappAccount(models.Model):
    _name = "whatsapp.account"
    _description = "WhatsApp Business Account"
    _inherit = ["mail.thread"]
    _order = "sequence, id"

    name = fields.Char(required=True, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    phone_number_id = fields.Char(
        string="Phone Number ID",
        required=True,
        tracking=True,
        help="In the Meta app, WhatsApp > API Setup: the ID of the phone number that sends the "
        "messages.",
    )
    waba_id = fields.Char(
        string="WhatsApp Business Account ID",
        required=True,
        tracking=True,
        help="In the Meta app, WhatsApp > API Setup: the ID of the WhatsApp Business account.",
    )
    app_id = fields.Char(
        string="App ID",
        tracking=True,
        help="In the Meta app, App settings > Basic: needed only to submit templates with a "
        "document, an image or a video in their header (sample uploaded to Meta).",
    )
    access_token = fields.Char(
        required=True,
        copy=False,
        groups="base.group_system",
        help="Permanent token of a system user of the Meta Business portfolio, with the "
        "whatsapp_business_messaging and whatsapp_business_management permissions.",
    )
    app_secret = fields.Char(
        copy=False,
        groups="base.group_system",
        help="In the Meta app, App settings > Basic: used to check that the webhook calls come "
        "from Meta. Without it, the receipts and replies are refused.",
    )
    verify_token = fields.Char(
        string="Webhook Verify Token",
        required=True,
        copy=False,
        groups="base.group_system",
        default=lambda self: secrets.token_urlsafe(24),
        help="To enter in the webhook settings of the Meta app, with the callback URL.",
    )
    api_version = fields.Char(
        string="API Version", required=True, default=const.DEFAULT_API_VERSION
    )
    require_opt_in = fields.Boolean(
        string="Only to Contacts who Agreed",
        default=True,
        help="Send the notifications only to the contacts who agreed to receive WhatsApp messages "
        "(box ticked at checkout or on the contact), as required by the WhatsApp Business "
        "policy. The answers to the customers who write are always allowed.",
    )
    webhook_url = fields.Char(string="Callback URL", compute="_compute_webhook_url")
    test_phone = fields.Char(
        string="Test Number", help="Number that receives the test message (hello_world template)."
    )
    template_count = fields.Integer(compute="_compute_counts")
    message_count = fields.Integer(compute="_compute_counts")
    conversation_count = fields.Integer(compute="_compute_counts")

    # === Team === #
    agent_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="whatsapp_account_agent_rel",
        column1="account_id",
        column2="user_id",
        string="Agents",
        domain=[("share", "=", False)],
        help="Users who answer the conversations of this number. When empty: all the WhatsApp "
        "agents.",
    )
    assignment_mode = fields.Selection(
        selection=[
            ("manual", "Taken by an agent"),
            ("round_robin", "Each agent in turn"),
        ],
        string="Assignment",
        default="manual",
        required=True,
        help="Taken by an agent: all the agents see the new conversation, the first one who "
        "answers (or takes it) handles it. Each agent in turn: the conversation goes to the "
        "agent with the fewest open conversations, online agents first.",
    )
    escalation_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="whatsapp_account_escalation_rel",
        column1="account_id",
        column2="user_id",
        string="Managers to Alert",
        domain=[("share", "=", False)],
        help="Added to the conversations that wait too long for an answer. When empty: the "
        "WhatsApp managers.",
    )
    response_delay = fields.Integer(
        string="Answer within (minutes)",
        default=15,
        help="Opening hours after which the agent is reminded of a message without answer "
        "(0: never).",
    )
    escalation_delay = fields.Integer(
        string="Alert the managers after (minutes)",
        default=60,
        help="Opening hours after which the managers are alerted of a message without answer "
        "(0: never).",
    )
    resource_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Opening Hours",
        default=lambda self: self.env.company.resource_calendar_id,
        help="Hours when the team answers, with the public holidays (Time off of the working "
        "schedule): the answer delays count only these hours, and the away message is sent "
        "outside of them.",
    )

    # === Automatic answers === #
    away_message_enabled = fields.Boolean(string="Send an Away Message", default=True)
    away_message = fields.Text(
        translate=True,
        help="Sent outside of the opening hours, at most once every 12 hours to a customer.",
    )
    bot_enabled = fields.Boolean(
        string="Welcome Menu",
        default=True,
        help="A new conversation starts with the welcome message and the menu of the options; "
        "the conversation goes to an agent when the customer asks for it or writes something "
        "the menu does not handle.",
    )
    welcome_message = fields.Text(translate=True)
    handover_message = fields.Text(
        translate=True,
        help="Sent when a message of the customer that the menu does not handle goes to the "
        "team (the customer already wrote what they need).",
    )
    handover_invite_message = fields.Text(
        string="Invitation to Write",
        translate=True,
        help="Sent when the customer asks for a person (option of the menu, \"advisor\"...): "
        "invites them to write what they need, so that the agent can answer at once.",
    )
    stop_message = fields.Text(
        translate=True, help="Sent when a customer answers STOP to stop the notifications."
    )
    start_message = fields.Text(
        translate=True, help="Sent when a customer answers START to receive them again."
    )
    bot_option_ids = fields.One2many(
        comodel_name="whatsapp.bot.option", inverse_name="account_id", string="Menu Options",
        domain=[("parent_id", "=", False)], context={"active_test": False}, copy=True,
    )

    # === Health === #
    display_phone_number = fields.Char(string="Phone Number", readonly=True)
    verified_name = fields.Char(string="WhatsApp Display Name", readonly=True)
    name_status = fields.Char(string="Display Name Status", readonly=True)
    number_status = fields.Char(string="Number Status", readonly=True)
    quality_rating = fields.Selection(
        selection=[
            ("GREEN", "High"),
            ("YELLOW", "Medium"),
            ("RED", "Low"),
            ("UNKNOWN", "Unknown"),
        ],
        string="Quality",
        readonly=True,
        help="Quality rating of the number at Meta, based on how the customers received the "
        "recent messages (blocks, reports).",
    )
    messaging_limit = fields.Char(
        string="Messaging Limit",
        readonly=True,
        help="Number of customers who can receive a template outside of the 24-hour window, in "
        "24 hours, for the whole Meta Business portfolio.",
    )
    health_state = fields.Selection(
        selection=[("ok", "OK"), ("warning", "Warning"), ("error", "Error")],
        string="Health",
        readonly=True,
    )
    health_message = fields.Text(string="Health Details", readonly=True)
    health_check_date = fields.Datetime(string="Last Check", readonly=True)
    last_webhook_date = fields.Datetime(
        string="Last Call from Meta", compute="_compute_last_webhook_date"
    )

    _phone_number_id_uniq = models.Constraint(
        "unique(phone_number_id)", "This phone number is already used by another account."
    )

    @api.depends("company_id")
    def _compute_webhook_url(self):
        for account in self:
            account.webhook_url = url_join(account.get_base_url(), "/whatsapp/webhook")

    def _compute_counts(self):
        def counts(model, domain):
            return dict(self.env[model]._read_group(
                [("whatsapp_account_id" if model == "discuss.channel" else "account_id",
                  "in", self.ids), *domain],
                ["whatsapp_account_id" if model == "discuss.channel" else "account_id"],
                ["__count"],
            ))

        templates = counts("whatsapp.template", [])
        messages = counts("whatsapp.message", [])
        conversations = counts("discuss.channel", [("channel_type", "=", "whatsapp")])
        for account in self:
            account.template_count = templates.get(account, 0)
            account.message_count = messages.get(account, 0)
            account.conversation_count = conversations.get(account, 0)

    def _compute_last_webhook_date(self):
        if not self.ids:
            self.last_webhook_date = False
            return
        self.env.cr.execute(SQL(
            "SELECT account_id, MAX(create_date) FROM whatsapp_webhook_event "
            "WHERE account_id IN %s GROUP BY account_id",
            tuple(self.ids),
        ))
        dates = dict(self.env.cr.fetchall())
        for account in self:
            account.last_webhook_date = dates.get(account.id)

    @api.model_create_multi
    def create(self, vals_list):
        accounts = super().create(vals_list)
        for account, vals in zip(accounts, vals_list):
            account._set_default_texts(vals)
            # the form of the account sends an empty list of options
            if not vals.get("bot_option_ids"):
                account._create_default_bot_options()
                account._ensure_lang_options()
        return accounts

    # === DEFAULTS === #

    def _get_default_texts(self):
        """Default automatic answers, in English (translated by the module's translations)."""
        return {
            "away_message": self.env._(
                "Thank you for your message! We are closed right now: an advisor will answer you "
                "as soon as we open."
            ),
            "welcome_message": self.env._(
                "Hello and welcome! How can we help you? Choose an option below, or write your "
                "question."
            ),
            "handover_message": self.env._(
                "Thank you, an advisor will answer you here as soon as possible."
            ),
            "handover_invite_message": self.env._(
                "Tell us here what you need (order number, item, question), you can also send a "
                "photo: an advisor will answer you as soon as possible."
            ),
            "stop_message": self.env._(
                "You will no longer receive our WhatsApp notifications. Send START to receive "
                "them again."
            ),
            "start_message": self.env._(
                "Thank you! You will receive our WhatsApp notifications again. Send STOP to stop "
                "them."
            ),
        }

    def _set_default_texts(self, vals=None):
        """Fill the empty automatic answers in each installed language."""
        langs = [code for code, _name in self.env["res.lang"].get_installed()]
        for account in self:
            missing = [
                fname for fname in account._get_default_texts()
                if not (vals or {}).get(fname) and not account[fname]
            ]
            if not missing:
                continue
            default_texts = account.with_context(lang="en_US")._get_default_texts()
            account.with_context(lang="en_US").write(
                {fname: default_texts[fname] for fname in missing}
            )
            for lang in langs:
                if lang == "en_US":
                    continue
                texts = account.with_context(lang=lang)._get_default_texts()
                for fname in missing:
                    account.update_field_translations(fname, {lang: texts[fname]})

    def _get_default_bot_options(self):
        """Options of the welcome menu created with the account; the modules add theirs.
        The ones that are not active are ready to be enabled."""
        options = [{
            "sequence": 100,
            "name": self.env._("Talk to an advisor"),
            "description": self.env._("A person of the team answers you"),
            "action": "handover",
        }, {
            "sequence": 80,
            "name": self.env._("Stop notifications"),
            "description": self.env._("No more WhatsApp messages about your orders"),
            "action": "stop",
            "active": False,
        }, {
            "sequence": 81,
            "name": self.env._("Get notifications"),
            "description": self.env._("WhatsApp messages about your orders"),
            "action": "start",
            "active": False,
        }]
        return options

    def _ensure_lang_options(self):
        """One "Change the language" option per installed language, named in its own
        language and disabled (ready to be enabled): at the creation of the account, and when
        a language is installed later."""
        installed = self.env["res.lang"].get_installed()
        Option = self.env["whatsapp.bot.option"].sudo().with_context(lang="en_US")
        for account in self:
            existing = set(account.bot_option_ids.filtered(lambda o: o.action == "lang").mapped("lang"))
            for code, name in installed:
                if code in existing:
                    continue
                option = Option.create({
                    "account_id": account.id,
                    "sequence": 90,
                    "name": re.sub(r"\s*\(.*\)$", "", name.split("/")[-1].strip())[:const.MAX_BUTTON_TITLE],
                    "description": account.with_context(lang="en_US").env._("Change the language"),
                    "action": "lang",
                    "lang": code,
                    "active": False,
                })
                for lang, _name in installed:
                    if lang != "en_US":
                        option.update_field_translations("description", {
                            lang: account.with_context(lang=lang).env._("Change the language"),
                        })

    def _create_default_bot_options(self, actions=None):
        """Create the default options of the welcome menu (only those of the given actions),
        translated in the installed languages."""
        langs = [code for code, _name in self.env["res.lang"].get_installed()]
        for account in self:

            def options_vals(lang, account=account):
                # the limits of WhatsApp, whatever the length of the translations
                return [
                    {**vals,
                     "name": vals["name"][:const.MAX_BUTTON_TITLE],
                     "description": (vals.get("description") or "")[:const.MAX_ROW_DESCRIPTION]}
                    for vals in account.with_context(lang=lang)._get_default_bot_options()
                    if actions is None or vals["action"] in actions
                ]

            options = self.env["whatsapp.bot.option"].with_context(lang="en_US").create([
                {**vals, "account_id": account.id} for vals in options_vals("en_US")
            ])
            for lang in langs:
                if lang == "en_US":
                    continue
                for option, vals in zip(options, options_vals(lang)):
                    for fname in ("name", "description", "answer"):
                        if vals.get(fname):
                            option.update_field_translations(fname, {lang: vals[fname]})

    # === GRAPH API === #

    def _api_request(self, method, path, *, params=None, json=None, data=None, files=None,
                     timeout=20):
        """Call the Graph API with the token of the account.

        :param str method: HTTP method.
        :param str path: path after the version, e.g. ``<phone_number_id>/messages``.
        :return: the JSON answer.
        :rtype: dict
        :raise WhatsAppApiError: if Meta answers with an error, or does not answer.
        """
        self.ensure_one()
        url = f"{const.GRAPH_URL}/{self.api_version}/{path}"
        headers = {"Authorization": f"Bearer {self.sudo().access_token}"}
        try:
            response = requests.request(
                method, url, params=params, json=json, data=data, files=files, headers=headers,
                timeout=timeout,
            )
        except requests.exceptions.RequestException as error:
            _logger.warning("WhatsApp: no answer from Meta for %s %s: %s", method, path, error)
            raise WhatsAppApiError(
                _("No answer from WhatsApp (Meta): %s", error), retryable=True
            ) from error
        try:
            result = response.json()
        except ValueError:
            result = {}
        if not response.ok or "error" in result:
            error = result.get("error") or {}
            details = (error.get("error_data") or {}).get("details")
            message = " ".join(filter(None, [
                error.get("error_user_msg") or error.get("message") or response.reason, details,
            ]))
            _logger.info("WhatsApp: error %s from Meta for %s %s: %s",
                         error.get("code"), method, path, message)
            raise WhatsAppApiError(
                message, code=error.get("code"), retryable=response.status_code >= 500
            )
        return result

    def _upload_media(self, attachment):
        """Upload a file to the media of the phone number; return the media ID."""
        self.ensure_one()
        result = self._api_request(
            "POST",
            f"{self.phone_number_id}/media",
            data={"messaging_product": "whatsapp", "type": attachment.mimetype},
            files={"file": (attachment.name, attachment.raw, attachment.mimetype)},
            timeout=60,
        )
        return result["id"]

    def _download_media(self, media_id, url=None):
        """Download a media received from a customer.

        The webhook gives a download URL (recent payloads), else it is asked to Meta from
        the media ID; such a URL is valid for 5 minutes only, and the media ID for 7 days.

        :return: (content, mimetype)
        :rtype: tuple
        :raise WhatsAppApiError: if Meta refuses or the file is too big.
        """
        self.ensure_one()
        mimetype = None
        if url:
            try:
                return self._download_url(url)
            except WhatsAppApiError as error:
                _logger.info("WhatsApp: media %s not downloaded from the webhook URL (%s), "
                             "asking a new URL.", media_id, error)
        info = self._api_request(
            "GET", media_id, params={"phone_number_id": self.phone_number_id}
        )
        if int(info.get("file_size") or 0) > const.MAX_MEDIA_SIZE:
            raise WhatsAppApiError(_("The file is too big (%s bytes).", info["file_size"]))
        content, mimetype = self._download_url(info["url"])
        return content, info.get("mime_type") or mimetype

    def _download_url(self, url):
        """Download a media URL of Meta (with the token, as required); (content, mimetype)."""
        headers = {"Authorization": f"Bearer {self.sudo().access_token}"}
        try:
            response = requests.get(url, headers=headers, timeout=60, stream=True)
            response.raise_for_status()
            chunks, size = [], 0
            for chunk in response.iter_content(chunk_size=65536):
                size += len(chunk)
                if size > const.MAX_MEDIA_SIZE:
                    raise WhatsAppApiError(_("The file is too big."))
                chunks.append(chunk)
        except requests.exceptions.RequestException as error:
            raise WhatsAppApiError(
                _("The file could not be downloaded from WhatsApp: %s", error), retryable=True
            ) from error
        return b"".join(chunks), response.headers.get("Content-Type")

    def _send_read_receipt(self, wa_message_id, typing=False):
        """Mark a message of a customer as read (blue ticks), and show "typing..." to them."""
        self.ensure_one()
        payload = {"messaging_product": "whatsapp", "status": "read", "message_id": wa_message_id}
        if typing:
            payload["typing_indicator"] = {"type": "text"}
        return self._api_request("POST", f"{self.phone_number_id}/messages", json=payload)

    def _check_signature(self, payload, signature):
        """Whether the webhook payload was signed by Meta with the app secret of the account."""
        self.ensure_one()
        secret = self.sudo().app_secret
        if not secret or not signature:
            return False
        expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    # === TEAM === #

    def _get_agents(self):
        """Users who answer the conversations of the account."""
        self.ensure_one()
        agents = self.agent_user_ids or self.env.ref("whatsapp_cloud.group_whatsapp_user").sudo().all_user_ids
        return agents.filtered(lambda user: user.active and not user.share and (
            self.company_id in user.company_ids
        ) and not user._is_superuser())

    def _get_team_lang(self):
        """Language of the notices for the team (automatic tasks, webhook): the most common
        language of the agents, else the one of the company."""
        self.ensure_one()
        langs = [user.lang for user in self._get_agents() if user.lang]
        if langs:
            return max(sorted(set(langs)), key=langs.count)
        return self.company_id.partner_id.lang or self.env.lang or "en_US"

    def _get_escalation_users(self):
        self.ensure_one()
        users = self.escalation_user_ids or self.env.ref(
            "whatsapp_cloud.group_whatsapp_manager"
        ).sudo().all_user_ids
        return users.filtered(lambda user: user.active and not user.share and not user._is_superuser())

    def _pick_agent(self, agents=None):
        """The agent who gets the next conversation: online first, then the fewest open
        conversations, then the one who got a conversation the longest time ago."""
        self.ensure_one()
        agents = agents if agents is not None else self._get_agents()
        if not agents:
            return self.env["res.users"]
        Channel = self.env["discuss.channel"].sudo()
        open_counts = dict(Channel._read_group(
            [("channel_type", "=", "whatsapp"), ("whatsapp_user_id", "in", agents.ids),
             ("whatsapp_state", "!=", "done")],
            ["whatsapp_user_id"], ["__count"],
        ))
        last_assignments = dict(Channel._read_group(
            [("channel_type", "=", "whatsapp"), ("whatsapp_user_id", "in", agents.ids)],
            ["whatsapp_user_id"], ["whatsapp_assigned_date:max"],
        ))
        oldest = fields.Datetime.from_string("2000-01-01 00:00:00")
        return min(agents, key=lambda user: (
            user.im_status != "online",
            open_counts.get(user, 0),
            last_assignments.get(user) or oldest,
            user.id,
        ))

    def _is_open(self, date=None):
        """Whether the team works at this date (opening hours and public holidays)."""
        self.ensure_one()
        calendar = self.resource_calendar_id
        if not calendar:
            return True
        start = self._to_calendar_tz(date or fields.Datetime.now())
        intervals = calendar._work_intervals_batch(start, start + timedelta(minutes=1))[False]
        return bool(list(intervals))

    def _get_working_minutes(self, start, end):
        """Minutes of opening hours between two dates (all the minutes without hours)."""
        self.ensure_one()
        if end <= start:
            return 0
        calendar = self.resource_calendar_id
        if not calendar:
            return (end - start).total_seconds() / 60
        return calendar.get_work_hours_count(
            self._to_calendar_tz(start), self._to_calendar_tz(end), compute_leaves=True
        ) * 60

    def _to_calendar_tz(self, date):
        """A date of the database (naive, UTC) in the time zone of the company: the hours of
        the working schedule are read in the time zone of the given dates."""
        self.ensure_one()
        tz = ZoneInfo(self.company_id.tz or self.company_id.partner_id.tz or "UTC")
        return date.replace(tzinfo=UTC).astimezone(tz)

    # === ACTIONS === #

    def action_sync_templates(self):
        """Create or update the templates of the account from the ones defined at Meta."""
        self.ensure_one()
        Template = self.env["whatsapp.template"]
        params = {
            "fields": "id,name,language,status,category,components,parameter_format,"
                      "rejected_reason,quality_score",
            "limit": 100,
        }
        created = updated = 0
        while True:
            try:
                result = self._api_request(
                    "GET", f"{self.waba_id}/message_templates", params=params
                )
            except WhatsAppApiError as error:
                raise UserError(
                    _("The templates could not be read from WhatsApp: %s",
                      self._get_error_text(error))
                ) from error
            for data in result.get("data", []):
                template = Template._find_from_meta(self, data)
                vals = Template._prepare_vals_from_meta(data)
                if template:
                    if vals["status"] == "rejected":
                        # Refused by Meta: the text of Odoo is the one being corrected (by the team
                        # or a module), Meta keeps the refused one; only the decision is read
                        vals = {
                            key: vals[key]
                            for key in ("status", "rejected_reason", "quality_score", "wa_template_id")
                            if key in vals
                        }
                    template.write(vals)
                    updated += 1
                else:
                    Template.create({**vals, "account_id": self.id, "name": data["name"]})
                    created += 1
            after = result.get("paging", {}).get("cursors", {}).get("after")
            if not after or not result.get("paging", {}).get("next"):
                break
            params["after"] = after
        return self._notify(
            _("Templates synchronised: %(created)s new, %(updated)s updated.",
              created=created, updated=updated),
            "success",
        )

    def action_send_test(self):
        """Send the "hello_world" template of Meta to the test number."""
        self.ensure_one()
        number = self.env["res.partner"]._whatsapp_normalize_number(
            self.test_phone, self.company_id.country_id
        )
        if not number:
            raise UserError(_("Enter the number that receives the test message."))
        try:
            self._api_request("POST", f"{self.phone_number_id}/messages", json={
                "messaging_product": "whatsapp",
                "to": number,
                "type": "template",
                "template": {"name": "hello_world", "language": {"code": "en_US"}},
            })
        except WhatsAppApiError as error:
            raise UserError(
                _("The test message was not sent: %s", self._get_error_text(error))
            ) from error
        return self._notify(_("Test message sent to +%s.", number), "success")

    def action_check_health(self):
        self.ensure_one()
        self._check_health()
        notification_type = {"ok": "success", "warning": "warning"}.get(
            self.health_state, "danger"
        )
        return self._notify(self.health_message or _("The account is working."), notification_type)

    def action_open_templates(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Templates"),
            "res_model": "whatsapp.template",
            "view_mode": "list,form",
            "domain": [("account_id", "=", self.id)],
            "context": {"default_account_id": self.id},
        }

    def action_open_messages(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Messages"),
            "res_model": "whatsapp.message",
            "view_mode": "list,form",
            "domain": [("account_id", "=", self.id)],
        }

    def action_open_conversations(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "whatsapp_cloud.discuss_channel_action_whatsapp"
        )
        action["domain"] = [("channel_type", "=", "whatsapp"), ("whatsapp_account_id", "=", self.id)]
        return action

    def _notify(self, message, notification_type):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"message": message, "type": notification_type, "sticky": False},
        }

    @api.model
    def _get_default_account(self, company):
        """The account used by the templates linked to no account."""
        return self.search([("company_id", "=", company.id)], limit=1) or self.search([], limit=1)

    @api.model
    def _get_error_text(self, error):
        """The error of Meta, with what to do about it when known."""
        help_text = const.ERROR_HELP.get(getattr(error, "code", None))
        return f"{error} {help_text}" if help_text else str(error)

    # === HEALTH === #

    def _check_health(self):
        """Read the status of the number at Meta, and alert the managers when it degrades."""
        for account in self:
            previous_state = account.health_state
            vals = {"health_check_date": fields.Datetime.now()}
            problems, warnings = [], []
            try:
                data = account._api_request("GET", account.phone_number_id, params={
                    "fields": "display_phone_number,verified_name,name_status,quality_rating,"
                              "status,health_status,whatsapp_business_manager_messaging_limit",
                })
            except WhatsAppApiError as error:
                problems.append(account._get_error_text(error))
                data = {}
            if data:
                quality = (data.get("quality_rating") or "UNKNOWN").upper()
                vals.update({
                    "display_phone_number": data.get("display_phone_number"),
                    "verified_name": data.get("verified_name"),
                    "name_status": data.get("name_status"),
                    "number_status": data.get("status"),
                    "quality_rating": quality if quality in ("GREEN", "YELLOW", "RED") else "UNKNOWN",
                    "messaging_limit": data.get("whatsapp_business_manager_messaging_limit"),
                })
                health = data.get("health_status") or {}
                can_send = (health.get("can_send_message") or "").upper()
                details = [
                    error.get("error_description") or error.get("possible_solution") or ""
                    for entity in health.get("entities") or []
                    for error in entity.get("errors") or []
                ]
                if can_send == "BLOCKED":
                    problems.append(" ".join(filter(None, [
                        _("Meta blocks the sending of messages."), *details,
                    ])))
                elif can_send == "LIMITED":
                    warnings.append(_("Meta limits the sending of messages."))
                if quality == "RED":
                    problems.append(_(
                        "The quality of the number is low: many customers blocked or reported "
                        "the recent messages. Send fewer messages, only to customers who agreed."
                    ))
                elif quality == "YELLOW":
                    warnings.append(_(
                        "The quality of the number is medium: some customers blocked or reported "
                        "the recent messages."
                    ))
                status = (data.get("status") or "").upper()
                if status and status not in ("CONNECTED", "MIGRATED"):
                    problems.append(_("The number is %s at Meta.", status))
                name_status = (data.get("name_status") or "").upper()
                if name_status and name_status not in ("APPROVED", "AVAILABLE_WITHOUT_REVIEW"):
                    warnings.append(_("The display name is %s at Meta.", name_status))
            if not account.sudo().app_secret:
                warnings.append(_(
                    "No app secret: the replies of the customers and the receipts are refused."
                ))
            vals["health_state"] = "error" if problems else "warning" if warnings else "ok"
            vals["health_message"] = "\n".join(problems + warnings) or False
            account.write(vals)
            if vals["health_state"] != previous_state and vals["health_state"] != "ok":
                account._alert_managers(
                    _("WhatsApp account %(name)s: %(details)s",
                      name=account.name, details=vals["health_message"])
                )

    @api.model
    def _cron_check_health(self):
        for account in self.search([]):
            account = account.with_context(lang=account._get_team_lang())
            account._check_health()
            account._check_webhook_silence()

    def _check_webhook_silence(self, hours=6):
        """Alert when messages were sent but Meta did not call back for hours: the webhook
        is probably broken (URL, certificate, subscription, app secret)."""
        limit = fields.Datetime.now() - timedelta(hours=hours)
        for account in self:
            sent = self.env["whatsapp.message"].search_count([
                ("account_id", "=", account.id),
                ("direction", "=", "outgoing"),
                ("state", "=", "sent"),
                ("sent_date", "<", limit),
                ("sent_date", ">", limit - timedelta(days=1)),
            ], limit=1)
            if sent and (not account.last_webhook_date or account.last_webhook_date < limit):
                account._alert_managers(_(
                    "WhatsApp account %(name)s: no receipt from Meta for %(hours)s hours although "
                    "messages were sent. Check the webhook of the Meta app (callback URL, "
                    "subscription to the messages field) and the app secret.",
                    name=account.name, hours=hours,
                ))

    def _alert_managers(self, text):
        """Note on the account, and notification to the managers in their inbox."""
        self.ensure_one()
        partners = self._get_escalation_users().partner_id
        self.message_post(
            body=text,
            partner_ids=partners.ids,
            message_type="notification",
            subtype_xmlid="mail.mt_comment",
        )
