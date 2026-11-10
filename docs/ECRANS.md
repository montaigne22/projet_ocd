# Écrans du design validé et leur réalisation

Le design validé est dans [`prototype/design-valide/`](../prototype/design-valide/) (un fichier par
écran). Ce tableau dit, pour chaque écran, où il est fait dans le code et où il en est.

État : ✅ fait et fidèle au design · 🟡 fait avec les écrans standard d'Odoo, à rapprocher du design · ⬜ pas encore fait

## Site des vendeurs : réserver un live

| Écran du design | Où | État |
|---|---|---|
| `Main` Accueil OCD Live | `/ocd`, `ocd_live/views/ocd_booking_templates.xml` (`home`) | ✅ |
| `Jour` Choisir le jour | `/reserver/<mode>`, modèle `booking_day` | ✅ |
| `Heure` Choisir l'heure | `/reserver/<mode>/<jour>`, modèle `booking_hour` (prix selon l'heure) | ✅ |
| `Paquet` Choisir le paquet | `/reserver/<mode>/<jour>/<heure>`, modèle `booking_package` | ✅ |
| `Infos` Informations du vendeur | modèle `booking_infos` | ✅ |
| `Payer` Payer la réservation | `/ocd/payer/<commande>` : formulaire de paiement d'Odoo, tous les fournisseurs configurés | ✅ |
| `Ticket` Ticket de réservation | `/ocd/ticket/<réservation>` | ✅ |
| `Connexion` Retrouver son espace | `/ocd/connexion` (lien ou code WhatsApp) | ✅ |
| `MonEspace` Mon espace vendeur | `/ocd/espace/<jeton>`, `ocd_space_templates.xml` | ✅ |

## Site : annuaire des lives

| Écran du design | Où | État |
|---|---|---|
| `Lives` Lives par pays | `/lives`, `ocd_directory_templates.xml` | ✅ |
| `LivesPays` Lives d'un pays | `/lives/<pays>` | ✅ |
| `Pass` Pass annuaire | `/lives/pass` | ✅ |
| `EnvoyerLien` Envoyer le lien de son live | `/lives/envoyer` | ✅ |
| `EnLigne` Vérification du live | `/lives/statut/<lien>` | ✅ |

## Site : shop et livraisons

| Écran du design | Où | État |
|---|---|---|
| `Vitrine` Boutique d'un vendeur | `/ocd/boutique/<vendeur>`, modèle `ocd_live_shop.boutique` : en live (produit à l'écran mis à jour toutes les 20 s) ou prochain live avec « Me prévenir sur WhatsApp » (`ocd.boutique.alert`), dernier replay, bouton WhatsApp selon le mode de vente, produits avec stock | ✅ |
| `Shop` Shop OCD | pages `/shop` de website_sale | 🟡 |
| `Produit` Fiche produit | pages produit de website_sale | 🟡 |
| `Panier` Panier | panier de website_sale | 🟡 |
| `Livraison` Adresse et livraison | étape adresse de website_sale (+ point de repère de delivery_cameroon / ocd_delivery_togo) | 🟡 |
| `PayerCommande` Payer la commande | paiement de website_sale ; à la porte : `/ocd/colis/<colis>/payer` | 🟡 |
| `Suivi` Suivi de commande | page de la commande du portail, avec le code de livraison | 🟡 |
| `Replay` Revoir un live | `/ocd/boutique/<vendeur>/replay`, modèle `ocd_live_shop.replay` : moments du live (lien à la seconde pour YouTube), bouton « Commander » ou « Écrire » du moment choisi | ✅ |
| `MesProduits` Mes produits | espace vendeur (produits ajoutés vérifiés par l'équipe) | 🟡 |
| `Livrer` Mes colis à livrer | `/ocd/livrer/<jeton>`, modèle `ocd_live_shop.delivery_app` : reversement à venir, onglets « À faire » et « Livrés », une carte par colis (étape, paiement, livreur qui passe, prêt, départ, paiement à la porte, code, problème, reprise) | ✅ |
| `Tournee` Ma tournée de livreur | `/ocd/livrer/<jeton>` pour un livreur OCD, modèle `ocd_live_shop.delivery_tour` : en service ou non, espèces sur soi, étapes numérotées (récupérer puis livrer), appeler le dispatch | ✅ |

## Back-office (équipe OCD)

| Écran du design | Où | État |
|---|---|---|
| `BoShell` En-tête (barre, onglets) | `ocd_live/static/src/backend/navbar.*`, menus `ocd_live_menus.xml` et des autres modules | ✅ |
| `BoDashboard` Tableau de bord | action `ocd_live.dashboard`, `ocd_live/static/src/dashboard/`, modèle `ocd.live.dashboard` (le shop et WhatsApp ajoutent leurs chiffres) | ✅ |
| `BoReservations` Réservations | action `ocd_live.planning`, `static/src/planning/`, modèle `ocd.live.planning` | ✅ |
| `Regie` Régie du live en cours | action `ocd_live_shop.regie`, `ocd_live_shop/static/src/regie/`, modèle `ocd.live.regie` | ✅ |
| `BoVerification` À vérifier | action `ocd_live.verification` (liens, produits, vendeurs), modèle `ocd.live.verification` | ✅ |
| `BoCommandes` Commandes du shop | action `ocd_live_shop.orders`, modèle `ocd.live.orders` | ✅ |
| `BoDispatch` Dispatch | action `ocd_live_shop.dispatch`, modèle `ocd.live.dispatch` | ✅ |
| `BoLivraison` Fiche d'une livraison | vue `stock_picking_view_form_ocd_parcel` | ✅ |
| `BoLivreurs` Livreurs et caisse | action `ocd_live_shop.couriers`, modèle `ocd.live.couriers` | ✅ |
| `BoVendeur` Fiche vendeur | vue `res_partner_view_form_ocd_vendor` (+ ajouts du shop), widget `ocd_choice_cards` | ✅ |
| `BoReversements` Reversements | liste `ocd_payout_view_list` avec `js_class="ocd_payout_list"` | ✅ |
| `BoRecrutement` Recrutement | kanban `hr_applicant_view_kanban_ocd_host` avec `js_class="ocd_host_kanban"` | ✅ |
| `BoParametres` Paramètres | réglages d'Odoo (application OCD Live), présentés en cartes | 🟡 |
| `BoAutomatisations` Automatisations | liste des tâches automatiques OCD Live, avec interrupteur (administrateurs) | 🟡 |
| `BoOutils` Outils Odoo utilisés | dans la documentation, pas dans le système : [`docs/OUTILS_ODOO.md`](OUTILS_ODOO.md) | ✅ |
| `BoWhatsApp` Conversations | écran de `whatsapp_cloud` | 🟡 |

## Écrans d'équipe sur téléphone

| Écran du design | Où | État |
|---|---|---|
| `EquipePlanning`, `EquipeValider`, `EquipeCommandes`, `EquipeVendeurs`, `EquipeFil` | back-office d'Odoo sur téléphone (barre repliée dans le menu) | 🟡 |
