from odoo.modules.module import Manifest
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOcdModuleTexts(TransactionCase):
    """The name, summary and description of a module in the Apps screen follow its
    translations after an update (Odoo kept those of the first installation)."""

    def test_texts_of_a_module_follow_its_translations(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        manifest = Manifest.for_addon("ocd_live")
        expected = manifest.get_translations(["fr_FR"])
        self.assertIn("summary", expected, "ocd_live has a French summary")
        module = self.env["ir.module.module"].search([("name", "=", "ocd_live")])
        module.with_context(lang="fr_FR").summary = "Ancien résumé"
        module._update_translations("fr_FR")
        module.invalidate_recordset(["summary"])
        self.assertEqual(module.with_context(lang="fr_FR").summary, expected["summary"]["fr_FR"])
        self.assertEqual(module.with_context(lang="en_US").summary, manifest["summary"], "English stays the manifest's")
