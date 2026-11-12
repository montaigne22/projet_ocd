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
from datetime import timedelta

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
# Their phone, for the vendors of the remote lives (« Call » on the page « Join my live »)
HOST_PHONES = {DZIFA: "+228 90112280", KAFUI: "+228 90112281"}

# The cards of the feed: a short video, an image; the others show the carousel of their
# products (automatic)
CARD_VIDEOS = {"vendor_awa": "awa_gateaux.mp4"}
CARD_IMAGES = {"vendor_ama": "ensemble_pagne.jpg"}
# Where the products of the vendor are shown in the video of a replay, as shares of its length
# (a live of 1 h 30: at 4 min 30, 21 min 36 and 43 min 12)
MOMENT_SHARES = (0.05, 0.24, 0.48)
# Length of the example videos (a live), and of a video of the settings by default
REPLAY_MINUTES = 90

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


# === THE SHOP IN DOUALA ===
# One day of orders (hours of Douala), played on the last week and today, then every day: the
# customers order in the morning and the afternoon, Brenda's parcels go with an OCD courier
# (Junior Ekwalla in Akwa, Makepe and Bonabéri, Raoul Nyobe in Bonabéri and Bonamoussadi), Fatou
# delivers hers. Each parcel follows its story; the couriers hand over their cash at 19:30; the
# payouts of the vendors are prepared at 7:00 and paid by the team at 10:00 the next day.
SHOP_TZ = "Africa/Douala"
SHOP_PAST_DAYS = 6
# (hour, customer, lines, story of the parcel of Brenda): a line is (product, its variants, one
# per day in turn, quantity)
SHOP_DAY = [
    ("08:45", "customer_estelle", (("product_wax_dress", (("Bleu", "S"), ("Rouge", "S")), 1),
                                   ("product_shea_butter", None, 2)), "cash"),
    ("09:10", "customer_sandrine", (("product_wax_shirt", None, 1),), "late"),
    ("10:30", "customer_herve", (("product_wax_shirt", None, 1),), "cash"),
    ("12:15", "customer_ruth", (("product_wax_dress", (("Rouge", "M"), ("Bleu", "XL")), 1),), "online"),
    ("13:20", "customer_bertrand", (("product_wax_pagne", None, 1),), "absent"),
    ("16:50", "customer_sandrine", (("product_shea_butter", None, 2),), "cash"),
]
# The steps of a parcel: minutes after the order, or "+1 HH:MM" the next day
STORIES = {
    # An OCD courier picks the parcel up at the vendor, the customer pays cash at the door
    "cash": (("ready", 60), ("pick_up", 120), ("leave", 130), ("deliver_cash", 190)),
    # The same, paid on the phone of the customer (QR code shown by the courier)
    "online": (("ready", 60), ("pick_up", 120), ("leave", 130), ("deliver_online", 190)),
    # The vendor does not prepare in time: reminded, then the dispatch is alerted; ready the
    # next afternoon
    "late": (("remind", 240), ("escalate", 360), ("ready", "+1 15:30"), ("pick_up", "+1 16:00"),
             ("leave", "+1 16:10"), ("deliver_cash", "+1 17:10")),
    # Nobody at home: the courier comes back the next day after 17:00, as asked
    "absent": (("ready", 60), ("pick_up", 120), ("leave", 130), ("absent", 190), ("retry", "+1 17:15"),
               ("leave", "+1 17:20"), ("deliver_cash", "+1 17:50")),
    # The vendor delivers herself; the customer pays on the phone
    "vendor": (("ready", 60), ("leave", 90), ("deliver_online", 150)),
    # Ordered in the evening from a vendor who delivers herself: the next morning
    "vendor_evening": (("ready", "+1 08:30"), ("leave", "+1 09:30"), ("deliver_online", "+1 10:30")),
}
VENDOR_EVENING_FROM = "16:00"
# The WhatsApp conversations of each order: (when, with whom, kind, text or template). Kinds:
# "template" (a message of OCD Live), "in" (written by the contact), "wait" (written by the
# contact, waiting for an answer), "out" (answer of the team), "note" (note of the team). In the
# texts: {first} the first name of the customer, {courier} the first name of the courier,
# {vendor} the name of the vendor, {delivered} the hour of the delivery (Douala).
SHOP_TALKS = [
    (  # Estelle: when does the courier come?
        (2, "customer", "template", "whatsapp_cloud_sale.template_order_confirmed"),
        (45, "customer", "wait", "Bonjour, le livreur arrive à quelle heure ? Je dois sortir à 13 h."),
        (95, "customer", "out", "Bonjour {first}, {courier} passe vers {delivered} et vous appelle avant."),
    ),
    (  # Sandrine: Brenda is late
        (2, "vendor", "template", "ocd_live_shop_whatsapp.template_parcel_to_prepare"),
        (240, "vendor", "template", "ocd_live_shop_whatsapp.template_parcel_reminder"),
        ("+1 10:05", "customer", "wait", "Bonjour, ma chemise d'hier arrive quand ?"),
        ("+1 10:35", "customer", "out", "Bonjour {first}, {vendor} la prépare : le livreur passe cet après-midi, vers {delivered}."),
    ),
    (  # Hervé: where is the courier?
        (2, "customer", "template", "whatsapp_cloud_sale.template_order_confirmed"),
        (130, "customer", "template", "ocd_live_shop_whatsapp.template_parcel_on_the_way"),
        (160, "customer", "in", "Bonjour, il est où le livreur ? Je suis à la maison."),
        (164, "customer", "out", "{courier} arrive dans 20 minutes, il vous appelle avant. Gardez bien votre code."),
        (166, "customer", "in", "D'accord, merci !"),
    ),
    (  # Ruth: paying by Mobile Money at the door
        (2, "customer", "template", "whatsapp_cloud_sale.template_order_confirmed"),
        (75, "customer", "wait", "Bonjour, je peux payer par Mobile Money à la livraison ?"),
        (110, "customer", "out", "Oui {first} : {courier} vous montre un QR code et vous payez sur votre téléphone."),
    ),
    (  # Bertrand: absent, the courier comes back the next day
        (2, "customer", "template", "whatsapp_cloud_sale.template_order_confirmed"),
        (130, "customer", "template", "ocd_live_shop_whatsapp.template_parcel_on_the_way"),
        (190, "customer", "template", "ocd_live_shop_whatsapp.template_parcel_failed"),
        (210, "customer", "wait", "Pardon, j'étais en réunion. Vous pouvez repasser demain après 17 h ?"),
        (213, "customer", "note", "{courier} peut repasser demain à 17 h 15 : à confirmer avec le dispatch."),
        ("+1 08:40", "customer", "out", "Bonjour {first}, c'est noté : {courier} repasse aujourd'hui vers 17 h 15."),
    ),
    (  # Sandrine, in the evening: Fatou delivers the next morning
        (2, "vendor", "template", "ocd_live_shop_whatsapp.template_parcel_to_prepare"),
        ("+1 08:35", "vendor", "in", "C'est prêt, je pars à 9 h 30."),
        ("+1 08:40", "vendor", "out", "Merci Fatou ! {first} attend son colis ce matin."),
    ),
]
CASH_HANDOVER = "19:30"
PAYOUTS_PREPARED = "07:00"
PAYOUTS_PAID = "10:00"
PAYOUT_REFERENCE = "MoMo %s"
# The ended steps of the demo are forgotten after two weeks
KEEP_STEPS_DAYS = 14


def when(moment, step_time):
    """The moment of a step: `moment` (the order, a datetime of Douala) plus minutes, or
    "+1 HH:MM" the next day."""
    if isinstance(step_time, int):
        return moment + timedelta(minutes=step_time)
    days, hour = step_time.split(" ")
    hours, minutes = (int(part) for part in hour.split(":"))
    return (moment + timedelta(days=int(days))).replace(hour=hours, minute=minutes)


def hour_text(moment):
    """« 12 h », « 13 h 45 »: the hour to the quarter, as said in Douala."""
    minutes = round((moment.hour * 60 + moment.minute) / 15) * 15
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h" if not minutes else f"{hours} h {minutes:02d}"
