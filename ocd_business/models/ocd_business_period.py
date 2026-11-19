"""The periods of OCD Business (chantier 12, design OcdBusiness, « Pour que ça tienne en vrai »).

The formula of a vendor is a chain of periods: paid (one per paid line of an order, unique), offered
by the team (with a reason), offered at the launch. « Until » is read from them, never typed: the
vendor has OCD Business up to the end of their last period not cancelled (res.partner,
`ocd_business_until`). A new period starts the day after the last one, or today when the formula
ended: no day is ever lost. The vendor is locked while the dates are computed: two confirmations of
the same payment add the days once, two payments at the same time lose none. A refund takes the days
not passed yet, never backwards, and the periods after it come closer."""
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

KINDS = [
    ("paid", "Paid"),
    ("offered", "Offered by the team"),
    ("launch", "Offered at the launch"),
]
STATES = [
    ("scheduled", "Later"),
    ("active", "Running"),
    ("ended", "Ended"),
    ("cancelled", "Cancelled"),
]


class OcdBusinessPeriod(models.Model):
    _name = "ocd.business.period"
    _description = "Period Of OCD Business"
    _inherit = ["mail.thread"]
    _order = "date_start desc, id desc"
    _check_company_auto = True

    vendor_id = fields.Many2one(
        comodel_name="res.partner", string="Vendor", required=True, index=True, ondelete="restrict", tracking=True,
    )
    company_id = fields.Many2one(comodel_name="res.company", required=True, index=True,
                                 default=lambda self: self.env.company)
    kind = fields.Selection(selection=KINDS, required=True, default="paid", tracking=True)
    date_start = fields.Date(string="From", required=True, tracking=True)
    date_end = fields.Date(string="Until", required=True, tracking=True, help="Included.")
    days = fields.Integer(required=True, readonly=True)
    state = fields.Selection(selection=STATES, required=True, default="scheduled", index=True, tracking=True)
    sale_line_id = fields.Many2one(
        comodel_name="sale.order.line", string="Order Line", readonly=True, index="btree_not_null",
        ondelete="restrict", copy=False,
    )
    sale_order_id = fields.Many2one(related="sale_line_id.order_id", string="Order", store=True, index="btree_not_null")
    currency_id = fields.Many2one(related="sale_line_id.currency_id", string="Currency")
    amount = fields.Monetary(related="sale_line_id.price_total", string="Paid", currency_field="currency_id")
    note = fields.Char(string="Why", tracking=True, help="Why the team offered these days, or cancelled them.")
    user_id = fields.Many2one(comodel_name="res.users", string="Offered By", readonly=True)

    _unique_sale_line = models.UniqueIndex(
        "(sale_line_id) WHERE sale_line_id IS NOT NULL", "A paid line gives one period of OCD Business."
    )

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for period in self:
            if period.date_end < period.date_start:
                raise ValidationError(self.env._("A period of OCD Business ends after it starts."))

    @api.depends("vendor_id.name", "date_start", "date_end")
    def _compute_display_name(self):
        for period in self:
            period.display_name = f"{period.vendor_id.name} · {period.date_start} → {period.date_end}"

    # === THE CHAIN OF A VENDOR === #

    @api.model
    def _ocd_lock(self, vendor):
        """The vendor is locked until the end of the transaction: the dates are computed by one
        payment at a time."""
        self.env.cr.execute("SELECT id FROM res_partner WHERE id = %s FOR UPDATE", [vendor.id])

    @api.model
    def _ocd_next_start(self, vendor, from_end=False):
        """The day a new period starts: the day after the last one, or today when it ended. With
        `from_end` (a payment checked during the grace), the day after the last one even if it
        passed: the days of grace are part of what is paid."""
        today = vendor._ocd_business_today()
        last = self.sudo().search([("vendor_id", "=", vendor.id), ("state", "!=", "cancelled")],
                                  order="date_end desc, id desc", limit=1)
        if not last:
            return today
        if from_end:
            return last.date_end + timedelta(days=1)
        return max(today, last.date_end + timedelta(days=1))

    @api.model
    def _ocd_state_for(self, start, end, today):
        if start > today:
            return "scheduled"
        return "active" if end >= today else "ended"

    @api.model
    def _ocd_add(self, vendor, days, kind, line=None, note=None, user=None, from_end=False):
        """Add `days` of OCD Business to `vendor` after their last period. A paid line gives one
        period only (unique in the database; checked again once the vendor is locked): an empty
        record when it already has its period."""
        if days < 1:
            raise UserError(self.env._("Give one day at least."))
        vendor = vendor.sudo()
        self._ocd_lock(vendor)
        if line:
            if self.sudo().search_count([("sale_line_id", "=", line.id)]):
                return self.browse()
        start = self._ocd_next_start(vendor, from_end=from_end)
        end = start + timedelta(days=days - 1)
        period = self.sudo().create({
            "vendor_id": vendor.id,
            "company_id": (line.order_id.company_id if line else vendor.company_id or self.env.company).id,
            "kind": kind,
            "date_start": start,
            "date_end": end,
            "days": days,
            "state": self._ocd_state_for(start, end, vendor._ocd_business_today()),
            "sale_line_id": line.id if line else False,
            "note": note or False,
            "user_id": user.id if user else False,
        })
        vendor._ocd_business_refresh()
        return period

    @api.model
    def _ocd_from_line(self, line):
        """A line of OCD Business paid (the order confirmed by the payment): its days, as bought
        (the product and the quantity of the order, never the settings of now)."""
        vendor = line.order_id.partner_id.commercial_partner_id
        days = (line.product_id.ocd_business_days or 30) * max(int(line.product_uom_qty), 1)
        grace = vendor.ocd_business_grace_until
        in_grace = bool(grace and grace >= vendor._ocd_business_today())
        period = self._ocd_add(vendor, days, "paid", line=line, from_end=in_grace)
        if period:
            vendor.sudo().ocd_business_grace_until = False
        return period

    def _ocd_cancel(self, note=None):
        """Cancel the days not passed yet (a refund, an order cancelled): a period not started is
        cancelled, a running one ends today; the days already passed stay. The periods after it
        come closer, so that no day is lost nor offered."""
        for period in self.sudo().filtered(lambda p: p.state != "cancelled"):
            vendor = period.vendor_id
            self._ocd_lock(vendor)
            today = vendor._ocd_business_today()
            if period.date_start > today:
                period.write({"state": "cancelled", "note": note or period.note})
            elif period.date_end >= today:
                period.write({"date_end": today, "state": "active", "note": note or period.note})
            period.message_post(body=self.env._("Days not passed yet taken back: %s", note or "-"))
            self._ocd_rechain(vendor)
            vendor._ocd_business_refresh()
        return True

    @api.model
    def _ocd_rechain(self, vendor):
        """The periods not started yet follow each other from the end of the ones before."""
        today = vendor._ocd_business_today()
        periods = self.sudo().search([("vendor_id", "=", vendor.id), ("state", "!=", "cancelled")],
                                     order="date_start, id")
        previous_end = None
        for period in periods:
            if period.date_start > today:
                start = max(today, previous_end + timedelta(days=1)) if previous_end else today
                if start != period.date_start:
                    end = start + timedelta(days=period.days - 1)
                    period.write({"date_start": start, "date_end": end,
                                  "state": self._ocd_state_for(start, end, today)})
            previous_end = max(previous_end, period.date_end) if previous_end else period.date_end

    # === ACTIONS OF THE TEAM === #

    def action_ocd_cancel(self):
        """Refunded: the days not passed yet are taken back."""
        if not self.env.user.has_group("ocd_live.group_ocd_live_manager"):
            raise AccessError(self.env._("Only a manager of OCD Live takes back days of OCD Business."))
        return self._ocd_cancel(self.env._("Refunded, by %s", self.env.user.name))

    # === EVERY DAY === #

    @api.model
    def _ocd_refresh_states(self):
        for period in self.sudo().search([("state", "in", ("scheduled", "active"))]):
            state = self._ocd_state_for(period.date_start, period.date_end, period.vendor_id._ocd_business_today())
            if state != period.state:
                period.state = state

    @api.model
    def _cron_ocd_business(self):
        """The states of the periods, the launch (once), the reminders and the end, told once per
        date of end."""
        self._ocd_refresh_states()
        self.env["res.company"].sudo().search([])._ocd_business_launch()
        self.env["res.partner"]._ocd_business_tell_ends()
