"""The scenario of the demo: who sells what, where and when.

15 vendors in 8 countries (Togo, Cameroon, Ivory Coast, Senegal, Benin, Ghana, Nigeria and the
diaspora in Paris). The scheduled action of the demo keeps the scenario on the days around
today (hooks.OcdLiveDemo.keep_current), so that a presentation always shows a living OCD Live:

- the lives of the directory, in the checking window of the moment: the dishes in the morning
  (orders for midday) and late afternoon (orders for the evening), phones and beauty at
  midday, home and fabrics in the afternoon, clothes in the evening when people are at home;
  one link waits for the check of the team;
- the lives booked at the studio of Lomé, one at a time: the vendors of Lomé come to the studio
  with what they need, the others live from home with an OCD host; Saturday is full (two
  vendors wait for a free hour); one remote live still has no host;
- the replays of the past lives, with the products shown on screen;
- a live held while the team checks a Mobile Money payment announced by the vendor.

The hours are those of the studio (Lomé, the hours of its slots and windows).
"""

import zlib

# Days kept around today: the replays of the last week, the lives of the next two weeks
PAST_DAYS = 7
NEXT_DAYS = 13

MORNING = "ocd_live.window_morning"
MIDDAY = "ocd_live_demo.window_midday"
AFTERNOON = "ocd_live_demo.window_afternoon"
EVENING = "ocd_live.window_evening"

# Live link of each vendor, shown name, and the checking windows when it goes live
DIRECTORY = [
    ("vendor_awa", "https://www.tiktok.com/@awa.gateaux/live", "Awa Gâteaux", (MORNING,)),
    ("vendor_papa", "https://www.tiktok.com/@papa.ndole/live", "Papa Ndolé", (MORNING, AFTERNOON)),
    ("vendor_adjoua", "https://www.tiktok.com/@adjoua.attieke/live", "Adjoua Attiéké", (MORNING,)),
    ("vendor_kadi", "https://www.instagram.com/kadi.epices/live", "Kadi Épices", (MORNING,)),
    ("vendor_kossi", "https://www.facebook.com/kossitech/live", "Kossi Tech", (MIDDAY, EVENING)),
    ("vendor_fatou", "https://www.tiktok.com/@fatou.karite/live", "Fatou Karité", (MIDDAY,)),
    ("vendor_junior", "https://www.facebook.com/juniorgadgets/live", "Junior Gadgets", (MIDDAY,)),
    ("vendor_chioma", "https://www.instagram.com/chioma.hair/live", "Chioma Hair", (MIDDAY,)),
    ("vendor_ama", "https://www.tiktok.com/@ama.pagnes/live", "Ama Pagnes", (AFTERNOON,)),
    ("vendor_aminata", "https://www.instagram.com/aminata.deco/live", "Aminata Déco", (AFTERNOON,)),
    ("vendor_akua", "https://www.youtube.com/@akuakente/live", "Akua Kente", (AFTERNOON,)),
    ("vendor_brenda", "https://www.tiktok.com/@brenda.wax/live", "Brenda Wax", (EVENING,)),
    ("vendor_mireille", "https://www.tiktok.com/@mireille.couture/live", "Mireille Couture", (EVENING,)),
    ("vendor_moussa", "https://www.tiktok.com/@moussa.bazin/live", "Moussa Bazin", (EVENING,)),
]
# The vendors go live one after the other at the start of a window (minutes after its start)
FIRST_LIVE_MINUTES = 2
BETWEEN_LIVES_MINUTES = 9
# The link left to check by the team is never one of these countries, so that the visitor of
# the country of the studio always finds its vendors live
CHECKED_FIRST = ("TG",)
# The links are sent this long before their window (the night before for the morning one)
SENT_BEFORE_MINUTES = 60
SENT_THE_NIGHT_BEFORE_HOURS = 12
# The ended links of the demo are removed after two weeks
KEEP_LINKS_DAYS = 14

