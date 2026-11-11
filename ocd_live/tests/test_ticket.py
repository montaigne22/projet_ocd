import io
from datetime import datetime, time, timedelta

from freezegun import freeze_time
from PIL import Image

from odoo import fields
from odoo.tests import HttpCase, tagged

from odoo.addons.ocd_live import tools

from .common import OcdLiveCommon


@tagged("post_install", "-at_install")
class TestOcdLiveTicket(OcdLiveCommon):

    def test_signed_ticket_lets_in_once(self):
        booking = self._book(self.starts[0], state="confirmed")
        signature = booking._ocd_ticket_signature()
        self.assertTrue(booking._ocd_ticket_check(signature))
        changed = signature[:-1] + ("1" if signature[-1] == "0" else "0")
        self.assertFalse(booking._ocd_ticket_check(changed), "A ticket changed by hand is refused")
        self.assertFalse(booking._ocd_ticket_check(""))
        self.assertRegex(booking._ocd_ticket_seal(), r"^[0-9A-F]{4}-[0-9A-F]{4}$")
        other = self._book(self.starts[2], partner=self.other_vendor, state="confirmed")
        self.assertFalse(other._ocd_ticket_check(signature), "Each ticket has its own signature")
        self.assertTrue(booking._ocd_let_in())
        self.assertEqual(booking.ticket_checked_in_by, self.env.user)
        self.assertFalse(booking._ocd_let_in(), "A copy shown again is seen at once")

    def test_moved_live_refuses_its_former_ticket(self):
        booking = self._book(self.starts[0], state="confirmed")
        former = booking._ocd_ticket_signature()
        booking.action_ocd_team_move(self.starts[3])
        self.assertFalse(booking._ocd_ticket_check(former))
        self.assertTrue(booking._ocd_ticket_check(booking._ocd_ticket_signature()))

    def test_ticket_in_the_time_of_the_vendor(self):
        booking = self._book(self.starts[0], state="confirmed")
        values = booking._ocd_ticket_values()
        local = tools.to_tz(booking.start_datetime, "Africa/Douala")
        self.assertTrue(values["hours"].startswith(f"{local:%H:%M}"), "The vendor is in Cameroon")
        self.assertEqual(values["time_zone"], tools.zone_text(self.env, "Africa/Douala"))
        studio = tools.to_tz(booking.start_datetime, "Africa/Lome")
        self.assertIn(f"{studio:%H:%M}", values["studio_hours"], "At the studio, the hour of Lome too")
        self.assertFalse(booking._ocd_ticket_values("Africa/Lome")["studio_hours"])
        remote = self._book(self.starts[4], mode="remote", state="confirmed")
        self.assertFalse(remote._ocd_ticket_values()["studio_hours"], "From home: the hour of the vendor only")
        sample = booking.with_context(whatsapp_sample=True)._ocd_ticket_values()
        self.assertNotIn(self.vendor.name, sample["vendor"], "The sample shown to Meta has no real vendor")
        self.assertEqual(sample["reference"], "LIVE/0000")

    def test_announcement_without_personal_data(self):
        booking = self._book(self.starts[0], state="confirmed")
        values = booking._ocd_announce_values()
        texts = " ".join(str(value) for value in values.values())
        for private in (booking.ticket_code, booking.name, "670000002", booking._ocd_ticket_seal()):
            self.assertNotIn(private, texts)
        self.assertIn(self.vendor.name, values["name"])
        with Image.open(io.BytesIO(booking._ocd_announce_png())) as image:
            self.assertEqual(image.size, (1080, 1350))

    def test_time_zone_of_the_person(self):
        partner = self.env["res.partner"].create({
            "name": "Kofi", "country_id": self.env.ref("base.ci").id, "tz": "UTC",
        })
        self.assertEqual(partner._ocd_tz_name(), "Africa/Abidjan", "The country before a default of Odoo")
        partner._ocd_remember_tz("Europe/Paris")
        self.assertEqual(partner._ocd_tz_name(), "Europe/Paris", "The phone first")
        partner._ocd_remember_tz("UTC")
        self.assertEqual(partner.ocd_phone_tz, "Europe/Paris", "A browser that hides its zone changes nothing")
        self.assertEqual(self.env["res.partner"].create({"name": "Nobody"})._ocd_tz_name(), "Africa/Lome")
        self.assertIsNone(tools.valid_tz("Mars/Olympus"))

    def test_slots_in_the_time_of_the_person(self):
        slots = self.env["ocd.live.booking"]._ocd_get_day_slots(self.day, tz_name="Africa/Douala")
        self.assertEqual(slots[0]["code"], "0830", "The key of the hour stays the one of the studio")
        self.assertEqual((slots[0]["label"], slots[0]["end_label"]), ("09:30", "11:00"))
        self.assertEqual(slots[0]["local_day"], self.day)

    def test_whatsapp_labels_for_the_vendor_and_the_team(self):
        booking = self._book(self.starts[0], state="confirmed")
        self.assertEqual(booking._ocd_local_labels()[1], f"{tools.to_tz(booking.start_datetime, 'Africa/Douala'):%H:%M}")
        self.assertEqual(booking._ocd_studio_labels()[1], f"{tools.to_tz(booking.start_datetime, 'Africa/Lome'):%H:%M}")


