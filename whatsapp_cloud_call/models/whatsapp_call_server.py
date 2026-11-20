from odoo import api, fields, models


class WhatsappCallServer(models.Model):
    """The state of the call server, as it reports every 30 seconds. A record of its own (not
    a configuration parameter, whose writes empty the caches of all the workers)."""

    _name = "whatsapp.call.server"
    _description = "WhatsApp Call Server"

    last_seen = fields.Datetime(string="Last Report", readonly=True)
    version = fields.Char(readonly=True)
    registrations = fields.Text(string="Connected Agents", readonly=True, help="Logins, one per line.")
    registration_count = fields.Integer(string="Number of Connected Agents", readonly=True)
    spool = fields.Integer(
        string="Files Waiting", readonly=True,
        help="Messages and records of calls kept on the call server until Odoo takes them.",
    )
    silence_alerted = fields.Boolean(readonly=True)

    @api.model
    def _get(self):
        """The record of the call server (one only)."""
        server = self.sudo().search([], limit=1)
        return server or self.sudo().create({})

    def _report(self, report):
        """Note what the call server reports."""
        self.ensure_one()
        registrations = [str(login)[:64] for login in (report.get("registrations") or [])][:200]
        spool = report.get("spool")
        self.write({
            "last_seen": fields.Datetime.now(),
            "version": str(report.get("version") or "")[:64],
            "registrations": "\n".join(registrations),
            "registration_count": len(registrations),
            "spool": int(spool) if str(spool or "0").isdigit() else 0,
        })
