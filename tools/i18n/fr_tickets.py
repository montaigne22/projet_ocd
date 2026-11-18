# Chantier 6: OCD Tickets, the tickets of the events (ocd_tickets, ocd_tickets_whatsapp)
TICKETS = {
    "%(day)s · %(hour)s": "%(day)s · %(hour)s",
    "%(kind)s ticket · %(event)s · %(when)s": "Billet %(kind)s · %(event)s · %(when)s",
    "%(price)s · price of the live": "%(price)s · prix du live",
    "%s a ticket": "%s le billet",
    "%s already entered: no refund.": "%s est déjà entré : pas de remboursement.",
    "%s entries noted without the network, sent when it is back.":
        "%s entrées notées sans réseau, envoyées dès son retour.",
    "%s has tickets sold: use « Move » so that the buyers are told and may ask for a refund.":
        "%s a des billets vendus : utilise « Déplacer » pour que les acheteurs soient prévenus et puissent demander le remboursement.",
    "%s tickets": "%s billets",
    "%s tickets at most per order.": "%s billets au plus par commande.",
    "%s tickets created by the payment.": "%s billets créés par le paiement.",
    "%s tickets sold": "%s billets vendus",
    "'Tickets %s' % (object.event_id.name)": "'Billets %s' % (object.event_id.name)",
    "1 entry noted without the network, sent when it is back.": "1 entrée notée sans réseau, envoyée dès son retour.",
    "1 ticket": "1 billet",
    "1 ticket refunded or to refund on your number.": "1 billet remboursé ou à rembourser sur ton numéro.",
    "1 ticket sold": "1 billet vendu",
    "1 left": "Il en reste 1",
    "%s left": "Il en reste %s",
    "Sold out": "Épuisé",
    "Only %s left": "Plus que %s",
    "24 hours before the start of an event": "24 heures avant le début d'un événement",
    "<b>OCD Live guarantee</b>\n            <span>Event cancelled: refunded. The organiser is paid after the event.</span>":
        "<b>Garantie OCD Live</b>\n            <span>Événement annulé : remboursé. L'organisateur est payé après l'événement.</span>",
    "<b>Payment not received: no ticket.</b>\n                                <span>Nothing was taken; the seats went back on sale.</span>":
        "<b>Paiement pas reçu : aucun billet.</b>\n                                <span>Rien n'a été pris ; les places sont remises en vente.</span>",
    "<b>Thank you: the team checks your payment.</b>\n                                    <span>Your seats stay held; your tickets arrive once it is checked.</span>":
        "<b>Merci : l'équipe vérifie ton paiement.</b>\n                                    <span>Tes places restent gardées ; tes billets arrivent une fois le paiement vérifié.</span>",
    "<b>The payment did not go through.</b>\n                            <span>Refused or cancelled on the phone, or not enough money. Nothing was taken.</span>":
        "<b>Le paiement n'est pas passé.</b>\n                            <span>Refusé ou annulé sur le téléphone, ou pas assez d'argent. Rien n'a été pris.</span>",
    "<i class=\"o_ocd_onair_dot\" aria-hidden=\"true\"/>\n                            <b>Live now</b>":
        "<i class=\"o_ocd_onair_dot\" aria-hidden=\"true\"/>\n                            <b>En live maintenant</b>",
    "<small class=\"o_ocd_tk_muted o_ocd_tk_offline\">Without the network: the list of the tickets stays in the phone, the entries leave as soon as the network is back.</small>\n                    <small class=\"o_ocd_tk_muted o_ocd_tk_pending\" hidden=\"hidden\"/>":
        "<small class=\"o_ocd_tk_muted o_ocd_tk_offline\">Hors réseau : la liste des billets reste dans le téléphone, les entrées partent dès que le réseau revient.</small>\n                    <small class=\"o_ocd_tk_muted o_ocd_tk_pending\" hidden=\"hidden\"/>",
    "<small class=\"o_ocd_tk_muted\">Allowed by the organiser: you sell on the spot.</small>":
        "<small class=\"o_ocd_tk_muted\">Autorisé par l'organisateur : tu vends sur place.</small>",
    "<small class=\"o_ocd_tk_muted\">Reminder on WhatsApp the day before, with the route.</small>":
        "<small class=\"o_ocd_tk_muted\">Rappel sur WhatsApp la veille, avec l'itinéraire.</small>",
    "<small class=\"o_ocd_tk_muted\">The ticket leaves on the WhatsApp of the customer and enters at once. The cash is counted with you at the end of the evening, like the cash of the couriers.</small>":
        "<small class=\"o_ocd_tk_muted\">Le billet part sur le WhatsApp du client et entre aussitôt. Les espèces sont comptées avec toi à la fin de la soirée, comme la caisse des livreurs.</small>",
    "<small class=\"o_ocd_tk_muted\">The ticket leaves on their WhatsApp with a new QR; the old one no longer works.</small>":
        "<small class=\"o_ocd_tk_muted\">Le billet part sur son WhatsApp avec un nouveau QR ; l'ancien ne marche plus.</small>",
    "<small class=\"o_ocd_tk_muted\">Then the payment of OCD Live: Mobile Money on your phone, or card. Your tickets arrive on WhatsApp as soon as the money is received, and stay in « My tickets ».</small>":
        "<small class=\"o_ocd_tk_muted\">Puis le paiement d'OCD Live : Mobile Money sur ton téléphone, ou carte. Tes billets arrivent sur WhatsApp dès que l'argent est reçu, et restent dans « Mes billets ».</small>",
    "<small class=\"o_ocd_vote_muted\">Their name, their WhatsApp, their gate: a message leaves on their WhatsApp. The evening of the event, they open « Entrance » and scan with the camera of their phone.</small>":
        "<small class=\"o_ocd_vote_muted\">Son nom, son WhatsApp, sa porte : un message part sur son WhatsApp. Le soir de l'événement, la personne ouvre « Entrée » et scanne avec la caméra de son téléphone.</small>",
    "<span class=\"o_ocd_tk_frame\" aria-hidden=\"true\"/>\n                        <span class=\"o_ocd_tk_hint\">Put the QR of the ticket in the frame</span>":
        "<span class=\"o_ocd_tk_frame\" aria-hidden=\"true\"/>\n                        <span class=\"o_ocd_tk_hint\">Mets le QR du billet dans le cadre</span>",
    "<span class=\"o_ocd_tk_muted o_ocd_tk_total_what\">Total</span><b class=\"o_ocd_tk_total_amount\"/>":
        "<span class=\"o_ocd_tk_muted o_ocd_tk_total_what\">Total</span><b class=\"o_ocd_tk_total_amount\"/>",
    "<span>Entered</span>": "<span>Entrés</span>",
    "<span>Open the camera</span>": "<span>Ouvrir la caméra</span>",
    "<span>Sells at the door</span>": "<span>Vend à l'entrée</span>",
    "<span>Sent on your WhatsApp. Show one QR per person at the entrance.</span>":
        "<span>Envoyés sur ton WhatsApp. Montre un QR par personne à l'entrée.</span>",
    "<span>Share the event</span>": "<span>Partager l'événement</span>",
    "<span>Tickets</span>": "<span>Billets</span>",
    "A buyer who cannot come at the new date asks for a refund during these days. No refund for a buyer who does not come.":
        "Un acheteur qui ne peut pas venir à la nouvelle date demande le remboursement pendant ces jours. Pas de remboursement pour un acheteur qui ne vient pas.",
    "A first event": "Un premier événement",
    "A ticket exists when its payment is confirmed: one per person, with its QR.":
        "Un billet existe quand son paiement est confirmé : un par personne, avec son QR.",
    "About The Event": "L'événement en quelques mots",
    "Add a controller": "Ajouter un contrôleur",
    "Add the kinds of tickets first (Standard, VIP...).": "Ajoute d'abord les types de billets (Standard, VIP…).",
    "Added by the organisers in their space, or here: they scan the tickets with their phone.":
        "Ajoutés par les organisateurs dans leur espace, ou ici : ils scannent les billets avec leur téléphone.",
    "Added: %s receives the news on WhatsApp.": "C'est ajouté : %s reçoit la nouvelle sur WhatsApp.",
    "Address Of The Page": "Adresse de la page",
    "After the event: payout to the organiser": "Après l'événement : reversement à l'organisateur",
    "Already entered": "Déjà entré",
    "Amount Of The Tickets": "Montant des billets",
    "Another event has this address.": "Un autre événement a cette adresse.",
    "Another ticket has this code.": "Un autre billet a ce code.",
    "At %(hour)s, %(gate)s, by %(who)s": "À %(hour)s, %(gate)s, par %(who)s",
    "At most, all kinds together.": "Au plus, tous types confondus.",
    "At the end of an event": "À la fin d'un événement",
    "By ticket": "Par billet",
    "Cancel and refund": "Annuler et rembourser",
    "Cancelled by %(user)s: %(count)s tickets to refund.": "Annulé par %(user)s : %(count)s billets à rembourser.",
    "Cancelled: they are refunded on their number. Moved: their tickets stay valid, refund on request for a few days.":
        "Annulé : ils sont remboursés sur leur numéro. Déplacé : leurs billets restent valables, remboursement sur demande pendant quelques jours.",
    "Cash To Collect": "Espèces à récupérer",
    "Cash at the door": "Espèces à l'entrée",
    "Cash collected": "Espèces récupérées",
    "Cash collected by %s.": "Espèces récupérées par %s.",
    "Cash not received": "Espèces pas reçues",
    "Cash to collect": "Espèces à récupérer",
    "Check and put on sale": "Vérifier et mettre en vente",
    "Checked by %s: on sale.": "Vérifié par %s : en vente.",
    "Checked by OCD Live": "Vérifié par OCD Live",
    "Choose at least one ticket.": "Choisis au moins un billet.",
    "Choose my tickets": "Choisir mes billets",
    "Code Of The Ticket": "Code du billet",
    "Collected During The Lives": "Encaissé pendant les lives",
    "Concerts and events: pay with Mobile Money, your tickets arrive on WhatsApp.":
        "Concerts et événements : paie en Mobile Money, tes billets arrivent sur WhatsApp.",
    "Controller Of An Event": "Contrôleur d'un événement",
    "Controllers": "Contrôleurs",
    "Controls Of Events": "Contrôles d'événements",
    "Currency Of OCD Tickets": "Devise d'OCD Tickets",
    "Currency Of The Company": "Devise de la société",
    "Days after an event is moved during which a buyer who cannot come asks for a refund.":
        "Jours après le déplacement d'un événement pendant lesquels un acheteur qui ne peut pas venir demande le remboursement.",
    "Do not let in.": "Ne pas laisser entrer.",
    "Do not let in. A ticket given to a friend has a new QR: the old one is refused.":
        "Ne pas laisser entrer. Un billet donné à un ami a un nouveau QR : l'ancien est refusé.",
    "Doors Open At": "Ouverture des portes",
    "Doors open at %(hour)s (time of %(city)s)": "Ouverture des portes %(hour)s (heure de %(city)s)",
    "Download (PDF)": "Télécharger (PDF)",
    "During a live": "Pendant un live",
    "During the lives selling the tickets, until the end of the live only. 0: the usual price.":
        "Pendant les lives qui vendent les billets, jusqu'à la fin du live seulement. 0 : le prix habituel.",
    "During these lives, the control room shows the tickets like products, at their live price if any.":
        "Pendant ces lives, la régie montre les billets comme des produits, à leur prix du live s'il y en a un.",
    "Each kind of ticket has a price: OCD Tickets sells no free ticket.":
        "Chaque type de billet a un prix : OCD Tickets ne vend pas de billet gratuit.",
    "Empty: an event of OCD Live. The organiser logs in with their number, like for OCD Vote.":
        "Vide : un événement d'OCD Live. L'organisateur se connecte avec son numéro, comme pour OCD Vote.",
    "End Of The Online Sales": "Fin des ventes en ligne",
    "End of the online sales": "Fin des ventes en ligne",
    "Entered": "Entrés",
    "Entered at %s": "Entré à %s",
    "Entrance": "Entrée",
    "Entrance · %s": "Entrée · %s",
    "Entries": "Entrées",
    "Entries of %s": "Entrées de %s",
    "Entry OK": "Entrée OK",
    "Event": "Événement",
    "Event Of The Tickets": "Événement des billets",
    "Event Registration": "Inscription à l'événement",
    "Event Ticket": "Ticket d'événement",
    "Event cancelled or moved: tell the buyers": "Événement annulé ou déplacé : prévenir les acheteurs",
    "Event passed: the share of the organiser is to pay.": "Événement passé : la part de l'organisateur est à verser.",
    "Event sent": "Événement envoyé",
    "Events": "Événements",
    "Events Whose Tickets Are Sold": "Événements dont les billets sont vendus",
    "Every ticket paid is to refund and the buyers are told. Cancel this event?":
        "Chaque billet payé est à rembourser et les acheteurs sont prévenus. Annuler cet événement ?",
    "For the controllers added by the organiser: give the number the organiser gave.":
        "Pour les contrôleurs ajoutés par l'organisateur : donne le numéro que l'organisateur a donné.",
    "From %s": "Dès %s",
    "Gate": "Porte",
    "Give the ticket": "Donner le billet",
    "Give this ticket": "Donner ce billet",
    "Given By": "Donné par",
    "Given by": "Donné par",
    "Given by %(before)s to %(after)s: a new QR, the old one no longer works.":
        "Donné par %(before)s à %(after)s : un nouveau QR, l'ancien ne marche plus.",
    "Given: the ticket left on the WhatsApp of %s with a new QR.":
        "Donné : le billet est parti sur le WhatsApp de %s avec un nouveau QR.",
    "Hello, I report the event %s on OCD Tickets.": "Bonjour, je signale l'événement %s sur OCD Tickets.",
    "Hello, I want to pay my tickets %(order)s (%(total)s) from %(country)s.":
        "Bonjour, je veux payer mes billets %(order)s (%(total)s) depuis %(country)s.",
    "Hello, I want to sell the tickets of %s during a live of OCD Live.":
        "Bonjour, je veux vendre les billets de %s pendant un live d'OCD Live.",
    "Hours before the start of the event; 0: at the start. The sale at the door goes on.":
        "Heures avant le début de l'événement ; 0 : au début. La vente à l'entrée continue.",
    "Hours before the start; 0: at the start. The sale at the door goes on.":
        "Heures avant le début ; 0 : au début. La vente à l'entrée continue.",
    "How many tickets?": "Combien de billets ?",
    "I cannot come: refund me": "Je ne peux pas venir : me rembourser",
    "It is paid: %s tickets": "C'est payé : %s billets",
    "It is paid: 1 ticket": "C'est payé : 1 billet",
    "Its date, its place and its kinds of tickets; the tab « OCD Live »: the organiser, their share, the\n                poster, the sale at the door and the controllers. Then « Check and put on sale ».":
        "Sa date, son lieu et ses types de billets ; l'onglet « OCD Live » : l'organisateur, sa part,\n                l'affiche, la vente à l'entrée et les contrôleurs. Puis « Vérifier et mettre en vente ».",
    "Its tickets are sold on the site of OCD Live, paid like the rest of OCD Live, checked at the entrance by the controllers.":
        "Ses billets sont vendus sur le site d'OCD Live, payés comme le reste d'OCD Live, contrôlés à l'entrée par les contrôleurs.",
    "Let In": "Laissés entrer",
    "Live Price": "Prix du live",
    "Live price until the end of the live.": "Prix du live jusqu'à la fin du live.",
    "Live prices": "Prix du live",
    "Lives Selling The Tickets": "Lives qui vendent les billets",
    "Log in again": "Se reconnecter",
    "Logs in with their number on /vote/organisateur, like the vendors: their contests and their events.":
        "Se connecte avec son numéro sur /vote/organisateur, comme les vendeurs : ses concours et ses événements.",
    "Minutes; past them, the tickets not paid are given back for sale (a payment checked by the team keeps them).":
        "Minutes ; passé ce délai, les billets non payés sont remis en vente (un paiement vérifié par l'équipe les garde).",
    "Move %s": "Déplacer %s",
    "Move An Event": "Déplacer un événement",
    "Move the event": "Déplacer l'événement",
    "Move": "Déplacer",
    "Moved On": "Déplacé le",
    "Moved by %(user)s to %(when)s.": "Déplacé par %(user)s au %(when)s.",
    "Moved to %(when)s. You cannot come? Ask for the refund before %(day)s.":
        "Déplacé au %(when)s. Tu ne peux pas venir ? Demande le remboursement avant le %(day)s.",
    "Moved: the tickets bought before stay valid.": "Déplacé : les billets achetés avant restent valables.",
    "My contests and events": "Mes concours et événements",
    "My controllers": "Mes contrôleurs",
    "My event": "Mon événement",
    "My ticket": "Mon billet",
    "My tickets": "Mes billets",
    "NAB-7K2Q-41": "NAB-7K2Q-41",
    "Name On The Tickets": "Nom sur les billets",
    "Name of your friend": "Nom de la personne",
    "New End": "Nouvelle fin",
    "New Start": "Nouveau début",
    "New event": "Nouvel événement",
    "No cash": "Pas d'espèces",
    "No controller yet: add the people who check the tickets at the doors.":
        "Pas encore de contrôleur : ajoute les personnes qui contrôlent les billets aux portes.",
    "No event on sale for now.": "Aucun événement en vente pour l'instant.",
    "No event to control for now.": "Aucun événement à contrôler pour l'instant.",
    "No event waiting.": "Aucun événement en attente.",
    "No ticket sold yet": "Aucun billet vendu pour l'instant",
    "Not enough seats left for %s tickets.": "Plus assez de places pour %s billets.",
    "Not for tonight": "Pas pour ce soir",
    "Not in the list of the phone: refuse, or check again with the network.":
        "Pas dans la liste du téléphone : refuser, ou vérifier de nouveau avec le réseau.",
    "Note the share of the organiser to pay within 3 days, like the payouts of the vendors.":
        "Noter la part de l'organisateur à verser sous 3 jours, comme les reversements des vendeurs.",
    "Noted: the team refunds your tickets on your number.": "C'est noté : l'équipe rembourse tes billets sur ton numéro.",
    "OCD Tickets": "OCD Tickets",
    "OCD Tickets: Tickets For Concerts And Events": "OCD Tickets : billets de concerts et d'événements",
    "OCD Tickets: seats not paid back on sale, reminders, payouts":
        "OCD Tickets : places non payées remises en vente, rappels, reversements",
    "Secret Of My Tickets": "Secret de « Mes billets »",
    "Of the tickets sold, paid after the event; the rest for OCD Live (with the fees of the Mobile Money). No fee added for the buyer.":
        "Des billets vendus, versée après l'événement ; le reste pour OCD Live (frais du Mobile Money compris). Aucun frais en plus pour l'acheteur.",
    "Once on sale, the date and the prices change only with the team: the buyers are told on WhatsApp.":
        "Une fois en vente, la date et les prix ne changent qu'avec l'équipe : les acheteurs sont prévenus sur WhatsApp.",
    "Only %(left)s « %(kind)s » tickets left.": "Plus que %(left)s billets « %(kind)s ».",
    "Open the entrance": "Ouvrir l'entrée",
    "Organiser (Contests And Events)": "Organisateur (concours et événements)",
    "Organiser On OCD Tickets": "Organisateur sur OCD Tickets",
    "Passed": "Passé",
    "Past this time, the tickets not paid go back on sale; a payment checked by the team keeps them.":
        "Passé ce délai, les billets non payés sont remis en vente ; un paiement vérifié par l'équipe les garde.",
    "Place or date unclear": "Lieu ou date pas clairs",
    "Planned Before At": "Prévu avant le",
    "Poster": "Affiche",
    "Poster not suitable": "Affiche pas adaptée",
    "Proof of the event missing": "Preuve de l'événement manquante",
    "QR of the ticket": "QR du billet",
    "Refund": "Remboursement",
    "Refund On Request After A Move": "Remboursement sur demande après un report",
    "Refund on request after a move": "Remboursement sur demande après un report",
    "Refunded by %s.": "Remboursé par %s.",
    "Refunded or cancelled: refuse.": "Remboursé ou annulé : refuser.",
    "Remind them of the hour, the doors and the place, with the button « My tickets ».":
        "Leur rappeler l'heure, l'ouverture des portes et le lieu, avec le bouton « Mes billets ».",
    "Reminder Sent At": "Rappel envoyé le",
    "Route": "Itinéraire",
    "Sale": "Vente",
    "Sale At The Door": "Vente à l'entrée",
    "Seats Held During The Payment": "Places gardées pendant le paiement",
    "Seats Held Until": "Places gardées jusqu'au",
    "Seats held during the payment": "Places gardées pendant le paiement",
    "See the event": "Voir l'événement",
    "Sell at the door": "Vendre à l'entrée",
    "Sell during a live": "Vendre pendant un live",
    "Sells At The Door": "Vend à l'entrée",
    "Send my event to OCD Live": "Envoyer mon événement à OCD Live",
    "Send the tickets on WhatsApp, with the button « My tickets ».":
        "Envoyer les billets sur WhatsApp, avec le bouton « Mes billets ».",
    "Sent: the team checks your event and writes to you on WhatsApp.":
        "Envoyé : l'équipe vérifie ton événement et t'écrit sur WhatsApp.",
    "Share Of The Organiser Of An Event (%)": "Part de l'organisateur d'un événement (%)",
    "Shown again without the network at %(hour)s by %(who)s.": "Montré de nouveau hors réseau à %(hour)s (contrôle : %(who)s).",
    "Six artists, two stages, from 20:00 until dawn.": "Six artistes, deux scènes, de 20 h à l'aube.",
    "Sold At The Door By": "Vendu à l'entrée par",
    "Sold On OCD Tickets": "Vendu sur OCD Tickets",
    "Sold at the door": "Vendu à l'entrée",
    "Sold during a live": "Vendu pendant un live",
    "Sold: the ticket left on the WhatsApp of the customer and entered.":
        "Vendu : le billet est parti sur le WhatsApp du client et il est entré.",
    "State On OCD Tickets": "État sur OCD Tickets",
    "The buyer cannot come at the new date: %s tickets to refund.":
        "L'acheteur ne peut pas venir à la nouvelle date : %s billets à rembourser.",
    "The buyers, and the friends who received a ticket.": "Les acheteurs, et les amis qui ont reçu un billet.",
    "The camera did not open: allow it in the browser, or type the code below.":
        "La caméra ne s'est pas ouverte : autorise-la dans le navigateur, ou tape le code en dessous.",
    "The cash of the door is counted with this controller?": "Les espèces de l'entrée sont comptées avec ce contrôleur ?",
    "The controllers of the events": "Les contrôleurs des événements",
    "The controllers who may sell sell tickets at the entrance (cash or Mobile Money).":
        "Les contrôleurs autorisés vendent des billets à l'entrée (espèces ou Mobile Money).",
    "The day before: reminder to the buyers": "La veille : rappel aux acheteurs",
    "The end of the address of its page: /billets/<address>.": "La fin de l'adresse de sa page : /billets/<adresse>.",
    "The entrance of your event.": "L'entrée de ton événement.",
    "The evening: the entries": "Le soir : les entrées",
    "The event ends after it starts.": "L'événement finit après son début.",
    "The event is over.": "L'événement est terminé.",
    "The events of an organiser with tickets sold.": "Les événements d'un organisateur avec des billets vendus.",
    "The holders of the tickets paid.": "Les détenteurs des billets payés.",
    "The payment provider (Mobile Money, card), the team that checks the payment, the sale at the door.":
        "Le moyen de paiement (Mobile Money, carte), l'équipe qui vérifie le paiement, la vente à l'entrée.",
    "The place or the date of the event is missing or unclear: write the hall, the city and the hours, then send it again.":
        "Le lieu ou la date de l'événement manque ou n'est pas clair : écris la salle, la ville et les heures, puis renvoie-le.",
    "The poster of the event is blurry or not suitable. Send another poster.":
        "L'affiche de l'événement est floue ou pas adaptée. Envoie une autre affiche.",
    "The price of the ticket, in the currency of the company.": "Le prix du billet, dans la devise de la société.",
    "The sale at the door is not open for this event.": "La vente à l'entrée n'est pas ouverte pour cet événement.",
    "The sale on the site is over.": "La vente sur le site est terminée.",
    "The sale on the site is over: tickets at the door, if there are any left.":
        "La vente sur le site est terminée : billets à l'entrée, s'il en reste.",
    "The team needs a proof that the event takes place (contract of the hall, artists): send it on WhatsApp.":
        "L'équipe a besoin d'une preuve que l'événement a lieu (contrat de la salle, artistes) : envoie-la sur WhatsApp.",
    "The tickets": "Les billets",
    "The tickets of %s are not on sale.": "Les billets de %s ne sont pas en vente.",
    "The tickets stay valid at the new date. The buyers are told on WhatsApp and may ask for a refund for a\n                    few days (Settings › Tickets).":
        "Les billets restent valables à la nouvelle date. Les acheteurs sont prévenus sur WhatsApp et peuvent demander le\n                    remboursement pendant quelques jours (Paramètres › Billets).",
    "Their WhatsApp": "Son WhatsApp",
    "Their gate (if you want)": "Sa porte (si tu veux)",
    "This contact already controls this event.": "Ce contact contrôle déjà cet événement.",
    "This event is cancelled: every buyer is refunded on their number.":
        "Cet événement est annulé : chaque acheteur est remboursé sur son numéro.",
    "This event is over.": "Cet événement est terminé.",
    "This ticket can no longer be given.": "Ce billet ne peut plus être donné.",
    "This ticket is already in this name.": "Ce billet est déjà à ce nom.",
    "This ticket is not for this event.": "Ce billet n'est pas pour cet événement.",
    "This ticket no longer lets in, and is refunded by the team. Go on?":
        "Ce billet ne laisse plus entrer, et il est remboursé par l'équipe. Continuer ?",
    "This ticket no longer lets in.": "Ce billet ne laisse plus entrer.",
    "Ticket %(index)s of %(count)s · %(kind)s": "Billet %(index)s sur %(count)s · %(kind)s",
    "Ticket of OCD Tickets": "Billet d'OCD Tickets",
    "Ticket of « %(event)s », on %(day)s": "Billet de « %(event)s », le %(day)s",
    "Tickets": "Billets",
    "Tickets (OCD Tickets)": "Billets (OCD Tickets)",
    "Tickets Per Order": "Billets par commande",
    "Tickets Sold": "Billets vendus",
    "Tickets of %s": "Billets de %s",
    "Tickets of concerts and events sold on their page and during the lives, paid like the rest of OCD Live, one signed QR per person checked once at the entrance, payout to the organiser":
        "Billets de concerts et d'événements vendus sur leur page et pendant les lives, payés comme le reste d'OCD Live, un QR signé par personne contrôlé une seule fois à l'entrée, reversement à l'organisateur",
    "Tickets of the events": "Billets des événements",
    "Tickets paid: send them": "Billets payés : les envoyer",
    "Tickets per order": "Billets par commande",
    "Tickets sold": "Billets vendus",
    "Time of %s": "Heure de %s",
    "Type the code of the ticket": "Taper le code du billet",
    "Type the code of the ticket below.": "Tape le code du billet en dessous.",
    "Unknown ticket": "Billet inconnu",
    "Valid only once. Keep it for yourself: a screenshot is enough to enter.":
        "Valable une seule fois. Garde-le pour toi : une capture d'écran suffit à entrer.",
    "Version Of The QR": "Version du QR",
    "What the event is, in a few sentences.": "Ce qu'est l'événement, en quelques phrases.",
    "WhatsApp of the customer": "WhatsApp du client",
    "When the organiser allows the sale at the door.": "Quand l'organisateur autorise la vente à l'entrée.",
    "When the payment of tickets is confirmed, or a ticket is given to a friend":
        "Quand le paiement de billets est confirmé, ou qu'un billet est donné à un ami",
    "When the team cancels or moves an event": "Quand l'équipe annule ou déplace un événement",
    "Without the network: noted in the phone.": "Hors réseau : noté dans le téléphone.",
    "Write the place of the event.": "Écris le lieu de l'événement.",
    "Write your name: it is on the tickets.": "Écris ton nom : il est sur les billets.",
    "Wrong code or changed copy: refuse.": "Code faux ou copie modifiée : refuser.",
    "Your WhatsApp (the tickets arrive there)": "Ton WhatsApp (les billets y arrivent)",
    "Your name (on the tickets)": "Ton nom (sur les billets)",
    "Your seats are held %s minutes.": "Tes places sont gardées %s minutes.",
    "Your share paid 3 days after the event": "Ta part versée 3 jours après l'événement",
    "control only": "contrôle seulement",
    "e.g. Concert": "ex. Concert",
    "e.g. Gate 1": "ex. Porte 1",
    "of %s": "sur %s",
    "of which %s during the lives": "dont %s pendant les lives",
    "paid after the event": "versée après l'événement",
    "sells at the door": "vend à l'entrée",
    "the evening itself": "le soir même",
    "tickets refunded or to refund on your number.": "billets remboursés ou à rembourser sur ton numéro.",
    "with the payment of OCD Live": "avec le paiement d'OCD Live",
    "« %s » is sold out.": "« %s » est épuisé.",
    "« Cancel and refund », « Move » on the event.": "« Annuler et rembourser », « Déplacer » sur l'événement.",
    "« Concert », « Gala », « Festival »: shown above the name.": "« Concert », « Gala », « Festival » : montré au-dessus du nom.",
    "« Gate 1 »: shown on the entries let in.": "« Porte 1 » : montré sur les entrées laissées passer.",
    "· OCD Tickets": "· OCD Tickets",
    "· Tickets": "· Billets",
    "Pay": "Payer",
    "Pay %s": "Payer %s",
    "Check": "Vérifier",
    "Remove": "Retirer",
    "Kind": "Type",
    "doors %s": "portes %s",
    "Entered At": "Entré à",
    "Let In By": "Laissé entrer par",
    "HTTP Routing": "Routage HTTP",
    "Ticket not valid": "Billet pas valable",
}

