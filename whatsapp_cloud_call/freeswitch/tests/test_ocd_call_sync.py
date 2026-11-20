"""Tests of ocd-call-sync and of the exchanges of the scripts with Odoo, without FreeSWITCH:

    python3 -m unittest discover -s whatsapp_cloud_call/freeswitch/tests -p "test_*.py"

The Lua parts run with lua5.3 (or lua) when it is installed.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs
from xml.etree import ElementTree

HERE = Path(__file__).resolve().parent
FREESWITCH = HERE.parent
sys.path.insert(0, str(FREESWITCH / "sync"))

import ocd_call_sync  # noqa: E402

LUA = shutil.which("lua5.3") or shutil.which("lua5.4") or shutil.which("lua")

CONFIG = {
    "domain": "calls.example.com",
    "trunks": [{"phone_number_id": "1110001", "number": "22890000001", "password": 'p&"ss<w>',
                "max_wait": 120, "voicemail": True}],
    "agents": [
        {"login": "agent5", "password": "secret5", "name": "Afi & Co", "available": True},
        {"login": "../evil", "password": "x", "name": "Bad"},
    ],
}


class FakeOdoo(BaseHTTPRequestHandler):
    requests = []
    status = 200

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        FakeOdoo.requests.append((self.path, dict(self.headers), body))
        if self.headers.get("Authorization") != "Bearer server-key":
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(FakeOdoo.status)
        if self.path == "/whatsapp/call/server/config":
            payload = json.dumps(CONFIG).encode()
            self.send_header("Content-Type", "application/json")
        elif self.path == "/whatsapp/call/server/route":
            payload = b"call=12\nname=Awa Ngono\nfirst=\nagents=agent5\nmax_wait=120\nvoicemail=1\nopen=1\n"
        else:
            payload = b"OK\n"
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


class TestSync(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOdoo)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        FakeOdoo.requests = []
        FakeOdoo.status = 200
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        # a fake fs_cli: notes the commands, answers the registrations
        self.fs_log = self.tmp / "fs.log"
        fs_cli = self.tmp / "fs_cli"
        fs_cli.write_text(
            "#!/bin/sh\n"
            f"echo \"$@\" >> {self.fs_log}\n"
            "case \"$*\" in\n"
            "  *xmlstatus*) echo '<profile><registrations><registration><user>agent5@calls.example.com</user>"
            "</registration></registrations></profile>';;\n"
            "  *version*) echo 'FreeSWITCH Version 1.10.12';;\n"
            "esac\n"
        )
        fs_cli.chmod(fs_cli.stat().st_mode | stat.S_IEXEC)
        self.conf = dict(ocd_call_sync.DEFAULTS)
        self.conf.update({
            "odoo_url": self.url,
            "token": "server-key",
            "fs_cli": str(fs_cli),
            "directory_dir": str(self.tmp / "directory"),
            "state_dir": str(self.tmp / "state"),
            "spool_dir": str(self.tmp / "spool"),
        })
        for folder in ("voicemail", "cdr-errors"):
            (self.tmp / "spool" / folder).mkdir(parents=True)

    def test_run_once_writes_the_users(self):
        sync = ocd_call_sync.Sync(self.conf)
        self.assertTrue(sync.run_once())
        path, headers, body = FakeOdoo.requests[0]
        self.assertEqual(path, "/whatsapp/call/server/config")
        report = json.loads(body)
        self.assertEqual(report["registrations"], ["agent5"])
        self.assertIn("1.10.12", report["version"])
        agents = ElementTree.parse(self.tmp / "directory" / "agents.xml").getroot()
        users = [user.get("id") for user in agents.iter("user")]
        self.assertEqual(users, ["agent5"], "Only the logins agent<id>")
        self.assertEqual(agents.find(".//param").get("value"), "secret5")
        meta = ElementTree.parse(self.tmp / "directory" / "meta.xml").getroot()
        self.assertEqual([u.get("id") for u in meta.iter("user")], ["+22890000001", "22890000001"])
        self.assertEqual(meta.find(".//param").get("value"), 'p&"ss<w>')
        self.assertIn("reloadxml", self.fs_log.read_text())
        headers_file = (self.tmp / "state" / "odoo_headers").read_text()
        self.assertEqual(headers_file, "Authorization: Bearer server-key\n")
        self.assertEqual(oct((self.tmp / "state" / "odoo_headers").stat().st_mode & 0o777), "0o640")

    def test_nothing_reloaded_when_unchanged(self):
        sync = ocd_call_sync.Sync(self.conf)
        sync.run_once()
        self.fs_log.write_text("")
        sync.run_once()
        self.assertNotIn("reloadxml", self.fs_log.read_text())

    def test_odoo_down_keeps_the_last_copy(self):
        sync = ocd_call_sync.Sync(self.conf)
        sync.run_once()
        before = (self.tmp / "directory" / "agents.xml").read_text()
        FakeOdoo.status = 500
        self.assertFalse(sync.run_once())
        self.assertEqual((self.tmp / "directory" / "agents.xml").read_text(), before)
        self.conf["odoo_url"] = "http://127.0.0.1:9"
        self.assertFalse(ocd_call_sync.Sync(self.conf).run_once())

    def test_voicemail_and_records_sent_again(self):
        voicemail = self.tmp / "spool" / "voicemail" / "uuid-1.wav"
        voicemail.write_bytes(b"RIFF....WAVEfmt " + b"\0" * 100)
        (self.tmp / "spool" / "voicemail" / "uuid-1.txt").write_text("call=12\nwacid=wacid.A\nuuid=uuid-1\n")
        record = self.tmp / "spool" / "cdr-errors" / "uuid-2.cdr.json"
        record.write_text(json.dumps({"variables": {"ocd_wacid": "wacid.B"}}))
        sync = ocd_call_sync.Sync(self.conf)
        self.assertTrue(sync.run_once())
        paths = [path for path, _headers, _body in FakeOdoo.requests]
        self.assertIn("/whatsapp/call/server/voicemail", paths)
        self.assertIn("/whatsapp/call/server/cdr", paths)
        body = next(b for p, _h, b in FakeOdoo.requests if p.endswith("voicemail"))
        self.assertIn(b'name="wacid"\r\n\r\nwacid.A', body)
        self.assertIn(b"RIFF....WAVE", body)
        self.assertFalse(voicemail.exists())
        self.assertFalse(record.exists())

    def test_strings_for_lua(self):
        self.assertEqual(ocd_call_sync.lua_string('a"b\\c\n'), '"a\\"b\\\\c\\010"')
        self.assertEqual(ocd_call_sync.lua_value({"b": [1, True], "a": "x"}), '{["a"] = "x", ["b"] = {1, true}}')

    @unittest.skipUnless(LUA, "Lua is not installed")
    def test_settings_read_by_lua(self):
        sync = ocd_call_sync.Sync(self.conf)
        sync.run_once()
        settings = self.tmp / "state" / "settings.lua"
        script = (
            f"package.path = {json.dumps(str(FREESWITCH / 'scripts') + '/?.lua')} .. ';' .. package.path\n"
            "local odoo = require('ocd.odoo')\n"
            f"local s = odoo.load_settings({json.dumps(str(settings))})\n"
            "print(s.domain, s.agents[1], #s.agents, s.trunks['1110001'].max_wait, s.trunks['1110001'].voicemail)\n"
        )
        output = subprocess.run([LUA, "-e", script], capture_output=True, text=True, check=True).stdout
        self.assertEqual(output.split(), ["calls.example.com", "agent5", "1", "120", "true"])

    @unittest.skipUnless(LUA and shutil.which("curl"), "Lua or curl is not installed")
    def test_lua_asks_odoo(self):
        """The script of the queue asks who rings (curl, the key read from the headers file)."""
        sync = ocd_call_sync.Sync(self.conf)
        sync.run_once()
        FakeOdoo.requests = []
        settings = self.tmp / "state" / "settings.lua"
        env = dict(os.environ, NO_PROXY="127.0.0.1", no_proxy="127.0.0.1")
        script = (
            f"package.path = {json.dumps(str(FREESWITCH / 'scripts') + '/?.lua')} .. ';' .. package.path\n"
            "local odoo = require('ocd.odoo')\n"
            f"local s = odoo.load_settings({json.dumps(str(settings))})\n"
            "local r = odoo.route(s, {wacid='wacid.X', uuid='u1', number='237670000000', pnid='1110001', business='22890000001'})\n"
            "print(r and r.call, r and r.agents)\n"
            "print(odoo.event(s, {event='ended', call='12', outcome='completed', talk=30}))\n"
        )
        output = subprocess.run([LUA, "-e", script], capture_output=True, text=True, check=True, env=env).stdout
        self.assertEqual(output.split(), ["12", "agent5", "true"])
        path, headers, body = FakeOdoo.requests[0]
        self.assertEqual(path, "/whatsapp/call/server/route")
        self.assertEqual(headers.get("Authorization"), "Bearer server-key")
        fields = parse_qs(body.decode())
        self.assertEqual(fields["wacid"], ["wacid.X"])
        self.assertEqual(fields["number"], ["237670000000"])
        self.assertEqual(parse_qs(FakeOdoo.requests[1][2].decode())["outcome"], ["completed"])

    @unittest.skipUnless(LUA, "Lua is not installed")
    def test_queue_lua(self):
        """Decisions of the queue, then whole calls through the script with a fake FreeSWITCH."""
        for script in ("test_queue.lua", "test_inbound.lua"):
            result = subprocess.run([LUA, str(HERE / script)], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
