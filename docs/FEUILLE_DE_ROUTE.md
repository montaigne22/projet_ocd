# Feuille de route d'OCD Live

Périmètre retenu avec l'équipe le 14 novembre 2026 : vendre ce qu'OCD a déjà construit à d'autres
clients (OCD Express, OCD Business, OCD Tickets), OCD Vote, et une sélection d'améliorations de
l'application. L'ordre ci-dessous est celui proposé ; l'avancement se suit dans
[`PROGRESSION.md`](PROGRESSION.md).

Complété le 16 novembre 2026 par l'espace vendeur : « Mes produits », les magasins des vendeurs et
le stock par magasin (chantiers 15 à 22, détaillés dans [`PLAN_MES_PRODUITS.md`](PLAN_MES_PRODUITS.md)),
le bouton « Signaler » de la garantie (chantier 2) et de nouvelles mesures.

## Phase 1 : de 0 à 2 mois, rapide et avec ce qui existe déjà

| # | Chantier | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| 15 | **Espace vendeur fiable** | En tête : les corrections de « Mes produits » (boutons − / + du stock, photo gardée après une erreur, double envoi, photo allégée, prix mal lu, appareil photo ou galerie, motif du refus montré au vendeur), la voix et l'aide prévues par le design validé | Plan, étape 0 | ~1,5 semaine |
| 16 | **Mes produits : gagner vite** | Chiffres déjà comptés (contacts WhatsApp, clients en attente), voir comme un client, partager un produit, filtres, dupliquer, ordre de la boutique, catalogue pour le statut WhatsApp, démarrage du vendeur (« Ta boutique est prête à 60 % ») | Plan, étape 1 ; fait avec les chantiers 1 et 3 | ~2,5 semaines |
| 1 | **Suivre un vendeur** | « Awa est en live maintenant » sur WhatsApp, à chaque live du vendeur suivi | « Préviens-moi » de la boutique, messages WhatsApp | ~1 semaine |
| 2 | **Garantie OCD et avis** | La garantie rendue visible (l'argent n'est versé au vendeur qu'après le code de livraison), les avis des acheteurs sur les boutiques et les cartes du fil, le badge « Vendeur vérifié » ; un bouton « Signaler » un produit ou un vendeur, pour les clients, vers l'écran « À vérifier » de l'équipe | Notes demandées après la livraison, code de livraison, vérification des vendeurs | 1 à 2 semaines, plus ~2 jours pour « Signaler » |
| 3 | **Statistiques du vendeur** | Dans son espace : vues, clics et ventes par live, meilleures heures, clients fidèles ; ventes par produit (plan, 3.3) | Espace vendeur, commandes, lives ; chiffres des produits et des magasins du plan (un seul calcul) | ~2 semaines, plus 2 à 3 jours pour les ventes par produit |
| 4 | **OCD Vote** | Votes payants en Mobile Money pour des concours (miss, awards, talents, écoles) : page du concours, candidats avec leur numéro, vote sur la page ou par WhatsApp (« VOTE 12 »), classement en direct, bandeau pour le live de la finale, reversement à l'organisateur. Seules les voix payées comptent, chacune liée à son paiement. | Paiements (CamPay, mode démo), reversements, WhatsApp, page d'un live | 3 à 4 semaines |
| 5 | **Paiement automatique dans l'UEMOA** | T-Money, Flooz, Orange Money, Wave… par un agrégateur (CinetPay, FedaPay ou PayDunya), à la place du Mobile Money vérifié à la main par l'équipe | Formulaire de paiement d'Odoo, reversements | 2 à 3 semaines, après le contrat avec l'agrégateur |

## Phase 2 : de 2 à 6 mois

| # | Chantier | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| 17 | **Magasins des vendeurs** | Les lieux du vendeur (magasin ouvert au public, ou « je vends depuis chez moi »), vérifiés par l'équipe ; « Nos magasins » sur la boutique (horaires, ouvert maintenant, itinéraire, appeler) ; back-office ; visites grâce à OCD ; affiche QR ; magasin de départ des colis ; interrupteur « Formule Business ». Avant les chantiers 9 et 10, qui reprennent la fiche « lieu » | Plan, magasins (M), A.4, B.1 | ~3 semaines |
| 18 | **Stock par magasin** | « Disponible à Akwa, épuisé à Bonapriso » : un emplacement de stock par lieu dans l'entrepôt actuel, le stock de chaque magasin dans « Mes produits » (avec les tailles et les couleurs), le magasin qui sert chaque commande | Plan, stock par magasin (S) et 2.5 | 3 à 4 semaines |
| 19 | **Gérer ses produits** | Modifier (vérifié, l'ancienne version reste en vente), retirer, WhatsApp accepté ou refusé, plusieurs photos, brouillon gardé hors connexion | Plan, étape 2 | ~2,5 semaines |
| 20 | **Autour des magasins** | Retrait en magasin (payé comme à la porte), le bot WhatsApp donne les magasins, vendeurs près de chez moi, mode vacances, mettre de côté pour essayer, nouveautés aux abonnés (après le chantier 1) | Plan, A.1 à A.3, A.5, A.7, A.8 | ~6 semaines |
| 6 | **OCD Tickets** | Billets de concerts et d'événements, vendus aussi en live ; QR vérifié une seule fois à l'entrée ; reversement à l'organisateur | Ticket PDF signé et son contrôle à l'entrée, application Événements d'Odoo (gratuite) | 2 à 3 semaines |
| 7 | **Programme et événements** | Programme des lives façon guide télé ; grandes soirées à plusieurs vendeurs (Tabaski, Noël, Vendredi noir, Saint-Valentin), où les vendeurs mettent un prix promo (plan, 3.1) | Fil des lives, page d'un live | 1 à 2 semaines, plus ~1 semaine pour le prix promo |
| 8 | **Clips automatiques** | Chaque moment produit d'un replay devient un clip vertical de 30 secondes, avec le lien du produit, à partager sur TikTok, Reels et les statuts ; les clips de chaque produit dans « Mes produits » | Moments du replay notés par la régie, conversion vidéo (ffmpeg) | 2 à 3 semaines |
| 9 | **OCD Express** | Livraison avec code et paiement à la porte pour tous les vendeurs des réseaux sociaux : espace expéditeur (connexion par numéro), colis sans commande de la boutique, suivi pour le destinataire | Livreurs, code de livraison, caisse du soir, reversements, tarifs par zone, messages des colis ; fiche « lieu » (chantier 17) pour l'endroit où le livreur prend les colis | ~4 semaines, plus l'organisation des livreurs |
| 10 | **Points relais** | Boutiques partenaires où retirer son colis ; livraison moins chère ; les magasins des vendeurs qui le veulent (plan, A.6) | Tarifs de livraison, colis, fiche « lieu » (chantier 17) | 2 à 3 semaines, plus les partenaires |
| 11 | **Ambassadeurs** | Chacun partage un produit avec son lien personnel et touche une commission quand le colis est livré | Images à partager, reversements, code de livraison, partage d'un produit (chantier 16) | 3 à 4 semaines |

## Phase 3 : de 6 à 12 mois

| # | Chantier | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| 21 | **Vendre plus** | Préparer son prochain live (le choix des produits pour la régie), alerte de stock bas, tailles et couleurs choisies par le vendeur dès la création | Plan, 3.2, 3.4, 3.5 | 2,5 à 3,5 semaines |
| 12 | **OCD Business** | Boutique, colis, WhatsApp et statistiques en formule mensuelle, OCD Express compris. Réservés à la formule : plusieurs lieux et le stock par magasin, l'équipe du vendeur, les statistiques détaillées, les nouveautés chaque semaine ; ce qui fait vendre reste pour tous | Le pass de l'annuaire (30 jours prépayés, rappel, renouvellement) : Odoo Community n'a pas d'abonnements ; l'interrupteur « Formule Business » (chantier 17) | ~2 semaines, après OCD Express et les statistiques |
| 22 | **Équipe du vendeur** | La vendeuse d'un magasin a son propre accès, limité au stock et aux commandes de son magasin | Plan, A.9 ; connexion par lien ou code WhatsApp | 1 à 2 semaines, avec le chantier 12 |
| 13 | **Diaspora** | « Acheter pour un proche » : payer en euros par carte, livrer au pays, code de livraison envoyé au proche ; ou retrait en magasin par le proche, avec son code | Devises par pays, paiement par carte, livraison avec code, retrait en magasin (chantier 20) | 2 à 3 semaines |
| 14 | **Live sur la plateforme** | Lecteur vidéo sur le site avec les produits, le chat et l'achat ; le même live diffusé en même temps sur TikTok, Facebook et YouTube | Page d'un live, régie, produits préparés pour le live (chantier 21) | ~6 semaines, plus un service vidéo payé à la minute |

## Charge

Avec les chantiers ajoutés le 16 novembre, le développement passe d'environ 37 à 63 semaines :
environ 15 en phase 1 (prévue sur 2 mois), 32 en phase 2, 15 en phase 3. À temps de développement
égal, le tout demande 14 à 15 mois au lieu de 12. Pour tenir 12 mois : plus de temps de
développement, ou repousser des chantiers sans lien avec l'espace vendeur (OCD Vote, OCD Tickets).

## Décisions à prendre

- **OCD Vote** (choix proposés, à confirmer) : concours créés par des organisateurs et par OCD ;
  100 F la voix, packs de 10 voix à 900 F et de 50 voix à 4 000 F ; 60 % pour l'organisateur et 40 %
  pour OCD ; pas de voix gratuites. À vérifier : le cadre légal des votes payants dans chaque pays
  (ne pas être assimilé à une loterie).
- **Paiement dans l'UEMOA** : choisir l'agrégateur, puis signer son contrat (documents de
  l'entreprise) : à lancer dès maintenant.
- **OCD Express** : nombre de livreurs, tarifs pour les expéditeurs, règles des espèces.
- **OCD Business** : le prix, après un essai avec 5 à 10 vendeurs (repère : le pass de l'annuaire,
  5 000 F pour 30 jours) ; piste : une commission plus basse pour la formule. Ce qui lui est réservé
  est décidé (`PLAN_MES_PRODUITS.md`).
- **Live sur la plateforme** : budget du service vidéo.

Les décisions de l'espace vendeur (chantiers 15 à 22) sont prises : voir
[`PLAN_MES_PRODUITS.md`](PLAN_MES_PRODUITS.md).

## Écarté

- **Le 14 novembre 2026** : studio et agence, acheter pendant le live (numéros des produits, page
  « Je prends »), intelligence artificielle, et les nouveaux concepts à part entière (La Fabrique,
  Battle des vendeurs, etc.).
- **Le 16 novembre 2026** : ajouter un produit par WhatsApp ; le code promo du vendeur, pour
  l'instant (à revoir après le prix promo).

## Ce qu'on mesure

- Lives : part des spectateurs qui achètent, panier moyen, clients qui rachètent sous 30 jours.
- OCD Express : colis par jour, coût de livraison par colis.
- OCD Vote : voix et montant par concours. OCD Tickets : billets vendus par événement.
- Espace vendeur : délai de vérification d'un produit, part des produits refusés et leurs motifs,
  vendeurs avec au moins un magasin vérifié, itinéraires et appels par magasin, retraits en magasin
  par semaine, part des mises de côté qui finissent en achat, clients en attente d'un produit épuisé.
