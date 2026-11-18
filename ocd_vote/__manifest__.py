{
    "name": "OCD Vote: Paid Votes For Contests",
    "summary": "Contests (miss, awards, talents, schools) with numbered candidates, votes paid "
    "with Mobile Money, live ranking, band for the live of the final, results and payout to "
    "the organiser",
    "description": """
OCD Vote
========

- A contest of an organiser (checked by the team, like the vendors) or of OCD
  Live: its dates, the price of a vote and its packs, the share of the
  organiser, its rules; numbered candidates with their photo.
- The public votes on the page of a candidate: a number of votes, then the
  payment form of OCD Live (Mobile Money, card...). Only the paid votes
  count, each one linked to its payment; a payment refunded removes its
  votes; a payment started after the end does not count. No free votes.
- Live ranking (the numbers hidden in the last hours, setting), a band for
  the live of the final (a page for the live software), the results
  certified by OCD Live (PDF signed).
- The organiser logs in with their number, like the vendors: their contest,
  their share, their candidates (checked by the team after the opening).
- The payout of the organiser after the results, with the reference of the
  transfer.
""",
    "version": "20.0.1.0.0",
    "category": "Website/Website",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["ocd_live_shop"],
    "data": [
        "security/ir.access.csv",
        "data/product_data.xml",
        "data/ocd_refuse_reason_data.xml",
        "data/ir_cron_data.xml",
        "data/ocd_automation_data.xml",
        "report/ocd_vote_results_report.xml",
        "views/ocd_vote_contest_views.xml",
        "views/ocd_vote_views.xml",
        "views/ocd_vote_menus.xml",
        "views/ocd_vote_templates.xml",
        "views/ocd_vote_organizer_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "ocd_vote/static/src/scss/ocd_vote.scss",
            "ocd_vote/static/src/interactions/*.js",
        ],
    },
    "installable": True,
    "application": False,
}
