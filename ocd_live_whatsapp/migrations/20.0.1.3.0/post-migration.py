from odoo import SUPERUSER_ID, api

# The previous texts of the templates of the module, refused by Meta: a variable at the end
# ("... : {{2}}." included), two variables separated by a comma only, too many variables for
# the length of the text. The login code takes the text that Meta writes.
OLD_TEXTS = {
    "ocd_live_whatsapp.template_login_code": [
        "Votre code OCD Live est {{1}}. Il est valable 10 minutes. Ne le donnez à personne.",
    ],
    "ocd_live_whatsapp.template_live_confirmed": [
        "Bonjour {{1}}, votre live est confirmé : {{2}}, de {{3}} à {{4}}, {{5}}. Référence {{6}}. "
        "Vous recevrez un rappel la veille.",
    ],
    "ocd_live_whatsapp.template_live_reminder": [
        "Bonjour {{1}}, rappel : votre live est {{2}} à {{3}}, {{4}}. Préparez vos produits. Au "
        "studio, venez 15 minutes avant.",
    ],
    "ocd_live_whatsapp.template_link_refused": [
        "Bonjour {{1}}, votre lien n'a pas été accepté dans l'annuaire : {{2}}",
    ],
    "ocd_live_whatsapp.template_ticket": [
        "Bonjour {{1}}, voici votre ticket OCD Live : {{2}}, de {{3}} à {{4}}, {{5}}. Code {{6}} : {{7}}",
        "Bonjour {{1}}, voici votre ticket OCD Live : {{2}}, de {{3}} à {{4}}, {{5}}. Code {{6}} : {{7}}"
        "\n\nÀ bientôt sur OCD Live !",
    ],
    "ocd_live_whatsapp.template_link_received": [
        "Bonjour {{1}}, nous avons bien reçu le lien de votre live. Il sera vérifié dès l'ouverture "
        "de l'annuaire : {{2}}.",
    ],
}


def migrate(cr, version):
    """The templates not approved by Meta yet, with a previous text of the module, take the
    new one: the template data is loaded only at the installation."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["whatsapp.template"]._update_module_texts("ocd_live_whatsapp", OLD_TEXTS)
