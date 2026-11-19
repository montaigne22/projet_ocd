# Chantier 10: the relay points (ocd_live_shop, ocd_live_shop_whatsapp, ocd_express,
# ocd_express_whatsapp). « tu » on the site (customer, relay point, courier), neutral in the back office.

RELAY = {
    # Space of the relay point (« My relay point »)
    "%(count)s parcels handed over · %(fee)s each": "%(count)s colis remis · %(fee)s chacun",
    "%(count)s parcels lost at the relay point %(relay)s: it receives no new parcel until the team checks it.":
        "%(count)s colis perdus au point relais %(relay)s : il ne reçoit plus de nouveau colis tant que l'équipe n'a pas vérifié.",
    "%(kept)s parcels kept on %(places)s · %(amount)s this month":
        "%(kept)s colis gardés sur %(places)s · %(amount)s ce mois-ci",
    "%(name)s sends from %(city)s: not at a relay point of %(relay_city)s.":
        "%(name)s envoie depuis %(city)s : pas de point relais de %(relay_city)s.",
    "%(received)s The courier keeps %(count)s parcels damaged or open.":
        "%(received)s Le livreur garde %(count)s colis abîmés ou ouverts.",
    "%(relays)s relay points open, %(waiting)s to visit; %(rates)s rates « relay point ». Without a rate for a city, its relay points are not offered.":
        "%(relays)s points relais ouverts, %(waiting)s à visiter ; %(rates)s tarifs « point relais ». Sans tarif pour une ville, ses points relais ne sont pas proposés.",
    "%(shop)s (%(district)s) asks to become a relay point: visit it.":
        "%(shop)s (%(district)s) demande à devenir point relais : à visiter.",
    "%s arrives with your parcels": "%s arrive avec tes colis",
    "%s delivers their parcels: not at a relay point.": "%s livre ses colis : pas de point relais.",
    "%s parcels lost: to check by the team": "%s colis perdus : à vérifier par l'équipe",
    "%s, OCD courier": "%s, livreur OCD",
    "%s parcels": "%s colis",
    "Identity Checked": "Identité vérifiée",
    "No parcel here.": "Aucun colis ici.",
    "To give back": "À rendre",
    "0: no reminder.": "0 : pas de rappel.",
    "<b class=\"o_ocd_rl_title\">Choose the parcel</b>": "<b class=\"o_ocd_rl_title\">Choisis le colis</b>",
    "<b>At a relay point</b>": "<b>En point relais</b>",
    "<b>Opening hours</b>": "<b>Horaires d'ouverture</b>",
    "<b>Request sent.</b>\n                            <span>The team of OCD Live calls you, then comes to see your shop before opening it.</span>":
        "<b>Demande envoyée.</b>\n                            <span>L'équipe d'OCD Live t'appelle, puis vient voir ta boutique avant de l'ouvrir.</span>",
    "<b>What it takes</b>\n                            <span>A shop open at least 6 days out of 7, with fixed hours.</span>":
        "<b>Ce qu'il faut</b>\n                            <span>Une boutique ouverte au moins 6 jours sur 7, avec des horaires fixes.</span>",
    "<small class=\"o_ocd_my_product_fact\">My store is a relay point: it keeps the parcels of the customers of the other vendors, paid for each parcel handed over.</small>":
        "<small class=\"o_ocd_my_product_fact\">Mon magasin est un point relais : il garde les colis des clients des autres vendeurs, payé pour chaque colis remis.</small>",
    "<small class=\"o_ocd_rl_hint o_ocd_rl_muted\" data-blocked=\"The camera did not open: allow it in the browser, or choose the parcel and type the code.\">The customer shows the QR of their page, or gives their code.</small>":
        "<small class=\"o_ocd_rl_hint o_ocd_rl_muted\" data-blocked=\"La caméra ne s'est pas ouverte : autorise-la dans le navigateur, ou choisis le colis et tape le code.\">Le client montre le QR de sa page, ou donne son code.</small>",
    "<small class=\"o_ocd_rl_muted\">The code gives the parcel, not a name: someone else may come for the customer. 3 wrong codes lock the parcel; the team unlocks it.</small>":
        "<small class=\"o_ocd_rl_muted\">C'est le code qui donne le colis, pas un nom : quelqu'un d'autre peut venir pour le client. 3 codes faux bloquent le colis ; l'équipe le débloque.</small>",
    "<small class=\"o_ocd_rl_muted\">The team comes to see your shop before opening it. You are a vendor on OCD Live with a verified store? In « My stores », tick « My store is a relay point ».</small>":
        "<small class=\"o_ocd_rl_muted\">L'équipe vient voir ta boutique avant de l'ouvrir. Tu es vendeur sur OCD Live avec un magasin vérifié ? Dans « Mes magasins », coche « Mon magasin est un point relais ».</small>",
    "<small class=\"o_ocd_rl_muted\">To change them, write to the team of OCD Live.</small>":
        "<small class=\"o_ocd_rl_muted\">Pour les changer, écris à l'équipe d'OCD Live.</small>",
    "<small class=\"o_ocd_rl_muted\">« On holiday »: no new parcel, the ones kept wait for their customers.</small>":
        "<small class=\"o_ocd_rl_muted\">« En congé » : plus de nouveau colis, ceux que tu gardes attendent leurs clients.</small>",
    "<small>Count each parcel when it arrives: it is in your care once counted.</small>":
        "<small>Compte chaque colis à son arrivée : une fois compté, il est sous ta garde.</small>",
    "<small>Kept</small>": "<small>Gardés</small>",
    "<small>Show this QR or give your code at the counter. Someone else may pick it up for you: give them your code.</small>":
        "<small>Montre ce QR ou donne ton code au comptoir. Quelqu'un d'autre peut le retirer pour toi : donne-lui ton code.</small>",
    "<small>The customer scans it and pays on their phone (Mobile Money). Touch « Check » once « Paid » shows: the code is accepted after the payment.</small>":
        "<small>Le client le scanne et paie sur son téléphone (Mobile Money). Touche « Vérifier » quand « Payé » s'affiche : le code est accepté après le paiement.</small>",
    "<small>This month</small>": "<small>Ce mois-ci</small>",
    "<span class=\"o_ocd_rl_badge\">For the shops of the neighbourhood</span>":
        "<span class=\"o_ocd_rl_badge\">Pour les boutiques du quartier</span>",
    "<span class=\"o_ocd_step_pill o_ocd_my_status_approved\">Relay point</span>":
        "<span class=\"o_ocd_step_pill o_ocd_my_status_approved\">Point relais</span>",
    "<span>A phone with WhatsApp, and your identity document.</span>":
        "<span>Un téléphone avec WhatsApp, et ta pièce d'identité.</span>",
    "<span>I refuse it: it goes back with the courier</span>": "<span>Je le refuse : il repart avec le livreur</span>",
    "<span>The customers come to you for their parcel, and see your shop. Your money is paid every month on your Mobile Money.</span>":
        "<span>Les clients viennent chez toi chercher leur colis, et découvrent ta boutique. Ton argent est versé chaque mois sur ton Mobile Money.</span>",
    # Settings and back office (neutral)
    "A bill of the earnings of the settings for each parcel handed over, paid every month with the payouts.\nA lost parcel: paid back by OCD and taken from the earnings; after the losses of the settings, the relay point is paused for the team.":
        "Une facture du gain des réglages pour chaque colis remis, payée chaque mois avec les versements.\nUn colis perdu : remboursé par OCD et retenu sur les gains ; après les pertes des réglages, le point relais est mis en pause pour l'équipe.",
    "A closed place for %s parcels, sheltered from the rain.": "Un endroit fermé pour %s colis, à l'abri de la pluie.",
    "A full relay point or on holiday is not offered. You pay before, or on your phone at the counter: never in cash, the relay point keeps no money.":
        "Un point relais plein ou en congé n'est pas proposé. Tu paies avant, ou sur ton téléphone au comptoir : jamais en espèces, le point relais ne garde pas d'argent.",
    "A parcel handed over with its code; a parcel lost at the relay point":
        "Un colis remis avec son code ; un colis perdu au point relais",
    "A parcel waits so many days for its customer (until the closing of the relay point on the last day), then it goes back.":
        "Un colis attend son client autant de jours (jusqu'à la fermeture du point relais le dernier jour), puis il repart.",
    "A partner of OCD Live who keeps the parcels in their shop (not a vendor).":
        "Un partenaire d'OCD Live qui garde les colis dans sa boutique (pas un vendeur).",
    "A relay point that lost so many parcels is paused until the team checks it. 0: never.":
        "Un point relais qui a perdu autant de colis est mis en pause jusqu'à la vérification de l'équipe. 0 : jamais.",
    "A vendor whose store is verified and open to the public keeps the parcels of the others, from « My stores ».":
        "Un vendeur dont le magasin est vérifié et ouvert au public garde les colis des autres, depuis « Mes magasins ».",
    "A vendor whose store is verified and open to the public may keep the parcels of the others.":
        "Un vendeur dont le magasin est vérifié et ouvert au public peut garder les colis des autres.",
    "Arrived %s": "Arrivé %s",
    "Ask to become a relay point": "Demander à devenir point relais",
    "At the relay point": "Au point relais",
    "At the relay point %s": "Au point relais %s",
    "At the relay point: on your phone with Mobile Money, never in cash. Your code is accepted once the payment is confirmed.":
        "Au point relais : sur ton téléphone avec Mobile Money, jamais en espèces. Ton code est accepté une fois le paiement confirmé.",
    "Call the relay point": "Appeler le point relais",
    "Check the payment": "Vérifier le paiement",
    "Choose the district of the shop.": "Choisis le quartier de la boutique.",
    "Choose the parcel.": "Choisis le colis.",
    "Choose the relay point where you pick it up.": "Choisis le point relais où tu le retires.",
    "Code given by the customer": "Code donné par le client",
    "Customer Reminded At": "Client relancé le",
    "Damaged or open": "Abîmé ou ouvert",
    "Days Kept At A Relay Point": "Jours de garde en point relais",
    "District of the shop": "Quartier de la boutique",
    "Drop: %s": "Dépôt : %s",
    "Earned By A Relay Point Per Parcel": "Gain d'un point relais par colis",
    "Earned This Month": "Gagné ce mois-ci",
    "Earned by a relay point": "Gagné par un point relais",
    "First the payment on the phone of the customer.": "D'abord le paiement sur le téléphone du client.",
    "First the pick-up at the vendors.": "D'abord le ramassage chez les vendeurs.",
    "For each parcel handed over to its customer, nothing for a parcel taken back; paid every month with the payouts.":
        "Pour chaque colis remis à son client, rien pour un colis repris ; payé chaque mois avec les versements.",
    "For each parcel handed over to its customer; nothing for a parcel taken back.":
        "Pour chaque colis remis à son client ; rien pour un colis repris.",
    "For the shops that keep the parcels of OCD Live: give the number of the relay point.":
        "Pour les boutiques qui gardent les colis d'OCD Live : donne le numéro du point relais.",
    "Full, it is not offered. Changed on the form of each relay point.":
        "Plein, il n'est pas proposé. Se change sur la fiche de chaque point relais.",
    "Good way! %s counts the parcels when you arrive.": "Bonne route ! %s compte les colis à ton arrivée.",
    "Hand a parcel over": "Remettre un colis",
    "Hand it over": "Le remettre",
    "Handed Over (30 Days)": "Remis (30 jours)",
    "Held By": "Tenu par",
    "Hello, I will not be able to go to the relay point %(relay)s for my order %(order)s: can you deliver it to my place?":
        "Bonjour, je ne pourrai pas aller au point relais %(relay)s pour ma commande %(order)s : pouvez-vous me la livrer chez moi ?",
    "Holds A Relay Point": "Tient un point relais",
    "I leave for the relay point": "Je pars au point relais",
    "I receive parcels again": "Je reçois de nouveau des colis",
    "I received the ticked parcels": "J'ai reçu les colis cochés",
    "I took these parcels back": "J'ai repris ces colis",
    "I will not be able to go: deliver it to my place (OCD Live on WhatsApp)":
        "Je ne pourrai pas y aller : livrez-la chez moi (OCD Live sur WhatsApp)",
    "It receives no new parcel; the parcels it keeps wait for their customers.":
        "Il ne reçoit plus de nouveau colis ; les colis qu'il garde attendent leurs clients.",
    "Itinerary to the relay point": "Itinéraire jusqu'au point relais",
    "Keep the parcels of OCD Live: %s per parcel handed over.": "Garde les colis d'OCD Live : %s par colis remis.",
    "Kept": "Gardés",
    "Kept Until": "Gardé jusqu'au",
    "Kept at the relay point": "Gardé au point relais",
    "Kept · %s": "Gardés · %s",
    "Last day": "Dernier jour",
    "Lost": "Perdus",
    "Lost At The Relay Point": "Perdu au point relais",
    "Lost at the relay point": "Perdu au point relais",
    "Make it a relay point": "En faire un point relais",
    "My relay point": "Mon point relais",
    "Name of the shop": "Nom de la boutique",
    "No cash at the relay point: you never keep the money of somebody else.":
        "Pas d'espèces au point relais : tu ne gardes jamais l'argent de quelqu'un d'autre.",
    "No parcel on the way to your relay point.": "Aucun colis en route vers ton point relais.",
    "No parcel to take back at this relay point.": "Aucun colis à reprendre à ce point relais.",
    "No parcel to take to this relay point.": "Aucun colis à déposer à ce point relais.",
    "No parcel waiting for its customer.": "Aucun colis n'attend son client.",
    "No price of the relay points in %s yet.": "Pas encore de prix des points relais à %s.",
    "No relay point to visit.": "Aucun point relais à visiter.",
    "No relay point yet": "Pas encore de point relais",
    "Not picked up before %s: the parcel goes back.": "Pas retiré avant %s : le colis repart.",
    "Not picked up in time: it waits at the relay point for the courier.":
        "Pas retiré à temps : il attend le livreur au point relais.",
    "Not picked up in time: the courier takes it back": "Pas retiré à temps : le livreur le reprend",
    "Not picked up in time: the parcel goes back. Paid online, OCD Live refunds you.":
        "Pas retiré à temps : le colis repart. Payé en ligne, OCD Live te rembourse.",
    "Not picked up: gone back": "Pas retiré : reparti",
    "Noted: no new parcel until you come back; the parcels kept wait for their customers.":
        "C'est noté : plus de nouveau colis jusqu'à ton retour ; les colis gardés attendent leurs clients.",
    "Noted: you receive parcels again.": "C'est noté : tu reçois de nouveau des colis.",
    "OCD Live: parcels at the relay points": "OCD Live : colis aux points relais",
    "OCD pays the parcel back and takes it from the earnings of the relay point. Continue?":
        "OCD rembourse le colis et le retient sur les gains du point relais. Continuer ?",
    "Off: no new parcel (on holiday, or paused by the team); the parcels it keeps wait for their customers.":
        "Désactivé : plus de nouveau colis (en congé, ou mis en pause par l'équipe) ; les colis qu'il garde attendent leurs clients.",
    "On The Way": "En route",
    "On holiday": "En congé",
    "On its way to the relay point": "En route vers le point relais",
    "Only a manager of OCD Live records a parcel lost at a relay point.":
        "Seul un responsable d'OCD Live enregistre un colis perdu en point relais.",
    "Only the team of OCD Live manages the relay points.": "Seule l'équipe d'OCD Live gère les points relais.",
    "Open": "Ouvert",
    "Open my relay point": "Ouvrir mon point relais",
    "Open the form": "Ouvrir la fiche",
    "Open the relay point again": "Rouvrir le point relais",
    "Parcel %s handed over": "Colis %s remis",
    "Parcel %s lost at the relay point": "Colis %s perdu au point relais",
    "Parcel at the relay point: tell the customer": "Colis au point relais : prévenir le client",
    "Parcel handed over": "Colis remis",
    "Parcel handed over by a relay point": "Colis remis par un point relais",
    "Parcel lost at a relay point": "Colis perdu en point relais",
    "Parcel lost at the relay point": "Colis perdu au point relais",
    "Parcels a relay point keeps at most, by default: full, it is not offered.":
        "Colis qu'un point relais garde au plus, par défaut : plein, il n'est pas proposé.",
    "Parcels it keeps at most: full, it is not offered.": "Colis qu'il garde au plus : plein, il n'est pas proposé.",
    "Parcels lost at a relay point before it is paused for the team. 0: never.":
        "Colis perdus par un point relais avant sa mise en pause pour l'équipe. 0 : jamais.",
    "Parcels of the relay point %s": "Colis du point relais %s",
    "Pause the relay point": "Mettre le point relais en pause",
    "Paused After (Parcels Lost)": "En pause après (colis perdus)",
    "Paused after": "En pause après",
    "Paused by the team": "En pause par l'équipe",
    "Pay at the relay point": "Payer au point relais",
    "Picked up at the relay point %s, with your code": "Retiré au point relais %s, avec ton code",
    "Picked up by the customer at the relay point %s.": "Retiré par le client au point relais %s.",
    "Places Of A Relay Point": "Places d'un point relais",
    "Places of a new relay point": "Places d'un nouveau point relais",
    "QR code to show at the counter": "QR code à montrer au comptoir",
    "Receive": "Recevoir",
    "Receive these parcels": "Recevoir ces colis",
    "Received By The Relay Point": "Reçu par le point relais",
    "Received by the relay point %s.": "Reçu par le point relais %s.",
    "Receives Parcels": "Reçoit des colis",
    "Refused by the relay point %(relay)s: %(note)s": "Refusé par le point relais %(relay)s : %(note)s",
    "Relay Point": "Point relais",
    "Relay Points": "Points relais",
    "Relay point": "Point relais",
    "Relay point %s": "Point relais %s",
    "Relay point: earned per parcel handed over, lost parcels taken back":
        "Point relais : gain par colis remis, colis perdus retenus",
    "Relay point: reminder before the end, then back": "Point relais : rappel avant la fin, puis retour",
    "Relay points": "Points relais",
    "Relay points and their prices": "Points relais et leurs prix",
    "Relay points: the parcels kept by the shops of the neighbourhood":
        "Points relais : les colis gardés par les boutiques du quartier",
    "Remind the customer; at the end, the parcel goes back (refunded when paid online) and waits at the relay point for the courier, who takes it back on his tour.":
        "Relancer le client ; à la fin, le colis repart (remboursé s'il a été payé en ligne) et attend au point relais le livreur, qui le reprend pendant sa tournée.",
    "Reminder Before The End (Days)": "Rappel avant la fin (jours)",
    "Scan their QR": "Scanner son QR",
    "See its parcels": "Voir ses colis",
    "Stop being a relay point": "Ne plus être point relais",
    "Store of a vendor": "Magasin d'un vendeur",
    "Stores Of The Vendors As Relay Points": "Magasins des vendeurs comme points relais",
    "Stores of the vendors as relay points": "Magasins des vendeurs comme points relais",
    "Take back: %(count)s parcels not picked up (%(names)s)": "À reprendre : %(count)s colis pas retirés (%(names)s)",
    "Taken Back At": "Repris le",
    "Taken back from the relay point %(relay)s by %(courier)s.": "Repris au point relais %(relay)s par %(courier)s.",
    "Tell the relay point the parcels coming, once per relay point.\nTell the customer it waits there and until when, with their code and the itinerary on their page.":
        "Prévenir le point relais des colis qui arrivent, une fois par point relais.\nPrévenir le client que son colis l'y attend et jusqu'à quand, avec son code et l'itinéraire sur sa page.",
    "Tested code of OCD Live, Invoicing.": "Code testé d'OCD Live, Facturation.",
    "The code of the customer at the relay point; « Lost at the relay point » on the parcel.":
        "Le code du client au point relais ; « Perdu au point relais » sur le colis.",
    "The courier leaves for the relay point; the relay point counts the parcel":
        "Le livreur part au point relais ; le point relais compte le colis",
    "The customer picks it up at a relay point": "Le client le retire en point relais",
    "The customers choose a relay point at the delivery step, cheaper than at the door.":
        "Les clients choisissent un point relais à l'étape de livraison, moins cher qu'à la porte.",
    "The customers may choose a relay point at the delivery step, where the relay points are open.":
        "Les clients peuvent choisir un point relais à l'étape de livraison, là où les points relais sont ouverts.",
    "The customers who pick their parcel up at a relay point.": "Les clients qui retirent leur colis en point relais.",
    "The days of the settings before the end, at the end": "Les jours des réglages avant la fin, à la fin",
    "The parcel %(parcel)s is lost at the relay point %(relay)s: pay back %(amount)s to the customer and its share to %(vendor)s.":
        "Le colis %(parcel)s est perdu au point relais %(relay)s : rembourser %(amount)s au client et sa part à %(vendor)s.",
    "The parcel %s is not at the relay point.": "Le colis %s n'est pas au point relais.",
    "The parcel %s is not kept by this relay point.": "Le colis %s n'est pas gardé par ce point relais.",
    "The parcel %s is not on its way to this relay point.": "Le colis %s n'est pas en route vers ce point relais.",
    "The parcel %s is not to take back.": "Le colis %s n'est pas à reprendre.",
    "The parcel could not reach the relay point. OCD Live calls you.":
        "Le colis n'a pas pu arriver au point relais. OCD Live t'appelle.",
    "The parcels kept at a relay point.": "Les colis gardés en point relais.",
    "The place keeps the parcels of the customers who chose it, for OCD Live.":
        "L'endroit garde les colis des clients qui l'ont choisi, pour OCD Live.",
    "The relay point %s does not take new parcels now: choose another one.":
        "Le point relais %s ne prend plus de nouveau colis pour l'instant : choisis-en un autre.",
    "The relay point counts the parcels on its phone: your tour updates.":
        "Le point relais compte les colis sur son téléphone : ta tournée se met à jour.",
    "The relay point where the customer picks the parcel up.": "Le point relais où le client retire le colis.",
    "The relay point where the customer picks up the parcels of the order.":
        "Le point relais où le client retire les colis de la commande.",
    "The relay point writes to you on WhatsApp when your parcel arrives.":
        "Le point relais t'écrit sur WhatsApp quand ton colis arrive.",
    "The relay points.": "Les points relais.",
    "The shops ask on the page /points-relais and the team visits them; a vendor makes their verified store a relay point from « My stores ».":
        "Les boutiques demandent sur la page /points-relais et l'équipe les visite ; un vendeur fait de son magasin vérifié un point relais depuis « Mes magasins ».",
    "The team of OCD Live paused your relay point: call them to open it again.":
        "L'équipe d'OCD Live a mis ton point relais en pause : appelle-la pour le rouvrir.",
    "This QR is not a parcel kept here.": "Ce QR n'est pas un colis gardé ici.",
    "This is not the code of this parcel. Attempts left: %s.": "Ce n'est pas le code de ce colis. Essais restants : %s.",
    "Tick each parcel you have in your hands. A parcel not ticked stays with the courier: never take a parcel you did not see.":
        "Coche chaque colis que tu as en main. Un colis non coché reste avec le livreur : ne prends jamais un colis que tu n'as pas vu.",
    "Tick the parcels you counted.": "Coche les colis que tu as comptés.",
    "To Take Back": "À reprendre",
    "To Take Back From The Relay Point": "À reprendre au point relais",
    "To give back · %s": "À rendre · %s",
    "To pay %s": "À payer %s",
    "To pay at the counter: %s": "À payer au comptoir : %s",
    "To pay: call the team of OCD Live.": "À payer : appelle l'équipe d'OCD Live.",
    "To receive · %s": "À recevoir · %s",
    "Too many wrong codes: the parcel is locked. Call the team.": "Trop de codes faux : le colis est bloqué. Appelle l'équipe.",
    "Until the closing of the relay point on the last day; then the parcel goes back.":
        "Jusqu'à la fermeture du point relais le dernier jour ; ensuite le colis repart.",
    "Visited By The Team": "Visité par l'équipe",
    "Visited: open it": "Visité : l'ouvrir",
    "Waiting for you at the relay point": "T'attend au point relais",
    "What The Shop Sells": "Ce que vend la boutique",
    "What is wrong (open box, wet, crushed)": "Ce qui ne va pas (carton ouvert, mouillé, écrasé)",
    "What your shop sells": "Ce que vend ta boutique",
    "Where you get your order": "Où tu récupères ta commande",
    "Why It Is Paused": "Pourquoi il est en pause",
    "With %s": "Avec %s",
    "Write the name of the shop and your name.": "Écris le nom de la boutique et ton nom.",
    "You come when you want, for %s days": "Tu passes quand tu veux, pendant %s jours",
    "You received %s parcels: each customer is told on WhatsApp.": "Tu as reçu %s colis : chaque client est prévenu sur WhatsApp.",
    "You received 1 parcel: its customer is told on WhatsApp.": "Tu as reçu 1 colis : son client est prévenu sur WhatsApp.",
    "You took back %s parcels: they go back to their vendors.": "Tu as repris %s colis : ils retournent à leurs vendeurs.",
    "You took back 1 parcel: it goes back to its vendor.": "Tu as repris 1 colis : il retourne à son vendeur.",
    "Your relay point.": "Ton point relais.",
    "asked %s": "demandé %s",
    "e.g. opposite the bakery": "ex. en face de la boulangerie",
    "e.g. phone credit, Mobile Money": "ex. crédit téléphone, Mobile Money",
    "on %s places": "sur %s places",
    "parcels lost": "colis perdus",
    "reminder before (days)": "rappel avant (jours)",
    "taken to the relay point by an OCD courier": "déposé au point relais par un livreur OCD",
    "« I leave for the relay point » on the tour, then « I received » at the relay point.":
        "« Je pars au point relais » sur la tournée, puis « J'ai reçu » au point relais.",
}

