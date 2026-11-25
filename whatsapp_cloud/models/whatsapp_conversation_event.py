from odoo import api, fields, models


class WhatsappConversationEvent(models.Model):
    """What happened in the conversations, for the figures of the team: the answer of an agent
    to a customer who waited (written, or a call taken), and the resolution of a conversation,
    each with its duration (real, and within the opening hours of the account)."""

    _name = "whatsapp.conversation.event"
    _description = "WhatsApp Conversation Event"
    _order = "date desc, id desc"

    channel_id = fields.Many2one(
        comodel_name="discuss.channel", string="Conversation", required=True, index=True,
        ondelete="cascade",
    )
    account_id = fields.Many2one(
        comodel_name="whatsapp.account", string="Account", required=True, index=True, ondelete="cascade",
    )
    user_id = fields.Many2one(comodel_name="res.users", string="Agent", index="btree_not_null", ondelete="set null")
    kind = fields.Selection(
        selection=[("answer", "Answer to a customer who waited"), ("resolve", "Conversation resolved")],
        required=True,
    )
    start_date = fields.Datetime(
        string="Since", required=True,
        help="Answer: the customer waited since this date. Resolution: the conversation opened then.",
    )
    date = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    minutes = fields.Integer(string="Minutes")
    working_minutes = fields.Integer(
        string="Minutes of Opening Hours",
        help="The minutes within the opening hours of the account (public holidays excluded).",
    )

    @api.model
    def _log(self, channel, kind, start, user=None, date=None):
        """Note an answer or a resolution of the conversation `channel`, from `start` (the customer
        waits, the conversation opened) to `date` (now by default)."""
        account = channel.whatsapp_account_id
        if not account or not start:
            return self.browse()
        date = date or fields.Datetime.now()
        start = min(start, date)
        return self.sudo().create({
            "channel_id": channel.id,
            "account_id": account.id,
            "user_id": user.id if user and not user._is_superuser() and not user.share else False,
            "kind": kind,
            "start_date": start,
            "date": date,
            "minutes": int((date - start).total_seconds() // 60),
            "working_minutes": int(account._get_working_minutes(start, date)),
        })
