from odoo import _, api, fields, models


class IrActionsServer(models.Model):
    """"Send WhatsApp" action, for the automation rules and the server actions."""

    _inherit = "ir.actions.server"

    state = fields.Selection(
        selection_add=[("whatsapp", "Send WhatsApp")], ondelete={"whatsapp": "cascade"}
    )
    whatsapp_template_id = fields.Many2one(
        comodel_name="whatsapp.template",
        string="WhatsApp Template",
        compute="_compute_whatsapp_template_id",
        readonly=False,
        store=True,
        ondelete="set null",
        domain="[('model_id', '=', model_id)]",
    )

    def _name_depends(self):
        return [*super()._name_depends(), "whatsapp_template_id"]

    def _generate_action_name(self):
        self.ensure_one()
        if self.state == "whatsapp" and self.whatsapp_template_id:
            return _(
                "Send WhatsApp %(template_name)s", template_name=self.whatsapp_template_id.name
            )
        return super()._generate_action_name()

    @api.depends("model_id", "state")
    def _compute_whatsapp_template_id(self):
        self.filtered(
            lambda action: action.state != "whatsapp"
            or action.model_id != action.whatsapp_template_id.model_id
        ).whatsapp_template_id = False

    @api.model
    def _warning_depends(self):
        return [*super()._warning_depends(), "whatsapp_template_id"]

    def _get_warning_messages(self):
        self.ensure_one()
        warnings = super()._get_warning_messages()
        if self.state == "whatsapp" and self.model_id.transient:
            warnings.append(_("WhatsApp messages can only be sent from documents, not wizards."))
        return warnings

    def _run_action_whatsapp_multi(self, eval_context=None):
        if not self.whatsapp_template_id or self._is_recompute():
            return False
        records = eval_context.get("records") or eval_context.get("record")
        if records:
            self.whatsapp_template_id._send(records)
        return False
