from odoo import _, api, fields, models
from odoo.tools import format_datetime

from .whatsapp_call_sound import listen_action


class WhatsappCallRecording(models.Model):
    """The recording of a call (the customer and the agent), for a complete trace. Only the
    managers of WhatsApp listen to it: its file belongs to this model, which only they can read."""

    _name = "whatsapp.call.recording"
    _description = "Recording of a WhatsApp Call"
    _order = "id desc"

    call_id = fields.Many2one(
        comodel_name="whatsapp.call", string="Call", required=True, index=True, ondelete="cascade"
    )
    account_id = fields.Many2one(related="call_id.account_id", store=True)
    attachment_id = fields.Many2one(comodel_name="ir.attachment", string="File", readonly=True, ondelete="set null")
    mimetype = fields.Char(related="attachment_id.mimetype")
    size = fields.Integer(string="Size (bytes)", readonly=True)
    duration = fields.Integer(string="Duration (s)", related="call_id.duration")
    start_date = fields.Datetime(related="call_id.start_date", store=True)

    _call_uniq = models.Constraint("unique(call_id)", "A call has one recording.")

    @api.depends("call_id")
    def _compute_display_name(self):
        for recording in self:
            recording.display_name = _("Recording of %s", recording.call_id.display_name)

    def _url(self, download):
        self.ensure_one()
        if not self.attachment_id:
            return False
        return (f"/web/content/{self.attachment_id.id}?unique={self.attachment_id.checksum or ''}"
                f"&download={'true' if download else 'false'}")

    def action_listen(self):
        self.ensure_one()
        return listen_action(
            _("Recording of the call: %s", self.call_id.display_name), self._url(False), self._url(True),
            self.attachment_id.name or "",
        )

    def action_download(self):
        self.ensure_one()
        return {"type": "ir.actions.act_url", "url": self._url(True), "target": "self"}

    @api.model
    def _file_name(self, call, extension):
        start = format_datetime(self.env, call.start_date, dt_format="yyyy-MM-dd HH'h'mm") if call.start_date else ""
        return f"{call.display_name} {start}.{extension}".replace("/", "-").strip()

    @api.model
    def _cron_delete_old(self):
        """The recordings older than the days kept of their account (0: kept): deleted, the call
        notes it."""
        now = fields.Datetime.now()
        accounts = self.env["whatsapp.account"].sudo().with_context(active_test=False).search([
            ("call_recording_days", ">", 0),
        ])
        for account in accounts:
            old = self.sudo().search([
                ("account_id", "=", account.id),
                ("start_date", "<", now - account._call_recording_kept()),
            ])
            if old:
                old.call_id.write({"recording_status": "deleted"})
                old.attachment_id.unlink()
                old.unlink()
