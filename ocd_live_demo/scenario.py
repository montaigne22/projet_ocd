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
    # Added after the first ones (the steps already played keep their number): picked up at the
    # store of Brenda in Akwa (free), ready an hour later with the code, picked up the next
    # morning and paid on the phone at the counter
    ("14:10", "customer_herve", (("product_wax_pagne", None, 1),), "collect"),
    # At the relay point « Chez Rose » in Bonamoussadi (cheaper than at the door): the courier
    # takes it there at the end of the afternoon, picked up the next day at lunch time
    ("15:20", "customer_carine", (("product_wax_shirt", None, 1),), "relay"),
]
# Where the orders of these stories go: the store of the vendor, the relay point
SHOP_COLLECT_STORE = "akwa"
SHOP_RELAY = "relay_rose"
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
    # Picked up at the store: ready (the code sent), picked up the next morning, paid on the phone
    "collect": (("collect_ready", 55), ("counter", "+1 10:20")),
    # To a relay point: prepared, taken there by the courier, counted by the relay point, picked
    # up the next day with the code (paid on the phone: a relay point keeps no money)
    "relay": (("ready", 40), ("pick_up", 70), ("leave", 80), ("relay_receive", 125), ("relay_hand_over", "+1 12:30")),
    # Ordered during an evening live: prepared the next morning, delivered before noon
    "live": (("ready", "+1 09:20"), ("pick_up", "+1 10:15"), ("leave", "+1 10:25"), ("deliver_online", "+1 11:35")),
}
# A review after a delivery: most buyers give one, half an hour after (stars, word), in turn
REVIEW_AFTER_MINUTES = 35
REVIEWS = [
    (5, "Très belle qualité, livrée à l'heure. Je recommande !"),
    (4, "Bien reçu, le livreur a appelé avant. Un peu d'attente."),
    (5, ""),
]
# What the buyer says of the product (added to REVIEWS for a parcel delivered at home)
REVIEWS_BY_PRODUCT = {
    "product_wax_dress": ((4, "Belle robe, la taille taille un peu petit."),
                          (5, "Parfait, je recommanderai pour ma sœur.")),
    "product_wax_shirt": ((5, "Chemise bien coupée, mon mari l'adore."),),
    "product_wax_pagne": ((5, "Le tissu est magnifique, conforme aux photos."),),
    "product_shea_butter": ((5, "Karité bien pur, ma peau dit merci."),),
}
# What the buyer says of the way the parcel came (instead of the ones above)
REVIEWS_BY_STORY = {
    "late": ((3, "Correct, mais le colis est arrivé en retard."),
             (4, "Un jour de retard, mais on m'a prévenue. Bel article.")),
    "absent": ((4, "Le livreur est repassé le lendemain comme je l'avais demandé."),
               (5, "J'étais absent, ils sont revenus après 17 h. Parfait.")),
    "collect": ((5, "Retirée au magasin d'Akwa en cinq minutes, très bon accueil."), (5, "")),
    "relay": ((5, "Récupéré chez Rose en rentrant du travail, très pratique."),),
    "live": ((5, "Commandé pendant le live, reçu le lendemain matin. Top !"), (5, "Encore plus beau qu'en live !")),
}
# One parcel in REVIEW_SKIP has no review (not every buyer gives one)
REVIEW_SKIP = 3
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
    (  # Hervé picks up at the store of Akwa
        (2, "customer", "template", "whatsapp_cloud_sale.template_order_confirmed"),
        (40, "customer", "in", "Bonjour, je peux passer au magasin d'Akwa demain matin ?"),
        (44, "customer", "out", "Bonjour {first}, oui : le magasin ouvre à 8 h. Montrez votre code au comptoir."),
    ),
    (  # Carine at the relay point
        (2, "customer", "template", "whatsapp_cloud_sale.template_order_confirmed"),
        (150, "customer", "in", "C'est bien chez Rose, à côté du carrefour Kotto ?"),
        (153, "customer", "out", "Oui {first}, chez Rose, à côté du carrefour Kotto. Votre colis vous attend 7 jours."),
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


# === OCD EXPRESS IN DOUALA (when ocd_express is installed) ===
# Nadège Mode sells shoes, bags and clothes on Instagram and TikTok, without a shop on OCD Live: she
# sends her parcels with OCD Express from Akwa. One day of parcels, played on the working days of
# the last week and today (Monday to Saturday, hours of Douala): the parcels of the morning are
# picked up at 11:00 and delivered in the afternoon, those of the afternoon picked up at 16:00 and
# delivered the next working day; one parcel refused at the door goes back to her against her
# return code, one customer reports a problem in the evening (checked by the team two days later),
# one parcel above her limit waits for the team. The cash is handed over at 19:30 with the cash of
# the shop; her money is paid every working day at 10:00 (a payout prepared at 7:00).
EXPRESS_SENDER = "sender_nadege"
# A request to send parcels, waiting for the team (« To check »)
EXPRESS_REQUEST = "sender_linda"
EXPRESS_SOCIAL = "@nadege.mode (Instagram, TikTok)"
EXPRESS_REQUEST_SOCIAL = "@linda.cosmetiques (TikTok)"
EXPRESS_POINT = "Point OCD, boulevard de la Liberté, Akwa (adresse d'exemple)"
EXPRESS_MOMO = "Orange Money 690 00 00 00 (numéro d'exemple)"
EXPRESS_SINCE_DAYS = 45
# The customers of Nadège: (name, WhatsApp, district of Douala, landmark); the parcels of a day go to
# a different one each day
EXPRESS_CUSTOMERS = [
    ("Grâce Ngo Bayiha", "+237 699210101", "makepe", "Derrière la pharmacie du rond-point"),
    ("Paul Ebongue", "+237 699210102", "bonamoussadi", "Carrefour Kotto, immeuble jaune"),
    ("Mireille Etame", "+237 699210103", "bonaberi", "Face à l'école publique"),
    ("Aïcha Bello", "+237 699210104", "akwa", "Hôtel Akwa Palace, à la réception"),
    ("Rodrigue Kamga", "+237 699210105", "bonapriso", "Rue Njo-Njo, portail vert"),
    ("Carine Moukoko", "+237 699210106", "deido", "Marché de Deïdo, entrée principale"),
    ("Steve Tchoumi", "+237 699210107", "makepe", "Après la boulangerie de Missoké"),
    ("Laure Ndjock", "+237 699210108", "akwa", "Boulevard de la Liberté, immeuble Kassap"),
    ("Yannick Essomba", "+237 699210109", "bonamoussadi", "Derrière la station Tradex"),
    ("Nadia Ekambi", "+237 699210110", "bonaberi", "Ancienne route, en face du garage"),
    ("Hélène Mbappe", "+237 699210111", "kotto", "Kotto Bloc, près de la chapelle"),
]
# (hour, what is in the parcel, to collect, value of a parcel already paid, who pays the delivery,
# story of the parcel)
EXPRESS_DAY = [
    ("08:15", "Sac à main en cuir noir", 18000, 0, "sender", "cash"),
    ("08:40", "Baskets blanches, pointure 43", 22000, 0, "customer", "online"),
    ("09:05", "Deux perruques lisses", 25000, 0, "sender", "refused"),
    ("09:30", "Coffret de parfums", 0, 15000, "customer", "prepaid"),
    ("11:20", "Escarpins rouges, pointure 38", 20000, 0, "sender", "claim"),
    ("12:45", "Montre dorée pour homme", 30000, 0, "sender", "next_cash"),
    ("13:30", "Ensemble pagne, taille M", 16000, 0, "sender", "absent"),
    ("14:20", "Téléphone Samsung Galaxy A55", 245000, 0, "sender", "check"),
    ("17:30", "Robe de soirée longue", 35000, 0, "customer", "evening"),
]
# The steps of a parcel of OCD Express: minutes after its creation, or "+N HH:MM" N working days
# later (Monday to Saturday); its pick-up is the passage of its wave
EXPRESS_STORIES = {
    # Picked up in the morning, the customer pays cash at the door
    "cash": (("confirm", 25), ("leave", "+0 13:50"), ("deliver_cash", "+0 15:10")),
    # Paid on the phone of the customer (QR code shown by the courier)
    "online": (("leave", "+0 13:50"), ("deliver_online", "+0 14:35")),
    # Refused at the door: it goes back to Nadège, given back the next morning against her code
    "refused": (("confirm", 40), ("leave", "+0 13:50"), ("refused", "+0 16:10"), ("return", "+0 17:00"),
                ("hand_back", "+1 11:05")),
    # Already paid to Nadège: the customer pays only the delivery; she sends her position
    "prepaid": (("leave", "+0 13:50"), ("position", "+0 14:30"), ("deliver_cash", "+0 16:20")),
    # Delivered the next morning; the customer reports a problem in the evening, the team checks
    # it two days later (Nadège was right: her money leaves with the next payout)
    "claim": (("confirm", 30), ("leave", "+1 08:30"), ("deliver_online", "+1 10:15"), ("claim", "+1 18:30"),
              ("sender_right", "+3 11:00")),
    "next_cash": (("leave", "+1 08:30"), ("deliver_cash", "+1 09:40")),
    # Nobody at home the next morning: the courier comes back in the afternoon
    "absent": (("leave", "+1 08:30"), ("absent", "+1 10:30"), ("retry", "+1 15:30"), ("leave", "+1 15:45"),
               ("deliver_cash", "+1 16:40")),
    # Above the limit of Nadège: checked by the team, then picked up with the afternoon parcels
    "check": (("approve", "+0 14:50"), ("leave", "+1 08:30"), ("deliver_online", "+1 11:30")),
    # Created in the evening: picked up the next morning
    "evening": (("confirm", 15), ("leave", "+1 13:50"), ("deliver_cash", "+1 15:40")),
}
EXPRESS_PICKUPS = (("morning", "11:00"), ("afternoon", "16:00"))
EXPRESS_PAID = "10:00"
EXPRESS_CLAIM = "La pointure ne correspond pas : 39 au lieu de 38."
# Where the customer who sends her position is (Akwa)
EXPRESS_POSITION = (4.0483, 9.7043)


def express_phones():
    """The WhatsApp numbers (digits) of the customers of OCD Express of the demo: examples, no
    message goes to them."""
    return {"".join(char for char in phone if char.isdigit()) for _name, phone, _district, _landmark in EXPRESS_CUSTOMERS}


# === THE STORES, THE TEAM AND THE LIFE OF THE SHOP ===
# The places of the vendors (chantier 17): key, vendor, kind, name, district, landmark, position,
# state. Brenda has two stores in Douala (Akwa, where her parcels leave from; Bonapriso, held by
# Aïcha of her team), Fatou sells from home, Kossi has his store in Lomé; the store of Ama waits for
# the check of the team.
PLACES = [
    ("akwa", "vendor_brenda", "store", "Brenda Wax Akwa", "delivery_cameroon.district_douala_akwa",
     "En face de la pharmacie du Port", (4.0511, 9.6942), "approved"),
    ("bonapriso", "vendor_brenda", "store", "Brenda Wax Bonapriso", "delivery_cameroon.district_douala_bonapriso",
     "Rue Njo-Njo, à côté de la boulangerie", (4.0335, 9.6965), "approved"),
    ("fatou_home", "vendor_fatou", "home", "Fatou Karité", "delivery_cameroon.district_douala_makepe",
     "Makepe Missoké", (4.0732, 9.7455), "approved"),
    ("kossi_store", "vendor_kossi", "store", "Kossi Tech, Grand Marché", None,
     "Grand Marché de Lomé, allée des téléphones", (6.1319, 1.2228), "approved"),
    ("ama_store", "vendor_ama", "store", "Ama Pagnes, Assigamé", None,
     "Marché d'Assigamé, rangée des pagnes", (6.1305, 1.2236), "to_check"),
]
# The relay point of the demo (chantier 10): a shop of the neighbourhood held by a partner of OCD
# Live, where the courier of Bonamoussadi brings the parcels of the customers who chose it
RELAY_PLACE = ("relay_rose", "Chez Rose", "delivery_cameroon.district_douala_bonamoussadi",
               "Carrefour Kotto, à côté de la pharmacie", (4.0598, 9.7397), 30)
# A shop that asks to become a relay point, waiting for the visit of the team (« To check »):
# (holder, shop, district, landmark, what the shop does)
RELAY_REQUEST = ("relay_ngo", "Alimentation Ngo", "delivery_cameroon.district_douala_logpom",
                 "Face à la station Total de Logpom",
                 "Alimentation ouverte de 7 h à 22 h, tous les jours. Je connais tout le quartier.")
# The city of the places without a district (Lomé)
PLACE_CITIES = {"kossi_store": "ocd_delivery_togo.city_tg_lome", "ama_store": "ocd_delivery_togo.city_tg_lome"}
# The pieces of each store of Brenda (the website counts them all: the same as before)
PLACE_STOCK = {
    "product_wax_dress": {
        "akwa": {"Bleu": {"S": 4, "M": 2, "L": 0, "XL": 1}, "Rouge": {"S": 3, "M": 2, "L": 0, "XL": 0}},
        "bonapriso": {"Bleu": {"S": 1, "M": 1}, "Rouge": {"S": 1}},
    },
    "product_wax_shirt": {"akwa": 4, "bonapriso": 2},
    "product_wax_pagne": {"akwa": 3, "bonapriso": 1},
}
# The person of her team who holds the store of Bonapriso (chantier 22)
TEAM = [("vendor_brenda", "member_aicha", "Aïcha Njoya", "bonapriso")]
# She opens her store space when she opens the store (Douala)
TEAM_VISIT = "08:10"
# A piece held to try at the store of Bonapriso, every day (A.7): asked at 10:00, accepted by Aïcha
HOLD = ("customer_ruth", "product_wax_dress", ("Rouge", "S"), "bonapriso", "10:05", "10:25")
# The visits of the stores thanks to OCD (itinerary, call, WhatsApp) each day: (kind, how many)
PLACE_TAPS = {"akwa": (("itinerary", 3), ("call", 1), ("whatsapp", 2)),
              "bonapriso": (("itinerary", 1), ("whatsapp", 1)),
              "kossi_store": (("itinerary", 2), ("call", 2), ("whatsapp", 1))}
# Who follows whom (chantier 1): vendor, followers
FOLLOWERS = {
    "vendor_brenda": ("customer_estelle", "customer_ruth", "customer_sandrine", "customer_herve", "customer_carine"),
    "vendor_awa": ("customer_estelle", "customer_bertrand", "customer_ruth"),
    "vendor_kossi": ("customer_herve", "customer_bertrand"),
    "vendor_fatou": ("customer_sandrine", "customer_estelle"),
}
# They followed this many days ago, in turn
FOLLOWED_DAYS_AGO = (82, 64, 47, 31, 19)
# « Tell me » when a size is back (sold out): the blue dress in L
STOCK_ALERTS = (("product_wax_dress", ("Bleu", "L"), ("customer_estelle", "customer_sandrine", "customer_carine")),)
# The vendors checked by the team (« Verified vendor »)
VERIFIED = ("vendor_brenda", "vendor_fatou", "vendor_kossi", "vendor_awa")
# A product reported by a customer, waiting for the team (« To check »)
REPORT = ("product_kente", "customer_bertrand", "fake", "Le même kente est vendu deux fois moins cher ailleurs, "
                                                        "je pense que ce n'est pas du tissé main.")
# The promo of the week of Brenda (3.1), from Monday to Sunday: (product, price)
PROMO = ("product_wax_pagne", 0.8)
# The products prepared for the next lives of Brenda (21): what the host shows, in this order
PREPARED = ("vendor_brenda", ("product_wax_dress", "product_wax_shirt", "product_wax_pagne"),
            "Je commence par la robe bleue, puis la chemise. Montrer le pagne en dernier.")
# A product on sale whose new name waits for the team, and a product refused, to correct
CHANGE = ("product_powerbank", "Batterie externe 20 000 mAh, charge rapide")
# The figures of the vendors day by day (chantier 3): visits of the boutique, WhatsApp contacts,
# lives opened from OCD; the last 90 days, more for the vendors of the shop
FIGURES_DAYS = 90
FIGURES = {
    "vendor_brenda": (38, 9, 26), "vendor_fatou": (17, 5, 11), "vendor_kossi": (24, 8, 19),
    "vendor_awa": (21, 6, 15), "vendor_ama": (14, 4, 10), "vendor_papa": (12, 4, 9),
}
FIGURES_OTHERS = (6, 2, 5)
# The sales of the lives of the vendors of the shop (« My figures » › « My lives »): during each
# live, the boutique is visited, customers order (counted for the live: they came during it) and
# a viewer follows. (minutes after the start, products as in SHOP_DAY), the customers in turn.
LIVE_SALES = {
    "vendor_brenda": ((20, (("product_wax_dress", (("Bleu", "M"), ("Rouge", "S"), ("Bleu", "S")), 1),)),
                      (45, (("product_wax_shirt", None, 1), ("product_wax_pagne", None, 1)))),
    "vendor_fatou": ((25, (("product_shea_butter", None, 2),)),),
}
LIVE_CUSTOMERS = ("customer_estelle", "customer_ruth", "customer_carine", "customer_herve", "customer_sandrine",
                  "customer_bertrand")
# Visits of the boutique during a live: from LIVE_VISITS[0], up to LIVE_VISITS[1] more; the
# visits and the new follower are counted at these minutes after the start
LIVE_VISITS = (28, 40)
# The lives of the week behind sell, from the first day of the demo
LIVE_PAST_DAYS = PAST_DAYS
LIVE_VISITS_AFTER = 50
LIVE_FOLLOW_AFTER = 35
