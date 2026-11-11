import hmac
import json
import logging

from werkzeug.exceptions import BadRequest, Forbidden

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WhatsAppWebhook(http.Controller):

    @http.route("/whatsapp/webhook", type="http", auth="public", methods=["GET", "POST"],
                csrf=False, save_session=False)
    def whatsapp_webhook(self, **kwargs):
        """Webhook of the Meta app: verification (GET), then notifications (POST).

        The calls are accepted only when signed with the app secret of the WhatsApp
        Business account they are about (X-Hub-Signature-256 header). They are stored and
        acknowledged at once, then processed in the background (see whatsapp.webhook.event):
        Meta expects a quick answer, and sends the notification again otherwise.
        """
        Account = request.env["whatsapp.account"].sudo()
        if request.httprequest.method == "GET":
            token = kwargs.get("hub.verify_token") or ""
            if kwargs.get("hub.mode") == "subscribe" and token and any(
                hmac.compare_digest(token, account.verify_token or "")
                for account in Account.search([])
            ):
                return request.make_response(kwargs.get("hub.challenge", ""))
            raise Forbidden()

        payload = request.httprequest.get_data()
        signature = request.httprequest.headers.get("X-Hub-Signature-256", "")
        try:
            data = json.loads(payload)
        except ValueError as error:
            raise BadRequest() from error
        if data.get("object") != "whatsapp_business_account":
            raise BadRequest()
        entries = []
        for entry in data.get("entry", []):
            # several numbers (accounts in Odoo) can belong to the same WhatsApp Business account
            accounts = Account.search([("waba_id", "=", entry.get("id"))])
            if not any(account._check_signature(payload, signature) for account in accounts):
                _logger.warning("WhatsApp: webhook call refused (account %s).", entry.get("id"))
                raise Forbidden()
            entries.append((accounts, entry))
        Event = request.env["whatsapp.webhook.event"].sudo()
        for accounts, entry in entries:
            Event._create_from_entry(accounts, entry)
        return request.make_response("OK")
