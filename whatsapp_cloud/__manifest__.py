{
    "name": "WhatsApp Cloud API",
    "summary": "WhatsApp Business with the Cloud API of Meta: notifications, conversations in "
    "Discuss, automatic answers, templates submitted from Odoo",
    "description": """
WhatsApp for Odoo Community
===========================

WhatsApp Business number of the company with the Cloud API of Meta (no intermediary):

- Accounts: phone number ID, WhatsApp Business account ID, access token and app
  secret, entered by an administrator in Odoo (never in the code). Health of the number
  (quality, messaging limit, display name, token) checked every 6 hours, managers alerted.
- Conversations in Discuss (WhatsApp tab): every type of message (texts, photos, voice
  messages, videos, documents, locations, contacts, reactions, quoted replies), files
  downloaded, answers of the agents with files and quotes, 24-hour window, read receipts
  and "typing...", delivery ticks with the reason of the failures, internal notes (/note),
  canned responses with variables, tags, information panel on the customer.
- Team: agents and managers, assignment (taken by an agent, each agent in turn), transfer,
  reminders and escalation of the messages waiting for an answer (opening hours and public
  holidays), unknown numbers identified or merged into the right contact.
- Automatic answers: away message outside of the opening hours, welcome menu with buttons,
  hand over to an agent, STOP / START.
- Templates: synchronised from Meta, or written in Odoo and submitted to Meta (header,
  footer, quick replies, link and call buttons, examples); status, quality and category
  updated by Meta; each contact gets the version in their language.
- "Send WhatsApp" action in the automation rules and server actions.
- Webhook signed by Meta (X-Hub-Signature-256), stored and acknowledged at once, then
  processed in the background without duplicates.
- Settings (WhatsApp section): each feature enabled or disabled (conversations, read
  receipts, reminders, welcome menu, away message).
""",
    "version": "20.0.2.3.0",
    "category": "Marketing",
    "author": "RollBackk",
    "license": "OPL-1",
    "depends": ["mail", "phone_validation", "base_automation", "resource"],
    "data": [
        "security/whatsapp_security.xml",
        "security/ir.access.csv",
        "data/ir_cron_data.xml",
        "data/whatsapp_template_data.xml",
        "views/whatsapp_bot_option_views.xml",
        "views/whatsapp_account_views.xml",
        "views/whatsapp_template_views.xml",
        "views/whatsapp_message_views.xml",
        "views/discuss_channel_views.xml",
        "views/res_partner_views.xml",
        "views/ir_actions_server_views.xml",
        "wizard/whatsapp_composer_views.xml",
        "views/res_config_settings_views.xml",
        "views/whatsapp_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "whatsapp_cloud/static/src/**/*",
        ],
    },
    "installable": True,
    "application": True,
}
