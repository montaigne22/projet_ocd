from odoo import SUPERUSER_ID, api

# Texts refused by Meta as INCORRECT_CATEGORY: Meta takes them for authentication messages (a
# personal link to keep for yourself, an account to activate with its username, a ticket number
# that the team will ask for). The new texts say what happened, like the messages of the bookings.
OLD_TEXTS = {
    "ocd_live_whatsapp.template_space_link": [
        "Bonjour {{1}}, voici votre lien personnel OCD Live. Gardez-le pour vous : il ouvre votre espace "
        "(vos lives, vos paquets, votre pass).",
    ],
    "ocd_live_whatsapp.template_space_link_en": [
        "Hello {{1}}, here is your personal OCD Live link. Keep it to yourself: it opens your space (your "
        "lives, your packages, your pass).",
    ],
    "ocd_live_whatsapp.template_access_link": [
        "Bonjour {{1}}, votre compte vendeur OCD Live est créé. Touchez le bouton pour l'activer. Pour vous "
        "connecter ensuite, votre identifiant est votre numéro WhatsApp.",
    ],
    "ocd_live_whatsapp.template_access_link_en": [
        "Hello {{1}}, your OCD Live vendor account has been created. Tap the button to activate it. To log "
        "in afterwards, your username is your WhatsApp number.",
    ],
    "ocd_live_whatsapp.template_ticket": [
        "Bonjour {{1}}, voici votre ticket OCD Live pour votre live du {{2}}, de {{3}} à {{4}}. Il a lieu "
        "{{5}}. Numéro du ticket : {{6}}. Gardez ce message, l'équipe d'OCD Live vous le demandera le jour "
        "du live.\n\nÀ bientôt sur OCD Live !",
    ],
    "ocd_live_whatsapp.template_ticket_en": [
        "Hello {{1}}, here is your OCD Live ticket for your live on {{2}}, from {{3}} to {{4}}. It takes "
        "place {{5}}. Ticket number: {{6}}. Keep this message, the OCD Live team will ask for it on the day "
        "of the live.\n\nSee you soon on OCD Live!",
    ],
}
REFUSED_STATUSES = ("unknown", "rejected", "pending")
# The button of the access says what it does now (its labels of before, then the new one)
BUTTONS = {
    "ocd_live_whatsapp.template_access_link": (("Activer mon compte", "Choisir mon mot de passe"), "Terminer mon inscription"),
    "ocd_live_whatsapp.template_access_link_en": (("Activate my account",), "Complete my registration"),
}


def migrate(cr, version):
    """The decisions of Meta first (without its webhook, Odoo still sees them waiting), then the
    refused templates take the new texts; the button of the access its new label. To submit to
    Meta again: WhatsApp › Templates, filter « Rejected », Action › Submit to Meta."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    Template = env["whatsapp.template"]
    Template._cron_read_pending_from_meta()
    Template._update_module_texts("ocd_live_whatsapp", OLD_TEXTS, statuses=REFUSED_STATUSES)
    # The new text (from this migration or one before it, which gave the text of the module)
    # needs its new button
    bodies = Template._get_module_bodies("ocd_live_whatsapp")
    for xmlid, (olds, new) in BUTTONS.items():
        template = env.ref(xmlid, raise_if_not_found=False)
        if template and template.body == bodies.get(xmlid):
            template.button_ids.filtered(lambda button, olds=olds: button.name in olds).name = new
