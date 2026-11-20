#!/usr/bin/env python3
"""ocd-call-sync: the call server keeps up with Odoo, and works without it.

Every 30 seconds, on the call server (FreeSWITCH):

- tells Odoo that the call server runs (agents connected, version, files waiting);
- gets the agents, their passwords and the numbers with calls, and writes them for
  FreeSWITCH (directory of the users, settings of the scripts); FreeSWITCH reloads them
  only when they changed. When Odoo does not answer, the last copy stays: the calls ring
  for the agents copied last;
- sends to Odoo the messages left (voicemail) and the records of the calls that Odoo did
  not take when the call ended.

Python 3 only (no library to install). Configuration: /etc/ocd-call-sync.conf (see
ocd-call-sync.conf.example). Run by systemd (ocd-call-sync.service).
"""

import argparse
import configparser
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from xml.etree import ElementTree
from xml.sax.saxutils import quoteattr

_logger = logging.getLogger("ocd-call-sync")

DEFAULTS = {
    "interval": "30",
    "timeout": "10",
    "fs_cli": "/usr/bin/fs_cli",
    "fs_password": "",
    "directory_dir": "/etc/freeswitch/directory/ocd",
    "state_dir": "/var/lib/freeswitch/ocd",
    "spool_dir": "/var/spool/ocd-calls",
    "sounds_dir": "/usr/share/freeswitch/sounds/ocd",
    "hold_music": "local_stream://moh",
    "agents_profile": "ocd_agents",
}


def lua_string(value):
    """A Lua string literal."""
    out = ['"']
    for char in str(value):
        code = ord(char)
        if char in '"\\':
            out.append("\\" + char)
        elif code < 32 or code == 127:
            out.append("\\%03d" % code)
        else:
            out.append(char)
    out.append('"')
    return "".join(out)


def lua_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, dict):
        items = ", ".join(f"[{lua_string(k)}] = {lua_value(v)}" for k, v in sorted(value.items()))
        return "{" + items + "}"
    if isinstance(value, (list, tuple)):
        return "{" + ", ".join(lua_value(v) for v in value) + "}"
    return lua_string(value)


def write_if_changed(path, content, mode=0o640):
    """Write the file atomically when its content changed; return whether it changed."""
    path = Path(path)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(dir=path.parent, prefix=".ocd-")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(content)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return True


def valid_login(login):
    """Logins of the agents given by Odoo: agent<id of the user>."""
    login = str(login or "")
    return login.startswith("agent") and login[5:].isdigit()


def directory_agents(agents):
    """Users of the agents (profile ocd_agents, WebRTC)."""
    lines = ["<include>"]
    for agent in agents:
        login = str(agent.get("login") or "")
        if not valid_login(login):
            continue
        lines += [
            f"  <user id={quoteattr(login)}>",
            "    <params>",
            f"      <param name=\"password\" value={quoteattr(str(agent.get('password') or ''))}/>",
            "    </params>",
            "    <variables>",
            "      <variable name=\"user_context\" value=\"ocd_agents\"/>",
            f"      <variable name=\"effective_caller_id_name\" value={quoteattr(str(agent.get('name') or login))}/>",
            "    </variables>",
            "  </user>",
        ]
    lines.append("</include>")
    return "\n".join(lines) + "\n"


def directory_meta(trunks):
    """Users with which Meta signs its calls (digest): the business number, with and without +,
    and the SIP password given by Meta."""
    lines = ["<include>"]
    for trunk in trunks:
        number = "".join(ch for ch in str(trunk.get("number") or "") if ch.isdigit())
        password = str(trunk.get("password") or "")
        if not number or not password:
            continue
        for user in (f"+{number}", number):
            lines += [
                f"  <user id={quoteattr(user)}>",
                "    <params>",
                f"      <param name=\"password\" value={quoteattr(password)}/>",
                "    </params>",
                "    <variables>",
                "      <variable name=\"user_context\" value=\"ocd_whatsapp\"/>",
                f"      <variable name=\"ocd_trunk\" value={quoteattr(str(trunk.get('phone_number_id') or ''))}/>",
                "    </variables>",
                "  </user>",
            ]
    lines.append("</include>")
    return "\n".join(lines) + "\n"


