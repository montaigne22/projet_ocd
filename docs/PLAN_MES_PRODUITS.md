# Plan de la page « Mes produits », des magasins et du stock par magasin

Page du vendeur `/ocd/espace/moi/produits` (design `MesProduits`) et ce qui s'y rattache. Plan
retenu le 16 novembre 2026, après une relecture du code : d'abord les corrections, puis les ajouts,
du plus rapide au plus long. Les durées sont des estimations, tests compris. Les décisions prises
sont en bas ; chacune rejoindra `DECISIONS.md` quand ce qu'elle règle sera fait.

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

## Étape 1 : rapide, avec ce qui existe déjà (~1 semaine)

| # | Ajout | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| 1.1 | **Les chiffres déjà comptés** | Sous chaque produit : « 12 personnes t'ont écrit sur WhatsApp », et sur un produit épuisé « 5 clients attendent son retour » | Clics WhatsApp de la boutique (`ocd_wa_clicks`, vus aujourd'hui seulement par l'équipe), demandes « Préviens-moi » (`ocd.stock.alert`) | ~1 jour |
| 1.2 | **Voir comme un client** | Lien vers la fiche du produit dans la boutique, quand il est en vente | Fiche produit | ~½ jour |
| 1.3 | **Partager un produit** | Photo et lien d'un produit précis, prêts pour le statut WhatsApp | Bouton « Partager ma boutique » (`ocd_live/static/src/interactions/share.js`) | ~1 jour |
| 1.4 | **Filtrer par état** | « À vérifier », « Refusé », « Épuisé », « En vente », quand le catalogue grandit | États déjà calculés par la page | ~½ jour |
| 1.5 | **Dupliquer un produit** | Le même modèle dans un autre tissu : la copie part à la vérification | Ajout d'un produit | ~1 jour |
| 1.6 | **Ordre de la boutique** | Monter un produit, en mettre un en avant | Ordre des produits de la boutique (`website_sequence`) | ~1 jour |

## Étape 2 : gérer ses produits (~2 semaines)

| # | Ajout | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| 2.1 | **Modifier** | Nouveau nom ou nouvelle photo : vérifiés par l'équipe, l'ancienne version reste en vente en attendant. Prix : sans vérification, mais un grand écart se confirme (« Tu passes de 15 000 F à 1 500 F, c'est bien ça ? ») et l'équipe voit l'historique des prix. Stock : jamais vérifié | Formulaire d'ajout, écran « À vérifier » | 4 à 5 jours |
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

## Magasins du vendeur (~2 semaines)

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

## Autour des magasins et de la boutique (~4 semaines)

| # | Ajout | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| A.1 | **Retrait en magasin** | Le client choisit « Je passe le récupérer » : pas de frais de livraison. Il paie comme à la porte : en ligne, sur son téléphone au comptoir (Mobile Money, chez tous les vendeurs), ou en espèces seulement chez les vendeurs qui encaissent déjà à la porte (commission retenue sur le reversement suivant). Pas de remise sans paiement : le code n'est accepté qu'une fois l'argent encaissé. Pas de retrait chez un vendeur qui vend depuis chez lui | Paiement à la porte et réglage `ocd_vendor_collects` (`DECISIONS.md:150-152`), code de livraison, reversements, magasins (M.1) | 1 à 2 semaines |
| A.2 | **Le bot WhatsApp donne les magasins** | Sur le numéro d'OCD, « Où êtes-vous ? » reçoit les magasins du vendeur de la commande ou du produit en question : adresse, horaires, position à ouvrir dans les cartes. Le bouton WhatsApp de la boutique, lui, mène au numéro du vendeur : le bot ne voit pas ces conversations | Envoi des magasins et des positions du bot (`whatsapp_cloud_sale`, `_whatsapp_send_location`), aujourd'hui pour les entrepôts d'OCD | 2 à 3 jours |
| A.3 | **Vendeurs près de chez moi** | Filtre par ville et quartier dans le shop et l'annuaire ; du plus proche au plus loin si le client partage sa position | Magasins (M.1), villes et quartiers | ~1 semaine |
| A.4 | **Point de départ des colis** | Le vendeur choisit le magasin d'où partent ses colis : le livreur vient l'y chercher, le prix de la livraison part de là | Départ des colis (`_ocd_origin`, aujourd'hui la ville du vendeur), tournées des livreurs | ~2 jours |
| A.5 | **Mode vacances** | « De retour le 2 janvier » sur la boutique : produits visibles, commandes en pause, « Préviens-moi à son retour » | « Préviens-moi » de la boutique (`ocd.boutique.alert`) | ~2 jours ; ne dépend pas des magasins, peut se faire tôt |
| A.6 | **Magasins points relais** | Les vendeurs qui le veulent gardent les colis d'autres vendeurs | Magasins (M.1) | Avec le chantier 10 (Points relais) de la feuille de route |

## Ordre de travail

Étape 0 → étape 1 → magasins (M) → stock par magasin (S, avec 2.5) → reste de l'étape 2 → autour
des magasins (A) → étape 3. Le mode vacances (A.5) peut remonter à tout moment. En tout, 4 à 5 mois
de travail.

## Décisions prises le 16 novembre 2026

- **Motif du refus d'un produit** : c'est une correction, pas un ajout : la décision de l'équipe
  le prévoit déjà (`DECISIONS.md:140`) ; faite à l'étape 0 (0.7).
- **Photo** : appareil photo ou galerie, au choix du vendeur ; l'authenticité vient de la
  vérification de l'équipe (0.6).
- **Modification d'un produit** : nouveau nom ou nouvelle photo vérifiés, l'ancienne version restant
  en vente en attendant ; prix sans vérification, grand écart à confirmer ; stock jamais vérifié (2.1).
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

## Encore ouvert

- **Design** : le site suit le design validé. Les nouveaux éléments (filtres, chiffres, modifier,
  magasins, promo…) sont à ajouter au design et à valider, ou à faire avec les composants existants
  puis à valider sur l'écran.
- **Photos des couleurs** : publiées aujourd'hui sans vérification ; à aligner sur la règle de 2.1 ?
- **Modèles WhatsApp** à faire approuver par Meta : produit accepté, produit refusé, stock bas.
- **Idées proposées, sans réponse** : affiche QR du magasin, mettre de côté pour essayer, catalogue
  pour le statut WhatsApp, code promo du vendeur, nouveautés aux abonnés, équipe du vendeur, visites
  grâce à OCD.

## Liens avec la feuille de route

« Ventes par produit » (3.3) rejoint le chantier 3 (Statistiques du vendeur) ; « Partager un
produit » (1.3) prépare le chantier 11 (Ambassadeurs) ; les magasins points relais (A.6) se font
avec le chantier 10 (Points relais).

## Écarté le 16 novembre 2026

Ajouter un produit par WhatsApp (envoyer une photo et un prix au numéro d'OCD).
