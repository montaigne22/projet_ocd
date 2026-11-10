from odoo import fields, models


class OcdVoiceLanguage(models.Model):
    """Language of the voice that reads the pages, e.g. French, English, Ewe, Pidgin."""

    _name = "ocd.voice.language"
    _description = "Voice Language"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, help="Short code, e.g. fr, en, ee.")
    speech_code = fields.Char(
        string="Voice Of The Phone",
        help="Language of the voice of the phone used when no recording exists, e.g. fr-FR. "
        "Empty: only the recordings are played.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _unique_code = models.UniqueIndex("(code)", "This language code already exists.")
