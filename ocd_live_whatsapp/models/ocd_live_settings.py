from odoo import api, models

# Status of a template at Meta, from the least to the most worrying
TEMPLATE_STATUS = ["approved", "unknown", "pending", "paused", "rejected", "disabled"]


class OcdLiveSettings(models.AbstractModel):
    """WhatsApp on the settings page of OCD Live: the number, the consent, the automatic
    answers and the templates with their status at Meta."""

    _inherit = "ocd.live.settings"

    @api.model
    def _ocd_sections(self):
        return [*super()._ocd_sections(), self._ocd_section_whatsapp()]

    @api.model
    def _ocd_section_whatsapp(self):
        _ = self.env._
        item = self._ocd_item
        company = self.env.company
        accounts = self._ocd_whatsapp_accounts()
        account = accounts[:1]
        if account:
            number = account.display_phone_number or account.verified_name or account.name
            healthy = account.health_state in (False, "ok")
            number_text = _("%s. The messages arrive in the WhatsApp conversations of OCD Live.", number)
            note = _("Connected") if healthy else (account.health_message or _("To check"))
            tone = "green" if healthy else "red"
        else:
            number_text = _("Connected with the official API of Meta: the messages arrive in the conversations.")
            note, tone = _("Not connected: add the account of Meta (WhatsApp, Accounts)."), "red"
        flag = {"get": "_ocd_get_whatsapp_flag", "set": "_ocd_set_whatsapp_flag", "readonly": not accounts}
        return {
            "key": "whatsapp",
            "sequence": 50,
            "icon": "WA",
            "label": _("WhatsApp"),
            "title": _("WhatsApp"),
            "items": [
                item("info", "wa_number", _("WhatsApp Business number of OCD Live"), number_text,
                     note=note, note_tone=tone,
                     link={"label": _("WhatsApp accounts"), "action": "whatsapp_cloud.whatsapp_account_action"}),
                item("check", "wa_require_opt_in", _("Only to the contacts who agreed"),
                     _("As WhatsApp asks. The messages asked by the contact (code, link, ticket, alert) always go."),
                     warn_off=_("Messages then go to contacts who agreed to nothing: WhatsApp can block the number."),
                     args=["require_opt_in"], **flag),
                item("check", "whatsapp_conversations", _("Conversations with the team"),
                     company._fields["whatsapp_conversations"].help),
                item("check", "whatsapp_read_receipts", _("Blue ticks and « typing… »"),
                     company._fields["whatsapp_read_receipts"].help),
                item("check", "whatsapp_answer_reminders", _("Reminders of the messages waiting for an answer"),
                     company._fields["whatsapp_answer_reminders"].help),
                item("check", "wa_welcome_menu", _("Welcome menu"),
                     _("A contact who writes for the first time gets the menu with its buttons."),
                     args=["bot_enabled"], **flag),
                item("check", "wa_away_message", _("Away message"),
                     _("Outside of the opening hours, the contact is told when the team answers."),
                     args=["away_message_enabled"], **flag),
                item("info", "wa_stop", _("STOP and START"),
                     _("A contact who writes STOP gets no automatic message any more; START starts them again."),
                     note=_("Always respected."), note_tone="green"),
                item("templates", "wa_templates", _("Templates of the messages, approved by Meta"),
                     _("Out of the 24 hours after the last message of a contact, only these templates can go. They are sent to Meta from OCD Live."),
                     rows=self._ocd_template_rows(),
                     link={"label": _("Templates"), "action": "whatsapp_cloud.whatsapp_template_action"}),
            ],
        }

    @api.model
    def _ocd_whatsapp_accounts(self):
        return self.env["whatsapp.account"].sudo().search([("company_id", "=", self.env.company.id)])

    def _ocd_get_whatsapp_flag(self, fname):
        accounts = self._ocd_whatsapp_accounts()
        return all(accounts.mapped(fname)) if accounts else True

    def _ocd_set_whatsapp_flag(self, fname, value):
        self._ocd_whatsapp_accounts().filtered(lambda account: account[fname] != value).write({fname: value})

    @api.model
    def _ocd_template_rows(self):
        """One row per template of OCD Live and of the shop (all its languages): name at Meta,
        what it is for, the most worrying status of its versions."""
        _ = self.env._
        data = self.env["ir.model.data"].sudo().search([
            ("model", "=", "whatsapp.template"),
            "|", ("module", "=like", "ocd\\_%"), ("module", "=", "whatsapp_cloud_sale"),
        ])
        templates = self.env["whatsapp.template"].sudo().browse(data.mapped("res_id")).exists()
        labels = {
            "approved": (_("Approved"), "green"),
            "unknown": (_("Not synchronised"), "grey"),
            "pending": (_("Waiting for Meta"), "yellow"),
            "paused": (_("Paused by Meta"), "red"),
            "rejected": (_("Refused by Meta"), "red"),
            "disabled": (_("Disabled by Meta"), "red"),
        }
        rows = {}
        for template in templates.sorted(lambda t: (not t.template_name.startswith("ocd_"), t.template_name, t.id)):
            row = rows.setdefault(template.template_name, {"name": template.template_name, "use": template.name, "status": "approved"})
            if TEMPLATE_STATUS.index(template.status or "unknown") > TEMPLATE_STATUS.index(row["status"]):
                row["status"] = template.status or "unknown"
        return [
            {"name": row["name"], "use": row["use"], "status": labels[row["status"]][0], "tone": labels[row["status"]][1]}
            for row in rows.values()
        ]
