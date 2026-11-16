# Plan de la page « Mes produits », des magasins et du stock par magasin

Page du vendeur `/ocd/espace/moi/produits` (design `MesProduits`) et ce qui s'y rattache. Plan
retenu le 16 novembre 2026, après une relecture du code : d'abord les corrections, puis les ajouts,
du plus rapide au plus long. Les durées sont des estimations, tests compris. Les décisions prises
et les réglages des administrateurs sont en bas ; chaque décision rejoindra `DECISIONS.md` quand ce
qu'elle règle sera fait.

## Étape 0 : corrections, avant tout le reste (~1,5 semaine)

| # | Correction | Le problème aujourd'hui | Ce qu'on fait | Effort |
|---|---|---|---|---|
| 0.1 | **Boutons − / + du stock** | La page affiche le stock disponible (stock moins ce qui est réservé), mais le bouton l'enregistre comme stock total : avec 5 en stock dont 2 réservés, la page montre 3, « + » pose 4 et la page montre 2. Le chiffre envoyé est celui de l'affichage : une vente arrivée entre-temps est effacée. | Le bouton envoie +1 ou −1, appliqué au stock réel au moment du clic ; prévu pour recevoir le magasin (S.2) | ~½ jour |
| 0.2 | **Photo perdue en cas d'erreur** | Nom ou prix manquant : la page se recharge et le vendeur doit reprendre la photo | Nom et prix vérifiés dans le téléphone avant l'envoi ; si le serveur refuse quand même, la photo reçue est gardée pour le nouvel essai | ~1 jour |
| 0.3 | **Double envoi** | Sur un réseau lent, un second appui crée deux produits | Bouton désactivé (« Envoi… ») et jeton unique par formulaire, vérifié par le serveur | ~½ jour |
| 0.4 | **Photo trop lourde** | Envoyée telle quelle (3 à 8 Mo), alors que le serveur la réduit de toute façon | Photo réduite dans le téléphone avant l'envoi (~300 Ko) : plus rapide, moins de forfait | ~1 jour |
| 0.5 | **Prix mal lu** | Tout ce qui n'est pas un chiffre est retiré : « 2500,50 » devient 250 050, « 3000-5000 » devient 30 005 000 | Ces saisies sont refusées avec un message clair | ~½ jour |
| 0.6 | **Appareil photo ou galerie** | La plupart des téléphones Android ouvrent seulement l'appareil photo (`capture="environment"`) | Les deux : « Ajouter une photo », le téléphone propose l'appareil photo ou la galerie ; nouvelle raison de refus « Photo qui n'est pas la tienne » | ~½ jour |
| 0.7 | **Motif du refus, corriger et renvoyer** | La décision de l'équipe dit qu'un refus envoie un motif au vendeur (`DECISIONS.md:140`), mais pour un produit le motif reste en note interne (`product_template.py:61`) : le vendeur voit « Refusé » sans savoir pourquoi, et ne peut rien corriger | Le message du motif s'affiche sous le produit ; le vendeur corrige et le renvoie à la vérification | ~2 jours |

Dès le début de l'étape 0 : écrire et soumettre à Meta les modèles WhatsApp du plan (voir les
décisions), car leur approbation ne dépend pas de nous.

## Étape 1 : rapide, avec ce qui existe déjà (~2 semaines)

