{
    "name": "OCD Live: Ambassadors",
    "summary": "Anyone shares a product of OCD Live with their personal link and earns a share of the "
    "articles once the parcel is delivered with its code and kept, paid every week on their Mobile Money",
    "description": """
Ambassadors
===========

- Anyone signs up on /ambassadeurs with their WhatsApp number (checked by a code)
  and their Mobile Money; the charter is accepted. Program open to all, on
  invitation or closed (settings).
- « My ambassador space »: to pay next Monday, waiting, the sales of the week and
  their state; « My money » (the detail of the payout, the returns taken back,
  the payouts made, a new number held 48 h); « Products to share » (best sellers,
  promos, live tonight, what one earns); « Share » (the image drawn by OCD Live at
  the price of now with the personal link, the text, the WhatsApp status, a
  contact, the clip of the live); « My links » (any page of the site).
- The personal link /a/<code> is kept 7 days on the phone; the last link opened
  counts, for all the articles of the order; the ambassador, the rate and the cap
  are written on the order when it is confirmed. Robots and the ambassador's own
  visits are not counted. « Grâce recommends this product » on the product page.
- The gain: 5 % of the articles (not the delivery), at most 3 000 F per parcel and
  never more than the commission of OCD on the article, paid by OCD. One gain per
  parcel: earned when delivered with the code, confirmed 7 days later (a bill of
  the ambassador), a return later taken back (a credit note); paid with the
  payouts of the shop every week, never a balance below zero.
- Against fraud: never on their own purchases (number, Mobile Money, account,
  their boutique), 5 orders of a customer per month, paused by itself above 30 %
  of returns, one Mobile Money per person, identity seen above 50 000 F, a new
  payout number held 48 h. « To check » of the team, settings, automations.
- The vendor sees « Sold thanks to the ambassadors » in « My figures ».
""",
    "version": "20.0.1.0.0",
    "category": "Website/Website",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["ocd_live_shop"],
    "data": [
        "security/ir.access.csv",
        "data/product_data.xml",
        "data/ir_cron_data.xml",
        "data/ocd_automation_data.xml",
        "data/ocd_refuse_reason_data.xml",
        "views/ocd_ambassador_views.xml",
        "views/ocd_ambassador_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "ocd_ambassadors/static/src/scss/ocd_ambassadors.scss",
            "ocd_ambassadors/static/src/interactions/*.js",
        ],
    },
    "installable": True,
    "application": False,
}
