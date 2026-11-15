from odoo import api, fields, models
from odoo.fields import Command
from odoo.tools import file_open
from odoo.tools.binary import BinaryBytes

ODOO_LOGO = "website/static/src/img/website_logo.svg"
OCD_LOGO = "ocd_live/static/img/ocd_logo_round.png"
ODOO_WEBSITE_NAMES = ("My Website", "Website")
# Photos and videos of the cards of the lives, sent by the CDN with the files of Odoo
OCD_CDN_FILTERS = ("^/lives/image/", "^/lives/carte/", "^/lives/video/")


class Website(models.Model):
    _inherit = "website"

    ocd_page_cache = fields.Boolean(
        "Pages Kept In Memory",
        default=True,
        help="The public pages (feed of the lives, page of a live, boutiques, products) are built once, "
        "then given to the next visitors for a few seconds.",
    )

    def _ocd_set_cdn(self, url):
        """Send the files, the photos and the videos of the site by the CDN at `url` (empty:
        by the server): the filters of Odoo get the ones of the cards of the lives."""
        for website in self:
            values = {"cdn_url": url or "", "cdn_activated": bool(url)}
            if url:
                filters = [line for line in (website.cdn_filters or "").splitlines() if line.strip()]
                values["cdn_filters"] = "\n".join(filters + [f for f in OCD_CDN_FILTERS if f not in filters])
            website.write(values)

    def _ocd_cdn_url(self, url):
        """`url` sent by the CDN when the site has one and it is a file of its filters (the
        sources and the posters of the videos, which Odoo does not change by itself)."""
        self.ensure_one()
        return self.get_cdn_url(url) if url and self.cdn_activated else url

    @api.model
    def _ocd_setup_site(self):
        """Make the site that of OCD Live where it is still as Odoo installs it:

        - the address of the site (/) shows the home of OCD Live (/ocd) and no more the empty
          page of Odoo;
        - French is the language of the visitors when it is installed;
        - logo and name of OCD Live in place of "Your Logo" and "My Website";
        - the menus that Odoo copied for the site in English ("Home", "Shop", "Jobs") get the
          translations of the menus they were copied from.

        What the team has already chosen (another home page or language, its logo, its name) is
        kept: this is run when the module is installed and once when it is updated."""
        with file_open(ODOO_LOGO, "rb") as file:
            odoo_logo = file.read()
        with file_open(OCD_LOGO, "rb") as file:
            ocd_logo = file.read()
        french = self.env["res.lang"].search([("code", "=", "fr_FR")], limit=1)
        for website in self.sudo().search([]):
            values = {}
            if not website.homepage_url or website.homepage_url == "/":
                values["homepage_url"] = "/ocd"
            if french and website.default_lang_id.code == "en_US":
                values["language_ids"] = [Command.link(french.id)]
                values["default_lang_id"] = french.id
            if not website.logo or website.logo.content == odoo_logo:
                values["logo"] = BinaryBytes(ocd_logo, filename="ocd_logo.png")
            if website.name in ODOO_WEBSITE_NAMES:
                values["name"] = "OCD Live"
            if values:
                website.write(values)
            website._ocd_translate_menus()

    def _ocd_translate_menus(self):
        """Odoo copies its menus for each site with the languages installed at that time: a site
        made before French was installed shows "Home", "Shop", "Jobs" in English to the French
        visitors. Give them the translations of the menu they were copied from, unless the team
        renamed them."""
        Menu = self.env["website.menu"].sudo()
        languages = [code for code, _name in self.env["res.lang"].get_installed() if code != "en_US"]
        sources = {}
        for source in Menu.search([("website_id", "=", False), ("parent_id", "!=", False)], order="id"):
            sources.setdefault(source.url, source)
        # A language loaded on an existing database from the command line (--load-language) is
        # loaded before the models of the site: the menus of Odoo then have no translation. Load
        # the texts of the modules that made them again, without changing what is translated.
        untranslated = Menu.browse([
            source.id for source in sources.values()
            if any(source.with_context(lang=code).name == source.with_context(lang="en_US").name for code in languages)
        ])
        modules = {
            xmlid.split(".")[0] for xmlids in untranslated._get_external_ids().values() for xmlid in xmlids
        }
        if modules:
            self.env["ir.module.module"]._load_module_terms(sorted(modules), languages)
            Menu.invalidate_model(["name"])
        for menu in Menu.search([("website_id", "in", self.ids)]):
            source = sources.get(menu.url) if menu.url and menu.url != "#" else None
            english = menu.with_context(lang="en_US").name
            if not source or source.with_context(lang="en_US").name != english:
                continue
            for code in languages:
                translated = source.with_context(lang=code).name
                # an empty translation (left by Odoo when the menu it copied had none yet) or the
                # English name: not translated
                current = menu.with_context(lang=code).name
                if translated and translated != english and (not current or current == english):
                    menu.with_context(lang=code).name = translated
