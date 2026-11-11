from datetime import timedelta

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

# Graph API of Meta, version set on each account.
GRAPH_URL = "https://graph.facebook.com"
DEFAULT_API_VERSION = "v26.0"

# Statuses sent by the webhook, in the order they happen ("played": first play of a voice
# message, after it was read).
STATUS_ORDER = ["queued", "sent", "delivered", "read"]
STATUS_ALIASES = {"played": "read"}

# Words a customer can send to stop the WhatsApp messages (opt-out), or to receive them again.
STOP_KEYWORDS = {
    "stop", "arret", "arrêt", "arreter", "arrêter", "desabonner", "désabonner", "unsubscribe",
}
START_KEYWORDS = {"start", "demarrer", "démarrer", "reprendre", "subscribe", "resume"}
# Words that show the menu of the automatic answers again, or ask for a person.
MENU_KEYWORDS = {"menu", "aide", "help"}
# Reply IDs of the "Main menu" and "Talk to the team" choices of the automatic answers.
MENU_REPLY_ID = "whatsapp_menu"
HANDOVER_REPLY_ID = "whatsapp_handover"
HANDOVER_KEYWORDS = {
    "conseiller", "conseillere", "conseillère", "humain", "agent", "operateur", "opérateur",
    "advisor", "human", "operator",
}

# The customer service window: free-form messages are allowed for 24 hours after the last
# message of the customer; templates are required after.
SERVICE_WINDOW = timedelta(hours=24)

# Errors worth a new attempt later (rate limits, temporary unavailability of Meta).
RETRYABLE_ERROR_CODES = {
    1, 2, 4, 80007, 130429, 131000, 131016, 131056, 131057, 133004, 2494100,
}
MAX_ATTEMPTS = 5

# Media of the messages (Meta limits) and the types that accept a caption.
MEDIA_TYPES = {"image", "audio", "video", "document", "sticker"}
CAPTION_TYPES = {"image", "video", "document"}
MAX_MEDIA_SIZE = 100 * 1024 * 1024
MEDIA_TYPE_BY_MIMETYPE = {
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "sticker",
    "audio/aac": "audio",
    "audio/amr": "audio",
    "audio/mpeg": "audio",
    "audio/mp4": "audio",
    "audio/ogg": "audio",
    "video/3gpp": "video",
    "video/mp4": "video",
}
MAX_MEDIA_SIZE_BY_TYPE = {
    "image": 5 * 1024 * 1024,
    "sticker": 500 * 1024,
    "audio": 16 * 1024 * 1024,
    "video": 16 * 1024 * 1024,
    "document": 100 * 1024 * 1024,
}

# Limits of the interactive messages.
MAX_REPLY_BUTTONS = 3
MAX_LIST_ROWS = 10
MAX_BUTTON_TITLE = 20
MAX_ROW_TITLE = 24
MAX_ROW_DESCRIPTION = 72
MAX_INTERACTIVE_BODY = 1024
MAX_TEXT_BODY = 4096
MAX_CAPTION = 1024

