import base64
import json
import logging
import re
from functools import reduce
from urllib.parse import quote, urlsplit

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools.safe_eval import safe_eval, time

from odoo.addons.whatsapp_cloud import const
from odoo.addons.whatsapp_cloud.models.whatsapp_account import WhatsAppApiError

_logger = logging.getLogger(__name__)

PLACEHOLDER_RE = re.compile(r"{{\s*(\w+)\s*}}")
# Characters kept as they are in the end of the URL of a link button; the others (spaces,
# accents, ":", "|"...) are percent-encoded, as Meta asks.
URL_SAFE_CHARS = "/?=&%#-._~!$'()*+,;@"


class WhatsappTemplate(models.Model):
    _name = "whatsapp.template"
    _description = "WhatsApp Template"
    _order = "model_id, name, id"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    account_id = fields.Many2one(
        comodel_name="whatsapp.account",
        string="Account",
        ondelete="cascade",
        help="Account that sends the messages; the first account of the company if empty.",
    )
    company_id = fields.Many2one(related="account_id.company_id", store=True)
    template_name = fields.Char(
        string="Name at Meta",
        required=True,
        help="Name of the template approved by Meta (lowercase letters, digits and _).",
    )
    lang_code = fields.Char(
        string="Language", required=True, default="fr",
        help="Language code of the template at Meta: fr, en_US, en...",
    )
    category = fields.Selection(
        selection=[
            ("utility", "Utility"),
            ("marketing", "Marketing"),
            ("authentication", "Authentication"),
        ],
        default="utility",
    )
    code_expiration_minutes = fields.Integer(
        string="Code Valid For (Minutes)",
        default=10,
        help="Authentication templates: Meta writes the text itself in the language of the "
        "template (the code, then a security advice) and adds this time in the footer, with a "
        "button that copies the code.",
    )
    status = fields.Selection(
        selection=[
            ("unknown", "Not synchronised"),
            ("approved", "Approved"),
            ("pending", "Pending approval"),
            ("rejected", "Rejected"),
            ("paused", "Paused"),
            ("disabled", "Disabled"),
        ],
        default="unknown",
        readonly=True,
        copy=False,
        help="Status of the template at Meta, read by the synchronisation. The messages are "
        "sent only with the approved and not synchronised templates.",
    )
    wa_template_id = fields.Char(
        string="ID at Meta", readonly=True, copy=False, index="btree_not_null"
    )
    rejected_reason = fields.Char(string="Reason of Meta", readonly=True, copy=False)
    quality_score = fields.Selection(
        selection=[("GREEN", "High"), ("YELLOW", "Medium"), ("RED", "Low"), ("UNKNOWN", "Unknown")],
        string="Quality",
        readonly=True,
        copy=False,
        help="Quality of the template at Meta, from how the customers receive it: a template "
        "of low quality is paused, then disabled.",
    )
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Applies to",
        required=True,
        ondelete="cascade",
        default=lambda self: self.env["ir.model"]._get("res.partner"),
        domain=[("transient", "=", False)],
    )
    model = fields.Char(related="model_id.model", store=True, index=True)
    partner_field = fields.Char(
        string="Recipient",
        default="partner_id",
        help="Field of the document that gives the contact who receives the message, e.g. "
        "partner_id (customer of an order). Ignored on the contacts themselves.",
    )
    body = fields.Text(
        help="Text of the template at Meta, with its variables {{1}}, {{2}}... (filled by the "
        "synchronisation); used for the preview and the message log.",
    )
    parameter_format = fields.Selection(
        selection=[("positional", "Numbered: {{1}}"), ("named", "Named: {{name}}")],
        default="positional",
        required=True,
    )
    variable_ids = fields.One2many(
        comodel_name="whatsapp.template.variable",
        inverse_name="template_id",
        string="Variables",
        copy=True,
    )
    header_type = fields.Selection(
        selection=[("none", "None"), ("text", "Text"), ("document", "PDF document")],
        default="none",
        required=True,
    )
    header_text = fields.Char(
        string="Header",
        help="Text of the header at Meta (60 characters), with at most one variable {{1}}.",
    )
    header_value = fields.Char(
        string="Header Variable",
        help="Value of the variable of a text header, e.g. {{ object.name }}.",
    )
    header_sample = fields.Char(
        string="Header Example", help="Example of the header variable, for the review by Meta."
    )
    header_sample_file = fields.Binary(
        string="Sample Document",
        attachment=True,
        help="Sample PDF for the review by Meta; when empty, the document of the latest record "
        "is used.",
    )
    header_sample_filename = fields.Char()
    footer_text = fields.Char(string="Footer", help="Text under the message (60 characters).")
    button_ids = fields.One2many(
        comodel_name="whatsapp.template.button",
        inverse_name="template_id",
        string="Buttons",
        copy=True,
    )
    header_report_id = fields.Many2one(
        comodel_name="ir.actions.report",
        string="Document",
        domain="[('model', '=', model), ('report_type', '=', 'qweb-pdf')]",
        help="PDF of the document sent in the header of the message (quotation, invoice...).",
    )
    button_url_value = fields.Char(
        string="Link Button Variable",
        help="End of the URL of the link button of the template, when its URL ends with a "
        "variable, e.g. {{ object.get_portal_url() }} for a button "
        "https://shop.example.com/{{1}}.",
    )
    button_url_dynamic = fields.Boolean(
        string="Link Button with Variable",
        readonly=True,
        help="The template has, at Meta, a link button whose URL ends with a variable (read by "
        "the synchronisation): Odoo sends the end of the URL given in Link Button Variable.",
    )
    preview = fields.Text(compute="_compute_preview")

    _template_lang_account_uniq = models.Constraint(
        "unique(account_id, template_name, lang_code)",
        "This template already exists in this language for this account.",
    )

    @api.constrains("template_name")
    def _check_template_name(self):
        for template in self:
            if not re.fullmatch(r"[a-z0-9_]+", template.template_name or ""):
                raise ValidationError(_(
                    "The name at Meta can only contain lowercase letters, digits and underscores: "
                    "%s", template.template_name,
                ))

    @api.depends("body", "variable_ids.value", "variable_ids.param_name")
    def _compute_preview(self):
        for template in self:
            values = {
                variable._get_placeholder_key(): f"[{variable.value or '?'}]"
                for variable in template.variable_ids
            }
            template.preview = template._fill_body(values)

    # === META === #

    STATUS_BY_EVENT = {
        "APPROVED": "approved",
        "REINSTATED": "approved",
        "UNARCHIVED": "approved",
        "PENDING": "pending",
        "IN_APPEAL": "pending",
        "REJECTED": "rejected",
        "LIMIT_EXCEEDED": "rejected",
        "PAUSED": "paused",
        "DISABLED": "disabled",
        "LOCKED": "disabled",
        "ARCHIVED": "disabled",
        "DELETED": "disabled",
        "PENDING_DELETION": "disabled",
    }
    META_FIELDS = (
        "id,name,language,status,category,components,parameter_format,rejected_reason,"
        "quality_score"
    )

    @api.model
    def _normalize_lang(self, code):
        """Language code of Meta's API (en_US), also from the webhooks (en-US)."""
        return (code or "").replace("-", "_")

    @api.model
    def _find_from_meta(self, account, data):
        """The template of Odoo for a template of Meta: same ID, else same name and language
        for the account or provided by a module for any account (a template provided in
        "en" also matches the one created in "en_US" at Meta)."""
        AllTemplates = self.with_context(active_test=False)
        if data.get("id"):
            template = AllTemplates.search([("wa_template_id", "=", str(data["id"]))], limit=1)
            if template:
                return template
        lang = self._normalize_lang(data.get("language"))
        return AllTemplates.search([
            ("account_id", "in", [account.id, False]),
            ("template_name", "=", data["name"]),
            ("lang_code", "=", lang),
        ], order="account_id", limit=1) or AllTemplates.search([
            ("account_id", "=", False),
            ("template_name", "=", data["name"]),
            ("lang_code", "=", self._lang_base(lang)),
        ], limit=1)

    @api.model
    def _prepare_vals_from_meta(self, data):
        """Values of a template from its definition at Meta (``message_templates`` API)."""
        vals = {
            "status": (data.get("status") or "unknown").lower(),
            "category": (data.get("category") or "utility").lower(),
            "parameter_format": (data.get("parameter_format") or "positional").lower(),
            "template_name": data["name"],
            "lang_code": self._normalize_lang(data["language"]),
            "button_url_dynamic": False,
            "rejected_reason": (
                data.get("rejected_reason") if data.get("rejected_reason") not in (None, "NONE")
                else False
            ),
            "header_type": "none",
            "header_text": False,
            "footer_text": False,
        }
        if data.get("id"):
            vals["wa_template_id"] = str(data["id"])
        quality = data.get("quality_score")
        score = (quality.get("score") if isinstance(quality, dict) else quality) or ""
        if score.upper() in dict(self._fields["quality_score"].selection):
            vals["quality_score"] = score.upper()
        if vals["status"] not in dict(self._fields["status"].selection):
            vals["status"] = self.STATUS_BY_EVENT.get(vals["status"].upper(), "unknown")
        if vals["category"] not in dict(self._fields["category"].selection):
            vals["category"] = "utility"
        buttons = []
        for component in data.get("components", []):
            component_type = (component.get("type") or "").upper()
            if component_type == "BODY":
                vals["body"] = component.get("text")
            elif component_type == "HEADER":
                header_format = (component.get("format") or "").upper()
                if header_format == "DOCUMENT":
                    vals["header_type"] = "document"
                elif header_format == "TEXT":
                    vals["header_type"] = "text"
                    vals["header_text"] = component.get("text")
            elif component_type == "FOOTER":
                vals["footer_text"] = component.get("text")
                if component.get("code_expiration_minutes"):
                    vals["code_expiration_minutes"] = component["code_expiration_minutes"]
            elif component_type == "BUTTONS" and vals["category"] == "authentication":
                continue
            elif component_type == "BUTTONS":
                for sequence, button in enumerate(component.get("buttons", [])):
                    button_type = (button.get("type") or "").lower()
                    if button_type not in ("quick_reply", "url", "phone_number"):
                        button_type = "other"
                    example = button.get("example")
                    buttons.append({
                        "sequence": sequence,
                        "button_type": button_type,
                        "name": button.get("text") or button_type,
                        "url": button.get("url") or False,
                        "url_example": (example[0] if isinstance(example, list) and example
                                        else example if isinstance(example, str) else False),
                        "phone_number": button.get("phone_number") or False,
                    })
                vals["button_url_dynamic"] = any(
                    button["button_type"] == "url" and "{{" in (button["url"] or "")
                    for button in buttons
                )
        vals["button_ids"] = [Command.clear()] + [Command.create(b) for b in buttons]
        return vals

    def _refresh_from_meta(self, account):
        """Read the template again from Meta."""
        for template in self.filtered("wa_template_id"):
            try:
                data = account._api_request(
                    "GET", template.wa_template_id, params={"fields": self.META_FIELDS}
                )
            except WhatsAppApiError as error:
                _logger.info("WhatsApp: template %s not read again: %s", template.wa_template_id, error)
                continue
            vals = template._prepare_vals_from_meta(data)
            if template.account_id or template.get_external_id().get(template.id):
                vals.pop("template_name", None)
            template.write(vals)

    @api.model
    def _process_webhook(self, account, field, value):
        """Status, quality or category of a template changed at Meta."""
        data = {
            "id": value.get("message_template_id"),
            "name": value.get("message_template_name") or "",
            "language": value.get("message_template_language") or "",
        }
        templates = self._find_from_meta(account, data) if data["name"] or data["id"] else self
        if not templates:
            return
        if field == "message_template_status_update":
            event = (value.get("event") or "").upper()
            reason = value.get("reason")
            details = " ".join(filter(None, [
                reason if reason not in (None, "NONE") else "",
                (value.get("rejection_info") or {}).get("reason"),
                (value.get("rejection_info") or {}).get("recommendation"),
                (value.get("other_info") or {}).get("description"),
            ]))
            vals = {"rejected_reason": details or False}
            if status := self.STATUS_BY_EVENT.get(event):
                vals["status"] = status
            if data["id"]:
                vals["wa_template_id"] = str(data["id"])
            templates.write(vals)
            if event in ("REJECTED", "PAUSED", "DISABLED", "FLAGGED", "LIMIT_EXCEEDED", "LOCKED",
                         "ARCHIVED", "PENDING_DELETION", "DELETED"):
                account._alert_managers(_(
                    "WhatsApp template %(name)s (%(lang)s): %(event)s at Meta. %(details)s",
                    name=data["name"], lang=data["language"], event=event, details=details,
                ))
        elif field == "message_template_quality_update":
            score = (value.get("new_quality_score") or "").upper()
            if score in dict(self._fields["quality_score"].selection):
                templates.write({"quality_score": score})
            if score == "RED":
                account._alert_managers(_(
                    "WhatsApp template %s: low quality at Meta, it may be paused.", data["name"]
                ))
        elif field == "template_category_update":
            if value.get("previous_category"):
                category = (value.get("new_category") or "").lower()
                if category in dict(self._fields["category"].selection):
                    templates.write({"category": category})
            elif value.get("correct_category"):
                account._alert_managers(_(
                    "WhatsApp template %(name)s: Meta changes its category to %(category)s in 24 "
                    "hours (prices of the category).",
                    name=data["name"], category=value["correct_category"],
                ))

    # === SUBMISSION TO META === #

    def action_submit_to_meta(self):
        """Create the template at Meta, or submit its changes; Meta reviews it (up to 24
        hours) and tells its decision to Odoo by the webhook."""
        self.ensure_one()
        account = self._get_account(self.env[self.model].browse())
        if not account:
            raise UserError(_("No WhatsApp account is configured."))
        self.button_ids._normalize_url_for_meta()
        self._check_for_meta()
        components = self._prepare_meta_components(account)
        try:
            if self.wa_template_id:
                if self.status not in ("approved", "rejected", "paused"):
                    raise UserError(_(
                        "Meta accepts changes only on the approved, rejected or paused templates."
                    ))
                payload = {"components": components}
                if self.status != "approved":
                    payload["category"] = self.category.upper()
                account._api_request("POST", self.wa_template_id, json=payload)
            else:
                result = account._api_request("POST", f"{account.waba_id}/message_templates", json={
                    "name": self.template_name,
                    "language": self.lang_code,
                    "category": self.category.upper(),
                    "parameter_format": self.parameter_format,
                    "components": components,
                })
                self.wa_template_id = result.get("id")
                if result.get("category"):
                    self.category = result["category"].lower()
        except WhatsAppApiError as error:
            raise UserError(_(
                "Meta refused the template: %s", account._get_error_text(error)
            )) from error
        self.write({"status": "pending", "rejected_reason": False})
        return account._notify(
            _("Template submitted to Meta: its review can take up to 24 hours."), "success"
        )

    def _check_for_meta(self):
        """The rules of Meta for a template, checked before submitting it."""
        self.ensure_one()
        if self.category == "authentication":
            self._check_authentication_for_meta()
            return
        body = self.body or ""
        if not body.strip():
            raise UserError(_("Write the text of the template."))
        if len(body) > 1024:
            raise UserError(_("The text of the template is too long: 1024 characters at most."))
        if re.search(r"{{\s*\w+\s*}}\s*{{", body):
            raise UserError(_("Two variables must be separated by text."))
        if re.match(r"\s*{{", body) or re.search(r"}}\s*$", body):
            raise UserError(_("The text cannot start or end with a variable."))
        if self.header_type == "text" and len(self.header_text or "") > 60:
            raise UserError(_("The header is too long: 60 characters at most."))
        if len(self.footer_text or "") > 60:
            raise UserError(_("The footer is too long: 60 characters at most."))
        self.button_ids._check_for_meta()

    def _check_authentication_for_meta(self):
        """Authentication templates: one variable (the code), positional, and a time of 1 to 90
        minutes; Meta writes the text and the button."""
        self.ensure_one()
        if self.parameter_format != "positional":
            raise UserError(_("An authentication template uses numbered variables ({{1}}), not named ones."))
        if len(self.variable_ids) != 1:
            raise UserError(_(
                "An authentication template has one variable, the code ({{1}}): Meta writes the rest of the text."
            ))
        if not 1 <= self.code_expiration_minutes <= 90:
            raise UserError(_("The code of an authentication template is valid from 1 to 90 minutes."))

    def _get_sample_record(self):
        self.ensure_one()
        if not self.model or self.model not in self.env:
            return None
        return self.env[self.model].search([], order="id desc", limit=1) or None

    def _get_samples(self):
        """Examples of the variables for the review: the sample values, else the values for
        the latest record."""
        self.ensure_one()
        record = self._get_sample_record()
        samples = {}
        for variable in self.variable_ids:
            value = variable.sample_value
            if not value and record is not None and variable.value:
                value = self._clean_parameter(self._render(variable.value, record)[record.id])
            samples[variable._get_placeholder_key()] = value if value and value != "-" else _("Example")
        return samples

    def _prepare_meta_components(self, account):
        """Components of the template for the API of Meta (creation or edition)."""
        self.ensure_one()
        if self.category == "authentication":
            # Meta refuses a text here: it writes "<code> is your verification code" itself, in
            # the language of the template, with the security advice and the time of the code
            return [
                {"type": "BODY", "add_security_recommendation": True},
                {"type": "FOOTER", "code_expiration_minutes": self.code_expiration_minutes},
                {"type": "BUTTONS", "buttons": [{"type": "OTP", "otp_type": "COPY_CODE"}]},
            ]
        components = []
        if self.header_type == "text" and self.header_text:
            header = {"type": "HEADER", "format": "TEXT", "text": self.header_text}
            if "{{" in self.header_text:
                header["example"] = {"header_text": [self.header_sample or _("Example")]}
            components.append(header)
        elif self.header_type == "document":
            components.append({
                "type": "HEADER",
                "format": "DOCUMENT",
                "example": {"header_handle": [self._upload_sample_document(account)]},
            })
        samples = self._get_samples()
        body = {"type": "BODY", "text": self.body}
        if self.variable_ids:
            if self.parameter_format == "named":
                body["example"] = {"body_text_named_params": [
                    {"param_name": key, "example": value} for key, value in samples.items()
                ]}
            else:
                body["example"] = {"body_text": [list(samples.values())]}
        components.append(body)
        if self.footer_text:
            components.append({"type": "FOOTER", "text": self.footer_text})
        if self.button_ids:
            components.append({
                "type": "BUTTONS",
                "buttons": [button._prepare_meta_button() for button in self.button_ids],
            })
        return components

    def _upload_sample_document(self, account):
        """Upload the sample PDF of the header with the Resumable Upload API of Meta (the
        App ID of the account is needed); return its handle."""
        self.ensure_one()
        if not account.app_id:
            raise UserError(_(
                "Enter the App ID of the Meta app on the WhatsApp account to submit a template "
                "with a document."
            ))
        if self.header_sample_file:
            content = base64.b64decode(self.header_sample_file)
            name = self.header_sample_filename or "sample.pdf"
        else:
            record = self._get_sample_record()
            if record is None or not self.header_report_id:
                raise UserError(_("Give a sample PDF for the header of the template."))
            report = self.header_report_id.sudo()
            content, _report_type = report._render_qweb_pdf(report.report_name, record.ids)
            name = "sample.pdf"
        version = account.api_version
        token = account.sudo().access_token
        try:
            session = requests.post(
                f"{const.GRAPH_URL}/{version}/{account.app_id}/uploads",
                params={"file_name": name, "file_length": len(content),
                        "file_type": "application/pdf", "access_token": token},
                timeout=30,
            )
            session.raise_for_status()
            upload = requests.post(
                f"{const.GRAPH_URL}/{version}/{session.json()['id']}",
                headers={"Authorization": f"OAuth {token}", "file_offset": "0"},
                data=content,
                timeout=60,
            )
            upload.raise_for_status()
            return upload.json()["h"]
        except (requests.exceptions.RequestException, KeyError, ValueError) as error:
            raise UserError(_("The sample document could not be uploaded to Meta: %s", error)) from error

    def write(self, vals):
        result = super().write(vals)
        if "body" in vals:
            self._sync_variables()
        return result

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        templates._sync_variables()
        return templates

    def _sync_variables(self):
        """Add a variable line for each variable of the body not mapped yet."""
        for template in self:
            known = {variable._get_placeholder_key() for variable in template.variable_ids}
            missing = [
                name for name in dict.fromkeys(PLACEHOLDER_RE.findall(template.body or ""))
                if name not in known
            ]
            template.variable_ids = [fields.Command.create({
                "sequence": int(name) if name.isdigit() else 10,
                "param_name": False if name.isdigit() else name,
                "value": False,
            }) for name in missing]

    def _fill_body(self, values):
        """The body with its variables replaced by the given values (by placeholder key)."""
        self.ensure_one()
        return PLACEHOLDER_RE.sub(
            lambda match: values.get(match.group(1), match.group(0)), self.body or ""
        )

    # === SENDING === #

    def _get_account(self, records):
        """The account that sends the template: the one of the conversation it is sent from
        (when the template exists in its WhatsApp Business account), else the account of the
        template, else the first account of the company."""
        self.ensure_one()
        channel = self.env["discuss.channel"].sudo().browse(
            self.env.context.get("whatsapp_channel_id") or []
        ).exists()
        channel_account = channel.whatsapp_account_id
        if channel_account and (
            not self.account_id or self.account_id.waba_id == channel_account.waba_id
        ):
            return channel_account
        if self.account_id:
            return self.account_id
        company = records[:1].company_id if "company_id" in records._fields else False
        return self.env["whatsapp.account"].sudo()._get_default_account(
            company or self.env.company
        )

    def _get_render_lang(self):
        """Odoo language matching the language of the template (amounts and dates)."""
        self.ensure_one()
        langs = [code for code, _name in self.env["res.lang"].get_installed()]
        code = self.lang_code.replace("-", "_")
        return next(
            (lang for lang in langs if lang == code),
            next((lang for lang in langs if lang.split("_")[0] == code.split("_")[0]), None),
        )

    def _render(self, source, records):
        """Render an inline template (``{{ object.name }}``) on records: {id: text}."""
        if not source:
            return dict.fromkeys(records.ids, "")
        Render = self.env["mail.render.mixin"].sudo().with_context(lang=self._get_render_lang())
        return Render._render_template(source, records._name, records.ids)

    def _get_recipient(self, record):
        """The contact who receives the message for this record."""
        self.ensure_one()
        if record._name == "res.partner":
            return record
        try:
            partner = reduce(lambda rec, fname: rec[fname], self.partner_field.split("."), record)
        except (KeyError, AttributeError):
            return self.env["res.partner"]
        if not partner or partner._name != "res.partner":
            return self.env["res.partner"]
        return partner[:1]

    def _get_lang_version(self, partner):
        """The version of this template in the language of the contact: the template of the
        same name at Meta for the same documents and account, in that language (or another
        variant of it: en for en_US), not refused by Meta. This template when there is none.
        """
        self.ensure_one()
        lang = (partner.lang or "") if partner else ""
        if not lang or self._lang_base(self.lang_code) == self._lang_base(lang):
            return self
        domain = [
            ("template_name", "=", self.template_name),
            ("model_id", "=", self.model_id.id),
            ("status", "not in", ("rejected", "paused", "disabled", "pending")),
            ("id", "!=", self.id),
        ]
        if self.account_id:
            domain.append(("account_id", "in", [self.account_id.id, False]))
        versions = self.search(domain)
        code = lang.replace("-", "_")
        same_code = versions.filtered(lambda version: version.lang_code.replace("-", "_") == code)
        same_language = versions.filtered(
            lambda version: self._lang_base(version.lang_code) == self._lang_base(code)
        )
        return same_code[:1] or same_language[:1] or self

    @staticmethod
    def _lang_base(code):
        """Language of a code without its country: fr for fr_FR, en for en-US."""
        return (code or "").replace("-", "_").split("_")[0].lower()

    def _send(self, records):
        """Queue a message of this template for each record; return the created messages.

        Each contact gets the version of the template in their language when there is one
        (see ``_get_lang_version``). The messages are sent in the background by a scheduled
        action started right away, so that the business flows (order confirmation...) never
        wait for Meta.
        """
        self.ensure_one()
        records = records.sudo()
        by_version = {}
        for record in records:
            version = self._get_lang_version(self._get_recipient(record))
            by_version[version] = by_version.get(version, records.browse()) | record
        if not by_version or list(by_version) == [self]:
            return self._send_version(records)
        return self.env["whatsapp.message"].concat(
            version._send_version(version_records)
            for version, version_records in by_version.items()
        )

    def _send_version(self, records):
        """Queue a message of this very template (this language) for each record."""
        self.ensure_one()
        account = self._get_account(records)
        if not account or not records:
            if not account:
                _logger.info("WhatsApp: no account, template %s not sent.", self.template_name)
            return self.env["whatsapp.message"]
        rendered = {
            variable: self._render(variable.value, records) for variable in self.variable_ids
        }
        header_values = (
            self._render(self.header_value, records) if self.header_type == "text" else {}
        )
        button_values = self._render(self.button_url_value, records)
        Message = self.env["whatsapp.message"].sudo()
        messages_vals = []
        for record in records:
            partner = self._get_recipient(record)
            vals = {
                "account_id": account.id,
                "template_id": self.id,
                "model": record._name,
                "res_id": record.id,
                "partner_id": partner.id,
                "direction": "outgoing",
                "state": "queued",
            }
            values = {
                variable._get_placeholder_key():
                    self._clean_parameter(rendered[variable][record.id])
                for variable in self.variable_ids
            }
            vals["body"] = self._fill_body(values)
            number = partner._whatsapp_number() if partner else False
            user_ref = partner.whatsapp_user_ref if partner and not number else False
            vals["phone"] = number
            vals["user_ref"] = user_ref
            button = (button_values.get(record.id) or "").strip()
            skip_reason = self._get_skip_reason(account, partner, number or user_ref)
            if not skip_reason and self.button_url_dynamic and not button:
                skip_reason = _(
                    "The link button of the template expects the end of its URL, but none is "
                    "given (Link Button Variable)."
                )
            if skip_reason:
                messages_vals.append({**vals, "state": "skipped", "error": skip_reason})
                continue
            payload = self._prepare_payload(
                number, values,
                header=self._clean_parameter(header_values.get(record.id)),
                button=button,
                user_ref=user_ref,
            )
            vals["payload"] = json.dumps(payload)
            if self.header_type == "document" and self.header_report_id:
                vals["attachment_id"] = self._render_document(record).id
            messages_vals.append(vals)
        messages = Message.create(messages_vals)
        if any(message.state == "queued" for message in messages):
            self.env.ref("whatsapp_cloud.ir_cron_send_queued_messages")._trigger()
        return messages

    @api.model
    def _clean_parameter(self, value):
        """A variable value accepted by WhatsApp: no line break nor tab, no more than 4 spaces
        in a row, never empty (non-breaking spaces of the amounts are kept)."""
        return re.sub(r"[ \t\n\r\f\v]+", " ", value or "").strip() or "-"

    def _get_skip_reason(self, account, partner, number):
        """Why the message cannot be sent to this contact, if it cannot."""
        self.ensure_one()
        if not partner:
            return _("No contact to send the message to.")
        if not number:
            return _("The contact has no valid phone number.")
        if self.status == "pending":
            return _("The template is waiting for the approval of Meta.")
        if account.require_opt_in and not partner.whatsapp_opt_in:
            return _("The contact did not agree to receive WhatsApp messages.")
        if self.status in ("rejected", "paused", "disabled"):
            return _("The template is %s at Meta.", self.status)
        return False

    def _prepare_payload(self, number, values, header=None, button=None, user_ref=None):
        """Body of the request to the messages API (without the media of the header)."""
        self.ensure_one()

        def parameter(key, text):
            param = {"type": "text", "text": text}
            if self.parameter_format == "named":
                param["parameter_name"] = key
            return param

        if self.category == "authentication":
            # The code goes in the text and in the button that copies it
            code = values[self.variable_ids[:1]._get_placeholder_key()] if self.variable_ids else ""
            components = [
                {"type": "body", "parameters": [{"type": "text", "text": code}]},
                {"type": "button", "sub_type": "url", "index": "0", "parameters": [{"type": "text", "text": code}]},
            ]
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                **self.env["whatsapp.message"]._get_recipient_vals(number, user_ref),
                "type": "template",
                "template": {
                    "name": self.template_name,
                    "language": {"code": self.lang_code},
                    "components": components,
                },
            }
        components = []
        header_expects_value = (
            "{{" in self.header_text if self.header_text else bool(self.header_value)
        )
        if self.header_type == "text" and header and header_expects_value:
            components.append({"type": "header", "parameters": [{"type": "text", "text": header}]})
        if self.variable_ids:
            components.append({
                "type": "body",
                "parameters": [
                    parameter(variable._get_placeholder_key(),
                              values[variable._get_placeholder_key()])
                    for variable in self.variable_ids
                ],
            })
        # the URL variable of the button, when Meta expects one (or when not synchronised yet)
        expects_button = self.status == "unknown" or self.button_url_dynamic
        if self.button_url_value and button and expects_button:
            url_button = self._get_url_button()
            components.append({
                "type": "button",
                "sub_type": "url",
                "index": str(self._get_url_button_index()),
                "parameters": [{
                    "type": "text",
                    "text": url_button._get_url_variable(button) if url_button
                    else quote(button.strip(), safe=URL_SAFE_CHARS),
                }],
            })
        template = {"name": self.template_name, "language": {"code": self.lang_code}}
        if components:
            template["components"] = components
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            **self.env["whatsapp.message"]._get_recipient_vals(number, user_ref),
            "type": "template",
            "template": template,
        }

    def _get_url_button(self):
        """The link button whose URL ends with a variable, if any."""
        self.ensure_one()
        return self.button_ids.sorted("sequence").filtered(
            lambda button: button.button_type == "url" and "{{" in (button.url or "")
        )[:1]

    def _get_url_button_index(self):
        """Position of the link button with a variable among the buttons of the template."""
        self.ensure_one()
        button = self._get_url_button()
        return self.button_ids.sorted("sequence").ids.index(button.id) if button else 0

    def _render_document(self, record):
        """PDF of the header, stored as an attachment of the message log."""
        self.ensure_one()
        report = self.header_report_id.sudo()
        pdf, _report_type = report._render_qweb_pdf(report.report_name, record.ids)
        name = (
            report.print_report_name
            and safe_eval(report.print_report_name, {"object": record, "time": time})
            or report.name
        )
        return self.env["ir.attachment"].sudo().create({
            "name": f"{name}.pdf",
            "raw": pdf,
            "mimetype": "application/pdf",
            "res_model": "whatsapp.message",
        })