# The week of the studio (one live at a time): (hour, vendor, mode, needed at the studio, host)
STUDIO, REMOTE = "studio", "remote"
DZIFA, KAFUI = "host_dzifa", "host_kafui"
WEEK = {
    0: [  # Monday
        ("10:00", "vendor_kossi", STUDIO, "shelf", None),
        ("14:30", "vendor_junior", REMOTE, "none", KAFUI),
        ("19:00", "vendor_brenda", REMOTE, "none", DZIFA),
    ],
    1: [  # Tuesday
        ("10:00", "vendor_awa", STUDIO, "table", None),
        ("16:00", "vendor_aminata", REMOTE, "none", KAFUI),
        ("19:00", "vendor_mireille", REMOTE, "none", DZIFA),
        ("20:30", "vendor_chioma", REMOTE, "none", None),
    ],
    2: [  # Wednesday
        ("11:30", "vendor_papa", REMOTE, "none", KAFUI),
        ("17:30", "vendor_ama", STUDIO, "rack", None),
        ("19:00", "vendor_fatou", REMOTE, "none", DZIFA),
    ],
    3: [  # Thursday
        ("10:00", "vendor_kossi", STUDIO, "shelf", None),
        ("14:30", "vendor_adjoua", REMOTE, "none", KAFUI),
        ("19:00", "vendor_akua", REMOTE, "none", DZIFA),
        ("20:30", "vendor_moussa", REMOTE, "none", KAFUI),
    ],
    4: [  # Friday
        ("10:00", "vendor_awa", STUDIO, "table", None),
        ("16:00", "vendor_junior", REMOTE, "none", KAFUI),
        ("19:00", "vendor_brenda", REMOTE, "none", DZIFA),
    ],
    5: [  # Saturday: every hour is taken
        ("08:30", "vendor_papa", REMOTE, "none", KAFUI),
        ("10:00", "vendor_awa", STUDIO, "table", None),
        ("11:30", "vendor_kadi", REMOTE, "none", DZIFA),
        ("13:00", "vendor_kossi", STUDIO, "shelf", None),
        ("14:30", "vendor_ama", STUDIO, "rack", None),
        ("16:00", "vendor_mireille", REMOTE, "none", KAFUI),
        ("17:30", "vendor_aminata", REMOTE, "none", DZIFA),
        ("19:00", "vendor_brenda", REMOTE, "none", KAFUI),
        ("20:30", "vendor_akua", REMOTE, "none", DZIFA),
    ],
    6: [  # Sunday
        ("16:00", "vendor_fatou", REMOTE, "none", KAFUI),
        ("19:00", "vendor_moussa", REMOTE, "none", DZIFA),
    ],
}
# A remote live of the past always had a host: this one when the week gives none
PAST_HOST = DZIFA
# Seconds of the video where the products of the vendor are shown (a live of 1 h 30)
MOMENTS = (250, 1295, 2585)

# The full day of the week: who waits for a free hour, and how
FULL_DAY = 5
WAITLIST = [("vendor_chioma", REMOTE), ("vendor_moussa", REMOTE)]

# A live held while the team checks the Mobile Money payment the vendor announced
PAYMENT_TO_CHECK = ("vendor_kossi", STUDIO, "shelf", ("13:00", "11:30", "16:00"))
PAYMENT_REFERENCE = "Flooz 99 12 34 56 · réf. %s"

# The package of two lives of Brenda: one placed (remote, with Dzifa), one left to place
PACKAGE = ("vendor_brenda", "ocd_live.product_package_duo", "14:30", DZIFA)


def number(*parts):
    """A number that never changes for the same parts (a day, a vendor...)."""
    return zlib.crc32("|".join(str(part) for part in parts).encode())


def replay_url(live_url, day, xmlid):
    """The link of the video of a past live, on the platform of the live link of the vendor."""
    seed = number(xmlid, day)
    if "tiktok.com/@" in live_url:
        handle = live_url.split("tiktok.com/", 1)[1].split("/", 1)[0]
        return f"https://www.tiktok.com/{handle}/video/74{seed:010d}{seed % 10_000_000:07d}"
    if "facebook.com/" in live_url:
        page = live_url.split("facebook.com/", 1)[1].split("/", 1)[0]
        return f"https://www.facebook.com/{page}/videos/10{seed:010d}{seed % 1000:03d}"
    if "youtube.com/" in live_url:
        letters = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789_-"
        code = "".join(letters[(seed >> (index * 3)) % len(letters)] for index in range(11))
        return f"https://www.youtube.com/watch?v={code}"
    account = live_url.rstrip("/").rsplit("/", 2)[-2]
    return f"https://www.instagram.com/{account}/reel/C{seed:010d}/"