# Only in ocd_live_shop: who holds the relay point (« Partner » is « Contact » in OCD Express)
RELAY_SHOP = {
    "Partner": "Partenaire",
}

RELAY_WHATSAPP = {
    "OCD Live: parcel at the relay point": "OCD Live : colis au point relais",
    "OCD Live: parcel at the relay point (English)": "OCD Live : colis au point relais (anglais)",
    "OCD Live: parcel not picked up at the relay point": "OCD Live : colis pas retiré au point relais",
    "OCD Live: parcel not picked up at the relay point (English)": "OCD Live : colis pas retiré au point relais (anglais)",
    "OCD Live: parcel to pick up at the relay point before the end":
        "OCD Live : colis à retirer au point relais avant la fin",
    "OCD Live: parcel to pick up at the relay point before the end (English)":
        "OCD Live : colis à retirer au point relais avant la fin (anglais)",
    "OCD Live: parcels coming to the relay point": "OCD Live : colis en route vers le point relais",
    "OCD Live: parcels coming to the relay point (English)": "OCD Live : colis en route vers le point relais (anglais)",
}

RELAY_EXPRESS = {
    "<small class=\"o_ocd_ex_muted\">You come when you want, with your code. Paid on your phone at the counter, never in cash.</small>":
        "<small class=\"o_ocd_ex_muted\">Tu passes quand tu veux, avec ton code. Payé sur ton téléphone au comptoir, jamais en espèces.</small>",
    "At a relay point (cheaper): your customer picks it up": "En point relais (moins cher) : ton client le retire",
    "Delivery at a relay point: %s instead of %s": "Livraison en point relais : %s au lieu de %s",
    "No price of the relay points from your city yet: choose a delivery at the door.":
        "Pas encore de prix des points relais depuis ta ville : choisis une livraison à la porte.",
    "Not there? I pick it up at a relay point": "Pas là ? Je le retire en point relais",
    "Noted: your parcel waits for you at the relay point %s.": "C'est noté : ton colis t'attendra au point relais %s.",
    "On its way to the relay point %s.": "En route vers le point relais %s.",
    "Pick it up at this relay point": "Le retirer à ce point relais",
    "Show this QR or give your code at the counter. Someone else may pick it up for you: give them your code.":
        "Montre ce QR ou donne ton code au comptoir. Quelqu'un d'autre peut le retirer pour toi : donne-lui ton code.",
    "The customer picks it up at the relay point %s.": "Le client le retire au point relais %s.",
    "This relay point does not take new parcels now: choose another one.":
        "Ce point relais ne prend plus de nouveau colis pour l'instant : choisis-en un autre.",
    "Waits for %(customer)s at %(relay)s until %(until)s.": "Attend %(customer)s chez %(relay)s jusqu'au %(until)s.",
    "Waits for you at the relay point %s.": "T'attend au point relais %s.",
    "Your code appears here when the relay point has your parcel.":
        "Ton code s'affiche ici quand le point relais a ton colis.",
    "lost at the relay point %s": "perdu au point relais %s",
    "relay point %s": "point relais %s",
    "To pay at the door": "À payer à la porte",
    "To pay at the relay point": "À payer au point relais",
    "In cash to the courier, or on your phone (Mobile Money): the courier shows you the payment. Never on the personal number of the courier.":
        "En espèces au livreur, ou sur ton téléphone (Mobile Money) : le livreur te montre le paiement. Jamais sur le numéro personnel du livreur.",
    "You may open the parcel at the counter before paying.": "Tu peux ouvrir le colis au comptoir avant de payer.",
}

RELAY_EXPRESS_WHATSAPP = {
    "OCD Express: parcel at the relay point": "OCD Express : colis au point relais",
    "OCD Express: parcel at the relay point (English)": "OCD Express : colis au point relais (anglais)",
}
