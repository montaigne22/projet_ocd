from odoo.addons.payment.const import SENSITIVE_KEYS as PAYMENT_SENSITIVE_KEYS

# Keys masked in the payment logs: the app password, the access token and the webhook signature.
SENSITIVE_KEYS = {"password", "token", "signature"}
PAYMENT_SENSITIVE_KEYS.update(SENSITIVE_KEYS)

# Campay API hosts: the demo host for test mode, the production host for live mode.
API_URLS = {
    "test": "https://demo.campay.net/api/",
    "live": "https://www.campay.net/api/",
}

# Campay only collects Central African CFA francs.
SUPPORTED_CURRENCIES = ["XAF"]

# The codes of the default payment methods to activate.
DEFAULT_PAYMENT_METHOD_CODES = {"mobile_money", "card"}

# Payment options of the Campay payment page, per payment method code.
PAYMENT_OPTIONS_MAPPING = {"card": "CARD", "mobile_money": "MOMO"}

# Mapping of transaction states to Campay transaction statuses.
PAYMENT_STATUS_MAPPING = {
    "pending": ("PENDING",),
    "done": ("SUCCESSFUL",),
    "error": ("FAILED",),
}

# Cameroonian mobile numbers: 9 digits starting with 6, with the 237 country code for Campay.
CAMEROON_PHONE_CODE = "237"

# How long (in minutes) a pending Mobile Money payment is checked with Campay by the cron.
PENDING_CHECK_WINDOW_MINUTES = 60