| # | Ajout | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| 1.1 | **Les chiffres déjà comptés** | Sous chaque produit : « 12 personnes t'ont écrit sur WhatsApp », et sur un produit épuisé « 5 clients attendent son retour » | Clics WhatsApp de la boutique (`ocd_wa_clicks`, vus aujourd'hui seulement par l'équipe), demandes « Préviens-moi » (`ocd.stock.alert`) | ~1 jour |
| 1.2 | **Voir comme un client** | Lien vers la fiche du produit dans la boutique, quand il est en vente | Fiche produit | ~½ jour |
| 1.3 | **Partager un produit** | Photo et lien d'un produit précis, prêts pour le statut WhatsApp | Bouton « Partager ma boutique » (`ocd_live/static/src/interactions/share.js`) | ~1 jour |
| 1.4 | **Filtrer par état** | « À vérifier », « Refusé », « Épuisé », « En vente », quand le catalogue grandit | États déjà calculés par la page | ~½ jour |
| 1.5 | **Dupliquer un produit** | Le même modèle dans un autre tissu : la copie part à la vérification | Ajout d'un produit | ~1 jour |
| 1.6 | **Ordre de la boutique** | Monter un produit, en mettre un en avant | Ordre des produits de la boutique (`website_sequence`) | ~1 jour |
| 1.7 | **Catalogue pour le statut WhatsApp** | Des images prêtes à poster (produits, prix, QR de la boutique), téléchargées d'un geste ; fait avec 1.3 | Image d'annonce du live (`ocd_live/announce_image.py`), QR code (`ocd_live/tools.py`) | 3 à 4 jours |

## Étape 2 : gérer ses produits (~2 semaines)

