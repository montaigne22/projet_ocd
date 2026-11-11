# Progression du projet OCD Live

Ce fichier est mis à jour à chaque évolution. Le plus récent est en haut.

## Où en est le projet (11 novembre 2026)

| Domaine | État |
|---|---|
| Réservations de lives (créneaux, paquets, crédits, liste d'attente, déplacement, prix selon l'heure) | ✅ fait, testé |
| Paiement : formulaire d'Odoo, tous les fournisseurs configurés par pays, devise par pays | ✅ fait, testé |
| Annuaire des lives (pass, envoi du lien, vérification par créneau, statut) | ✅ fait, testé |
| Espace vendeur sans mot de passe (lien ou code WhatsApp) | ✅ fait, testé |
| Site fidèle au design : réservation, annuaire, espace (téléphone, tablette, ordinateur) | ✅ fait |
| Adresse du site (`/`) = accueil d'OCD Live, site en français, logo et pied de page d'OCD sur les pages d'Odoo | ✅ fait, testé |
| Thème du site « OCD Live » (`theme_ocd`) dans le choix des thèmes d'Odoo | ✅ fait, testé |
| Site : toutes les pages du shop fidèles au design (shop, produit, panier, livraison, paiement, suivi, boutique, replay, mes produits, mes colis, tournée) | ✅ fait, testé |
| Frais de livraison selon le vendeur : un prix par colis, de la ville du vendeur au quartier du client | ✅ fait, testé |
| Shop : un colis par vendeur, code de livraison, dispatch, caisse des livreurs, reversements | ✅ fait, testé |
| Back-office fidèle au design : barre, onglets, tableau de bord, réservations, régie, à vérifier, commandes, dispatch, fiche livraison, livreurs et caisse, fiche vendeur, reversements, recrutement | ✅ fait |
| Outils Odoo utilisés : dans la documentation ([`OUTILS_ODOO.md`](OUTILS_ODOO.md)), pas dans le système | ✅ fait |
| Back-office : paramètres à sections, catalogue des automatisations, conversations WhatsApp, fidèles au design | ✅ fait, testé |
| WhatsApp : tous les messages des lives, de l'annuaire et des colis, un seul accord, messages demandés toujours envoyés | ✅ fait, testé |
| Aucune mention d'Odoo pour l'équipe, les vendeurs et les clients (site, back-office, erreurs, e-mails) | ✅ fait, testé |
| Recrutement des animatrices (offre sur le site, 5 étapes, embauche) | ✅ fait, testé |
| Togo (villes, quartiers, livraison) | ✅ fait |
| Données de démonstration désinstallables, qui remplissent tous les écrans (photos, variantes, stock, colis à chaque étape, reversements) | ✅ fait, testé |
| Traductions françaises de tous les modules, descriptions longues comprises | ✅ faites (à compléter à chaque nouvel écran) |

Derniers tests lancés (11 novembre 2026, base neuve, tous les modules OCD sauf la démo, avec
`ocd_debranding`) : **190 tests, aucun échec** (et, sur une base neuve avec la démo, 5 tests sans échec :
la démo remplit les écrans, conversations WhatsApp comprises, puis se désinstalle sans rien laisser).

## Reste à faire, par priorité

1. **Tarifs à saisir par l'équipe avant l'ouverture**, pas à pas dans [`LIVRAISONS.md`](LIVRAISONS.md)
   (OCD Live › Livraisons › Tarifs de livraison) :
   livreurs OCD par ville, agences vers les autres villes et pays, bornes des prix des vendeurs, part
   d'OCD sur les livraisons des vendeurs, ville du stock. Les modes de livraison sans prix ont donné des
   tarifs archivés : les compléter puis les activer. Sans tarif, le shop refuse l'adresse (jamais de
   livraison à un prix inconnu).
2. **WhatsApp chez Meta** (équipe) : connecter le numéro d'OCD Live (WhatsApp › Comptes), puis soumettre
   les modèles depuis Odoo (WhatsApp › Messages automatiques) : tant qu'un modèle n'est pas approuvé, son
   message ne part pas (les Paramètres, section WhatsApp, et les Automatisations le signalent). Les
   réponses rapides de l'équipe se créent dans les conversations (`::livreur`, `::retard`…).
