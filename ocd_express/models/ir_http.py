from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        """The texts of the scripts of OCD Express (« You receive 13 775 F ») in the language of
        the visitor."""
        return [*super()._get_translation_frontend_modules_name(), "ocd_express"]