| # | Ajout | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| 2.1 | **Modifier** | Nouveau nom ou nouvelle photo : vérifiés par l'équipe, l'ancienne version reste en vente en attendant. Prix : sans vérification, mais un grand écart se confirme (« Tu passes de 15 000 F à 1 500 F, c'est bien ça ? ») et l'équipe voit l'historique des prix. Stock : jamais vérifié. Les photos de couleur suivent la même règle (aujourd'hui publiées sans vérification) | Formulaire d'ajout, écran « À vérifier » | 4 à 5 jours, plus ~½ jour pour les photos de couleur |
| 2.2 | **Retirer** | Ne plus montrer un produit, et pouvoir le remettre ; jamais supprimé, les commandes passées le gardent | Produits masqués (`is_published`) | ~½ jour |
| 2.4 | **WhatsApp accepté ou refusé** | « Ton produit Robe wax est en vente » ou « … est refusé : photo floue », avec le lien de la page | Messages WhatsApp aux vendeurs | 1 à 2 jours, plus l'approbation des modèles par Meta |
| 2.5 | **Stock par taille et par couleur** | Les − / + pour chaque variante (aujourd'hui seulement les produits sans variantes) ; fait avec S.2, en un seul écran de stock | Réglage du stock (`_ocd_set_stock`), photos des couleurs | Compté dans S.2 |
| 2.6 | **Plusieurs photos** | Ajouter, retirer et ordonner les photos d'un produit ; une nouvelle photo est vérifiée comme en 2.1 | Galerie de la fiche produit (`product_template_image_ids`) | 2 à 3 jours |

## Étape 3 : vendre plus et suivre (4 à 5 semaines)

| # | Ajout | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| 3.1 | **Prix promo** | Prix barré et nouveau prix, jusqu'à une date ; affiché dans la boutique, la fiche et le panier | Prix barré du site d'Odoo, à confirmer sur la version utilisée | ~1 semaine |
| 3.2 | **Préparer son prochain live** | Cocher les produits à montrer : la régie les a sous la main | Produits montrés pendant un live (`_ocd_show_product`), aujourd'hui choisis seulement par l'équipe | 3 à 4 jours |
| 3.3 | **Ventes par produit** | Pièces vendues, dernière vente | Commandes ; à faire avec le chantier 3 « Statistiques du vendeur » de la feuille de route | 2 à 3 jours |
| 3.4 | **Alerte de stock bas** | WhatsApp au vendeur quand il reste peu de pièces (2 par défaut) | Messages WhatsApp aux vendeurs, stock | 1 à 2 jours, plus l'approbation du modèle par Meta |
| 3.5 | **Tailles et couleurs dès la création** | Le vendeur choisit les tailles et les couleurs en ajoutant le produit, au lieu de l'équipe | Attributs et variantes d'Odoo, photos des couleurs | 1 à 2 semaines |

## Magasins du vendeur (~2,5 semaines)

Le client sait où se trouvent les magasins du vendeur ; le vendeur les enregistre et les règle dans
son espace ; l'équipe les voit dans le back-office.

Un magasin est une fiche légère du vendeur : nom, ville et quartier (les listes déjà utilisées pour
la livraison), repère (« en face de la pharmacie »), position, photo de la devanture, téléphone,
horaires par jour, « fermé jusqu'au… ». Ce ne sont pas des entrepôts d'Odoo (voir le stock par
magasin). Module : `ocd_live_shop`, qui a déjà la boutique et les quartiers.

En ajoutant un lieu, le vendeur choisit **« Un magasin ouvert au public »** ou **« Je vends depuis
chez moi »**. Chez lui, les clients voient seulement le quartier, « Sur rendez-vous » et le bouton
WhatsApp : ni position, ni repère, ni photo, ni itinéraire, et pas de retrait. L'équipe voit
toujours l'adresse complète (le livreur vient y chercher les colis).

| # | Ajout | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| M.1 | **Mes magasins** (espace vendeur) | Ajouter, modifier, retirer un lieu (magasin ou domicile) ; position prise par le bouton « Je suis dans mon magasin » (position du téléphone) ; horaires par jour ; fermé pour un temps | Espace vendeur, villes et quartiers (`res.city`, `res.city.district`), repère (`delivery_landmark`) | 3 à 4 jours |
| M.2 | **Nos magasins** (boutique) | Pour chaque magasin : quartier et repère, photo, horaires, « Ouvert · ferme à 19 h » ou « Fermé · ouvre demain à 8 h » (à l'heure du magasin, même pour un client à l'étranger), boutons « Itinéraire », « Appeler », « WhatsApp ». Sous le nom du vendeur : « 2 magasins à Douala » | Boutique, fuseau horaire du vendeur, lien Google Maps déjà utilisé par WhatsApp | ~2 jours |
| M.3 | **Fiche produit** | « Aussi en magasin : Akwa, Bonapriso », vers les magasins de la boutique ; devient la disponibilité par magasin avec S.3 | Fiche produit | ~½ jour |
| M.4 | **Back-office** | Onglet « Magasins » sur la fiche du vendeur ; menu avec tous les magasins (filtres par ville, vendeur, état) ; l'équipe peut les saisir pour un vendeur ; lien vers la carte | Fiche vendeur | ~1 jour |
| M.5 | **Vérification** | Un magasin est vérifié avant d'être montré : photo de la devanture (enseigne visible) et position prise sur place. Seuls un changement d'adresse, de position ou de photo repassent à la vérification ; horaires, téléphone et « fermé jusqu'au… » changent tout de suite. Un refus envoie son motif | Écran « À vérifier », raisons de refus | 1 à 2 jours |
| M.6 | **Visites grâce à OCD** | « 18 personnes ont demandé l'itinéraire de ton magasin cette semaine » : appuis sur Itinéraire, Appeler et WhatsApp comptés par magasin ; fait avec M.2 | Même principe que les clics WhatsApp (1.1) | ~1 jour |
| M.7 | **Affiche QR du magasin** | Affiche ou autocollant à imprimer (« Commandez aussi en ligne, livré chez vous ») avec le QR de la boutique ; étiquettes de prix avec le QR de chaque produit | Image d'annonce du live, QR code | ~2 jours |

## Stock par magasin (3 à 4 semaines)

« Disponible à Akwa, épuisé à Bonapriso ». Un **emplacement de stock par magasin**, rangé dans
l'entrepôt où est déjà tout le stock des vendeurs, et non un entrepôt par magasin : un entrepôt
crée chacun ses emplacements, types d'opérations, routes et numérotations, et la disponibilité du
site d'Odoo se calcule sur l'entrepôt du site : avec un entrepôt par magasin, les produits des
autres magasins paraîtraient épuisés. Avec des emplacements, le site compte toujours le total, et
chaque magasin a le sien.

Le stock par magasin n'apparaît qu'**à partir de 2 lieux** : un vendeur qui n'en a qu'un ne voit rien
de nouveau. Les vendeurs dont les produits sont dans le stock d'OCD ne sont pas concernés.

| # | Ajout | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| S.1 | **Un emplacement par lieu** | Créé avec le lieu ; le stock d'aujourd'hui va au premier lieu du vendeur | Entrepôt actuel, réglage du stock (`_ocd_set_stock`) | ~1 jour |
| S.2 | **Stock par magasin dans « Mes produits »** | Choisir le magasin, puis les − / + ; avec les tailles et les couleurs (2.5) ; « J'envoie 3 robes à Bonapriso » entre deux magasins, tracé | Écran du stock | 4 à 5 jours, 2.5 compris |
| S.3 | **Disponibilité pour le client** | « Disponible » ou « Épuisé » par magasin, et « Plus que 2 » comme sur les cartes, sans le nombre exact de chaque magasin ; sur la fiche produit et les magasins de la boutique ; « Préviens-moi » dit où le produit est revenu | Fiche produit, « Plus que N » des cartes, `ocd.stock.alert` | 1 à 2 jours |
| S.4 | **Le magasin qui sert une commande** | Celui de la ville du client qui a toute la commande, sinon le magasin de départ des colis (A.4), sinon un colis par magasin, chacun avec son code. Le livreur va chercher le colis là, la livraison est comptée depuis là ; un retour revient au magasin d'où il est parti | Colis par vendeur (`stock_move.py`, `_key_assign_picking`), départ des colis (A.4), code de livraison | 1 à 1,5 semaine |
| S.5 | **Retrait dans un magasin** | Le client ne choisit qu'un magasin qui a le produit | Retrait en magasin (A.1) | ~1 jour de plus sur A.1 |
| S.6 | **Back-office** | Stock par magasin sur la fiche produit et la fiche vendeur | Stock par emplacement d'Odoo | ~1 jour |

## Autour des magasins et de la boutique (7 à 8 semaines)

| # | Ajout | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| A.1 | **Retrait en magasin** | Le client choisit « Je passe le récupérer » : pas de frais de livraison. Il paie comme à la porte : en ligne, sur son téléphone au comptoir (Mobile Money, chez tous les vendeurs), ou en espèces seulement chez les vendeurs qui encaissent déjà à la porte (commission retenue sur le reversement suivant). Pas de remise sans paiement : le code n'est accepté qu'une fois l'argent encaissé. Pas de retrait chez un vendeur qui vend depuis chez lui. Client qui ne vient pas : rappel WhatsApp la veille de la fin du délai, puis colis annulé et pièces rendues au stock du magasin, avec un avoir s'il a payé en ligne, comme un colis retourné après des échecs de livraison | Paiement à la porte et réglage `ocd_vendor_collects` (`DECISIONS.md:150-152`), code de livraison, reversements, magasins (M.1) | 1 à 2 semaines |
| A.2 | **Le bot WhatsApp donne les magasins** | Sur le numéro d'OCD, « Où êtes-vous ? » reçoit les magasins du vendeur de la commande ou du produit en question : adresse, horaires, position à ouvrir dans les cartes. Le bouton WhatsApp de la boutique, lui, mène au numéro du vendeur : le bot ne voit pas ces conversations | Envoi des magasins et des positions du bot (`whatsapp_cloud_sale`, `_whatsapp_send_location`), aujourd'hui pour les entrepôts d'OCD | 2 à 3 jours |
| A.3 | **Vendeurs près de chez moi** | Filtre par ville et quartier dans le shop et l'annuaire ; du plus proche au plus loin si le client partage sa position | Magasins (M.1), villes et quartiers | ~1 semaine |
| A.4 | **Point de départ des colis** | Le vendeur choisit le magasin d'où partent ses colis : le livreur vient l'y chercher, le prix de la livraison part de là | Départ des colis (`_ocd_origin`, aujourd'hui la ville du vendeur), tournées des livreurs | ~2 jours |
| A.5 | **Mode vacances** | « De retour le 2 janvier » sur la boutique : produits visibles, commandes en pause, « Préviens-moi à son retour » | « Préviens-moi » de la boutique (`ocd.boutique.alert`) | ~2 jours ; ne dépend pas des magasins, peut se faire tôt |
| A.6 | **Magasins points relais** | Les vendeurs qui le veulent gardent les colis d'autres vendeurs | Magasins (M.1) | Avec le chantier 10 (Points relais) de la feuille de route |
| A.7 | **Mettre de côté pour essayer** | Le client réserve une pièce dans un magasin pour venir l'essayer ; le vendeur est prévenu et peut refuser ; la pièce est libérée seule après le délai. Garde-fous : 24 h, une réservation active par client chez un vendeur, plus de réservation après deux absences | Stock par magasin (S), magasins (M.1) | ~1 semaine, après S et A.1 |
| A.8 | **Nouveautés aux abonnés** | Un message groupé : « Cette semaine chez Awa : 3 nouveautés », seulement à ceux qui suivent le vendeur ; une fois par mois, chaque semaine avec OCD Business | « Suivre un vendeur » (chantier 1 de la feuille de route), modèle WhatsApp *Marketing* | 2 à 3 jours, après le chantier 1 |
| A.9 | **Équipe du vendeur** | La vendeuse d'un magasin a son propre accès, limité au stock et aux commandes de son magasin, sans les prix ni les reversements | Connexion par lien ou code WhatsApp, magasins, stock par magasin | 1 à 2 semaines, en dernier |

## OCD Business : ce qui est réservé à la formule (~2 jours dans ce plan)

OCD touche une commission sur chaque vente : ce qui fait vendre reste pour tous. La formule
mensuelle OCD Business (chantier 12 de la feuille de route) réunit ce qui sert les vendeurs
organisés (plusieurs lieux, une équipe, piloter) et ce qui coûte à OCD à chaque usage (messages
WhatsApp *Marketing*). C'est aussi le cœur de l'offre pour les commerçants qui ne font pas de lives.

| Pour tous les vendeurs | Réservé à OCD Business |
|---|---|
| Toutes les corrections (étape 0) | Plusieurs lieux, donc le stock par magasin (S) : un vendeur à un seul lieu ne voit aucune différence |
| Ajouter, modifier, retirer, partager ses produits ; catalogue pour le statut | L'équipe du vendeur (A.9) |
| Un lieu (magasin ou domicile), sa vérification, l'affiche QR | Les statistiques détaillées (chantier 3) ; les chiffres sous chaque produit et magasin (1.1, M.6) restent pour tous |
| Retrait en magasin, mise de côté, mode vacances, prix promo, alertes | Les nouveautés aux abonnés chaque semaine (pour tous : une fois par mois) |

| # | Ajout | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| B.1 | **Interrupteur « Formule Business »** | Sur la fiche du vendeur, jusqu'à une date ; un réglage général « Fonctions Business offertes à tous », allumé jusqu'au lancement d'OCD Business. Les fonctions de la formule le lisent dès qu'elles sont faites : le chantier 12 n'a plus qu'à vendre la formule | Pass de l'annuaire (30 jours prépayés, rappel, renouvellement) | ~2 jours, avec les magasins |

- **Avant le lancement** : ces fonctions sont annoncées dès le premier jour « offertes pendant le
  lancement ».
- **Au lancement** : les vendeurs qui les utilisent déjà reçoivent 2 mois de formule, plutôt
  qu'une coupure.
- **Fin de la formule, rien n'est supprimé** : les lieux en plus sont masqués aux clients (les
  commandes partent toujours de tous les magasins), l'équipe est mise en pause, les statistiques
  détaillées sont cachées ; tout revient avec la formule.
- **Le prix** est fixé par l'équipe, après un essai avec 5 à 10 vendeurs. Repère : le pass de
  l'annuaire coûte 5 000 F pour 30 jours, et OCD Business comprend OCD Express. Piste à étudier :
  une commission plus basse pour les vendeurs de la formule.

## Ordre de travail

Étape 0 (et les modèles WhatsApp soumis à Meta) → étape 1 → magasins (M, avec B.1) → stock par magasin (S,
avec 2.5) → reste de l'étape 2 → autour des magasins (A.1 à A.7) → étape 3 → équipe du vendeur
(A.9). Le mode vacances (A.5) peut remonter à tout moment ; les nouveautés (A.8) viennent après le
chantier 1 de la feuille de route. En tout, 5 à 6 mois de travail.

## Décisions prises le 16 novembre 2026

- **Motif du refus d'un produit** : c'est une correction, pas un ajout : la décision de l'équipe
  le prévoit déjà (`DECISIONS.md:140`) ; faite à l'étape 0 (0.7).
- **Photo** : appareil photo ou galerie, au choix du vendeur ; l'authenticité vient de la
  vérification de l'équipe (0.6).
- **Modification d'un produit** : nouveau nom ou nouvelle photo vérifiés, l'ancienne version restant
  en vente en attendant ; prix sans vérification, grand écart à confirmer ; stock jamais vérifié (2.1).
- **Photos de couleur** : vérifiées comme les autres photos ; une photo ajoutée par l'équipe ne l'est
  pas (2.1).
- **Magasins vérifiés avant d'être montrés** : photo de la devanture et position prise sur place ;
  seuls l'adresse, la position et la photo repassent à la vérification (M.5).
- **Vendeur qui vend depuis chez lui** : le quartier, « Sur rendez-vous » et WhatsApp, rien de plus ;
  pas de retrait chez lui ; l'équipe voit l'adresse complète (M).
- **Paiement du retrait en magasin** : les règles du paiement à la porte (A.1).
- **Stock par magasin à partir de 2 lieux** seulement (S).
- **Magasin qui sert une livraison** : celui de la ville du client qui a toute la commande, sinon
  le magasin de départ, sinon un colis par magasin (S.4).
- **Ce que voit le client** : « Disponible » ou « Épuisé » par magasin et « Plus que N », sans le
  nombre exact de chaque magasin (S.3).
- **Design** : les petits ajouts dans un écran existant sont faits avec les composants existants et
  validés sur une capture du téléphone ; les nouveaux écrans et parcours (Mes magasins, Nos
  magasins, écran du stock, choix du retrait, vérification des magasins) sont d'abord dessinés dans
  `prototype/design-valide/`, validés, puis faits.
- **Modèles WhatsApp** : écrits et soumis à Meta dès le début de l'étape 0. Les messages
  d'information (produit ou magasin accepté ou refusé, stock bas, colis prêt au retrait) en
  *Utility*, sans promotion ni invitation à acheter, sinon Meta les refuse (`INCORRECT_CATEGORY`,
  voir `PROGRESSION.md`) ; les nouveautés (A.8) en *Marketing*, plus strict et plus cher.
- **Client qui ne vient pas chercher son colis** : la règle d'une livraison échouée. Rappel WhatsApp
  la veille de la fin du délai (3 jours par défaut), puis colis annulé, pièces rendues au stock du
  magasin, et un avoir s'il a payé en ligne (A.1).
- **Réglages des administrateurs** : la liste ci-dessous et ses valeurs par défaut.
- **OCD Business** : ce qui fait vendre reste pour tous ; plusieurs lieux et le stock par magasin,
  l'équipe du vendeur, les statistiques détaillées et les nouveautés chaque semaine sont réservés à
  la formule ; offerts pendant le lancement, 2 mois offerts à leurs utilisateurs au lancement, rien
  de supprimé à la fin de la formule (B.1).

## Réglages des administrateurs

Ce que l'équipe pourra changer dans Odoo sans toucher au code, validé le 16 novembre 2026 avec
les valeurs par défaut ci-dessous. Chaque réglage est fait avec son chantier, dans les écrans qui
existent déjà. Les Paramètres et les Automatisations sont pour les responsables d'OCD Live, qui
n'ont pas besoin d'être administrateurs d'Odoo (`PROGRESSION.md`, points d'attention).

