{
    "name": "OCD Live: Automatic Clips Of The Lives",
    "summary": "Each product shown in a live becomes a vertical clip of 30 seconds with its short link, to share "
    "on the WhatsApp statuses, TikTok and Reels; shown on the product page and the replay",
    "description": """
Automatic clips of the lives
============================

- After a live, the team sends its video (the recording of the studio, or the
  video downloaded from the account of OCD Live), in pieces that start again
  where they stopped; it is checked when it arrives (readable, image and
  sound, its length) and deleted after a few days, the clips stay.
- Each product noted by the control room becomes a vertical clip: from a
  little before its moment, 30 seconds at most, cut before the next product;
  the logo « Seen in live », the name, the vendor and the short link written
  out of the zones covered by TikTok, Reels and the statuses; the last 2
  seconds with the QR code. Made with ffmpeg on the server, one after the
  other, in low priority, 3 tries.
- The vendor: « My clips » in their space, share the video itself with its
  text, save it, hide it, make it the video of their card in the feed; the
  clips of each product in « My products ».
- The public: « Seen in live » on the product page, the clip of each product
  on the replay; the short link leads to the product with the colour shown,
  its visits and its sales counted for the vendor.
""",
    "version": "20.0.1.0.1",
    "category": "Website/Website",
    "author": "RollBackk",
    "license": "LGPL-3",
    "depends": ["ocd_live_shop"],
    "data": [
        "security/ir.access.csv",
        "data/ir_cron_data.xml",
        "data/ocd_automation_data.xml",
        "views/ocd_live_clip_views.xml",
        "views/ocd_clips_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ocd_clips/static/src/screen/*",
            "ocd_clips/static/src/regie/*",
        ],
        "web.assets_frontend": [
            "ocd_clips/static/src/scss/ocd_clips.scss",
            "ocd_clips/static/src/interactions/*.js",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
