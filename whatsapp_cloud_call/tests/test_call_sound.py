import hashlib
import json
from unittest.mock import patch

import psycopg2

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import Form, HttpCase, tagged
from odoo.tools import BinaryBytes, mute_logger

from odoo.addons.whatsapp_cloud_call import const

from .common import WhatsAppCallCommon

MP3 = b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"\xff\xfb\x90\x00" * 64
WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 40


@tagged("post_install", "-at_install")
class TestCallSound(WhatsAppCallCommon, HttpCase):
    """The messages heard by the customers who call (welcome, voice while waiting...), given in
    Odoo, fetched by the call server."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.headers = {"Authorization": "Bearer server-key"}
        cls.Sound = cls.env["whatsapp.call.sound"]

    def sound(self, kind="accueil", content=MP3, **values):
        return self.Sound.create({
            "account_id": self.account.id, "kind": kind, "file": BinaryBytes(content, filename=f"{kind}.mp3"),
            "file_name": f"{kind}.mp3", **values,
        })

    def config(self, report=None):
        response = self.url_open("/whatsapp/call/server/config", data=json.dumps(report or {}),
                                 headers=self.headers)
        self.assertEqual(response.status_code, 200)
        return next(t for t in response.json()["trunks"] if t["phone_number_id"] == "1110001")

    def test_files_and_their_facts(self):
        sound = self.sound()
        self.assertEqual(sound.checksum, hashlib.sha1(MP3).hexdigest())
        self.assertEqual(sound.size, len(MP3))
        self.assertEqual(sound.server_state, "pending")
        self.assertEqual(sound._file_content(), MP3)
        self.assertTrue(self.sound("voix", WAV))
        with self.assertRaises(ValidationError):
            self.sound("messagerie", b"<html>not a sound</html>")
        with patch.object(const, "MAX_SOUND_SIZE", 100), self.assertRaises(ValidationError):
            self.sound("indisponible", MP3)

    def test_one_message_of_each_role_per_number(self):
        self.sound("accueil")
        self.sound("voix", sequence=1)
        self.sound("voix", sequence=2)  # the voices and the music are lists
        with mute_logger("odoo.sql_db"), self.assertRaises(psycopg2.IntegrityError), self.env.cr.savepoint():
            self.sound("accueil")

    def test_given_to_the_call_server_and_its_report(self):
        welcome = self.sound("accueil")
        voice = self.sound("voix", WAV, sequence=5)
        trunk = self.config()
        self.assertEqual(trunk["hold_voice_every"], 30)
        self.assertEqual(trunk["sounds"], [
            {"id": welcome.id, "kind": "accueil", "sequence": 10, "checksum": welcome.checksum},
            {"id": voice.id, "kind": "voix", "sequence": 5, "checksum": voice.checksum},
        ])
        # the call server fetches the file with its key
        self.assertEqual(self.url_open("/whatsapp/call/server/sound", data={"id": welcome.id}).status_code, 403)
        response = self.url_open("/whatsapp/call/server/sound", data={"id": welcome.id}, headers=self.headers)
        self.assertEqual(response.content, MP3)
        self.assertEqual(response.headers["Content-Type"], "audio/mpeg")
        self.assertEqual(response.headers["X-OCD-Checksum"], welcome.checksum)
        response = self.url_open("/whatsapp/call/server/sound", data={"id": voice.id}, headers=self.headers)
        self.assertEqual(response.headers["Content-Type"], "audio/wav")
        self.assertEqual(self.url_open("/whatsapp/call/server/sound", data={"id": 999999},
                                       headers=self.headers).status_code, 404)
        # what it did with them
        self.config({"sounds": {
            str(welcome.id): {"checksum": welcome.checksum, "state": "ok"},
            str(voice.id): {"checksum": voice.checksum, "state": "error", "message": "not an MP3 or a WAV"},
        }})
        welcome.invalidate_recordset()
        voice.invalidate_recordset()
        self.assertEqual(welcome.server_state, "ok")
        self.assertEqual((voice.server_state, voice.server_message), ("error", "not an MP3 or a WAV"))
        # a new file: sent again; a report on the former file is left aside
        former = welcome.checksum
        welcome.file = BinaryBytes(MP3 + b"\x00", filename="accueil.mp3")
        self.assertEqual(welcome.server_state, "pending")
        self.assertNotEqual(welcome.checksum, former)
        self.config({"sounds": {str(welcome.id): {"checksum": former, "state": "ok"}}})
        welcome.invalidate_recordset()
        self.assertEqual(welcome.server_state, "pending")

    def test_settings_and_access(self):
        self.account.call_hold_voice_every = 45
        with self.assertRaises(ValidationError):
            self.account.call_hold_voice_every = 5
        sound = self.sound()
        action = sound.action_listen()
        self.assertEqual(action["url"], f"/web/content/whatsapp.call.sound/{sound.id}/file?download=false")
        with self.assertRaises(AccessError):
            sound.with_user(self.agent).read(["name"])

    def test_proposed_texts(self):
        self.account.verified_name = "OCD Live"
        form = Form(self.Sound.with_context(default_account_id=self.account.id))
        form.kind = "accueil"
        self.assertEqual(form.name, "Bonjour et bienvenue chez OCD Live. Un conseiller va vous répondre dans "
                         "un instant.\nHello and welcome to OCD Live. An advisor will be with you in a moment.")
        form.kind = "messagerie"  # a proposed text follows the message chosen
        self.assertIn("Laissez votre message après le bip", form.name)
        self.assertIn("leave your message after the beep", form.name)
        form.kind = "musique"  # no text for the music
        self.assertFalse(form.name)
        form.kind = "voix"
        form.name = "Merci de rester en ligne."
        form.kind = "indisponible"  # the text of the team stays
        self.assertEqual(form.name, "Merci de rester en ligne.")
        # each message with a role has its text; the business is the name of the account without
        # the display name of WhatsApp
        self.account.verified_name = False
        self.assertIn(f"chez {self.account.name}.", self.Sound.new({"account_id": self.account.id})._example("accueil"))
        self.assertEqual(set(const.SOUND_EXAMPLES), {"accueil", "enregistrement", "voix", "reconnexion",
                                                     "messagerie", "indisponible"})
        sound = self.sound("voix")
        self.assertEqual(sound.display_name, "Voice while Waiting (voix.mp3)")
