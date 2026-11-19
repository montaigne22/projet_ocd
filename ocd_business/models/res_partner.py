from datetime import datetime, timedelta

import pytz

from odoo import api, fields, models


class ResPartner(models.Model):
    """The formula of OCD Business of a vendor (chantier 12, design OcdBusiness): the date of its
    end is read from its periods, its day is the one of the country of the vendor, a payment
    checked by the team keeps the features a few days after the end."""

    _inherit = "res.partner"

    ocd_business_period_ids = fields.One2many(
        comodel_name="ocd.business.period", inverse_name="vendor_id", string="Periods Of OCD Business",
    )
    ocd_business_grace_until = fields.Date(
        string="OCD Business Kept Until (Payment Checked)", copy=False, readonly=True,
        help="« I paid » for a Mobile Money checked by the team: the features stay until this day, the time of the "
             "check.",
    )
    ocd_business_reminded_for = fields.Date(string="First Reminder Sent For", copy=False, readonly=True)
    ocd_business_last_call_for = fields.Date(string="Reminder Of The Day Before Sent For", copy=False, readonly=True)
    ocd_business_end_told_for = fields.Date(string="End Told For", copy=False, readonly=True)

    # === THE DAY OF THE VENDOR === #

    def _ocd_business_today(self):
        """Today in the country of the vendor: the formula ends at midnight there."""
        self.ensure_one()
        tz = pytz.timezone(self._ocd_tz_name() or "UTC")
        return datetime.now(tz).date()

    def _ocd_business_refresh(self):
        """« Until » from the periods not cancelled: written only here (the team offers days, it
        never types a date)."""
        Period = self.env["ocd.business.period"].sudo()
        for partner in self.sudo():
            last = Period.search([("vendor_id", "=", partner.id), ("state", "!=", "cancelled")],
                                 order="date_end desc, id desc", limit=1)
            until = last.date_end if last else False
            if partner.ocd_business_until != until:
                partner.ocd_business_until = until

    # === THE ONE RULE === #

    def _ocd_business_formula(self):
        """Override of `ocd_live_shop`: their own formula today, in their country, or a payment
        checked by the team within the days of grace."""
        self.ensure_one()
        today = self._ocd_business_today()
        if self.ocd_business_until and self.ocd_business_until >= today:
            return True
        return bool(self.ocd_business_grace_until and self.ocd_business_grace_until >= today)

    def _ocd_business(self):
        """Override of `ocd_live_shop`: the features offered to all before the launch, or the
        formula of the vendor (with the grace of a payment checked)."""
        self.ensure_one()
        company = self.company_id or self.env.company
        return bool(company.ocd_business_offered_all) or self._ocd_business_formula()

    def _ocd_business_grace(self, order):
        """« I paid » for a Mobile Money checked by the team, for `order` of OCD Business: the
        features stay the days of grace after the end of the formula, the time of the check. A
        vendor without a formula, or whose formula ended long ago, gets nothing more."""
        self.ensure_one()
        company = order.company_id or self.env.company
        days = company.ocd_business_grace_days
        if not days or not self.ocd_business_until:
            return False
        grace = self.ocd_business_until + timedelta(days=days)
        if grace < self._ocd_business_today():
            return False
        if not self.ocd_business_grace_until or self.ocd_business_grace_until < grace:
            self.sudo().ocd_business_grace_until = grace
        return True

    # === WHAT THE SPACE SAYS === #

    def _ocd_business_space_note(self):
        """The line of « My space » about the formula: the end close, the payment checked, the end
        (30 days); nothing while the features are offered to all."""
        self.ensure_one()
        _ = self.env._
        company = self.company_id or self.env.company
        if company.ocd_business_offered_all or not self.ocd_business_until:
            return False
        today = self._ocd_business_today()
        until = self.ocd_business_until
        day = self._ocd_business_day_text(until)
        if self.ocd_business_grace_until and self.ocd_business_grace_until >= today and until < today:
            return {"kind": "grace", "title": _("Your payment of OCD Business is being checked."),
                    "line": _("Your features stay until %s, the time of the check.",
                              self._ocd_business_day_text(self.ocd_business_grace_until)),
                    "button": False}
        if today <= until <= today + timedelta(days=max(company.ocd_business_reminder_days, 1)):
            return {"kind": "soon", "title": _("Your formula OCD Business ends on %s.", day),
                    "line": _("Renew it to keep your stores shown, your team and your figures in detail."),
                    "button": _("Renew")}
        if today - timedelta(days=30) <= until < today:
            return {"kind": "ended", "title": _("Your formula OCD Business ended on %s.", day),
                    "line": _("Your stores beyond the first one are hidden, your team is paused: nothing is erased, "
                              "everything comes back with the formula."),
                    "button": _("Renew")}
        return False

    def _ocd_business_day_text(self, day):
        from odoo.addons.ocd_live.tools import day_text
        return day_text(self.env, day, "EEEE d MMMM")

    # === THE REMINDERS AND THE END === #

    @api.model
    def _ocd_business_tell_ends(self):
        """The first reminder (the days of the settings before), the one of the day before, then
        the end: each once per date of end, computed when sent (never after a renewal), never
        while the features are offered to all."""
        company = self.env.company
        if company.ocd_business_offered_all:
            return
        first = max(company.ocd_business_reminder_days, 1)
        horizon = fields.Date.context_today(self) + timedelta(days=first + 1)
        vendors = self.sudo().search([("ocd_business_until", "!=", False), ("ocd_business_until", "<=", horizon),
                                      ("ocd_business_until", ">=", fields.Date.context_today(self) - timedelta(days=2))])
        for vendor in vendors:
            until = vendor.ocd_business_until
            today = vendor._ocd_business_today()
            if until < today:
                if vendor.ocd_business_end_told_for != until and not vendor._ocd_business_formula():
                    vendor.ocd_business_end_told_for = until
                    vendor._ocd_business_tell("ended")
            elif until == today + timedelta(days=1):
                if vendor.ocd_business_last_call_for != until:
                    vendor.ocd_business_last_call_for = until
                    vendor._ocd_business_tell("last_call")
            elif until <= today + timedelta(days=first) and vendor.ocd_business_reminded_for != until:
                vendor.ocd_business_reminded_for = until
                vendor._ocd_business_tell("soon")

    def _ocd_business_tell(self, event):
        """Tell the vendor about their formula: paid, soon, last_call, ended, launch (extended by
        the WhatsApp module)."""

    # === THE TEAM === #

    def action_ocd_business_offer(self):
        """« Offer days »: a period offered, with its reason."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Offer days of OCD Business"),
            "res_model": "ocd.business.offer",
            "view_mode": "form",
            "target": "new",
            "context": {"default_vendor_id": self.id},
        }
