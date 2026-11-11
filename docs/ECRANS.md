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
| `Shop` Shop OCD | `/shop` d'Odoo, gabarit `ocd_live_shop.shop` : recherche, pays de livraison, catégories des vendeurs, produits avec vendeur, mode de vente et stock | ✅ |
| `Produit` Fiche produit | `/shop/<produit>` d'Odoo, gabarit `ocd_live_shop.product` : variantes (couleur, taille) avec stock et prix, quantité, vendeur ; contact direct : WhatsApp avec le choix | ✅ |
| `Panier` Panier | `/shop/cart` d'Odoo, gabarit `ocd_live_shop.cart` : quantités (`/ocd/panier/ligne`), total | ✅ |
| `Livraison` Adresse et livraison | `/shop/checkout` d'Odoo, gabarit `ocd_live_shop.delivery`, envoi `/ocd/livraison` (formulaires d'adresse d'Odoo, sans e-mail) : ville, quartier, repère, mode de livraison et prix en direct | ✅ |
| `PayerCommande` Payer la commande | `/shop/payment` d'Odoo, gabarit `ocd_live_shop.payment` : formulaire de paiement d'Odoo (Mobile Money, paiement à la livraison…) ; à la porte : `/ocd/colis/<colis>/payer` | ✅ |
| `Suivi` Suivi de commande | `/ocd/suivi/<commande>?access_token=` (après la confirmation d'Odoo) : un bloc par colis, étapes, livreur, code, note, demande de retour | ✅ |
| `Replay` Revoir un live | `/ocd/boutique/<vendeur>/replay`, modèle `ocd_live_shop.replay` : moments du live (lien à la seconde pour YouTube), bouton « Commander » ou « Écrire » du moment choisi | ✅ |
| `MesProduits` Mes produits | `/ocd/espace/moi/produits` : ajout avec photo (vérifié par l'équipe), stock de chaque produit, partager sa boutique | ✅ |
| (hors design) Mes prix de livraison | `/ocd/espace/moi/livraison` : prix par ville ou quartiers, dans les bornes de l'équipe ; prix d'OCD Live depuis sa ville | ✅ |
| `Livrer` Mes colis à livrer | `/ocd/livrer/<jeton>`, modèle `ocd_live_shop.delivery_app` : reversement à venir, onglets « À faire » et « Livrés », une carte par colis (étape, paiement, livreur qui passe, prêt, départ, paiement à la porte, code, problème, reprise) | ✅ |
| `Tournee` Ma tournée de livreur | `/ocd/livrer/<jeton>` pour un livreur OCD, modèle `ocd_live_shop.delivery_tour` : en service ou non, espèces sur soi, étapes numérotées (récupérer puis livrer), appeler le dispatch | ✅ |

## Site : pages d'Odoo gardées

Le design n'a pas d'écran pour ces pages : elles prennent l'allure d'OCD Live par le thème du site.

| Page | Où | État |
|---|---|---|
| Accueil du site `/` | réglage du site (URL de la page d'accueil = `/ocd`), `ocd_live/models/website.py` | ✅ |
| Recrutement, contact, connexion, portail, pages de l'éditeur | thème `theme_ocd` ; pied de page et bouton « Réserver un live » : `ocd_live/views/website_templates.xml` | ✅ |

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
| `BoParametres` Paramètres | action `ocd_live.settings`, modèle `ocd.live.settings` : sections déclarées par chaque module (lives, annuaire, shop, paiements, WhatsApp), barre « enregistré / non enregistré », contrôles entre réglages, question avant de quitter | ✅ |
| `BoAutomatisations` Automatisations | action `ocd_live.automations`, modèle `ocd.automation` (catalogue en données, un par module) : règle modifiable, heure fixe ou code, exécutions sur 7 jours, interrupteur lu par le code | ✅ |
| `BoOutils` Outils Odoo utilisés | dans la documentation, pas dans le système : [`docs/OUTILS_ODOO.md`](OUTILS_ODOO.md) | ✅ |
| `BoWhatsApp` Conversations | action `ocd_live_whatsapp.inbox`, modèle `ocd.whatsapp.inbox` sur les conversations de `whatsapp_cloud` : liste (toutes, en attente), messages automatiques, réponses, notes internes, fenêtre de 24 h, réponses rapides, modèles, contact (commande et colis, live), canaux de l'équipe | ✅ |

## Écrans d'équipe sur téléphone

| Écran du design | Où | État |
|---|---|---|
| `EquipePlanning`, `EquipeValider`, `EquipeCommandes`, `EquipeVendeurs`, `EquipeFil` | back-office d'Odoo sur téléphone (barre repliée dans le menu) | 🟡 |
