# Chantier 11: the ambassadors (ocd_ambassadors, ocd_ambassadors_whatsapp). « tu » on the site,
# neutral in the back office.

AMBASSADORS_DESCRIPTION = """
Ambassadeurs
============

- Chacun s'inscrit sur /ambassadeurs avec son numéro WhatsApp (vérifié par un code)
  et son Mobile Money ; la charte est acceptée. Programme ouvert à tous, sur
  invitation ou fermé (réglages).
- « Mon espace ambassadeur » : à verser lundi, en attente, les ventes de la semaine
  et leur état ; « Mon argent » (le détail du versement, les retours retirés, les
  versements faits, un nouveau numéro retenu 48 h) ; « Produits à partager » (les
  plus vendus, les promos, en live ce soir, ce qu'on gagne) ; « Partager » (l'image
  faite par OCD Live au prix du moment avec le lien personnel, le texte, le statut
  WhatsApp, un contact, le clip du live) ; « Mes liens » (n'importe quelle page du
  site).
- Le lien personnel /a/<code> est gardé 7 jours sur le téléphone ; le dernier lien
  ouvert compte, pour tous les articles de la commande ; l'ambassadeur, le taux et
  le plafond sont inscrits sur la commande à sa confirmation. Les robots et les
  propres visites de l'ambassadeur ne comptent pas. « Grâce te recommande ce
  produit » sur la fiche produit.
- Le gain : 5 % des articles (pas la livraison), au plus 3 000 F par colis et jamais
  plus que la commission d'OCD sur l'article, payé par OCD. Un gain par colis :
  gagné à la livraison avec le code, confirmé 7 jours plus tard (une facture de
  l'ambassadeur), un retour plus tard repris (un avoir) ; versé avec les
  reversements du shop chaque semaine, jamais un solde négatif.
- Contre la fraude : jamais sur ses propres achats (numéro, Mobile Money, compte, sa
  boutique), 5 commandes d'un même client par mois, mis en pause tout seul au-delà
  de 30 % de retours, un Mobile Money par personne, pièce d'identité au-delà de
  50 000 F, un nouveau numéro de versement retenu 48 h. « À vérifier » de l'équipe,
  réglages, automatisations.
- Le vendeur voit « Vendu grâce aux ambassadeurs » dans « Mes chiffres ».
"""

