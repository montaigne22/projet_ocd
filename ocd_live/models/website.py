from odoo import api, models
from odoo.fields import Command
from odoo.tools import file_open
from odoo.tools.binary import BinaryBytes

ODOO_LOGO = "website/static/src/img/website_logo.svg"
OCD_LOGO = "ocd_live/static/img/ocd_logo_round.png"
ODOO_WEBSITE_NAMES = ("My Website", "Website")


class Website(models.Model):
    _inherit = "website"

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