3. **Mise en production** : `list_db = False` dans `odoo.conf` (pas de gestion des bases sur la page
   de connexion), un sous-domaine pour l'équipe si une adresse à la marque est voulue (les adresses du
   back-office gardent `/odoo/`, voir [`DECISIONS.md`](DECISIONS.md)).

## Points d'attention

- Sur un écran de moins de 1 534 px, Odoo met la discussion (chatter) **sous** les fiches et non à droite.
- Les écrans sur mesure du back-office gardent un bouton vers la liste standard d'Odoo (tri, export).
- Odoo 20 n'a plus Font Awesome : les icônes sont celles d'Odoo (`data-icon`).
- Les pages « Paramètres » et « Automatisations » sont pour les responsables d'OCD Live : ils changent les
  réglages et les interrupteurs sans être administrateurs d'Odoo (rien d'autre n'est écrit).
- Le module `disable_odoo_online` de l'OCA (dépôt server-brand, branche 20.0) doit être dans le chemin
  des modules : `ocd_debranding` en dépend. C'est le seul module qui n'est pas dans le dépôt.
- La confirmation d'une commande envoie un PDF : le serveur a besoin du moteur PDF d'Odoo
  (`wkhtmltopdf`), sinon la commande reste « en attente du paiement ».
- Odoo publie au départ sa « Livraison standard » (gratuite, partout) : l'équipe ne publie que les
  modes de livraison d'OCD Live, sinon elle passe avant elles.

## Journal

