"""A remote live: the vendor goes live from home, on an account of OCD Live, as a guest.

Before the hour, the team and the automations make sure the vendor is there:

- 30 minutes before, the host (else the manager of the live) has an activity « Call the vendor »:
  a test call, to check the application, the account and the products;
- 15 minutes before, the vendor receives an invitation (WhatsApp with ocd_live_whatsapp) with a
  button « Join my live »: a page with the steps, « I am ready » and « I have a problem »;
- 5 minutes before, when the vendor did not say they were ready, the host is alerted.

The page of the vendor, the form of the live and the control room show where it stands."""

from datetime import timedelta

from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.tools import consteq, format_datetime
from odoo.tools.misc import hmac

HOST_CALL_MINUTES = 30
JOIN_INVITE_MINUTES = 15
NOT_READY_MINUTES = 5
CALL_ACTIVITY = "mail.mail_activity_data_call"
ALERT_ACTIVITY = "ocd_live.mail_activity_type_vendor_alert"

PROBLEMS = [
    ("no_invite", "I did not receive the invitation"),
    ("app", "The application does not work"),
    ("late", "I will be late"),
    ("other", "Another problem"),
]
JOIN_STATES = [
    ("waiting", "Not invited yet"),
    ("invited", "Invited"),
    ("ready", "Ready"),
    ("problem", "Problem"),
]


