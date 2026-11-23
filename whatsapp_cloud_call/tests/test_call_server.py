import base64
import json

from odoo.tests import HttpCase, tagged

from odoo.addons.whatsapp_cloud_call import const


@tagged("post_install", "-at_install")
class TestCallServerApi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        params = cls.env["ir.config_parameter"].sudo()
        params.set_str(const.PARAM_HOST, "calls.example.com")
        params.set_str(const.PARAM_TOKEN, "server-key")
        cls.agent = cls.env["res.users"].create({
            "name": "Afi Agent",
            "login": "afi.agent",
            "password": "afi.agent.password",
            "group_ids": [(4, cls.env.ref("whatsapp_cloud.group_whatsapp_user").id)],
            "whatsapp_call_available": True,
        })
        cls.account = cls.env["whatsapp.account"].create({
            "name": "OCD",
            "phone_number_id": "1110001",
            "waba_id": "2220002",
            "access_token": "test-token",
            "app_secret": "test-secret",
            "call_enabled": True,
            "display_phone_number": "+228 90 00 00 01",
            "agent_user_ids": [(6, 0, cls.agent.ids)],
            "resource_calendar_id": False,
        })
        cls.account.sudo().call_sip_password = "meta-sip-password"
        cls.headers = {"Authorization": "Bearer server-key"}

    def test_refused_without_the_key(self):
        response = self.url_open("/whatsapp/call/server/config", data="{}")
        self.assertEqual(response.status_code, 403)
        response = self.url_open("/whatsapp/call/server/config", data="{}",
                                 headers={"Authorization": "Bearer wrong"})
        self.assertEqual(response.status_code, 403)

    def test_config_and_report(self):
        response = self.url_open(
            "/whatsapp/call/server/config",
            data=json.dumps({"registrations": [f"agent{self.agent.id}"], "version": "1.10.12", "spool": 0}),
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["domain"], "calls.example.com")
        self.assertEqual(data["trunks"], [{
            "phone_number_id": "1110001", "number": "22890000001", "password": "meta-sip-password",
            "max_wait": 180, "voicemail": True, "record": False,
        }])
        self.assertEqual(data["agents"][0]["login"], f"agent{self.agent.id}")
        self.assertTrue(data["agents"][0]["password"])
        server = self.env["whatsapp.call.server"]._get()
        self.assertTrue(server.last_seen)
        self.assertEqual(server.registrations, f"agent{self.agent.id}")
        self.assertEqual(server.version, "1.10.12")

    def test_basic_authentication(self):
        """mod_json_cdr sends the key as the password of a basic authentication."""
        basic = base64.b64encode(b"freeswitch:server-key").decode()
        response = self.url_open("/whatsapp/call/server/cdr", data=json.dumps({"variables": {}}),
                                 headers={"Authorization": f"Basic {basic}"})
        self.assertEqual(response.status_code, 200)

    def test_route_event_and_cdr(self):
        response = self.url_open("/whatsapp/call/server/route", data={
            "wacid": "wacid.HTTP", "uuid": "u-1", "number": "+237670000000",
            "phone_number_id": "1110001",
        }, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        lines = dict(line.split("=", 1) for line in response.text.strip().splitlines())
        self.assertEqual(lines["agents"], f"agent{self.agent.id}")
        self.assertEqual(lines["voicemail"], "1")
        call = self.env["whatsapp.call"].browse(int(lines["call"]))
        response = self.url_open("/whatsapp/call/server/event", data={
            "event": "answered", "call": lines["call"], "agent": f"agent{self.agent.id}",
        }, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(call.state, "answered")
        cdr = {"variables": {"ocd_wacid": "wacid.HTTP", "ocd_outcome": "completed", "ocd_talk": "61",
                             "ocd_answered_agent": f"agent{self.agent.id}", "hangup_cause": "NORMAL_CLEARING"}}
        # posted url-encoded in the field "cdr"
        response = self.url_open("/whatsapp/call/server/cdr", data={"cdr": json.dumps(cdr)},
                                 headers=self.headers)
        self.assertEqual(response.status_code, 200)
        call.invalidate_recordset()
        self.assertEqual(call.state, "completed")
        self.assertEqual(call.duration, 61)

    def test_voicemail_upload(self):
        self.url_open("/whatsapp/call/server/route", data={
            "wacid": "wacid.VM", "number": "+237670000000", "phone_number_id": "1110001",
        }, headers=self.headers)
        response = self.url_open(
            "/whatsapp/call/server/voicemail",
            data={"wacid": "wacid.VM"},
            files={"file": ("message.wav", b"RIFF....WAVEfmt ", "audio/wav")},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        call = self.env["whatsapp.call"].search([("wacid", "=", "wacid.VM")])
        self.assertEqual(call.state, "voicemail")
        self.assertTrue(call.voicemail_attachment_id)
        # unknown call: refused, the call server keeps the message for later
        response = self.url_open(
            "/whatsapp/call/server/voicemail", data={"call": "999999"},
            files={"file": ("message.wav", b"RIFF", "audio/wav")}, headers=self.headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_softphone_routes(self):
        self.authenticate("afi.agent", "afi.agent.password")
        config = self.make_jsonrpc_request("/whatsapp/call/softphone/config", {})
        self.assertEqual(config["login"], f"agent{self.agent.id}")
        config = self.make_jsonrpc_request("/whatsapp/call/softphone/available", {"available": False})
        self.assertFalse(config["available"])
        self.assertFalse(self.agent.whatsapp_call_available)
        call = self.env["whatsapp.call"]._server_route({
            "wacid": "wacid.SOFT", "number": "+237670000000", "phone_number_id": "1110001",
        })["call"]
        info = self.make_jsonrpc_request("/whatsapp/call/softphone/info", {"call_id": call})
        self.assertEqual(info["number"], "+237670000000")
        self.make_jsonrpc_request("/whatsapp/call/softphone/declined", {"call_id": call})
        self.assertIn(self.agent, self.env["whatsapp.call"].browse(call).declined_user_ids)
        # what the phone did when the agent answered, kept on the call
        self.make_jsonrpc_request("/whatsapp/call/softphone/trace", {
            "call_id": call, "trace": "phone 20.0.1.4.6; microphone 120 ms;\nanswer sent 2100 ms (relay)",
        })
        trace = self.env["whatsapp.call"].browse(call).phone_trace
        self.assertIn("Afi Agent: phone 20.0.1.4.6; microphone 120 ms; answer sent 2100 ms (relay)", trace)