### 11 novembre 2026 — thème du site « OCD Live », plus de page 404 après « Confirmer »
- **Thème `theme_ocd`**, proposé dans Site Web › Configuration › Paramètres › Choisir un thème (et dans
  l'éditeur, Thème › Changer de thème) : polices Bricolage Grotesque (titres) et Figtree (textes),
  palette orange / encre / sable, boutons arrondis, champs aux grands coins, en-tête blanc (logo, menu,
  bouton « Réserver un live », sans barre de recherche ni téléphone), pied de page sombre aux liens
  orange. Les pages d'OCD Live ne changent pas (leur propre cadre). Captures `site-*-o-*` et
  `backoffice-16-choix-du-theme.png`.
- Bouton de l'en-tête des pages d'Odoo : « Réserver un live » (vers `/ocd`) au lieu de « Contactez-nous ».
- **`/reserver/confirmer` en 404 sur staging** : cette adresse ne reçoit que le formulaire ; ouverte
  comme une page (page rechargée par le téléphone, retour, onglet rouvert), Odoo la prenait pour un mode
  « confirmer » inconnu. Maintenant : ouverte sans formulaire, elle ramène au début de la réservation ;
  après une erreur dans le formulaire, la page prend l'adresse de son étape (un rechargement réaffiche
  l'étape) ; une heure devenue impossible (prise, trop proche) ramène au choix de l'heure avec le message
  « Cette heure n'est plus disponible : choisis-en une autre ». Même chose pour `/reserver/attente`.
- Test corrigé : le jeton de l'espace vendeur « modifié » pouvait retomber sur le vrai (1 fois sur 64).

### 11 novembre 2026 — le site est celui d'OCD Live dès l'installation
Constat sur un serveur où tout était installé : `/` montrait la page vide d'Odoo (« Your Logo »,
« Bienvenue sur votre site », pied de page d'exemple, +1 555-555-5556) et le menu était en anglais.
- `/` ouvre l'accueil d'OCD Live (réglage « URL de la page d'accueil » du site : `/ocd`).
- Le site passe en français quand le français est installé ; logo rond et nom d'OCD Live.
- Les menus que Odoo avait copiés pour le site en anglais (« Home », « Shop », « Jobs ») reçoivent leur
  traduction (« Accueil », « Boutique », « Postes ») ; un menu renommé par l'équipe est laissé tel quel.
- Pages d'Odoo (recrutement, connexion, portail, contact) : pied de page d'OCD Live (liens, téléphone,
  e-mail et ville de la société), téléphone de la société dans l'en-tête, côté de la page des offres
  d'emploi avec OCD Live, « Rechercher... » en français.
- Fait à l'installation de `ocd_live` et, sur un serveur déjà installé, à la mise à jour de `ocd_live`
  (version 20.0.1.1.0). Seul ce qui est encore comme Odoo l'installe est changé.

### 11 novembre 2026 — branche fusionnée dans main, modules complémentaires dans le dépôt
- `whatsapp_cloud`, `whatsapp_cloud_sale`, `payment_campay` et `delivery_cameroon` sont dans le dépôt
  (plus de « dépendance absente » dans les Applications). Seul `disable_odoo_online` (OCA) s'ajoute à
  part.
- Le travail de la branche `claude/serene-johnson-x7ucgf` (boutique, replay, appli de livraison, toutes les
  pages du shop, frais de livraison, démo, paramètres, automatisations, conversations WhatsApp, sans la
  marque Odoo) est dans `main`.

### 11 novembre 2026 — paramètres, automatisations, conversations WhatsApp, sans la marque Odoo
- **WhatsApp** : un seul accord (la case d'OCD Live et l'accord WhatsApp, STOP et START, restent
  identiques) ; les messages demandés par le contact (code, lien, ticket, alerte) partent toujours, les
  autres jamais après un refus. Avant, en production, `whatsapp_cloud` aurait bloqué tous les messages
  des vendeurs (accord jamais transmis). Nouveaux messages : ticket renvoyé, créneau libéré pour la liste
  d'attente, ouverture de l'annuaire, lien reçu hors des fenêtres. « Commande expédiée » du shop plus
  envoyé pour les colis d'OCD (il arrivait après « colis livré »), note demandée une fois par commande.
- **Paramètres** (`BoParametres`) : 5 sections déclarées par les modules, plus de 50 réglages avec leurs
  contrôles (nombres, heures, prix mini ≤ maxi, derniers lives avant minuit, au moins un jour ouvert),
  barre « enregistré / non enregistré », question avant de quitter, avertissement quand une protection
  est coupée ; un moyen de paiement publié ou non par case ; les responsables d'OCD Live les changent sans
  être administrateurs.
- **Automatisations** (`BoAutomatisations`) : catalogue de 30 automatisations réelles (règles que l'équipe
  met en pause, heures fixes, code de l'argent et des preuves toujours actif, tâches techniques), avec
  leurs exécutions des 7 derniers jours et la dernière ; un interrupteur coupe vraiment l'action (message
  à l'équipe, modèle WhatsApp, tâche planifiée).
- **Conversations WhatsApp** (`BoWhatsApp`) : sur celles de `whatsapp_cloud` (droits des agents,
  envoi, fenêtre de 24 h) ; messages automatiques, réponses, notes internes, réponses rapides, modèles
  hors des 24 h, contact avec sa commande et ses colis ou son prochain live, canaux de l'équipe, codes de
  livraison masqués ; nouveaux messages par le bus et toutes les 20 secondes. L'équipe d'OCD Live est
  agente WhatsApp. La démo a 5 conversations (sur un compte archivé : rien ne part chez Meta).
- **Sans la marque Odoo** (`ocd_debranding`, avec `disable_odoo_online` de l'OCA) : site, connexion,
  portail, onglet du back-office, menu de l'utilisateur, fenêtres d'erreur, e-mails, robot « OCD Live » ;
  aucun lien vers les écrans d'Odoo dans les écrans d'OCD.
- Traductions : tous les textes, et les longues descriptions des modules.
- Correction : dans un groupe de champs des Paramètres, la saisie du premier champ allait dans le dernier
  (variable de gabarit partagée) ; chaque champ porte maintenant sa clé.

### 11 novembre 2026 — démo qui remplit tous les écrans
- Photos (illustrations) des 8 produits, robe en 2 couleurs et 4 tailles, stock par variante (« Plus que
  3 », taille épuisée, savon épuisé), commandes chiffrées colis par colis.
- Colis à chaque étape : à préparer, prêt, en route, livrés (payé sur le téléphone, espèces chez Junior),
  en problème (client absent), en retard (vendeuse relancée, dispatch alerté).
- Factures des vendeuses et reversements à vérifier ; deux autres livreurs (dont un en repos), trois
  clientes et clients de plus.
- Le paiement à la livraison est publié par la démo : une commande du shop se paie de bout en bout
  (captures `8b` et `8c` : deux vendeuses, un prix par colis, puis le paiement). Remis comme avant à la
  désinstallation.
- Toujours entièrement désinstallable (vérifié par une vraie désinstallation) : le stock est posé sans
  mouvement, les colis livrés ne valident pas le transfert, factures et reversements sont retirés.
- Correction trouvée grâce à la démo : un paiement sur le téléphone du client (ou un Mobile Money
  déclaré) chez un vendeur qui livre était retenu sur son reversement comme s'il avait gardé l'argent ;
  seules les espèces gardées par le vendeur sont désormais retenues.

### 11 novembre 2026 — guide des livraisons
- [`docs/LIVRAISONS.md`](LIVRAISONS.md) : comment le prix d'un colis est choisi, exemples, ce que voient
  le client et le vendeur, l'argent, la mise en route pas à pas, les questions fréquentes, le code.

### 11 novembre 2026 — frais de livraison selon le vendeur
- **Un prix par colis** (un colis par vendeur), de la ville d'où part le colis au quartier, à la ville
  ou au pays du client ; le tarif le plus précis l'emporte. Le total de la livraison est la somme des
  colis, détaillée sur les pages Livraison et Payer.
- **Tarifs des vendeurs qui livrent** : le vendeur les fixe dans son espace (« Mes prix de livraison »),
  entre les bornes de l'équipe ; ailleurs dans ses zones, il livre au prix du livreur OCD de sa ville ;
  hors zones, un livreur OCD ou une agence prend le relais si l'équipe l'autorise.
- **Tarifs d'OCD Live** : livreurs OCD dans une ville, agences vers les autres villes et vers un autre
  pays (jamais d'agence dans la même ville, jamais de paiement à la porte par agence ou vers un autre
  pays). Créés au départ depuis les modes de livraison par ville (actifs seulement s'ils avaient un
  prix).
- **Une seule livraison d'Odoo « Livraison OCD Live »** qui additionne les colis et **refuse avant le
  paiement** une adresse qu'un colis ne peut pas atteindre, avec la raison et un bouton pour retirer les
  produits de ce vendeur. Le client choisit son pays de livraison.
- Chaque colis reçoit **son prix exact** (fin du partage égal) et le tarif décide qui livre ; le vendeur
  touche sa livraison moins la part d'OCD (réglable, 0 % par défaut). Colis par agence : le livreur le
  porte à l'agence, l'équipe valide quand le client l'a retiré.

### 10 novembre 2026 — toutes les pages du shop fidèles au design
- Shop, fiche produit, panier, livraison, paiement : les pages d'Odoo gardent leur logique (prix des
  listes de prix, panier, modes de livraison, formulaire de paiement, confirmation) ; seul l'affichage
  suit le design, et les formulaires appellent les mêmes méthodes d'Odoo.
- Fiche produit : variantes avec leur prix et leur stock (valeurs épuisées barrées), quantité ; contact
  direct : pas de panier (bloqué aussi côté serveur), WhatsApp avec le choix et le lien du produit.
- Livraison sans e-mail : nom, WhatsApp, ville, quartier, point de repère ; prix de la livraison en direct.
- Suivi de la commande (`/ocd/suivi/…`) : un bloc par colis avec ses étapes, le livreur, le code ; note de
  1 à 5 et demande de retour (30 jours, réglable) une fois livré.
- Mes produits : le vendeur ajoute un produit avec une photo (vérifié par l'équipe) et règle son stock.
- Choix robustes : pas de remise sans paiement encaissé, reprise de livraison tracée, catégorie du
  vendeur enregistrée sur le produit (filtre du shop sans lire les contacts).

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
