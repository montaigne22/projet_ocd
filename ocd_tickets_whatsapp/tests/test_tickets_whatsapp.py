from datetime import timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.tests import tagged

from odoo.addons.ocd_live.tests.common import pending_payment
from odoo.addons.ocd_live_shop.tests.common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdTicketsWhatsapp(OcdShopCommon):
    """OCD Tickets on WhatsApp (chantier 6, design OcdTickets): the tickets ready, the reminder,
    the event cancelled or moved, the controller added."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env["base"].with_context(lang="en_US").env
        cls.env["whatsapp.account"].search([]).active = False
        cls.account = cls.env["whatsapp.account"].create({
            "name": "OCD Live", "phone_number_id": "1110029", "waba_id": "2220029", "access_token": "test-token",
            "resource_calendar_id": False,
        })
        cameroon = cls.env.ref("base.cm")
        hall = cls.env["res.partner"].create({"name": "Palais des Sports", "city": "Douala", "country_id": cameroon.id})
        organizer = cls.env["res.partner"].create({"name": "Etoile Events", "ocd_vote_organizer": True})
        now = fields.Datetime.now()
        cls.event = cls.env["event.event"].create({
            "name": "Afrobeat Night", "ocd_ticketing": True, "ocd_organizer_id": organizer.id,
            "date_begin": now + timedelta(days=3), "date_end": now + timedelta(days=3, hours=6),
            "date_tz": "Africa/Douala", "address_id": hall.id,
            "event_ticket_ids": [fields.Command.create({"name": "Standard", "price": 5000, "seats_max": 50})],
        })
        cls.event.action_ocd_approve()
        cls.buyer = cls.env["res.partner"].create({
            "name": "Paul", "phone": "+237 670000049", "country_id": cameroon.id, "lang": "en_US",
        })
        cls.Message = cls.env["whatsapp.message"]

    def _messages(self, name):
        return self.Message.search([("template_id.template_name", "=", name)], order="id")

    def _paid(self, count=2):
        order = self.env["sale.order"]._ocd_ticket_create(
            self.event, {self.event.event_ticket_ids: count}, self.buyer, "Paul Mbida")
        transaction = pending_payment(self, order)
        transaction._set_done()
        transaction._post_process()
        return order

    def test_the_tickets_leave_on_whatsapp(self):
        order = self._paid()
        ready = self._messages("ocd_billets_prets")
        self.assertEqual(len(ready), 1, "One message for the order")
        self.assertIn("Your tickets for Afrobeat Night are ready: see you", ready.body)
        self.assertIn("Palais des Sports, Douala", ready.body)
        template = self.env.ref("ocd_tickets_whatsapp.template_tickets_ready")
        first = order.ocd_ticket_registration_ids.sorted("id")[0]
        self.assertEqual(template._render(template.button_url_value, first)[first.id],
                         order._ocd_tickets_path().lstrip("/"))
        self.assertFalse(self.Message.search([
            ("model", "=", "sale.order"), ("res_id", "=", order.id),
            ("template_id.template_name", "in", ("order_confirmed", "order_received")),
        ]), "Not the messages of the orders of the shop")
        # Given to a friend: the same message, the button opens their ticket
        friend = self.env["res.partner"].create({"name": "Linda", "phone": "+237 690000049", "lang": "en_US"})
        given = order.ocd_ticket_registration_ids.sorted("id")[1]._ocd_give(friend, "Linda Eko")
        ready = self._messages("ocd_billets_prets")
        self.assertEqual(ready[-1:].res_id, given.id)
        self.assertEqual(template._render(template.button_url_value, given)[given.id], given._ocd_ticket_path().lstrip("/"))

    def test_the_reminder_and_the_changes(self):
        order = self._paid()
        with freeze_time(self.event.date_begin - timedelta(hours=10)):
            self.event._cron_ocd_tickets()
        reminder = self._messages("ocd_billets_rappel")
        self.assertEqual(len(reminder), 1)
        self.assertIn("Reminder: Afrobeat Night tomorrow at", reminder.body)
        begin = self.event.date_begin + timedelta(days=7)
        self.event._ocd_move(begin, begin + timedelta(hours=6))
        moved = self._messages("ocd_billets_deplace")
        self.assertEqual(len(moved), 1)
        self.assertIn("is moved to", moved.body)
        self.assertIn("your tickets stay valid", moved.body)
        self.event.action_ocd_cancel()
        cancelled = self._messages("ocd_billets_annule")
        self.assertEqual(len(cancelled), 1)
        self.assertIn("OCD Live refunds you on this number", cancelled.body)
        self.assertEqual(cancelled.res_id, order.ocd_ticket_registration_ids.sorted("id")[0].id)

    def test_the_controller_is_told(self):
        partner = self.env["res.partner"].create({"name": "Junior", "phone": "+237 655000049", "lang": "en_US"})
        control = self.env["ocd.ticket.controller"].create({
            "event_id": self.event.id, "partner_id": partner.id, "name": "Junior",
        })
        control._ocd_tell_added()
        message = self._messages("ocd_billets_controleur")
        self.assertIn("Etoile Events gives you the control of the entrances of Afrobeat Night", message.body)
