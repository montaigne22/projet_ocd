from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestThemeOcd(TransactionCase):

    def test_theme_is_offered_in_the_theme_chooser(self):
        Module = self.env["ir.module.module"]
        theme = Module.search([("name", "=", "theme_ocd")])
        self.assertIn(theme, Module.search(Module.get_themes_domain()))

    def test_header_of_ocd_live_when_the_theme_is_chosen(self):
        website = self.env["website"].search([], limit=1)
        theme = self.env["ir.module.module"].search([("name", "=", "theme_ocd")])
        self.env["theme.utils"].with_context(website_id=website.id)._theme_ocd_post_copy(theme)
        website = website.with_context(website_id=website.id)
        self.assertFalse(website.is_view_active("website.header_search_box"))
        self.assertFalse(website.is_view_active("website.header_text_element"))
        self.assertTrue(website.is_view_active("website.template_header_default"))
        self.assertTrue(website.is_view_active("website.footer_custom"))
