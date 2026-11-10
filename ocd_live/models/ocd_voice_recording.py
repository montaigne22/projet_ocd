from odoo import fields, models


class OcdVoiceRecording(models.Model):
    _name = "ocd.voice.recording"
    _description = "Recorded Voice Of A Page"
    _order = "prompt_id, language_id, id"

    prompt_id = fields.Many2one(
        comodel_name="ocd.voice.prompt", string="Page", required=True, index=True, ondelete="cascade"
    )
    language_id = fields.Many2one(
        comodel_name="ocd.voice.language", string="Language", required=True, ondelete="cascade"
    )
    audio = fields.Binary(string="Audio File", attachment=True, required=True)
    audio_filename = fields.Char()
    mimetype = fields.Char(default="audio/mpeg")

    _unique_prompt_language = models.UniqueIndex(
        "(prompt_id, language_id)", "This page already has a recording in this language."
    )