AMBASSADORS = {
    # The site (« tu »)
    "%(amount)s confirmed on %(day)s": "%(amount)s confirmés le %(day)s",
    "%(count)s parcels delivered less than %(days)s days ago": "%(count)s colis livrés il y a moins de %(days)s jours",
    "1 visit": "1 visite",
    "%s visits": "%s visites",
    "1 delivered": "1 livré",
    "%s delivered": "%s livrés",
    "Payouts made": "Versements faits",
    "%s if it is delivered and kept": "%s s'il est livré et gardé",
    "%s in your next payout": "%s dans ton prochain versement",
    "%s on the way": "%s en route",
    "%s paid": "%s versés",
    "%s waits for the decision of the team": "%s attend la décision de l'équipe",
    "%s · waits before a payout": "%s · attend avant un versement",
    "1 on the way": "1 en route",
    "1 parcel delivered less than %s days ago": "1 colis livré il y a moins de %s jours",
    "<b>Choose a product</b><span>The best sellers, the promos, the ones in live tonight.</span>":
        "<b>Choisis un produit</b><span>Les plus vendus, les promos, ceux en live ce soir.</span>",
    "<b>My link to the shop</b>": "<b>Mon lien vers le shop</b>",
    "<b>My payout number</b>": "<b>Mon numéro de versement</b>",
    "<b>Receive your gains every Monday</b>": "<b>Reçois tes gains chaque lundi</b>",
    "<b>Request sent.</b>\n                            <span>The team of OCD Live opens your account and tells you on WhatsApp.</span>":
        "<b>Demande envoyée.</b>\n                            <span>L'équipe d'OCD Live ouvre ton compte et te prévient sur WhatsApp.</span>",
    "<b>Share it</b><span>WhatsApp status, a contact, TikTok: the image and the text are ready, with your link.</span>":
        "<b>Partage-le</b><span>Statut WhatsApp, un contact, TikTok : l'image et le texte sont prêts, avec ton lien.</span>",
    "<b>The link of any page</b>\n                <small class=\"o_ocd_amb_muted\">A boutique, a live, the programme: paste its address, your link is made.</small>":
        "<b>Le lien de n'importe quelle page</b>\n                <small class=\"o_ocd_amb_muted\">Une boutique, un live, le programme : colle son adresse, ton lien est fait.</small>",
    "<i aria-hidden=\"true\"/><span class=\"o_ocd_amb_reco_text\">%s recommends this product to you</span>":
        "<i aria-hidden=\"true\"/><span class=\"o_ocd_amb_reco_text\">%s te recommande ce produit</span>",
    "<small class=\"o_ocd_amb_muted\">In your name: it is checked before the first payout.</small>":
        "<small class=\"o_ocd_amb_muted\">À ton nom : il est vérifié avant le premier versement.</small>",
    "<small class=\"o_ocd_amb_muted\">The image is drawn by OCD Live with the price of now: a new price, a new image. The price cannot be changed.</small>":
        "<small class=\"o_ocd_amb_muted\">L'image est faite par OCD Live avec le prix du moment : un nouveau prix, une nouvelle image. Le prix ne se change pas.</small>",
    "<small class=\"o_ocd_amb_muted\">The products sold on OCD Live, the ones of your country first (not the vendors in direct contact on WhatsApp: the sale does not go through the site). A product sold out leaves the list; your link stays good and leads to the boutique.</small>":
        "<small class=\"o_ocd_amb_muted\">Les produits vendus sur OCD Live, ceux de ton pays d'abord (pas ceux des vendeurs en contact direct sur WhatsApp : la vente ne passe pas par le site). Un produit épuisé quitte la liste ; ton lien reste bon et mène à la boutique.</small>",
    "<small class=\"o_ocd_amb_muted\">You may change the text; the link is added at the end if it is missing.</small>":
        "<small class=\"o_ocd_amb_muted\">Tu peux changer le texte ; le lien est ajouté à la fin s'il manque.</small>",
    "<small class=\"o_ocd_amb_muted\">You see the first name and the district of your customers, never their number.</small>":
        "<small class=\"o_ocd_amb_muted\">Tu vois le prénom et le quartier de tes clients, jamais leur numéro.</small>",
    "<small><b>Example</b></small>": "<small><b>Exemple</b></small>",
    "<small>Last 7 days</small>": "<small>7 derniers jours</small>",
    "<small>Waiting</small>": "<small>En attente</small>",
    "<span class=\"o_ocd_amb_badge\">For everybody, without a boutique</span>":
        "<span class=\"o_ocd_amb_badge\">Pour tout le monde, sans boutique</span>",
    "<span>I share honestly: the real price, no messages in mass to strangers, never a purchase with my own link. I am 18 or more.</span>":
        "<span>Je partage honnêtement : le vrai prix, pas de messages en masse à des inconnus, jamais d'achat avec mon propre lien. J'ai 18 ans ou plus.</span>",
    "<span>Since the start</span>": "<span>Depuis le début</span>",
    "<span>To pay</span>": "<span>À verser</span>",
    "A gain is confirmed %s days after the delivery. A return later is taken from the next payout; below the minimum, or nothing, it waits for the next week: nothing is lost, nothing is paid too much.":
        "Un gain est confirmé %s jours après la livraison. Un retour plus tard est retiré du versement suivant ; sous le minimum, ou s'il ne reste rien, il attend la semaine d'après : rien n'est perdu, rien n'est versé en trop.",
    "A gain is due only for a parcel delivered with its code and kept.":
        "Un gain n'est dû que pour un colis livré avec son code et gardé.",
    "A new number waits %s hours before the first payout, and the number of your account is told on WhatsApp: if it is not you, you stop it.":
        "Un nouveau numéro attend %s heures avant le premier versement, et le numéro de ton compte est prévenu sur WhatsApp : si ce n'est pas toi, tu l'arrêtes.",
    "A return taken back is more than your gains: it waits for your next gains.":
        "Un retour repris dépasse tes gains : il attend tes prochains gains.",
    "Above %s earned, the team sees your identity document before the next payout (once).":
        "Au-delà de %s gagnés, l'équipe voit ta pièce d'identité avant le versement suivant (une seule fois).",
    "Address of the page": "Adresse de la page",
    "Ask to become an ambassador": "Demander à devenir ambassadeur",
    "Become an ambassador": "Devenir ambassadeur",
    "Become one": "Le devenir",
    "Below %s, it waits for the next payout day.": "Sous %s, il attend le prochain jour de versement.",
    "Cancelled: no gain.": "Annulé : pas de gain.",
    "Change my number": "Changer mon numéro",
    "Copied: paste it where you want.": "Copié : colle-le où tu veux.",
    "Copy the link": "Copier le lien",
    "Each link counts for you %s days on the phone that opens it, for everything ordered there; the last link opened counts.":
        "Chaque lien compte pour toi %s jours sur le téléphone qui l'ouvre, pour tout ce qui y est commandé ; le dernier lien ouvert compte.",
    "Give the WhatsApp number of your account of ambassador: a code arrives on WhatsApp. Not an ambassador yet?":
        "Donne le numéro WhatsApp de ton compte d'ambassadeur : un code arrive sur WhatsApp. Pas encore ambassadeur ?",
    "Give your Mobile Money number.": "Donne ton numéro Mobile Money.",
    "In live tonight": "En live ce soir",
    "Look at %(product)s of %(vendor)s: %(price)s on OCD Live, delivered with a code. %(link)s":
        "Regarde %(product)s de %(vendor)s : %(price)s sur OCD Live, livré avec un code. %(link)s",
    "Make my link": "Faire mon lien",
    "Messages in mass to people who did not ask for them close the account.":
        "Des messages en masse à des personnes qui ne les ont pas demandés ferment le compte.",
    "My ambassador space": "Mon espace ambassadeur",
    "My links": "Mes liens",
    "My sales": "Mes ventes",
    "New Mobile Money number": "Nouveau numéro Mobile Money",
    "No gain": "Pas de gain",
    "No number yet": "Pas encore de numéro",
    "No product here for now.": "Aucun produit ici pour l'instant.",
    "No sale yet: share a product, your contacts order with your link.":
        "Pas encore de vente : partage un produit, tes contacts commandent avec ton lien.",
    "Noted: your new number waits %s hours before a payout, the number of your account is told.":
        "C'est noté : ton nouveau numéro attend %s heures avant un versement, le numéro de ton compte est prévenu.",
    "Nothing waiting.": "Rien en attente.",
    "On your Mobile Money %s": "Sur ton Mobile Money %s",
    "On your Mobile Money, from %s.": "Sur ton Mobile Money, dès %s.",
    "One account per person, paid on your own Mobile Money.": "Un compte par personne, versé sur ton propre Mobile Money.",
    "Open my ambassador space": "Ouvrir mon espace ambassadeur",
    "Ordered while the program was closed.": "Commandé pendant que le programme était fermé.",
    "Ordered while your account was paused.": "Commandé pendant que ton compte était en pause.",
    "Ordered with your own number: your own purchase does not count.":
        "Commandé avec ton propre numéro : ton propre achat ne compte pas.",
    "Paste the address of a page of OCD Live (a boutique, a live, the programme).":
        "Colle l'adresse d'une page d'OCD Live (une boutique, un live, le programme).",
    "Products to share": "Produits à partager",
    "Put it in my WhatsApp status": "Mettre en statut WhatsApp",
    "Refused at the door or returned: no gain.": "Refusé à la porte ou retourné : pas de gain.",
    "Save the image": "Enregistrer l'image",
    "Search a product, a boutique": "Chercher un produit, une boutique",
    "See more": "Voir plus",
    "Send to a contact": "Envoyer à un contact",
    "Share a boutique or a live": "Partager une boutique ou un live",
    "Share, and earn on each parcel delivered": "Partage, et gagne sur chaque colis livré",
    "The charter": "La charte",
    "The clip of 30 seconds of the live where the product was shown, with the same link.":
        "Le clip de 30 secondes du live où le produit a été montré, avec le même lien.",
    "The program of the ambassadors is closed for now.": "Le programme des ambassadeurs est fermé pour l'instant.",
    "The program of the ambassadors is closed for now. Come back soon.":
        "Le programme des ambassadeurs est fermé pour l'instant. Reviens bientôt.",
    "The same number if empty": "Le même numéro si vide",
    "The team checks your account before your next payout: your gains are kept.":
        "L'équipe vérifie ton compte avant ton prochain versement : tes gains sont gardés.",
    "The team sees your identity document once before the payout.":
        "L'équipe voit ta pièce d'identité une fois avant le versement.",
    "The text": "Le texte",
    "This customer already ordered several times this month with your links.":
        "Ce client a déjà commandé plusieurs fois ce mois-ci avec tes liens.",
    "This is already your number.": "C'est déjà ton numéro.",
    "This number can no longer open an account of ambassador: write to OCD Live.":
        "Ce numéro ne peut plus ouvrir de compte d'ambassadeur : écris à OCD Live.",
    "This product is from your own boutique: it earns you nothing as an ambassador.":
        "Ce produit est de ta propre boutique : il ne te rapporte rien comme ambassadeur.",
    "Tick that you share honestly and that you are 18 or more.":
        "Coche que tu partages honnêtement et que tu as 18 ans ou plus.",
    "Too many parcels refused or returned pause the account; the gains due are kept.":
        "Trop de colis refusés ou retournés mettent le compte en pause ; les gains dus sont gardés.",
    "Type your Mobile Money number, with the same country.": "Tape ton numéro Mobile Money, avec le même pays.",
    "You earn %s": "Tu gagnes %s",
    "You earn %s on each piece delivered and kept.": "Tu gagnes %s sur chaque pièce livrée et gardée.",
    "You receive a code on WhatsApp to log in, like the vendors, then your gains and your payouts on WhatsApp. One account per number.":
        "Tu reçois un code sur WhatsApp pour te connecter, comme les vendeurs, puis tes gains et tes versements sur WhatsApp. Un compte par numéro.",
    "You share a product of OCD Live with your link. Your contact orders within %(days)s days: when their parcel is delivered and they keep it, you earn %(rate)s of the articles.":
        "Tu partages un produit d'OCD Live avec ton lien. Ton contact commande dans les %(days)s jours : quand son colis est livré et qu'il le garde, tu gagnes %(rate)s des articles.",
    "Your Mobile Money, for your gains": "Ton Mobile Money, pour tes gains",
    "Your account is checked by the team before the payout.": "Ton compte est vérifié par l'équipe avant le versement.",
    "Your account is not open yet.": "Ton compte n'est pas encore ouvert.",
    "Your account is paused: the team calls you.": "Ton compte est en pause : l'équipe t'appelle.",
    "Your account is paused: your links still work, nothing is earned for now. %s":
        "Ton compte est en pause : tes liens marchent encore, rien ne se gagne pour l'instant. %s",
    "Your ambassador space.": "Ton espace ambassadeur.",
    "Your gains confirmed come here.": "Tes gains confirmés arrivent ici.",
    "Your link: %s": "Ton lien : %s",
    "Your new number waits until %s.": "Ton nouveau numéro attend jusqu'au %s.",
    "Your own purchases, and the ones of your own boutique, never count.":
        "Tes propres achats, et ceux de ta propre boutique, ne comptent jamais.",
    "delivered on %s": "livré le %s",
    "for a wax dress at %s delivered and kept. Your contact pays the same price as on the site.":
        "pour une robe en wax à %s livrée et gardée. Ton contact paie le même prix que sur le site.",
    "https://…/ocd/boutique/12": "https://…/ocd/boutique/12",
    "− %s: already confirmed, taken from your next payout": "− %s : déjà confirmé, retiré de ton prochain versement",
    "▶ The clip of the live": "▶ Le clip du live",
    "Ordered": "Commandé",
    # Back office (neutral)
    "% of returns": "% de retours",
    "%(active)s ambassadors active, %(waiting)s waiting for the team.":
        "%(active)s ambassadeurs actifs, %(waiting)s en attente de l'équipe.",
    "%(bad)s parcels refused or returned on %(count)s: paused by itself.":
        "%(bad)s colis refusés ou retournés sur %(count)s : mis en pause tout seul.",
    "%s earned since the start": "%s gagnés depuis le début",
    "%s, returned": "%s, retourné",
    "0: no cap.": "0 : pas de plafond.",
    "A gain is paid or taken back once.": "Un gain est versé ou repris une seule fois.",
    "A gain is written for each parcel of an order brought by the link of an ambassador.":
        "Un gain est écrit pour chaque colis d'une commande apportée par le lien d'un ambassadeur.",
    "A new payout number waits the hours of the settings before the first payout.":
        "Un nouveau numéro de versement attend les heures des réglages avant le premier versement.",
    "A parcel gives one gain at most.": "Un colis donne un gain au plus.",
    "Account asked": "Compte demandé",
    "Account of ambassador opened by %s.": "Compte d'ambassadeur ouvert par %s.",
    "Account paused": "Compte en pause",
    "After the delivery with the code: the gain is then paid. A return later is taken from the next payout.":
        "Après la livraison avec le code : le gain est alors versé. Un retour plus tard est retiré du versement suivant.",
    "Already paid: taken from the next payout if the return is made.":
        "Déjà versé : retiré du prochain versement si le retour est fait.",
    "Ambassador": "Ambassadeur",
    "Ambassador Cap Per Parcel": "Plafond par colis de l'ambassadeur",
    "Ambassador Rate (%)": "Taux de l'ambassadeur (%)",
    "Ambassador Since": "Ambassadeur depuis",
    "Ambassador paused: too many returns": "Ambassadeur en pause : trop de retours",
    "Ambassadors": "Ambassadeurs",
    "Ambassadors: At Most Per Parcel": "Ambassadeurs : au plus par colis",
    "Ambassadors: Confirmed After (Days)": "Ambassadeurs : confirmé après (jours)",
    "Ambassadors: Gain (%)": "Ambassadeurs : gain (%)",
    "Ambassadors: Identity Checked Above": "Ambassadeurs : pièce d'identité au-delà de",
    "Ambassadors: Minimum Payout": "Ambassadeurs : versement minimum",
    "Ambassadors: New Payout Number Waits (Hours)": "Ambassadeurs : nouveau numéro de versement retenu (heures)",
    "Ambassadors: Orders Of A Customer Per Month": "Ambassadeurs : commandes d'un client par mois",
    "Ambassadors: Paused Above (% Of Returns)": "Ambassadeurs : en pause au-delà de (% de retours)",
    "Ambassadors: Paused From (Parcels)": "Ambassadeurs : en pause à partir de (colis)",
    "Ambassadors: Program": "Ambassadeurs : programme",
    "Ambassadors: The Link Counts (Days)": "Ambassadeurs : le lien compte (jours)",
    "Ambassadors: the sales brought by their shares": "Ambassadeurs : les ventes apportées par leurs partages",
    "An order placed this long after the link was opened counts for the ambassador (the last link opened).":
        "Une commande passée jusqu'à ce délai après l'ouverture du lien compte pour l'ambassadeur (le dernier lien ouvert).",
    "Another ambassador has this code.": "Un autre ambassadeur a ce code.",
    "Anyone shares a product of OCD Live with their personal link and earns a share of the articles once the parcel is delivered with its code and kept, paid every week on their Mobile Money":
        "Chacun partage un produit d'OCD Live avec son lien personnel et gagne une part des articles une fois le colis livré avec son code et gardé, versée chaque semaine sur son Mobile Money",
    "Anyone signs up on the page /ambassadeurs of the site, with their WhatsApp number and their Mobile Money.":
        "Chacun s'inscrit sur la page /ambassadeurs du site, avec son numéro WhatsApp et son Mobile Money.",
    "Articles": "Articles",
    "Asked to become an ambassador on the site.": "A demandé à devenir ambassadeur sur le site.",
    "At most per parcel": "Au plus par colis",
    "Before the first payout on a new number; the number of the account is told on WhatsApp.":
        "Avant le premier versement sur un nouveau numéro ; le numéro du compte est prévenu sur WhatsApp.",
    "The number of the account is told on WhatsApp.": "Le numéro du compte est prévenu sur WhatsApp.",
    "Accept": "Accepter",
    "Asked": "Demandé",
    "Everybody": "Tout le monde",
    "Figures Of A Vendor, Day By Day": "Chiffres d'un vendeur, jour par jour",
    "I already have an account": "J'ai déjà un compte",
    "In promo": "En promo",
    "Log out": "Se déconnecter",
    "My money": "Mon argent",
    "New payout number: wait": "Nouveau numéro de versement : attente",
    "Open the account": "Ouvrir le compte",
    "See their space": "Voir son espace",
    "Why": "Pourquoi",
    "Below, the gains wait for the next payout day.": "En dessous, les gains attendent le prochain jour de versement.",
    "Bill": "Facture",
    "Charter Accepted At": "Charte acceptée le",
    "Close the account": "Fermer le compte",
    "Closed by the team.": "Fermé par l'équipe.",
    "Closed: no new gain, the gains already due are paid.": "Fermé : plus de nouveau gain, les gains déjà dus sont versés.",
    "Code Of The Links": "Code des liens",
    "Confirm the gains kept: a bill each, paid with the payouts of the shop every week.\nIn the evening, tell each ambassador the parcels delivered since the last message, once a day.\nRemove the accounts asked whose number was never checked (7 days).":
        "Confirmer les gains gardés : une facture chacun, versée avec les reversements du shop chaque semaine.\nLe soir, dire à chaque ambassadeur les colis livrés depuis le dernier message, une fois par jour.\nSupprimer les comptes demandés dont le numéro n'a jamais été vérifié (7 jours).",
    "Confirmed At": "Confirmé le",
    "Confirmed On": "Confirmé le",
    "Counts in the rate of returns of the ambassador.": "Compte dans le taux de retours de l'ambassadeur.",
    "Credit Note": "Avoir",
    "Delivered (30 Days)": "Livrés (30 jours)",
    "Did not count": "N'a pas compté",
    "Earned Since The Start": "Gagné depuis le début",
    "Everybody: the account opens once the number is checked. Invited: the team opens it. Closed: no new gain (the gains already due are paid).":
        "Tout le monde : le compte s'ouvre une fois le numéro vérifié. Sur invitation : l'équipe l'ouvre. Fermé : plus de nouveau gain (les gains déjà dus sont versés).",
    "Gain": "Gain",
    "Gain Of An Ambassador": "Gain d'un ambassadeur",
    "Gain of an ambassador": "Gain d'un ambassadeur",
    "Gain of an ambassador taken back": "Gain d'un ambassadeur repris",
    "Gain on %(parcel)s (%(products)s)": "Gain sur %(parcel)s (%(products)s)",
    "Gain on the articles": "Gain sur les articles",
    "Gain taken back": "Gain repris",
    "Gains Of The Ambassador": "Gains de l'ambassadeur",
    "Gains Of The Day Told On": "Gains du jour dits le",
    "Gains This Month": "Gains du mois",
    "Gains confirmed and not paid yet, minus the returns taken back.":
        "Gains confirmés et pas encore versés, moins les retours repris.",
    "Gains confirmed since the start: above, the team sees an identity document before the next payout. 0: never.":
        "Gains confirmés depuis le début : au-delà, l'équipe voit une pièce d'identité avant le versement suivant. 0 : jamais.",
    "Gains confirmed, returns watched": "Gains confirmés, retours surveillés",
    "Gains of %s": "Gains de %s",
    "Gains of the ambassadors": "Gains des ambassadeurs",
    "Gains since the start: the team sees an identity document once before the next payout. 0: never.":
        "Gains depuis le début : l'équipe voit une pièce d'identité une fois avant le versement suivant. 0 : jamais.",
    "Identity Seen (Ambassador)": "Pièce d'identité vue (ambassadeur)",
    "Identity seen": "Pièce vue",
    "Identity seen above": "Pièce d'identité au-delà de",
    "Identity to see": "Pièce d'identité à voir",
    "In the currency of OCD, at most the cap of the day.": "Dans la devise d'OCD, au plus le plafond du jour.",
    "In the personal links of the ambassador: ocdlive.com/a/GRACE7.": "Dans les liens personnels de l'ambassadeur : ocdlive.com/a/GRACE7.",
    "Invited by the team": "Sur invitation de l'équipe",
    "Invoicing, code of OCD Live.": "Facturation, code d'OCD Live.",
    "Link Opened At": "Lien ouvert le",
    "Messages to strangers": "Messages à des inconnus",
    "Mobile Money %s": "Mobile Money %s",
    "Mobile Money of another person": "Mobile Money d'une autre personne",
    "New payout number: %(new)s (was %(old)s).": "Nouveau numéro de versement : %(new)s (avant : %(old)s).",
    "No ambassador yet": "Pas encore d'ambassadeur",
    "No gain yet": "Pas encore de gain",
    "No new gain; the gains due are paid a last time.": "Plus de nouveau gain ; les gains dus sont versés une dernière fois.",
    "No return: keep the gain": "Pas de retour : garder le gain",
    "Not confirmed: it waits for the return.": "Pas confirmé : il attend le retour.",
    "Not on the delivery; never more than the commission of OCD on the article. Paid by OCD: the customer pays the same price, the vendor pays nothing.":
        "Pas sur la livraison ; jamais plus que la commission d'OCD sur l'article. Payé par OCD : le client paie le même prix, le vendeur ne paie rien.",
    "Nothing is due on this parcel; a confirmed gain is taken from the next payout.":
        "Rien n'est dû sur ce colis ; un gain confirmé est retiré du prochain versement.",
    "Nothing waiting for the ambassadors.": "Rien en attente pour les ambassadeurs.",
    "Number never checked.": "Numéro jamais vérifié.",
    "Number to check": "Numéro à vérifier",
    "OCD Live: Ambassadors": "OCD Live : Ambassadeurs",
    "OCD Live: gains of the ambassadors": "OCD Live : gains des ambassadeurs",
    "Of the articles of the order (not the delivery), never more than the commission of OCD on the article.":
        "Des articles de la commande (pas la livraison), jamais plus que la commission d'OCD sur l'article.",
    "On the payout day of the shop": "Le jour de versement du shop",
    "On the payout day of the shop, on their Mobile Money; below, it waits.":
        "Le jour de versement du shop, sur leur Mobile Money ; en dessous, il attend.",
    "Only the team of OCD Live decides on the gains of the ambassadors.":
        "Seule l'équipe d'OCD Live décide des gains des ambassadeurs.",
    "Only the team of OCD Live manages the ambassadors.": "Seule l'équipe d'OCD Live gère les ambassadeurs.",
    "Open again": "Rouvrir",
    "Order brought by an ambassador": "Commande apportée par un ambassadeur",
    "Orders (30 Days)": "Commandes (30 jours)",
    "Orders of a customer per month": "Commandes d'un client par mois",
    "Orders of their own": "Commandes pour soi-même",
    "Paid every week from": "Versé chaque semaine dès",
    "Parcels refused at the door or returned, on the last parcels of the ambassador. 0: never.":
        "Colis refusés à la porte ou retournés, sur les derniers colis de l'ambassadeur. 0 : jamais.",
    "Parcels refused at the door or returned: the links still work, nothing is earned, the gains due are kept. 0: never.":
        "Colis refusés à la porte ou retournés : les liens marchent encore, rien ne se gagne, les gains dus sont gardés. 0 : jamais.",
    "Pause": "Mettre en pause",
    "Paused by itself above": "Mis en pause tout seul au-delà de",
    "Paused by the team.": "Mis en pause par l'équipe.",
    "Pay the gains confirmed minus the returns taken back, from the minimum of the settings.\nNever a balance below zero, nor to an account paused or to check, nor on a new number before its hours, nor above the gains of the settings without an identity seen.\nPause an account above the rate of returns of the settings.":
        "Verser les gains confirmés moins les retours repris, dès le minimum des réglages.\nJamais un solde négatif, ni à un compte en pause ou à vérifier, ni sur un nouveau numéro avant ses heures, ni au-delà des gains des réglages sans pièce d'identité vue.\nMettre en pause un compte au-delà du taux de retours des réglages.",
    "Payout Number Since": "Numéro de versement depuis",
    "Program or account closed": "Programme ou compte fermé",
    "Rate (%)": "Taux (%)",
    "Refused Or Returned": "Refusé ou retourné",
    "Refused at the door or returned": "Refusé à la porte ou retourné",
    "Return Asked": "Retour demandé",
    "Return asked": "Retour demandé",
    "Return made: no gain": "Retour fait : pas de gain",
    "Return of %(parcel)s (%(products)s)": "Retour de %(parcel)s (%(products)s)",
    "Returns (30 Days)": "Retours (30 jours)",
    "Sales, code of OCD Live.": "Ventes, code d'OCD Live.",
    "See an identity document in their name before the next payout (once).":
        "Voir une pièce d'identité à son nom avant le prochain versement (une seule fois).",
    "See the ambassador": "Voir l'ambassadeur",
    "See the order": "Voir la commande",
    "See their gains": "Voir ses gains",
    "Sold thanks to the ambassadors": "Vendu grâce aux ambassadeurs",
    "Taken back": "Repris",
    "The account of ambassador of %s is not open.": "Le compte d'ambassadeur de %s n'est pas ouvert.",
    "The ambassador": "L'ambassadeur",
    "The ambassadors": "Les ambassadeurs",
    "The ambassadors.": "Les ambassadeurs.",
    "The day the gain is confirmed, if kept.": "Le jour où le gain est confirmé, s'il est gardé.",
    "The days of the settings after the delivery with the code.": "Les jours des réglages après la livraison avec le code.",
    "The first name, the initial and the district: never the number.": "Le prénom, l'initiale et le quartier : jamais le numéro.",
    "The gain %s is already decided.": "Le gain %s est déjà décidé.",
    "The gains of the ambassadors.": "Les gains des ambassadeurs.",
    "The last link of an ambassador opened on the phone, within the days of the settings.":
        "Le dernier lien d'un ambassadeur ouvert sur le téléphone, dans les jours des réglages.",
    "The last link of an ambassador opened on this phone before the order.":
        "Le dernier lien d'un ambassadeur ouvert sur ce téléphone avant la commande.",
    "The last link opened on the phone counts; the gain is confirmed after the delivery with the code, a return later is taken from the next payout.":
        "Le dernier lien ouvert sur le téléphone compte ; le gain est confirmé après la livraison avec le code, un retour plus tard est retiré du versement suivant.",
    "The link and the confirmation": "Le lien et la confirmation",
    "The money of the ambassadors": "L'argent des ambassadeurs",
    "The orders of the same customer that count for the same ambassador in a month. 0: no limit.":
        "Les commandes d'un même client qui comptent pour un même ambassadeur dans un mois. 0 : pas de limite.",
    "The orders of the same customer that count for the same ambassador. 0: no limit.":
        "Les commandes d'un même client qui comptent pour un même ambassadeur. 0 : pas de limite.",
    "The payouts of the shop.": "Les reversements du shop.",
    "The program": "Le programme",
    "The rate of returns counts from this number of parcels.": "Le taux de retours compte à partir de ce nombre de colis.",
    "The rate of the day of the order.": "Le taux du jour de la commande.",
    "Their Mobile Money is the one of %s.": "Son Mobile Money est celui de %s.",
    "Their links still work, nothing is earned; the gains due are kept until you open the account again.":
        "Ses liens marchent encore, rien ne se gagne ; les gains dus sont gardés jusqu'à la réouverture du compte.",
    "Their own purchase": "Son propre achat",
    "Their sales": "Ses ventes",
    "This month": "Ce mois-ci",
    "To Pay": "À verser",
    "Told To The Ambassador": "Dit à l'ambassadeur",
    "Too many orders of the same customer this month": "Trop de commandes du même client ce mois-ci",
    "Too many returns": "Trop de retours",
    "Visit By An Ambassador": "Visite par un ambassadeur",
    "Visits (30 Days)": "Visites (30 jours)",
    "Waiting for the team": "En attente de l'équipe",
    "When an order is confirmed after the link of an ambassador": "Quand une commande est confirmée après le lien d'un ambassadeur",
    "Why It Did Not Count": "Pourquoi elle n'a pas compté",
    "Why the account is to check, paused or closed.": "Pourquoi le compte est à vérifier, en pause ou fermé.",
    "Write the ambassador on the order with the rate and the cap of the day, never changed after.\nRefuse their own purchase, the orders of a customer above the limit of the month, an account paused or closed.\nWrite a gain per parcel: nothing is due before the delivery with the code.":
        "Inscrire l'ambassadeur sur la commande avec le taux et le plafond du jour, jamais changés ensuite.\nRefuser son propre achat, les commandes d'un client au-delà de la limite du mois, un compte en pause ou fermé.\nÉcrire un gain par colis : rien n'est dû avant la livraison avec le code.",
    "Your account of ambassador is closed: messages sent in mass to people who did not ask for them.":
        "Ton compte d'ambassadeur est fermé : des messages envoyés en masse à des personnes qui ne les ont pas demandés.",
    "Your account of ambassador is closed: one account per person, paid on their own Mobile Money.":
        "Ton compte d'ambassadeur est fermé : un compte par personne, versé sur son propre Mobile Money.",
    "Your account of ambassador is closed: orders made by you or for you with your links.":
        "Ton compte d'ambassadeur est fermé : des commandes faites par toi ou pour toi avec tes liens.",
    "Your account of ambassador is closed: too many parcels refused at the door or returned.":
        "Ton compte d'ambassadeur est fermé : trop de colis refusés à la porte ou retournés.",
    "by %s ambassadors": "par %s ambassadeurs",
    "by 1 ambassador": "par 1 ambassadeur",
    "days the link counts": "jours où le lien compte",
    "days after the delivery": "jours après la livraison",
    "on parcels at least": "sur colis au moins",
    "your products shared by %s ambassadors": "tes produits partagés par %s ambassadeurs",
    "your products shared by 1 ambassador": "tes produits partagés par 1 ambassadeur",
    "You pay nothing: OCD Live pays the ambassadors on its commission. Their names and numbers stay with OCD Live.":
        "Tu ne paies rien : OCD Live paie les ambassadeurs sur sa commission. Leurs noms et leurs numéros restent chez OCD Live.",
}

