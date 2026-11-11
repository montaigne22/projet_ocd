from odoo import SUPERUSER_ID, api

from odoo.addons.ocd_live_whatsapp.hooks import restore_english_templates

# Texts refused by Meta: a « code » in a Utility template and a sentence in a variable (ticket),
# a password with a link (access of a vendor)
OLD_TEXTS = {
    "ocd_live_whatsapp.template_ticket": [
        "Bonjour {{1}}, voici votre ticket OCD Live pour votre live du {{2}}, de {{3}} à {{4}}. Il a "
        "lieu {{5}}. Votre code est {{6}}. Pour l'utiliser, {{7}}\n\nÀ bientôt sur OCD Live !",
    ],
    "ocd_live_whatsapp.template_access_link": [
        "Bonjour {{1}}, choisissez votre mot de passe OCD Live avec ce lien. Pour vous connecter, "
        "votre identifiant est votre numéro WhatsApp.",
    ],
}
REFUSED_STATUSES = ("unknown", "rejected", "pending")


def migrate(cr, version):
    """The decisions of Meta first (without its webhook, Odoo still sees them waiting), then the
    refused templates take the new texts; the button of the access gets its new label."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Template = env["whatsapp.template"]
    # English versions wanted after all: the ones of the WhatsApp modules are active again (the
    # English versions of OCD Live come with the data of this version)
    restore_english_templates(env)
    Template._cron_read_pending_from_meta()
    Template._update_module_texts("ocd_live_whatsapp", OLD_TEXTS, statuses=REFUSED_STATUSES)
    xmlid = "ocd_live_whatsapp.template_access_link"
    access = env.ref(xmlid, raise_if_not_found=False)
    if access and access.body == Template._get_module_bodies("ocd_live_whatsapp")[xmlid]:
        access.button_ids.filtered(lambda button: button.name == "Choisir mon mot de passe").name = "Activer mon compte"
