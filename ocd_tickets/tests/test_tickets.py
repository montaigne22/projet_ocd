import io
from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time
from PIL import Image

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged
from odoo.tools import BinaryBytes

from odoo.addons.ocd_live.tests.common import pending_payment
from odoo.addons.ocd_live_shop.tests.common import OcdShopCommon


def png(color=(244, 106, 0)):
    data = io.BytesIO()
    Image.new("RGB", (60, 40), color).save(data, "PNG")
    return data.getvalue()


@tagged("post_install", "-at_install")
class TestOcdTickets(HttpCase, OcdShopCommon):
    """OCD Tickets (chantier 6, design OcdTickets): tickets of events, one signed QR per person
    checked once at the entrance, paid like the rest of OCD Live."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({
            "ocd_ticket_organizer_share": 90, "ocd_ticket_max_per_order": 10, "ocd_ticket_hold_minutes": 10,
            "ocd_ticket_sale_end_hours": 0, "ocd_ticket_refund_days": 7, "phone": "+237 690000000",
        })
        cls.cameroon = cls.env.ref("base.cm")
        cls.organizer = cls.env["res.partner"].create({
            "name": "Etoile Events", "phone": "+237 677112233", "ocd_vote_organizer": True,
            "ocd_vote_organizer_verified": True, "country_id": cls.cameroon.id,
        })
        cls.hall = cls.env["res.partner"].create({
            "name": "Palais des Sports", "street": "Warda", "city": "Douala", "country_id": cls.cameroon.id,
        })
        cls.Event = cls.env["event.event"]
        cls.Order = cls.env["sale.order"]
        cls.RegistrationClass = type(cls.env["event.registration"])
        cls.Partner = type(cls.env["res.partner"])

    def _event(self, name="Nuit de l'Afrobeat", days=5, **values):
        now = fields.Datetime.now()
        return self.Event.create({
            "name": name,
            "ocd_ticketing": True,
            "ocd_organizer_id": self.organizer.id,
            "ocd_kind": "Concert",
            "date_begin": now + timedelta(days=days),
            "date_end": now + timedelta(days=days, hours=8),
            "ocd_doors_at": now + timedelta(days=days, hours=-1, minutes=-30),
            "date_tz": "Africa/Douala",
            "address_id": self.hall.id,
            "ocd_about": "Six artistes, deux scènes, de 20 h à l'aube.",
            "event_ticket_ids": [
                fields.Command.create({"name": "Standard", "price": 5000, "seats_max": 100,
                                       "description": "Debout, fosse"}),
                fields.Command.create({"name": "VIP", "price": 15000, "seats_max": 12,
                                       "description": "Places assises, boisson offerte"}),
                fields.Command.create({"name": "Table de 6", "price": 80000, "seats_max": 1,
                                       "description": "6 billets, une table réservée"}),
            ],
            **values,
        })

    def _open(self, **values):
        event = self._event(**values)
        event.action_ocd_send_to_check()
        event.action_ocd_approve()
        return event

    def _kind(self, event, name):
        return event.event_ticket_ids.filtered(lambda ticket: ticket.name == name)

    def _buy(self, event, counts, partner=None, name="Estelle Ngono", **kwargs):
        quantities = {self._kind(event, kind): count for kind, count in counts.items()}
        return self.Order._ocd_ticket_create(event, quantities, partner or self.estelle, name, **kwargs)

    def _pay(self, order):
        transaction = pending_payment(self, order)
        transaction._set_done()
        transaction._post_process()
        return order.ocd_ticket_registration_ids

    def _controller(self, event, **values):
        partner = self.env["res.partner"].create({"name": "Junior", "phone": "+237 655443322",
                                                  "country_id": self.cameroon.id})
        return self.env["ocd.ticket.controller"].create({
            "event_id": event.id, "partner_id": partner.id, "name": "Junior", "gate": "Porte 1", **values,
        })

    # === THE EVENT === #

    def test_an_event_its_kinds_and_its_check(self):
        event = self._event()
        self.assertEqual(event.ocd_slug, "nuit-de-l-afrobeat")
        self.assertEqual(self._event().ocd_slug, "nuit-de-l-afrobeat-2", "Each event has its own address")
        self.assertEqual(self._event(name="Entrée").ocd_slug, "entree-2", "Not the address of the entrance")
        products = event.event_ticket_ids.product_id
        self.assertEqual(len(products), 3, "A product of its own for each kind: the control room shows it")
        self.assertEqual(products.mapped("service_tracking"), ["event"] * 3)
        self.assertEqual(self._kind(event, "VIP").product_id.list_price, 15000)
        self.assertFalse(event.event_mail_ids, "No e-mail of the Events application: WhatsApp")
        self.assertEqual(len(event._ocd_code_prefix()), 3)
        self.assertFalse(event._ocd_public(), "Checked by the team before it shows")
        empty = self.Event.create({"name": "Vide", "ocd_ticketing": True, "date_begin": event.date_begin,
                                   "date_end": event.date_end})
        with self.assertRaisesRegex(UserError, "kinds of tickets"):
            empty.action_ocd_send_to_check()
        event.action_ocd_send_to_check()
        self.assertEqual(event.ocd_state, "to_check")
        items = next(column for column in self.env["ocd.live.verification"]._ocd_columns()
                     if column["key"] == "ticket")["items"]
        self.assertEqual([item["id"] for item in items], [event.id])
        self.env["ocd.live.verification"].ocd_approve("ticket_event", event.id)
        self.assertEqual(event.ocd_state, "approved")
        self.assertTrue(event._ocd_public() and event._ocd_on_sale())
        self.assertEqual(event._ocd_place_text(), "Palais des Sports, Douala")
        self.assertIn("google.com/maps", event._ocd_route_url())
        self.assertEqual(event._ocd_seats_line(), ("0 tickets sold", "113 left"))

    # === BUY, HOLD, PAY === #

    def test_the_seats_are_held_then_the_tickets_paid(self):
        event = self._open()
        standard, vip = self._kind(event, "Standard"), self._kind(event, "VIP")
        with self.assertRaisesRegex(UserError, "at most"):
            self._buy(event, {"Standard": 11})
        self.company.ocd_ticket_max_per_order = 20
        with self.assertRaisesRegex(UserError, "Only 12"):
            self._buy(event, {"VIP": 13})
        self.company.ocd_ticket_max_per_order = 10
        with self.assertRaisesRegex(UserError, "at least one"):
            self._buy(event, {"Standard": 0})
        order = self._buy(event, {"Standard": 2, "VIP": 1})
        self.assertEqual(order.amount_total, 25000)
        self.assertEqual(order.ocd_ticket_amount_company, 25000)
        self.assertEqual(order.order_line.mapped("event_ticket_id"), standard | vip)
        self.assertFalse(order.ocd_ticket_registration_ids, "No ticket before the payment")
        left = event._ocd_left()
        self.assertEqual((left[standard.id], left[vip.id]), (98, 11), "Held during the payment")
        told = []
        with patch.object(self.RegistrationClass, "_ocd_tell_ready", lambda records: told.append(records)):
            tickets = self._pay(order)
        self.assertEqual(order.state, "sale")
        self.assertEqual(len(tickets), 3, "One ticket per person")
        self.assertEqual(set(tickets.mapped("state")), {"open"})
        self.assertEqual(set(tickets.mapped("name")), {"Estelle Ngono"})
        self.assertEqual(len(set(tickets.mapped("ocd_code"))), 3)
        self.assertRegex(tickets[0].ocd_code, r"^[A-Z0-9]{3}-[A-Z0-9]{4}-[A-Z0-9]{2}$")
        self.assertEqual(len(told), 1)
        self.assertEqual(len(told[0]), 1, "One message for the order, which opens all its tickets")
        self.assertEqual(event.ocd_sold_count, 3)
        self.assertEqual((event.ocd_amount_total, event.ocd_organizer_amount), (25000, 22500))
        self.assertEqual(event._ocd_left()[standard.id], 98)
        self.assertEqual(tickets.mapped("ocd_amount_company"), [5000, 5000, 15000])
        self.assertIn("Ticket 1 of 3", tickets.sorted("id")[0]._ocd_index_text())
        # Not paid in time: the seats go back on sale
        late = self._buy(event, {"VIP": 2})
        self.assertEqual(event._ocd_left()[vip.id], 9)
        with freeze_time(fields.Datetime.now() + timedelta(minutes=11)):
            self.assertEqual(event._ocd_left()[vip.id], 11, "The time to pay is over")
            event._cron_ocd_tickets()
        self.assertEqual(late.state, "cancel")
        # A payment checked by the team keeps its seats
        waiting = self._buy(event, {"VIP": 1})
        pending_payment(self, waiting)
        with freeze_time(fields.Datetime.now() + timedelta(minutes=30)):
            event._cron_ocd_tickets()
            self.assertEqual(event._ocd_left()[vip.id], 10)
        self.assertEqual(waiting.state, "draft")

    def test_the_last_seats_paid_twice_make_two_tickets(self):
        """Two buyers paying the last table at the same time: both paid, both get their ticket (the
        money is received), the team sees it."""
        event = self._open()
        first = self._buy(event, {"Table de 6": 1})
        first.ocd_ticket_hold_until = fields.Datetime.now() - timedelta(minutes=1)
        second = self._buy(event, {"Table de 6": 1}, partner=self.brenda)
        self._pay(first)
        self._pay(second)
        self.assertEqual(len(event.registration_ids.filtered(lambda reg: reg.state == "open")), 2)

    # === THE ENTRANCE === #

    def _login_controller(self, phone="655443322"):
        self.authenticate(None, None)
        with patch.object(self.Partner, "_ocd_send_login_code", lambda partner: True), \
                patch.object(self.Partner, "_ocd_check_login_code", lambda partner, code: code == "123456"):
            page = self.url_open("/billets/entree/connexion", data={
                "csrf_token": self.csrf_token(), "phone": phone, "country_id": self.cameroon.id,
            }).text
            self.assertIn('name="code"', page)
            return self.url_open("/billets/entree/code", data={"csrf_token": self.csrf_token(), "code": "123456"})

    def test_the_entrance_lets_each_ticket_in_once(self):
        event = self._open()
        other = self._open(name="Gospel Live Yaoundé", days=12)
        control = self._controller(event)
        tickets = self._pay(self._buy(event, {"Standard": 2}))
        foreign = self._pay(self._buy(other, {"Standard": 1}))
        self.assertIn("/billets/entree/connexion", self.url_open("/billets/entree").url)
        response = self._login_controller()
        self.assertIn(f"/billets/entree/{event.id}", response.url, "Their only event")
        self.assertIn("Put the QR of the ticket in the frame", response.text)
        self.assertIn("0 / 2", response.text)
        scan = f"/billets/entree/{event.id}/scan"
        first = tickets.sorted("id")[0]
        result = self.make_jsonrpc_request(scan, {"text": f"{first.get_base_url()}{first._ocd_ticket_path()}"})
        self.assertEqual(result["kind"], "ok")
        self.assertEqual(result["title"], "Entry OK")
        self.assertIn("Standard · Estelle Ngono", result["lines"][0])
        self.assertEqual(result["counter"], "1 / 2")
        self.assertEqual((first.state, first.ocd_controller_id, first.ocd_gate), ("done", control, "Porte 1"))
        result = self.make_jsonrpc_request(scan, {"text": first._ocd_ticket_path()})
        self.assertEqual(result["kind"], "already")
        self.assertIn("Porte 1, by Junior", result["lines"][0])
        result = self.make_jsonrpc_request(scan, {"text": foreign.ocd_code})
        self.assertEqual((result["kind"], result["title"]), ("other", "Not for tonight"))
        self.assertIn("Gospel Live Yaoundé", result["lines"][0])
        changed = first._ocd_ticket_path()[:-3] + "abc"
        self.assertEqual(self.make_jsonrpc_request(scan, {"text": changed})["kind"], "unknown", "A changed copy")
        self.assertEqual(self.make_jsonrpc_request(scan, {"text": "XYZ-0000-00"})["kind"], "unknown")
        # The code typed by hand, in small letters, with spaces; without the network, its hour
        second = tickets.sorted("id")[1]
        typed = second.ocd_code.replace("-", " ").lower()
        at = fields.Datetime.now() - timedelta(minutes=20)
        result = self.make_jsonrpc_request(scan, {"text": typed, "at": at.timestamp() + 0})
        self.assertEqual(result["kind"], "ok")
        self.assertEqual(second.ocd_entered_at.replace(microsecond=0), at.replace(microsecond=0),
                         "An entry made without the network keeps its hour")
        listed = self.make_jsonrpc_request(f"/billets/entree/{event.id}/liste", {})
        self.assertEqual(len(listed["tickets"]), 2)
        self.assertTrue(all(row["entered"] for row in listed["tickets"]))
        # Without JavaScript: the code typed in the form
        page = self.url_open(f"/billets/entree/{event.id}", data={"csrf_token": self.csrf_token(),
                                                                   "code": second.ocd_code}).text
        self.assertIn("Already entered", page)
        # The entrance of another event is not theirs
        self.assertEqual(self.url_open(f"/billets/entree/{other.id}").status_code, 404)

    def test_give_a_ticket_to_a_friend(self):
        event = self._open()
        order = self._buy(event, {"Standard": 2})
        tickets = self._pay(order)
        ticket = tickets.sorted("id")[1]
        old_path, old_code = ticket._ocd_ticket_path(), ticket.ocd_code
        self.authenticate(None, None)
        told = []
        with patch.object(self.RegistrationClass, "_ocd_tell_ready", lambda records: told.append(records)):
            response = self.url_open(f"{old_path}/donner", data={
                "csrf_token": self.csrf_token(), "t": order.ocd_ticket_token, "name": "Paul Eto'o",
                "phone": "699887766", "country_id": self.cameroon.id,
            })
        self.assertIn("Given: the ticket left on the WhatsApp of Paul Eto&#39;o with a new QR.", response.text)
        self.assertEqual((ticket.name, ticket.ocd_version, ticket.ocd_given_by_id), ("Paul Eto'o", 2, self.estelle))
        self.assertNotEqual(ticket.ocd_code, old_code)
        self.assertEqual(told, [ticket], "The friend receives it on WhatsApp")
        self.assertEqual(self.url_open(old_path).status_code, 404, "The old QR no longer works")
        self.assertEqual(self.url_open(ticket._ocd_ticket_path()).status_code, 200)
        registration, current = self.env["event.registration"]._ocd_find(old_path)
        self.assertEqual((registration, current), (ticket, False))
        page = self.url_open(order._ocd_tickets_path()).text
        self.assertIn("It is paid: 1 ticket", page, "The buyer keeps the other one")
        self.assertNotIn(ticket.ocd_code, page)

    # === CANCELLED, MOVED === #

    def test_cancelled_or_moved(self):
        event = self._open()
        order = self._buy(event, {"Standard": 2})
        tickets = self._pay(order)
        waiting = self._buy(event, {"VIP": 1})
        with self.assertRaisesRegex(UserError, "Move"):
            event.date_begin = event.date_begin + timedelta(days=1)
        changes = []
        with patch.object(self.RegistrationClass, "_ocd_tell_changed",
                          lambda records, change: changes.append((records, change))):
            new_begin = event.date_begin + timedelta(days=7)
            wizard = self.env["ocd.ticket.move"].create({
                "event_id": event.id, "date_begin": new_begin, "date_end": new_begin + timedelta(hours=8),
            })
            wizard.action_move()
            self.assertEqual(event.date_begin, new_begin)
            self.assertTrue(event.ocd_moved_at)
            self.assertEqual([change for _records, change in changes], ["moved"])
            self.assertTrue(all(ticket._ocd_valid() for ticket in tickets), "The tickets stay valid")
            # The buyer who cannot come asks for the refund during the days set
            self.authenticate(None, None)
            page = self.url_open(order._ocd_tickets_path()).text
            self.assertIn("I cannot come: refund me", page)
            self.url_open(f"/billets/commande/{order.id}/rembourser", data={
                "csrf_token": self.csrf_token(), "t": order.ocd_ticket_token,
            })
            self.assertEqual(set(tickets.mapped("ocd_refund_state")), {"to_refund"})
            self.assertFalse(any(ticket._ocd_valid() for ticket in tickets))
            # Cancelled: every ticket paid is to refund, the order waiting is cancelled
            other = self._pay(self._buy(event, {"Standard": 1}, partner=self.brenda, name="Brenda"))
            event.action_ocd_cancel()
        self.assertEqual(changes[-1][1], "cancelled")
        self.assertEqual(changes[-1][0].partner_id, self.brenda)
        self.assertEqual(other.ocd_refund_state, "to_refund")
        self.assertEqual(waiting.state, "cancel")
        other.action_ocd_refunded()
        self.assertEqual(other.ocd_refund_state, "refunded")
        self.assertIn("cancelled", self.url_open(f"/billets/{event.ocd_slug}").text)

    # === AT THE DOOR === #

    def test_sell_at_the_door(self):
        event = self._open(ocd_door_sale=True)
        control = self._controller(event, can_sell=True)
        self._login_controller()
        page = self.url_open(f"/billets/entree/{event.id}/vendre").text
        self.assertIn("WhatsApp of the customer", page)
        vip = self._kind(event, "VIP")
        response = self.url_open(f"/billets/entree/{event.id}/vendre", data={
            "csrf_token": self.csrf_token(), f"q_{vip.id}": "1", "phone": "698765432",
            "country_id": self.cameroon.id, "method": "cash",
        })
        self.assertIn("Sold: the ticket left on the WhatsApp of the customer and entered.", response.text)
        order = self.Order.search([("ocd_ticket_controller_id", "=", control.id)])
        self.assertEqual((order.state, order.ocd_ticket_cash_state, order.ocd_ticket_source), ("sale", "to_collect", "door"))
        ticket = order.ocd_ticket_registration_ids
        self.assertEqual((ticket.state, ticket.ocd_controller_id, ticket.ocd_source), ("done", control, "door"))
        self.assertEqual(control.cash_amount, 15000)
        self.assertEqual(ticket.ocd_payment_method, "Cash at the door")
        control.action_ocd_cash_collected()
        self.assertEqual(order.ocd_ticket_cash_state, "collected")
        # Mobile Money: the payment form of OCD Live
        response = self.url_open(f"/billets/entree/{event.id}/vendre", data={
            "csrf_token": self.csrf_token(), f"q_{vip.id}": "1", "phone": "698765432",
            "country_id": self.cameroon.id, "method": "momo",
        })
        self.assertIn("/billets/commande/", response.url)
        momo = self.Order.search([("ocd_ticket_controller_id", "=", control.id), ("state", "=", "draft")])
        tickets = self._pay(momo)
        self.assertEqual(tickets.state, "done", "Paid at the door: it enters at once")
        # A controller who does not sell
        control.can_sell = False
        self.assertIn(f"/billets/entree/{event.id}", self.url_open(f"/billets/entree/{event.id}/vendre").url)

    # === DURING A LIVE === #

    def test_a_ticket_on_screen_during_a_live(self):
        event = self._open()
        standard = self._kind(event, "Standard")
        standard.ocd_live_price = 4000
        now = fields.Datetime.now()
        later = self.company._ocd_local_today() + timedelta(days=30)
        live = self.env["ocd.live.booking"].create({
            "partner_id": self.brenda.id, "start_datetime": self.company._ocd_slot_starts(later)[0], "mode": "remote",
        })
        live.write({"state": "confirmed"})
        self.env.cr.execute(
            "UPDATE ocd_live_booking SET start_datetime = %s, end_datetime = %s WHERE id = %s",
            [now - timedelta(minutes=18), now + timedelta(minutes=72), live.id],
        )
        live.invalidate_recordset(["start_datetime", "end_datetime"])
        self.assertEqual(standard._ocd_price(), 5000, "Not sold during this live yet")
        event.ocd_booking_ids = live
        self.assertEqual(standard._ocd_price(), 4000)
        self.assertIn(standard.product_id.product_tmpl_id, live.vendor_product_ids, "The control room shows it")
        self.env["ocd.live.regie"].ocd_show_product(live.id, standard.product_id.product_tmpl_id.id)
        self.assertEqual(live.current_product_tmpl_id, standard.product_id.product_tmpl_id)
        self.authenticate(None, None)
        page = self.url_open(f"/ocd/boutique/{self.brenda.id}").text
        self.assertIn(f"{event._ocd_public_path()}/acheter?q_{standard.id}=1", page)
        self.assertIn("price of the live", page)
        order = self._buy(event, {"Standard": 2})
        self.assertEqual((order.amount_total, order.ocd_ticket_source, order.ocd_ticket_live_id), (8000, "live", live))
        self._pay(order)
        self.assertEqual(event.ocd_live_amount, 8000)
        page = self.url_open(event._ocd_public_path()).text
        self.assertIn("Live price until the end of the live.", page)

    # === THE PAGES === #

    def test_the_pages_buy_and_my_tickets(self):
        draft = self._event()
        event = self._open(ocd_poster=BinaryBytes(png(), filename="affiche.png"))
        self.authenticate(None, None)
        self.assertEqual(self.url_open(f"/billets/{draft.ocd_slug}").status_code, 404, "Not checked yet")
        page = self.url_open("/billets").text
        self.assertIn("Nuit de l&#39;Afrobeat", page)
        self.assertIn("From ", page)
        self.assertIn("5,000", page)
        page = self.url_open(f"/billets/{event.ocd_slug}").text
        for text in ("Palais des Sports, Douala", "Warda", "Debout, fosse", "Only 12 left", "OCD Live guarantee",
                     "Organiser checked", "Choose my tickets", "0 tickets sold", "Six artistes"):
            self.assertIn(text, page)
        self.assertEqual(self.url_open(event._ocd_poster_url()).status_code, 200)
        standard = self._kind(event, "Standard")
        page = self.url_open(f"/billets/{event.ocd_slug}/acheter?q_{standard.id}=2").text
        self.assertIn("How many tickets?", page)
        self.assertIn(f'name="q_{standard.id}"', page)
        self.assertIn("10 tickets at most per order.", page)
        page = self.url_open(f"/billets/{event.ocd_slug}/acheter", data={
            "csrf_token": self.csrf_token(), f"q_{standard.id}": "2", "name": "", "phone": "670000000",
            "country_id": self.cameroon.id,
        }).text
        self.assertIn("Write your name", page)
        response = self.url_open(f"/billets/{event.ocd_slug}/acheter", data={
            "csrf_token": self.csrf_token(), f"q_{standard.id}": "2", "name": "Estelle Ngono", "phone": "670000000",
            "country_id": self.cameroon.id,
        })
        order = self.Order.search([("ocd_ticket_event_id", "=", event.id)])
        self.assertEqual(order.partner_id, self.estelle, "The contact of the number")
        self.assertIn(f"/billets/commande/{order.id}", response.url)
        self.assertIn("Your seats are held 10 minutes.", response.text)
        self.assertEqual(self.url_open(f"/billets/commande/{order.id}?t=wrong").status_code, 404)
        self._pay(order)
        page = self.url_open(order._ocd_tickets_path()).text
        self.assertIn("It is paid: 2 tickets", page)
        tickets = order.ocd_ticket_registration_ids
        for ticket in tickets:
            self.assertIn(ticket.ocd_code, page)
        self.assertIn("data:image/png;base64,", page, "The QR of each person")
        self.assertIn("Give this ticket", page)
        self.assertIn(f'action="{tickets.sorted("id")[0]._ocd_ticket_path()}/donner"', page)
        pdf = self.url_open(f"/billets/commande/{order.id}/pdf?t={order.ocd_ticket_token}")
        self.assertEqual(pdf.headers["Content-Type"], "application/pdf")
        page = self.url_open(tickets[0]._ocd_ticket_path()).text
        self.assertIn(tickets[0].ocd_code, page)
        self.assertEqual(self.url_open(f"/billets/billet/{tickets[0].id}/wrong").status_code, 404)
        self.assertIn("2 tickets sold", self.url_open(f"/billets/{event.ocd_slug}").text)

    # === THE ORGANISER === #

    def test_the_space_of_the_organiser(self):
        event = self._event()
        self.authenticate(None, None)
        with patch.object(self.Partner, "_ocd_send_login_code", lambda partner: True), \
                patch.object(self.Partner, "_ocd_check_login_code", lambda partner, code: code == "123456"):
            self.url_open("/vote/organisateur/connexion", data={
                "csrf_token": self.csrf_token(), "phone": "677112233", "country_id": self.cameroon.id,
            })
            response = self.url_open("/vote/organisateur/code", data={"csrf_token": self.csrf_token(), "code": "123456"})
        self.assertIn(f"/vote/organisateur/evenement/{event.id}", response.url, "Their only event")
        for text in ("Tickets sold", "Your share (90 %)", "Send my event to OCD Live", "By ticket", "Standard"):
            self.assertIn(text, response.text)
        response = self.url_open(f"/vote/organisateur/evenement/{event.id}/envoyer", data={"csrf_token": self.csrf_token()})
        self.assertEqual(event.ocd_state, "to_check")
        self.assertIn("the team checks your event", response.text)
        added = []
        Controller = type(self.env["ocd.ticket.controller"])
        with patch.object(Controller, "_ocd_tell_added", lambda records: added.append(records)):
            response = self.url_open(f"/vote/organisateur/evenement/{event.id}/controleurs", data={
                "csrf_token": self.csrf_token(), "name": "Aïcha", "phone": "699001122", "country_id": self.cameroon.id,
                "gate": "Porte 2",
            })
        self.assertIn("Added: Aïcha receives the news on WhatsApp.", response.text)
        control = event.ocd_controller_ids
        self.assertEqual((control.name, control.gate, control.can_sell), ("Aïcha", "Porte 2", False))
        self.assertEqual(added, [control])
        self.assertIn("Porte 2 · control only", response.text)
        self.url_open(f"/vote/organisateur/evenement/{event.id}/controleurs/{control.id}/retirer",
                      data={"csrf_token": self.csrf_token()})
        self.assertFalse(control.active)
        other = self._event(ocd_organizer_id=self.env["res.partner"].create({"name": "Autre", "ocd_vote_organizer": True}).id)
        self.assertEqual(self.url_open(f"/vote/organisateur/evenement/{other.id}").status_code, 404)

    # === THE BACK OFFICE === #

    def test_the_back_office_and_the_payout(self):
        event = self._open()
        self._pay(self._buy(event, {"Standard": 4}))
        sections = str(self.env["ocd.live.settings"]._ocd_sections())
        for text in ("Share of the organiser", "Tickets per order", "Seats held during the payment",
                     "Refund on request after a move"):
            self.assertIn(text, sections)
        self.assertIn("tickets", str(self.env["ocd.automation"].get_automations_page()))
        self.assertEqual(event.action_ocd_view_tickets()["domain"], [("event_id", "=", event.id)])
        self.assertEqual(self.organizer.action_ocd_view_events()["domain"], [("ocd_organizer_id", "=", self.organizer.id)])
        with freeze_time(event.date_end + timedelta(minutes=10)):
            event._cron_ocd_tickets()
        self.assertEqual(event.ocd_payout_state, "to_pay")
        self.assertEqual(event.ocd_organizer_amount, 18000)
        with self.assertRaisesRegex(UserError, "reference"):
            event.action_ocd_payout_paid()
        event.ocd_payout_reference = "MOMO-7781"
        event.action_ocd_payout_paid()
        self.assertEqual(event.ocd_payout_state, "paid")

    def test_the_reminder_the_day_before(self):
        event = self._open(days=2)
        self._pay(self._buy(event, {"Standard": 2}))
        reminded = []
        with patch.object(self.RegistrationClass, "_ocd_tell_reminder", lambda records: reminded.append(records)):
            event._cron_ocd_tickets()
            self.assertFalse(reminded, "Not yet")
            with freeze_time(event.date_begin - timedelta(hours=20)):
                event._cron_ocd_tickets()
                event._cron_ocd_tickets()
        self.assertEqual(len(reminded), 1, "Once")
        self.assertEqual(len(reminded[0]), 1, "One message per buyer")
