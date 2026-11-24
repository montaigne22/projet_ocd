from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.whatsapp_cloud_call import const

# The messages with a role (one each per number); "voix" and "musique" are lists, played in turn.
SINGLE_KINDS = ("accueil", "enregistrement", "reconnexion", "messagerie", "indisponible")

# MPEG audio (MP3): kbit/s by bitrate index, for (MPEG-1, layer) and (MPEG-2 or 2.5, layer)
MPEG_BITRATES = {
    (True, 1): (0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448),
    (True, 2): (0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384),
    (True, 3): (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320),
    (False, 1): (0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256),
    (False, 2): (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
    (False, 3): (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
}
MPEG_RATES = {3: (44100, 48000, 32000), 2: (22050, 24000, 16000), 0: (11025, 12000, 8000)}


def mp3_frame(head):
    """(length in bytes, samples, sample rate) of the MPEG audio frame starting with these 4 bytes,
    or None when they are not the header of a frame."""
    if len(head) < 4 or head[0] != 0xFF or head[1] & 0xE0 != 0xE0:
        return None
    version, layer = (head[1] >> 3) & 3, 4 - ((head[1] >> 1) & 3)
    index, rate_index, padding = head[2] >> 4, (head[2] >> 2) & 3, (head[2] >> 1) & 1
    if version == 1 or layer == 4 or index in (0, 15) or rate_index == 3:
        return None
    bitrate = MPEG_BITRATES[(version == 3, layer)][index] * 1000
    rate = MPEG_RATES[version][rate_index]
    if layer == 1:
        return (12 * bitrate // rate + padding) * 4, 384, rate
    samples = 1152 if layer == 2 or version == 3 else 576
    return samples // 8 * bitrate // rate + padding, samples, rate


def mp3_seconds(content):
    """The length of an MP3, frame by frame (constant or variable bitrate); 0 when unknown."""
    data = bytes(content)
    pos = 0
    if data[:3] == b"ID3" and len(data) >= 10:  # a tag ID3v2 first (its size is "syncsafe")
        size = (data[6] & 0x7F) << 21 | (data[7] & 0x7F) << 14 | (data[8] & 0x7F) << 7 | data[9] & 0x7F
        pos = 10 + size + (10 if data[5] & 0x10 else 0)
    seconds, synced = 0.0, False
    while 0 <= pos <= len(data) - 4:
        frame = mp3_frame(data[pos:pos + 4])
        # out of step (junk, a tag at the end): a frame is taken again when the next one follows it
        if frame and not synced:
            following = data[pos + frame[0]:pos + frame[0] + 4]
            if following and not mp3_frame(following):
                frame = None
        if not frame:
            synced = False
            pos = data.find(b"\xff", pos + 1)
            continue
        synced = True
        seconds += frame[1] / frame[2]
        pos += frame[0]
    return seconds


def wav_seconds(content):
    """The length of a WAV: the size of its data over its bytes per second; 0 when unknown."""
    data = bytes(content)
    pos, byte_rate = 12, 0
    while pos + 8 <= len(data):
        chunk, size = data[pos:pos + 4], int.from_bytes(data[pos + 4:pos + 8], "little")
        if chunk == b"fmt " and size >= 16:
            byte_rate = int.from_bytes(data[pos + 16:pos + 20], "little")
        elif chunk == b"data":
            size = min(size, len(data) - pos - 8)
            return size / byte_rate if byte_rate else 0.0
        pos += 8 + size + (size & 1)
    return 0.0


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
    duration = fields.Float(
        string="Duration (s)", compute="_compute_file_facts", store=True, digits=(16, 1),
        help="How long the message lasts, read in its file.",
    )
    duration_advice = fields.Char(string="Recommended Duration", compute="_compute_duration_advice")
    too_long = fields.Boolean(compute="_compute_duration_advice")
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
            sound.duration = self._seconds(bytes(attachment.raw)) if attachment else 0.0

    @api.model
    def _seconds(self, content):
        """The length of an MP3 or a WAV, in seconds (0 when it cannot be read)."""
        try:
            kind = self._format(content)
            return round(wav_seconds(content) if kind == "wav" else mp3_seconds(content) if kind else 0.0, 1)
        except (IndexError, KeyError, ValueError, ZeroDivisionError):
            return 0.0

    @api.depends("kind", "duration")
    def _compute_duration_advice(self):
        for sound in self:
            seconds = const.SOUND_SECONDS.get(sound.kind)
            if sound.kind == "musique":
                sound.duration_advice = _("2 to 5 minutes, or several files")
            elif seconds:
                sound.duration_advice = _(
                    "About %(one)s s in one language, %(most)s s at most with both", one=seconds[0], most=seconds[1],
                )
            else:
                sound.duration_advice = False
            sound.too_long = bool(seconds and sound.duration > seconds[1])

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
