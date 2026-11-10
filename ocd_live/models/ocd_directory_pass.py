from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class OcdDirectoryPass(models.Model):
    """Prepaid right to send live links to the directory (Mobile Money cannot be charged
    automatically every month, so the pass is paid in advance and reminded before its end)."""

    _name = "ocd.directory.pass"
    _description = "Directory Pass"
    _inherit = ["mail.thread"]
    _order = "date_end desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True, default=lambda self: self.env._("New")
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Vendor", required=True, index=True, tracking=True
    )
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Pass",
        domain=[("ocd_product_kind", "=", "directory_pass")],
        check_company=True,
    )
    sale_line_id = fields.Many2one(
        comodel_name="sale.order.line", string="Order Line", copy=False, index="btree_not_null"
    )
    sale_order_id = fields.Many2one(
        related="sale_line_id.order_id", store=True, string="Order", index="btree_not_null"
    )
    date_start = fields.Date(string="From", required=True, tracking=True)
    date_end = fields.Date(string="Until", required=True, tracking=True)
    state = fields.Selection(
        selection=[
            ("scheduled", "Starts later"),
            ("active", "Active"),
            ("expired", "Expired"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="active",
        tracking=True,
        index=True,
    )
    reminder_sent = fields.Boolean(copy=False)

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for directory_pass in self:
            if directory_pass.date_end < directory_pass.date_start:
                raise ValidationError(self.env._("A pass ends after it starts."))

    @api.model_create_multi
    def create(self, vals_list):
        default_name = self.env._("New")
        for vals in vals_list:
            if vals.get("name", default_name) == default_name:
                vals["name"] = self.env["ir.sequence"].next_by_code("ocd.directory.pass") or default_name
        return super().create(vals_list)

    @api.model
    def _ocd_create_from_line(self, line):
        """Create the pass bought with a confirmed order line. A pass bought before the end of
        the current one starts the day after it, so that no day is lost."""
        partner = line.order_id.partner_id
        today = fields.Date.context_today(self)
        last = self.search(
            [("partner_id", "=", partner.id), ("state", "in", ("scheduled", "active"))],
            order="date_end desc, id desc",
            limit=1,
        )
        date_start = max(today, last.date_end + timedelta(days=1)) if last else today
        days = (line.product_id.ocd_pass_days or 30) * max(int(line.product_uom_qty), 1)
        return self.create({
            "partner_id": partner.id,
            "company_id": line.order_id.company_id.id,
            "product_id": line.product_id.id,
            "sale_line_id": line.id,
            "date_start": date_start,
            "date_end": date_start + timedelta(days=days - 1),
            "state": "scheduled" if date_start > today else "active",
        })

    def action_cancel(self):
        self.write({"state": "cancelled"})
        return True

    @api.model
    def _cron_update_states(self):
        today = fields.Date.context_today(self)
        self.search([("state", "=", "scheduled"), ("date_start", "<=", today)]).write({"state": "active"})
        self.search([("state", "in", ("scheduled", "active")), ("date_end", "<", today)]).write(
            {"state": "expired"}
        )

    @api.model
    def _cron_send_reminders(self):
        """Remind the vendors whose pass ends soon and who did not buy the next one."""
        today = fields.Date.context_today(self)
        passes = self.search([("state", "=", "active"), ("reminder_sent", "=", False)])
        to_remind = self.browse()
        later = self.search([("state", "=", "scheduled"), ("partner_id", "in", passes.partner_id.ids)])
        partners_with_next = set(later.partner_id.ids)
        for directory_pass in passes:
            days = directory_pass.company_id.ocd_pass_reminder_days
            if (
                directory_pass.date_end - timedelta(days=days) <= today
                and directory_pass.partner_id.id not in partners_with_next
            ):
                to_remind |= directory_pass
        for directory_pass in to_remind:
            directory_pass._ocd_send_reminder()
        to_remind.reminder_sent = True

    def _ocd_send_reminder(self):
        """Tell the vendor that the pass ends soon. Extended by ocd_live_whatsapp."""
        self.ensure_one()
        self.message_post(
            body=self.env._(
                "The pass of %(vendor)s ends on %(date)s.",
                vendor=self.partner_id.name,
                date=self.date_end,
            ),
            partner_ids=self.partner_id.ids,
        )
