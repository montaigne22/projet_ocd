from odoo import _, fields, models

from odoo.addons.whatsapp_cloud_call.models.whatsapp_call import format_duration


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    whatsapp_call_ids = fields.One2many(
        comodel_name="whatsapp.call", inverse_name="channel_id", string="WhatsApp Calls"
    )

    def _whatsapp_get_info_sections(self):
        """The last calls of the customer next to the conversation."""
        sections = super()._whatsapp_get_info_sections()
        calls = self.env["whatsapp.call"].sudo().search([("channel_id", "=", self.id)], limit=5)
        if calls:
            states = dict(calls._fields["state"]._description_selection(self.env))
            sections.append({
                "title": _("Calls"),
                "items": [
                    {
                        "name": "%s · %s" % (
                            fields.Datetime.context_timestamp(self, call.start_date).strftime("%d/%m %H:%M"),
                            states.get(call.state),
                        ),
                        "detail": " · ".join(filter(None, [
                            call.user_id.name,
                            format_duration(self.env, call.duration) if call.duration else "",
                        ])),
                        "model": "whatsapp.call",
                        "id": call.id,
                    }
                    for call in calls
                ],
            })
        return sections
