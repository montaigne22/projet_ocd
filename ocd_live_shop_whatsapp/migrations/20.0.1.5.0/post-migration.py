from odoo import SUPERUSER_ID, Command, api

# Text refused by Meta: the code of the parcel in a Utility template. The new text sends to the
# page that follows the order, where the code is, with a button.
OLD_TEXTS = {
    "ocd_live_shop_whatsapp.template_parcel_on_the_way": [
        "Bonjour {{1}}, votre colis {{2}} est en route avec {{3}}. Votre code de livraison : {{4}}. "
        "Donnez-le au livreur seulement quand vous avez le colis en main.",
    ],
}
REFUSED_STATUSES = ("unknown", "rejected", "pending")
BUTTON = {
    "button_type": "url",
    "name": "Suivre mon colis",
    "url": "{base_url}/{{1}}",
    "url_example": "ocd/suivi/12?access_token=abc123",
}


def migrate(cr, version):
    """The decisions of Meta first (without its webhook, Odoo still sees them waiting), then the
    refused template takes the new text and its button « Suivre mon colis »."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Template = env["whatsapp.template"]
    Template._cron_read_pending_from_meta()
    Template._update_module_texts("ocd_live_shop_whatsapp", OLD_TEXTS, statuses=REFUSED_STATUSES)
    xmlid = "ocd_live_shop_whatsapp.template_parcel_on_the_way"
    parcel = env.ref(xmlid, raise_if_not_found=False)
    # The new text (from this migration or the one before) needs its button
    if parcel and parcel.body == Template._get_module_bodies("ocd_live_shop_whatsapp")[xmlid] and not parcel.button_ids:
        parcel.write({
            "button_url_value": "{{ object._ocd_tracking_path() }}",
            "button_ids": [Command.create(BUTTON)],
        })
