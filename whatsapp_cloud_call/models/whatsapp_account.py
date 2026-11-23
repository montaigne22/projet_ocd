import logging
from collections import Counter
from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.whatsapp_cloud.models.whatsapp_account import WhatsAppApiError
from odoo.addons.whatsapp_cloud_call import const

_logger = logging.getLogger(__name__)

DAYS = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")
# Meta: 2 periods a day at most, 20 public holidays at most.
MAX_PERIODS_PER_DAY = 2
MAX_HOLIDAYS = 20
HOLIDAY_DAYS = 120


class WhatsappAccount(models.Model):
    _inherit = "whatsapp.account"

    call_enabled = fields.Boolean(
        string="Calls",
        tracking=True,
        help="The customers can call this number from WhatsApp; the calls go through the call "
        "server of the company (Settings > WhatsApp > Calls).",
    )
    call_icon_visibility = fields.Selection(
        selection=[("DEFAULT", "Shown"), ("DISABLE_ALL", "Hidden")],
        string="Call Icon",
        default="DEFAULT",
        required=True,
        help="Phone icon in the conversation with the company, in WhatsApp.",
    )
    call_use_hours = fields.Boolean(
        string="Calls during the Opening Hours Only",
        default=True,
        help="Meta takes the calls only during the opening hours of the team (Team tab), public "
        "holidays closed. Without opening hours, the calls are taken at any time.",
    )
    call_srtp = fields.Selection(
        selection=[("SDES", "SDES (recommended with FreeSWITCH)"), ("DTLS", "DTLS (WebRTC)")],
        string="Encryption of the Voice",
        default="SDES",
        required=True,
        help="How Meta and the call server agree on the keys of the encrypted voice.",
    )
    call_callback_permission = fields.Boolean(
        string="Call back the Customers who Called",
        default=True,
        help="A customer who calls allows the company to call them back (Meta, 7 days).",
    )
    call_max_wait = fields.Integer(
        string="Waiting before the Voicemail (seconds)",
        default=180,
        help="A customer who waits this long without an agent leaves a message.",
    )
    call_voicemail = fields.Boolean(
        string="Voicemail",
        default=True,
        help="Nobody answers: the customer leaves a message, posted in their conversation.",
    )
    call_sip_password = fields.Char(
        string="SIP Password of Meta",
        readonly=True,
        groups="base.group_system",
        copy=False,
        help="Given by Meta when the SIP server is set: Meta signs its calls with it, and the "
        "call server checks it.",
    )
    call_meta_state = fields.Selection(
        selection=[
            ("disabled", "Disabled"),
            ("pending", "To send to Meta"),
            ("ok", "Enabled at Meta"),
            ("restricted", "Restricted by Meta"),
            ("error", "Error"),
        ],
        string="Calls at Meta",
        default="disabled",
        readonly=True,
        copy=False,
    )
    call_meta_message = fields.Text(string="Message of Meta", readonly=True, copy=False)
    call_meta_date = fields.Datetime(string="Last Exchange with Meta", readonly=True, copy=False)
    call_count = fields.Integer(string="Number of Calls", compute="_compute_call_count")
    # the thresholds to open the calls to all (const.CALL_STATS_DAYS last days)
    call_stats_count = fields.Integer(string="Calls (14 days)", compute="_compute_call_stats")
    call_stats_cut_rate = fields.Float(
        string="Calls Cut", compute="_compute_call_stats",
        help="Calls lost or failed, and calls where the agent was cut off (network, closed "
        "page), among the calls of the last 14 days. To open the calls to all: under 2 %.",
    )
    call_stats_voicemail_rate = fields.Float(
        string="Voicemail while an Agent was Free", compute="_compute_call_stats",
        help="Calls ended missed or in the voicemail although an agent taking the calls was "
        "free, among the calls of the call hours of the last 14 days. To open the calls to all: "
        "under 5 %.",
    )
    call_stats_wait = fields.Integer(
        string="Average Wait (s)", compute="_compute_call_stats",
        help="Average wait of the calls answered during the call hours of the last 14 days. To "
        "open the calls to all: under 60 seconds.",
    )
    call_stats_ok = fields.Boolean(string="Thresholds Met", compute="_compute_call_stats")
    call_limit_warning = fields.Char(compute="_compute_call_limit_warning")
    call_hours_warning = fields.Char(compute="_compute_call_hours_warning")

    def _compute_call_count(self):
        counts = dict(self.env["whatsapp.call"]._read_group(
            [("account_id", "in", self.ids)], ["account_id"], ["__count"]
        ))
        for account in self:
            account.call_count = counts.get(account, 0)

    def _compute_call_stats(self):
        since = fields.Datetime.now() - timedelta(days=const.CALL_STATS_DAYS)
        for account in self:
            calls = self.env["whatsapp.call"].sudo().search([
                ("account_id", "=", account.id), ("direction", "=", "inbound"),
                ("start_date", ">=", since), ("state", "not in", ("ringing", "answered")),
            ])
            cut = calls.filtered(lambda c: c.state in ("lost", "failed") or c.reconnect_count)
            in_hours = calls.filtered("in_hours")
            free = in_hours.filtered(lambda c: c.available_agents)
            voicemail = free.filtered(lambda c: c.state in ("missed", "voicemail"))
            answered = in_hours.filtered(lambda c: c.state == "completed" and c.answer_date)
            account.call_stats_count = len(calls)
            account.call_stats_cut_rate = len(cut) / len(calls) if calls else 0.0
            account.call_stats_voicemail_rate = len(voicemail) / len(free) if free else 0.0
            account.call_stats_wait = (
                round(sum(answered.mapped("wait_duration")) / len(answered)) if answered else 0
            )
            account.call_stats_ok = bool(calls) and (
                account.call_stats_cut_rate < const.CALL_MAX_CUT_RATE
                and account.call_stats_voicemail_rate < const.CALL_MAX_VOICEMAIL_RATE
                and account.call_stats_wait < const.CALL_MAX_AVERAGE_WAIT
            )

    @api.depends("messaging_limit", "call_enabled")
    def _compute_call_limit_warning(self):
        for account in self:
            limit = (account.messaging_limit or "").upper()
            account.call_limit_warning = (
                _("Meta enables the calls only for a number that may send templates to 2,000 "
                  "customers a day or more (limit now: %s). Check the account to read it again.",
                  limit)
                if account.call_enabled and limit and limit not in const.CALLING_MIN_TIERS
                else False
            )

    @api.depends("call_enabled", "call_use_hours", "resource_calendar_id.attendance_ids.duration_based")
    def _compute_call_hours_warning(self):
        for account in self:
            account.call_hours_warning = (
                account._call_hours_without_times_text()
                if account.call_enabled and account.call_use_hours and account._call_hours_without_times()
                else False
            )

    def _call_hours_without_times(self):
        """Opening hours given as a number of hours a day, without start and end: Odoo would
        place them around noon (10 hours: 7:00 to 17:00), not the hours of the team."""
        self.ensure_one()
        return bool(self.resource_calendar_id.attendance_ids.filtered("duration_based"))

    def _call_hours_without_times_text(self):
        return _(
            "The opening hours (Team tab) give a number of hours a day but not when: Meta would "
            "get hours placed around noon by Odoo (10 hours: 7:00 to 17:00). In the opening hours, "
            "show the columns Work from and Work to of the list (icon at the right of its header) "
            "and set them on each day; or untick Calls during the Opening Hours Only."
        )

    def write(self, vals):
        watched = {
            "call_enabled", "call_icon_visibility", "call_use_hours", "call_srtp",
            "call_callback_permission", "resource_calendar_id",
        }
        res = super().write(vals)
        if watched & set(vals):
            for account in self.filtered(lambda a: a.call_enabled or a.call_meta_state != "disabled"):
                account.call_meta_state = "pending"
        return res

    # === SETTINGS AT META === #

    def _call_server_host(self):
        return (self.env["ir.config_parameter"].sudo().get_str(const.PARAM_HOST) or "").strip()

    def _call_settings_payload(self):
        """The calling settings of the number, as Meta expects them (POST <number>/settings)."""
        self.ensure_one()
        host = self._call_server_host()
        if self.call_enabled and not host:
            raise UserError(_(
                "Enter the address of the call server first (Settings > WhatsApp > Calls)."
            ))
        params = self.env["ir.config_parameter"].sudo()
        port = int(params.get_str(const.PARAM_SIP_PORT) or const.DEFAULT_SIP_PORT)
        calling = {
            "status": "ENABLED" if self.call_enabled else "DISABLED",
            "call_icon_visibility": self.call_icon_visibility,
            "callback_permission_status": "ENABLED" if self.call_callback_permission else "DISABLED",
            "call_hours": self._call_hours_payload(),
        }
        if host:
            calling["sip"] = {
                "status": "ENABLED" if self.call_enabled else "DISABLED",
                "servers": [{"hostname": host, "port": port}],
                "webhook_delivery": "ENABLED",
            }
            if self.call_enabled:
                # in "calling", not in "sip" (refused by Meta there: "Unexpected key"); SDES
                # only with the SIP server enabled
                calling["srtp_key_exchange_protocol"] = self.call_srtp
        return {"calling": calling}

    def _call_hours_payload(self):
        """The hours of the calls at Meta: the opening hours of the team (a usual week) and the
        days closed in the coming months (public holidays)."""
        self.ensure_one()
        calendar = self.resource_calendar_id
        if not self.call_use_hours or not calendar:
            return {"status": "DISABLED"}
        if self._call_hours_without_times():
            raise UserError(self._call_hours_without_times_text())
        tz_name = self.company_id.tz or self.company_id.partner_id.tz or "UTC"
        now = self._to_calendar_tz(fields.Datetime.now())
        today = now.date()
        weeks = 4
        start = datetime.combine(today, time.min, tzinfo=now.tzinfo)
        end = start + timedelta(days=7 * weeks)
        theoretical = calendar._attendance_intervals_batch(start, end)[False]
        periods_by_date = {}
        for begin, stop, _attendance in theoretical:
            periods_by_date.setdefault(begin.date(), []).append((begin, stop))
        # the usual periods of each day of the week: the most frequent over the coming weeks
        usual = {}
        for weekday in range(7):
            schedules = Counter(
                tuple(self._call_merge_periods(periods))
                for day, periods in periods_by_date.items() if day.weekday() == weekday
            )
            if schedules:
                usual[weekday] = list(schedules.most_common(1)[0][0])
        weekly = [
            {"day_of_week": DAYS[weekday], "open_time": open_time, "close_time": close_time}
            for weekday in range(7)
            for open_time, close_time in usual.get(weekday, [])
        ]
        if not weekly:
            return {"status": "DISABLED"}
        # the days with usual hours but nobody working: closed (public holidays)
        holidays = []
        start = datetime.combine(today + timedelta(days=1), time.min, tzinfo=now.tzinfo)
        end = start + timedelta(days=HOLIDAY_DAYS)
        working_days = {
            begin.date() for begin, _stop, _attendance in calendar._work_intervals_batch(start, end)[False]
        }
        day = start.date()
        while day < end.date() and len(holidays) < MAX_HOLIDAYS:
            if usual.get(day.weekday()) and day not in working_days:
                holidays.append({
                    "date": day.isoformat(), "start_time": "0000", "end_time": "2359",
                })
            day += timedelta(days=1)
        payload = {
            "status": "ENABLED",
            "timezone_id": tz_name,
            "weekly_operating_hours": weekly,
        }
        if holidays:
            payload["holiday_schedule"] = holidays
        return payload

    @api.model
    def _call_merge_periods(self, periods):
        """Periods of a day as Meta takes them: (open, close) in 'HHMM', joined when they
        touch, 2 at most (the shortest breaks are filled)."""
        periods = sorted(periods)
        merged = []
        for begin, stop in periods:
            if merged and begin <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], stop))
            else:
                merged.append((begin, stop))
        while len(merged) > MAX_PERIODS_PER_DAY:
            gaps = [merged[i + 1][0] - merged[i][1] for i in range(len(merged) - 1)]
            index = gaps.index(min(gaps))
            merged[index:index + 2] = [(merged[index][0], merged[index + 1][1])]

        def hhmm(moment, end=False):
            if end and moment.time() == time.min and moment.date() > periods[0][0].date():
                return "2359"
            return moment.strftime("%H%M")

        return [(hhmm(begin), hhmm(stop, end=True)) for begin, stop in merged]

    def action_call_send_settings(self):
        """Send the calling settings to Meta, then read them back (state, restrictions, SIP
        password)."""
        for account in self:
            payload = account._call_settings_payload()
            try:
                account._api_request("POST", f"{account.phone_number_id}/settings", json=payload)
            except WhatsAppApiError as error:
                account.write({
                    "call_meta_state": "error",
                    "call_meta_message": account._get_error_text(error),
                    "call_meta_date": fields.Datetime.now(),
                })
                continue
            account.message_post(
                body=_("Calls: settings sent to Meta (%s).",
                       _("enabled") if account.call_enabled else _("disabled")),
                message_type="notification",
            )
            account._call_read_settings()
        return self._call_notify_result()

    def action_call_read_settings(self):
        self._call_read_settings()
        return self._call_notify_result()

    def _call_notify_result(self):
        errors = self.filtered(lambda a: a.call_meta_state in ("error", "restricted"))
        if errors:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "warning",
                    "sticky": True,
                    "message": "\n".join(
                        f"{account.name}: {account.call_meta_message or ''}" for account in errors
                    ),
                },
            }
        return True

    def _call_read_settings(self):
        """Read the calling settings at Meta: the state, the restrictions imposed by Meta, and
        the SIP password of the number (kept for the call server)."""
        for account in self:
            vals = {"call_meta_date": fields.Datetime.now()}
            try:
                data = account._api_request(
                    "GET", f"{account.phone_number_id}/settings",
                    params={"include_sip_credentials": "true"},
                )
            except WhatsAppApiError as error:
                vals.update(call_meta_state="error", call_meta_message=account._get_error_text(error))
                account.write(vals)
                continue
            calling = data.get("calling") or {}
            restrictions = (calling.get("restrictions") or {}).get("restrictions_list") or (
                calling.get("restrictions") or {}
            ).get("restriction_list") or []
            servers = (calling.get("sip") or {}).get("servers") or []
            host = account._call_server_host()
            server = next(
                (s for s in servers if (s.get("hostname") or "").lower() == host.lower()),
                servers[0] if servers else {},
            )
            password = server.get("sip_user_password")
            if password and password != "[REDACTED]":
                account.sudo().call_sip_password = password
            enabled = (calling.get("status") or "").upper() == "ENABLED"
            messages = [
                _("%(type)s: %(reason)s", type=item.get("type"), reason=item.get("reason") or "")
                + (
                    _(" (until %s)", fields.Datetime.to_string(datetime.fromtimestamp(int(item["expiration"]))))
                    if item.get("expiration") else ""
                )
                for item in restrictions
            ]
            if enabled and not account.sudo().call_sip_password:
                messages.append(_(
                    "Meta gave no SIP password: check the SIP server in the settings, then send "
                    "them again."
                ))
            if restrictions:
                state = "restricted"
            elif enabled and account.sudo().call_sip_password:
                state = "ok"
            elif enabled:
                state = "error"
            else:
                state = "disabled" if not account.call_enabled else "pending"
            vals.update(call_meta_state=state, call_meta_message="\n".join(messages) or False)
            account.write(vals)
            if state in ("restricted", "error") and account.call_enabled:
                account._alert_managers(_(
                    "WhatsApp account %(name)s, calls: %(details)s",
                    name=account.name, details=vals["call_meta_message"] or state,
                ))

    def action_open_calls(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("whatsapp_cloud_call.whatsapp_call_action")
        action["domain"] = [("account_id", "=", self.id)]
        action["context"] = {"default_account_id": self.id}
        return action

    # === CALL SERVER === #

    @api.model
    def _call_get_agents(self):
        """The agents of the accounts with calls: {user: accounts}."""
        agents = {}
        for account in self.sudo().search([("call_enabled", "=", True)]):
            for user in account._get_agents():
                agents.setdefault(user, self.browse())
                agents[user] |= account
        return agents

    def _call_business_number(self):
        """Number of the account in international format, digits only."""
        self.ensure_one()
        return "".join(ch for ch in (self.display_phone_number or "") if ch.isdigit())

    @api.model
    def _call_find_by_phone_number_id(self, phone_number_id, business_number=None):
        """The account of a call: by the phone number ID given by Meta, else by the number."""
        accounts = self.sudo().search([("call_enabled", "=", True)])
        account = accounts.filtered(lambda a: phone_number_id and a.phone_number_id == phone_number_id)
        if not account and business_number:
            digits = "".join(ch for ch in business_number if ch.isdigit())
            account = accounts.filtered(lambda a: digits and a._call_business_number() == digits)
        return account[:1] or (accounts[:1] if len(accounts) == 1 else self.browse())
