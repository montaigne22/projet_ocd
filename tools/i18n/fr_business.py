# Chantier 12: OCD Business (ocd_business, ocd_business_whatsapp). « tu » on the site (the space of the
# vendor), neutral in the back office.

BUSINESS_DESCRIPTION = """
OCD Business
============

- La formule est une suite de périodes : payées (une par ligne de commande payée,
  unique dans la base), offertes par l'équipe (avec un motif), offertes au
  lancement. « Jusqu'au » se lit dans les périodes, ne se tape jamais ; une nouvelle
  période commence le lendemain de la dernière, ou aujourd'hui si la formule est
  terminée : aucun jour n'est perdu. Le vendeur est verrouillé le temps de calculer
  les dates.
- Achetée depuis l'espace du vendeur (1, 3 ou 12 mois, prix dans les réglages, dans
  la devise de chaque pays) avec le paiement d'OCD Live ; la durée et le prix sont
  ceux de la commande. Une facture par paiement.
- Un Mobile Money vérifié par l'équipe : « J'ai payé » garde les fonctions 3 jours
  après la fin, le temps de la vérification ; vérifié, les jours partent de la fin
  de la formule.
- Un remboursement reprend les jours pas encore passés, jamais en arrière ; les
  périodes suivantes se rapprochent.
- Rappels 7 jours avant et la veille, à l'heure du vendeur, une fois par date de
  fin ; la fin est dite. Rien n'est effacé à la fin : le magasin de départ des
  colis reste visible, l'équipe se met en pause, les chiffres en détail se cachent.
- Le lancement : les vendeurs qui utilisent les fonctions reçoivent une fois les
  mois des réglages, avant que les fonctions offertes à tous s'arrêtent.
- « Mon espace » › OCD Business, la ligne avant et après la fin, le chemin vers la
  formule depuis chaque fonction qu'elle garde, la page /business, le back-office.
"""

