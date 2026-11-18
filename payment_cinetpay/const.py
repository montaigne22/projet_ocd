from odoo.addons.payment.const import SENSITIVE_KEYS as PAYMENT_SENSITIVE_KEYS

# Keys masked in the payment logs: the API key and the secret key of the site
SENSITIVE_KEYS = {"apikey", "secret_key"}
PAYMENT_SENSITIVE_KEYS.update(SENSITIVE_KEYS)

# The checkout API of CinetPay (the same host for the test and the live sites: the site and its
# keys tell which one)
API_URL = "https://api-checkout.cinetpay.com/v2/"

# The currencies CinetPay collects
SUPPORTED_CURRENCIES = ["XOF", "XAF", "CDF", "GNF", "USD"]

# Currencies without decimals whose amounts are asked in multiples of 5
MULTIPLE_OF_5_CURRENCIES = {"XOF", "XAF", "CDF", "GNF"}

# The codes of the default payment methods to activate
DEFAULT_PAYMENT_METHOD_CODES = {"mobile_money", "wallet", "card"}

# The channels of the payment page of CinetPay, per payment method code
CHANNELS_MAPPING = {"mobile_money": "MOBILE_MONEY", "wallet": "WALLET", "card": "CREDIT_CARD"}

# Mapping of the transaction states to the statuses of CinetPay
PAYMENT_STATUS_MAPPING = {
    "done": ("ACCEPTED",),
    "cancel": ("CANCELED", "CANCELLED"),
    "error": ("REFUSED",),
}

# How long (in hours) a pending payment is checked again with CinetPay by the scheduled task
PENDING_CHECK_WINDOW_HOURS = 24
