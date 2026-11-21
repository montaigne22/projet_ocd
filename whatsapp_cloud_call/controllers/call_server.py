import base64
import hmac
import json
import logging
from urllib.parse import parse_qs

from werkzeug.exceptions import BadRequest, Forbidden

from odoo import SUPERUSER_ID, http
from odoo.http import request

from odoo.addons.whatsapp_cloud_call import const

_logger = logging.getLogger(__name__)


def _clean(value, size=128):
    """A value of the call server: one line, limited."""
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:size]


class WhatsAppCallServer(http.Controller):
    """What the call server (FreeSWITCH) asks Odoo, with the key of Settings > WhatsApp >
    Calls: the agents and their passwords (every 30 seconds), who rings for a call, the events
    of the calls, the messages left, the records of the calls."""

    def _check_token(self):
        token = request.env["ir.config_parameter"].sudo().get_str(const.PARAM_TOKEN)
        header = request.httprequest.headers.get("Authorization", "")
        given = ""
        if header.startswith("Bearer "):
            given = header[7:].strip()
        elif header.startswith("Basic "):
            try:
                given = base64.b64decode(header[6:].strip()).decode().split(":", 1)[-1]
            except ValueError:
                given = ""
        if not token or not given or not hmac.compare_digest(token, given):
            _logger.warning("WhatsApp calls: call server request refused (%s).",
                            request.httprequest.remote_addr)
            raise Forbidden()

    def _calls(self):
        """The calls as OdooBot: what the call server notes in the conversations is signed
        by it (as the notifications of Meta)."""
        return request.env(user=SUPERUSER_ID, su=True)["whatsapp.call"]

    def _values(self):
        return {key: _clean(value) for key, value in request.httprequest.form.items()}

    @http.route("/whatsapp/call/server/config", type="http", auth="public", methods=["POST"],
                csrf=False, save_session=False)
    def config(self, **kwargs):
        """The call server reports (every 30 seconds) and gets the agents, their passwords and
        the numbers with calls."""
        self._check_token()
        try:
            report = json.loads(request.httprequest.get_data() or b"{}")
        except ValueError as error:
            raise BadRequest() from error
        env = request.env(user=SUPERUSER_ID, su=True)
        params = env["ir.config_parameter"]
        env["whatsapp.call.server"]._get()._report({
            "registrations": [_clean(r, 64) for r in (report.get("registrations") or [])],
            "version": _clean(report.get("version"), 64),
            "spool": report.get("spool"),
        })
        accounts = env["whatsapp.account"].search([("call_enabled", "=", True)])
        agents = env["whatsapp.account"]._call_get_agents()
        data = {
            "domain": (params.get_str(const.PARAM_HOST) or "").strip(),
            "trunks": [
                {
                    "phone_number_id": account.phone_number_id,
                    "number": account._call_business_number(),
                    "password": account.call_sip_password or "",
                    "max_wait": max(account.call_max_wait, 30),
                    "voicemail": account.call_voicemail,
                }
                for account in accounts
            ],
            "agents": [
                {
                    "login": f"{const.AGENT_PREFIX}{user.id}",
                    "password": user._whatsapp_call_password(),
                    "name": user.name,
                    "available": user.whatsapp_call_available,
                }
                for user in sorted(agents, key=lambda u: u.id)
            ],
        }
        return request.make_json_response(data)

    @http.route("/whatsapp/call/server/route", type="http", auth="public", methods=["POST"],
                csrf=False, save_session=False)
    def route(self, **kwargs):
        """Who rings for a call; answered as lines "key=value" (read by the script of the
        call server, without a JSON library)."""
        self._check_token()
        route = self._calls()._server_route(self._values())
        lines = []
        for key, value in route.items():
            if isinstance(value, list):
                value = ",".join(value)
            lines.append(f"{key}={_clean(value, 512)}")
        return request.make_response("\n".join(lines) + "\n", headers=[("Content-Type", "text/plain")])

    @http.route("/whatsapp/call/server/event", type="http", auth="public", methods=["POST"],
                csrf=False, save_session=False)
    def event(self, **kwargs):
        self._check_token()
        call = self._calls()._server_event(self._values())
        return request.make_response(f"call={call.id if call else ''}\n",
                                     headers=[("Content-Type", "text/plain")])

    @http.route("/whatsapp/call/server/voicemail", type="http", auth="public", methods=["POST"],
                csrf=False, save_session=False)
    def voicemail(self, **kwargs):
        self._check_token()
        upload = request.httprequest.files.get("file")
        if not upload:
            raise BadRequest()
        content = upload.read(const.MAX_VOICEMAIL_SIZE + 1)
        if len(content) > const.MAX_VOICEMAIL_SIZE:
            raise BadRequest()
        call = self._calls()._server_voicemail(
            self._values(), content, upload.mimetype or "audio/wav"
        )
        if not call:
            # nothing to attach it to: keep it on the call server for later
            raise BadRequest()
        return request.make_response("OK\n", headers=[("Content-Type", "text/plain")])

    @http.route("/whatsapp/call/server/cdr", type="http", auth="public", methods=["POST"],
                csrf=False, save_session=False)
    def cdr(self, **kwargs):
        """Record of a call (mod_json_cdr), raw JSON or the form field "cdr"; an answer other
        than 200 makes the call server send it again later."""
        self._check_token()
        raw = request.httprequest.get_data(as_text=True) or ""
        try:
            if raw.lstrip().startswith("{"):
                data = json.loads(raw)
            else:
                data = json.loads((parse_qs(raw).get("cdr") or [request.httprequest.form.get("cdr") or "{}"])[0])
        except ValueError as error:
            raise BadRequest() from error
        self._calls()._server_cdr(data)
        return request.make_response("OK\n", headers=[("Content-Type", "text/plain")])