TICKETS_WHATSAPP = {
    "Controller Of An Event": "Contrôleur d'un événement",
    "Event Registration": "Inscription à l'événement",
    "OCD Tickets: WhatsApp": "OCD Tickets : WhatsApp",
    "OCD Tickets: controller added": "OCD Tickets : contrôleur ajouté",
    "OCD Tickets: controller added (English)": "OCD Tickets : contrôleur ajouté (anglais)",
    "OCD Tickets: event cancelled": "OCD Tickets : événement annulé",
    "OCD Tickets: event cancelled (English)": "OCD Tickets : événement annulé (anglais)",
    "OCD Tickets: event moved": "OCD Tickets : événement déplacé",
    "OCD Tickets: event moved (English)": "OCD Tickets : événement déplacé (anglais)",
    "OCD Tickets: reminder the day before": "OCD Tickets : rappel la veille",
    "OCD Tickets: reminder the day before (English)": "OCD Tickets : rappel la veille (anglais)",
    "OCD Tickets: tickets ready": "OCD Tickets : billets prêts",
    "OCD Tickets: tickets ready (English)": "OCD Tickets : billets prêts (anglais)",
    "The tickets sent on WhatsApp once paid or given, the reminder the day before, the event cancelled or moved told to the buyers, the controllers told of their event":
        "Les billets envoyés sur WhatsApp une fois payés ou donnés, le rappel la veille, l'événement annulé ou déplacé annoncé aux acheteurs, les contrôleurs prévenus de leur événement",
}

