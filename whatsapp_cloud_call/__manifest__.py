{
    "name": "WhatsApp Calls",
    "summary": "The customers call the company from WhatsApp: a FreeSWITCH call server between "
    "Meta and the agents, queue, agents who answer in Odoo, history in the conversations",
    "description": """
WhatsApp calls for Odoo Community
=================================

The customers call the WhatsApp number of the company (the phone icon in WhatsApp). The calls
go through a call server of the company (FreeSWITCH, SIP over TLS with Meta), which rings the
agents in their browser, in Odoo (WebRTC):

- Settings of the calls at Meta from the WhatsApp account: calls enabled, call icon, call
  hours (the opening hours of the team and its public holidays), SIP server, SRTP, webhook of
  the calls; the SIP password given by Meta kept for the call server.
- Queue on the call server: music, all the free agents ring together, the agent of the
  conversation first; an agent cut off (network, closed tab) gets the call back while the
  customer waits; voicemail when nobody answers, posted in the conversation.
- The call server works without Odoo: the agents and their passwords are copied every minute
  on the server; when Odoo does not answer, all the connected agents ring.
- Phone of the agents in the top bar: take the calls or not, ringing, name of the customer and
  their conversation, answer, decline, mute, hang up; a second call is refused while busy.
- History: each call (wait, duration, agent, outcome) and a line in the conversation; a missed
  call or a voicemail waits for an answer of the team (reminders of WhatsApp).
- Monitoring: the call server reports every minute, the managers are alerted when it is
  silent; a call seen by Meta and not by the call server is "lost" and reported.
- TURN credentials for the agents (coturn), valid 12 hours.

The configuration of the call server is in the freeswitch folder of the module.
""",
    "version": "20.0.1.13.0",
    "category": "Marketing",
    "author": "RollBackk",
    "license": "OPL-1",
    "depends": ["whatsapp_cloud"],
    "data": [
        "security/ir.access.csv",
        "data/ir_cron_data.xml",
        "views/whatsapp_call_views.xml",
        "views/whatsapp_account_views.xml",
        "views/res_config_settings_views.xml",
        "views/whatsapp_call_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "whatsapp_cloud_call/static/src/softphone/*",
            "whatsapp_cloud_call/static/src/audio_player/*",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
}
