from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WhatsappComposer(models.TransientModel):
    _name = "whatsapp.composer"
    _description = "Send a WhatsApp Message"

    res_model = fields.Char(required=True)
    res_ids = fields.Json(required=True)
    template_id = fields.Many2one(
        comodel_name="whatsapp.template",
        string="Template",
        required=True,
        domain="[('model', '=', res_model), "
        "('status', 'not in', ('rejected', 'paused', 'disabled'))]",
    )
    recipient = fields.Char(compute="_compute_preview")
    preview = fields.Text(compute="_compute_preview")
    warning = fields.Char(compute="_compute_preview")

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        context = self.env.context
        res_model = context.get("default_res_model") or context.get("active_model")
        res_ids = context.get("default_res_ids") or context.get("active_ids")
        if res_model and res_ids:
            result.update(res_model=res_model, res_ids=res_ids)
            if "template_id" in fields and not result.get("template_id"):
                result["template_id"] = self.env["whatsapp.template"].search(
                    [("model", "=", res_model)], limit=1
                ).id
        return result

    def _get_records(self):
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_ids or []).exists()

    @api.depends("template_id", "res_model", "res_ids")
    def _compute_preview(self):
        for composer in self:
            records = composer._get_records() if composer.res_model else None
            template = composer.template_id
            composer.recipient = composer.preview = composer.warning = False
            if not records or not template:
                continue
            record = records[:1]
            partner = template._get_recipient(record)
            number = partner._whatsapp_number() if partner else False
            if len(records) > 1:
                composer.recipient = _("%s documents", len(records))
            elif partner:
                composer.recipient = (
                    f"{partner.display_name} (+{number})" if number else partner.display_name
                )
            values = {
                variable._get_placeholder_key(): template._render(variable.value, record)[record.id]
                for variable in template.variable_ids
            }
            composer.preview = template._fill_body(values)
            account = template._get_account(record)
            if not account:
                composer.warning = _("No WhatsApp account is configured.")
            elif len(records) == 1:
                composer.warning = template._get_skip_reason(account, partner, number)

    def action_send(self):
        self.ensure_one()
        records = self._get_records()
        messages = self.template_id._send(records)
        if not messages:
            raise UserError(_("No WhatsApp account is configured."))
        queued = len(messages.filtered(lambda message: message.state == "queued"))
        skipped = messages.filtered(lambda message: message.state == "skipped")
        message = _("%s WhatsApp message(s) being sent.", queued)
        if skipped:
            message += " " + _("Not sent: %s", ", ".join(set(skipped.mapped("error"))))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": message,
                "type": "warning" if skipped else "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
