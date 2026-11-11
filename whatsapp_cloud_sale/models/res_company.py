from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    whatsapp_order_tracking = fields.Boolean(
        string="WhatsApp Order Tracking",
        default=True,
        help="In the WhatsApp conversations, the \"Track my order\" option of the welcome menu "
        "and the order references written by the customers are answered with the status of "
        "their orders.",
    )
    whatsapp_quotation = fields.Boolean(
        string="Quotations on WhatsApp",
        default=True,
        help="\"Send on WhatsApp\" button of the quotations, with the link to view and pay "
        "them online.",
    )
