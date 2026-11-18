# OCD Live : modules Odoo 20 Community

Réservation de lives au studio de Lomé ou à distance, annuaire des lives, shop des vendeurs avec
livraison et reversements, messages WhatsApp, recrutement des animatrices. Tout est fait en
modules Odoo 20 **Community** : aucune application payante n'est nécessaire.

| Module | Rôle |
|---|---|
| `ocd_live` | Réservations (créneaux, paquets, crédits, prix selon l'heure), annuaire des lives et pass, espace vendeur, voix des pages, tableau de bord et écrans de l'équipe (planning, à vérifier), thème du site et du back-office |
| `ocd_live_shop` | Shop des vendeurs : mode de vente et « qui livre » par vendeur, un colis par vendeur, code de livraison, dispatch, livreurs et caisse, paiement à la porte, reversements, régie en direct, commandes de la semaine, prix promo (prix barré, jusqu'à une date), programme des lives |
| `ocd_live_whatsapp` | Messages WhatsApp d'OCD Live (lien personnel, code, ticket, live confirmé, rappels, créneau libéré, pass, annuaire), un seul accord WhatsApp, écran des conversations, avec `whatsapp_cloud` |
| `ocd_live_shop_whatsapp` | Messages WhatsApp des colis (à préparer, en route avec le code, échec, livré, retourné) |
| `ocd_vote` | OCD Vote : concours (miss, awards, talents, écoles) avec candidats numérotés, voix payées en Mobile Money (seules les voix payées comptent), classement en direct, bandeau de la finale, résultats certifiés, espace de l'organisateur et son reversement |
| `ocd_vote_whatsapp` | OCD Vote sur WhatsApp : « VOTE 12 » au bot, voix comptées, finale annoncée |
| `ocd_tickets` | OCD Tickets : billets de concerts et d'événements (application Événements d'Odoo), vendus sur la page de l'événement et pendant les lives, un QR signé par personne contrôlé une fois à l'entrée par le téléphone des contrôleurs (même hors réseau), vente à l'entrée, « Donner ce billet », annulé ou déplacé, reversement à l'organisateur |
| `ocd_tickets_whatsapp` | OCD Tickets sur WhatsApp : billets prêts, rappel la veille, événement annulé ou déplacé, contrôleur ajouté |
| `ocd_soirees` | Grands événements d'OCD Live (Vendredi noir, Noël, Saint-Valentin, Tabaski), d'une soirée ou de plusieurs jours : les vendeurs des pays invités participent avec un live et leurs promos de l'événement, vérifiées par l'équipe ; page de l'événement (compte à rebours, programme jour par jour, promos, « Me prévenir sur WhatsApp »), l'événement sur le programme des lives |
| `ocd_soirees_whatsapp` | Grands événements sur WhatsApp : l'invitation des vendeurs, le début annoncé à ceux qui l'ont demandé |
| `ocd_live_recruitment` | Offre « Animatrice live · Lomé » sur le site, 5 étapes de recrutement, l'embauchée devient animatrice |
| `ocd_delivery_togo` | Régions, villes et quartiers du Togo, point de repère, modes de livraison pour Lomé et le reste du Togo |
| `ocd_debranding` | Aucune mention d'Odoo pour l'équipe, les vendeurs et les clients : site, connexion, portail, back-office, fenêtres d'erreur, e-mails |
| `ocd_live_demo` | Données de démonstration, retirées entièrement en désinstallant le module |
| `theme_ocd` | Thème du site « OCD Live » (polices, couleurs, boutons, en-tête, pied de page du design) pour les pages d'Odoo : à choisir dans Site Web › Configuration › Paramètres › Choisir un thème |

| `whatsapp_cloud` | Conversations WhatsApp dans Odoo, messages automatiques validés par Meta, STOP et START |
| `whatsapp_cloud_sale` | Messages WhatsApp de la commande du shop au client |
| `payment_campay` | Paiement au Cameroun : MTN MoMo, Orange Money, carte |
| `payment_cinetpay` | Paiement dans l'UEMOA, au Cameroun, en Guinée et en RD Congo avec CinetPay : Mobile Money (Orange, MTN, Moov, Free, T-Money, Flooz…), Wave, carte ; Flutterwave (module d'Odoo) en second |
| `delivery_cameroon` | Villes et quartiers du Cameroun, point de repère obligatoire dans l'adresse |

Le dépôt contient tous les modules nécessaires. `disable_odoo_online` (OCA, nécessaire à
`ocd_debranding`) est dans `marketplace/oca_server_brand/` : ajouter ce dossier au chemin des modules. Ce que fait chaque outil pour OCD Live : [`docs/OUTILS_ODOO.md`](docs/OUTILS_ODOO.md).

## Pour reprendre le projet

- [`docs/PROGRESSION.md`](docs/PROGRESSION.md) : où en est le projet, ce qui reste à faire. **À lire en premier.**
- [`docs/DECISIONS.md`](docs/DECISIONS.md) : les choix validés avec l'équipe OCD.
- [`docs/FEUILLE_DE_ROUTE.md`](docs/FEUILLE_DE_ROUTE.md) : les chantiers retenus (OCD Express, OCD Business,
  OCD Tickets, OCD Vote, améliorations), dans leur ordre.
- [`docs/ECRANS.md`](docs/ECRANS.md) : chaque écran du design validé et où il est fait dans le code.
- [`docs/DEVELOPPEMENT.md`](docs/DEVELOPPEMENT.md) : installer, lancer, tester, traduire, faire des captures.
- [`docs/OUTILS_ODOO.md`](docs/OUTILS_ODOO.md) : les outils d'Odoo et ce qu'ils font pour OCD Live.
- [`docs/LIVRAISONS.md`](docs/LIVRAISONS.md) : les frais de livraison (un prix par colis), la mise en
  route des tarifs avant l'ouverture, les questions fréquentes.
- [`docs/RAPPORT_DE_CHARGE.md`](docs/RAPPORT_DE_CHARGE.md) : prouver que le site tient le grand public
  (objectifs, méthode, rapport à remplir, mesures de référence).
- [`prototype/`](prototype/) : le design validé (tous les écrans) et le prototype interactif.
- [`docs/captures/`](docs/captures/) : captures des écrans tels qu'ils sont aujourd'hui.

## Installation rapide

```bash
odoo -c odoo.conf -d ocd -i ocd_live,ocd_live_shop,ocd_live_whatsapp,ocd_live_shop_whatsapp,ocd_live_recruitment,ocd_delivery_togo,ocd_debranding,ocd_vote,ocd_vote_whatsapp,ocd_tickets,ocd_tickets_whatsapp,ocd_soirees,ocd_soirees_whatsapp --load-language=fr_FR
```

Pour voir le projet avec des données : ajouter `ocd_live_demo` (le désinstaller retire tout).
Puis choisir le thème du site : Site Web › Configuration › Paramètres › **Choisir un thème** › « OCD Live ».
