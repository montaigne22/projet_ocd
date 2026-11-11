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
""",
    "version": "20.0.1.0.1",
    "category": "Accounting/Payment Providers",
    "sequence": 360,
    "author": "RollBackk",
    "license": "OPL-1",
    "depends": ["payment"],
    "data": [
        "views/payment_campay_templates.xml",
        "views/payment_provider_views.xml",
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
