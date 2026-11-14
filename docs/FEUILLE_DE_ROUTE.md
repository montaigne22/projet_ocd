# Feuille de route d'OCD Live

Périmètre retenu avec l'équipe le 14 novembre 2026 : vendre ce qu'OCD a déjà construit à d'autres
clients (OCD Express, OCD Business, OCD Tickets), OCD Vote, et une sélection d'améliorations de
l'application. L'ordre ci-dessous est celui proposé ; l'avancement se suit dans
[`PROGRESSION.md`](PROGRESSION.md).

## Phase 1 : de 0 à 2 mois, rapide et avec ce qui existe déjà

| # | Chantier | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| 1 | **Suivre un vendeur** | « Awa est en live maintenant » sur WhatsApp, à chaque live du vendeur suivi | « Préviens-moi » de la boutique, messages WhatsApp | ~1 semaine |
| 2 | **Garantie OCD et avis** | La garantie rendue visible (l'argent n'est versé au vendeur qu'après le code de livraison), les avis des acheteurs sur les boutiques et les cartes du fil, le badge « Vendeur vérifié » | Notes demandées après la livraison, code de livraison, vérification des vendeurs | 1 à 2 semaines |
| 3 | **Statistiques du vendeur** | Dans son espace : vues, clics et ventes par live, meilleures heures, clients fidèles | Espace vendeur, commandes, lives | ~2 semaines |
| 4 | **OCD Vote** | Votes payants en Mobile Money pour des concours (miss, awards, talents, écoles) : page du concours, candidats avec leur numéro, vote sur la page ou par WhatsApp (« VOTE 12 »), classement en direct, bandeau pour le live de la finale, reversement à l'organisateur. Seules les voix payées comptent, chacune liée à son paiement. | Paiements (CamPay, mode démo), reversements, WhatsApp, page d'un live | 3 à 4 semaines |
| 5 | **Paiement automatique dans l'UEMOA** | T-Money, Flooz, Orange Money, Wave… par un agrégateur (CinetPay, FedaPay ou PayDunya), à la place du Mobile Money vérifié à la main par l'équipe | Formulaire de paiement d'Odoo, reversements | 2 à 3 semaines, après le contrat avec l'agrégateur |

## Phase 2 : de 2 à 6 mois

| # | Chantier | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| 6 | **OCD Tickets** | Billets de concerts et d'événements, vendus aussi en live ; QR vérifié une seule fois à l'entrée ; reversement à l'organisateur | Ticket PDF signé et son contrôle à l'entrée, application Événements d'Odoo (gratuite) | 2 à 3 semaines |
| 7 | **Programme et événements** | Programme des lives façon guide télé ; grandes soirées à plusieurs vendeurs (Tabaski, Noël, Vendredi noir, Saint-Valentin) | Fil des lives, page d'un live | 1 à 2 semaines |
| 8 | **Clips automatiques** | Chaque moment produit d'un replay devient un clip vertical de 30 secondes, avec le lien du produit, à partager sur TikTok, Reels et les statuts | Moments du replay notés par la régie, conversion vidéo (ffmpeg) | 2 à 3 semaines |
| 9 | **OCD Express** | Livraison avec code et paiement à la porte pour tous les vendeurs des réseaux sociaux : espace expéditeur (connexion par numéro), colis sans commande de la boutique, suivi pour le destinataire | Livreurs, code de livraison, caisse du soir, reversements, tarifs par zone, messages des colis | ~4 semaines, plus l'organisation des livreurs |
| 10 | **Points relais** | Boutiques partenaires où retirer son colis ; livraison moins chère | Tarifs de livraison, colis | 2 à 3 semaines, plus les partenaires |
| 11 | **Ambassadeurs** | Chacun partage un produit avec son lien personnel et touche une commission quand le colis est livré | Images à partager, reversements, code de livraison | 3 à 4 semaines |

## Phase 3 : de 6 à 12 mois

| # | Chantier | Ce que c'est | Ce qu'on réutilise | Effort |
|---|---|---|---|---|
| 12 | **OCD Business** | Boutique, colis, WhatsApp et statistiques en formule mensuelle, OCD Express compris | Le pass de l'annuaire (30 jours prépayés, rappel, renouvellement) : Odoo Community n'a pas d'abonnements | ~2 semaines, après OCD Express et les statistiques |
| 13 | **Diaspora** | « Acheter pour un proche » : payer en euros par carte, livrer au pays, code de livraison envoyé au proche | Devises par pays, paiement par carte, livraison avec code | 2 à 3 semaines |
| 14 | **Live sur la plateforme** | Lecteur vidéo sur le site avec les produits, le chat et l'achat ; le même live diffusé en même temps sur TikTok, Facebook et YouTube | Page d'un live, régie | ~6 semaines, plus un service vidéo payé à la minute |

## Décisions à prendre

- **OCD Vote** (choix proposés, à confirmer) : concours créés par des organisateurs et par OCD ;
  100 F la voix, packs de 10 voix à 900 F et de 50 voix à 4 000 F ; 60 % pour l'organisateur et 40 %
  pour OCD ; pas de voix gratuites. À vérifier : le cadre légal des votes payants dans chaque pays
  (ne pas être assimilé à une loterie).
- **Paiement dans l'UEMOA** : choisir l'agrégateur, puis signer son contrat (documents de
  l'entreprise) : à lancer dès maintenant.
- **OCD Express** : nombre de livreurs, tarifs pour les expéditeurs, règles des espèces.
- **Live sur la plateforme** : budget du service vidéo.

## Écarté le 14 novembre 2026

Studio et agence, acheter pendant le live (numéros des produits, page « Je prends »), intelligence
artificielle, et les nouveaux concepts à part entière (La Fabrique, Battle des vendeurs, etc.).

## Ce qu'on mesure

- Lives : part des spectateurs qui achètent, panier moyen, clients qui rachètent sous 30 jours.
- OCD Express : colis par jour, coût de livraison par colis.
- OCD Vote : voix et montant par concours. OCD Tickets : billets vendus par événement.
