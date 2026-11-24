from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import HttpCase, tagged

from .common import WhatsAppCallCommon


@tagged("post_install", "-at_install")
class TestCallRecording(WhatsAppCallCommon, HttpCase):
    """The recordings of the calls (phase 3.1): asked by Odoo, sent by the call server once the
    call ended, listened by the managers only, deleted after the days kept."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.headers = {"Authorization": "Bearer server-key"}
        cls.manager = cls.env["res.users"].create({
            "name": "Mia Manager",
            "login": "mia.manager",
            "password": "mia.manager.password",
            "group_ids": [(4, cls.env.ref("whatsapp_cloud.group_whatsapp_manager").id)],
        })
        cls.agent.password = "afi.agent.password"

    def send(self, wacid, content=b"ID3\x04mp3-data", mimetype="audio/mpeg", call=None):
        return self.url_open(
            "/whatsapp/call/server/recording",
            data={"call": call} if call else {"wacid": wacid},
            files={"file": ("recording.mp3", content, mimetype)},
            headers=self.headers,
        )

    def test_the_call_server_is_told_to_record(self):
        route = self.route("wacid.R0")
        self.assertEqual(route["record"], 0)
        self.account.call_recording = True
        self.assertEqual(self.route("wacid.R1")["record"], 1)

    def test_recording_kept_for_the_managers(self):
        self.account.call_recording = True
        self.route("wacid.REC")
        call = self.Call.search([("wacid", "=", "wacid.REC")])
        self.assertEqual(call.recording_status, "none")
        response = self.send("wacid.REC")
        self.assertEqual(response.status_code, 200)
        call.invalidate_recordset()
        self.assertEqual(call.recording_status, "kept")
        recording = call.recording_id
        self.assertEqual(bytes(recording.attachment_id.raw), b"ID3\x04mp3-data")
        self.assertEqual(recording.attachment_id.mimetype, "audio/mpeg")
        self.assertEqual(recording.attachment_id.res_model, "whatsapp.call.recording")
        self.assertTrue(recording.attachment_id.name.endswith(".mp3"))
        # sent again (the call server did not get the answer): one recording
        self.assertEqual(self.send("wacid.REC").status_code, 200)
        self.assertEqual(self.env["whatsapp.call.recording"].search_count([("call_id", "=", call.id)]), 1)
        # the managers listen to it, the agents do not
        action = call.with_user(self.manager).action_listen_recording()
        # listened to in Odoo itself (a player, no new tab the browser could block)
        self.assertEqual(action["tag"], "whatsapp_call_audio")
        attachment = recording.attachment_id
        self.assertEqual(action["params"]["url"], f"/web/content/{attachment.id}?unique={attachment.checksum}&download=false")
        self.assertEqual(action["params"]["download_url"],
                         f"/web/content/{attachment.id}?unique={attachment.checksum}&download=true")
        self.assertEqual(action["params"]["file_name"], attachment.name)
        with self.assertRaises(AccessError):
            recording.with_user(self.agent).read(["size"])
        with self.assertRaises(AccessError):
            recording.attachment_id.with_user(self.agent).read(["raw"])
        self.authenticate("afi.agent", "afi.agent.password")
        self.assertNotEqual(self.url_open(f"/web/content/{recording.attachment_id.id}").status_code, 200)
        self.authenticate("mia.manager", "mia.manager.password")
        self.assertEqual(self.url_open(f"/web/content/{recording.attachment_id.id}").content, b"ID3\x04mp3-data")

    def test_refused_without_key_call_or_file(self):
        self.assertEqual(self.url_open("/whatsapp/call/server/recording", data={"wacid": "x"}).status_code, 403)
        # unknown call: kept on the call server for later
        self.assertEqual(self.send(None, call="999999").status_code, 400)
        self.route("wacid.EMPTY")
        self.assertEqual(self.send("wacid.EMPTY", content=b"").status_code, 400)

    def test_deleted_after_the_days_kept(self):
        self.account.write({"call_recording": True, "call_recording_days": 30})
        self.route("wacid.OLD")
        self.route("wacid.NEW")
        self.send("wacid.OLD")
        self.send("wacid.NEW")
        old = self.Call.search([("wacid", "=", "wacid.OLD")])
        new = self.Call.search([("wacid", "=", "wacid.NEW")])
        old.start_date = fields.Datetime.now() - timedelta(days=31)
        attachment = old.recording_id.attachment_id
        self.env["whatsapp.call.recording"]._cron_delete_old()
        self.assertEqual(old.recording_status, "deleted")
        self.assertFalse(old.recording_id)
        self.assertFalse(attachment.exists())
        self.assertEqual(new.recording_status, "kept")
        # a recording that comes after the deletion is not kept again
        self.send("wacid.OLD")
        self.assertFalse(old.recording_id)
        # 0: kept
        self.account.call_recording_days = 0
        new.start_date = fields.Datetime.now() - timedelta(days=400)
        self.env["whatsapp.call.recording"]._cron_delete_old()
        self.assertEqual(new.recording_status, "kept")

    def test_call_of_the_company_recorded(self):
        self.account.call_recording = True
        channel = self.env["discuss.channel"].sudo()._whatsapp_get_or_create(
            self.account, "237670000000", None, self.partner
        )
        call = self.Call.create({
            "account_id": self.account.id, "direction": "outbound", "channel_id": channel.id,
            "number": "237670000000", "user_id": self.agent.id,
        })
        answer = self.Call._server_outbound({"call": call.id, "agent": f"agent{self.agent.id}"})
        self.assertEqual(answer["record"], 1)
