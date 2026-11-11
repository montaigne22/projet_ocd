from odoo import SUPERUSER_ID, api

# The previous texts of the templates of the module, refused by Meta: a variable at the end,
# two variables separated by punctuation only.
OLD_TEXTS = {
    "ocd_live_shop_whatsapp.template_parcel_to_prepare": [
        "Bonjour {{1}}, nouveau colis à préparer pour {{2}} ({{3}}) : {{4}}. Touchez le bouton "
        "quand il est prêt.",
    ],
    "ocd_live_shop_whatsapp.template_parcel_on_the_way": [
        "Bonjour {{1}}, votre colis {{2}} est en route avec {{3}}. Donnez ce code au livreur "
        "seulement quand vous avez le colis en main : {{4}}",
    ],
    "ocd_live_shop_whatsapp.template_parcel_failed": [
        "Bonjour {{1}}, {{2}} n'a pas pu vous livrer. Répondez à ce message pour choisir un autre "
        "moment. Votre code reste le même.",
    ],
}


def migrate(cr, version):
    """The templates not approved by Meta yet, with a previous text of the module, take the
    new one: the template data is loaded only at the installation."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["whatsapp.template"]._update_module_texts("ocd_live_shop_whatsapp", OLD_TEXTS)
