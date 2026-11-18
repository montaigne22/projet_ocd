{
    "name": "Payment Provider: CinetPay",
    "summary": "Mobile Money (Orange, MTN, Moov, Free, Wave...) and cards in the UEMOA and Central "
    "Africa with CinetPay",
    "description": """
CinetPay payment provider
=========================

- Mobile Money of the UEMOA (Côte d'Ivoire, Senegal, Togo, Benin, Mali, Burkina
  Faso, Niger) and of Cameroon, Guinea and the DR Congo: Orange Money, MTN, Moov,
  Free, T-Money, Flooz..., Wave and the other wallets, and the cards, on the
  payment page of CinetPay.
- The amount asked to CinetPay is a multiple of 5 in CFA francs (rule of CinetPay):
  rounded up by a few francs at most, the order is paid for its own amount.
- The state of a payment is always read from CinetPay (verification API), never
  from the parameters of the notification or of the return.
- The payments still waiting are checked again every 10 minutes for a day, in case
  a notification was missed.
""",
    "version": "20.0.1.0.0",
    "category": "Accounting/Payment Providers",
    "sequence": 355,
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["account_payment"],
    "data": [
        "views/payment_provider_views.xml",
        "data/payment_provider_data.xml",
        "data/payment_method_data.xml",
        "data/ir_cron_data.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
}
