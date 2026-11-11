{
    "name": "WhatsApp Cloud API - eCommerce",
    "summary": "WhatsApp for the online shop: order notifications, order tracking, quotations "
    "with payment link, satisfaction after delivery, Order on WhatsApp",
    "description": """
WhatsApp of the online shop
===========================

- Checkout: "Receive the follow-up of my orders on WhatsApp" box in the address form,
  ticked by default unless the customer refused before (consent stored on the
  customer, required by WhatsApp).
- Templates and automation rules, ready to use once the templates are approved by Meta
  (submitted from Odoo or created at Meta): order received, confirmed, shipped, ready for
  pickup, quotation sent with its payment link, satisfaction 2 days after the delivery.
  In French, and in English for the English-speaking customers.
- Conversations: "Track my order" option of the welcome menu and order numbers answered
  automatically (only the orders of the customer), assignment to the salesperson of the
  customer, orders in the information panel, new quotation from the conversation.
- Quotations: "Send on WhatsApp" button, as an answer in the conversation within 24 hours
  or with the template after, with the link to view and pay online.
- Ratings of the customers stored on the orders; review link to the satisfied customers,
  unsatisfied customers handed over to the team.
- "Order on WhatsApp" button on the product pages (product and chosen options in the
  message), WhatsApp number of the shop.
- Settings (WhatsApp section): each feature enabled or disabled (notifications of the
  orders, satisfaction, order tracking, quotations, "Order on WhatsApp" button, consent
  at the checkout).
""",
    "version": "20.0.2.3.0",
    "category": "Website/Website",
    "author": "RollBackk",
    "license": "OPL-1",
    "depends": ["whatsapp_cloud", "website_sale", "sale_stock", "stock_delivery", "rating"],
    "data": [
        "data/whatsapp_template_data.xml",
        "data/base_automation_data.xml",
        "views/whatsapp_composer_actions.xml",
        "views/sale_order_views.xml",
        "views/templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "whatsapp_cloud_sale/static/src/js/**/*",
        ],
    },
    "auto_install": True,
    "installable": True,
}
