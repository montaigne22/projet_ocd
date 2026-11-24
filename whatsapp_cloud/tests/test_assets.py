from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAssets(TransactionCase):

    def test_backend_style_compiles(self):
        """The style of the conversations (laid out like WhatsApp) compiles with the whole backend:
        a SCSS error puts Odoo on its former style, with a red banner, for everybody."""
        bundle = self.env["ir.qweb"]._get_asset_bundle("web.assets_backend", js=False)
        bundle.css()
        self.assertEqual(bundle.css_errors, [])
