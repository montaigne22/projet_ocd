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

It talks to FreeSWITCH through its event socket (127.0.0.1:8021): no FreeSWITCH program is
needed next to it (its own container in Docker). Python 3 only (no library to install).
Configuration: /etc/ocd-call-sync.conf (see ocd-call-sync.conf.example), or the environment
(OCD_ODOO_URL, OCD_TOKEN, OCD_ESL_PASSWORD...: Docker). Run by systemd (ocd-call-sync.service)
or Docker (docker/docker-compose.yml).
"""

import argparse
import configparser
import hashlib
import json
import logging
import os
import re
import shutil
import socket
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
    "esl_host": "127.0.0.1",
    "esl_port": "8021",
    "esl_password": "",
    "directory_dir": "/etc/freeswitch/directory/ocd",
    "state_dir": "/var/lib/freeswitch/ocd",
    "spool_dir": "/var/spool/ocd-calls",
    "sounds_dir": "/usr/share/freeswitch/sounds/ocd",
    "hold_music": "local_stream://moh",
    "agents_profile": "ocd_agents",
}


# Settings that the environment may give (Docker), over the configuration file.
ENVIRONMENT = {
    "OCD_ODOO_URL": "odoo_url",
    "OCD_TOKEN": "token",
    "OCD_ESL_PASSWORD": "esl_password",
    "OCD_ESL_PORT": "esl_port",
    "OCD_SYNC_INTERVAL": "interval",
}
# Written after each exchange with Odoo; its age tells whether the service works (--health).
HEALTH_FILE = "sync_ok"
# The messages of the calls given in Odoo, per number: <state>/sounds/<phone number ID>/...; the
# hold stream of each number (music and voices) in <state>/local_stream_ocd.xml (read by
# local_stream.conf.xml); the settings of the hold music of this server (folder sounds/) written
# by the entrypoint in hold_defaults.json.
SOUND_ROLES = ("accueil", "enregistrement", "reconnexion", "messagerie", "indisponible")
SOUND_LISTS = {"voix": "voix", "musique": "attente"}
STREAMS_FILE = "local_stream_ocd.xml"
HOLD_DEFAULTS_FILE = "hold_defaults.json"
HOLD_DEFAULTS = {"music_dir": "/usr/share/freeswitch/sounds/music/16000", "shuffle": True, "voices": [], "every": 30}
# A recording is sent once its file has not changed for this long (the call ended); under this
# size (half a second at 16 kHz), nothing was said: dropped.
RECORDING_QUIET = 30
RECORDING_MIN_BYTES = 16000
HEALTH_MAX_AGE = 180


class EventSocketError(Exception):
    pass


class EventSocket:
    """The event socket of FreeSWITCH (inbound): one connection per command, the API answer."""

    def __init__(self, host, port, password, timeout=30):
        self.host, self.port, self.password, self.timeout = host, int(port), password, timeout

    @staticmethod
    def _read_message(reader):
        headers = {}
        while True:
            line = reader.readline()
            if not line:
                raise EventSocketError("connection closed by FreeSWITCH")
            line = line.decode("utf-8", "replace").rstrip("\r\n")
            if not line:
                if headers:
                    break
                continue
            key, _sep, value = line.partition(":")
            headers[key.strip().lower()] = value.strip()
        body = b""
        length = int(headers.get("content-length") or 0)
        while len(body) < length:
            chunk = reader.read(length - len(body))
            if not chunk:
                raise EventSocketError("answer cut")
            body += chunk
        return headers, body.decode("utf-8", "replace")

    def api(self, command):
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            reader = sock.makefile("rb")
            headers, _body = self._read_message(reader)
            if headers.get("content-type") != "auth/request":
                raise EventSocketError("not the event socket of FreeSWITCH")
            sock.sendall(f"auth {self.password}\n\n".encode())
            headers, _body = self._read_message(reader)
            if not headers.get("reply-text", "").startswith("+OK"):
                raise EventSocketError("password of the event socket refused")
            sock.sendall(f"api {command}\n\n".encode())
            headers, body = self._read_message(reader)
            try:
                sock.sendall(b"exit\n\n")
            except OSError:
                pass
            return body


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


class SoundError(Exception):
    """A message of the calls the call server cannot use (told to Odoo)."""


def sound_format(content):
    """"mp3", "wav" or None, from the first bytes of the file (as Odoo checks it)."""
    head = bytes(content[:12])
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if head[:3] == b"ID3" or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0):
        return "mp3"
    return None


def sound_path(entry):
    """Where a message given by Odoo goes in the folder of its number (None: unknown kind)."""
    kind = str(entry.get("kind") or "")
    sound_id = "".join(ch for ch in str(entry.get("id") or "") if ch.isdigit())
    if not sound_id:
        return None
    if kind in SOUND_ROLES:
        return f"{kind}.wav"
    if kind in SOUND_LISTS:
        sequence = max(0, min(9999, int(entry.get("sequence") or 0)))
        return f"{SOUND_LISTS[kind]}/{sequence:04d}-{sound_id}.wav"
    return None


def stream_name(phone_number_id):
    return "ocd_" + "".join(ch for ch in str(phone_number_id) if ch.isalnum())


def hold_streams_xml(streams):
    """The hold streams of the numbers (local_stream): their music, and their voices over it."""
    lines = ["<include>"]
    for name, stream in sorted(streams.items()):
        lines += [
            f"  <directory name={quoteattr(name)} path={quoteattr(stream['path'])}>",
            '    <param name="rate" value="16000"/>',
            f'    <param name="shuffle" value="{"true" if stream["shuffle"] else "false"}"/>',
            '    <param name="channels" value="1"/>',
            '    <param name="interval" value="20"/>',
            '    <param name="timer-name" value="soft"/>',
        ]
        if stream["voices"]:
            lines += [
                f'    <param name="chime-list" value={quoteattr(",".join(stream["voices"]))}/>',
                f'    <param name="chime-freq" value="{int(stream["every"])}"/>',
                '    <param name="chime-max" value="60000"/>',
            ]
        lines.append("  </directory>")
    lines.append("</include>")
    return "\n".join(lines) + "\n"


def convert_sound(content, target):
    """The message in WAV for FreeSWITCH: mono, 16 kHz, 16 bits, its loudness evened (sox)."""
    kind = sound_format(content)
    if not kind:
        raise SoundError("not an MP3 or a WAV")
    sox = shutil.which("sox")
    if not sox:
        raise SoundError("sox is missing on the call server (rebuild its images)")
    target.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(dir=target.parent, prefix=".ocd-"))
    try:
        source, output = work / f"in.{kind}", work / "out.wav"
        source.write_bytes(content)
        result = subprocess.run(
            [sox, "-q", str(source), "-r", "16000", "-c", "1", "-b", "16", str(output), "norm", "-3"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode or not output.exists() or output.stat().st_size <= 44:
            reason = (result.stderr or "").strip().splitlines()[-1:] or ["no sound in it"]
            raise SoundError(f"could not read it: {reason[0][:150]}")
        os.chmod(output, 0o644)
        os.replace(output, target)
    except subprocess.TimeoutExpired as error:
        raise SoundError("too long to convert") from error
    finally:
        shutil.rmtree(work, ignore_errors=True)


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


def gateways_meta(trunks):
    """Gateways to Meta for the calls of the company (meta_<phone number ID>): signed with the
    business number without "+" and the SIP password of Meta, From +<number>@<the call server>
    (Meta checks both); TLS. The $${...} are variables of FreeSWITCH (vars_ocd.xml)."""
    lines = ["<include>"]
    for trunk in trunks:
        pnid = "".join(ch for ch in str(trunk.get("phone_number_id") or "") if ch.isalnum())
        number = "".join(ch for ch in str(trunk.get("number") or "") if ch.isdigit())
        password = str(trunk.get("password") or "")
        if not pnid or not number or not password:
            continue
        lines += [
            f"  <gateway name={quoteattr('meta_' + pnid)}>",
            '    <param name="proxy" value="$${ocd_meta_sip}"/>',
            '    <param name="realm" value="wa.meta.vc"/>',
            f'    <param name="username" value={quoteattr(number)}/>',
            f'    <param name="password" value={quoteattr(password)}/>',
            f'    <param name="from-user" value={quoteattr("+" + number)}/>',
            '    <param name="from-domain" value="$${ocd_sip_domain}"/>',
            '    <param name="register" value="false"/>',
            '    <param name="register-transport" value="tls"/>',
            '    <param name="caller-id-in-from" value="false"/>',
            "  </gateway>",
        ]
    lines.append("</include>")
    return "\n".join(lines) + "\n"


def gateway_names(content):
    return re.findall(r'<gateway name="([^"]+)"', content)


def settings_lua(data, conf, holds=None):
    """Settings read by the scripts of the queue (holds: the hold stream running of each number)."""
    holds = holds or {}
    settings = {
        "odoo_url": conf["odoo_url"].rstrip("/"),
        "headers_file": str(Path(conf["state_dir"]) / "odoo_headers"),
        "domain": data.get("domain") or "",
        "spool": conf["spool_dir"],
        "sounds": conf["sounds_dir"],
        "sounds_odoo": str(Path(conf["state_dir"]) / "sounds"),
        "hold_music": conf["hold_music"],
        "agents": [a["login"] for a in data.get("agents") or [] if valid_login(a.get("login"))],
        "trunks": {
            str(t.get("phone_number_id")): {
                "number": str(t.get("number") or ""),
                "max_wait": int(t.get("max_wait") or 180),
                "voicemail": bool(t.get("voicemail", True)),
                "record": bool(t.get("record", False)),
                **({"hold": holds[str(t.get("phone_number_id"))]} if str(t.get("phone_number_id")) in holds else {}),
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
        self.esl = EventSocket(conf["esl_host"], conf["esl_port"], conf["esl_password"])
        # a reload that FreeSWITCH did not take (down, wrong password) is asked again; once at
        # the start of the service, whatever happened before
        self.reload_pending = True
        self.cdr_reload_pending = False
        # at start, the gateways written before are checked (rescan adds the missing ones and
        # cuts no call); "reload" when they changed (taken again)
        self.gateways_pending = "rescan"
        # the messages of the calls: what to tell Odoo (sent with the next report), the hold
        # streams applied (their settings), a change FreeSWITCH did not take yet
        self.sound_report = {}
        self.streams_applied = {}
        self.streams_pending = True

    # === ODOO === #

    def _request(self, path, data=None, content_type="application/json", timeout=None):
        request = urllib.request.Request(
            self.conf["odoo_url"].rstrip("/") + path,
            data=data,
            headers={
                "Authorization": f"Bearer {self.conf['token']}",
                "Content-Type": content_type,
                # not the one of Python (Python-urllib): refused by Cloudflare (error 1010)
                "User-Agent": "ocd-call-sync",
            },
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
        """A command of FreeSWITCH (event socket); "" when FreeSWITCH does not answer."""
        try:
            return self.esl.api(command)
        except (OSError, EventSocketError) as error:
            _logger.warning("FreeSWITCH, %s: %s", command, error)
            return ""

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

    def recording_files(self):
        return sorted((self.spool / "recordings").glob("*.wav"))

    def write_files(self, data, holds=None):
        conf = self.conf
        directory = Path(conf["directory_dir"])
        changed = write_if_changed(directory / "agents.xml", directory_agents(data.get("agents") or []))
        changed |= write_if_changed(directory / "meta.xml", directory_meta(data.get("trunks") or []))
        state = Path(conf["state_dir"])
        write_if_changed(state / "settings.lua", settings_lua(data, conf, holds), mode=0o640)
        write_if_changed(state / "odoo_headers", f"Authorization: Bearer {conf['token']}\n", mode=0o640)
        vars_changed = write_if_changed(state / "vars_secret.xml", vars_secret(conf), mode=0o640)
        gateways = gateways_meta(data.get("trunks") or [])
        gateways_changed = write_if_changed(state / "gateways_meta.xml", gateways, mode=0o640)
        if changed or vars_changed or gateways_changed or self.reload_pending:
            self.reload_pending = "+OK" not in self.fs("reloadxml")
            if not self.reload_pending:
                _logger.info("FreeSWITCH: users reloaded (%s agents)", len(data.get("agents") or []))
        if gateways_changed:
            # a number or its SIP password changed: the gateways to Meta are taken again (until
            # FreeSWITCH answers)
            self.gateways_pending = "reload"
        if self.gateways_pending and not self.reload_pending:
            if self.gateways_pending == "reload":
                for name in gateway_names(gateways):
                    self.fs(f"sofia profile ocd_whatsapp killgw {name}")
            if "+OK" in self.fs("sofia profile ocd_whatsapp rescan"):
                self.gateways_pending = False
                _logger.info("FreeSWITCH: gateways to Meta: %s", ", ".join(gateway_names(gateways)) or "none")
        if vars_changed or self.cdr_reload_pending:
            # the address of Odoo or the key changed: the records of the calls follow
            self.cdr_reload_pending = "+OK" not in self.fs("reload mod_json_cdr")
        return changed

    # === MESSAGES OF THE CALLS === #

    def sync_sounds(self, data):
        """The messages of each number given in Odoo: fetched when they changed, converted, their
        hold stream applied without restarting. Return {phone number ID: hold stream running}."""
        root = Path(self.conf["state_dir"]) / "sounds"
        defaults = self.hold_defaults()
        report, streams, numbers = {}, {}, {}
        for trunk in data.get("trunks") or []:
            pnid = "".join(ch for ch in str(trunk.get("phone_number_id") or "") if ch.isalnum())
            if not pnid:
                continue
            folder = root / pnid
            present = self.sync_number_sounds(folder, trunk.get("sounds") or [], report)
            voices = sorted(str(folder / rel) for rel in present if rel.startswith("voix/"))
            music = any(rel.startswith("attente/") for rel in present)
            every = int(trunk.get("hold_voice_every") or defaults["every"])
            streams[stream_name(pnid)] = {
                "path": str(folder / "attente") if music else defaults["music_dir"],
                "shuffle": False if music else bool(defaults["shuffle"]),
                "voices": voices or list(defaults["voices"]),
                "every": max(10, min(600, every)),
            }
            numbers[stream_name(pnid)] = pnid
        if root.exists():
            for child in root.iterdir():
                if child.is_dir() and stream_name(child.name) not in streams:
                    shutil.rmtree(child, ignore_errors=True)  # a number without calls any more
        self.sound_report = report
        running = self.apply_streams(streams)
        return {numbers[name]: f"local_stream://{name}" for name in streams if name in running}

    def sync_number_sounds(self, folder, entries, report):
        """The files of one number; return the paths (in its folder) of the messages ready."""
        manifest_path = folder / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            manifest = {}
        wanted = {}
        for entry in entries:
            rel = sound_path(entry)
            checksum = str(entry.get("checksum") or "")
            if not rel or not checksum:
                continue
            sound_id = str(entry.get("id"))
            wanted[rel] = sound_id
            target = folder / rel
            if manifest.get(rel) == checksum and target.exists():
                report[sound_id] = {"checksum": checksum, "state": "ok"}
                continue
            try:
                status, content = self._request("/whatsapp/call/server/sound",
                                                 f"id={sound_id}".encode(), "application/x-www-form-urlencoded",
                                                 timeout=120)
            except (urllib.error.URLError, OSError) as error:
                _logger.warning("Message %s not fetched: %s", rel, error)
                continue  # again at the next run
            if status != 200 or hashlib.sha1(content).hexdigest() != checksum:
                continue  # changed meanwhile in Odoo: the next run has its new file
            try:
                convert_sound(content, target)
            except SoundError as error:
                _logger.warning("Message %s of %s refused: %s", rel, folder.name, error)
                report[sound_id] = {"checksum": checksum, "state": "error", "message": str(error)}
                continue
            manifest[rel] = checksum
            report[sound_id] = {"checksum": checksum, "state": "ok"}
            _logger.info("Message %s of %s ready", rel, folder.name)
        if folder.exists():
            for path in folder.rglob("*.wav"):
                rel = path.relative_to(folder).as_posix()
                if rel not in wanted:
                    path.unlink(missing_ok=True)  # removed or replaced in Odoo
                    manifest.pop(rel, None)
        manifest = {rel: checksum for rel, checksum in manifest.items() if rel in wanted}
        if manifest or manifest_path.exists():
            write_if_changed(manifest_path, json.dumps(manifest, sort_keys=True), mode=0o644)
        return [rel for rel in wanted if rel in manifest and (folder / rel).exists()]

    def hold_defaults(self):
        """The hold music of this server (folder sounds/, read by the entrypoint), else the one of
        FreeSWITCH."""
        defaults = dict(HOLD_DEFAULTS)
        try:
            given = json.loads((Path(self.conf["state_dir"]) / HOLD_DEFAULTS_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return defaults
        if isinstance(given, dict):
            for key in defaults:
                if key in given:
                    defaults[key] = given[key]
        return defaults

    def running_streams(self):
        output = self.fs("local_stream show")
        return {line.split(",", 1)[0].strip() for line in output.splitlines() if "," in line}

    def apply_streams(self, streams):
        """The hold streams of the numbers, written and started or reloaded in FreeSWITCH (the
        customers waiting are not cut off); return the names of those running."""
        path = Path(self.conf["state_dir"]) / STREAMS_FILE
        changed = write_if_changed(path, hold_streams_xml(streams), mode=0o644)
        if changed or self.streams_pending:
            if "+OK" not in self.fs("reloadxml"):
                self.streams_pending = True
                return self.running_streams() & set(streams)
        running = self.running_streams()
        pending = False
        for name, stream in streams.items():
            digest = json.dumps(stream, sort_keys=True)
            if name in running and self.streams_applied.get(name) == digest:
                continue
            command = "reload" if name in running else "start"
            if "+OK" in self.fs(f"local_stream {command} {name}"):
                self.streams_applied[name] = digest
                _logger.info("FreeSWITCH: hold stream %s %s", name, "reloaded" if command == "reload" else "started")
            else:
                pending = True
        for name in running - set(streams):
            if name.startswith("ocd_"):
                self.fs(f"local_stream stop {name}")
                self.streams_applied.pop(name, None)
        self.streams_pending = pending
        return self.running_streams() & set(streams)

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

    def send_recordings(self, files):
        """The recordings of the calls ended (unchanged for RECORDING_QUIET seconds), in MP3 (lame;
        the WAV when it cannot convert), with the facts written by the script of the call."""
        for path in files:
            try:
                age = time.time() - path.stat().st_mtime
            except OSError:
                continue
            if age < RECORDING_QUIET:
                continue  # the call goes on, or its file was just closed
            facts_path = path.with_suffix(".txt")
            facts = {"uuid": path.stem}
            if facts_path.exists():
                for line in facts_path.read_text(encoding="utf-8").splitlines():
                    key, _sep, value = line.partition("=")
                    if key.strip():
                        facts[key.strip()] = value.strip()
            if path.stat().st_size < RECORDING_MIN_BYTES:
                # nothing said (an agent who answered and hung up at once)
                for leftover in (path, facts_path, path.with_suffix(".mp3")):
                    leftover.unlink(missing_ok=True)
                continue
            sent, content_type = self.recording_mp3(path), "audio/mpeg"
            if not sent:
                sent, content_type = path, "audio/wav"
            body, multipart_type = multipart(facts, sent, content_type)
            try:
                status, _answer = self._request("/whatsapp/call/server/recording", body, multipart_type, timeout=120)
            except urllib.error.HTTPError as error:
                status = error.code
            except (urllib.error.URLError, OSError) as error:
                _logger.warning("Recording %s not sent: %s", path.name, error)
                return
            if status == 200:
                for leftover in (path, facts_path, path.with_suffix(".mp3")):
                    leftover.unlink(missing_ok=True)
                _logger.info("Recording %s sent to Odoo", path.stem)
            elif age > 7 * 86400:
                # refused for a week (call unknown to Odoo): kept aside for the team
                path.rename(path.with_suffix(".refused.wav"))
                path.with_suffix(".mp3").unlink(missing_ok=True)

    def recording_mp3(self, path):
        """The MP3 of a recording (mono, 32 kbit/s: about 240 kB a minute), made once; None when
        lame is missing or fails."""
        mp3 = path.with_suffix(".mp3")
        if mp3.exists() and mp3.stat().st_size and mp3.stat().st_mtime >= path.stat().st_mtime:
            return mp3
        lame = shutil.which("lame")
        if not lame:
            return None
        try:
            subprocess.run([lame, "--quiet", "-m", "m", "-b", "32", str(path), str(mp3)],
                           check=True, timeout=600, capture_output=True)
        except (subprocess.SubprocessError, OSError) as error:
            _logger.warning("Recording %s not converted to MP3 (%s): sent in WAV", path.name, error)
            mp3.unlink(missing_ok=True)
            return None
        return mp3

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
        recordings = self.recording_files()
        report = {
            "registrations": self.registrations(),
            "version": self.version(),
            "spool": len(voicemails) + len(cdrs) + len(recordings),
            "sounds": self.sound_report,
        }
        try:
            data = self.fetch_config(report)
        except (urllib.error.URLError, OSError, ValueError, RuntimeError) as error:
            _logger.warning("Odoo does not answer (%s): the last copy of the agents stays", error)
            return False
        try:
            holds = self.sync_sounds(data)
        except Exception:  # noqa: BLE001 - the messages never stop the copy of the agents
            _logger.exception("Messages of the calls not applied")
            holds = {}
        self.write_files(data, holds)
        self.send_voicemails(voicemails)
        self.send_cdrs(cdrs)
        self.send_recordings(recordings)
        write_if_changed(Path(self.conf["state_dir"]) / HEALTH_FILE, f"{int(time.time())}\n", mode=0o644)
        return True

    def run(self):
        for folder in ("voicemail", "cdr-errors", "recordings"):
            try:
                (self.spool / folder).mkdir(parents=True, exist_ok=True)
            except OSError as error:
                # Docker: the folders are given to FreeSWITCH by its container, a moment later
                _logger.warning("Folder %s not ready yet: %s", folder, error)
        interval = float(self.conf["interval"])
        while True:
            started = time.monotonic()
            try:
                self.run_once()
            except Exception:  # noqa: BLE001 - the service never stops on an error
                _logger.exception("Unexpected error")
            time.sleep(max(1.0, interval - (time.monotonic() - started)))


def multipart(fields, path, content_type="audio/wav"):
    """Body multipart/form-data with the fields and the file."""
    boundary = uuid.uuid4().hex
    parts = []
    for key, value in fields.items():
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode()
        )
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\n"
        f"Content-Type: {content_type}\r\n\r\n".encode()
    )
    parts.append(path.read_bytes())
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def load_conf(path, environ=None):
    """The configuration file (when it exists), then the environment."""
    environ = os.environ if environ is None else environ
    parser = configparser.ConfigParser()
    parser.read(path)
    conf = dict(DEFAULTS)
    conf.update(parser["ocd"] if parser.has_section("ocd") else {})
    if conf.get("fs_password") and not conf.get("esl_password"):
        conf["esl_password"] = conf["fs_password"]  # name of the first versions
    for variable, key in ENVIRONMENT.items():
        if environ.get(variable):
            conf[key] = environ[variable]
    for key in ("odoo_url", "token", "esl_password"):
        if not conf.get(key):
            sys.exit(f"{key} missing: in {path} or in the environment ({', '.join(ENVIRONMENT)})")
    return conf


def healthy(conf):
    """Whether the service exchanged with Odoo in the last 3 minutes."""
    try:
        written = int((Path(conf["state_dir"]) / HEALTH_FILE).read_text().strip())
    except (OSError, ValueError):
        return False
    return time.time() - written < HEALTH_MAX_AGE


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--conf", default="/etc/ocd-call-sync.conf")
    parser.add_argument("--once", action="store_true", help="One run, then stop.")
    parser.add_argument("--health", action="store_true", help="Exit 0 when the service works.")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if args.health:
        conf = dict(DEFAULTS)
        conf.update({key: os.environ[var] for var, key in ENVIRONMENT.items() if os.environ.get(var)})
        return 0 if healthy(conf) else 1
    sync = Sync(load_conf(args.conf))
    if args.once:
        return 0 if sync.run_once() else 1
    sync.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
