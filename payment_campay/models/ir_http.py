from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        """Override of `http_routing` to translate the messages of the payment form."""
        return [*super()._get_translation_frontend_modules_name(), "payment_campay"]
