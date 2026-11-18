from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        """The texts of the scripts of OCD Tickets (the scanner, the total) in the language of the
        visitor."""
        return [*super()._get_translation_frontend_modules_name(), "ocd_tickets"]