class WhatsappTemplateVariable(models.Model):
    _name = "whatsapp.template.variable"
    _description = "WhatsApp Template Variable"
    _order = "template_id, sequence, id"

    template_id = fields.Many2one(
        comodel_name="whatsapp.template", required=True, index=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    param_name = fields.Char(
        string="Name", help="Name of the variable, for the templates with named variables."
    )
    placeholder = fields.Char(string="Variable", compute="_compute_placeholder")
    sample_value = fields.Char(
        string="Example",
        help="Example of the value, for the review of the template by Meta; when empty, the "
        "value for the latest document is used.",
    )
    value = fields.Char(
        help="Value of the variable for each document, e.g. {{ object.partner_id.name }}, "
        "{{ object.name }}, {{ format_amount(object.amount_total, object.currency_id) }}.",
    )

    @api.depends("param_name", "sequence", "template_id.variable_ids")
    def _compute_placeholder(self):
        for variable in self:
            variable.placeholder = "{{%s}}" % variable._get_placeholder_key()

    def _get_placeholder_key(self):
        """Key of the variable in the body: its name, or its position (1, 2...)."""
        self.ensure_one()
        if self.param_name:
            return self.param_name
        positional = self.template_id.variable_ids.filtered(lambda v: not v.param_name)
        return str(list(positional).index(self) + 1) if self in positional else "1"


class WhatsappTemplateButton(models.Model):
    _name = "whatsapp.template.button"
    _description = "WhatsApp Template Button"
    _order = "template_id, sequence, id"

    template_id = fields.Many2one(
        comodel_name="whatsapp.template", required=True, index=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    button_type = fields.Selection(
        selection=[
            ("quick_reply", "Quick reply"),
            ("url", "Link"),
            ("phone_number", "Call"),
            ("other", "Other (at Meta)"),
        ],
        string="Type",
        required=True,
        default="quick_reply",
    )
    name = fields.Char(string="Text", required=True, translate=False)
    url = fields.Char(
        string="URL",
        help="https://... ; for a link per document, end it with {{1}} after a slash (e.g. "
        "{base_url}/{{1}}): Odoo adds the value of the Link Button Variable of the template.",
    )
    url_example = fields.Char(
        string="URL Example",
        help="Example of the end of the URL (or of the whole URL), for the review by Meta.",
    )
    phone_number = fields.Char(help="Number in international format, e.g. +237699000000.")

    def _check_for_meta(self):
        buttons = self.sorted("sequence")
        if len(buttons) > 10:
            raise UserError(_("A template has 10 buttons at most."))
        if len(buttons.filtered(lambda b: b.button_type == "url")) > 2:
            raise UserError(_("A template has 2 link buttons at most."))
        if len(buttons.filtered(lambda b: b.button_type == "phone_number")) > 1:
            raise UserError(_("A template has 1 call button at most."))
        kinds = [button.button_type == "quick_reply" for button in buttons]
        # the quick replies must be together, before or after the other buttons
        if sum(1 for a, b in zip(kinds, kinds[1:]) if a != b) > 1:
            raise UserError(_("The quick replies must follow each other, before or after the other buttons."))
        for button in buttons:
            if button.button_type == "other":
                raise UserError(_("The button %s can only be edited at Meta.", button.name))
            if len(button.name or "") > 25:
                raise UserError(_("The text of the button %s is too long: 25 characters at most.", button.name))
            url = button._get_resolved_url()
            host = urlsplit(url.partition("{{")[0]).hostname or ""
            if button.button_type == "url" and (
                not url.startswith("https://") or "." not in host or host == "localhost"
            ):
                if "{base_url}" in (button.url or ""):
                    raise UserError(_(
                        "The link of the button %(button)s must be a public address in https, "
                        "but the address of the site is %(url)s: set it in the system parameter "
                        "web.base.url (Settings > Technical > System Parameters).",
                        button=button.name, url=button.get_base_url(),
                    ))
                raise UserError(_("The link of the button %s must start with https://.", button.name))
            if button.button_type == "url" and "{{" in url and not url.endswith("}}"):
                raise UserError(_("The variable of the link %s must be at its end.", button.name))
            if button.button_type == "phone_number" and not button.phone_number:
                raise UserError(_("Give the number of the button %s.", button.name))

    def _get_resolved_url(self):
        """URL of the button, {base_url} replaced by the address of the site."""
        self.ensure_one()
        return (self.url or "").strip().replace("{base_url}", self.get_base_url().rstrip("/"))

    def _get_url_prefix(self):
        """Beginning of the URL of the button, before its variable."""
        self.ensure_one()
        return self._get_resolved_url().partition("{{")[0]

    def _normalize_url_for_meta(self):
        """Meta refuses a variable glued to the domain name (https://shop.example.com{{1}},
        "not a valid URI"): add the slash (https://shop.example.com/{{1}})."""
        for button in self.filtered(lambda b: b.button_type == "url" and "{{" in (b.url or "")):
            if not urlsplit(button._get_url_prefix()).path:
                start, brace, end = button.url.strip().partition("{{")
                button.url = f"{start}/{brace}{end}"

    def _get_url_variable(self, value):
        """End of the URL sent with a message for this button: without a double slash, the
        special characters percent-encoded as Meta asks."""
        self.ensure_one()
        value = (value or "").strip()
        if self._get_url_prefix().endswith("/"):
            value = value.lstrip("/")
        return quote(value, safe=URL_SAFE_CHARS)

    def _get_meta_url_example(self):
        """Example of the URL for the review by Meta: a whole URL."""
        self.ensure_one()
        example = (self.url_example or "").strip() or "example"
        if example.startswith(("https://", "http://")):
            return example
        return self._get_url_prefix() + self._get_url_variable(example)

    def _prepare_meta_button(self):
        self.ensure_one()
        if self.button_type == "url":
            url = self._get_resolved_url()
            vals = {"type": "URL", "text": self.name, "url": url}
            if "{{" in url:
                vals["example"] = [self._get_meta_url_example()]
            return vals
        if self.button_type == "phone_number":
            return {"type": "PHONE_NUMBER", "text": self.name, "phone_number": self.phone_number}
        return {"type": "QUICK_REPLY", "text": self.name}
