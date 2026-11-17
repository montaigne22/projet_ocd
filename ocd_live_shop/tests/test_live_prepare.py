from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged

from .common import OcdShopCommon


@tagged("post_install", "-at_install")
class TestOcdLivePrepare(HttpCase, OcdShopCommon):
    """Prepare the next live (chantier 21, 3.2 of the plan of « My products », design
    PreparerLive): the products ticked by the vendor, in their order, first in the control room."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.ocd_vendor_login = "link"
        cls.coat = cls._product("Veste", 20000, cls.brenda)
        cls.bag = cls._product("Sac en raphia", 8000, cls.brenda)
        for product in (cls.dress, cls.coat, cls.bag):
            product.product_tmpl_id.write({"is_published": True, "ocd_review_state": "approved"})
        cls.booking = cls.env["ocd.live.booking"].create({
            "partner_id": cls.brenda.id,
            "start_datetime": cls.company._ocd_slot_starts(fields.Date.today() + timedelta(days=5))[0],
            "mode": "remote",
        })
        cls.booking._ocd_confirm()

    def test_the_control_room_shows_them_first(self):
        Regie = self.env["ocd.live.regie"]
        data = Regie.get_regie_data(self.booking.id)
        self.assertEqual(data["prepared"], [], "Nothing prepared: all the products, as before")
        self.assertEqual(len(data["products"]), 3)
        dress, coat, bag = (p.product_tmpl_id for p in (self.dress, self.coat, self.bag))
        self.booking._ocd_prepare(bag | coat, "  Je commence par le sac  ")
        data = Regie.get_regie_data(self.booking.id)
        self.assertEqual([(tile["id"], tile["number"]) for tile in data["prepared"]], [(bag.id, 1), (coat.id, 2)])
        self.assertEqual([tile["id"] for tile in data["products"]], [dress.id])
        self.assertIn("« Je commence par le sac »", data["host_note"])
        self.assertIn("· 2", data["prepared_title"])
        # A product taken off sale leaves the list; another vendor's product is refused
        coat.ocd_vendor_retired = True
        self.assertEqual(self.booking._ocd_prepared_products(), bag)
        with self.assertRaises(UserError):
            self.booking._ocd_prepare(self.butter.product_tmpl_id)
        # Done: no longer prepared
        self.booking.state = "done"
        with self.assertRaisesRegex(UserError, "over"):
            self.booking._ocd_prepare(bag)

    def test_the_page_of_the_vendor(self):
        dress, coat, bag = (p.product_tmpl_id for p in (self.dress, self.coat, self.bag))
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        page = self.url_open("/ocd/espace/moi").text
        self.assertIn("No product prepared", page)
        self.assertIn(f"/ocd/espace/moi/live/{self.booking.id}", page)
        response = self.url_open("/ocd/espace/moi/live", allow_redirects=False)
        self.assertTrue(response.headers["Location"].endswith(f"/ocd/espace/moi/live/{self.booking.id}"))
        page = self.url_open(f"/ocd/espace/moi/live/{self.booking.id}").text
        self.assertIn("Sac en raphia", page)
        self.assertIn('name="coches"', page)
        base = f"/ocd/espace/moi/live/{self.booking.id}"
        # Ticked: dress, bag, coat; the order kept says coat first, the others follow the list
        data = {"csrf_token": self.csrf_token(), "coches": [dress.id, bag.id, coat.id], "ordre": str(coat.id),
                "note": "Promo sur les robes"}
        response = self.url_open(base, data=data, allow_redirects=False)
        self.assertTrue(response.headers["Location"].endswith(f"/ocd/espace/moi?pret={self.booking.id}"))
        self.assertEqual(self.booking._ocd_prepared_products().ids[0], coat.id)
        self.assertEqual(set(self.booking._ocd_prepared_products().ids), {dress.id, bag.id, coat.id})
        self.assertEqual(self.booking.ocd_host_note, "Promo sur les robes")
        # ↓ without JavaScript: the first goes down one place, the page comes back
        order = ",".join(map(str, self.booking._ocd_prepared_products().ids))
        response = self.url_open(base, data={**data, "ordre": order, "descendre": coat.id}, allow_redirects=False)
        self.assertIn("#dans-mon-live", response.headers["Location"])
        self.assertEqual(self.booking._ocd_prepared_products().ids[1], coat.id)
        page = self.url_open("/ocd/espace/moi?pret=1").text
        self.assertIn("It is ready", page)
        self.assertIn("3 products ready", page)
        # Another vendor's live: not found
        other = self.env["ocd.live.booking"].create({
            "partner_id": self.fatou.id,
            "start_datetime": self.company._ocd_slot_starts(fields.Date.today() + timedelta(days=5))[2],
            "mode": "remote",
        })
        self.assertEqual(self.url_open(f"/ocd/espace/moi/live/{other.id}").status_code, 404)