@tagged("post_install", "-at_install")
class TestOcdLiveTicketPages(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write({"ocd_booking_open_date": False, "ocd_min_notice_hours": 2, "ocd_studio_tz": "Africa/Lome"})
        cls.vendor = cls.env["res.partner"].create({
            "name": "Awa Mensah",
            "ocd_is_vendor": True,
            "ocd_vendor_state": "approved",
            "phone": "+228 90 00 00 08",
            "country_id": cls.env.ref("base.tg").id,
        })
        cls.discovery = cls.env.ref("ocd_live.product_package_discovery").product_variant_id
        cls.day = fields.Date.today() + timedelta(days=6)
        start = cls.company._ocd_slot_starts(cls.day)[0]
        cls.order = cls.env["sale.order"].create({
            "partner_id": cls.vendor.id,
            "order_line": [fields.Command.create({"product_id": cls.discovery.id, "product_uom_qty": 1})],
        })
        cls.booking = cls.env["ocd.live.booking"].create({
            "partner_id": cls.vendor.id,
            "start_datetime": start,
            "slot_count": 1,
            "product_id": cls.discovery.id,
            "sale_line_id": cls.order.order_line[:1].id,
            "state": "confirmed",
        })
        cls.token = cls.order._portal_ensure_token()

    def _set_tz_cookie(self, tz_name):
        self.opener.cookies.set("tz", tz_name, domain="127.0.0.1", path="/")

    def test_ticket_page_pdf_and_announcement(self):
        booking, token = self.booking, self.token
        response = self.url_open(f"/ocd/ticket/{booking.id}?access_token={token}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(booking._ocd_ticket_seal(), response.text)
        self.assertIn(f"/ocd/ticket/{booking.id}/pdf?access_token={token}", response.text)
        self.assertIn('id="annonce"', response.text)
        self.assertNotIn("/report/barcode/QR/", response.text, "The QR code is signed, made by the server")
        pdf = self.url_open(f"/ocd/ticket/{booking.id}/pdf?access_token={token}")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf.headers["Content-Type"], "application/pdf")
        self.assertIn("no-store", pdf.headers["Cache-Control"], "Personal: no copy in a proxy")
        image = self.url_open(f"/ocd/ticket/{booking.id}/annonce?access_token={token}&telecharger=1")
        self.assertEqual(image.headers["Content-Type"], "image/png")
        self.assertIn("attachment", image.headers["Content-Disposition"])
        self.assertEqual(self.url_open(f"/ocd/ticket/{booking.id}/pdf?access_token=wrong").status_code, 404)
        self.assertEqual(self.url_open(f"/ocd/ticket/{booking.id}/annonce?access_token=wrong").status_code, 404)

    def test_check_at_the_entry(self):
        booking = self.booking
        signature = booking._ocd_ticket_signature()
        url = f"/ocd/ticket/verifier/{booking.id}/{signature}"
        response = self.url_open(url)
        self.assertIn("Valid ticket, for another day", response.text)
        self.assertNotIn(self.vendor.name, response.text, "Only the team sees who the ticket is for")
        self.assertIn("Ticket not valid", self.url_open(f"/ocd/ticket/verifier/{booking.id}/{'0' * 32}").text)
        live_day = datetime.combine(self.day, time(7, 0))
        with freeze_time(live_day):
            response = self.url_open(url)
            self.assertIn("Valid ticket", response.text)
            self.assertNotIn("Let in", response.text, "Only the team lets in")
            self.authenticate("admin", "admin")
            response = self.url_open(url)
            self.assertIn(self.vendor.name, response.text)
            self.assertIn("Let in", response.text)
            response = self.url_open(f"{url}/entree", data={"csrf_token": self.csrf_token()})
            self.assertIn("Have a good live", response.text)
            self.assertTrue(booking.ticket_checked_in)
            response = self.url_open(url)
            self.assertIn("Ticket already used", response.text)

    def test_hours_of_the_booking_in_the_time_of_the_phone(self):
        self._set_tz_cookie("Africa/Douala")
        response = self.url_open(f"/reserver/studio/{self.day.isoformat()}")
        self.assertEqual(response.status_code, 200)
        first = self.company._ocd_slot_starts(self.day)[1]
        self.assertIn(f"{tools.to_tz(first, 'Africa/Douala'):%H:%M}", response.text)
        self.assertIn(f"/reserver/studio/{self.day.isoformat()}/1000", response.text, "The hour of the studio in the address")
        self.assertIn(tools.zone_text(self.env, "Africa/Douala"), response.text)
        # The phone of the vendor gives its time zone, kept for the messages
        self.url_open(f"/ocd/espace/{self.vendor._ocd_get_space_token()}")
        self.url_open("/ocd/espace/moi")
        self.assertEqual(self.vendor.ocd_phone_tz, "Africa/Douala")

