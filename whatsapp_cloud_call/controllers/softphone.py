from odoo import fields, http
from odoo.http import request


class WhatsAppSoftphone(http.Controller):
    """The phone of the top bar of the agents."""

    @http.route("/whatsapp/call/softphone/config", type="jsonrpc", auth="user")
    def softphone_config(self):
        return request.env.user._whatsapp_call_softphone()

    @http.route("/whatsapp/call/softphone/available", type="jsonrpc", auth="user")
    def softphone_available(self, available):
        user = request.env.user
        if user._whatsapp_call_softphone() is None:
            return None
        user.sudo().whatsapp_call_available = bool(available)
        return user._whatsapp_call_softphone()

    def _get_call(self, call_id):
        user = request.env.user
        call = request.env["whatsapp.call"].sudo().browse(int(call_id or 0)).exists()
        if not call or user not in call.account_id._get_agents():
            return request.env["whatsapp.call"]
        return call

    @http.route("/whatsapp/call/softphone/info", type="jsonrpc", auth="user")
    def softphone_info(self, call_id):
        call = self._get_call(call_id)
        if not call:
            return None
        return {
            "id": call.id,
            "name": call._call_customer_label(),
            "number": f"+{call.number}" if call.number else "",
            "channel_id": call.channel_id.id or False,
            "account": call.account_id.name,
            "previous_calls": request.env["whatsapp.call"].sudo().search_count([
                ("channel_id", "=", call.channel_id.id), ("id", "!=", call.id),
            ]) if call.channel_id else 0,
        }

    @http.route("/whatsapp/call/softphone/trace", type="jsonrpc", auth="user")
    def softphone_trace(self, call_id, trace):
        """What the phone did when the agent answered (see whatsapp.call phone_trace)."""
        call = self._get_call(call_id)
        if call:
            call._call_add_phone_trace(request.env.user, trace)
        return True

    @http.route("/whatsapp/call/softphone/dial_failed", type="jsonrpc", auth="user")
    def softphone_dial_failed(self, call_id, reason=""):
        """The phone could not place a call of the company (not connected, microphone...)."""
        call = self._get_call(call_id)
        if call and call.direction == "outbound" and call.state == "ringing" and not call.server_seen:
            call.sudo().write({
                "state": "failed", "end_date": fields.Datetime.now(), "ended_by": "agent",
                "end_cause": str(reason or "PHONE")[:64],
            })
        return True

    @http.route("/whatsapp/call/softphone/declined", type="jsonrpc", auth="user")
    def softphone_declined(self, call_id):
        call = self._get_call(call_id)
        if call:
            call.declined_user_ids = [(4, request.env.user.id)]
        return True
