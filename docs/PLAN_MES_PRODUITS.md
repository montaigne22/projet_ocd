# Plan de la page « Mes produits »

Page du vendeur `/ocd/espace/moi/produits` (design `MesProduits`). Plan retenu le 16 novembre 2026,
après une relecture du code : d'abord les corrections, puis les ajouts, du plus rapide au plus long.
Les durées sont des estimations, tests compris.

## Étape 0 : corrections, avant tout le reste (~1 semaine)

| # | Correction | Le problème aujourd'hui | Ce qu'on fait | Effort |
|---|---|---|---|---|
| 0.1 | **Boutons − / + du stock** | La page affiche le stock disponible (stock moins ce qui est réservé), mais le bouton l'enregistre comme stock total : avec 5 en stock dont 2 réservés, la page montre 3, « + » pose 4 et la page montre 2. Le chiffre envoyé est celui de l'affichage : une vente arrivée entre-temps est effacée. | Le bouton envoie +1 ou −1, appliqué au stock réel au moment du clic | ~½ jour |
| 0.2 | **Photo perdue en cas d'erreur** | Nom ou prix manquant : la page se recharge et le vendeur doit reprendre la photo | Nom et prix vérifiés dans le téléphone avant l'envoi ; si le serveur refuse quand même, la photo reçue est gardée pour le nouvel essai | ~1 jour |
| 0.3 | **Double envoi** | Sur un réseau lent, un second appui crée deux produits | Bouton désactivé (« Envoi… ») et jeton unique par formulaire, vérifié par le serveur | ~½ jour |
| 0.4 | **Photo trop lourde** | Envoyée telle quelle (3 à 8 Mo), alors que le serveur la réduit de toute façon | Photo réduite dans le téléphone avant l'envoi (~300 Ko) : plus rapide, moins de forfait | ~1 jour |
| 0.5 | **Prix mal lu** | Tout ce qui n'est pas un chiffre est retiré : « 2500,50 » devient 250 050, « 3000-5000 » devient 30 005 000 | Ces saisies sont refusées avec un message clair | ~½ jour |

## Étape 1 : rapide, avec ce qui existe déjà (~1 semaine)

| # | Ajout | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| 1.1 | **Les chiffres déjà comptés** | Sous chaque produit : « 12 personnes t'ont écrit sur WhatsApp », et sur un produit épuisé « 5 clients attendent son retour » | Clics WhatsApp de la boutique (`ocd_wa_clicks`, vus aujourd'hui seulement par l'équipe), demandes « Préviens-moi » (`ocd.stock.alert`) | ~1 jour |
| 1.2 | **Voir comme un client** | Lien vers la fiche du produit dans la boutique, quand il est en vente | Fiche produit | ~½ jour |
| 1.3 | **Partager un produit** | Photo et lien d'un produit précis, prêts pour le statut WhatsApp | Bouton « Partager ma boutique » (`ocd_live/static/src/interactions/share.js`) | ~1 jour |
| 1.4 | **Filtrer par état** | « À vérifier », « Refusé », « Épuisé », « En vente », quand le catalogue grandit | États déjà calculés par la page | ~½ jour |
| 1.5 | **Dupliquer un produit** | Le même modèle dans un autre tissu : la copie part à la vérification | Ajout d'un produit | ~1 jour |
| 1.6 | **Ordre de la boutique** | Monter un produit, en mettre un en avant | Ordre des produits de la boutique (`website_sequence`) | ~1 jour |

## Étape 2 : gérer ses produits (2 à 3 semaines)

| # | Ajout | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| 2.1 | **Modifier** | Changer le nom, le prix ou la photo d'un produit envoyé (voir la décision sur la revérification) | Formulaire d'ajout | 2 à 3 jours |
| 2.2 | **Retirer** | Ne plus montrer un produit, et pouvoir le remettre ; jamais supprimé, les commandes passées le gardent | Produits masqués (`is_published`) | ~½ jour |
| 2.3 | **Refus expliqué, corriger et renvoyer** | La raison choisie par l'équipe s'affiche sous le produit (aujourd'hui seulement en note interne) ; le vendeur corrige et le renvoie à la vérification | Raisons de refus (`ocd.listing.refuse.reason`), écran « À vérifier » de l'équipe | ~2 jours |
| 2.4 | **WhatsApp accepté ou refusé** | « Ton produit Robe wax est en vente » ou « … est refusé : photo floue », avec le lien de la page | Messages WhatsApp aux vendeurs | 1 à 2 jours, plus l'approbation des modèles par Meta |
| 2.5 | **Stock par taille et par couleur** | Les − / + pour chaque variante (aujourd'hui seulement les produits sans variantes) | Réglage du stock (`_ocd_set_stock`), photos des couleurs | 2 à 3 jours |
| 2.6 | **Plusieurs photos** | Ajouter, retirer et ordonner les photos d'un produit | Galerie de la fiche produit (`product_template_image_ids`) | 2 à 3 jours |

## Étape 3 : vendre plus et suivre (4 à 5 semaines)

| # | Ajout | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| 3.1 | **Prix promo** | Prix barré et nouveau prix, jusqu'à une date ; affiché dans la boutique, la fiche et le panier | Prix barré du site d'Odoo, à confirmer sur la version utilisée | ~1 semaine |
| 3.2 | **Préparer son prochain live** | Cocher les produits à montrer : la régie les a sous la main | Produits montrés pendant un live (`_ocd_show_product`), aujourd'hui choisis seulement par l'équipe | 3 à 4 jours |
| 3.3 | **Ventes par produit** | Pièces vendues, dernière vente | Commandes ; à faire avec le chantier 3 « Statistiques du vendeur » de la feuille de route | 2 à 3 jours |
| 3.4 | **Alerte de stock bas** | WhatsApp au vendeur quand il reste peu de pièces (2 par défaut) | Messages WhatsApp aux vendeurs, stock | 1 à 2 jours, plus l'approbation du modèle par Meta |
| 3.5 | **Tailles et couleurs dès la création** | Le vendeur choisit les tailles et les couleurs en ajoutant le produit, au lieu de l'équipe | Attributs et variantes d'Odoo, photos des couleurs | 1 à 2 semaines |

## Décisions à prendre

- **Revérification après une modification** (proposition) : un nouveau nom ou une nouvelle photo
  repassent à la vérification ; le prix et le stock non. Pendant la vérification, deux choix :
  le produit est masqué (simple), ou l'ancienne version reste en vente (mieux pour le vendeur,
  ~2 jours de plus).
- **Photo** (proposition) : laisser le choix entre l'appareil photo et la galerie. Aujourd'hui la
  plupart des téléphones Android ouvrent seulement l'appareil photo (`capture="environment"`), alors
  que beaucoup de vendeurs ont déjà leurs photos dans la galerie ou sur WhatsApp.
- **Design** : le site suit le design validé. Les nouveaux éléments (filtres, chiffres, modifier,
  promo…) sont à ajouter au design `MesProduits` et à valider, ou à faire avec les composants
  existants puis à valider sur l'écran.
- **Modèles WhatsApp** à faire approuver par Meta : produit accepté, produit refusé, stock bas.
- **Liens avec la feuille de route** : « Ventes par produit » rejoint le chantier 3 (Statistiques
  du vendeur) ; « Partager un produit » prépare le chantier 11 (Ambassadeurs, lien personnel).

## Écarté le 16 novembre 2026

Ajouter un produit par WhatsApp (envoyer une photo et un prix au numéro d'OCD).
