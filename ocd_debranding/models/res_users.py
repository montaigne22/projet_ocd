from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _init_odoobot(self):
        """Override of `mail_bot`: no welcome chat of the robot, which presents Odoo."""
        self.ensure_one()
        self.sudo().odoobot_state = "disabled"
        return self.env["discuss.channel"]
