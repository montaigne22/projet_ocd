from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import format_datetime

GROUPS = [
    ("lives", "Lives"),
    ("directory", "Directory"),
    ("shop", "Shop and deliveries"),
    ("money", "Money"),
    ("recruitment", "Recruitment"),
    ("technical", "Technical tasks"),
]
GROUP_ORDER = [key for key, _label in GROUPS]
KINDS = [
    ("rule", "Rule the team can pause"),
    ("cron", "At a fixed hour"),
    ("code", "Code of OCD Live"),
]
WEEK = timedelta(days=7)


class OcdAutomation(models.Model):
    """An automation of OCD Live in the catalogue of the team (BoAutomatisations): when...
    then..., on what, with which tools of Odoo, how often it ran these 7 days, and its switch.

    - kind "rule": the team pauses it here; the code asks `_ocd_enabled(code)` before acting
      (and ocd_live_whatsapp before sending its templates);
    - kind "cron": a scheduled action of Odoo, paused by archiving it;
    - kind "code": it protects the money or the proofs, written and tested in the modules.
    `locked`: always on (the rules of the code, and the technical tasks the system needs).
    Each module adds its automations in its data."""

    _name = "ocd.automation"
    _description = "Automation Of OCD Live"
    _order = "group_sequence, sequence, id"

    code = fields.Char(required=True, help="Key read by the code: `_ocd_enabled(code)`.")
    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    group = fields.Selection(selection=GROUPS, required=True, default="lives")
    group_sequence = fields.Integer(compute="_compute_group_sequence", store=True)
    kind = fields.Selection(selection=KINDS, required=True, default="rule")
    locked = fields.Boolean(help="Always on: it protects the money or the proofs, or the system needs it.")
    model_id = fields.Many2one(comodel_name="ir.model", string="On", ondelete="cascade")
    when = fields.Char(translate=True, help="Short line under the name, in the list.")
    trigger = fields.Char(string="When", translate=True)
    scope = fields.Char(string="For", translate=True)
    actions = fields.Text(string="Then, in this order", translate=True, help="One action per line.")
    tools = fields.Char(string="Made with", translate=True)
    note = fields.Char(translate=True, help="Shown in yellow in the detail.")
    cron_id = fields.Many2one(comodel_name="ir.cron", string="Scheduled Action", ondelete="set null")
    enabled = fields.Boolean(default=True, help="Switch of a rule without scheduled action.")

    _code_unique = models.UniqueIndex("(code)", "Each automation has its own key.")

    @api.depends("group")
    def _compute_group_sequence(self):
        for automation in self:
            automation.group_sequence = GROUP_ORDER.index(automation.group) if automation.group in GROUP_ORDER else 99

    # === SWITCH === #

    def _ocd_is_on(self):
        self.ensure_one()
        if self.locked:
            return True
        if self.cron_id:
            return self.cron_id.sudo().active
        return self.enabled

    @api.model
    def _ocd_enabled(self, code):
        """Whether the automation `code` runs (True when it is not in the catalogue)."""
        automation = self.sudo().search([("code", "=", code)], limit=1)
        return not automation or automation._ocd_is_on()

    # === PAGE === #

    @api.model
    def get_automations_page(self):
        self._ocd_check_manager()
        automations = self.sudo().search([])
        rows = [automation._ocd_row() for automation in automations]
        labels = dict(self._fields["group"]._description_selection(self.env))
        groups = [
            {"key": key, "label": labels[key], "rows": [row for row in rows if row["group"] == key]}
            for key in GROUP_ORDER
            if any(row["group"] == key for row in rows)
        ]
        counts = {kind: len([row for row in rows if row["kind"] == kind and row["group"] != "technical"]) for kind, _l in KINDS}
        _ = self.env._
        return {
            "groups": groups,
            "pager": _("%s automations", len(rows)),
            "kinds": [
                {"kind": "rule", "count": counts["rule"], "label": _("rules that the team can pause")},
                {"kind": "cron", "count": counts["cron"], "label": _("at a fixed hour")},
                {"kind": "code", "count": counts["code"], "label": _("in the code, because they touch the money or the proofs")},
            ],
        }

    @api.model
    def ocd_switch(self, automation_id, value):
        """The team pauses or starts again the automation."""
        self._ocd_check_manager()
        automation = self.sudo().browse(automation_id).exists()
        if not automation or automation.locked or automation.kind == "code":
            raise UserError(self.env._("This automation is always on."))
        if automation.cron_id:
            automation.cron_id.active = bool(value)
        else:
            automation.enabled = bool(value)
        return automation._ocd_row()

    @api.model
    def _ocd_check_manager(self):
        if not self.env.user.has_group("ocd_live.group_ocd_live_manager"):
            raise AccessError(self.env._("Only the managers of OCD Live see and switch the automations."))

    def _ocd_row(self):
        self.ensure_one()
        _ = self.env._
        count, last_date, last_label = self._ocd_runs()
        on = self._ocd_is_on()
        kinds = dict(self._fields["kind"]._description_selection(self.env))
        if self.locked:
            status = _("Always on")
        else:
            status = _("On") if on else _("Paused")
        return {
            "id": self.id,
            "code": self.code,
            "group": self.group,
            "kind": self.kind,
            "kind_label": kinds[self.kind],
            "name": self.name,
            "when": self.when or "",
            "model": self.model_id.name or "",
            "trigger": self.trigger or "",
            "scope": self.scope or "",
            "actions": [line.strip() for line in (self.actions or "").splitlines() if line.strip()],
            "tools": self.tools or "",
            "locked": self.locked,
            "active": on,
            "status": status,
            "warning": self._ocd_warning(on),
            "runs": count,
            "history": self._ocd_history_text(count, last_date, last_label),
            "foot": self._ocd_foot_text(),
        }

    def _ocd_warning(self, on):
        self.ensure_one()
        if not self.locked and not on:
            return self.env._("Paused: nothing goes any more for this automation. The team does these actions by hand.")
        return self.note or ""

    def _ocd_foot_text(self):
        self.ensure_one()
        _ = self.env._
        if self.group == "technical":
            return _("Technical task needed by the system: always on.")
        if self.kind == "code":
            return _("It protects the money or the proof of delivery: written and tested in the modules of OCD Live, the team cannot switch it off.")
        if self.kind == "cron":
            return _("Scheduled task: its hours and delays are set in the Settings, without touching the code.")
        return _("The team pauses it here; its texts are the WhatsApp templates and its delays are set in the Settings.")

    def _ocd_history_text(self, count, last_date, last_label):
        _ = self.env._
        if not count:
            return _("No run over 7 days.")
        text = _("1 run over 7 days.") if count == 1 else _("%s runs over 7 days.", f"{count:,}".replace(",", " "))
        if last_date:
            last = format_datetime(self.env, last_date, dt_format="EEE d MMM, HH:mm")
            last = f"{last} · {last_label}" if last_label else last
            text = _("%(text)s Last: %(last)s.", text=text, last=last)
        return text

    # === RUNS OVER 7 DAYS === #

    def _ocd_runs(self):
        """(count, last date, label of the last one) over the last 7 days: from the method
        `_ocd_runs_<code>` when the module gives one, else from the runs of the scheduled
        action."""
        self.ensure_one()
        method = getattr(self, f"_ocd_runs_{self.code}", None)
        if method:
            return method()
        if self.cron_id:
            since = fields.Datetime.now() - WEEK
            runs = self.env["ir.cron.progress"].sudo().search_count(
                [("cron_id", "=", self.cron_id.id), ("create_date", ">=", since)]
            )
            return runs, self.cron_id.sudo().lastcall if runs else False, ""
        return 0, False, ""

    @api.model
    def _ocd_runs_of(self, records, date_field, label=None):
        """(count, last date, label) of `records`, by their `date_field`."""
        if not records:
            return 0, False, ""
        last = max(records, key=lambda record: record[date_field] or fields.Datetime.now())
        return len(records), last[date_field], label(last) if label else last.display_name

    def _ocd_runs_booking_confirmed(self):
        since = fields.Datetime.now() - WEEK
        bookings = self.env["ocd.live.booking"].sudo().search([
            ("state", "in", ("confirmed", "done")), ("sale_order_id.date_order", ">=", since),
        ])
        if not bookings:
            return 0, False, ""
        last = max(bookings, key=lambda booking: booking.sale_order_id.date_order)
        return len(bookings), last.sale_order_id.date_order, last.partner_id.name
