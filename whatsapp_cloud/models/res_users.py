from odoo import models

from odoo.addons.mail.tools.discuss import Store


class ResUsers(models.Model):
    _inherit = "res.users"

    def _store_init_global_fields(self, res: Store.FieldList):
        super()._store_init_global_fields(res)
        res.attr(
            "has_access_whatsapp",
            not self.share
            and self.has_group("whatsapp_cloud.group_whatsapp_user")
            and self.env.company.whatsapp_conversations,
        )
