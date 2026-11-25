import io
import math
import struct
import wave
from unittest.mock import MagicMock, patch

from odoo.tests import tagged

from odoo.addons.whatsapp_cloud import audio

from .common import REQUEST, WhatsAppCommon, mock_response

DOWNLOAD = "odoo.addons.whatsapp_cloud.models.whatsapp_account.requests.get"
FFMPEG = "odoo.addons.whatsapp_cloud.audio.ffmpeg"
CONVERT = "odoo.addons.whatsapp_cloud.audio.convert"


def wav(seconds=1.0, rate=16000):
    """A short sound: a tone of 440 Hz, in WAV."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(rate)
        file.writeframes(b"".join(
            struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * index / rate)))
            for index in range(int(seconds * rate))
        ))
    return buffer.getvalue()


@tagged("post_install", "-at_install")
class TestWhatsAppVoice(WhatsAppCommon):
    """The voice messages: recorded in Odoo (MP3), they reach the customer as voice notes (OGG
    Opus); those of the customers (OGG Opus) are kept as MP3, played by every browser (old iPhones
    too). With ffmpeg; without it, the files go and stay as they are."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account.bot_enabled = False
        cls.has_ffmpeg = bool(audio.ffmpeg())

    def setUp(self):
        super().setUp()
        if not self.has_ffmpeg:
            self.skipTest("ffmpeg is not installed on this server")

    def channel(self):
        message = self.env["whatsapp.message"]._process_incoming(self.account, {
            "from": "237670000000", "id": "wamid.IN1", "timestamp": "1760000000", "type": "text",
            "text": {"body": "Bonjour"},
        }, [{"profile": {"name": "Awa"}, "wa_id": "237670000000"}])
        return message.channel_id

    def post_file(self, channel, name, raw, mimetype, voice=False):
        attachment = self.env["ir.attachment"].create({
            "name": name, "raw": raw, "mimetype": mimetype, "res_model": "discuss.channel", "res_id": channel.id,
        })
        if voice:
            attachment._set_voice_metadata()
        channel.message_post(body="", message_type="comment", attachment_ids=attachment.ids)
        return self.env["whatsapp.message"].search([("attachment_id", "=", attachment.id)])

    def send(self, message):
        answers = [mock_response({"id": "media-1"}), mock_response({"messages": [{"id": "wamid.OUT"}]})]
        with patch(REQUEST, side_effect=answers) as request:
            message._send()
        upload, sent = request.call_args_list
        return upload.kwargs["files"]["file"], sent.kwargs["json"]

    def test_conversions(self):
        voice = audio.convert(wav(), "voice")
        self.assertTrue(voice.startswith(b"OggS"))
        self.assertIn(b"OpusHead", voice[:200], "Opus in OGG: the voice notes of WhatsApp")
        mp3 = audio.convert(voice, "mp3")
        self.assertTrue(mp3[:3] == b"ID3" or mp3[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"))
        self.assertIsNone(audio.convert(b"not a sound", "mp3"))
        self.assertIsNone(audio.convert(b"", "voice"))

    def test_voice_message_of_odoo_is_a_voice_note(self):
        """Recorded in Odoo (MP3): converted to OGG Opus and sent with « voice »."""
        channel = self.channel()
        mp3 = audio.convert(wav(), "mp3")
        message = self.post_file(channel, "Voice-2026-11-25.mp3", mp3, "audio/mpeg", voice=True)
        self.assertEqual(message.message_type, "audio")
        (name, raw, mimetype), sent = self.send(message)
        self.assertEqual((name, mimetype), ("Voice-2026-11-25.ogg", "audio/ogg"))
        self.assertTrue(raw.startswith(b"OggS"))
        self.assertEqual(sent["audio"], {"id": "media-1", "voice": True})
        self.assertEqual(message.state, "sent")
        # the conversation keeps the file recorded (played by every browser)
        self.assertEqual(message.attachment_id.mimetype, "audio/mpeg")

    def test_sound_whatsapp_does_not_take(self):
        """A WAV: converted to OGG Opus, a plain sound; an MP3 file goes as it is."""
        channel = self.channel()
        message = self.post_file(channel, "annonce.wav", wav(), "audio/wav")
        self.assertEqual(message.message_type, "audio")
        (name, _raw, mimetype), sent = self.send(message)
        self.assertEqual((name, mimetype), ("annonce.ogg", "audio/ogg"))
        self.assertEqual(sent["audio"], {"id": "media-1"})
        song = self.post_file(channel, "jingle.mp3", audio.convert(wav(), "mp3"), "audio/mpeg")
        (name, _raw, mimetype), sent = self.send(song)
        self.assertEqual((name, mimetype, sent["type"]), ("jingle.mp3", "audio/mpeg", "audio"))

    def test_without_ffmpeg(self):
        """No ffmpeg: the voice message goes as a plain sound, a WAV as a document; the health of
        the account says it."""
        channel = self.channel()
        with patch(FFMPEG, return_value=None):
            voice = self.post_file(channel, "Voice.mp3", audio.convert(wav(), "mp3"), "audio/mpeg", voice=True)
            (name, _raw, mimetype), sent = self.send(voice)
            self.assertEqual((name, mimetype, sent["audio"]), ("Voice.mp3", "audio/mpeg", {"id": "media-1"}))
            sound = self.post_file(channel, "annonce.wav", wav(), "audio/wav")
            self.assertEqual(sound.message_type, "document")
            with patch(REQUEST, return_value=mock_response({"error": {"code": 190, "message": "token"}}, 400)):
                self.account._check_health()
            self.assertIn("ffmpeg is not installed", self.account.health_message)

    def test_conversion_failed_sends_a_document(self):
        """Queued as a sound to convert, not converted when it leaves: a document, never a sound
        WhatsApp would refuse."""
        channel = self.channel()
        message = self.post_file(channel, "annonce.wav", wav(), "audio/wav")
        with patch(CONVERT, return_value=None):
            (name, _raw, mimetype), sent = self.send(message)
        self.assertEqual((name, mimetype), ("annonce.wav", "audio/wav"))
        self.assertEqual(sent["type"], "document")
        self.assertEqual(sent["document"], {"id": "media-1", "filename": "annonce.wav"})

    def test_voice_note_of_a_customer_kept_as_mp3(self):
        """A voice note of a customer (OGG Opus): kept as MP3, played by old iPhones too."""
        ogg = audio.convert(wav(), "voice")
        download = MagicMock()
        download.raise_for_status.return_value = None
        download.iter_content.return_value = [ogg]
        download.headers = {"Content-Type": "audio/ogg"}
        with patch(DOWNLOAD, return_value=download), patch(REQUEST):
            message = self.env["whatsapp.message"]._process_incoming(self.account, {
                "from": "237670000000", "id": "wamid.VOICE", "timestamp": "1760000000", "type": "audio",
                "audio": {"id": "media-7", "mime_type": "audio/ogg; codecs=opus", "voice": True,
                          "url": "https://lookaside.fbsbx.com/whatsapp_business/attachments/?mid=7"},
            }, [{"profile": {"name": "Awa"}, "wa_id": "237670000000"}])
        attachment = message.attachment_id
        self.assertEqual(attachment.mimetype, "audio/mpeg")
        self.assertTrue(attachment.name.startswith("Voice message-"))
        self.assertTrue(attachment.name.endswith(".mp3"))
        self.assertEqual(message.mail_message_id.attachment_ids, attachment)
        # a sound every browser plays stays as it is
        mp3 = audio.convert(wav(), "mp3")
        download.iter_content.return_value = [mp3]
        download.headers = {"Content-Type": "audio/mpeg"}
        with patch(DOWNLOAD, return_value=download), patch(REQUEST), patch(CONVERT) as convert:
            message = self.env["whatsapp.message"]._process_incoming(self.account, {
                "from": "237670000000", "id": "wamid.SONG", "timestamp": "1760000000", "type": "audio",
                "audio": {"id": "media-8", "mime_type": "audio/mpeg",
                          "url": "https://lookaside.fbsbx.com/whatsapp_business/attachments/?mid=8"},
            }, [{"profile": {"name": "Awa"}, "wa_id": "237670000000"}])
        convert.assert_not_called()
        self.assertEqual(bytes(message.attachment_id.raw), mp3)