def settings_lua(data, conf):
    """Settings read by the scripts of the queue."""
    settings = {
        "odoo_url": conf["odoo_url"].rstrip("/"),
        "headers_file": str(Path(conf["state_dir"]) / "odoo_headers"),
        "domain": data.get("domain") or "",
        "spool": conf["spool_dir"],
        "sounds": conf["sounds_dir"],
        "hold_music": conf["hold_music"],
        "agents": [a["login"] for a in data.get("agents") or [] if valid_login(a.get("login"))],
        "trunks": {
            str(t.get("phone_number_id")): {
                "number": str(t.get("number") or ""),
                "max_wait": int(t.get("max_wait") or 180),
                "voicemail": bool(t.get("voicemail", True)),
            }
            for t in data.get("trunks") or [] if t.get("phone_number_id")
        },
    }
    return "-- written by ocd-call-sync, do not change: changed again at its next run\nreturn " + lua_value(settings) + "\n"


def vars_secret(conf):
    """Variables of FreeSWITCH for mod_json_cdr (address of Odoo and the key)."""
    return (
        "<include>\n"
        f"  <X-PRE-PROCESS cmd=\"set\" data={quoteattr('ocd_odoo_url=' + conf['odoo_url'].rstrip('/'))}/>\n"
        f"  <X-PRE-PROCESS cmd=\"set\" data={quoteattr('ocd_odoo_token=' + conf['token'])}/>\n"
        "</include>\n"
    )


