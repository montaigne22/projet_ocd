{
    "name": "OCD Tickets: Tickets For Concerts And Events",
    "summary": "Tickets of concerts and events sold on their page and during the lives, paid like the "
    "rest of OCD Live, one signed QR per person checked once at the entrance, payout to the organiser",
    "description": """
OCD Tickets
===========

- An event of an organiser (checked by the team, the same account as for OCD
  Vote) or of OCD Live, made with the Events application of Odoo: its date,
  its place, its kinds of tickets and their seats.
- The public buys on the page of the event: a number per kind of ticket, the
  name on the tickets, the WhatsApp number, then the payment form of OCD Live
  (Mobile Money, card...). The seats are held while the payment is made, then
  given back. A ticket exists once its payment is confirmed.
- « My tickets »: one QR per person, signed by the server, valid once; the
  PDF; « Give this ticket » to a friend (a new QR, the old one no longer
  works).
- The controllers of the organiser log in with their number and scan the
  tickets with the camera of their phone, without an application; the list of
  the tickets stays in the phone when the network is gone. They may sell at
  the door (cash or Mobile Money) when the organiser allows it.
- During a live, the control room shows a ticket like a product, with a live
  price if the organiser wants one.
- Cancelled: every buyer is refunded; moved: the tickets stay valid, refund on
  request for a few days. The organiser is paid a few days after the event.
""",
    "version": "20.0.1.0.0",
    "category": "Website/Website",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["ocd_vote", "event_sale"],
    "data": [
        "security/ir.access.csv",
        "data/ocd_refuse_reason_data.xml",
        "data/ir_cron_data.xml",
        "data/ocd_automation_data.xml",
        "report/ocd_ticket_report.xml",
        "views/event_event_views.xml",
        "views/event_registration_views.xml",
        "views/ocd_ticket_controller_views.xml",
        "views/ocd_ticket_move_views.xml",
        "views/ocd_tickets_menus.xml",
        "views/ocd_tickets_templates.xml",
        "views/ocd_tickets_entrance_templates.xml",
        "views/ocd_tickets_organizer_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "ocd_tickets/static/src/scss/ocd_tickets.scss",
            "ocd_tickets/static/src/interactions/*.js",
        ],
    },
    "installable": True,
    "application": False,
}
