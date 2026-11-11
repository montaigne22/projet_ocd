from random import randint

from odoo import fields, models


class WhatsappTag(models.Model):
    _name = "whatsapp.tag"
    _description = "WhatsApp Conversation Tag"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(default=lambda self: randint(1, 11))

    _name_uniq = models.Constraint("unique(name)", "This tag already exists.")
