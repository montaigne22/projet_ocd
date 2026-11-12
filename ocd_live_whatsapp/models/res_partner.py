from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    # === CONSENT === #
    # OCD Live asks the consent in its forms (booking, vendor space, checkout of the shop) and
    # keeps it on ocd_whatsapp_optin; WhatsApp (whatsapp_cloud) keeps its own (whatsapp_opt_in),
    # also changed by STOP and START. Both say the same: what is written on one is written on
    # the other.

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._ocd_sync_consent_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        return super().write(self._ocd_sync_consent_vals(dict(vals)))

    @api.model
    def _ocd_sync_consent_vals(self, vals):
        if "ocd_whatsapp_optin" in vals and "whatsapp_opt_in" not in vals:
            vals["whatsapp_opt_in"] = bool(vals["ocd_whatsapp_optin"])
        elif "whatsapp_opt_in" in vals and "ocd_whatsapp_optin" not in vals:
            vals["ocd_whatsapp_optin"] = bool(vals["whatsapp_opt_in"])
        return vals

    def _ocd_whatsapp_refused(self):
        """The contact refused the messages: box unticked, switch off, or STOP answered."""
        self.ensure_one()
        return not self.ocd_whatsapp_optin or self.whatsapp_opt_out

    def _ocd_whatsapp_consent(self):
        """Override of `ocd_live`: the messages reach the contact when they agreed, or when
        the WhatsApp account does not require the consent, and never after a refusal."""
        self.ensure_one()
        if self._ocd_whatsapp_refused():
            return False
        if self.whatsapp_opt_in:
            return True
        account = self.env["whatsapp.account"].sudo()._get_default_account(self.env.company)
        return bool(account) and not account.require_opt_in

    # === SENDING === #

    @api.model
    def _ocd_whatsapp_send(self, xmlid, records, requested=False, **context):
        """Queue the WhatsApp message of the template `xmlid` for `records`; return whether a
        message is on its way (not refused, not skipped by WhatsApp).

        - `requested`: the contact asks for this very message now (login code, link, ticket,
          alert they registered for): it goes even without the consent to the notifications.
        - Otherwise, never to a contact who refused; and only to the contacts who agreed when
          the WhatsApp account requires it (the default).

        Values that are not stored (a login code, a link) are given in `context` and read by
        the template with ctx.get()."""
        template = self.env.ref(xmlid, raise_if_not_found=False)
        if not template or not records:
            return False
        # sudo: the messages are sent by the system, also from the public pages
        template = template.sudo().with_context(ocd_whatsapp_requested=bool(requested), **context)
        if not self.env["ocd.automation"]._ocd_template_enabled(template):
            return False  # paused by the team (Automations)
        records = records.sudo()
        if not requested:
            records = records.filtered(lambda record: not self._ocd_whatsapp_refused_for(template, record))
        if not records:
            return False
        messages = template._send(records)
        return bool(messages.filtered(lambda message: message.state != "skipped"))

    @api.model
    def _ocd_whatsapp_refused_for(self, template, record):
        partner = template._get_recipient(record)
        return not partner or partner._ocd_whatsapp_refused()

    def _ocd_deliver_login_code(self, code):
        """Override of `ocd_live` to send the login code on WhatsApp."""
        return self._ocd_whatsapp_send(
            "ocd_live_whatsapp.template_login_code", self, requested=True, ocd_login_code=code
        )

    def _ocd_send_space_link(self):
        """Override of `ocd_live` to send the personal link on WhatsApp."""
        return self._ocd_whatsapp_send("ocd_live_whatsapp.template_space_link", self, requested=True)

    @api.model
    def _ocd_link_templates(self):
        """The template of the personal link of each login page."""
        return {"space": "ocd_live_whatsapp.template_space_link"}

    @api.model
    def _ocd_link_login_ready(self, target):
        """Override of `ocd_live`: the links leave when their template is not waiting for Meta,
        refused or paused. Otherwise the login asks for a code, whose template is an
        authentication one, the only kind Meta accepts for a login; when the code cannot leave
        either, the page keeps the link."""
        if not super()._ocd_link_login_ready(target):
            return False
        xmlid = self._ocd_link_templates().get(target)
        if not xmlid or self._ocd_template_usable(xmlid):
            return True
        return not self._ocd_template_usable("ocd_live_whatsapp.template_login_code")

    @api.model
    def _ocd_template_usable(self, xmlid):
        """Whether the messages of the template `xmlid` can leave: not waiting for Meta, not
        refused or paused at Meta, not paused by the team (Automations)."""
        template = self.env.ref(xmlid, raise_if_not_found=False)
        if not template:
            return False
        template = template.sudo()
        if template.status in ("pending", "rejected", "paused", "disabled"):
            return False
        return self.env["ocd.automation"]._ocd_template_enabled(template)

    def _ocd_send_access_link(self, url):
        """Override of `ocd_live` to send the link to choose a password on WhatsApp."""
        return self._ocd_whatsapp_send(
            "ocd_live_whatsapp.template_access_link", self, requested=True, ocd_access_url=url
        )