### Paramètres d'OCD Live (OCD Live › Configuration › Paramètres)

Une nouvelle section « Produits et magasins des vendeurs », comme « Shop et livraisons ».

| Réglage | Chantier | Par défaut |
|---|---|---|
| Photos de la galerie acceptées | 0.6 | Oui |
| Taille maximale d'une photo envoyée | 0.4 | 10 Mo (aujourd'hui écrit dans le code : `MAX_PHOTO_BYTES`) |
| Taille des photos réduites dans le téléphone | 0.4 | 1600 px de côté |
| Changements vérifiés par l'équipe | 2.1, 2.6 | Nom, photos, photos de couleur ; pas le prix |
| Écart de prix à confirmer par le vendeur | 2.1 | 50 % |
| « Plus que N » sur les cartes et par magasin | S.3 | 3 (aujourd'hui écrit dans le code : `LOW_STOCK`) |
| Seuil de l'alerte de stock bas | 3.4 | 2 pièces |
| Prix promo : durée et remise au plus | 3.1 | 30 jours, 50 % |
| Tailles et couleurs proposées aux vendeurs | 3.5 | Les attributs choisis par l'équipe (taille, couleur, pointure…) |
| Lieux par vendeur, au plus | M.1 | 5 |
| Horaires proposés à un nouveau magasin | M.1 | Lun.–sam., 8 h–19 h |
| Vente depuis chez soi permise | M | Oui |
| Magasins vérifiés avant d'être montrés ; photo de la devanture et position obligatoires | M.5 | Oui |
| Cartes de l'itinéraire | M.2 | Google Maps (ou OpenStreetMap) |
| Texte de l'affiche QR | M.7 | « Commandez aussi en ligne, livré chez vous » |
| Produits par image du catalogue | 1.7 | 4 |
| Stock par magasin | S | Activé, à partir de 2 lieux |
| Magasin qui sert une livraison | S.4 | Ville du client d'abord, puis le magasin de départ |
| Retrait en magasin | A.1 | Activé |
| Paiements au retrait | A.1 | Les mêmes que le paiement à la porte |
| Délai pour venir chercher un colis | A.1 | 3 jours, rappel la veille de la fin |
| Mise de côté : durée, réservations actives par client, absences avant blocage | A.7 | 24 h, 1, 2 |
| Mode vacances : durée au plus | A.5 | 60 jours |
| Nouveautés aux abonnés : rythme et jour d'envoi | A.8 | Une fois par mois pour tous, chaque semaine avec OCD Business ; le vendredi |
| Personnes dans l'équipe d'un vendeur, au plus | A.9 | 5 |
| Fonctions Business offertes à tous | B.1 | Oui, jusqu'au lancement d'OCD Business |

### Sur la fiche du vendeur (back-office)

Comme pour le temps de préparation d'un colis aujourd'hui : laissé vide, le réglage général
s'applique.

| Réglage | Chantier |
|---|---|
| Seuil de l'alerte de stock bas | 3.4 |
| Lieux au plus | M.1 |
| Retrait en magasin permis | A.1 |
| Encaisse les espèces (existe déjà : `ocd_vendor_collects`), aussi au retrait | A.1 |
| Magasin de départ des colis (choisi par le vendeur, changé par l'équipe au besoin) | A.4 |
| Mode vacances (dates), mis par l'équipe pour le vendeur au besoin | A.5 |
| Mise de côté permise | A.7 |
| Personnes de son équipe : ajouter, retirer | A.9 |
| Formule Business, jusqu'au… (comme le pass de l'annuaire) | B.1 |

### Listes et automatisations (écrans qui existent déjà)

| Écran | Ce que l'équipe y règle | Chantiers |
|---|---|---|
| Raisons de refus (lien depuis les Paramètres) | Les motifs et leur message au vendeur ; nouveaux : « Photo qui n'est pas la tienne », motifs des magasins (« Devanture absente », « Position loin de l'adresse ») | 0.6, 0.7, M.5 |
| Automatisations (`ocd.automation`, un interrupteur par règle) | Allumer ou éteindre : WhatsApp produit accepté ou refusé, magasin accepté ou refusé, stock bas, colis prêt au retrait, colis pas venu chercher, mise de côté libérée, nouveautés aux abonnés, « Préviens-moi » au retour de vacances | 2.4, 3.4, M.5, A.1, A.5, A.7, A.8 |
| WhatsApp › Modèles | Les textes des messages, soumis à Meta | Tous les messages |
| Attributs et valeurs d'Odoo | Tailles, couleurs et leur teinte | 2.5, 3.5 |
| Villes et quartiers | Les listes des lieux | M.1, A.3 |

