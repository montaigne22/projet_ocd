from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WhatsappConversationAssign(models.TransientModel):
    _name = "whatsapp.conversation.assign"
    _description = "Transfer a WhatsApp Conversation"

    channel_id = fields.Many2one(comodel_name="discuss.channel", required=True, readonly=True)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Agent",
        required=True,
        domain="[('id', 'in', available_user_ids)]",
    )
    available_user_ids = fields.Many2many(
        comodel_name="res.users", compute="_compute_available_user_ids"
    )
    note = fields.Text(help="Shown in the conversation, for the agent who takes it over.")

    @api.depends("channel_id")
    def _compute_available_user_ids(self):
        for wizard in self:
            account = wizard.channel_id.sudo().whatsapp_account_id
            wizard.available_user_ids = account._get_agents() if account else False

    def action_transfer(self):
        self.ensure_one()
        channel = self.channel_id
        channel._whatsapp_check_agent()
        channel = channel.sudo()
        channel._whatsapp_assign(self.user_id, notify=False)
        text = _("Conversation transferred to %(user)s by %(by)s.",
                 user=self.user_id.name, by=self.env.user.name)
        if self.note:
            text = f"{text} {self.note}"
        channel._whatsapp_notify(text, partners=self.user_id.partner_id)
        return {"type": "ir.actions.act_window_close"}


class WhatsappLinkPartner(models.TransientModel):
    """Identify the customer of a conversation started from an unknown number."""

    _name = "whatsapp.link.partner"
    _description = "Identify a WhatsApp Customer"

    channel_id = fields.Many2one(comodel_name="discuss.channel", required=True, readonly=True)
    current_partner_id = fields.Many2one(
        related="channel_id.whatsapp_partner_id", string="Contact Created"
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Existing Contact",
        required=True,
        help="The contact who writes: the conversation, the messages and the WhatsApp number "
        "go to this contact, and the contact created for the unknown number is merged into it.",
    )

    def action_link(self):
        self.ensure_one()
        channel = self.channel_id
        channel._whatsapp_check_agent()
        channel = channel.sudo()
        created = channel.whatsapp_partner_id
        partner = self.partner_id.sudo()
        if partner == created:
            created.action_whatsapp_confirm_contact()
            return {"type": "ir.actions.act_window_close"}
        vals = {"whatsapp_to_identify": False}
        if channel.whatsapp_user_ref and not partner.whatsapp_user_ref:
            vals["whatsapp_user_ref"] = channel.whatsapp_user_ref
        if created.whatsapp_username and not partner.whatsapp_username:
            vals["whatsapp_username"] = created.whatsapp_username
        if channel.whatsapp_number and partner._whatsapp_number() != channel.whatsapp_number:
            vals["phone"] = f"+{channel.whatsapp_number}"
            if partner.phone:
                partner.message_post(body=_(
                    "WhatsApp number +%(number)s replaces the phone %(phone)s.",
                    number=channel.whatsapp_number, phone=partner.phone,
                ))
        partner.write(vals)
        channel._whatsapp_set_partner(partner)
        if created and created.whatsapp_to_identify:
            self._merge_into(created, partner)
        channel._whatsapp_notify(_(
            "Customer identified by %(user)s: %(partner)s.",
            user=self.env.user.name, partner=partner.display_name,
        ))
        return {"type": "ir.actions.act_window_close"}

    def _merge_into(self, created, partner):
        """Move the messages and documents of the contact created for the number to the
        right contact, then remove it."""
        if created.user_ids:
            raise UserError(_("The contact %s is a user: it cannot be merged.", created.display_name))
        self.env["whatsapp.message"].sudo().search([("partner_id", "=", created.id)]).write(
            {"partner_id": partner.id}
        )
        self.env["mail.message"].sudo().search([("author_id", "=", created.id)]).write(
            {"author_id": partner.id}
        )
        wizard = self.env["base.partner.merge.automatic.wizard"].sudo()
        wizard._merge((created | partner).ids, partner, extra_checks=False)
        # the merge fills the empty fields of the contact from the merged one
        partner.whatsapp_to_identify = False
