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
| Site : pages du shop (shop, produit, panier, livraison, paiement, suivi, replay, livrer, tournée) | 🟡 fonctionnent, à rapprocher du design |
| Shop : un colis par vendeur, code de livraison, dispatch, caisse des livreurs, reversements | ✅ fait, testé |
| Back-office fidèle au design : barre, onglets, tableau de bord, réservations, régie, à vérifier, commandes, dispatch, fiche livraison, livreurs et caisse, fiche vendeur, reversements, recrutement, outils | ✅ fait |
| Back-office : paramètres, automatisations, conversations WhatsApp | 🟡 écrans d'Odoo présentés au mieux |
| WhatsApp (messages des lives et des colis) | ✅ fait ; quelques nouveaux messages à brancher (voir plus bas) |
| Recrutement des animatrices (offre sur le site, 5 étapes, embauche) | ✅ fait, testé |
| Togo (villes, quartiers, livraison) | ✅ fait |
| Données de démonstration désinstallables | ✅ fait, testé |
| Traductions françaises de tous les modules | ✅ faites (à compléter à chaque nouvel écran) |

Derniers tests lancés : 99 tests OCD sans échec (ocd_live, ocd_live_shop, ocd_live_whatsapp), puis
les tests ajoutés écran par écran (planning, vérification, régie, dispatch, commandes, livreurs,
recrutement) sans échec.

## Reste à faire, par priorité

1. **Envoyer le dépôt sur GitHub** : le dépôt privé `projet_ocd` doit être créé sur GitHub par le
   propriétaire, avec l'application GitHub de Claude autorisée dessus ; tout est commité en local.
2. **Pages du shop sur le site** fidèles au design (`Shop`, `Vitrine`, `Produit`, `Panier`,
   `Livraison`, `PayerCommande`, `Suivi`, `Replay`, `MesProduits`, `Livrer`, `Tournee`).
3. **Messages WhatsApp à brancher** sur les nouveaux points d'accroche : ticket renvoyé
   (`_ocd_send_ticket`), créneau libéré pour la liste d'attente (`_ocd_send_free_slot`), ouverture du
   créneau de l'annuaire, filtrage par accord WhatsApp du vendeur.
4. **Paramètres** : page à sections comme le design (`BoParametres`), au lieu des réglages d'Odoo en cartes.
5. **Automatisations** : catalogue complet « Quand… alors… » avec détail (`BoAutomatisations`).
6. **Conversations WhatsApp** dans le style du design (`BoWhatsApp`) : écran de `whatsapp_cloud`.
7. Démo : ajouter des colis livrés et des reversements, et deux autres livreurs, pour remplir tous les écrans.

## Points d'attention

- Sur un écran de moins de 1 534 px, Odoo met la discussion (chatter) **sous** les fiches et non à droite.
- Les écrans sur mesure du back-office gardent un bouton vers la liste standard d'Odoo (tri, export).
- Odoo 20 n'a plus Font Awesome : les icônes sont celles d'Odoo (`data-icon`).
- La page « Automatisations » lit les tâches automatiques d'Odoo : elle est réservée aux administrateurs.

## Journal

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
