from odoo import api, fields, models
from odoo.addons.ocd_live.models.ocd_automation import WEEK


class OcdAutomation(models.Model):
    """The WhatsApp templates of an automation: they are sent only while it runs, its runs
    are the messages sent with them, and a template not approved by Meta is told."""

    _inherit = "ocd.automation"

    template_ids = fields.Many2many(comodel_name="whatsapp.template", string="WhatsApp Templates")

    @api.model
    def _ocd_template_enabled(self, template):
        """Whether every automation that sends `template` runs."""
        automations = self.sudo().search([("template_ids", "in", template.ids)])
        return all(automation._ocd_is_on() for automation in automations)

    def _ocd_runs(self):
        self.ensure_one()
        if getattr(self, f"_ocd_runs_{self.code}", None) or not self.template_ids:
            return super()._ocd_runs()
        messages = self.env["whatsapp.message"].sudo().search([
            ("template_id", "in", self.template_ids.ids),
            ("state", "!=", "skipped"),
            ("create_date", ">=", fields.Datetime.now() - WEEK),
        ], order="create_date desc, id desc")
        if not messages:
            return 0, False, ""
        return len(messages), messages[0].create_date, messages[0].partner_id.name or ""

    def _ocd_warning(self, on):
        warning = super()._ocd_warning(on)
        if not on or warning:
            return warning
        _ = self.env._
        waiting = self.template_ids.filtered(lambda template: template.status == "pending")
        refused = self.template_ids.filtered(lambda template: template.status in ("rejected", "paused", "disabled"))
        if refused:
            return _("The template %s cannot be sent: refused or paused by Meta. Change its text and submit it again.",
                     ", ".join(refused.mapped("template_name")))
        if waiting:
            return _("The template %s waits for the approval of Meta: until then, this message does not go.",
                     ", ".join(waiting.mapped("template_name")))
        return ""

    def _ocd_row(self):
        row = super()._ocd_row()
        if self.template_ids:
            row["templates"] = sorted(set(self.template_ids.mapped("template_name")))
        return row
