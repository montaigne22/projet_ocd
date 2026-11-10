# OCD Live — modules Odoo 20 Community

Réservation de lives au studio de Lomé ou à distance, annuaire des lives, shop des vendeurs avec
livraison et reversements, messages WhatsApp, recrutement des animatrices. Tout est fait en
modules Odoo 20 **Community** : aucune application payante n'est nécessaire.

| Module | Rôle |
|---|---|
| `ocd_live` | Réservations (créneaux, paquets, crédits, prix selon l'heure), annuaire des lives et pass, espace vendeur, voix des pages, tableau de bord et écrans de l'équipe (planning, à vérifier, outils), thème du site et du back-office |
| `ocd_live_shop` | Shop des vendeurs : mode de vente et « qui livre » par vendeur, un colis par vendeur, code de livraison, dispatch, livreurs et caisse, paiement à la porte, reversements, régie en direct, commandes de la semaine |
| `ocd_live_whatsapp` | Messages WhatsApp d'OCD Live (lien personnel, code, live confirmé, rappels, pass, annuaire) avec `whatsapp_cloud` |
| `ocd_live_shop_whatsapp` | Messages WhatsApp des colis (à préparer, en route avec le code, échec, livré, retourné) |
| `ocd_live_recruitment` | Offre « Animatrice live · Lomé » sur le site, 5 étapes de recrutement, l'embauchée devient animatrice |
| `ocd_delivery_togo` | Régions, villes et quartiers du Togo, point de repère, modes de livraison pour Lomé et le reste du Togo |
| `ocd_live_demo` | Données de démonstration, retirées entièrement en désinstallant le module |

Les modules `whatsapp_cloud`, `whatsapp_cloud_sale`, `payment_campay` et `delivery_cameroon`
viennent du dépôt `tchokos-projet` : ils doivent être dans le chemin des modules (`addons_path`).

## Pour reprendre le projet

- [`docs/PROGRESSION.md`](docs/PROGRESSION.md) : où en est le projet, ce qui reste à faire. **À lire en premier.**
- [`docs/DECISIONS.md`](docs/DECISIONS.md) : les choix validés avec l'équipe OCD.
- [`docs/ECRANS.md`](docs/ECRANS.md) : chaque écran du design validé et où il est fait dans le code.
- [`docs/DEVELOPPEMENT.md`](docs/DEVELOPPEMENT.md) : installer, lancer, tester, traduire, faire des captures.
- [`prototype/`](prototype/) : le design validé (tous les écrans) et le prototype interactif.
- [`docs/captures/`](docs/captures/) : captures des écrans tels qu'ils sont aujourd'hui.

## Installation rapide

```bash
odoo -c odoo.conf -d ocd -i ocd_live,ocd_live_shop,ocd_live_whatsapp,ocd_live_shop_whatsapp,ocd_live_recruitment,ocd_delivery_togo --load-language=fr_FR
```

Pour voir le projet avec des données : ajouter `ocd_live_demo` (le désinstaller retire tout).
