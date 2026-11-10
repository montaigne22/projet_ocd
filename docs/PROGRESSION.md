# Progression du projet OCD Live

Ce fichier est mis à jour à chaque évolution. Le plus récent est en haut.

## Où en est le projet (10 novembre 2026)

| Domaine | État |
|---|---|
| Réservations de lives (créneaux, paquets, crédits, liste d'attente, déplacement, prix selon l'heure) | ✅ fait, testé |
| Paiement : formulaire d'Odoo, tous les fournisseurs configurés par pays, devise par pays | ✅ fait, testé |
| Annuaire des lives (pass, envoi du lien, vérification par créneau, statut) | ✅ fait, testé |
| Espace vendeur sans mot de passe (lien ou code WhatsApp) | ✅ fait, testé |
| Site fidèle au design : réservation, annuaire, espace (téléphone, tablette, ordinateur) | ✅ fait |
| Site : boutique d'un vendeur (`Vitrine`), replay (`Replay`), appli des colis (`Livrer`), tournée du livreur (`Tournee`) | ✅ fait, testé |
| Site : autres pages du shop (shop, produit, panier, livraison, paiement, suivi, mes produits) | 🟡 fonctionnent, à rapprocher du design |
| Shop : un colis par vendeur, code de livraison, dispatch, caisse des livreurs, reversements | ✅ fait, testé |
| Back-office fidèle au design : barre, onglets, tableau de bord, réservations, régie, à vérifier, commandes, dispatch, fiche livraison, livreurs et caisse, fiche vendeur, reversements, recrutement | ✅ fait |
| Outils Odoo utilisés : dans la documentation ([`OUTILS_ODOO.md`](OUTILS_ODOO.md)), pas dans le système | ✅ fait |
| Back-office : paramètres, automatisations, conversations WhatsApp | 🟡 écrans d'Odoo présentés au mieux |
| WhatsApp (messages des lives et des colis) | ✅ fait ; quelques nouveaux messages à brancher (voir plus bas) |
| Recrutement des animatrices (offre sur le site, 5 étapes, embauche) | ✅ fait, testé |
| Togo (villes, quartiers, livraison) | ✅ fait |
| Données de démonstration désinstallables | ✅ fait, testé |
| Traductions françaises de tous les modules | ✅ faites (à compléter à chaque nouvel écran) |

Derniers tests lancés (10 novembre 2026, base neuve, tous les modules OCD sauf la démo) :
**127 tests, aucun échec**.

## Reste à faire, par priorité

1. **Pages du shop sur le site** (en cours) fidèles au design. Faites : `Vitrine`, `Replay`, `Livrer`,
   `Tournee`. Restent : `Produit` (avec le bouton WhatsApp du contact direct : la boutique ouvre
   WhatsApp en attendant), `Shop`, `Panier`, `Livraison`, `PayerCommande`, `Suivi`, `MesProduits`.
2. **Messages WhatsApp à brancher** sur les nouveaux points d'accroche : ticket renvoyé
   (`_ocd_send_ticket`), créneau libéré pour la liste d'attente (`_ocd_send_free_slot`), ouverture du
   créneau de l'annuaire, filtrage par accord WhatsApp du vendeur.
3. **Paramètres** : page à sections comme le design (`BoParametres`), au lieu des réglages d'Odoo en cartes.
4. **Automatisations** : catalogue complet « Quand… alors… » avec détail (`BoAutomatisations`).
5. **Conversations WhatsApp** dans le style du design (`BoWhatsApp`) : écran de `whatsapp_cloud`.
6. Démo : ajouter des colis livrés et des reversements, et deux autres livreurs, pour remplir tous les écrans.

## Points d'attention

- Sur un écran de moins de 1 534 px, Odoo met la discussion (chatter) **sous** les fiches et non à droite.
- Les écrans sur mesure du back-office gardent un bouton vers la liste standard d'Odoo (tri, export).
- Odoo 20 n'a plus Font Awesome : les icônes sont celles d'Odoo (`data-icon`).
- La page « Automatisations » lit les tâches automatiques d'Odoo : elle est réservée aux administrateurs.

## Journal

### 10 novembre 2026 — appli des colis et tournée du livreur fidèles au design
- Vendeur (`Livrer`) : « Bonjour Fatou », reversement à venir, onglets « À faire » et « Livrés », une
  carte par colis : étape, adresse, produits, paiement (payé en ligne ou à encaisser), livreur OCD qui
  passe, et le bouton du moment (c'est prêt, je pars livrer, paiement à la porte, code, problème).
- Livreur OCD (`Tournee`) : en service ou non, espèces sur soi, étapes numérotées (récupérer chez le
  vendeur, puis livrer), dernières livraisons du jour, « Appeler le dispatch ».
- Le message ou l'erreur d'une action s'affiche dans la carte du colis ; « Reprendre la livraison »
  après un problème ; un vendeur qui n'encaisse pas peut montrer le paiement sur le téléphone du client.

### 10 novembre 2026 — boutique d'un vendeur et replay fidèles au design
- Boutique (`/ocd/boutique/<vendeur>`) : vendeur, mode de vente, adresse ; en live (depuis combien de
  temps, sur quelle plateforme, produit à l'écran) ou prochain live ; dernier replay ; bouton WhatsApp
  (OCD Live quand OCD vend, le vendeur sinon) ; produits avec « Plus que N » et « Épuisé ».
- « Me prévenir sur WhatsApp » : `ocd.boutique.alert`, envoyé par une tâche automatique (toutes les
  5 minutes) quand le live commence ; message `ocd_vendeur_en_live` dans `ocd_live_shop_whatsapp`.
- Replay (`/ocd/boutique/<vendeur>/replay`) : moments du live, bouton du bas selon le moment choisi.
- Bouton « Partager » dans l'en-tête des pages (partage du téléphone, ou lien copié) ; « Shop » dans le
  menu du bas.
- Captures : `tools/captures/site-shop.js`.

### 10 novembre 2026 — outils Odoo dans la documentation, shop du site commencé
- La page « Outils Odoo utilisés » quitte le back-office : elle devient `docs/OUTILS_ODOO.md`, avec ce
  que chaque outil fait concrètement pour OCD Live.
- Dépôt GitHub `projet_ocd` en place : tout y est envoyé à chaque évolution.

### 10 novembre 2026 — back-office fidèle au design
- Couleurs et polices dans un seul fichier, partagé par les deux thèmes (site et back-office).
- Barre sombre avec le logo et les sections, onglets de la section dessous, menus nommés comme le design.
- Tableau de bord, planning des réservations, régie en direct, à vérifier, commandes, dispatch, fiche
  d'une livraison, livreurs et caisse, fiche vendeur, reversements, recrutement, outils Odoo utilisés.
- Motifs de refus par type (liens, vendeurs, produits), visites de la boutique pendant le live.
- Traductions françaises de tous les modules.
- Documents de suivi (`docs/`), prototype complet (`prototype/`), outils de traduction et de captures (`tools/`).

### 10 novembre 2026 — site fidèle au design, paiements génériques
- Pages de réservation, annuaire et espace vendeur fidèles au design, responsives.
- Paiement par le formulaire d'Odoo : aucun fournisseur figé, devise selon le pays.
- Prix selon l'heure et la date ; barre du bas toujours en bas de l'écran.
- Module de démonstration désinstallable.

### Avant — modules de base
- Réservations, crédits, annuaire, shop avec colis par vendeur, WhatsApp, Togo, recrutement.
