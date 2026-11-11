import json
import logging
from datetime import timedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3


class WhatsappWebhookEvent(models.Model):
    """A notification received from Meta, stored as soon as it arrives and processed in the
    background: Meta gets its answer right away, and nothing is lost when the processing
    fails (it is tried again, and kept for the analysis)."""

    _name = "whatsapp.webhook.event"
    _description = "WhatsApp Webhook Event"
    _order = "id"

    account_id = fields.Many2one(
        comodel_name="whatsapp.account", required=True, index=True, ondelete="cascade"
    )
    field = fields.Char(required=True, help="Field of the WhatsApp webhook: messages...")
    payload = fields.Text(required=True, help="Value of the change, as sent by Meta (JSON).")
    state = fields.Selection(
        selection=[("pending", "To process"), ("done", "Processed"), ("failed", "Failed")],
        default="pending",
        required=True,
        index=True,
    )
    attempts = fields.Integer(readonly=True)
    error = fields.Text(readonly=True)

    @api.model
    def _create_from_entry(self, accounts, entry):
        """Store the changes of an entry of the webhook (a WhatsApp Business account); each
        change goes to the account of its number. Return the events."""
        vals_list = []
        for change in entry.get("changes", []):
            value = change.get("value") or {}
            number_id = (value.get("metadata") or {}).get("phone_number_id")
            account = accounts.filtered(lambda a: a.phone_number_id == number_id)[:1]
            if number_id and not account:
                _logger.warning(
                    "WhatsApp: notification for the number %s, configured in no account.", number_id
                )
            vals_list.append({
                "account_id": (account or accounts[:1]).id,
                "field": change.get("field") or "unknown",
                "payload": json.dumps(value),
            })
        events = self.sudo().create(vals_list)
        if events:
            self.env.ref("whatsapp_cloud.ir_cron_process_webhook_events").sudo()._trigger()
        return events

    @api.model
    def _cron_process(self):
        self._process_pending(commit=True)

    @api.model
    def _process_pending(self, batch_size=200, commit=False):
        """Process the received events, oldest first (committing after each one in the
        scheduled action)."""
        events = self.search([("state", "=", "pending")], order="id", limit=batch_size)
        if commit:
            self.env["ir.cron"]._commit_progress(remaining=len(events))
        for event in events:
            event._process()
            if commit and not self.env["ir.cron"]._commit_progress(1):
                break
        if commit and self.search_count([("state", "=", "pending")], limit=1):
            self.env.ref("whatsapp_cloud.ir_cron_process_webhook_events")._trigger()

    def _process(self):
        """Process the event; an error is kept on the event, and tried again later."""
        self.ensure_one()
        if self.state != "pending":
            return
        try:
            with self.env.cr.savepoint():
                # the notices for the team in the language of the team
                lang = self.account_id._get_team_lang() if self.account_id else self.env.lang
                self.with_context(lang=lang)._dispatch(json.loads(self.payload))
        except Exception as error:  # noqa: BLE001 - kept on the event, never lost
            _logger.exception("WhatsApp: event %s (%s) not processed", self.id, self.field)
            attempts = self.attempts + 1
            self.write({
                "attempts": attempts,
                "error": str(error),
                "state": "failed" if attempts >= MAX_ATTEMPTS else "pending",
            })
            return
        self.write({"state": "done", "error": False})

    def _dispatch(self, value):
        """Process the value of the change according to its field."""
        account = self.account_id
        if self.field == "messages":
            metadata = value.get("metadata") or {}
            if metadata.get("phone_number_id") not in (None, account.phone_number_id):
                return
            Message = self.env["whatsapp.message"]
            for status in value.get("statuses", []):
                Message._process_status(account, status)
            for message in value.get("messages", []):
                Message._process_incoming(account, message, value.get("contacts", []))
            for error in value.get("errors", []):
                _logger.warning("WhatsApp: error from Meta for account %s: %s", account.id, error)
        elif self.field in (
            "message_template_status_update",
            "message_template_quality_update",
            "template_category_update",
        ):
            self.env["whatsapp.template"]._process_webhook(account, self.field, value)
        elif self.field in ("phone_number_quality_update", "phone_number_name_update"):
            account._check_health()
            account.message_post(body=self._describe(value), message_type="notification")
        elif self.field in ("account_update", "account_alerts", "business_capability_update"):
            account.message_post(body=self._describe(value), message_type="notification")
            if self.field in ("account_update", "account_alerts"):
                account._alert_managers(
                    _("WhatsApp account %(name)s: %(details)s",
                      name=account.name, details=self._describe(value))
                )

    def _describe(self, value):
        """Readable text of a notification of Meta about the account."""
        parts = [
            f"{key}: {val}" for key, val in value.items()
            if isinstance(val, (str, int, float)) and val not in ("", None)
        ]
        return _("Meta (%(field)s): %(details)s", field=self.field, details=", ".join(parts))

    @api.autovacuum
    def _gc_events(self, days=30):
        """Delete the processed events after a month (the failed ones after three)."""
        now = fields.Datetime.now()
        self.search([
            "|",
            "&", ("state", "=", "done"), ("create_date", "<", now - timedelta(days=days)),
            "&", ("state", "=", "failed"), ("create_date", "<", now - timedelta(days=days * 3)),
        ]).unlink()

    def action_retry(self):
        self.filtered(lambda event: event.state == "failed").write(
            {"state": "pending", "attempts": 0}
        )
        self.env.ref("whatsapp_cloud.ir_cron_process_webhook_events")._trigger()
