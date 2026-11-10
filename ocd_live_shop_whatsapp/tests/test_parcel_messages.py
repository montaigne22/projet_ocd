from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.ocd_live_shop.tests.common import OcdShopCommon
from odoo.addons.whatsapp_cloud.models.whatsapp_template import WhatsappTemplate


@tagged("post_install", "-at_install")
class TestOcdParcelMessages(OcdShopCommon):

    def test_messages_of_a_parcel(self):
        calls = []

        def fake_send(template, records):
            calls.append((template.template_name, records))
            return template.env["whatsapp.message"]

        with patch.object(WhatsappTemplate, "_send", fake_send):
            order = self._order(self.estelle, [(self.butter, 1)])
            parcel = order.picking_ids
            parcel.action_ocd_ready()
            parcel.action_ocd_leave()
            parcel._ocd_report_problem("unreachable")
            parcel.action_ocd_retry()
            parcel.action_ocd_leave()
            parcel._ocd_check_code(parcel.sudo().ocd_delivery_code)
        # whatsapp_cloud_sale also sends its own message of the confirmed order
        names = [name for name, _records in calls if name.startswith("ocd_")]
        self.assertEqual(names, [
            "ocd_colis_a_preparer",
            "ocd_colis_en_route",
            "ocd_colis_echec",
            "ocd_colis_en_route",
            "ocd_colis_livre",
        ])

    def test_code_is_in_the_message(self):
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        parcel.action_ocd_pick_up()
        with patch.object(WhatsappTemplate, "_send", lambda template, records: template.env["whatsapp.message"]):
            parcel.action_ocd_leave()
        template = self.env.ref("ocd_live_shop_whatsapp.template_parcel_on_the_way")
        code_variable = template.variable_ids.filtered(lambda v: v.sequence == 4)
        rendered = template._render(code_variable.value, parcel)
        self.assertEqual(rendered[parcel.id], parcel.sudo().ocd_delivery_code)
