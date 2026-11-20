from odoo.addons.whatsapp_cloud.tests.common import WhatsAppCommon
from odoo.addons.whatsapp_cloud_call import const


class WhatsAppCallCommon(WhatsAppCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        params = cls.env["ir.config_parameter"].sudo()
        params.set_str(const.PARAM_HOST, "calls.example.com")
        params.set_str(const.PARAM_TOKEN, "server-key")
        cls.account.write({
            "call_enabled": True,
            "display_phone_number": "+228 90 00 00 01",
            "resource_calendar_id": False,
        })
        cls.account.sudo().call_sip_password = "meta-sip-password"
        cls.agent = cls.env["res.users"].create({
            "name": "Afi Agent",
            "login": "afi.agent",
            "group_ids": [(4, cls.env.ref("whatsapp_cloud.group_whatsapp_user").id)],
            "whatsapp_call_available": True,
        })
        cls.agent2 = cls.env["res.users"].create({
            "name": "Kossi Agent",
            "login": "kossi.agent",
            "group_ids": [(4, cls.env.ref("whatsapp_cloud.group_whatsapp_user").id)],
            "whatsapp_call_available": True,
        })
        cls.account.agent_user_ids = cls.agent | cls.agent2
        cls.Call = cls.env["whatsapp.call"]

    def route(self, wacid="wacid.ABC", number="237670000000"):
        return self.Call._server_route({
            "wacid": wacid,
            "uuid": f"uuid-{wacid}",
            "number": f"+{number}",
            "phone_number_id": self.account.phone_number_id,
        })
