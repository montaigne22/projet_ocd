from odoo.fields import Command
from odoo.tests import HttpCase, tagged
from odoo.tools import file_open
from odoo.tools.binary import BinaryBytes


@tagged("post_install", "-at_install")
class TestOcdSiteSetup(HttpCase):
    """The site is that of OCD Live from its installation: home of OCD Live on /, French, logo
    and name, footer without the examples of Odoo; what the team chose is kept."""

    def _read(self, path):
        with file_open(path, "rb") as file:
            return file.read()

    def _site_as_odoo_installs_it(self):
        english = self.env.ref("base.lang_en")
        return self.env["website"].create({
            "name": "My Website",
            "logo": BinaryBytes(self._read("website/static/src/img/website_logo.svg")),
            "language_ids": [Command.set(english.ids)],
            "default_lang_id": english.id,
        })

    def test_new_site_becomes_ocd_live(self):
        french = self.env["res.lang"]._activate_lang("fr_FR")
        website = self._site_as_odoo_installs_it()
        self.env["website"]._ocd_setup_site()
        self.assertEqual(website.homepage_url, "/ocd")
        self.assertEqual(website.default_lang_id, french)
        self.assertIn(french, website.language_ids)
        self.assertEqual(website.name, "OCD Live")
        self.assertEqual(website.logo.content, self._read("ocd_live/static/img/ocd_logo_round.png"))

    def test_menus_copied_in_english_are_translated(self):
        french = self.env["res.lang"]._activate_lang("fr_FR")
        source = self.env["website.menu"].create({
            "name": "Live studio", "url": "/ocd-test-studio", "parent_id": self.env.ref("website.main_menu").id,
        })
        source.with_context(lang=french.code).name = "Studio du live"
        website = self._site_as_odoo_installs_it()
        copied = self.env["website.menu"].create({
            "name": "Live studio", "url": "/ocd-test-studio", "parent_id": website.menu_id.id, "website_id": website.id,
        })
        renamed = self.env["website.menu"].create({
            "name": "Our studio", "url": "/ocd-test-studio", "parent_id": website.menu_id.id, "website_id": website.id,
        })
        self.env["website"]._ocd_setup_site()
        self.assertEqual(copied.with_context(lang=french.code).name, "Studio du live")
        self.assertEqual(renamed.with_context(lang=french.code).name, "Our studio")

    def test_choices_of_the_team_are_kept(self):
        website = self._site_as_odoo_installs_it()
        own_logo = BinaryBytes(self._read("ocd_live/static/description/icon.png"))
        website.write({"homepage_url": "/lives", "name": "OCD Togo", "logo": own_logo})
        self.env["website"]._ocd_setup_site()
        self.assertEqual(website.homepage_url, "/lives")
        self.assertEqual(website.name, "OCD Togo")
        self.assertEqual(website.logo.content, own_logo.content)

    def test_address_of_the_site_shows_the_home_of_ocd_live(self):
        self.assertEqual(self.env.ref("base.default_website").homepage_url, "/ocd")
        response = self.url_open("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("o_ocd_app", response.text)
        self.assertIn("/reserver/studio", response.text)

    def test_footer_without_the_examples_of_odoo(self):
        self.env.company.write({"phone": "+228 90 00 00 01", "email": "bonjour@ocd.example"})
        response = self.url_open("/contactus")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Useful Links", response.text)
        self.assertNotIn("info@yourcompany.example.com", response.text)
        self.assertNotIn('href="tel:+1 555-555-5556"', response.text)
        self.assertIn("tel:+228 90 00 00 01", response.text)
        self.assertIn("/ocd/connexion", response.text)
