from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.whatsapp_cloud import const


class WhatsappBotOption(models.Model):
    """Option of the welcome menu sent to the customers who start a conversation."""

    _name = "whatsapp.bot.option"
    _description = "WhatsApp Menu Option"
    _order = "account_id, sequence, id"

    account_id = fields.Many2one(
        comodel_name="whatsapp.account", required=True, index=True, ondelete="cascade"
    )
    parent_id = fields.Many2one(
        comodel_name="whatsapp.bot.option",
        string="Sub-menu of",
        index="btree_not_null",
        ondelete="cascade",
        domain="[('account_id', '=', account_id), ('action', '=', 'submenu')]",
    )
    child_ids = fields.One2many(
        comodel_name="whatsapp.bot.option", inverse_name="parent_id", string="Options of the Sub-menu",
        context={"active_test": False}, copy=True,
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(
        string="Option",
        required=True,
        translate=True,
        help="Text of the button (20 characters at most).",
    )
    description = fields.Char(
        translate=True,
        help="Shown under the option when the menu has more than 3 options (72 characters at "
        "most).",
    )
    action = fields.Selection(
        selection=[
            ("text", "Answer with a text"),
            ("submenu", "Open a sub-menu"),
            ("lang", "Change the language"),
            ("stop", "Stop the notifications"),
            ("start", "Receive the notifications"),
            ("handover", "Hand over to an agent"),
        ],
        required=True,
        default="text",
    )
    answer = fields.Text(
        translate=True,
        help="Text sent when the customer chooses the option; for a sub-menu, the text above "
        "its options.",
    )
    lang = fields.Selection(
        selection="_get_lang_selection",
        string="Language",
        help="Language of the answers, menus and notifications of the customer who chooses "
        "the option. The option is not offered to the customers who already use it.",
    )

    @api.model
    def _get_lang_selection(self):
        return self.env["res.lang"].get_installed()

    @api.model_create_multi
    def create(self, vals_list):
        # the options of a sub-menu belong to the account of the sub-menu
        parents = self.browse({vals["parent_id"] for vals in vals_list if vals.get("parent_id")})
        account_by_parent = {parent.id: parent.account_id.id for parent in parents}
        for vals in vals_list:
            if vals.get("parent_id"):
                vals["account_id"] = account_by_parent[vals["parent_id"]]
        return super().create(vals_list)

    @api.constrains("name", "description", "action", "answer", "lang")
    def _check_option(self):
        for option in self:
            if len(option.name or "") > const.MAX_BUTTON_TITLE:
                raise ValidationError(_(
                    "The option %s is too long: WhatsApp shows 20 characters at most.", option.name
                ))
            if len(option.description or "") > const.MAX_ROW_DESCRIPTION:
                raise ValidationError(_(
                    "The description of the option %s is too long: 72 characters at most.",
                    option.name,
                ))
            if option.action == "text" and not (option.answer or "").strip():
                raise ValidationError(_("Give the answer of the option %s.", option.name))
            if option.action == "lang" and not option.lang:
                raise ValidationError(_("Choose the language of the option %s.", option.name))

    @api.constrains("parent_id")
    def _check_parent(self):
        if self._has_cycle():
            raise ValidationError(_("A sub-menu cannot contain itself."))

    def _get_reply_id(self):
        """ID of the option in the interactive message, sent back by WhatsApp when chosen."""
        self.ensure_one()
        return f"whatsapp_option_{self.id}"

    def _is_available(self, channel):
        """Whether the option is offered to the customer of the conversation."""
        self.ensure_one()
        partner = channel.whatsapp_partner_id
        if self.action == "lang":
            return bool(self.lang) and self.lang != channel._whatsapp_get_lang()
        if self.action == "stop":
            return bool(partner.whatsapp_opt_in)
        if self.action == "start":
            return bool(partner) and not partner.whatsapp_opt_in
        if self.action == "submenu":
            return bool(channel._whatsapp_get_bot_options(self))
        return True

    def _run(self, channel, wa_message):
        """Answer the customer who chose the option in the conversation."""
        self.ensure_one()
        if self.action == "handover":
            channel._whatsapp_handover()
            return
        # a question answered: the menu stays usable, the conversation stays with the bot
        channel.whatsapp_bot_state = "menu"
        if self.action == "text":
            channel._whatsapp_send_answer(
                self.with_context(lang=channel._whatsapp_get_lang()).answer
            )
        elif self.action == "submenu":
            channel._whatsapp_send_menu(parent=self)
        elif self.action == "lang":
            channel._whatsapp_set_lang(self.lang)
        elif self.action in ("stop", "start"):
            channel._whatsapp_set_subscription(self.action == "start")
