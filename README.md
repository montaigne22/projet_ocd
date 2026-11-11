# OCD Live — modules Odoo 20 Community

Réservation de lives au studio de Lomé ou à distance, annuaire des lives, shop des vendeurs avec
livraison et reversements, messages WhatsApp, recrutement des animatrices. Tout est fait en
modules Odoo 20 **Community** : aucune application payante n'est nécessaire.

| Module | Rôle |
|---|---|
| `ocd_live` | Réservations (créneaux, paquets, crédits, prix selon l'heure), annuaire des lives et pass, espace vendeur, voix des pages, tableau de bord et écrans de l'équipe (planning, à vérifier), thème du site et du back-office |
| `ocd_live_shop` | Shop des vendeurs : mode de vente et « qui livre » par vendeur, un colis par vendeur, code de livraison, dispatch, livreurs et caisse, paiement à la porte, reversements, régie en direct, commandes de la semaine |
| `ocd_live_whatsapp` | Messages WhatsApp d'OCD Live (lien personnel, code, ticket, live confirmé, rappels, créneau libéré, pass, annuaire), un seul accord WhatsApp, écran des conversations, avec `whatsapp_cloud` |
| `ocd_live_shop_whatsapp` | Messages WhatsApp des colis (à préparer, en route avec le code, échec, livré, retourné) |
| `ocd_live_recruitment` | Offre « Animatrice live · Lomé » sur le site, 5 étapes de recrutement, l'embauchée devient animatrice |
| `ocd_delivery_togo` | Régions, villes et quartiers du Togo, point de repère, modes de livraison pour Lomé et le reste du Togo |
| `ocd_debranding` | Aucune mention d'Odoo pour l'équipe, les vendeurs et les clients : site, connexion, portail, back-office, fenêtres d'erreur, e-mails |
| `ocd_live_demo` | Données de démonstration, retirées entièrement en désinstallant le module |

| `whatsapp_cloud` | Conversations WhatsApp dans Odoo, messages automatiques validés par Meta, STOP et START |
| `whatsapp_cloud_sale` | Messages WhatsApp de la commande du shop au client |
| `payment_campay` | Paiement au Cameroun : MTN MoMo, Orange Money, carte |
| `delivery_cameroon` | Villes et quartiers du Cameroun, point de repère obligatoire dans l'adresse |

Le dépôt contient tous les modules nécessaires, sauf `disable_odoo_online` (OCA, dépôt
[server-brand](https://github.com/OCA/server-brand), branche 20.0), à ajouter au chemin des modules
pour `ocd_debranding`. Ce que fait chaque outil pour OCD Live : [`docs/OUTILS_ODOO.md`](docs/OUTILS_ODOO.md).

## Pour reprendre le projet

- [`docs/PROGRESSION.md`](docs/PROGRESSION.md) : où en est le projet, ce qui reste à faire. **À lire en premier.**
- [`docs/DECISIONS.md`](docs/DECISIONS.md) : les choix validés avec l'équipe OCD.
- [`docs/ECRANS.md`](docs/ECRANS.md) : chaque écran du design validé et où il est fait dans le code.
- [`docs/DEVELOPPEMENT.md`](docs/DEVELOPPEMENT.md) : installer, lancer, tester, traduire, faire des captures.
- [`docs/OUTILS_ODOO.md`](docs/OUTILS_ODOO.md) : les outils d'Odoo et ce qu'ils font pour OCD Live.
- [`docs/LIVRAISONS.md`](docs/LIVRAISONS.md) : les frais de livraison (un prix par colis), la mise en
  route des tarifs avant l'ouverture, les questions fréquentes.
- [`prototype/`](prototype/) : le design validé (tous les écrans) et le prototype interactif.
- [`docs/captures/`](docs/captures/) : captures des écrans tels qu'ils sont aujourd'hui.

## Installation rapide

```bash
odoo -c odoo.conf -d ocd -i ocd_live,ocd_live_shop,ocd_live_whatsapp,ocd_live_shop_whatsapp,ocd_live_recruitment,ocd_delivery_togo,ocd_debranding --load-language=fr_FR
```

Pour voir le projet avec des données : ajouter `ocd_live_demo` (le désinstaller retire tout).