# What to do after an error of Meta, shown to the users with the error itself.
ERROR_HELP = {
    0: _lt("Meta could not authenticate the request: check the access token of the account."),
    190: _lt("The access token of the account expired or was revoked: generate a permanent token "
             "of a system user in the Meta Business portfolio and enter it on the account."),
    3: _lt("The app lacks a capability or a permission: check the permissions of the token."),
    4: _lt("Too many calls of the app to Meta: Odoo tries again later."),
    33: _lt("The phone number of the account was deleted at Meta."),
    80007: _lt("Too many calls to the WhatsApp Business account: Odoo tries again later."),
    10: _lt("The access token lacks a permission: give it whatsapp_business_messaging and "
            "whatsapp_business_management."),
    200: _lt("The access token lacks a permission: give it whatsapp_business_messaging and "
             "whatsapp_business_management."),
    368: _lt("Meta temporarily blocked the number for a policy violation: see the Meta Business "
             "Support Home."),
    100: _lt("A parameter of the message is invalid (variables of the template, number, "
             "media...): check the template and its variables."),
    130429: _lt("Too many messages per second: Odoo sends the message again later."),
    130403: _lt("The company blocked this customer on WhatsApp: unblock them to write to them."),
    130497: _lt("The WhatsApp Business account cannot write to customers of this country."),
    130472: _lt("The customer is part of an experiment of Meta and does not receive marketing "
                "messages for now."),
    131000: _lt("Unknown error at Meta: Odoo sends the message again later."),
    131005: _lt("The access token lacks a permission: give it whatsapp_business_messaging and "
                "whatsapp_business_management."),
    131008: _lt("A required parameter is missing: check the variables of the template."),
    131009: _lt("A parameter value is invalid: check the variables of the template and the number."),
    131016: _lt("WhatsApp is temporarily unavailable: Odoo sends the message again later."),
    131021: _lt("The recipient is the number of the account itself."),
    131026: _lt("The message could not be delivered: the number may not use WhatsApp, or have an "
                "outdated WhatsApp version, or not have accepted the latest terms. Contact the "
                "customer another way."),
    131031: _lt("The WhatsApp Business account is locked or restricted by Meta: see the Meta "
                "Business Support Home."),
    131037: _lt("The number has no approved display name yet: check it in the WhatsApp Manager."),
    131042: _lt("Payment issue of the WhatsApp Business account: add a valid payment method in "
                "the Meta Business portfolio."),
    131045: _lt("The number is not registered on the Cloud API: register it again in the Meta app."),
    131047: _lt("More than 24 hours since the last message of the customer: only an approved "
                "template can be sent (Send a template)."),
    131048: _lt("Meta limits the messages of the number because of their quality (spam reports): "
                "send fewer messages, only to customers who agreed."),
    131049: _lt("Meta did not deliver this marketing message to keep a good experience for the "
                "customer (limit of marketing messages per person). Try again later, not as soon "
                "as possible."),
    131050: _lt("The customer stopped the marketing messages of the company on WhatsApp."),
    131051: _lt("This type of message is not supported."),
    131052: _lt("The media of the message could not be downloaded from Meta."),
    131053: _lt("The media could not be uploaded to Meta: check its format and size."),
    131059: _lt("The list of the templates could not be read: synchronise again."),
    131060: _lt("This message of the customer is not available on the Cloud API."),
    131062: _lt("This message cannot be sent to a customer known only by their WhatsApp username "
                "(no number): ask for their number."),
    131063: _lt("The marketing templates are disabled on the Cloud API for this account."),
    131064: _lt("Messaging limit reached because of templates in the wrong category: it is lifted "
                "automatically after a while."),
    131056: _lt("Too many messages to the same customer in a short time: Odoo sends the message "
                "again later."),
    131057: _lt("The WhatsApp Business account is under maintenance: Odoo sends the message again "
                "later."),
    132000: _lt("The number of variables differs from the template at Meta: synchronise the "
                "templates and check their variables."),
    132001: _lt("The template does not exist at Meta in this language, or is not approved yet: "
                "synchronise the templates."),
    132005: _lt("A variable of the template is too long once filled."),
    132007: _lt("The text of the template breaks the WhatsApp policy."),
    132012: _lt("The format of a variable is invalid (text expected, image, document...)."),
    132015: _lt("The template is paused by Meta because of its low quality: edit it at Meta."),
    132016: _lt("The template is disabled by Meta because of its low quality."),
    132068: _lt("The flow of the template is blocked."),
    132069: _lt("The flow of the template is throttled."),
    133000: _lt("The number was not fully deleted before its new registration."),
    133004: _lt("The WhatsApp server is temporarily unavailable: Odoo sends the message again "
                "later."),
    133005: _lt("The two-step verification PIN of the number is wrong."),
    133006: _lt("The number must be verified again before its registration."),
    133008: _lt("Too many PIN attempts for the number: try again later."),
    133009: _lt("The PIN was entered too fast: try again later."),
    133010: _lt("The number is not registered on the Cloud API: register it in the Meta app."),
    133015: _lt("The number was recently deleted: wait a few minutes before registering it."),
    133016: _lt("Too many registrations of the number: try again later."),
    132018: _lt("A variable of the template is invalid: check the variables of the template."),
    2494100: _lt("The WhatsApp Business account is under maintenance: Odoo sends the message "
                 "again later."),
    135000: _lt("Unknown error of a parameter: check the message and the template."),
}
