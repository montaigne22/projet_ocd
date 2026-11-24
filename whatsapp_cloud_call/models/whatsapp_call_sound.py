from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.whatsapp_cloud_call import const

# The messages with a role (one each per number); "voix" and "musique" are lists, played in turn.
SINGLE_KINDS = ("accueil", "enregistrement", "reconnexion", "messagerie", "indisponible")


class WhatsappCallSound(models.Model):
    """A message heard by the customers who call a WhatsApp number (welcome, recording notice,
    voice while waiting, music...), in MP3 or WAV. The call server fetches it, converts it and
    uses it without restarting; its folder sounds/ is the fallback when a number has none."""

    _name = "whatsapp.call.sound"
    _description = "Message of the WhatsApp Calls"
    _order = "account_id, kind, sequence, id"

    account_id = fields.Many2one(
        comodel_name="whatsapp.account", string="WhatsApp Account", required=True, index=True,
        ondelete="cascade",
    )
    kind = fields.Selection(
        selection=[
            ("accueil", "Welcome"),
            ("enregistrement", "Recording Notice"),
            ("voix", "Voice while Waiting"),
            ("musique", "Music while Waiting"),
            ("reconnexion", "Agent Cut Off"),
            ("messagerie", "Voicemail"),
            ("indisponible", "Nobody Available"),
        ],
        string="Message", required=True,
        help="Welcome: as soon as the call arrives. Recording Notice: after the welcome, and when the "
        "customer picks up a call of the company (when the calls are recorded). Voice while Waiting: "
        "over the music, every few seconds, one after the other. Music while Waiting: played one "
        "after the other. Agent Cut Off: while the call comes back. Voicemail: before the beep. "
        "Nobody Available: when there is no voicemail.",
    )
    sequence = fields.Integer(default=10, help="Order of the voices and of the music.")
    name = fields.Text(
        string="Text",
        help="What the message says, for the team who records it: a text in French and in English is "
        "proposed when the message is chosen (both said in the same file, French first).",
    )
    file = fields.Binary(string="File (MP3 or WAV)", attachment=True, required=True)
    file_name = fields.Char()
    checksum = fields.Char(compute="_compute_file_facts", store=True, readonly=True)
    size = fields.Integer(string="Size (bytes)", compute="_compute_file_facts", store=True)
    server_state = fields.Selection(
        selection=[("pending", "Being sent"), ("ok", "On the call server"), ("error", "Refused")],
        string="Call Server", default="pending", readonly=True, copy=False,
        help="Being sent: the call server takes it within a minute. Refused: see the reason.",
    )
    server_message = fields.Char(string="Reason", readonly=True, copy=False)

    _single_kind_uniq = models.UniqueIndex(
        "(account_id, kind) WHERE kind IN ('accueil', 'enregistrement', 'reconnexion', 'messagerie', 'indisponible')",
        "This message is already given for this number: change its file.",
    )

    @api.depends("kind", "file_name")
    def _compute_display_name(self):
        labels = dict(self._fields["kind"]._description_selection(self.env))
        for sound in self:
            label = labels.get(sound.kind) or ""
            sound.display_name = f"{label} ({sound.file_name})" if label and sound.file_name else label

    def _example(self, kind=None):
        """The text proposed for a message (French, then English), with the name of the business:
        the display name of the number at WhatsApp, else the name of the account."""
        texts = const.SOUND_EXAMPLES.get(kind or self.kind)
        if not texts:
            return False
        account = self.account_id
        business = account.verified_name or account.name or self.env.company.name
        return "\n".join(text.format(name=business) for text in texts)

    @api.onchange("kind")
    def _onchange_kind(self):
        """The text proposed for the message chosen, as long as the team has not written its own."""
        proposed = {self._example(kind) for kind in const.SOUND_EXAMPLES}
        if not self.name or self.name in proposed:
            self.name = self._example()

    def _file_attachment(self):
        self.ensure_one()
        return self.env["ir.attachment"].sudo().search([
            ("res_model", "=", self._name), ("res_field", "=", "file"), ("res_id", "=", self.id),
        ], limit=1)

    def _file_content(self):
        attachment = self._file_attachment()
        return bytes(attachment.raw) if attachment else b""

    @api.depends("file")
    def _compute_file_facts(self):
        for sound in self:
            attachment = sound._file_attachment() if sound.id else self.env["ir.attachment"]
            sound.checksum = attachment.checksum or False
            sound.size = attachment.file_size or 0

    @api.model
    def _format(self, content):
        """"mp3", "wav" or None, from the first bytes of the file."""
        head = bytes(content[:12])
        if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
            return "wav"
        if head[:3] == b"ID3" or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0):
            return "mp3"
        return None

    @api.constrains("file")
    def _check_file(self):
        for sound in self:
            content = sound._file_content()
            if len(content) > const.MAX_SOUND_SIZE:
                raise ValidationError(_("The file of a message is at most 20 MB."))
            if not self._format(content):
                raise ValidationError(_("The file of a message is an MP3 or a WAV."))

    def write(self, vals):
        if "file" in vals:
            vals = dict(vals, server_state="pending", server_message=False)
        return super().write(vals)

    def action_listen(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self._name}/{self.id}/file?download=false",
            "target": "new",
        }

    # === CALL SERVER === #

    def _server_entries(self):
        """The messages of a number for the call server (it fetches the ones it does not have)."""
        return [
            {"id": sound.id, "kind": sound.kind, "sequence": sound.sequence, "checksum": sound.checksum}
            for sound in self.sorted(lambda s: (s.kind, s.sequence, s.id)) if sound.checksum
        ]

    @api.model
    def _server_report(self, report):
        """What the call server did with each message: {id: {checksum, state, message}}; a report
        on an older file of the message is left aside."""
        if not isinstance(report, dict):
            return
        ids = [int(key) for key in report if str(key).isdigit()]
        for sound in self.sudo().browse(ids).exists():
            entry = report.get(str(sound.id)) or {}
            if not isinstance(entry, dict) or entry.get("checksum") != sound.checksum:
                continue
            state = "ok" if entry.get("state") == "ok" else "error"
            message = False if state == "ok" else str(entry.get("message") or "")[:200]
            if (sound.server_state, sound.server_message or False) != (state, message):
                super(WhatsappCallSound, sound).write({"server_state": state, "server_message": message})
