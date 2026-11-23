from odoo import fields, models


class WhatsappCallRate(models.Model):
    """Price of a minute of call of the company to a country (rate card of Meta, entered by the
    managers: Meta changes it every quarter)."""

    _name = "whatsapp.call.rate"
    _description = "Rate of the WhatsApp Calls of the Company"
    _order = "country_id"

    account_id = fields.Many2one(
        comodel_name="whatsapp.account", required=True, index=True, ondelete="cascade"
    )
    country_id = fields.Many2one(comodel_name="res.country", string="Country Called", required=True)
    phone_code = fields.Integer(related="country_id.phone_code")
    price_per_minute = fields.Float(
        string="Price of a Minute", digits=(16, 5), required=True,
        help="Rate of Meta for a minute of call of the company to this country (billed by "
        "pulses of 6 seconds).",
    )
    currency_id = fields.Many2one(related="account_id.call_currency_id")

    _account_country_unique = models.Constraint(
        "unique(account_id, country_id)", "A country has one rate per WhatsApp account."
    )