AMBASSADORS_WHATSAPP = {
    "OCD Live: Ambassadors On WhatsApp": "OCD Live : Ambassadeurs sur WhatsApp",
    "OCD Live: parcels of an ambassador delivered": "OCD Live : colis d'un ambassadeur livrés",
    "OCD Live: parcels of an ambassador delivered (English)": "OCD Live : colis d'un ambassadeur livrés (anglais)",
    "OCD Live: payout number of an ambassador changed": "OCD Live : numéro de versement d'un ambassadeur changé",
    "OCD Live: payout number of an ambassador changed (English)": "OCD Live : numéro de versement d'un ambassadeur changé (anglais)",
    "OCD Live: payout of an ambassador made": "OCD Live : versement d'un ambassadeur fait",
    "OCD Live: payout of an ambassador made (English)": "OCD Live : versement d'un ambassadeur fait (anglais)",
    "The ambassadors on WhatsApp: the parcels they shared delivered today (once a day), their payout made, their payout number changed":
        "Les ambassadeurs sur WhatsApp : les colis qu'ils ont partagés livrés aujourd'hui (une fois par jour), leur versement fait, leur numéro de versement changé",
    "1 parcel": "1 colis",
    "%s parcels": "%s colis",
    "Vendor Payout": "Reversement au vendeur",
}
