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
| 15 | **Espace vendeur fiable** | En tête : les corrections de « Mes produits » (boutons − / + du stock, photo gardée après une erreur, double envoi, photo allégée, prix mal lu, appareil photo ou galerie, motif du refus montré au vendeur), la voix et l'aide prévues par le design validé | Plan, étape 0 | ~1,5 semaine ; **fait le 16 novembre 2026** |
| 16 | **Mes produits : gagner vite** | Chiffres déjà comptés (contacts WhatsApp, clients en attente), voir comme un client, partager un produit, filtres, dupliquer, ordre de la boutique, catalogue pour le statut WhatsApp, démarrage du vendeur (« Ta boutique est prête à 60 % ») | Plan, étape 1 ; fait avec les chantiers 1 et 3 | ~2,5 semaines ; **fait le 16 novembre 2026** |
| 1 | **Suivre un vendeur** | « Awa est en live maintenant » sur WhatsApp, à chaque live du vendeur suivi | « Préviens-moi » de la boutique, messages WhatsApp | ~1 semaine ; **fait le 17 novembre 2026**, avec les nouveautés aux abonnés (A.8) |
| 2 | **Garantie OCD et avis** | La garantie rendue visible (l'argent n'est versé au vendeur qu'après le code de livraison), les avis des acheteurs sur les boutiques et les cartes du fil, le badge « Vendeur vérifié » ; un bouton « Signaler » un produit ou un vendeur, pour les clients, vers l'écran « À vérifier » de l'équipe | Notes demandées après la livraison, code de livraison, vérification des vendeurs | 1 à 2 semaines, plus ~2 jours pour « Signaler » ; **fait le 17 novembre 2026** |
| 3 | **Statistiques du vendeur** | Dans son espace : vues, clics et ventes par live, meilleures heures, clients fidèles ; ventes par produit (plan, 3.3) | Espace vendeur, commandes, lives ; chiffres des produits et des magasins du plan (un seul calcul) | ~2 semaines, plus 2 à 3 jours pour les ventes par produit ; **fait le 17 novembre 2026**, avec 3.3 et le résumé du lundi sur WhatsApp |
| 4 | **OCD Vote** | Votes payants en Mobile Money pour des concours (miss, awards, talents, écoles) : page du concours, candidats avec leur numéro, vote sur la page ou par WhatsApp (« VOTE 12 »), classement en direct, bandeau pour le live de la finale, reversement à l'organisateur. Seules les voix payées comptent, chacune liée à son paiement. | Paiements (CamPay, mode démo), reversements, WhatsApp, page d'un live | 3 à 4 semaines ; **fait le 17 novembre 2026** (modules `ocd_vote` et `ocd_vote_whatsapp`) |
| 5 | **Paiement automatique dans l'UEMOA** | T-Money, Flooz, Orange Money, Wave… par CinetPay et Flutterwave (choisis le 18 novembre 2026), à la place du Mobile Money vérifié à la main par l'équipe | Formulaire de paiement d'Odoo, Flutterwave d'Odoo, reversements | 2 à 3 semaines ; **fait le 18 novembre 2026** (module `payment_cinetpay`, Flutterwave d'Odoo) ; ouvert dès que les clés des comptes sont saisies |

## Phase 2 : de 2 à 6 mois

| # | Chantier | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| 17 | **Magasins des vendeurs** | Les lieux du vendeur (magasin ouvert au public, ou « je vends depuis chez moi »), vérifiés par l'équipe ; « Nos magasins » sur la boutique (horaires, ouvert maintenant, itinéraire, appeler) ; back-office ; visites grâce à OCD ; affiche QR ; magasin de départ des colis ; interrupteur « Formule Business ». Avant les chantiers 9 et 10, qui reprennent la fiche « lieu » | Plan, magasins (M), A.4, B.1 | ~3 semaines ; **fait le 16 novembre 2026** |
| 18 | **Stock par magasin** | « Disponible à Akwa, épuisé à Bonapriso » : un emplacement de stock par lieu dans l'entrepôt actuel, le stock de chaque magasin dans « Mes produits » (avec les tailles et les couleurs), le magasin qui sert chaque commande | Plan, stock par magasin (S) et 2.5 | 3 à 4 semaines ; **fait le 16 novembre 2026** (le retrait dans un magasin, S.5, vient avec le retrait en magasin, A.1) |
| 19 | **Gérer ses produits** | Modifier (vérifié, l'ancienne version reste en vente), retirer, WhatsApp accepté ou refusé, plusieurs photos, brouillon gardé hors connexion | Plan, étape 2 | ~2,5 semaines ; **fait le 17 novembre 2026** |
| 20 | **Autour des magasins** | Retrait en magasin (payé comme à la porte), le bot WhatsApp donne les magasins, vendeurs près de chez moi, mode vacances, mettre de côté pour essayer, nouveautés aux abonnés (après le chantier 1) | Plan, A.1 à A.3, A.5, A.7, A.8 | ~6 semaines ; **fait le 17 novembre 2026** (les nouveautés aux abonnés, A.8, faites le même jour avec le chantier 1) |
| 6 | **OCD Tickets** | Billets de concerts et d'événements, vendus aussi en live ; QR vérifié une seule fois à l'entrée ; reversement à l'organisateur | Ticket PDF signé et son contrôle à l'entrée, application Événements d'Odoo (gratuite) | 2 à 3 semaines ; **fait le 18 novembre 2026** (modules `ocd_tickets` et `ocd_tickets_whatsapp`) |
| 7 | **Programme et événements** | Programme des lives façon guide télé ; grands événements à plusieurs vendeurs (Tabaski, Noël, Vendredi noir, Saint-Valentin), d'une soirée ou de plusieurs jours, où les vendeurs mettent un prix promo (plan, 3.1) | Fil des lives, page d'un live | 1 à 2 semaines, plus ~1 semaine pour le prix promo ; **fait le 18 novembre 2026** (prix promo dans `ocd_live_shop`, modules `ocd_soirees` et `ocd_soirees_whatsapp`) |
| 8 | **Clips automatiques** | Chaque moment produit d'un replay devient un clip vertical de 30 secondes, avec le lien du produit, à partager sur TikTok, Reels et les statuts ; les clips de chaque produit dans « Mes produits » | Moments du replay notés par la régie, conversion vidéo (ffmpeg) | 2 à 3 semaines ; **fait le 18 novembre 2026** (modules `ocd_clips` et `ocd_clips_whatsapp`, « Le live commence » dans la régie, en-tête vidéo des modèles WhatsApp) |
| 9 | **OCD Express** | Livraison avec code et paiement à la porte pour tous les vendeurs des réseaux sociaux : espace expéditeur (connexion par numéro), colis sans commande de la boutique, suivi pour le destinataire | Livreurs, code de livraison, caisse du soir, reversements, tarifs par zone, messages des colis ; fiche « lieu » (chantier 17) pour l'endroit où le livreur prend les colis | ~5 semaines avec les choix du 18 novembre 2026 (dettes, retours rendus contre un code, colis annoncé au client), plus l'organisation des livreurs ; **fait le 18 novembre 2026** (modules `ocd_express` et `ocd_express_whatsapp`), dans les données de démonstration le même jour |
| 10 | **Points relais** | Boutiques partenaires où retirer son colis ; livraison moins chère ; les magasins des vendeurs qui le veulent (plan, A.6) | Tarifs de livraison, colis, fiche « lieu » (chantier 17) | 2 à 3 semaines, plus les partenaires ; **fait le 19 novembre 2026** (maquette `PointsRelais`) |
| 11 | **Ambassadeurs** | Chacun partage un produit avec son lien personnel et touche une commission quand le colis est livré | Images à partager, reversements, code de livraison, partage d'un produit (chantier 16) | 3 à 4 semaines ; **fait le 19 novembre 2026** (maquette `Ambassadeurs`, modules `ocd_ambassadors` et `ocd_ambassadors_whatsapp`) |

## Phase 3 : de 6 à 12 mois

| # | Chantier | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| 21 | **Vendre plus** | Préparer son prochain live (le choix des produits pour la régie), alerte de stock bas, tailles et couleurs choisies par le vendeur dès la création | Plan, 3.2, 3.4, 3.5 | 2,5 à 3,5 semaines ; **fait le 17 novembre 2026** |
| 12 | **OCD Business** | Boutique, colis, WhatsApp et statistiques en formule mensuelle, OCD Express compris. Réservés à la formule : plusieurs lieux et le stock par magasin, l'équipe du vendeur, les statistiques détaillées, les nouveautés chaque semaine ; ce qui fait vendre reste pour tous | Le pass de l'annuaire (30 jours prépayés, rappel, renouvellement) : Odoo Community n'a pas d'abonnements ; l'interrupteur « Formule Business » (chantier 17) | ~2 semaines, après OCD Express et les statistiques ; **fait le 19 novembre 2026** (maquette `OcdBusiness`, modules `ocd_business` et `ocd_business_whatsapp`) |
| 22 | **Équipe du vendeur** | La vendeuse d'un magasin a son propre accès, limité au stock et aux commandes de son magasin | Plan, A.9 ; connexion par lien ou code WhatsApp | 1 à 2 semaines, avec le chantier 12 ; **fait le 17 novembre 2026** |
| 13 | **Diaspora** | « Acheter pour un proche » : payer en euros par carte, livrer au pays, code de livraison envoyé au proche ; ou retrait en magasin par le proche, avec son code | Devises par pays, paiement par carte, livraison avec code, retrait en magasin (chantier 20) | 2 à 3 semaines |
| 14 | **Live sur la plateforme** | Lecteur vidéo sur le site avec les produits, le chat et l'achat ; le même live diffusé en même temps sur TikTok, Facebook et YouTube | Page d'un live, régie, produits préparés pour le live (chantier 21) | ~6 semaines, plus un service vidéo payé à la minute |

## Appels WhatsApp (chantier 23, ajouté le 20 novembre 2026)

Les clients appellent OCD Live depuis WhatsApp, sur le numéro des messages ; l'équipe décroche dans
Odoo. Solution retenue : un serveur d'appels FreeSWITCH entre Meta et l'équipe (la plus robuste, voir
`DECISIONS.md`). Le détail, les essais et les seuils pour ouvrir : [`APPELS_WHATSAPP.md`](APPELS_WHATSAPP.md).

| # | Étape | Ce que c'est | Effort |
|---|---|---|---|
| 23.0 | **Préalables** (équipe) | Limite d'envoi du numéro de 2 000 par jour ou plus, droits et réglages chez Meta (`APPELS_WHATSAPP_META.md`), serveur avec IP fixe et Docker, certificat, messages enregistrés | Quelques jours ; **à faire** |
| 23.1 | **Les clients appellent OCD** | Module `whatsapp_cloud_call` et serveur d'appels : réglages chez Meta depuis Odoo, file d'attente, conseiller coupé qui récupère l'appel, messagerie dans la conversation, téléphone dans la barre du haut, historique, surveillance, relais TURN | ~3 semaines ; **fait le 20 novembre 2026** ; en Docker et vu de bout en bout avec un faux Meta le 21 novembre ; reste le vrai serveur et le vrai Meta |
| 23.2 | **OCD appelle les gens** | Accord du client, rappeler un appel manqué ou coupé, l'animatrice qui appelle le vendeur ; payant à la minute, avec tarifs, budget par mois et durée maximale. Le livreur qui appelle par le numéro d'OCD : abandonné (coût) | ~2 semaines ; accord, rappel et coût **faits le 23 novembre 2026** ; reste l'animatrice |
| 23.3 | **La qualité** | Enregistrement annoncé, voix off d'attente, chiffres des appels sur le tableau de bord, transfert à un collègue, deuxième serveur | ~2 semaines ; enregistrement et voix off **faits le 23 novembre 2026** |

## Messages WhatsApp : améliorations (chantier 24, proposé et fait le 25 novembre 2026)

Déjà fait les 24 et 25 novembre 2026 (modules `whatsapp_cloud` 20.0.2.16.0, `ocd_live_whatsapp`
20.0.1.11.0) : conversations disposées comme dans WhatsApp (client à gauche, équipe à droite, avis
et notes au centre), fichiers lus sur place (sons, vidéos, images, documents) dans Discuss et dans la
boîte de réception d'OCD Live, appels dans la boîte de réception (Rappeler, Écouter l'enregistrement,
Appeler, Demander l'accord), notes internes à tout moment, modèle de relance proposé d'abord (réglage
« Modèle de relance » du compte), « Envoyer un modèle » en bas de la conversation.

| # | Étape | Ce que c'est | Où | Effort |
|---|---|---|---|---|
| 24.1 | **Les modèles dans une langue absente chez Meta** (fiabilité, d'abord) | Un client anglophone reçoit la version anglaise d'un modèle même quand Meta ne la connaît pas : erreur #132001 (« Template name does not exist in the translation »), le client ne reçoit rien (vu le 24 novembre avec `ocd_soiree_invitation`). Sur cette erreur : renvoyer aussitôt le message dans la langue principale du modèle, marquer la version comme absente chez Meta (ne plus la choisir tant qu'elle n'est pas synchronisée), lister sur le compte les versions à créer chez Meta | `whatsapp_cloud` : `whatsapp.template._get_lang_version`, envoi et erreurs dans `whatsapp_message.py` (`ERROR_HELP` de `const.py`), santé du compte | 2 à 3 jours ; **fait le 25 novembre 2026** (`whatsapp_cloud` 20.0.2.17.0, `ocd_live_whatsapp` 20.0.1.12.0) |
| 24.2 | **Prévenir avant la fin des 24 h** (coût) | Répondre dans les 24 h est gratuit, après il faut un modèle payant. Le temps restant dans la conversation et la liste (« encore 2 h 15 ») ; une alerte au conseiller (puis aux responsables) une heure avant la fermeture pour un client qui attend une réponse | `whatsapp_channel_valid_until` de `discuss.channel`, tâche « remind the conversations waiting for an answer », en-tête de la conversation (Discuss et boîte de réception) | 2 jours ; **fait le 25 novembre 2026** (`whatsapp_cloud` 20.0.2.18.0, `ocd_live_whatsapp` 20.0.1.13.0) |
| 24.3 | **La boîte de réception d'OCD Live complète** (usage) | Envoyer des fichiers (photo, PDF, vocal), « Prendre » et « Marquer résolu », chercher par nom ou numéro, plus de 80 conversations (charger la suite), sur téléphone le panneau du contact (appels) en onglet | `ocd_live_whatsapp` : `ocd.whatsapp.inbox` (`LIST_LIMIT`, `ocd_post`), `static/src/inbox/` ; actions `whatsapp_action_take` / `whatsapp_action_resolve` de `whatsapp_cloud` | 1 semaine ; **fait le 25 novembre 2026** (`ocd_live_whatsapp` 20.0.1.14.0) |
| 24.4 | **Les chiffres des conversations** (pilotage) | Délai de première réponse, conversations par conseiller, en attente, temps de résolution, modèles envoyés (payés) par mois ; sur le tableau de bord, comme les seuils des appels | `whatsapp_cloud` (calcul), `ocd_live_whatsapp` (tableau de bord `ocd.live.dashboard`) | 3 à 4 jours ; **fait le 25 novembre 2026** (`whatsapp_cloud` 20.0.2.19.0, `whatsapp_cloud_call` 20.0.1.13.0, `ocd_live_whatsapp` 20.0.1.15.0) |
| 24.5 | **Les messages vocaux** (confort) | Un vocal enregistré dans Odoo (MP3) arrive chez le client comme un fichier audio, pas comme une note vocale (il faut du OGG Opus) ; les notes vocales des clients (OGG) ne se lisent pas sur d'anciens iPhone (Safari). Convertir à l'envoi et à la réception, avec ffmpeg sur le serveur d'Odoo (à vérifier d'abord) | `whatsapp_cloud` : envoi des médias (`MEDIA_TYPE_BY_MIMETYPE`), réception (`_download_media`) | 2 à 3 jours ; **fait le 25 novembre 2026** (`whatsapp_cloud` 20.0.2.20.0) |

## OCD sur téléphone : épuré, compact, intuitif (chantier 25, demandé et fait le 25 novembre 2026)

Retour de l'équipe, captures du téléphone à l'appui : beaucoup d'écrans, de l'équipe comme du site,
sont trop grands, chargés et peu intuitifs sur un téléphone (colonnes coupées, listes écrasées à
deux lignes, détail sous la liste, bulles de discussion d'Odoo par-dessus les boutons, « Chargement… »
qui revient sans cesse). Règle pour tous les écrans sur un téléphone : une chose à la fois (des
onglets ou des sections qui s'ouvrent, comme dans WhatsApp), la page qui défile en entier (jamais
une carte coupée à la hauteur de l'écran), le détail qui monte du bas ou prend l'écran avec ←, des
tailles de téléphone (titres 17 px, boutons de 32 à 40 px).

| # | Étape | Ce que c'est | Où | Effort |
|---|---|---|---|---|
| 25.1 | **Le socle commun** | Les bulles des discussions d'Odoo cachées sur téléphone (les conversations restent dans le menu de la barre) ; les rafraîchissements automatiques sans « Chargement… » ; l'en-tête des écrans compact (titre d'abord) | `ocd_live/static/src/backend/theme.scss`, `regie.js`, `inbox.js`, `screen.js` des clips | 1 jour ; **fait le 25 novembre 2026** |
| 25.2 | **Les écrans de l'équipe montrés** | Conversations (une conversation à la fois, le modèle après 24 h dans une carte), Dispatch (une étape à la fois, en onglets), Réservations (un jour à la fois, le créneau en panneau du bas), À vérifier (une colonne ouverte à la fois), Régie (la page défile, rien n'est coupé) | `ocd_live_whatsapp`, `ocd_live_shop` (dispatch, régie), `ocd_live` (planning, vérification) | 2 jours ; **fait le 25 novembre 2026** |
| 25.3 | **Les autres écrans de l'équipe** | Commandes et Automatisations (la liste en entier, le détail en plein écran avec ←), tableau de bord, livreurs, paramètres, fiches (vendeur, colis) et listes d'Odoo, recrutement | `ocd_live_shop` (commandes), `ocd_live` (automatisations, paramètres) | 2 à 3 jours ; **fait le 25 novembre 2026** (les listes et fiches d'Odoo tiennent déjà sur un téléphone ; le recrutement reste à revoir avec des candidatures) |
| 25.4 | **Le site : accueil, lives, shop** | Moins grand et plus épuré : en-têtes, cartes de l'accueil, pays et catégories, « Je suis en live », cartes des lives et des produits | `ocd_live`, `ocd_live_shop` (site) | 3 jours ; **fait le 25 novembre 2026** (tailles de téléphone pour tout le site) |
| 25.5 | **Les autres pages du site, et un contrôle automatique** | Fiche produit, panier, réservation, Mon espace, pages des modules ; `tools/captures/mise-en-page.js` étendu aux écrans de l'équipe sur un téléphone (rien de coupé, rien de plus large que l'écran) | tous les modules du site | 3 à 4 jours ; **fait le 25 novembre 2026** : 88 sortes de pages parcourues à 450 px (visiteur, vendeur, livreur, magasin, ambassadeur, Express), titres de 26 px partout, barre du bas plus basse, « Je suis en live » dans la barre du haut, la carte d'un live allégée ; le contrôle automatique couvre les écrans de l'équipe et les pages du site sur un téléphone (310 contrôles). L'espace du point relais (connexion par code) reste à voir sur un vrai téléphone |

## Charge

Avec les chantiers ajoutés le 16 novembre, le développement passe d'environ 37 à 63 semaines :
environ 15 en phase 1 (prévue sur 2 mois), 32 en phase 2, 15 en phase 3. À temps de développement
égal, le tout demande 14 à 15 mois au lieu de 12. Pour tenir 12 mois : plus de temps de
développement, ou repousser des chantiers sans lien avec l'espace vendeur (OCD Vote, OCD Tickets).

## Décisions à prendre

- **OCD Vote** : choix validés le 17 novembre 2026 avec la maquette (voir `DECISIONS.md`). Reste à
  vérifier avant d'ouvrir dans un pays : le cadre légal des votes payants (ne pas être assimilé à une
  loterie).
- **Paiement dans l'UEMOA** : CinetPay et Flutterwave choisis le 18 novembre 2026, le code est prêt.
  Reste à ouvrir les deux comptes (documents de l'entreprise), saisir leurs clés, les publier, puis
  cocher « Live » après un premier paiement réel.
- **OCD Express** : choix validés le 18 novembre 2026 avec la maquette (voir `DECISIONS.md`) : le prix
  (1 000 F dans Douala, 1,5 % pour encaisser, revu après 4 semaines avec le coût réel), les règles des
  espèces, les livreurs actuels de Douala à 20 colis par jour. Reste à faire avant d'ouvrir au public :
  vérifier avec un juriste les règles des services de paiement de la CEMAC et la loi sur les données
  personnelles ; un numéro WhatsApp à part pour OCD Express. Le code est prêt (18 novembre 2026).
- **OCD Business** : choix validés le 19 novembre 2026 avec la maquette (voir `DECISIONS.md`) :
  10 000 F par mois, 27 000 F pour 3 mois, 100 000 F pour 12 mois, sans commission plus basse, OCD
  Express compris, 2 mois offerts au lancement. Le code est prêt (19 novembre 2026). Reste à l'équipe :
  choisir le jour du lancement (Paramètres › OCD Business), revoir le prix après un essai avec 5 à 10
  vendeurs.
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
- OCD Express : colis par jour, coût de livraison par colis, colis par livreur et par jour, part des
  colis confirmés par le client, taux de retour.
- OCD Vote : voix et montant par concours. OCD Tickets : billets vendus par événement.
- Espace vendeur : délai de vérification d'un produit, part des produits refusés et leurs motifs,
  vendeurs avec au moins un magasin vérifié, itinéraires et appels par magasin, retraits en magasin
  par semaine, part des mises de côté qui finissent en achat, clients en attente d'un produit épuisé.
