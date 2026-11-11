from datetime import timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.modules.module import load_script
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

    def test_code_is_behind_the_button(self):
        """Meta refuses a code in a Utility template: the message has no code, its button opens
        the page that follows the order, where the customer reads it."""
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = order.picking_ids
        parcel.action_ocd_pick_up()
        with patch.object(WhatsappTemplate, "_send", lambda template, records: template.env["whatsapp.message"]):
            parcel.action_ocd_leave()
        template = self.env.ref("ocd_live_shop_whatsapp.template_parcel_on_the_way")
        self.assertNotIn("{{4}}", template.body)
        self.assertFalse(template.variable_ids.filtered(lambda v: v.sequence == 4))
        for variable in template.variable_ids:
            self.assertNotEqual(template._render(variable.value, parcel)[parcel.id], parcel.sudo().ocd_delivery_code)
        self.assertEqual(template.button_ids.name, "Suivre mon colis")
        path = template._render(template.button_url_value, parcel)[parcel.id]
        self.assertEqual(path, f"ocd/suivi/{order.id}?access_token={order.access_token}")

    def test_migration_puts_the_code_behind_the_button(self):
        """A database installed before has the refused text with the code and no button, still
        waiting in Odoo (no webhook): the migration gives the new text and the button."""
        xmlid = "ocd_live_shop_whatsapp.template_parcel_on_the_way"
        template = self.env.ref(xmlid)
        new_text = template.body
        migration = load_script(
            "ocd_live_shop_whatsapp/migrations/20.0.1.5.0/post-migration.py", "ocd_shop_whatsapp_texts_20_0_1_5_0"
        )
        template.write({
            "body": migration.OLD_TEXTS[xmlid][0], "button_ids": [Command.clear()],
            "button_url_value": False, "status": "pending",
        })
        template.variable_ids.filtered(lambda v: v.sequence == 4).value = "{{ object.ocd_delivery_code }}"
        migration.migrate(self.env.cr, "20.0.1.4.0")
        self.env.invalidate_all()
        self.assertEqual(template.body, new_text)
        self.assertEqual(template.button_ids.mapped("name"), ["Suivre mon colis"])
        self.assertEqual(template.button_url_value, "{{ object._ocd_tracking_path() }}")
        self.assertEqual(sorted(template.variable_ids.mapped("sequence")), [1, 2, 3])

    def test_message_when_the_vendor_goes_live(self):
        alert = self.env["ocd.boutique.alert"]._ocd_register(self.brenda, phone="+228 90112233")
        later = self.company._ocd_local_today() + timedelta(days=30)
        booking = self.env["ocd.live.booking"].create({
            "partner_id": self.brenda.id, "start_datetime": self.company._ocd_slot_starts(later)[0], "mode": "remote",
        })
        booking.state = "confirmed"
        now = fields.Datetime.now()
        self.env.cr.execute(
            "UPDATE ocd_live_booking SET start_datetime = %s, end_datetime = %s WHERE id = %s",
            [now - timedelta(minutes=5), now + timedelta(minutes=85), booking.id],
        )
        booking.invalidate_recordset(["start_datetime", "end_datetime"])
        calls = []

        def fake_send(template, records):
            calls.append((template.template_name, records))
            return template.env["whatsapp.message"]

        with patch.object(WhatsappTemplate, "_send", fake_send):
            self.env["ocd.boutique.alert"]._ocd_send_due()
        self.assertEqual(calls, [("ocd_vendeur_en_live", alert)])
        self.assertEqual(alert.state, "sent")
        template = self.env.ref("ocd_live_shop_whatsapp.template_vendor_live")
        rendered = template._render(template.variable_ids.value, alert)
        self.assertEqual(rendered[alert.id], "Brenda Wax")

    def _deliver(self, parcel):
        if parcel.ocd_stage == "to_prepare":
            parcel.action_ocd_ready()
        if parcel.ocd_delivery_mode != "vendor" and parcel.ocd_stage == "ready":
            parcel.action_ocd_pick_up()
        parcel.action_ocd_leave()
        parcel._ocd_check_code(parcel.sudo().ocd_delivery_code)

    def test_shop_messages_not_doubled_for_the_parcels(self):
        """"Order shipped" of the shop goes when a transfer is validated, i.e. when a parcel is
        delivered: not for the parcels, which have their own messages. The satisfaction message
        goes once per order, after its last parcel."""
        Template = self.env["whatsapp.template"]
        shipped = Template.new({"template_name": "order_shipped"})
        feedback = Template.new({"template_name": "delivery_feedback"})
        order = self._order(self.estelle, [(self.butter, 1), (self.dress, 1)])
        parcels = order.picking_ids
        self.assertEqual(len(parcels), 2, "One parcel per vendor")
        first, second = parcels.sorted("id")
        self._deliver(first)
        self.assertEqual(first.state, "done")
        self.assertFalse(parcels._ocd_whatsapp_keep(shipped))
        self.assertFalse(parcels._ocd_whatsapp_keep(feedback), "A parcel is still on its way")
        self._deliver(second)
        self.assertEqual(parcels._ocd_whatsapp_keep(feedback), second)
        other = Template.new({"template_name": "ocd_colis_livre"})
        self.assertEqual(parcels._ocd_whatsapp_keep(other), parcels)
