{
    "name": "Payment Provider: Campay",
    "summary": "Mobile Money payments in Cameroon (MTN MoMo, Orange Money) and cards with Campay",
    "description": """
Campay payment provider
=======================

- Mobile Money (MTN Mobile Money and Orange Money): the customer enters the phone number
  at checkout and confirms the payment on the phone, without leaving the website.
- Card payments through the Campay payment page.
- Signed webhook (JWT HS256 with the webhook key) and status checks with the Campay API:
  the payment state is always read from Campay, never from the callback parameters.
- Demo payments, for a presentation or a test with real phones: each payment collects a
  small amount (25 F CFA by default) instead of the price, for every number or for the
  demo numbers only, until a last day. The pages show the real prices, the order is paid
  as usual and the accounts record the money received.
""",
    "version": "20.0.1.2.0",
    "category": "Accounting/Payment Providers",
    "sequence": 360,
    "author": "RollBackk",
    "license": "OPL-1",
    "depends": ["account_payment"],
    "data": [
        "views/payment_campay_templates.xml",
        "views/payment_provider_views.xml",
        "views/payment_transaction_views.xml",
        "data/payment_provider_data.xml",
        "data/payment_method_data.xml",
        "data/ir_cron_data.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "payment_campay/static/src/interactions/payment_form.js",
        ],
    },
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
}
