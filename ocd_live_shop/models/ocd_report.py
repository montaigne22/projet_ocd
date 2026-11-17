"""Report a product or a vendor (chantier 2, design GarantieAvis): a customer tells the team what is
wrong (a fake, a misleading price, a scam…), with a word and their WhatsApp if they want. The team
sees the reports in « To check », grouped by product or vendor: nothing to do, or the product
removed from sale with a reason sent to the vendor (as a refusal). The vendor never knows who
reported. One report a day per person (or per device without a number) and per product or vendor."""
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

NOTE_MAX = 500


class OcdReport(models.Model):
    _name = "ocd.report"
    _description = "Report Of A Customer"
    _order = "create_date desc, id desc"
    _check_company_auto = True

    product_id = fields.Many2one(
        comodel_name="product.template", string="Product", index=True, ondelete="cascade",
        help="Empty: the vendor is reported.",
    )
    vendor_id = fields.Many2one(
        comodel_name="res.partner", string="Vendor", required=True, index=True, ondelete="cascade",
    )
    reason = fields.Selection(
        selection=[
            ("fake", "Fake, or copy of a brand"),
            ("misleading", "Misleading price or description"),
            ("scam", "Scam, or never delivered"),
            ("forbidden", "Forbidden or shocking product"),
            ("other", "Something else"),
        ],
        required=True,
    )
    note = fields.Text(string="Word Of The Customer")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Contact", ondelete="set null")
    phone = fields.Char(related="partner_id.phone", string="WhatsApp")
    visitor_key = fields.Char(index=True, readonly=True, help="The device that reported, without a number.")
    state = fields.Selection(
        selection=[("new", "To check"), ("done", "Action taken"), ("dismissed", "Nothing to do")],
        default="new", required=True, index=True,
    )
    decision = fields.Char(readonly=True)
    handled_at = fields.Datetime(readonly=True)
    handled_by_id = fields.Many2one(comodel_name="res.users", string="Handled By", readonly=True)
    company_id = fields.Many2one(
        comodel_name="res.company", required=True, index=True, default=lambda self: self.env.company
    )

    @api.depends("product_id", "vendor_id", "reason")
    def _compute_display_name(self):
        reasons = dict(self._fields["reason"]._description_selection(self.env))
        for report in self:
            target = report.product_id.name or report.vendor_id.name
            report.display_name = f"{target} · {reasons.get(report.reason, '')}"

    @api.model
    def _ocd_create(self, reason, note=None, product=None, vendor=None, partner=None, visitor_key=None):
        """A report of a customer, checked: a product on sale or a vendor online, one a day per
        person (or per device) and per product or vendor."""
        product, vendor = (product or self.env["product.template"]).sudo(), (vendor or self.env["res.partner"]).sudo()
        if product:
            vendor = product.ocd_vendor_id
            if not vendor or not product.is_published:
                raise UserError(self.env._("This product cannot be reported."))
        if not vendor or not vendor.ocd_is_vendor or vendor.ocd_vendor_state != "approved":
            raise UserError(self.env._("This vendor cannot be reported."))
        if reason not in dict(self._fields["reason"].selection):
            raise UserError(self.env._("Choose what is wrong."))
        note = " ".join((note or "").split())[:NOTE_MAX]
        if reason == "other" and not note:
            raise UserError(self.env._("Tell us what is wrong."))
        who = [("partner_id", "=", partner.id)] if partner else [("visitor_key", "=", visitor_key or "-")]
        if self.sudo().search_count(who + [
            ("product_id", "=", product.id or False), ("vendor_id", "=", vendor.id),
            ("create_date", ">=", fields.Datetime.now() - timedelta(days=1)),
        ]):
            raise UserError(self.env._("You already reported it today: the team looks at it."))
        return self.sudo().create({
            "product_id": product.id or False,
            "vendor_id": vendor.id,
            "reason": reason,
            "note": note or False,
            "partner_id": partner.id if partner else False,
            "visitor_key": False if partner else visitor_key,
            "company_id": (vendor.company_id or self.env.company).id,
        })

    def _ocd_close(self, state, decision):
        self.sudo().write({
            "state": state, "decision": decision, "handled_at": fields.Datetime.now(), "handled_by_id": self.env.uid,
        })


class ResPartner(models.Model):
    _inherit = "res.partner"

    ocd_report_count = fields.Integer(string="Reports", compute="_compute_ocd_report_count")

    def _compute_ocd_report_count(self):
        counts = dict(self.env["ocd.report"].sudo()._read_group(
            [("vendor_id", "in", self.ids), ("state", "=", "new")], ["vendor_id"], ["__count"]
        ))
        for partner in self:
            partner.ocd_report_count = counts.get(partner._origin, 0)

    def action_ocd_view_reports(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Reports of %s", self.name),
            "res_model": "ocd.report",
            "view_mode": "list,form",
            "domain": [("vendor_id", "=", self.id)],
        }
