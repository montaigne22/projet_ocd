from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    whatsapp_conversations = fields.Boolean(
        string="WhatsApp Conversations",
        default=True,
        help="The messages of the customers arrive in Discuss (WhatsApp tab), where the team "
        "answers them. Disabled: they are only noted on the contacts, without answer.",
    )
    whatsapp_read_receipts = fields.Boolean(
        string="WhatsApp Read Receipts",
        default=True,
        help="The customers see the blue ticks when an agent reads their message, and "
        "\"typing...\" while the agent writes.",
    )
    whatsapp_answer_reminders = fields.Boolean(
        string="WhatsApp Answer Reminders",
        default=True,
        help="The agents are reminded of the messages waiting for an answer, then the managers "
        "are alerted (delays of the WhatsApp account).",
    )
