from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        """The texts of the scripts of OCD Vote (« Pay 900 F for 10 votes ») in the language of the
        visitor."""
        return [*super()._get_translation_frontend_modules_name(), "ocd_vote"]
