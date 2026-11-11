import unicodedata

from odoo import api, fields, models
from odoo.exceptions import AccessError

from .. import countries


def _sort_key(country):
    """Name without accents, for the order of the lists: Égypte with the E."""
    return unicodedata.normalize("NFKD", country.name or "").encode("ascii", "ignore").decode().lower()


class ResCountry(models.Model):
    _inherit = "res.country"

    ocd_offered = fields.Boolean(
        string="Offered by OCD Live",
        help="The vendors, the couriers and the customers of this country choose it in the forms "
        "(WhatsApp number, directory). At the installation: every country of Africa and the best "
        "known of Europe, the Americas and Asia.",
    )
    ocd_continent = fields.Selection(
        selection=[
            ("africa", "Africa"),
            ("europe", "Europe"),
            ("americas", "Americas"),
            ("asia", "Asia"),
            ("oceania", "Oceania"),
        ],
        string="Continent",
        compute="_compute_ocd_continent",
        store=True,
    )

    @api.depends("code")
    def _compute_ocd_continent(self):
        for country in self:
            country.ocd_continent = countries.continent(country.code)

    @api.model
    def _ocd_offered(self):
        """The countries offered by the team; the ones of the installation when none is."""
        Country = self.sudo()
        return Country.search([("ocd_offered", "=", True)]) or Country.search(
            [("code", "in", countries.DEFAULT_OFFERED)]
        )

    @api.model
    def _ocd_ordered(self, first=None):
        """The offered countries in the order of the lists: `first` (the one of the person), the
        countries where OCD Live started, then each continent by name. Return (country, group)
        pairs, the group being "first" or the continent."""
        offered = self._ocd_offered()
        if first and first not in offered:
            offered |= first
        main = [code for code in countries.MAIN_COUNTRIES]
        head = (first or self.browse()) | offered.filtered(lambda c: c.code in main).sorted(
            lambda c: main.index(c.code)
        )
        rows = [(country, "first") for country in head]
        rest = (offered - head).sorted(_sort_key)
        for continent in countries.CONTINENTS:
            rows += [(country, continent) for country in rest if country.ocd_continent == continent]
        return rows

    def _ocd_check_manager(self):
        if not self.env.user.has_group("ocd_live.group_ocd_live_manager"):
            raise AccessError(self.env._("Only a manager of OCD Live chooses the countries."))

    def action_ocd_offer(self):
        """Offer the countries in the forms of the website (managers of OCD Live)."""
        self._ocd_check_manager()
        self.sudo().ocd_offered = True
        return True

    def action_ocd_withdraw(self):
        """Withdraw the countries from the forms; the contacts of these countries keep theirs."""
        self._ocd_check_manager()
        self.sudo().ocd_offered = False
        return True

    @api.model
    def _ocd_set_default_offered(self):
        """Offer the countries of the installation, and the ones of the vendors already known,
        when no country is offered yet (the choices of the team are kept)."""
        Country = self.sudo()
        if Country.search_count([("ocd_offered", "=", True)], limit=1):
            return
        known = self.env["res.partner"].sudo().search([("ocd_is_vendor", "=", True)]).country_id
        (Country.search([("code", "in", countries.DEFAULT_OFFERED)]) | known).ocd_offered = True
