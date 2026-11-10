from odoo import api, fields, models


class OcdVoicePrompt(models.Model):
    """Sentence read aloud on a page of the website, with its recordings per language."""

    _name = "ocd.voice.prompt"
    _description = "Voice Of A Page"
    _order = "sequence, id"

    key = fields.Char(required=True, help="Technical key used by the page.")
    name = fields.Char(string="Page", required=True, translate=True)
    text = fields.Text(
        required=True,
        translate=True,
        help="Read by the voice of the phone when the page has no recording in the language.",
    )
    sequence = fields.Integer(default=10)
    recording_ids = fields.One2many(
        comodel_name="ocd.voice.recording", inverse_name="prompt_id", string="Recordings"
    )
    recording_count = fields.Integer(compute="_compute_recording_count")

    _unique_key = models.UniqueIndex("(key)", "This key already exists.")

    @api.depends("recording_ids")
    def _compute_recording_count(self):
        for prompt in self:
            prompt.recording_count = len(prompt.recording_ids)

    def _ocd_voice_data(self, language, lang_code=None):
        """Return what the page needs to speak this prompt in `language`: the url of the
        recording, or the text and the voice of the phone."""
        self.ensure_one()
        recording = self.recording_ids.filtered(lambda r: r.language_id == language and r.audio)[:1]
        text = self.with_context(lang=lang_code).text if lang_code else self.text
        return {
            "url": f"/ocd/voix/audio/{recording.id}" if recording else False,
            "text": text if language.speech_code else False,
            "speech_code": language.speech_code or False,
        }
