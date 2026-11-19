from odoo import api, models

APP_NAME = "OCD Live"
# The names Odoo gives the application when nobody chose one
ODOO_NAMES = ("", "Odoo")


class IrConfigParameter(models.Model):
    _inherit = "ir.config_parameter"

    @api.model
    def _ocd_default_web_app_name(self):
        """The name of the application installed on the phones and computers of the team: OCD Live,
        unless the team chose another one in the settings. Called at each install and update: the
        parameter may already exist without the module (saved from the settings), it is never
        created twice."""
        current = self.sudo().get_str("web.web_app_name") or ""
        if current.strip() in ODOO_NAMES:
            self.sudo().set_str("web.web_app_name", APP_NAME)
        return True