class Sync:

    def __init__(self, conf):
        self.conf = conf
        self.spool = Path(conf["spool_dir"])

    # === ODOO === #

    def _request(self, path, data=None, content_type="application/json", timeout=None):
        request = urllib.request.Request(
            self.conf["odoo_url"].rstrip("/") + path,
            data=data,
            headers={"Authorization": f"Bearer {self.conf['token']}", "Content-Type": content_type},
            method="POST",
        )
        timeout = timeout or float(self.conf["timeout"])
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()

    def fetch_config(self, report):
        status, body = self._request("/whatsapp/call/server/config", json.dumps(report).encode())
        if status != 200:
            raise RuntimeError(f"Odoo answered {status}")
        return json.loads(body)

    # === FREESWITCH === #

    def fs(self, command):
        args = [self.conf["fs_cli"], "-x", command]
        if self.conf.get("fs_password"):
            args[1:1] = ["-p", self.conf["fs_password"]]
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            _logger.warning("fs_cli %s: %s", command, error)
            return ""
        return result.stdout

    def registrations(self):
        """The agents connected now (profile ocd_agents)."""
        output = self.fs(f"sofia xmlstatus profile {self.conf['agents_profile']} reg")
        users = set()
        try:
            root = ElementTree.fromstring(output.strip() or "<profile/>")
        except ElementTree.ParseError:
            return []
        for registration in root.iter("registration"):
            user = (registration.findtext("user") or "").split("@")[0]
            if user:
                users.add(user)
        return sorted(users)

    def version(self):
        return self.fs("version").strip()[:64]

    # === FILES === #

    def spool_files(self):
        voicemails = sorted((self.spool / "voicemail").glob("*.wav"))
        cdrs = sorted((self.spool / "cdr-errors").glob("*.json"))
        return voicemails, cdrs

    def write_files(self, data):
        conf = self.conf
        directory = Path(conf["directory_dir"])
        changed = write_if_changed(directory / "agents.xml", directory_agents(data.get("agents") or []))
        changed |= write_if_changed(directory / "meta.xml", directory_meta(data.get("trunks") or []))
        state = Path(conf["state_dir"])
        write_if_changed(state / "settings.lua", settings_lua(data, conf), mode=0o640)
        write_if_changed(state / "odoo_headers", f"Authorization: Bearer {conf['token']}\n", mode=0o640)
        vars_changed = write_if_changed(state / "vars_secret.xml", vars_secret(conf), mode=0o640)
        if changed or vars_changed:
            self.fs("reloadxml")
            _logger.info("FreeSWITCH: users reloaded (%s agents)", len(data.get("agents") or []))
        if vars_changed:
            # the address of Odoo or the key changed: the records of the calls follow
            self.fs("reload mod_json_cdr")
        return changed

    def send_voicemails(self, files):
        """Messages left that Odoo did not take when the call ended."""
        for path in files:
            facts_path = path.with_suffix(".txt")
            facts = {}
            if facts_path.exists():
                for line in facts_path.read_text(encoding="utf-8").splitlines():
                    key, _sep, value = line.partition("=")
                    facts[key.strip()] = value.strip()
            if time.time() - path.stat().st_mtime < 60 and not facts:
                continue  # still being recorded
            body, content_type = multipart(facts, path)
            try:
                status, _answer = self._request("/whatsapp/call/server/voicemail", body, content_type, timeout=30)
            except urllib.error.HTTPError as error:
                status = error.code
            except (urllib.error.URLError, OSError) as error:
                _logger.warning("Voicemail %s not sent: %s", path.name, error)
                return
            if status == 200:
                path.unlink(missing_ok=True)
                facts_path.unlink(missing_ok=True)
                _logger.info("Voicemail %s sent to Odoo", path.name)
            elif time.time() - path.stat().st_mtime > 7 * 86400:
                # refused for a week (call unknown to Odoo): kept aside for the team
                path.rename(path.with_suffix(".refused.wav"))

    def send_cdrs(self, files):
        """Records of calls that mod_json_cdr could not give to Odoo."""
        for path in files:
            try:
                status, _answer = self._request("/whatsapp/call/server/cdr", path.read_bytes())
            except urllib.error.HTTPError as error:
                status = error.code
            except (urllib.error.URLError, OSError) as error:
                _logger.warning("Record %s not sent: %s", path.name, error)
                return
            if status == 200:
                path.unlink(missing_ok=True)

    # === LOOP === #

    def run_once(self):
        voicemails, cdrs = self.spool_files()
        report = {
            "registrations": self.registrations(),
            "version": self.version(),
            "spool": len(voicemails) + len(cdrs),
        }
        try:
            data = self.fetch_config(report)
        except (urllib.error.URLError, OSError, ValueError, RuntimeError) as error:
            _logger.warning("Odoo does not answer (%s): the last copy of the agents stays", error)
            return False
        self.write_files(data)
        self.send_voicemails(voicemails)
        self.send_cdrs(cdrs)
        return True

    def run(self):
        for folder in ("voicemail", "cdr-errors"):
            (self.spool / folder).mkdir(parents=True, exist_ok=True)
        interval = float(self.conf["interval"])
        while True:
            started = time.monotonic()
            try:
                self.run_once()
            except Exception:  # noqa: BLE001 - the service never stops on an error
                _logger.exception("Unexpected error")
            time.sleep(max(1.0, interval - (time.monotonic() - started)))


def multipart(fields, path):
    """Body multipart/form-data with the fields and the file."""
    boundary = uuid.uuid4().hex
    parts = []
    for key, value in fields.items():
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode()
        )
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\n"
        "Content-Type: audio/wav\r\n\r\n".encode()
    )
    parts.append(path.read_bytes())
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def load_conf(path):
    parser = configparser.ConfigParser()
    if not parser.read(path):
        sys.exit(f"Configuration missing: {path}")
    conf = dict(DEFAULTS)
    conf.update(parser["ocd"] if parser.has_section("ocd") else {})
    for key in ("odoo_url", "token"):
        if not conf.get(key):
            sys.exit(f"{key} missing in {path}")
    return conf


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--conf", default="/etc/ocd-call-sync.conf")
    parser.add_argument("--once", action="store_true", help="One run, then stop.")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sync = Sync(load_conf(args.conf))
    if args.once:
        return 0 if sync.run_once() else 1
    sync.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