### Ce qui reste fixe dans le code

Ce qui protège l'argent, les preuves ou les personnes, comme les automatisations « toujours
actives » : pas de remise sans paiement, un code par colis, un produit retiré jamais supprimé (les
commandes passées le gardent), l'adresse d'un vendeur qui vend depuis chez lui jamais montrée aux
clients, le stock jamais vérifié.

## Liens avec la feuille de route

Chaque chantier de `FEUILLE_DE_ROUTE.md` (retenus le 14 novembre 2026) et ce qu'il partage avec ce
plan. OCD Vote (4) et OCD Tickets (6) n'ont pas de lien avec lui.

| Chantier | Ce qu'il partage avec ce plan | Ce qu'on fait |
|---|---|---|
| 1. Suivre un vendeur | Les nouveautés aux abonnés (A.8) en dépendent | Fait avant A.8 ; le bouton « Suivre » est aussi sur les magasins (M.2) |
| 2. Garantie OCD et avis | Le badge « Vendeur vérifié » ; les avis des acheteurs | Un magasin vérifié (M.5) a le même badge ; les avis de chaque produit s'affichent dans « Mes produits » une fois le chantier 2 fait |
| 3. Statistiques du vendeur | Les chiffres des produits et des magasins (1.1, 3.3, M.6) | 3.3 se fait dans le chantier 3 ; 1.1 et M.6 restent sous chaque produit et magasin, et l'écran des statistiques les reprend : un seul calcul |
| 5. Paiement automatique dans l'UEMOA | Le paiement sur le téléphone au comptoir (A.1) | Automatique au Cameroun (CamPay) ; ailleurs, Mobile Money vérifié par l'équipe jusqu'au chantier 5, donc plus lent au comptoir |
| 7. Programme et événements | Le prix promo (3.1) | Une grande soirée (Vendredi noir, Tabaski…) invite ses vendeurs à mettre une promo pour la soirée |
| 8. Clips automatiques | Partager un produit, catalogue (1.3, 1.7) | Les clips d'un produit s'affichent dans « Mes produits », prêts à partager |
| 9. OCD Express | Les lieux (M) | Le lieu où le livreur prend les colis d'un expéditeur reprend la fiche « lieu » |
| 10. Points relais | Les lieux (M), A.6 | Un point relais est un lieu ; A.6 se fait avec le chantier 10 |
| 11. Ambassadeurs | Partager un produit (1.3) | Le lien de partage reçoit ensuite le lien personnel de l'ambassadeur |
| 12. OCD Business | Plusieurs lieux, stock par magasin, équipe du vendeur, statistiques | Ce qui est réservé à la formule est décidé (section OCD Business) ; l'interrupteur (B.1) est déjà fait quand le chantier 12 commence |
| 13. Diaspora | Retrait en magasin (A.1) | Un proche retire en magasin ce qu'on lui a acheté : le code part sur son WhatsApp |
| 14. Live sur la plateforme | Préparer son prochain live (3.2) | Les produits préparés s'affichent dans le lecteur du live |

Écarté le 14 novembre et à ne pas réintroduire : « Préparer son prochain live » (3.2) reste le choix
des produits pour la régie, sans numéros de produits ni page « Je prends » ; aucune intelligence
artificielle.

## Écarté le 16 novembre 2026

- Ajouter un produit par WhatsApp (envoyer une photo et un prix au numéro d'OCD).
- Code promo du vendeur, pour l'instant : deux façons de baisser un prix avec le prix promo (3.1) ;
  dans un panier de plusieurs vendeurs, le code ne doit toucher que les produits de son vendeur et
  la commission se calcule sur le prix réduit. À revoir après 3.1 si les vendeurs le demandent.