TICKETS_DESCRIPTION = """
OCD Tickets
===========

- Un événement d'un organisateur (vérifié par l'équipe, le même compte que
  pour OCD Vote) ou d'OCD Live, fait avec l'application Événements d'Odoo : sa
  date, son lieu, ses types de billets et leurs places.
- Le public achète sur la page de l'événement : un nombre par type de billet,
  le nom sur les billets, le numéro WhatsApp, puis le formulaire de paiement
  d'OCD Live (Mobile Money, carte…). Les places sont gardées pendant le
  paiement, puis remises en vente. Un billet existe quand son paiement est
  confirmé.
- « Mes billets » : un QR par personne, signé par le serveur, valable une fois ;
  le PDF ; « Donner ce billet » à un ami (un nouveau QR, l'ancien ne marche
  plus).
- Les contrôleurs de l'organisateur se connectent avec leur numéro et
  scannent les billets avec la caméra de leur téléphone, sans application ; la
  liste des billets reste dans le téléphone quand le réseau s'en va. Ils
  peuvent vendre à l'entrée (espèces ou Mobile Money) quand l'organisateur
  l'autorise.
- Pendant un live, la régie montre un billet comme un produit, avec un prix du
  live si l'organisateur le veut.
- Annulé : chaque acheteur est remboursé ; déplacé : les billets restent
  valables, remboursement sur demande pendant quelques jours. L'organisateur
  est payé quelques jours après l'événement.
"""
