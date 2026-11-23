import logging
import re
from datetime import UTC, datetime, timedelta

import psycopg2

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.whatsapp_cloud_call import const

_logger = logging.getLogger(__name__)

FINAL_STATES = ("completed", "missed", "voicemail", "lost", "failed")


def clean_number(value):
    """The number of a customer, digits only; empty when Meta gives their WhatsApp user ID
    (BSUID) instead (a customer who hides their number behind a WhatsApp username)."""
    value = str(value or "").strip()
    return value.lstrip("+") if re.fullmatch(r"\+?\d{6,15}", value) else ""


def format_duration(env, seconds):
    """'3 min 12 s', '45 s', '1 h 02 min'."""
    seconds = int(seconds or 0)
    if seconds < 60:
        return env._("%s s", seconds)
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return env._("%(minutes)s min %(seconds)02d s", minutes=minutes, seconds=seconds)
    hours, minutes = divmod(minutes, 60)
    return env._("%(hours)s h %(minutes)02d min", hours=hours, minutes=minutes)


class WhatsappCall(models.Model):
    """A call of a customer on WhatsApp, as told by the call server (FreeSWITCH) and by Meta."""

    _name = "whatsapp.call"
    _description = "WhatsApp Call"
    _order = "start_date desc, id desc"

    account_id = fields.Many2one(
        comodel_name="whatsapp.account", string="WhatsApp Account", required=True, index=True,
        ondelete="cascade", readonly=True,
    )
    company_id = fields.Many2one(related="account_id.company_id", store=True)
    channel_id = fields.Many2one(
        comodel_name="discuss.channel", string="Conversation", index="btree_not_null",
        ondelete="set null", readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Customer", index="btree_not_null", ondelete="set null",
        readonly=True,
    )
    number = fields.Char(string="Number of the Customer", readonly=True)
    user_ref = fields.Char(
        string="WhatsApp ID of the Customer", readonly=True,
        help="ID of the customer for the company at WhatsApp (BSUID), given by Meta also when "
        "the customer hides their number behind a WhatsApp username.",
    )
    wacid = fields.Char(string="Call ID at Meta", readonly=True, index=True, copy=False)
    server_uuid = fields.Char(string="Call ID on the Call Server", readonly=True, copy=False)
    direction = fields.Selection(
        selection=[("inbound", "Customer calls"), ("outbound", "Company calls")],
        default="inbound", required=True, readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("ringing", "Waiting"),
            ("answered", "In progress"),
            ("completed", "Completed"),
            ("missed", "Missed"),
            ("voicemail", "Voicemail"),
            ("lost", "Lost"),
            ("failed", "Failed"),
        ],
        default="ringing", required=True, index=True, readonly=True,
    )
    start_date = fields.Datetime(
        string="Called on", default=fields.Datetime.now, required=True, readonly=True, index=True
    )
    answer_date = fields.Datetime(string="Answered on", readonly=True)
    end_date = fields.Datetime(string="Ended on", readonly=True)
    wait_duration = fields.Integer(string="Waiting (s)", readonly=True)
    duration = fields.Integer(string="Duration (s)", readonly=True)
    duration_display = fields.Char(string="Duration", compute="_compute_displays")
    wait_display = fields.Char(string="Waiting", compute="_compute_displays")
    user_id = fields.Many2one(
        comodel_name="res.users", string="Answered by", index="btree_not_null",
        ondelete="set null", readonly=True,
    )
    declined_user_ids = fields.Many2many(
        comodel_name="res.users", relation="whatsapp_call_declined_rel", string="Declined by",
        readonly=True,
    )
    reconnect_count = fields.Integer(
        string="Agent Cut Off", readonly=True,
        help="Times the agent was cut off (network, closed page) and the call came back while "
        "the customer waited.",
    )
    ended_by = fields.Selection(
        selection=[("customer", "Customer"), ("agent", "Agent"), ("system", "Call server")],
        readonly=True,
    )
    end_cause = fields.Char(string="End Cause", readonly=True)
    voicemail_attachment_id = fields.Many2one(
        comodel_name="ir.attachment", string="Message", readonly=True, ondelete="set null"
    )
    server_seen = fields.Boolean(
        string="Seen by the Call Server", readonly=True,
        help="The call server took the call (else only Meta told it).",
    )
    meta_seen = fields.Boolean(string="Seen by Meta", readonly=True)
    meta_status = fields.Char(string="Status at Meta", readonly=True)
    meta_duration = fields.Integer(string="Duration at Meta (s)", readonly=True)
    notice_message_id = fields.Many2one(comodel_name="mail.message", readonly=True, ondelete="set null")
    in_hours = fields.Boolean(
        string="During the Call Hours", readonly=True,
        help="The call came while the team works (opening hours of the account).",
    )
    available_agents = fields.Integer(
        string="Free Agents", readonly=True,
        help="Agents who took the calls and were free when the call came.",
    )
    phone_trace = fields.Text(
        string="Diagnostic of the Phone", readonly=True,
        help="What the phone of each agent who answered did (version, microphone, network "
        "addresses, answer sent, end), to understand a call that did not connect.",
    )

    _wacid_uniq = models.UniqueIndex(
        "(account_id, wacid) WHERE wacid IS NOT NULL", "This call is already recorded."
    )

    @api.depends("duration", "wait_duration")
    def _compute_displays(self):
        for call in self:
            call.duration_display = format_duration(self.env, call.duration) if call.duration else False
            call.wait_display = format_duration(self.env, call.wait_duration) if call.wait_duration else False

    @api.depends("partner_id", "number", "user_ref", "start_date")
    def _compute_display_name(self):
        for call in self:
            call.display_name = _("Call of %s", call._call_customer_label() or _("Unknown"))

    def _call_customer_label(self):
        """The customer as the team sees them: their contact, else their number, else their
        WhatsApp ID."""
        self.ensure_one()
        return self.partner_id.display_name or (f"+{self.number}" if self.number else self.user_ref or "")

    # === FINDING THE CALL === #

    @api.model
    def _call_get_or_create(self, account, wacid, number=None, server_uuid=None, user_ref=None):
        """The call with this ID of Meta (created by the first of the call server or Meta
        to tell it)."""
        call = self.sudo().search([("account_id", "=", account.id), ("wacid", "=", wacid)], limit=1)
        if call:
            return call
        vals = {"account_id": account.id, "wacid": wacid, "number": number or False,
                "user_ref": user_ref or False, "server_uuid": server_uuid or False,
                "in_hours": account._is_open()}
        try:
            with self.env.cr.savepoint():
                call = self.sudo().create(vals)
                call.flush_recordset()
        except (psycopg2.IntegrityError, ValidationError):
            # created at the same time by the other one (webhook of Meta and call server)
            call = self.sudo().search([("account_id", "=", account.id), ("wacid", "=", wacid)], limit=1)
        return call

    def _call_link_conversation(self):
        """The customer and their conversation (created at their first call, like at their
        first message)."""
        for call in self.filtered(lambda c: (c.number or c.user_ref) and not c.channel_id):
            account = call.account_id
            number, user_ref = call.number or "", call.user_ref or ""
            Partner = self.env["res.partner"].sudo()
            Channel = self.env["discuss.channel"].sudo()
            # the customer of the conversation, once known (as for a message)
            partner = Channel._whatsapp_find(account, number, user_ref).whatsapp_partner_id
            if not partner.active:
                partner = Partner._whatsapp_find(number, user_ref) or Partner._whatsapp_create_unknown(
                    number, user_ref, {}, account
                )
            if user_ref and not partner.whatsapp_user_ref:
                partner.whatsapp_user_ref = user_ref
            channel = Channel._whatsapp_get_or_create(account, number, user_ref, partner)
            call.write({"partner_id": channel.whatsapp_partner_id.id or partner.id, "channel_id": channel.id})

    # === CALL SERVER === #

    @api.model
    def _agent_login(self, user):
        return f"{const.AGENT_PREFIX}{user.id}"

    @api.model
    def _agent_from_login(self, login):
        login = (login or "").split("@")[0]
        if not login.startswith(const.AGENT_PREFIX):
            return self.env["res.users"]
        user_id = login[len(const.AGENT_PREFIX):]
        if not user_id.isdigit():
            return self.env["res.users"]
        return self.env["res.users"].sudo().browse(int(user_id)).exists()

    def _call_busy_users(self):
        """Agents in a call now."""
        return self.sudo().search([("state", "=", "answered"), ("user_id", "!=", False)]).user_id

    def _call_route(self):
        """Who rings for the call: the agents of the account who take the calls, free, who did
        not decline it; the agent of the conversation first."""
        self.ensure_one()
        account = self.account_id
        agents = account._get_agents().filtered("whatsapp_call_available")
        agents -= self._call_busy_users() | self.declined_user_ids
        today = fields.Datetime.now() - timedelta(hours=12)
        counts = dict(self.sudo()._read_group(
            [("user_id", "in", agents.ids), ("start_date", ">", today)], ["user_id"], ["__count"]
        ))
        ordered = agents.sorted(lambda user: (user.im_status != "online", counts.get(user, 0), user.id))
        preferred = self.channel_id.whatsapp_user_id
        first = preferred if preferred in ordered else self.env["res.users"]
        if first:
            ordered = first | (ordered - first)
        # an agent cut off during the call gets it back first
        if self.state == "ringing" and self.user_id and self.reconnect_count and self.user_id in ordered:
            first = self.user_id
            ordered = first | (ordered - first)
        return {
            "call": self.id,
            "name": self._call_customer_label(),
            "channel": self.channel_id.id or "",
            "first": [self._agent_login(user) for user in first],
            "agents": [self._agent_login(user) for user in ordered],
            "max_wait": max(account.call_max_wait, 30),
            "voicemail": 1 if account.call_voicemail else 0,
            "open": 1 if account._is_open() else 0,
        }

    @api.model
    def _server_route(self, values):
        """The call server asks who rings for a new call (or again while the customer waits)."""
        account = self.env["whatsapp.account"]._call_find_by_phone_number_id(
            values.get("phone_number_id"), values.get("business_number")
        )
        if not account:
            _logger.warning("WhatsApp call %s: no account with calls for %s",
                            values.get("wacid"), values.get("phone_number_id"))
            return {}
        number = clean_number(values.get("number"))
        user_ref = (values.get("user_ref") or "").strip()[:64]
        call = self._call_get_or_create(
            account, values.get("wacid") or values.get("uuid"), number, values.get("uuid"), user_ref
        )
        vals = {"server_seen": True}
        if number and not call.number:
            vals["number"] = number
        if user_ref and not call.user_ref:
            vals["user_ref"] = user_ref
        if values.get("uuid") and not call.server_uuid:
            vals["server_uuid"] = values["uuid"]
        if call.state == "lost":
            # the call server took it after all
            vals.update(state="ringing", notice_message_id=False)
        first = not call.server_seen
        call.write(vals)
        call._call_link_conversation()
        route = call._call_route()
        if first:
            # the agents free when the call came (thresholds: voicemail while an agent was free)
            call.available_agents = len(route["agents"])
        return route

    @api.model
    def _server_find(self, values):
        """The call of an event of the call server."""
        call = self.browse()
        if str(values.get("call") or "").isdigit():
            call = self.sudo().browse(int(values["call"])).exists()
        if not call and values.get("wacid"):
            call = self.sudo().search([("wacid", "=", values["wacid"])], limit=1)
        if not call and values.get("uuid"):
            call = self.sudo().search([("server_uuid", "=", values["uuid"])], limit=1)
        if not call and values.get("wacid"):
            # the call server could not reach Odoo when the call arrived
            route = self._server_route(values)
            if route:
                call = self.sudo().browse(route["call"])
        return call

    @api.model
    def _server_event(self, values):
        """An event of the call server: answered, agent cut off, ended."""
        call = self._server_find(values)
        if not call:
            return False
        event = values.get("event")
        user = self._agent_from_login(values.get("agent"))
        if event == "answered" and call.state not in FINAL_STATES:
            now = fields.Datetime.now()
            call.write({
                "state": "answered",
                "user_id": user.id or call.user_id.id,
                "answer_date": call.answer_date or now,
                "wait_duration": int(values.get("wait") or 0) or int((now - call.start_date).total_seconds()),
                "server_seen": True,
            })
            channel = call.channel_id
            if channel and user:
                if channel.whatsapp_user_id != user:
                    channel._whatsapp_assign(user, notify=False)
                channel.sudo().write({"whatsapp_waiting_since": False, "whatsapp_alert_level": 0,
                                      "whatsapp_bot_state": "agent", "whatsapp_state": "open"})
            call._call_bus_send()
        elif event == "agent_lost" and call.state not in FINAL_STATES:
            call.write({
                "state": "ringing",
                "user_id": user.id or call.user_id.id,
                "reconnect_count": call.reconnect_count + 1,
            })
            call._call_bus_send()
        elif event == "ended":
            call._call_end(values)
        return call

    def _call_end(self, values):
        """End of the call, told by the call server (event, or its record of the call)."""
        self.ensure_one()
        if self.state in ("completed", "missed", "voicemail") and self.server_seen and self.end_date:
            # already ended: the record of the call completes the values only
            vals = {}
            if not self.duration and str(values.get("talk") or "").isdigit():
                vals["duration"] = int(values["talk"])
            if not self.ended_by and values.get("ended_by") in ("customer", "agent", "system"):
                vals["ended_by"] = values["ended_by"]
            if not self.end_cause and values.get("cause"):
                vals["end_cause"] = values["cause"][:64]
            if str(values.get("wait") or "").isdigit() and values.get("event") == "ended":
                # the time waited for an agent, as the call server counts it
                vals["wait_duration"] = int(values["wait"])
            if vals:
                self.write(vals)
            return
        outcome = values.get("outcome")
        user = self._agent_from_login(values.get("agent")) or self.user_id
        talk = int(values.get("talk") or 0)
        if outcome not in ("completed", "missed", "voicemail", "failed"):
            outcome = "completed" if talk or user and self.answer_date else "missed"
        if outcome == "voicemail" and not self.account_id.call_voicemail:
            outcome = "missed"
        now = fields.Datetime.now()
        vals = {
            "state": outcome,
            # a call noted lost and told by the call server after all: a new line in the
            # conversation
            "notice_message_id": False if self.state == "lost" else self.notice_message_id.id,
            "server_seen": True,
            "end_date": self.end_date or now,
            "duration": talk or self.duration,
            "wait_duration": int(values.get("wait") or 0) or self.wait_duration
            or int((now - self.start_date).total_seconds()),
            "ended_by": values.get("ended_by") if values.get("ended_by") in ("customer", "agent", "system") else False,
            "end_cause": (values.get("cause") or "")[:64] or False,
        }
        if user and outcome == "completed":
            vals["user_id"] = user.id
            vals["answer_date"] = self.answer_date or now
        if values.get("reconnects") and str(values["reconnects"]).isdigit():
            vals["reconnect_count"] = max(self.reconnect_count, int(values["reconnects"]))
        self.write(vals)
        self._call_post_notice()
        self._call_bus_send()

    @api.model
    def _server_cdr(self, cdr):
        """The record of a call (mod_json_cdr of FreeSWITCH), sent again by the call server
        until Odoo takes it: the end of the call when its event was lost."""
        variables = (cdr or {}).get("variables") or {}
        wacid = variables.get("ocd_wacid")
        if not wacid:
            return False
        values = {
            "event": "ended",
            "wacid": wacid,
            "uuid": variables.get("uuid") or variables.get("call_uuid"),
            "call": variables.get("ocd_call"),
            "number": variables.get("ocd_from"),
            "user_ref": variables.get("ocd_user_ref"),
            "phone_number_id": variables.get("ocd_pnid"),
            "agent": variables.get("ocd_answered_agent"),
            "outcome": variables.get("ocd_outcome"),
            "ended_by": variables.get("ocd_ended_by"),
            "wait": variables.get("ocd_wait"),
            "talk": variables.get("ocd_talk"),
            "reconnects": variables.get("ocd_reconnects"),
            "cause": variables.get("hangup_cause"),
        }
        call = self._server_find(values)
        if not call:
            return False
        call._call_end(values)
        return call

    @api.model
    def _server_voicemail(self, values, content, mimetype):
        """The message left by a customer: posted in their conversation as their voice
        message, the team is asked to answer."""
        call = self._server_find(values)
        if not call:
            return False
        if call.voicemail_attachment_id:
            return call
        call._call_link_conversation()
        channel = call.channel_id
        extension = "ogg" if "ogg" in (mimetype or "") else "wav"
        attachment = self.env["ir.attachment"].sudo().create({
            "name": _("Message of %(name)s.%(ext)s",
                      name=call._call_customer_label(), ext=extension),
            "raw": content,
            "mimetype": mimetype or "audio/wav",
            "res_model": "discuss.channel" if channel else "whatsapp.call",
            "res_id": channel.id if channel else call.id,
        })
        call.write({"voicemail_attachment_id": attachment.id})
        if channel:
            channel = channel.with_context(lang=channel._whatsapp_get_lang())
            channel.with_context(whatsapp_skip_send=True).message_post(
                author_id=call.partner_id.id,
                body=Markup("<p>%s</p>") % _("Voice message left after a call."),
                attachment_ids=attachment.ids,
                message_type="whatsapp_message",
                subtype_xmlid="mail.mt_comment",
            )
        if call.state not in FINAL_STATES:
            call._call_end({**values, "event": "ended", "outcome": "voicemail"})
        elif call.state == "missed":
            call.state = "voicemail"
        return call

    # === META === #

    @api.model
    def _meta_process(self, account, value):
        """Notification of Meta on the calls (webhook "calls"): a call attempted, a call ended.
        With the SIP server, Meta tells only call_created and terminate."""
        for data in value.get("calls") or []:
            wacid = data.get("id")
            if not wacid:
                continue
            direction = (data.get("direction") or "USER_INITIATED").upper()
            # the number of the customer, missing when they hide it behind a WhatsApp username:
            # their WhatsApp user ID (BSUID) then
            side = "from" if direction == "USER_INITIATED" else "to"
            number = clean_number(data.get(side))
            user_ref = str(data.get(f"{side}_user_id") or "").strip()[:64]
            if direction == "BUSINESS_INITIATED":
                self._call_link_outbound(account, wacid, number, user_ref)
            call = self._call_get_or_create(account, wacid, number, user_ref=user_ref)
            vals = {"meta_seen": True}
            if direction == "BUSINESS_INITIATED":
                vals["direction"] = "outbound"
            if number and not call.number:
                vals["number"] = number
            if user_ref and not call.user_ref:
                vals["user_ref"] = user_ref
            timestamp = data.get("timestamp") or data.get("start_time")
            if timestamp and str(timestamp).isdigit() and not call.server_seen:
                vals["start_date"] = datetime.fromtimestamp(int(timestamp), UTC).replace(tzinfo=None)
            event = data.get("event")
            if event == "connect" and not account.call_enabled:
                _logger.info("WhatsApp call %s: calls disabled in Odoo, nobody answers.", wacid)
            if event == "terminate":
                vals["meta_status"] = data.get("status")
                if str(data.get("duration") or "").isdigit():
                    vals["meta_duration"] = int(data["duration"])
            call.write(vals)
            call._call_link_conversation()
            if event == "terminate" and call.server_seen and call.state not in FINAL_STATES:
                # ended at Meta, still going on the call server (the end of Meta did not
                # reach it): the phone of the agent hangs up, the call server sees it
                _logger.info("WhatsApp call %s: ended at Meta, the agents' phones hang up.", wacid)
                call._call_bus_send(ended_at_meta=True)

    # === CALLS OF THE COMPANY === #

    @api.model
    def _call_link_outbound(self, account, wacid, number, user_ref):
        """A call of the company told by Meta: the call prepared in Odoo when the agent clicked
        (Meta gives its ID only then)."""
        if self.sudo().search_count([("account_id", "=", account.id), ("wacid", "=", wacid)]):
            return
        customer = [("number", "=", number)] if number else [("user_ref", "=", user_ref)]
        if not (number or user_ref):
            return
        call = self.sudo().search([
            ("account_id", "=", account.id), ("direction", "=", "outbound"), ("wacid", "=", False),
            ("create_date", ">=", fields.Datetime.now() - const.OUTBOUND_META_LINK),
            *customer,
        ], order="id desc", limit=1)
        if call:
            call.wacid = wacid

    @api.model
    def _server_outbound(self, values):
        """The call server asks whether an agent may make a call of the company (prepared by
        Odoo when they clicked): whom, through which number; else why not."""
        call_id = str(values.get("call") or "")
        call = self.sudo().browse(int(call_id)).exists() if call_id.isdigit() else self.browse()
        user = self._agent_from_login(values.get("agent"))
        if (
            not call or call.direction != "outbound" or call.state != "ringing" or call.server_seen
            or not user or call.user_id != user
            or call.create_date < fields.Datetime.now() - const.OUTBOUND_PREPARED_FOR
        ):
            _logger.warning("WhatsApp call %s: call of %s refused by Odoo (not prepared).",
                            call_id, values.get("agent"))
            return {"error": "Call not prepared by Odoo"}
        account = call.account_id
        if not account.call_enabled or not account.sudo().call_sip_password or not call.number:
            return {"error": "Calls not enabled or no number"}
        call.write({"server_seen": True, "server_uuid": values.get("uuid") or False})
        return {
            "number": call.number,
            "phone_number_id": account.phone_number_id,
            "business_number": account._call_business_number(),
            "srtp": account.call_srtp,
            "max_ring": const.OUTBOUND_MAX_RING,
        }

    def action_call_back(self):
        """Call the customer back (the phone of the top bar calls them through WhatsApp)."""
        self.ensure_one()
        if not self.channel_id:
            raise UserError(_("This call has no conversation."))
        return self.channel_id.with_user(self.env.user).whatsapp_action_call()

    # === CHECKS === #

    @api.model
    def _cron_check_calls(self):
        """Calls lost (seen by Meta, never by the call server), calls without an end (call
        server stopped during the call), and the silence of the call server."""
        now = fields.Datetime.now()
        lost = self.sudo().search([
            ("direction", "=", "inbound"),
            ("meta_seen", "=", True),
            ("server_seen", "=", False),
            ("state", "=", "ringing"),
            ("create_date", "<", now - const.LOST_AFTER),
        ])
        for account, calls in lost.grouped("account_id").items():
            account = account.with_context(lang=account._get_team_lang())
            for call in calls.with_context(lang=account.env.lang):
                call.write({"state": "lost", "end_date": now, "ended_by": "system"})
                call._call_post_notice()
            account._alert_managers(_(
                "WhatsApp account %(name)s: %(count)s call(s) of customers did not reach the call "
                "server (lost). Check the call server and its connection with Meta (port, "
                "certificate, SIP password); the customers are to call back or to write to.",
                name=account.name, count=len(calls),
            ))
        stale = self.sudo().search([
            ("state", "in", ("ringing", "answered")),
            ("server_seen", "=", True),
            ("start_date", "<", now - const.STALE_AFTER),
        ])
        for call in stale:
            call._call_end({"event": "ended", "outcome": "completed" if call.answer_date else "missed",
                            "ended_by": "system", "cause": "NO_END_RECEIVED"})
        # calls of the company prepared but never placed (phone closed, browser refused)
        self.sudo().search([
            ("direction", "=", "outbound"), ("state", "=", "ringing"), ("server_seen", "=", False),
            ("create_date", "<", now - const.OUTBOUND_PREPARED_FOR),
        ]).write({"state": "failed", "end_date": now, "ended_by": "system", "end_cause": "NOT_PLACED"})
        self._cron_check_server()

    @api.model
    def _cron_check_server(self):
        """Alert the managers when the call server has been silent for 5 minutes (once until
        it reports again)."""
        accounts = self.env["whatsapp.account"].sudo().search([("call_enabled", "=", True)])
        if not accounts:
            return
        server = self.env["whatsapp.call.server"]._get()
        last_seen = server.last_seen
        silent = not last_seen or last_seen < fields.Datetime.now() - const.SERVER_SILENCE
        if silent and not server.silence_alerted:
            server.silence_alerted = True
            for account in accounts:
                account = account.with_context(lang=account._get_team_lang())
                account._alert_managers(_(
                    "The call server has not reported since %s: the WhatsApp calls may not ring. "
                    "Check that FreeSWITCH and the copy of the agents (ocd-call-sync) run on it.",
                    fields.Datetime.to_string(last_seen) if last_seen else _("its installation"),
                ))
        elif not silent and server.silence_alerted:
            server.silence_alerted = False

    # === CONVERSATION === #

    def _call_notice_text(self):
        self.ensure_one()
        env = self.env
        wait = format_duration(env, self.wait_duration)
        if self.direction == "outbound":
            agent = self.user_id.name or _("an agent")
            if self.state == "completed":
                return _("Call to the customer of %(duration)s, by %(agent)s.",
                         duration=format_duration(env, self.duration), agent=agent)
            if self.state == "failed":
                return _("Call to the customer by %(agent)s: it did not go through (%(cause)s).",
                         agent=agent, cause=self.end_cause or _("call server"))
            if self.ended_by == "agent":
                return _("Call to the customer by %s: hung up before they answered.", agent)
            return _("Call to the customer by %s: no answer.", agent)
        if self.state == "completed":
            text = _("Call of %(duration)s, answered by %(agent)s (waited %(wait)s).",
                     duration=format_duration(env, self.duration),
                     agent=self.user_id.name or _("an agent"), wait=wait)
            if self.reconnect_count:
                text += " " + _("Agent cut off %s time(s), the call came back.", self.reconnect_count)
            return text
        if self.state == "voicemail":
            return _("Missed call (waited %s): the customer left a message.", wait)
        if self.state == "lost":
            return _("Call lost: the call server did not take it. Call the customer back or write "
                     "to them.")
        if self.state == "failed":
            return _("Call failed (%s).", self.end_cause or _("call server"))
        return _("Missed call (waited %s): call the customer back or write to them.", wait)

    def _call_post_notice(self):
        """A line in the conversation for the team; a missed call or a message waits for an
        answer (the reminders of WhatsApp)."""
        for call in self.filtered("channel_id"):
            if call.notice_message_id:
                continue
            channel = call.channel_id.sudo()
            channel = channel.with_context(lang=channel.whatsapp_account_id._get_team_lang())
            call = call.with_context(lang=channel.env.lang)
            if call.direction == "inbound" and call.state in ("missed", "voicemail", "lost"):
                channel._whatsapp_route_to_agents()
                partners = channel.whatsapp_user_id.partner_id or None
            else:
                partners = None
            message = channel._whatsapp_notify(call._call_notice_text(), partners=partners)
            call.notice_message_id = message

    def _call_bus_send(self, ended_at_meta=False):
        """Tell the agents of the account that the call changed (the phone of the top bar);
        ended at Meta: their phone hangs up this call."""
        for call in self:
            call.account_id._get_agents()._bus_send("whatsapp.call/update", {
                "id": call.id,
                "state": call.state,
                "user_id": call.user_id.id,
                "user_name": call.user_id.name or "",
                "ended_at_meta": ended_at_meta,
            })

    def _call_add_phone_trace(self, user, trace):
        """The account of an answer by the phone of an agent, kept on the call."""
        self.ensure_one()
        line = "%s %s: %s" % (
            fields.Datetime.to_string(fields.Datetime.now()), user.name,
            " ".join(str(trace or "").split())[:1500],
        )
        self.sudo().phone_trace = "\n".join(filter(None, [self.phone_trace, line]))[-20000:]

    # === ACTIONS === #

    def action_open_conversation(self):
        self.ensure_one()
        return self.channel_id.whatsapp_action_open() if self.channel_id else False
