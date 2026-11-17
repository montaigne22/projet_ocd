from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import Command, fields
from freezegun import freeze_time

from odoo.tests import HttpCase, tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdVendorFigures(HttpCase, OcdShopCommon):
    """The figures of the vendor (chantier 3, design MesChiffres, with 3.3 « Sales per product »):
    one calculation for « My figures », « My space », the line « Sold » of « My products » and the
    summary of the week on WhatsApp."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({"ocd_business_offered_all": True, "ocd_vendor_login": "link", "ocd_live_sales_hours": 3,
                           "ocd_loyal_orders": 2})
        cls.cameroon = cls.env.ref("base.cm")
        (cls.brenda | cls.fatou).write({"country_id": cls.cameroon.id})
        for product in (cls.dress, cls.butter):
            product.product_tmpl_id.write({"is_published": True, "ocd_review_state": "approved"})
        cls.Figures = cls.env["ocd.vendor.figures"]
        cls.Count = cls.env["ocd.vendor.count"]
        cls.PartnerClass = type(cls.env["res.partner"])

    def _post(self, url, **data):
        return self.url_open(url, data={"csrf_token": self.csrf_token(), **data})

    def _live(self, vendor, start, minutes=60):
        """A confirmed live of `vendor` from `start` (written directly: no slot needed)."""
        self._slot = getattr(self, "_slot", 0) + 1
        later = self.company._ocd_local_today() + timedelta(days=40 + self._slot)
        booking = self.env["ocd.live.booking"].create({
            "partner_id": vendor.id, "start_datetime": self.company._ocd_slot_starts(later)[0], "mode": "studio",
        })
        booking.state = "confirmed"
        self.env.cr.execute(
            "UPDATE ocd_live_booking SET start_datetime = %s, end_datetime = %s WHERE id = %s",
            [start, start + timedelta(minutes=minutes), booking.id],
        )
        booking.invalidate_recordset(["start_datetime", "end_datetime"])
        return booking

    def _draft(self, customer, lines):
        return self.env["sale.order"].create({
            "partner_id": customer.id,
            "order_line": [
                Command.create({"product_id": product.id, "product_uom_qty": qty, "tax_ids": [Command.clear()]})
                for product, qty in lines
            ],
        })

    def _ago(self, order, days):
        order.date_order = fields.Datetime.now() - timedelta(days=days)

    # === THE SALES === #

    def test_the_sales_without_the_cancelled_orders_nor_the_returned_parcels(self):
        self._order(self.estelle, [(self.dress, 2)])
        self._order(self.herve, [(self.dress, 1), (self.butter, 3)])  # each vendor their part
        cancelled = self._order(self.herve, [(self.dress, 5)])
        cancelled._action_cancel()
        returned = self._order(self.estelle, [(self.dress, 4)])
        self._parcel(returned, self.brenda).ocd_stage = "returned"
        before = self._order(self.estelle, [(self.dress, 1)])
        self._ago(before, 40)
        figures = self.Figures._ocd_figures(self.brenda, 30)
        self.assertEqual((figures["sales"]["pieces"], figures["sales"]["orders"], figures["sales"]["amount"]),
                         (3, 2, 36000.0), "Without the delivery, the cancelled order, the returned parcel")
        self.assertEqual(figures["pieces_line"], "2 orders")
        self.assertEqual(figures["amount_evolution"]["text"], "▲ 200 % compared with the 30 days before")
        self.assertEqual(self.Figures._ocd_figures(self.fatou, 30)["sales"]["pieces"], 3)
        self.assertEqual(self.Figures._ocd_figures(self.brenda, 7)["amount_evolution"]["text"], "▲ new")
        # The visits and the WhatsApp contacts, day by day
        for _visit in range(3):
            self.Count._ocd_add(self.brenda, "visit")
        self.Count._ocd_add(self.brenda, "contact", self.dress.product_tmpl_id.id)
        figures = self.Figures._ocd_figures(self.brenda, 30)
        self.assertEqual((figures["visits"], figures["contacts"]), (3, 1))
        self.assertEqual(figures["visits_evolution"]["text"], "▲ new")
        self.assertEqual(self.Figures._ocd_figures(self.fatou, 30)["visits"], 0)
        # The month of « My space »
        self.assertIn("· 3 pieces", self.Figures._ocd_month(self.brenda)["line"])

    def test_the_sales_of_a_live(self):
        now = fields.Datetime.now()
        live = self._live(self.brenda, now - timedelta(minutes=30), minutes=60)
        old = self._live(self.brenda, now - timedelta(days=3), minutes=60)
        # Came to the boutique during the live, then ordered: the lines of Brenda count for it
        order = self._draft(self.estelle, [(self.dress, 2), (self.butter, 1)])
        order._ocd_note_lives(live | old)
        self.assertEqual(order.ocd_live_seen_ids, live, "The old live no longer counts")
        order.action_confirm()
        brenda_line = order.order_line.filtered(lambda line: line.ocd_vendor_id == self.brenda)
        self.assertEqual(brenda_line.ocd_live_id, live)
        self.assertFalse((order.order_line - brenda_line).ocd_live_id, "Fatou had no live")
        # Bought without the live
        self._order(self.herve, [(self.dress, 1)])
        self.Count._ocd_add(self.brenda, "watch", live.id)
        self.Count._ocd_add(self.brenda, "watch", live.id)
        self.env["ocd.vendor.follower"]._ocd_follow(self.brenda, self.herve)
        figures = self.Figures._ocd_figures(self.brenda, 7)
        rows = {row["booking"]: row for row in figures["lives"]}
        self.assertEqual((rows[live]["opened"], rows[live]["pieces"], rows[live]["followers"], rows[live]["star"]),
                         ("2", 2, "+1", "Robe en wax"))
        self.assertTrue(rows[live]["best"])
        self.assertFalse(rows[old]["best"])
        self.assertEqual(rows[old]["pieces_text"], "0 pieces")
        self.assertTrue(figures["idea"].startswith("67 % of your sales come from your lives."), figures["idea"])
        self.assertIn("alone made 67 % of these 7 days", figures["idea"])
        # In the hours after the live (setting), not later
        self.assertTrue(live._ocd_sales_open(live.end_datetime + timedelta(hours=2)))
        self.assertFalse(live._ocd_sales_open(live.end_datetime + timedelta(hours=4)))

    def test_the_loyal_customers_the_best_hours_and_the_products(self):
        for days in (2, 20, 100):
            self._ago(self._order(self.estelle, [(self.dress, 1)]), days)
        self._order(self.herve, [(self.dress, 1)])
        loyal = self.Figures._ocd_figures(self.brenda, 30)["loyal"]
        self.assertEqual([row["name"] for row in loyal["rows"]], ["Estelle N."], "First name and initial only")
        self.assertEqual(loyal["rows"][0]["line"].split(" · ")[0], "3 orders")
        self.assertEqual(loyal["line"], "1 customer bought 2 times or more: 75 % of your sales.")
        self.assertNotIn("670000000", str(loyal), "Never their number")
        self.company.ocd_loyal_orders = 4
        self.assertFalse(self.Figures._ocd_figures(self.brenda, 30)["loyal"]["rows"])
        # The best hours: the orders at the hour of the vendor
        hours = self.Figures._ocd_figures(self.brenda, 30)["hours"]
        self.assertEqual(sum(cell["count"] for row in hours["rows"] for cell in row["cells"]), 3, "3 months")
        self.assertTrue(hours["line"].startswith("Your customers buy mostly on "))
        self.assertTrue(hours["book"]["label"].startswith("Book a live on "))
        # The products (3.3): sold, not sold with a lot of interest
        scarf = self._product("Foulard", 3000, self.brenda).product_tmpl_id
        scarf.write({"is_published": True, "ocd_review_state": "approved"})
        for _contact in range(5):
            self.Count._ocd_add(self.brenda, "contact", scarf.id)
        rows = {row["product"]: row for row in self.Figures._ocd_figures(self.brenda, 30)["products"]}
        line = rows[self.dress.product_tmpl_id]["line"]
        self.assertTrue(line.startswith("3 sold · ") and line.endswith(" · last sale today"), line)
        self.assertEqual(rows[self.dress.product_tmpl_id]["pieces"], 3)
        self.assertEqual(rows[scarf]["line"], "0 sold in 30 days")
        self.assertTrue(rows[scarf]["interest"])
        self.assertEqual(rows[scarf]["facts"], "5 WhatsApp contacts")
        # The line « Sold » of « My products »: the same calculation
        sales = self.Figures._ocd_product_sales(self.brenda, self.dress.product_tmpl_id | scarf)
        self.assertEqual(sales[scarf.id], (0, None))
        pieces, last = sales[self.dress.product_tmpl_id.id]
        self.assertEqual(self.Figures._ocd_sold_line(self.brenda, pieces, last), "Sold: 3 in 30 days · last sale today")
        self.assertFalse(self.Figures._ocd_sold_line(self.brenda, 0, None))

    def test_the_stores(self):
        akwa = self.akwa
        store = self.env["ocd.vendor.place"].sudo().create({
            "vendor_id": self.brenda.id, "name": "Brenda Wax Akwa", "kind": "store", "city_id": akwa.city_id.id,
            "district_id": akwa.id, "state": "approved",
        })
        Tap = self.env["ocd.vendor.place.tap"].sudo()
        Tap.create([{"place_id": store.id, "kind": kind} for kind in ("itinerary", "itinerary", "call")])
        order = self._order(self.estelle, [(self.dress, 1)])
        parcel = self._parcel(order, self.brenda)
        parcel.write({"ocd_pickup_place_id": store.id, "ocd_picked_at": fields.Datetime.now()})
        rows = self.Figures._ocd_figures(self.brenda, 30)["stores"]
        self.assertEqual(rows[0]["taps"], "2 itineraries · 1 call · 0 WhatsApp")
        self.assertEqual(rows[0]["parcels"], "0 pick-ups at the counter · 1 parcel left from here")
        self.assertEqual(store._ocd_week_taps()[store.id], {"itinerary": 2, "call": 1, "whatsapp": 0}, "The same count")

    # === THE COUNTS OF THE PAGES === #

    def test_the_boutique_counts_one_visit_a_day_and_the_contacts(self):
        self.brenda.phone = "+237 690000001"
        self.authenticate(None, None)
        page = self.url_open(f"/ocd/boutique/{self.brenda.id}").text
        self.assertIn(f'data-visit="{self.brenda.id}"', page, "The page tells the visit once shown")
        today = fields.Date.today()
        self.assertEqual(self.Count._ocd_totals(self.brenda, "visit", today - timedelta(days=1), today + timedelta(days=1)),
                         0, "The page itself counts nothing: it stays the same for everyone")
        for _visit in range(2):
            self.assertEqual(self.url_open(f"/ocd/boutique/{self.brenda.id}/vu", data={"vu": "1"}).status_code, 204)
        self.assertEqual(self.Count._ocd_totals(self.brenda, "visit", today - timedelta(days=1), today + timedelta(days=1)),
                         1, "One per phone and per day")
        response = self.url_open(f"/ocd/wa/{self.dress.product_tmpl_id.id}", allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        totals = self.Count._ocd_totals(self.brenda, "contact", today - timedelta(days=1), today + timedelta(days=1),
                                        by_record=True)
        self.assertEqual(totals, {self.dress.product_tmpl_id.id: 1})
        # « Watch » of the boutique during a live: counted, then the live
        live = self._live(self.brenda, fields.Datetime.now() - timedelta(minutes=10))
        live.live_url = "https://www.tiktok.com/@brendawax/live"
        page = self.url_open(f"/ocd/boutique/{self.brenda.id}").text
        self.assertIn(f"/ocd/regarder/{live.id}?d=boutique", page)
        response = self.url_open(f"/ocd/regarder/{live.id}?d=boutique", allow_redirects=False)
        self.assertEqual(response.headers["Location"], "https://www.tiktok.com/@brendawax/live")
        self.assertEqual(self.Count._ocd_record_totals(self.brenda, "watch", [live.id]), {live.id: 1})

    # === THE PAGE === #

    def test_my_figures_with_and_without_ocd_business(self):
        self._order(self.estelle, [(self.dress, 2)])
        live = self._live(self.brenda, fields.Datetime.now() - timedelta(days=2))
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        page = self.url_open("/ocd/espace/moi/chiffres").text
        for text in ("My figures", "Visits of your boutique", "Opened from OCD", "My best hours", "My loyal customers",
                     "Sales per product", "Receive the summary of my week", "o_ocd_figures_heat"):
            self.assertIn(text, page)
        self.assertIn("/reserver/", page, "Book a live on the best hour")
        self.assertIn("670000000", self.estelle.phone)
        self.assertNotIn("670000000", page, "Never the numbers of the customers")
        page = self.url_open("/ocd/espace/moi/chiffres?periode=7&vue=pas-vendus").text
        self.assertIn('aria-current="true">7 days', page.replace("\n", ""))
        # My space and My products: for every vendor
        self.assertIn("This month:", self.url_open("/ocd/espace/moi").text)
        self.assertIn("Sold: 2 in 30 days · last sale ", self.url_open("/ocd/espace/moi/produits").text)
        # The summary of the week, asked for
        response = self._post("/ocd/espace/moi/chiffres/resume", actif="1")
        self.assertIn("your week arrives on WhatsApp", response.text)
        self.assertTrue(self.brenda.ocd_week_summary)
        self._post("/ocd/espace/moi/chiffres/resume")
        self.assertFalse(self.brenda.ocd_week_summary)
        # « Add to my next live »: the products prepared for it (chantier 21)
        later = self._live(self.brenda, fields.Datetime.now() + timedelta(days=2))
        response = self._post(f"/ocd/espace/moi/chiffres/live/{self.dress.product_tmpl_id.id}")
        self.assertTrue(response.url.endswith(f"/ocd/espace/moi/live/{later.id}"))
        self.assertEqual(later._ocd_prepared_products(), self.dress.product_tmpl_id)
        self.assertEqual(self._post(f"/ocd/espace/moi/chiffres/live/{self.butter.product_tmpl_id.id}").status_code, 404,
                         "Not their product")
        self.assertTrue(live)
        # Without OCD Business: the sales and the pieces, then the detail announced
        self.company.ocd_business_offered_all = False
        page = self.url_open("/ocd/espace/moi/chiffres?periode=7").text
        self.assertIn("The detail with OCD Business", page)
        self.assertIn("Sales, 30 days", page)
        self.assertNotIn("My best hours", page)
        self.assertNotIn("o_ocd_figures_lives", page)

    def test_the_team_opens_the_figures_of_a_vendor(self):
        admin = self.env.ref("base.user_admin")
        admin.group_ids |= self.env.ref("ocd_live.group_ocd_live_user")
        action = self.brenda.with_user(admin).action_ocd_view_figures()
        self.assertIn(f"/ocd/espace/equipe/{self.brenda.id}?signature=", action["url"])
        self.assertTrue(action["url"].endswith("&vers=chiffres"))
        self.authenticate("admin", "admin")
        response = self.url_open(action["url"])
        self.assertTrue(response.url.split("?")[0].endswith("/ocd/espace/moi/chiffres"), response.url)
        self.assertIn("My figures", response.text)
        sections = str(self.env["ocd.live.settings"]._ocd_sections())
        for text in ("Sales of a live", "Loyal customers", "Summary of the week on WhatsApp"):
            self.assertIn(text, sections)

    # === THE SUMMARY OF THE WEEK === #

    def test_the_summary_of_the_week_on_monday_when_asked(self):
        monday = datetime(2026, 11, 23, 8, 30)  # 9:30 in Douala
        self.assertFalse(self.brenda._ocd_week_summary_due(monday), "Only when asked for")
        self.brenda.ocd_week_summary = True
        self.assertTrue(self.brenda._ocd_week_summary_due(monday))
        self.assertFalse(self.brenda._ocd_week_summary_due(monday - timedelta(hours=1)), "From 9:00")
        self.assertFalse(self.brenda._ocd_week_summary_due(monday + timedelta(days=1)), "On Monday")
        with freeze_time(monday - timedelta(days=2)):
            self._order(self.estelle, [(self.dress, 2)])
            self.Count._ocd_add(self.brenda, "visit")
        told = []
        with patch.object(self.PartnerClass, "_ocd_tell_week_summary", lambda vendors, summary: told.append((vendors, summary))):
            self.env["res.partner"]._ocd_send_week_summaries(monday)
            self.env["res.partner"]._ocd_send_week_summaries(monday + timedelta(hours=1))
        self.assertEqual(len(told), 1, "Once a day")
        vendor, summary = told[0]
        self.assertEqual(vendor, self.brenda)
        self.assertEqual((summary["pieces"], summary["amount"], summary["visits"], summary["best"]),
                         (2, 24000.0, 1, self.dress.product_tmpl_id))
        words = self.Figures._ocd_week_values(self.brenda, summary, "en_US")
        self.assertEqual((words["trend"], words["best"]), ("up", "Robe en wax"))
        self.assertEqual(self.Figures._ocd_week_values(self.brenda, dict(summary, percent=12), "en_US")["trend"], "up 12 %")
        # Nothing happened: nothing sent
        self.assertIsNone(self.Figures._ocd_week_summary(self.fatou, monday))
        # The team pauses it in the automations
        self.brenda.ocd_week_summary_sent_at = False
        self.env.ref("ocd_live_shop.ir_cron_week_summary").active = False
        told.clear()
        with patch.object(self.PartnerClass, "_ocd_tell_week_summary", lambda vendors, summary: told.append(vendors)):
            self.env["res.partner"]._ocd_send_week_summaries(monday)
        self.assertEqual(told, [])
