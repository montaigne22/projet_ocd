from odoo import http
from odoo.http import request


class OcdLiveVoice(http.Controller):
    """Voice of the pages: the recording of the chosen language, or the text for the voice
    of the phone."""

    @http.route("/ocd/voix/<string:key>", type="jsonrpc", auth="public", website=True)
    def voice_data(self, key, lang=None):
        prompt = request.env["ocd.voice.prompt"].sudo().search([("key", "=", key)], limit=1)
        language = request.env["ocd.voice.language"].sudo().search([("code", "=", lang)], limit=1)
        if not language:
            language = request.env["ocd.voice.language"].sudo().search([], limit=1)
        if not prompt or not language:
            return {"url": False, "text": False, "speech_code": False}
        return prompt._ocd_voice_data(language, lang_code=request.lang.code)

    @http.route("/ocd/voix/audio/<int:recording_id>", type="http", auth="public", website=True, sitemap=False)
    def voice_audio(self, recording_id, **kwargs):
        recording = request.env["ocd.voice.recording"].sudo().browse(recording_id).exists()
        if not recording or not recording.audio or not recording.language_id.active:
            raise request.not_found()
        stream = request.env["ir.binary"]._get_stream_from(recording, "audio", filename=recording.audio_filename)
        stream.mimetype = recording.mimetype or "audio/mpeg"
        return stream.get_response(max_age=3600)
