from odoo import models


class ThemeUtils(models.AbstractModel):
    _inherit = "theme.utils"

    def _theme_ocd_post_copy(self, mod):
        """Header and footer of OCD Live: the simple header (logo, menu, button "Book a live"),
        as the pages of OCD Live, without the search bar and the phone of Odoo (the phone is in
        the footer), and the footer of OCD Live."""
        self.enable_view("website.template_header_default")
        self.enable_view("website.footer_custom")
        self.disable_view("website.header_search_box")
        self.disable_view("website.header_text_element")