BUSINESS = {
    # The space of the vendor (« tu »)
    "%(count)s of %(max)s": "%(count)s sur %(max)s",
    "%s days": "%s jours",
    "%s months": "%s mois",
    "%s months offered": "%s mois offerts",
    "%s per month": "%s par mois",
    "1 month": "1 mois",
    "1 month offered": "1 mois offert",
    "12 months": "12 mois",
    ", then « OCD Business » in your space.": ", puis « OCD Business » dans ton espace.",
    "<b>For all, always</b>\n                                <small class=\"o_ocd_biz_muted\">Your boutique, your products, one store, the pick-up at the store, the promos, the lives, the clips, the ambassadors, the payouts.</small>":
        "<b>Pour tous, toujours</b>\n                                <small class=\"o_ocd_biz_muted\">Ta boutique, tes produits, un magasin, le retrait en magasin, les promos, les lives, les clips, les ambassadeurs, les reversements.</small>",
    "<b>Grow with the formula</b><span>Your other stores, your team, your figures, OCD Express.</span>":
        "<b>Grandis avec la formule</b><span>Tes autres magasins, ton équipe, tes chiffres, OCD Express.</span>",
    "<b>If the formula stops</b>\n                                <small class=\"o_ocd_biz_muted\">Your stores beyond the first one are hidden from your customers (the orders still leave from their stock; the store your parcels leave from stays shown), your team is paused, your figures in detail are hidden, your news go once a month. Nothing is ever erased: everything comes back when you renew.</small>":
        "<b>Si la formule s'arrête</b>\n                                <small class=\"o_ocd_biz_muted\">Tes magasins en plus sont masqués à tes clients (les commandes partent toujours de leur stock ; le magasin de départ de tes colis reste visible), ton équipe est en pause, tes chiffres en détail sont cachés, tes nouveautés partent une fois par mois. Rien n'est jamais effacé : tout revient quand tu renouvelles.</small>",
    "<b>Open your boutique</b><span>Free: your products, one store, a commission on each sale.</span>":
        "<b>Ouvre ta boutique</b><span>Gratuit : tes produits, un magasin, une commission sur chaque vente.</span>",
    "<b>The features of OCD Business are offered to all during the launch.</b>":
        "<b>Les fonctions d'OCD Business sont offertes à tous pendant le lancement.</b>",
    "<b>With OCD Business</b>\n                                <span class=\"o_ocd_biz_check\"><b>Several stores</b> and the stock of each; the customers see « Available in Akwa »</span>\n                                <span class=\"o_ocd_biz_check\"><b>Your team</b>: the people who hold your stores, without the prices or the money</span>\n                                <span class=\"o_ocd_biz_check\"><b>Your figures in detail</b>: each live, your best hours, your loyal customers, each product</span>\n                                <span class=\"o_ocd_biz_check\"><b>Your news every week</b> to those who follow you (once a month without the formula)</span>\n                                <span class=\"o_ocd_biz_check\"><b>OCD Express</b>: your parcels outside the boutique, account open at once, the small pick-up free</span>":
        "<b>Avec OCD Business</b>\n                                <span class=\"o_ocd_biz_check\"><b>Plusieurs magasins</b> et le stock de chacun ; les clients voient « Disponible à Akwa »</span>\n                                <span class=\"o_ocd_biz_check\"><b>Ton équipe</b> : les personnes qui tiennent tes magasins, sans les prix ni l'argent</span>\n                                <span class=\"o_ocd_biz_check\"><b>Tes chiffres en détail</b> : chaque live, tes meilleures heures, tes clients fidèles, chaque produit</span>\n                                <span class=\"o_ocd_biz_check\"><b>Tes nouveautés chaque semaine</b> à ceux qui te suivent (une fois par mois sans la formule)</span>\n                                <span class=\"o_ocd_biz_check\"><b>OCD Express</b> : tes colis hors boutique, compte ouvert tout de suite, le petit ramassage gratuit</span>",
    "<small class=\"o_ocd_biz_muted\">Mobile Money, Wave or card, with the payment of OCD Live. Nothing is debited: you renew when you want, you are told before the end.</small>":
        "<small class=\"o_ocd_biz_muted\">Mobile Money, Wave ou carte, avec le paiement d'OCD Live. Rien n'est prélevé : tu renouvelles quand tu veux, on te prévient avant la fin.</small>",
    "<small><b>Your formula</b></small>": "<small><b>Ta formule</b></small>",
    "<small>Stores</small>": "<small>Magasins</small>",
    "<small>Your team</small>": "<small>Ton équipe</small>",
    "<span class=\"o_ocd_biz_badge\">For the organised vendors</span>":
        "<span class=\"o_ocd_biz_badge\">Pour les vendeurs organisés</span>",
    "<span>For the shops, even without lives: your products on OCD Live, delivered with a code, the money paid after the delivery.</span>":
        "<span>Pour les commerçants, même sans live : tes produits sur OCD Live, livrés avec un code, l'argent versé après la livraison.</span>",
    "<span>OCD Business</span>": "<span>OCD Business</span>",
    "<span>What makes you sell stays free for all. OCD Business adds what helps when you grow.</span>":
        "<span>Ce qui fait vendre reste gratuit pour tous. OCD Business ajoute ce qui sert quand tu grandis.</span>",
    "<span>Without commitment, paid when you want.</span>": "<span>Sans engagement, payé quand tu veux.</span>",
    "A payment of OCD Business is on its way.": "Un paiement d'OCD Business est en cours.",
    "Choose your formula": "Choisis ta formule",
    "Hello, I want to open my boutique on OCD Live.": "Bonjour, je veux ouvrir ma boutique sur OCD Live.",
    "Invoice": "Facture",
    "Log in": "Me connecter",
    "Not shown to your customers: one store without OCD Business.": "Pas visible de tes clients : un magasin sans OCD Business.",
    "More stores come with OCD Business.": "D'autres magasins viennent avec OCD Business.",
    "The team comes with OCD Business: the people who hold your stores, without the prices or the money.":
        "L'équipe vient avec OCD Business : les personnes qui tiennent tes magasins, sans les prix ni l'argent.",
    "OCD Business": "OCD Business",
    "Offered at the launch": "Offert au lancement",
    "Offered by the team": "Offert par l'équipe",
    "Offered to all until %s.": "Offertes à tous jusqu'au %s.",
    "Open my boutique: write to OCD Live": "Ouvrir ma boutique : écrire à OCD Live",
    "Paid: thank you. Your formula runs %s.": "Payé : merci. Ta formule court %s.",
    "Renew": "Renouveler",
    "Renew OCD Business": "Renouveler OCD Business",
    "Renew it to keep your stores shown, your team and your figures in detail.":
        "Renouvelle-la pour garder tes magasins visibles, ton équipe et tes chiffres en détail.",
    "Renewing adds days after this date: no day is lost.": "Renouveler ajoute des jours après cette date : aucun jour n'est perdu.",
    "Running": "En cours",
    "See OCD Business": "Voir OCD Business",
    "See my payment": "Voir mon paiement",
    "Several stores, a team, your figures in detail": "Plusieurs magasins, une équipe, tes chiffres en détail",
    "Thank you: your payment is on its way. Your formula is added as soon as it is confirmed.":
        "Merci : ton paiement est en cours. Ta formule est ajoutée dès qu'il est confirmé.",
    "You already sell on OCD Live?": "Tu vends déjà sur OCD Live ?",
    "Your features of OCD Business then stay while the team checks the payment.":
        "Tes fonctions d'OCD Business restent alors le temps que l'équipe vérifie le paiement.",
    "Your features stay until %s, the time of the check.": "Tes fonctions restent jusqu'au %s, le temps de la vérification.",
    "Your formula OCD Business ended on %s.": "Ta formule OCD Business s'est terminée le %s.",
    "Your formula OCD Business ends on %s.": "Ta formule OCD Business se termine le %s.",
    "Your hour then stays held while the team checks the payment. Without it, the hour is offered again to the others.":
        "Ton heure reste alors gardée pendant que l'équipe vérifie le paiement. Sans ça, l'heure est de nouveau proposée aux autres.",
    "Your online shop, your stores, your deliveries": "Ta boutique en ligne, tes magasins, tes livraisons",
    "Your payment of OCD Business is being checked.": "Ton paiement d'OCD Business est en cours de vérification.",
    "Your stores beyond the first one are hidden, your team is paused: nothing is erased, everything comes back with the formula.":
        "Tes magasins en plus sont masqués, ton équipe est en pause : rien n'est effacé, tout revient avec la formule.",
    "payment being checked": "paiement en cours de vérification",
    "until %s": "jusqu'au %s",
    # Back office (neutral)
    "%(days)s days of OCD Business offered by %(user)s: %(note)s": "%(days)s jours d'OCD Business offerts par %(user)s : %(note)s",
    "%s vendors with a formula running.": "%s vendeurs avec une formule en cours.",
    "A formula of OCD Business lasts one day at least.": "Une formule OCD Business dure un jour au moins.",
    "A paid line gives one period of OCD Business.": "Une ligne payée donne une période d'OCD Business.",
    "A period of OCD Business ends after it starts.": "Une période d'OCD Business finit après son début.",
    "A vendor buys OCD Business from their space (« OCD Business »); the team offers days from the form of the vendor.":
        "Un vendeur achète OCD Business depuis son espace (« OCD Business ») ; l'équipe offre des jours depuis la fiche du vendeur.",
    "Add the days bought after the end of the formula (or from today), once per payment.\nMake the invoice of the payment.\nTell the vendor until when.":
        "Ajouter les jours achetés après la fin de la formule (ou à partir d'aujourd'hui), une fois par paiement.\nFaire la facture du paiement.\nDire au vendeur jusqu'à quand.",
    "After « I paid » for a Mobile Money checked by the team: the features stay this long after the end, the time of the check.":
        "Après « J'ai payé » pour un Mobile Money vérifié par l'équipe : les fonctions restent ce temps après la fin, le temps de la vérification.",
    "Days": "Jours",
    "Days Of OCD Business": "Jours d'OCD Business",
    "Days not passed yet taken back: %s": "Jours pas encore passés repris : %s",
    "End Told For": "Fin dite pour",
    "First Reminder Sent For": "Premier rappel envoyé pour",
    "First reminder": "Premier rappel",
    "Formula paid: the days added": "Formule payée : les jours ajoutés",
    "Formulas: reminders, end and launch": "Formules : rappels, fin et lancement",
    "Give one day at least.": "Donner un jour au moins.",
    "Grace for a payment checked": "Grâce pour un paiement vérifié",
    "Included.": "Inclus.",
    "Later": "Plus tard",
    "Launch": "Lancement",
    "Launch Of OCD Business": "Lancement d'OCD Business",
    "Launch Of OCD Business Done": "Lancement d'OCD Business fait",
    "Months Offered At The Launch": "Mois offerts au lancement",
    "Months offered at the launch": "Mois offerts au lancement",
    "No formula yet": "Pas encore de formule",
    "OCD Business (1 month)": "OCD Business (1 mois)",
    "OCD Business (12 months)": "OCD Business (12 mois)",
    "OCD Business (3 months)": "OCD Business (3 mois)",
    "OCD Business Kept Until (Payment Checked)": "OCD Business gardé jusqu'au (paiement vérifié)",
    "OCD Business until": "OCD Business jusqu'au",
    "OCD Business: First Reminder (Days Before)": "OCD Business : premier rappel (jours avant)",
    "OCD Business: Grace For A Payment Checked (Days)": "OCD Business : grâce pour un paiement vérifié (jours)",
    "OCD Business: the monthly formula of the organised vendors": "OCD Business : la formule mensuelle des vendeurs organisés",
    "OCD Live: OCD Business": "OCD Live : OCD Business",
    "OCD Live: formulas of OCD Business": "OCD Live : formules d'OCD Business",
    "Offer": "Offrir",
    "Offer Days Of OCD Business": "Offrir des jours d'OCD Business",
    "Offer between 1 and 400 days.": "Offrir entre 1 et 400 jours.",
    "Offer days": "Offrir des jours",
    "Offer days of OCD Business": "Offrir des jours d'OCD Business",
    "Offered": "Offertes",
    "Offered By": "Offert par",
    "Offered at the launch of OCD Business": "Offert au lancement d'OCD Business",
    "Only a manager of OCD Live offers days of OCD Business.": "Seul un responsable d'OCD Live offre des jours d'OCD Business.",
    "Only a manager of OCD Live takes back days of OCD Business.": "Seul un responsable d'OCD Live reprend des jours d'OCD Business.",
    "Order %s cancelled": "Commande %s annulée",
    "Paid in advance, never debited; in the currency of each country, as the directory pass. A price changed counts for the next payments.":
        "Payé d'avance, jamais prélevé ; dans la devise de chaque pays, comme le pass de l'annuaire. Un prix changé vaut pour les paiements suivants.",
    "Period Of OCD Business": "Période d'OCD Business",
    "Period of OCD Business": "Période d'OCD Business",
    "Periods Of OCD Business": "Périodes d'OCD Business",
    "Periods of OCD Business": "Périodes d'OCD Business",
    "Refunded, by %s": "Remboursé, par %s",
    "Refunded: take back the days": "Remboursé : reprendre les jours",
    "Remind the vendor the days of the settings before the end, then the day before, once per date of end.\nAt the end, tell what is paused (nothing is erased).\nThe day of the launch, offer the months of the settings to the vendors who use the features, then stop the features offered to all.":
        "Rappeler au vendeur les jours des réglages avant la fin, puis la veille, une fois par date de fin.\nÀ la fin, dire ce qui est en pause (rien n'est effacé).\nLe jour du lancement, offrir les mois des réglages aux vendeurs qui utilisent les fonctions, puis arrêter les fonctions offertes à tous.",
    "Reminder Of The Day Before Sent For": "Rappel de la veille envoyé pour",
    "Sales, Invoicing, code of OCD Live.": "Ventes, Facturation, code d'OCD Live.",
    "Set by hand before OCD Business": "Mis à la main avant OCD Business",
    "Started this month": "Commencées ce mois-ci",
    "The date of end of each formula, at the hour of the vendor; the day of the launch.":
        "La date de fin de chaque formule, à l'heure du vendeur ; le jour du lancement.",
    "The days not passed yet are taken back; the periods after it come closer.":
        "Les jours pas encore passés sont repris ; les périodes suivantes se rapprochent.",
    "The days of the formula one piece gives, from the end of the current one.":
        "Les jours de formule que donne une pièce, à partir de la fin de la formule en cours.",
    "The formula OCD Business for 30 days": "La formule OCD Business pour 30 jours",
    "The formula OCD Business for 365 days": "La formule OCD Business pour 365 jours",
    "The formula OCD Business for 90 days": "La formule OCD Business pour 90 jours",
    "The formulas": "Les formules",
    "The invoice could not be made: %s": "La facture n'a pas pu être faite : %s",
    "The monthly formula of the organised vendors: several stores and their stock, their team, their figures in detail, their news every week, OCD Express; paid in advance, never debited":
        "La formule mensuelle des vendeurs organisés : plusieurs magasins et leur stock, leur équipe, leurs chiffres en détail, leurs nouveautés chaque semaine, OCD Express ; payée d'avance, jamais prélevée",
    "The payment confirmed by its provider, or checked by the team.": "Le paiement confirmé par son fournisseur, ou vérifié par l'équipe.",
    "The vendors who buy OCD Business.": "Les vendeurs qui achètent OCD Business.",
    "The vendors with a formula.": "Les vendeurs avec une formule.",
    "Then the day before; once per date of end, never after a renewal.":
        "Puis la veille ; une fois par date de fin, jamais après un renouvellement.",
    "Then the day before; one message per date of end, never after a renewal.":
        "Puis la veille ; un message par date de fin, jamais après un renouvellement.",
    "This day, the features offered to all stop (« OCD Business features offered to all », section Stores); the vendors who use them receive the months below first.":
        "Ce jour-là, les fonctions offertes à tous s'arrêtent (« Fonctions OCD Business offertes à tous », section Magasins) ; les vendeurs qui les utilisent reçoivent d'abord les mois ci-dessous.",
    "This day, the features offered to all stop; the vendors who use them receive the months of the settings first, once.":
        "Ce jour-là, les fonctions offertes à tous s'arrêtent ; les vendeurs qui les utilisent reçoivent d'abord les mois des réglages, une fois.",
    "To the vendors who use the features (several stores, a team) on the day of the launch.":
        "Aux vendeurs qui utilisent les fonctions (plusieurs magasins, une équipe) le jour du lancement.",
    "To the vendors with several stores or a team, once.": "Aux vendeurs avec plusieurs magasins ou une équipe, une fois.",
    "WhatsApp, code of OCD Live.": "WhatsApp, code d'OCD Live.",
    "When a payment of OCD Business is confirmed": "Quand un paiement d'OCD Business est confirmé",
    "Why the team offered these days, or cancelled them.": "Pourquoi l'équipe a offert ces jours, ou les a annulés.",
    "e.g. a gesture after a problem, a vendor tested": "ex. un geste après un problème, un vendeur testé",
    "« I paid » for a Mobile Money checked by the team: the features stay this long after the end.":
        "« J'ai payé » pour un Mobile Money vérifié par l'équipe : les fonctions restent ce temps après la fin.",
    "« I paid » for a Mobile Money checked by the team: the features stay until this day, the time of the check.":
        "« J'ai payé » pour un Mobile Money vérifié par l'équipe : les fonctions restent jusqu'à ce jour, le temps de la vérification.",
}

BUSINESS_WHATSAPP = {
    "%s months": "%s mois",
    "1 month": "1 mois",
    "OCD Business on WhatsApp: the formula paid, its end close, its end, the months offered at the launch":
        "OCD Business sur WhatsApp : la formule payée, sa fin proche, sa fin, les mois offerts au lancement",
    "OCD Business: formula paid": "OCD Business : formule payée",
    "OCD Business: formula paid (English)": "OCD Business : formule payée (anglais)",
    "OCD Business: months offered at the launch": "OCD Business : mois offerts au lancement",
    "OCD Business: months offered at the launch (English)": "OCD Business : mois offerts au lancement (anglais)",
    "OCD Business: the end is close": "OCD Business : la fin approche",
    "OCD Business: the end is close (English)": "OCD Business : la fin approche (anglais)",
    "OCD Business: the formula ended": "OCD Business : la formule est terminée",
    "OCD Business: the formula ended (English)": "OCD Business : la formule est terminée (anglais)",
    "OCD Live: OCD Business On WhatsApp": "OCD Live : OCD Business sur WhatsApp",
}
