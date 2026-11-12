from odoo import models
from odoo.modules.module import Manifest


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def _update_translations(self, filter_lang=None, overwrite=False):
        """Override of `base`: the name, summary and description of a module follow its
        translations when it is updated. Odoo keeps the first ones of an installed module (its
        record is « noupdate »): after a change of the manifest, the Apps screen showed the
        French text of the first installation. The translations are read as Odoo reads them for
        the modules not installed (`_load_non_installed_modules_manifest_terms`)."""
        super()._update_translations(filter_lang=filter_lang, overwrite=overwrite)
        if not filter_lang:
            langs = [code for code, _name in self.env["res.lang"].get_installed()]
        else:
            langs = list(filter_lang) if isinstance(filter_lang, (list, tuple)) else [filter_lang]
        langs = [lang for lang in langs if lang != "en_US"]
        if not langs:
            return
        for module in self.filtered(lambda m: m.state in ("installed", "to install", "to upgrade")):
            manifest = Manifest.for_addon(module.name, display_warning=False)
            if not manifest:
                continue
            translations = manifest.get_translations(langs)
            if not translations:
                continue
            # the English texts come with them, as Odoo does (see the method above)
            source = self.get_values_from_terp(manifest)
            for field_name, values in translations.items():
                values["en_US"] = source[field_name]
            module.write(dict(translations))