class OcdLiveBooking(models.Model):
    _inherit = "ocd.live.booking"

    account_id = fields.Many2one(
        comodel_name="ocd.live.account",
        string="Live Account",
        compute="_compute_account_id",
        store=True,
        readonly=False,
        tracking=True,
        check_company=True,
        help="The account of OCD Live where the live goes: the vendor of a remote live joins it as a guest. "
        "Chosen by itself (mode, country of the vendor, free at the hour), the team can change it.",
    )
    vendor_live_handle = fields.Char(related="partner_id.ocd_live_handle", readonly=False)
    ocd_call_planned = fields.Boolean(string="Call Planned", copy=False, readonly=True)
    ocd_join_tried = fields.Boolean(string="Invitation Tried", copy=False, readonly=True)
    ocd_join_sent_at = fields.Datetime(string="Invitation Sent At", copy=False, readonly=True)
    ocd_not_ready_alerted = fields.Boolean(string="Alert Not Ready Sent", copy=False, readonly=True)
    ocd_vendor_ready_at = fields.Datetime(string="Vendor Ready At", copy=False, readonly=True, tracking=True)
    ocd_vendor_problem = fields.Selection(
        selection=PROBLEMS, string="Problem Of The Vendor", copy=False, readonly=True, tracking=True
    )
    ocd_vendor_problem_note = fields.Char(string="Problem Told", copy=False, readonly=True)
    ocd_vendor_problem_at = fields.Datetime(string="Problem Told At", copy=False, readonly=True)
    ocd_host_called_at = fields.Datetime(string="Vendor Called At", copy=False, readonly=True)
    ocd_host_called_by = fields.Many2one(comodel_name="res.users", string="Called By", copy=False, readonly=True)
    ocd_join_state = fields.Selection(selection=JOIN_STATES, string="Vendor At The Hour", compute="_compute_ocd_join_state")

    @api.depends("mode", "partner_id.country_id", "company_id")
    def _compute_account_id(self):
        """Another mode, another vendor: the account is chosen again (the team can change it)."""
        Account = self.env["ocd.live.account"]
        for booking in self:
            booking.account_id = Account._ocd_pick(booking)

    @api.model
    def _ocd_assign_accounts(self):
        """The lives to come whose account no longer fits (or without one) take one: an account
        was added, changed or removed."""
        Account = self.env["ocd.live.account"]
        bookings = self.sudo().search(
            [("state", "in", ("draft", "confirmed")), ("end_datetime", ">", fields.Datetime.now())],
            order="start_datetime",
        )
        for booking in bookings:
            current = booking.account_id
            if current and current.active and current._ocd_fits(booking.mode, booking.partner_id.country_id):
                continue
            account = Account._ocd_pick(booking)
            if account != current:
                booking.account_id = account

    @api.depends("ocd_join_sent_at", "ocd_vendor_ready_at", "ocd_vendor_problem")
    def _compute_ocd_join_state(self):
        for booking in self:
            if booking.ocd_vendor_problem:
                booking.ocd_join_state = "problem"
            elif booking.ocd_vendor_ready_at:
                booking.ocd_join_state = "ready"
            elif booking.ocd_join_sent_at:
                booking.ocd_join_state = "invited"
            else:
                booking.ocd_join_state = "waiting"

    def write(self, vals):
        if any(key in vals for key in ("start_datetime", "mode", "partner_id")):
            # Another hour, another live: the steps before it start again
            vals = {
                "ocd_call_planned": False, "ocd_join_tried": False, "ocd_join_sent_at": False,
                "ocd_not_ready_alerted": False, "ocd_vendor_ready_at": False, "ocd_vendor_problem": False,
                "ocd_vendor_problem_note": False, "ocd_vendor_problem_at": False,
                "ocd_host_called_at": False, "ocd_host_called_by": False, **vals,
            }
        return super().write(vals)

    # === LINK OF THE LIVE === #

    def _ocd_watch_url(self):
        """Where the live is watched: its own link, else the one of its account."""
        self.ensure_one()
        return self.live_url or self.account_id.live_url or False

    # === PAGE « JOIN MY LIVE » === #

    def _ocd_join_token(self):
        """Secret of the page « Join my live », sent to the vendor alone: a live moved since
        has another one."""
        self.ensure_one()
        message = ":".join(map(str, [self.id, self.partner_id.id, fields.Datetime.to_string(self.start_datetime)]))
        return hmac(self.env(su=True), "ocd_live.join", message)[:32]

    def _ocd_join_check(self, token):
        self.ensure_one()
        return bool(token) and consteq(self._ocd_join_token(), token)

    def _ocd_join_path(self):
        self.ensure_one()
        return f"/ocd/live/{self.id}/rejoindre/{self._ocd_join_token()}"

    def _ocd_join_url(self):
        self.ensure_one()
        return f"{self.get_base_url()}{self._ocd_join_path()}"

    def _ocd_host_user(self):
        """Who calls the vendor: the host, else the manager of the live."""
        self.ensure_one()
        return self.animatrice_id.user_id or self._ocd_activity_user()

    def _ocd_host_phone(self):
        self.ensure_one()
        host = self.animatrice_id
        return host.mobile_phone or host.work_phone or False

    # === BEFORE THE HOUR === #

    @api.model
    def _cron_remote_join(self):
        """Every 5 minutes: the steps before the remote lives that start soon (see the top)."""
        if not self.env["ocd.automation"]._ocd_enabled("remote_join"):
            return
        now = fields.Datetime.now()
        bookings = self.search([
            ("mode", "=", "remote"),
            ("state", "=", "confirmed"),
            ("start_datetime", ">", now - timedelta(minutes=10)),
            ("start_datetime", "<=", now + timedelta(minutes=HOST_CALL_MINUTES)),
        ], order="start_datetime")
        for booking in bookings:
            left = booking.start_datetime - now
            if not booking.ocd_call_planned:
                booking._ocd_plan_host_call()
            if left <= timedelta(minutes=JOIN_INVITE_MINUTES) and not booking.ocd_join_tried:
                booking._ocd_invite_to_join()
            if (
                left <= timedelta(minutes=NOT_READY_MINUTES)
                and not booking.ocd_vendor_ready_at
                and not booking.ocd_not_ready_alerted
            ):
                booking._ocd_alert_not_ready()

    def _ocd_activity_texts(self):
        self.ensure_one()
        vendor = self.partner_id
        hour = self._ocd_studio_labels()[1]
        return vendor, hour

    def _ocd_plan_host_call(self):
        """The host calls the vendor before the live: a test, to be sure everything works."""
        self.ensure_one()
        self.ocd_call_planned = True
        if self.ocd_host_called_at:
            return
        vendor, hour = self._ocd_activity_texts()
        account = self.account_id
        lines = [self.env._(
            "Call %(vendor)s (%(phone)s) for a test before the live of %(hour)s.",
            vendor=vendor.name, phone=vendor.phone or "-", hour=hour,
        )]
        if account:
            lines.append(self.env._(
                "Check that they follow %(handle)s on %(platform)s and that the application is up to date.",
                handle=account.handle, platform=account.platform_id.name,
            ))
        lines.append(self.env._("Then click « Vendor called » on the live."))
        user = self._ocd_host_user()
        self.activity_schedule(
            CALL_ACTIVITY,
            date_deadline=fields.Date.context_today(self),
            summary=self.env._("Call %(vendor)s before the live (%(hour)s)", vendor=vendor.name, hour=hour),
            note=Markup("<br/>").join(lines),
            user_id=user.id if user else self.env.uid,
        )

    def _ocd_invite_to_join(self):
        """15 minutes before: the invitation to join the live, with the link of the page."""
        self.ensure_one()
        self.ocd_join_tried = True
        if self._ocd_send_join_invitation():
            self.ocd_join_sent_at = fields.Datetime.now()
            self.message_post(body=self.env._("The vendor received the invitation to join the live."))
        else:
            self.message_post(body=self.env._(
                "The invitation to join could not be sent: give this link to the vendor: %s", self._ocd_join_url(),
            ))

    def _ocd_send_join_invitation(self):
        """Send the invitation to join to the vendor; return whether it left. Overridden by
        ocd_live_whatsapp (the WhatsApp message with its button)."""
        return False

    def _ocd_alert_not_ready(self):
        """5 minutes before, the vendor did not say they were ready: the host calls them."""
        self.ensure_one()
        self.ocd_not_ready_alerted = True
        vendor, hour = self._ocd_activity_texts()
        user = self._ocd_host_user()
        self.activity_schedule(
            ALERT_ACTIVITY,
            date_deadline=fields.Date.context_today(self),
            summary=self.env._("%(vendor)s is not ready: live at %(hour)s", vendor=vendor.name, hour=hour),
            note=escape(self.env._("Call them now: %s", vendor.phone or "-")),
            user_id=user.id if user else self.env.uid,
        )
        self.message_post(body=self.env._("%s did not say they were ready, 5 minutes before the live.", vendor.name))

    # === WHAT THE VENDOR SAYS (page « Join my live ») === #

    def _ocd_vendor_says_ready(self):
        self.ensure_one()
        self.write({
            "ocd_vendor_ready_at": fields.Datetime.now(),
            "ocd_vendor_problem": False,
            "ocd_vendor_problem_note": False,
            "ocd_vendor_problem_at": False,
        })
        self._ocd_close_join_alerts()
        self.message_post(body=self.env._("%s is ready to join the live.", self.partner_id.name))

    def _ocd_vendor_says_problem(self, problem, note=None):
        self.ensure_one()
        problem = problem if problem in dict(PROBLEMS) else "other"
        note = (note or "").strip()[:300]
        self.write({
            "ocd_vendor_problem": problem,
            "ocd_vendor_problem_note": note or False,
            "ocd_vendor_problem_at": fields.Datetime.now(),
            "ocd_vendor_ready_at": False,
        })
        label = dict(self._fields["ocd_vendor_problem"]._description_selection(self.env))[problem]
        vendor, hour = self._ocd_activity_texts()
        user = self._ocd_host_user()
        self.activity_schedule(
            ALERT_ACTIVITY,
            date_deadline=fields.Date.context_today(self),
            summary=self.env._("%(vendor)s has a problem: %(problem)s", vendor=vendor.name, problem=label),
            note=escape(self.env._(
                "Live at %(hour)s. Call them: %(phone)s. %(note)s", hour=hour, phone=vendor.phone or "-", note=note,
            )),
            user_id=user.id if user else self.env.uid,
        )
        self.message_post(body=self.env._(
            "%(vendor)s has a problem: %(problem)s %(note)s", vendor=vendor.name, problem=label, note=note,
        ))

    def _ocd_close_join_alerts(self):
        """The vendor is ready: the alerts of the team about it are done."""
        alert = self.env.ref(ALERT_ACTIVITY, raise_if_not_found=False)
        if alert:
            self.activity_ids.filtered(lambda activity: activity.activity_type_id == alert).action_feedback(
                feedback=self.env._("The vendor is ready.")
            )

    # === THE TEAM === #

    def action_ocd_host_called(self):
        """The host called the vendor before the live."""
        now = fields.Datetime.now()
        for booking in self:
            booking.write({"ocd_host_called_at": now, "ocd_host_called_by": self.env.uid})
            call = self.env.ref(CALL_ACTIVITY, raise_if_not_found=False)
            activities = booking.activity_ids.filtered(lambda activity: activity.activity_type_id == call)
            if activities:
                activities.action_feedback(feedback=self.env._("Vendor called."))
            else:
                booking.message_post(body=self.env._("Vendor called by %s.", self.env.user.name))
        return True

    def action_ocd_open_join_page(self):
        """The page « Join my live » of the vendor, to send its link by hand or to see it."""
        self.ensure_one()
        return {"type": "ir.actions.act_url", "url": self._ocd_join_path(), "target": "new"}

    def _ocd_join_status_text(self):
        """Where the vendor of a remote live stands, in a few words, for the team."""
        self.ensure_one()
        _ = self.env._
        tz = self.company_id._ocd_tz().zone
        if self.ocd_join_state == "problem":
            label = dict(self._fields["ocd_vendor_problem"]._description_selection(self.env))[self.ocd_vendor_problem]
            return _("Problem: %s", label) + (f" · {self.ocd_vendor_problem_note}" if self.ocd_vendor_problem_note else "")
        if self.ocd_join_state == "ready":
            return _("Ready since %s", format_datetime(self.env, self.ocd_vendor_ready_at, tz=tz, dt_format="HH:mm"))
        if self.ocd_join_state == "invited":
            return _("Invited at %s, not ready yet", format_datetime(self.env, self.ocd_join_sent_at, tz=tz, dt_format="HH:mm"))
        return _("The invitation leaves %s minutes before the live", JOIN_INVITE_MINUTES)
