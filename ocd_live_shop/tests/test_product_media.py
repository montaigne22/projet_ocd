import base64
import io
import json
import re
from html import unescape
from unittest.mock import patch

from PIL import Image

from odoo import Command
from odoo.tests import HttpCase, tagged
from odoo.tools import BinaryBytes

from .test_website import TestOcdShopWebsite

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def other_png(colour="red"):
    """Another small photo (not the main one)."""
    output = io.BytesIO()
    Image.new("RGB", (4, 4), colour).save(output, format="PNG")
    return output.getvalue()


@tagged("post_install", "-at_install")
class TestOcdProductMedia(TestOcdShopWebsite):
    """Photos of a product (gallery, viewer, photo of a colour), « Tell me when it is back »,
    and the replay that plays in the page."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Attribute = cls.env["product.attribute"]
        cls.colour = Attribute.create({
            "name": "Couleur", "display_type": "color", "create_variant": "always",
            "value_ids": [Command.create({"name": "Bleu", "html_color": "#1F4E9C"}),
                          Command.create({"name": "Rouge", "html_color": "#B22222"})],
        })
        cls.size = Attribute.create({
            "name": "Taille", "create_variant": "always",
            "value_ids": [Command.create({"name": "S"}), Command.create({"name": "L"})],
        })
        cls.robe = cls.env["product.template"].create({
            "name": "Robe test", "list_price": 12000, "type": "consu", "is_storable": True,
            "allow_out_of_stock_order": False, "ocd_vendor_id": cls.brenda.id, "is_published": True,
            "ocd_review_state": "approved", "image_1920": BinaryBytes(PNG), "taxes_id": [Command.clear()],
            "attribute_line_ids": [
                Command.create({"attribute_id": cls.colour.id, "value_ids": [Command.set(cls.colour.value_ids.ids)]}),
                Command.create({"attribute_id": cls.size.id, "value_ids": [Command.set(cls.size.value_ids.ids)]}),
            ],
        })
        cls.stock = cls.env.ref("stock.warehouse0").lot_stock_id
        for variant in cls.robe.product_variant_ids:
            names = set(variant.product_template_attribute_value_ids.mapped("name"))
            if "S" in names:
                cls.env["stock.quant"]._update_available_quantity(variant, cls.stock, 5)

    def _value(self, name):
        return self.robe.attribute_line_ids.product_template_value_ids.filtered(lambda value: value.name == name)

    def _variant(self, *names):
        return self.robe.product_variant_ids.filtered(
            lambda variant: set(names) <= set(variant.product_template_attribute_value_ids.mapped("name"))
        )

    def _data(self, html):
        return json.loads(unescape(re.search(r'data-variants="([^"]+)"', html).group(1)))

    def test_photo_of_a_colour_and_the_gallery(self):
        red = self._value("Rouge")
        red.ocd_image = BinaryBytes(PNG)
        self.env["product.image"].create({"name": "Back", "product_tmpl_id": self.robe.id, "image_1920": BinaryBytes(other_png())})
        response = self.url_open(self.robe.website_url)
        data = self._data(response.text)
        for variant in data["variants"]:
            if red.id in variant["values"]:
                self.assertIn("product.template.attribute.value", variant["photo"]["src"], "The photo of the red")
            else:
                self.assertIsNone(variant["photo"], "The other colours: the main photo")
        self.assertTrue(data["main"])
        self.assertEqual(len(data["extras"]), 1, "The other photos of the product")
        self.assertIn("o_ocd_viewer", response.text)
        self.assertEqual(self.url_open(data["variants"][0]["photo"] and data["variants"][0]["photo"]["src"] or
                                       next(v["photo"]["src"] for v in data["variants"] if v["photo"])).status_code, 200,
                         "The photo of a colour opens for the visitors")
        # The address gives the colour: the red is chosen, its photo first
        response = self.url_open(f"{self.robe.website_url}?v={red.id}")
        self.assertRegex(response.text, rf'value="{red.id}"\s+checked="checked"')
        self.assertIn("product.template.attribute.value", re.search(r'o_ocd_gallery_slide[^>]*>\s*<img[^>]*src="([^"]+)"', response.text).group(1))

    def test_sold_out_choice_tells_when_it_is_back(self):
        red_l = self._variant("Rouge", "L")
        response = self.url_open(f"{self.robe.website_url}?v={','.join(map(str, red_l.product_template_attribute_value_ids.ids))}")
        self.assertIn("Rouge, L: sold out for now.", response.text)
        self.authenticate(None, None)
        response = self.url_open("/ocd/produit/prevenir", data={
            "csrf_token": self.csrf_token(), "product_id": red_l.id,
            "country_id": self.env.ref("base.cm").id, "phone": "6 70 00 00 09",
        })
        self.assertIn("as soon as it is back", response.text)
        alert = self.env["ocd.stock.alert"].search([("product_id", "=", red_l.id)])
        self.assertEqual((alert.state, alert.partner_id.phone), ("waiting", "+237 670000009"))
        self.assertIn(f"?v={red_l.product_template_attribute_value_ids.sorted('id')[0].id}", alert._ocd_product_path())
        self.assertEqual(alert._ocd_variant_label(), "Rouge, L")
        sent = []
        Alert = type(self.env["ocd.stock.alert"])
        with patch.object(Alert, "_ocd_send_product_back", lambda alerts: sent.extend(alerts.ids)):
            self.env["ocd.stock.alert"]._ocd_send_back()
            self.assertFalse(sent, "Still sold out")
            self.env["stock.quant"]._update_available_quantity(red_l, self.stock, 2)
            self.env["ocd.stock.alert"]._ocd_send_back()
        self.assertEqual(sent, alert.ids)
        self.assertEqual(alert.state, "sent")
        # A product removed from the shop ends its alerts
        other = self.env["ocd.stock.alert"]._ocd_register(self._variant("Bleu", "L"), phone="+237 670000009")
        self._variant("Bleu", "L").active = False
        self.env["ocd.stock.alert"]._ocd_send_back()
        self.assertEqual(other.state, "cancelled")

    def test_vendor_adds_the_photo_of_a_colour(self):
        self.company.ocd_vendor_login = "link"
        self.authenticate(None, None)
        self.url_open(f"/ocd/espace/{self.brenda._ocd_get_space_token()}")
        page = self.url_open("/ocd/espace/moi/produits")
        self.assertIn("Photos of the colours", page.text)
        red = self._value("Rouge")
        response = self.url_open(f"/ocd/espace/moi/produits/{self.robe.id}/couleur/{red.id}",
                                 data={"csrf_token": self.csrf_token()}, files={"photo": ("rouge.png", PNG, "image/png")})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(red.ocd_image)
        other = self.env["product.template"].create({"name": "Pagne", "ocd_vendor_id": self.fatou.id})
        value = self._value("Bleu")
        response = self.url_open(f"/ocd/espace/moi/produits/{other.id}/couleur/{value.id}",
                                 data={"csrf_token": self.csrf_token()}, files={"photo": ("bleu.png", PNG, "image/png")})
        self.assertEqual(response.status_code, 404, "Only the photos of its own products")

    def test_replay_plays_in_the_page(self):
        self.authenticate(None, None)
        booking = self._live_now(self.brenda, replay_url="https://youtu.be/dQw4w9WgXcQ")
        self.env.cr.execute(
            "UPDATE ocd_live_booking SET start_datetime = start_datetime - interval '2 days', "
            "end_datetime = end_datetime - interval '2 days' WHERE id = %s", [booking.id],
        )
        booking.invalidate_recordset(["start_datetime", "end_datetime"])
        Moment = self.env["ocd.live.moment"]
        Moment.create({"booking_id": booking.id, "product_tmpl_id": self.dress.product_tmpl_id.id, "offset_seconds": 240})
        Moment.create({
            "booking_id": booking.id, "product_tmpl_id": self.robe.id, "offset_seconds": 1260,
            "product_id": self._variant("Rouge", "S").id,
        })
        booking.replay_published = True
        response = self.url_open(f"/ocd/boutique/{self.brenda.id}/replay?live={booking.id}&t=1300")
        self.assertIn('data-platform="youtube"', response.text)
        self.assertIn('data-video="dQw4w9WgXcQ"', response.text)
        self.assertEqual(response.text.count('class="o_ocd_player_mark"'), 2, "A mark per product on the bar")
        self.assertIn('class="o_ocd_moment o_ocd_on" data-seconds="1260"', response.text, "The product on screen at 21:40")
        self.assertIn("?v=", unescape(re.search(r'data-order-url="([^"]*robe-test[^"]*)"', response.text).group(1)),
                      "The colour shown in the live")
        # The product page says where it was seen
        page = self.url_open(self.robe.website_url)
        self.assertIn(f"/replay?live={booking.id}&amp;t=1260", page.text)
        # « Tell me » the next live, from the replay
        response = self.url_open(f"/ocd/boutique/{self.brenda.id}/prevenir", data={
            "csrf_token": self.csrf_token(), "replay": booking.id,
            "country_id": self.env.ref("base.cm").id, "phone": "6 70 00 00 08",
        })
        self.assertIn(f"/replay?live={booking.id}&noted=1", response.url)

    def test_replay_links_of_the_platforms(self):
        booking = self._live_now(self.brenda)
        cases = {
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10": ("youtube", "dQw4w9WgXcQ", True),
            "https://youtu.be/dQw4w9WgXcQ": ("youtube", "dQw4w9WgXcQ", True),
            "https://www.youtube.com/live/dQw4w9WgXcQ?si=x": ("youtube", "dQw4w9WgXcQ", True),
            "https://www.tiktok.com/@brenda.wax/video/7400000000000000001": ("tiktok", "7400000000000000001", True),
            "https://www.facebook.com/brendawax/videos/123456789/": ("facebook", "https://www.facebook.com/brendawax/videos/123456789/", True),
            "https://www.instagram.com/reel/Cabc123/": ("instagram", "", False),
            "https://vm.tiktok.com/ZMabc/": ("", "", False),
            "https://example.com/video": ("", "", False),
        }
        for url, (platform, video, seek) in cases.items():
            booking.replay_url = url
            embed = booking._ocd_replay_embed()
            self.assertEqual((embed["platform"], embed["id"], embed["seek"]), (platform, video, seek), url)
        Moment = self.env["ocd.live.moment"]
        self.assertEqual(Moment._ocd_time_label(240), "04:00")
        self.assertEqual(Moment._ocd_time_label(3930), "1:05:30")
