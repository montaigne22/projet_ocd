from odoo import SUPERUSER_ID, api

# Texts refused by Meta as INCORRECT_CATEGORY, or that it would refuse: a code named in a Utility
# template, a link to keep for yourself; Meta takes them for authentication messages. The new
# texts say what happens to the parcel; the code stays on the page that follows the order.
OLD_TEXTS = {
    "ocd_live_shop_whatsapp.template_parcel_on_the_way": [
        "Bonjour {{1}}, votre colis {{2}} est en route avec {{3}}. Touchez « Suivre mon colis » pour voir le "
        "code à donner au livreur, seulement quand vous avez le colis en main.",
    ],
    "ocd_live_shop_whatsapp.template_parcel_on_the_way_en": [
        'Hello {{1}}, your parcel {{2}} is on its way with {{3}}. Tap "Track my parcel" to see the code to '
        "give to the courier, only when you have the parcel in your hands.",
    ],
    "ocd_live_shop_whatsapp.template_delivery_link": [
        "Bonjour {{1}}, voici votre lien pour préparer et livrer les colis OCD Live. Gardez-le pour vous.",
    ],
    "ocd_live_shop_whatsapp.template_delivery_link_en": [
        "Hello {{1}}, here is your link to prepare and deliver the OCD Live parcels. Keep it to yourself.",
    ],
    "ocd_live_shop_whatsapp.template_parcel_failed": [
        "Bonjour {{1}}, votre colis n'a pas pu vous être livré par {{2}}. Répondez à ce message pour choisir "
        "un autre moment. Votre code de livraison reste le même.",
    ],
    "ocd_live_shop_whatsapp.template_parcel_failed_en": [
        "Hello {{1}}, your parcel could not be delivered to you by {{2}}. Reply to this message to choose "
        "another time. Your delivery code stays the same.",
    ],
}
REFUSED_STATUSES = ("unknown", "rejected", "pending")


def migrate(cr, version):
    """The decisions of Meta first (without its webhook, Odoo still sees them waiting), then the
    refused templates take the new texts. An approved template keeps its text: it is the one
    Meta sends."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Template = env["whatsapp.template"]
    Template._cron_read_pending_from_meta()
    Template._update_module_texts("ocd_live_shop_whatsapp", OLD_TEXTS, statuses=REFUSED_STATUSES)
