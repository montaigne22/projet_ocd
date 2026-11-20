# Progression du projet OCD Live

Ce fichier est mis à jour à chaque évolution. Le plus récent est en haut.

## Où en est le projet (20 novembre 2026)

| Domaine | État |
|---|---|
| Réservations de lives (créneaux, paquets, crédits, liste d'attente, déplacement, prix selon l'heure) | ✅ fait, testé |
| Ticket du live en PDF signé (vérifié à l'entrée, une seule fois), image pour annoncer son live | ✅ fait, testé |
| Heures dans le fuseau horaire de chacun (vendeur, livreur, client) | ✅ fait, testé |
| 112 pays proposés (Afrique entière, principaux d'Europe, d'Amérique, d'Asie), numéros de tous les pays | ✅ fait, testé |
| Fil des lives façon TikTok : pays de la personne d'abord, défilement infini, jamais vide | ✅ fait, testé |
| Cartes du fil claires et épurées ; média au choix du vendeur : vidéo courte, carrousel de ses produits ou image | ✅ fait, testé |
| Plateformes de live configurables (TikTok, Facebook, Instagram, YouTube, et celles que l'équipe ajoute) | ✅ fait, testé |
| Comptes de live d'OCD Live (plusieurs : par pays, studio, à distance), choisis pour chaque live | ✅ fait, testé |
| Live à distance : le vendeur invité sur le compte d'OCD (appel de l'animatrice, WhatsApp « Rejoindre mon live », alerte s'il n'est pas prêt) | ✅ fait, testé (modèles WhatsApp à faire approuver par Meta) |
| Paiement par carte (Stripe, clés à saisir) ; aide de l'équipe quand aucun moyen ne convient | ✅ fait, testé |
| Photos des produits : visionneuse, photo par couleur, galerie ; « Préviens-moi » au retour en stock | ✅ fait, testé |
| Replay lu dans la page (YouTube, TikTok, Facebook), saut au moment d'un produit | ✅ fait, testé |
| Paiement : formulaire d'Odoo, tous les fournisseurs configurés par pays, devise par pays | ✅ fait, testé |
| Devises par pays : XOF (UEMOA), XAF (CEMAC, CamPay), EUR (Europe, reste de l'Afrique), USD (Amériques, Asie, Océanie) ; conversion automatique arrondie, dollar du jour | ✅ fait, testé (bouton à cliquer dans les Paramètres) |
| Paiements de démo CamPay : 25 F CFA encaissés au lieu du prix, pour tous ou pour des numéros, jusqu'à un dernier jour | ✅ fait, testé |
| Annuaire des lives (pass, envoi du lien, vérification par créneau, statut) | ✅ fait, testé |
| Espace vendeur sans mot de passe (lien ou code WhatsApp) | ✅ fait, testé |
| « Moi » pour les comptes Odoo connectés : vendeur, équipe (« Voir son espace »), client | ✅ fait, testé |
| Livreurs : leur numéro, puis lien ou code sur WhatsApp, comme les vendeurs ; déconnexion | ✅ fait, testé |
| Site fidèle au design : réservation, annuaire, espace (téléphone, tablette, ordinateur) | ✅ fait |
| Adresse du site (`/`) = accueil d'OCD Live, site en français, logo et pied de page d'OCD sur les pages d'Odoo | ✅ fait, testé |
| Thème du site « OCD Live » (`theme_ocd`) dans le choix des thèmes d'Odoo | ✅ fait, testé |
| Site : toutes les pages du shop fidèles au design (shop, produit, panier, livraison, paiement, suivi, boutique, replay, mes produits, mes colis, tournée) | ✅ fait, testé |
| « Mes produits » fiable (chantier 15) : stock − / + qui garde les pièces des commandes, prix lu ou refusé, formulaire pour réseau lent (photo gardée, réduite, un seul envoi), galerie, refus expliqué et produit corrigé puis renvoyé, voix de la page | ✅ fait, testé (3 modèles WhatsApp à faire approuver par Meta) |
| « Mes produits » aide à vendre (chantier 16) : contacts WhatsApp et clients en attente, menu « Plus », ordre de la boutique, copie, filtres, partage d'un produit avec son image, catalogue pour le statut, démarrage du vendeur | ✅ fait, testé |
| Magasins des vendeurs (chantier 17) : magasin vérifié ou « je vends depuis chez moi », horaires et « ouvert maintenant », itinéraire, appeler, WhatsApp, visites comptées, affiche QR et étiquettes de prix, magasin de départ des colis, interrupteur OCD Business, back-office et vérification | ✅ fait, testé (2 modèles WhatsApp à faire approuver par Meta) |
| Stock par magasin (chantier 18) : un emplacement par lieu, « Mon stock » avec les tailles et les couleurs, envoyer des pièces d'un magasin à l'autre, le magasin qui sert chaque commande (un colis par magasin si besoin), disponibilité par magasin sur la fiche produit, « Préviens-moi » qui nomme les magasins | ✅ fait, testé (1 modèle WhatsApp à faire approuver par Meta) |
| Gérer ses produits (chantier 19) : modifier un produit en vente (vérifié pendant que la version d'aujourd'hui reste en vente, prix tout de suite, grand écart confirmé, historique des prix), plusieurs photos, retirer de la vente et remettre, produit gardé dans le téléphone sans réseau | ✅ fait, testé (1 modèle WhatsApp à faire approuver par Meta) |
| Autour des magasins (chantier 20) : mode vacances, vendeurs près de chez moi, le bot WhatsApp donne les magasins, retrait en magasin (payé au comptoir, code après l'argent), mettre de côté pour essayer | ✅ fait, testé (8 modèles WhatsApp à faire approuver par Meta) ; les nouveautés aux abonnés (A.8) attendent le chantier 1 |
| Vendre plus (chantier 21) : préparer son prochain live (les produits pour la régie, dans l'ordre du vendeur), alerte de stock bas sur WhatsApp, tailles et couleurs dès la création | ✅ fait, testé (le WhatsApp est le modèle `ocd_stock_bas`, soumis à Meta le 16 novembre) |
| Équipe du vendeur (chantier 22) : la personne qui tient un magasin a son espace « Mon magasin » (connexion par son numéro, lien ou code), le stock de son magasin sans les prix, ses colis, retraits au comptoir et pièces à essayer, sans les reversements ; « Mon équipe » du vendeur (5 au plus, OCD Business, en pause sans rien supprimer) ; onglet « Équipe » du back-office | ✅ fait, testé (3 modèles WhatsApp à faire approuver par Meta) |
| Suivre un vendeur (chantier 1) et ses nouveautés (A.8) : « Suivre » sur la boutique, les cartes des lives, le replay et la fiche produit ; un WhatsApp à chaque live (2 par jour au plus) ; les nouveautés le vendredi (une fois par mois, chaque semaine avec OCD Business) ; « Mes vendeurs suivis » ; « Mes abonnés » du vendeur | ✅ fait, testé (1 modèle WhatsApp Marketing à faire approuver par Meta) |
| Garantie OCD et avis (chantier 2) : la garantie montrée sur la fiche produit et la boutique (le vendeur payé après le code de livraison, pas livré : remboursé, retour possible), un avis par colis livré, la note du vendeur dès 3 avis, « Vendeur vérifié », « Signaler » un produit ou un vendeur vers « À vérifier » | ✅ fait, testé |
| Statistiques du vendeur (chantier 3) et ventes par produit (3.3) : « Mes chiffres » (ventes, pièces, visites de la boutique, contacts WhatsApp et leur évolution sur 7 jours, 30 jours ou 3 mois ; ce que rapporte chaque live ; meilleures heures et « Réserver un live » ; clients fidèles ; ventes par produit avec « Pas vendus » ; magasins), la ligne « Vendu » de Mes produits, les ventes du mois dans Mon espace, le résumé du lundi sur WhatsApp ; nouveaux comptages jour par jour (« Regarder », visites, contacts) | ✅ fait, testé (1 modèle WhatsApp à faire approuver par Meta) |
| OCD Vote (chantier 4) : concours avec candidats numérotés, voix payées en Mobile Money (seules les voix payées comptent, chacune liée à son paiement), vote sur la page ou par WhatsApp « VOTE 12 », classement en direct, bandeau de la finale, résultats certifiés, espace de l'organisateur, reversement | ✅ fait, testé (2 modèles WhatsApp à faire approuver par Meta) |
| OCD Tickets (chantier 6) : billets de concerts et d'événements (application Événements d'Odoo), page de l'événement, achat (places gardées pendant le paiement), « Mes billets » (un QR signé par personne, PDF, « Donner ce billet »), contrôle à l'entrée avec le téléphone (même hors réseau), vente à l'entrée, billet à l'écran pendant un live avec son prix du live, annulé ou déplacé, espace de l'organisateur et ses contrôleurs, reversement | ✅ fait, testé (5 modèles WhatsApp à faire approuver par Meta) |
| Programme et événements (chantier 7) et prix promo (3.1) : « Mettre en promo » dans Mes produits (prix barré = le plus bas des 14 derniers jours, jusqu'à une date, partout le même prix) ; le programme des lives des 7 prochains jours (guide télé sur ordinateur) ; les grands événements d'une soirée ou de plusieurs jours (Vendredi noir, Tabaski…) où les vendeurs invités participent avec un live et leurs promos, vérifiées par l'équipe, « Me prévenir sur WhatsApp » | ✅ fait, testé (2 modèles WhatsApp à faire approuver par Meta) |
| Clips automatiques (chantier 8) : chaque produit montré dans un live devient un clip vertical de 30 secondes avec son lien court, à partager sur les statuts, TikTok et Reels ; la vidéo du live envoyée par l'équipe par morceaux, vérifiée ; « Mes clips » du vendeur, « Vu en live » sur la fiche produit et le replay, visites et ventes de chaque clip | ✅ fait, testé (2 modèles WhatsApp à faire approuver par Meta) |
| OCD Express (chantier 9) : la livraison avec code pour tous les vendeurs des réseaux, sans boutique ; connexion par numéro, « Nouveau colis » (accord du client, montant ou valeur, qui paie la livraison, ouvrir avant de payer, ramassage ou point OCD), deux vagues et capacité, un passage de ramassage par expéditeur (photo, « pas pris », expéditeur absent), page de suivi du client (code, « Je confirme », « Pas là ? », position, souci 48 h, « Ce n'est pas pour moi »), retours rendus contre un code, « Mon argent » (versé le jour ouvré suivant une fois l'argent chez OCD, dettes plafonnées, nouveau numéro retenu 48 h), plafonds et vérifications dans « À vérifier », clients effacés après 6 mois ; manque de caisse des livreurs en dette | ✅ fait, testé (6 modèles WhatsApp à faire approuver par Meta, sur un numéro à part) |
| Points relais (chantier 10) : « En point relais » à la livraison du shop (moins cher qu'à la porte, les points relais ouverts et pas pleins de la ville), la page du client (code et QR de retrait, jusqu'à quand, itinéraire, « livrez-la chez moi »), « Mon point relais » (connexion par numéro, colis gardés sur ses places, gains du mois, congé, recevoir en comptant chaque colis, remettre contre le code ou le QR, payé avant ou sur le téléphone du client, jamais en espèces), l'arrêt du livreur (déposer, reprendre les colis pas retirés), 7 jours puis retour, 150 F par colis remis versés chaque mois, colis perdu remboursé et retenu, pause après 2 pertes ; la page `/points-relais` pour devenir partenaire, le magasin vérifié d'un vendeur point relais (A.6) ; OCD Express au point relais (choisi par l'expéditeur ou par le client) ; back-office, « À vérifier », réglages | ✅ fait, testé (4 modèles WhatsApp à faire approuver par Meta, et 1 sur le numéro d'OCD Express) |
| Ambassadeurs (chantier 11) : chacun partage un produit avec son lien personnel (`/a/<code>`) et gagne 5 % des articles une fois le colis livré avec son code et gardé, payés par OCD sur sa commission (le client paie le même prix, le vendeur rien) ; inscription par numéro vérifié, « Mon espace ambassadeur » (ventes et leur état), « Mon argent » (versé chaque lundi dès 2 000 F, nouveau numéro retenu 48 h), « Produits à partager », « Partager » (image au prix du moment avec le lien, texte, statut WhatsApp, clip du live), « Mes liens » ; « Grâce te recommande ce produit » ; un gain par colis, une facture à la confirmation, un avoir pour un retour ; contre la fraude : jamais sur ses propres achats, 5 commandes d'un client par mois, pause au-delà de 30 % de retours, un Mobile Money par personne, pièce d'identité au-delà de 50 000 F ; « Vendu grâce aux ambassadeurs » dans Mes chiffres ; back-office, « À vérifier », réglages | ✅ fait, testé (3 modèles WhatsApp à faire approuver par Meta) |
| OCD Business (chantier 12) : la formule des vendeurs organisés (plusieurs magasins et leur stock, leur équipe, leurs chiffres en détail, leurs nouveautés chaque semaine, OCD Express avec compte ouvert tout de suite et petit ramassage gratuit), 1, 3 ou 12 mois payés d'avance avec le paiement d'OCD Live, jamais prélevés ; des périodes (payées, offertes par l'équipe avec un motif, offertes au lancement), une par paiement, la date de fin calculée, jamais tapée, aucun jour perdu ; une facture par paiement ; le Mobile Money vérifié par l'équipe garde les fonctions 3 jours après « J'ai payé » ; un remboursement reprend les jours pas passés ; rappels 7 jours avant et la veille ; à la fin, rien n'est effacé et le magasin de départ des colis reste visible ; le lancement offre 2 mois aux vendeurs qui utilisent les fonctions ; « OCD Business » dans Mon espace, chaque fonction gardée y mène, la page `/business` pour les commerçants ; back-office et réglages | ✅ fait, testé (4 modèles WhatsApp à faire approuver par Meta) |
| Paiement automatique dans l'UEMOA (chantier 5) : CinetPay (module `payment_cinetpay` : Mobile Money, Wave, carte ; UEMOA, Cameroun, Guinée, RD Congo) et Flutterwave (module d'Odoo) ; l'état lu chez CinetPay, revérifié toutes les 10 minutes ; le Mobile Money vérifié par l'équipe s'efface devant un Mobile Money automatique en production ; clés manquantes et mode test dits dans les Paramètres | ✅ fait, testé (clés des comptes à saisir) |
| Tout le site sur tablette et ordinateur : la largeur de l'écran utilisée (listes en grilles, fiches en deux colonnes, parcours avec récapitulatif à droite, espaces avec leur menu à gauche) ; le téléphone inchangé | ✅ fait, testé |
| Frais de livraison selon le vendeur : un prix par colis, de la ville du vendeur au quartier du client | ✅ fait, testé |
| Shop : un colis par vendeur, code de livraison, dispatch, caisse des livreurs, reversements | ✅ fait, testé |
| Back-office fidèle au design : barre, onglets, tableau de bord, réservations, régie, à vérifier, commandes, dispatch, fiche livraison, livreurs et caisse, fiche vendeur, reversements, recrutement | ✅ fait |
| Outils Odoo utilisés : dans la documentation ([`OUTILS_ODOO.md`](OUTILS_ODOO.md)), pas dans le système | ✅ fait |
| Back-office : paramètres à sections, catalogue des automatisations, conversations WhatsApp, fidèles au design | ✅ fait, testé |
| WhatsApp : tous les messages des lives, de l'annuaire et des colis, un seul accord, messages demandés toujours envoyés | ✅ fait, testé |
| Aucune mention d'Odoo pour l'équipe, les vendeurs et les clients (site, back-office, erreurs, e-mails) | ✅ fait, testé |
| Recrutement des animatrices (offre sur le site, 5 étapes, embauche) | ✅ fait, testé |
| Togo (villes, quartiers, livraison) | ✅ fait |
| Données de démonstration désinstallables, qui remplissent tous les écrans (photos, variantes, stock, colis à chaque étape, reversements, OCD Express) ; installées en une fois avec les modules, avec leurs factures et reversements | ✅ fait, testé |
| Démo de présentation tenue à jour : 15 vendeurs dans 8 pays, lives en cours, semaine du studio, replays, boutique de Douala heure par heure (colis, caisse, reversements, WhatsApp), OCD Express (Nadège Mode : ses colis à chaque étape, deux passages par jour, un retour, un souci, son argent versé chaque jour ouvré ; une demande à vérifier), magasins, équipe, retrait au magasin, point relais, ventes des lives, avis, abonnés, promo, signalement, chiffres sur 90 jours ; quand ils sont installés : formules OCD Business, une ambassadrice et ses gains, Vendredi wax, clips, un concours OCD Vote, un concert et ses billets ; scénario ([`DEMO.md`](DEMO.md)) ; aucun WhatsApp vers ses contacts | ✅ fait, testé |
| Traductions françaises de tous les modules, descriptions longues comprises | ✅ faites (à compléter à chaque nouvel écran) |
| Grand public : pages publiques gardées en mémoire quelques secondes, photos et vidéos par un CDN, questions répétées des pages réduites ; modèle de rapport de charge ([`RAPPORT_DE_CHARGE.md`](RAPPORT_DE_CHARGE.md)) | ✅ fait, testé (à mesurer sur les vrais serveurs) |

Derniers tests lancés (12 novembre 2026, base neuve, tous les modules OCD sauf la démo, avec
`ocd_debranding`, plus les tests de `whatsapp_cloud` et `whatsapp_cloud_sale`) : **354 tests, un seul
échec, connu** (« commande confirmée puis expédiée » de `whatsapp_cloud_sale` : OCD remplace ce message par
ceux des colis). Nouveaux tests des cartes, des plateformes, des comptes et des lives à distance : 24 sans échec. Sur
une base neuve avec la démo, 17 tests sans échec : la démo remplit les écrans et se
tient à jour (semaine du studio, annuaire fenêtre par fenêtre, fil de chaque pays, paiement à vérifier,
journée de la boutique heure par heure, le lendemain, rien ne s'empile), prend la vidéo et le compte des
paramètres, aucun WhatsApp ne part vers ses contacts, puis elle se désinstalle sans rien laisser.
Devises par pays et paiements de démo CamPay (12 novembre) : tests d'OCD sur la base de test, 286 sans
échec ; sur une base avec CamPay, 63 tests (CamPay, devises, paramètres, frais de livraison) sans échec ;
démo, 15 tests sans échec (devises de Brenda, Kadi et Awa comprises).
Pages en mémoire, médias à part (15 novembre) : tous les tests d'OCD sauf la démo, avec WhatsApp et
CamPay, **391 sans échec** (dont 9 nouveaux pour la mémoire des pages, 3 pour la boutique, le shop et
les paramètres) ; démo, 17 sans échec.

## Reste à faire, par priorité

Les nouveaux chantiers retenus le 14 novembre 2026 (OCD Express, OCD Business, OCD Tickets, OCD Vote et
les améliorations choisies), complétés le 16 novembre par l'espace vendeur (« Mes produits », magasins,
stock par magasin : chantiers 15 à 22, détaillés dans [`PLAN_MES_PRODUITS.md`](PLAN_MES_PRODUITS.md)),
dans leur ordre : [`FEUILLE_DE_ROUTE.md`](FEUILLE_DE_ROUTE.md). Avant eux :

1. **Tarifs à saisir par l'équipe avant l'ouverture**, pas à pas dans [`LIVRAISONS.md`](LIVRAISONS.md)
   (OCD Live › Livraisons › Tarifs de livraison) :
   livreurs OCD par ville, agences vers les autres villes et pays, bornes des prix des vendeurs, part
   d'OCD sur les livraisons des vendeurs, ville du stock, et un tarif « point relais » par ville où des
   points relais ouvrent. Les modes de livraison sans prix ont donné des
   tarifs archivés : les compléter puis les activer. Sans tarif, le shop refuse l'adresse (jamais de
   livraison à un prix inconnu).
2. **WhatsApp chez Meta** (équipe) : connecter le numéro d'OCD Live (WhatsApp › Comptes), puis soumettre
   (le code de connexion est un modèle *Authentification* : Meta en écrit le texte, Odoo envoie le code)
   les modèles depuis Odoo (WhatsApp › Messages automatiques) : tant qu'un modèle n'est pas approuvé, son
   message ne part pas (les Paramètres, section WhatsApp, et les Automatisations le signalent). **Après la
   mise à jour du 12 novembre** : WhatsApp › Modèles, filtre « Refusés ou en pause », tout cocher, Action ›
   « Soumettre à Meta » (les textes refusés pour `INCORRECT_CATEGORY` ont été réécrits). Les
   réponses rapides de l'équipe se créent dans les conversations (`::livreur`, `::retard`…).
   **Depuis le 16 novembre**, aussi : `ocd_produit_accepte`, `ocd_produit_refuse`, `ocd_stock_bas`,
   `ocd_magasin_accepte`, `ocd_magasin_refuse` (français et anglais), pour les messages aux vendeurs sur
   leurs produits et leurs magasins ; et `ocd_produit_de_retour_magasin` (français et anglais), pour
   « Préviens-moi » qui nomme les magasins où le produit est revenu (l'ancien message part jusque-là) ; et `ocd_modification_refusee` (français et anglais), pour une modification de produit
   refusée par l'équipe (rien ne part avant). **Depuis le 17 novembre**, aussi `ocd_resume_semaine`
   (français et anglais, Utilitaire), pour le résumé de la semaine que le vendeur demande dans « Mes
   chiffres » (rien ne part avant). **Avec OCD Vote**, aussi `ocd_vote_comptee` et `ocd_vote_finale`
   (français et anglais, Utilitaire) : les voix comptées au votant, la finale à ceux qui l'ont demandé.
   **Avec OCD Tickets**, aussi `ocd_billets_prets`, `ocd_billets_rappel`, `ocd_billets_annule`,
   `ocd_billets_deplace` et `ocd_billets_controleur` (français et anglais, Utilitaire) : les billets
   payés ou donnés, le rappel la veille, l'événement annulé ou déplacé, le contrôleur ajouté.
   **Avec les grands événements**, aussi `ocd_soiree_invitation` et `ocd_soiree_commence` (français et
   anglais, Utilitaire) : l'invitation des vendeurs, le début annoncé à ceux qui l'ont demandé.
   **Avec les clips automatiques**, aussi `ocd_clips_prets` et `ocd_clip_video` (français et anglais,
   Utilitaire) : les clips d'un live prêts, le clip lui-même avec la vidéo en tête (à soumettre une fois
   un premier clip fait : Meta reçoit sa vidéo en exemple). **Avec OCD Express**, sur le numéro à part
   d'OCD Express (choisi dans le champ « Compte » des modèles), `ocd_express_annonce`,
   `ocd_express_en_route`, `ocd_express_pris`, `ocd_express_etat`, `ocd_express_versement` et
   `ocd_express_numero` (français et anglais, Utilitaire) : le colis annoncé et en route au client, les
   colis pris, les nouvelles d'un colis, le versement fait et le numéro de versement changé à l'expéditeur.
   **Avec les points relais**, aussi `ocd_colis_point_relais`, `ocd_colis_rappel_relais`,
   `ocd_colis_non_retire_relais` et `ocd_relais_arrivage` (français et anglais, Utilitaire) : le colis qui
   attend au point relais, le rappel avant la fin, le colis pas retiré (au client), les colis qui arrivent
   (au point relais) ; et sur le numéro d'OCD Express, `ocd_express_point_relais` (français et anglais).
   **Avec les ambassadeurs**, aussi `ocd_ambassadeur_livres`, `ocd_ambassadeur_versement` et
   `ocd_ambassadeur_numero` (français et anglais, Utilitaire) : les colis partagés livrés du jour, le
   versement fait, le numéro de versement changé (à l'ambassadeur).
   **Avec OCD Business**, aussi `ocd_business_payee`, `ocd_business_fin_proche`, `ocd_business_terminee`
   et `ocd_business_lancement` (français et anglais, Utilitaire) : la formule payée, la fin qui approche
   (7 jours avant et la veille), la fin, les mois offerts au lancement (au vendeur).
3. **Paiement dans l'UEMOA** (équipe) : ouvrir les comptes CinetPay et Flutterwave (documents de
   l'entreprise), saisir leurs clés, publier, faire un premier paiement réel, puis cocher « Live » : pas à
   pas dans [`DEVELOPPEMENT.md`](DEVELOPPEMENT.md) (Paiement dans l'UEMOA). Jusque-là, le Mobile Money
   vérifié par l'équipe reste proposé.
4. **Mise en production** : `list_db = False` dans `odoo.conf` (pas de gestion des bases sur la page
   de connexion), un sous-domaine pour l'équipe si une adresse à la marque est voulue (les adresses du
   back-office gardent `/odoo/`, voir [`DECISIONS.md`](DECISIONS.md)).

## Points d'attention

- Sur un écran de moins de 1 534 px, Odoo met la discussion (chatter) **sous** les fiches et non à droite.
- Les écrans sur mesure du back-office gardent un bouton vers la liste standard d'Odoo (tri, export).
- Odoo 20 n'a plus Font Awesome : les icônes sont celles d'Odoo (`data-icon`).
- Les pages « Paramètres » et « Automatisations » sont pour les responsables d'OCD Live : ils changent les
  réglages et les interrupteurs sans être administrateurs d'Odoo (rien d'autre n'est écrit).
- Le module `disable_odoo_online` de l'OCA est dans `marketplace/oca_server_brand/` : ce dossier doit être
  dans le chemin des modules, `ocd_debranding` en dépend.
- La confirmation d'une commande envoie un PDF : le serveur a besoin du moteur PDF d'Odoo
  (`wkhtmltopdf`), sinon la commande reste « en attente du paiement ».
- Odoo publie au départ sa « Livraison standard » (gratuite, partout) : l'équipe ne publie que les
  modes de livraison d'OCD Live, sinon elle passe avant elles.

## Journal

### 20 novembre 2026 · La démo des modules autour de la boutique : Business, ambassadrice, événements, clips, vote, billets
`ocd_live_demo` 20.0.1.8.0 (migration). Quand ils sont installés, avant ou après la démo
([`DEMO.md`](DEMO.md)) :
- **OCD Business** : la formule payée de Brenda (sa commande, sa facture), un mois offert à Kossi, celle
  de Junior qui finit dans deux jours, celle de Fatou finie ; les dates suivent le jour de la
  présentation.
- **Ambassadeurs** : Grâce Mbia et son lien `GRACE7`, une commande de la boutique sur trois jours qui
  vient d'elle, ses gains confirmés et versés le lundi (Mobile Money, en comptabilité : jamais versé
  deux fois), les visites de ses liens ; Kevin Tchoumi attend l'équipe.
- **Grands événements** : « Vendredi wax » chaque vendredi soir au Cameroun, Brenda acceptée avec ses
  promos, Fatou à vérifier, trois clientes à prévenir ; toujours les deux prochains.
- **Clips** : un clip par produit montré dans chaque replay d'Awa, joué et visité chaque jour.
- **OCD Vote** : « Le meilleur plat de Douala 2026 », quatre plats, des votes payés chaque jour, la fin
  des votes toujours dans onze jours.
- **OCD Tickets** : « Nuit de l'Afrobeat » chaque samedi, en vente deux semaines avant, des billets
  vendus chaque jour, une table complète, un contrôleur à la porte.

Ce que la démo met en place une fois garde l'enregistrement qu'elle a créé (`ocd.live.demo.event`) : la
désinstallation retire ses événements, les formules et les gains de ses contacts. Vérifié à l'écran
(espace de Grâce, « Mon argent », Vendredi wax, OCD Business de Brenda). La suite complète sur une base
neuve : **726 sans échec**, la démo : **25 sans échec** ; la mise à jour d'une démo existante vérifiée
(de 20.0.1.6.0 : magasins, Business et ambassadrice tout de suite, le reste au passage suivant de
l'action planifiée).
**Sur le serveur** : `-u ocd_live_demo` (seulement là où la démo est installée), puis « Exécuter »
l'action planifiée « Démo d'OCD Live » (ou attendre un quart d'heure) pour les événements, le concours,
les concerts et les clips.

### 20 novembre 2026 · La démo montre la boutique en entier : magasins, retrait, point relais, ventes des lives
Ce qui a été livré pour la boutique n'avait pas de données de démo : une présentation montrait des pages
vides. `ocd_live_demo` 20.0.1.7.0 (migration : la mise à jour met tout en place), tenu à jour par l'action
planifiée comme le reste, chaque chose une seule fois, tout retiré à la désinstallation
([`DEMO.md`](DEMO.md)).
- **Magasins et équipe** : Brenda a deux magasins à Douala (Akwa, d'où partent ses colis, et Bonapriso,
  tenu par Aïcha Njoya de son équipe, active chaque matin), ses pièces réparties entre les deux ; Fatou
  vend de chez elle, Kossi a son magasin au Grand Marché de Lomé, celui d'Ama attend l'équipe.
- **Retrait au magasin et point relais** : chaque jour, Hervé retire un pagne au magasin d'Akwa (le code,
  le comptoir le lendemain) ; la chemise de Carine va au point relais **Chez Rose** (Bonamoussadi), qui la
  compte et la remet avec le code, et gagne sa part ; Ruth demande à essayer une robe à Bonapriso, Aïcha
  accepte. **Alimentation Ngo** demande à devenir point relais.
- **Les ventes des lives** : pendant chaque live de Brenda et de Fatou, des visites de la boutique, des
  commandes comptées pour le live (livrées le lendemain) et un abonné : « Mes chiffres » montre la part
  des lives, le meilleur live et le jour où ses lives vendent le plus.
- **La vie de la boutique** : un avis après la plupart des livraisons, qui colle au parcours du colis et au
  produit ; abonnés, « Préviens-moi » sur la robe bleue L, vendeurs vérifiés, un signalement et la promo
  de Brenda chaque semaine, les prochains lives préparés pour l'animatrice, un nom à vérifier, un produit
  refusé, les itinéraires et appels des magasins, 90 jours de visites, contacts et lives ouverts.

La démo active le retrait au magasin, les pièces à essayer et les points relais si l'équipe ne l'a pas fait,
et les remet comme avant à sa désinstallation. Vérifié à l'écran (espace de Brenda, fiche produit, boutique,
« À vérifier »). La suite complète sur une base neuve : **726 sans échec**, la démo : **24 sans
échec**.
**Sur le serveur** : `-u ocd_live_demo` (seulement là où la démo est installée).

### 19 novembre 2026 · Correctif : le menu du bas sur toutes les pages de l'espace
Sur téléphone, « Mes chiffres » (capture de l'équipe) n'avait pas le menu du bas : impossible de revenir à
l'accueil d'un toucher. Seules « Mon espace » et « Ma carte dans le fil » le demandaient, sur 21 pages de
l'espace. Il est maintenant sur chacune, par défaut (une page de l'espace qui ne dit rien l'a) ; une barre
de boutons collée en bas d'une page reste au-dessus de lui. `tools/captures/mise-en-page.js` ouvre chaque
page du menu de l'espace sur téléphone et vérifie qu'elle l'a : toutes les règles tenues. `ocd_live`
20.0.1.28.1 et `ocd_live_shop` 20.0.1.48.2 (un test complété), sans migration ; la suite complète sur une
base neuve : **726 sans échec**, la démo : **22 sans échec**.
**Sur le serveur** : `-u ocd_live,ocd_live_shop`.

### 19 novembre 2026 · « Moi » sur téléphone : toutes les entrées, plus court, plus rien qui se chevauche
Après une remarque de l'équipe. `ocd_live` 20.0.1.28.0 et `ocd_live_shop` 20.0.1.48.1, sans migration.
- **Toutes les entrées sur téléphone** : le menu de l'espace (un seul, chaque module y ajoute sa page)
  était caché sur téléphone, où « Mes clips » et « OCD Business » (hors fin de formule) manquaient. Il
  est maintenant en onglets qui défilent sous l'en-tête, sur chaque page de l'espace ; l'onglet de la
  page ouverte est amené à l'écran.
- **Plus court** : « Mon espace » montrait tous les prochains lives, chacun avec ses boutons (4 700 px de
  haut pour 7 lives). Le prochain et les deux suivants, puis « Voir mes 4 autres lives » (sans
  JavaScript aussi) : 3 600 px, onglets compris.
- **Plus rien qui se chevauche** : le titre « Mon shop » passait sous ses boutons (le bloc n'était pas
  dans le flux de la page). Les montants de « Mes chiffres » ne se coupent plus (« 559 000 FC / FA ») :
  leur taille suit la largeur de la tuile.
- **Contrôle** : `tools/captures/mise-en-page.js` contrôle aussi « Mon espace » avec le lien d'un vendeur
  de la démo (les mêmes entrées à 390, 820 et 1440 px, aucun titre recouvert, aucun montant coupé) : toutes
  les règles tenues. Test : 1 nouveau ; la suite complète sur une base neuve : **726 sans échec**, la
  démo : **22 sans échec**.
- **Sur un serveur** : `-u ocd_live,ocd_live_shop`.

### 19 novembre 2026 · Correctif : une seule carte sur toute la largeur dans la page d'un pays
Sur ordinateur, la page d'un pays (Côte d'Ivoire, capture de l'équipe) étirait sa carte sur toute la
largeur : la règle « une colonne » du téléphone l'emportait aussi sur grand écran. Elle ne vaut plus que
pour le téléphone ; à partir de la tablette, les colonnes du fil (3 cartes de 412 px à 1914 px).
`tools/captures/mise-en-page.js` contrôle maintenant aussi la page d'un pays (aucune carte coupée, aucune
plus large que 640 px) : **88 règles tenues**. `ocd_live` 20.0.1.27.1, sans migration ; la suite complète
sur une base neuve : **725 sans échec**, la démo : **22 sans échec**.
**Sur le serveur** : `-u ocd_live`.

### 19 novembre 2026 · Les cartes sur la page d'un pays, « Cherche ton pays », les catégories dans l'onglet Lives
Demandés par l'équipe en regardant la démo. `ocd_live` 20.0.1.27.0 et `ocd_live_shop` 20.0.1.48.0, sans
migration.
- **La page d'un pays** (`/lives/<pays>`, ouverte par les pays de l'accueil) n'est plus une liste : les
  mêmes cartes que l'onglet Lives (ses lives en cours, au studio, ses prochains lives, ses replays), avec
  ses catégories, « Où ? » et où vend chaque vendeur sur sa carte (« 2 magasins · Akwa », en congé),
  « Programme des lives » du pays, « Je suis en live » en haut sur grand écran. Sous les filtres, les
  cartes sont l'une sous l'autre et la page défile, sur téléphone aussi. « 1 live » au lieu de « 1 lives ».
- **« Cherche ton pays »** sur l'accueil : les pays viennent au fil de la frappe, avec leur drapeau et
  leurs lives, par leur nom sans les accents (« cote » trouve la Côte d'Ivoire), leur nom anglais, leur
  code (CM) ou un nom courant (Ivory Coast, RDC, USA, Dubaï…) ; les flèches choisissent, Entrée ouvre.
  « Tous les pays » ouvre la nouvelle page `/lives/pays` : tous les pays, filtrés à la frappe ; sans
  JavaScript, la recherche y mène (un seul pays trouvé ouvre sa page).
- **Les catégories dans l'onglet Lives**, sous les pays, plus discrètes (la catégorie choisie en
  orange) : les lives d'une catégorie dans tous les pays ; changer de pays garde la catégorie, et les
  cartes chargées en défilant sont de la même catégorie.
- Contrôlé dans le navigateur en français à 390, 820, 1366 × 657 et 1914 px ; `tools/captures/mise-en-page.js` :
  toutes les règles tenues. Tests : 3 nouveaux (la recherche du pays, la page d'un pays avec les cartes, les
  catégories du fil), 1 complété (le programme depuis la page d'un pays) ; la suite complète sur une base
  neuve : **725 sans échec**, la démo : **22 sans échec**.
- **Sur un serveur** : `-u ocd_live,ocd_live_shop`.

### 19 novembre 2026 · Trois écrans qui tiennent à toute taille : le fil des lives, l'accueil, « À vérifier »
Après des captures de l'équipe : ces écrans grandissent avec les données (les pays, les lives, une
colonne de plus à chaque chantier), et leur mise en page cassait sur grand écran. Reproduits sur la démo,
corrigés dans `ocd_live` (20.0.1.26.0, sans migration : seuls les écrans changent). Le téléphone ne change
pas.
- **Le fil des lives** sur tablette et ordinateur : sur un portable (1366 × 657), la boîte du fil faisait
  406 px de haut pour des cartes de 540 : noms et boutons coupés, deux défilements l'un dans l'autre.
  Maintenant la page défile (le script suit la page : lives suivants, vidéo, pays de la barre) ; des
  colonnes de 320 px au moins, alignées sur l'en-tête (la photo du produit n'est plus une bande de
  40 px, plus de « Camerc » ni de « Regarder sur Tik… ») ; chaque pays commence sa ligne sous un bandeau
  à son nom (choisir le Togo n'affiche plus d'abord des replays du Cameroun), sans « Glisse vers le
  haut » ; la barre des pays reste en haut avec « Je suis en live », qui ne flotte plus sur les cartes.
- **L'accueil** n'affiche plus les 112 pays (dont 109 à 0, 2 000 px de pastilles) : les pays où il y a un
  live, les plus actifs d'abord, puis celui du visiteur, puis « Tous les pays » ; « En direct maintenant
  · 3 » ensemble.
- **« À vérifier »** : 12 colonnes de 137 px, dont 8 vides, écrasaient les cartes (liens coupés au milieu
  des mots, boutons sur deux lignes, barres de défilement dans les colonnes au zoom). Maintenant seules
  les colonnes avec quelque chose à vérifier sont sur le tableau, 280 px au moins, les autres en une ligne
  « Rien en attente : … » ; si elles ne tiennent pas, le tableau défile de côté.
- **Contrôle** : `tools/captures/mise-en-page.js` vérifie ces règles sur la démo à 390, 820, 1024,
  1366 × 657, 1440 et 1914 px, et à 125 % de zoom pour le back-office : **60 règles tenues**. Vu dans le
  navigateur en français à chaque taille. Remarqué au passage, pas changé : sur tablette (820 px), la
  barre de menus du haut du back-office déborde sur toutes ses pages.
- Tests : 1 nouveau (l'accueil ne nomme que les pays utiles), 1 complété (le fil et ses éléments pour
  grand écran) ; la suite complète sur une base neuve : **722 sans échec**, la démo : **22
  sans échec**.
- **Sur un serveur** : `-u ocd_live` (`python3 tools/versions.py --db <base>` le dit).

### 19 novembre 2026 · Outil : les modules à mettre à jour sur un serveur
`python3 tools/versions.py --db <base> --conf <odoo.conf>` compare les versions installées dans une base
à celles du code récupéré, et donne la commande `odoo` à lancer : les modules à mettre à jour (`-u`), ceux
qui restent d'une commande arrêtée en route (« à installer », « à mettre à jour »), les modules du projet
pas installés (ceux qui viennent seuls avec un autre sont signalés, la démo n'est jamais proposée), et un
code plus ancien que la base. Il ne fait que lire la base, avec le Python d'Odoo ou `psql`. Essayé sur la
base de démo (il y trouve `ocd_business` et `ocd_debranding` à mettre à jour) ; 6 tests
(`tools/test_versions.py`). Aucun module ne change : rien à mettre à jour.

### 19 novembre 2026 · Correctif : `ocd_business` ne s'installait pas avant la mise à jour d'`ocd_live`
Sur le serveur de préproduction, l'installation s'arrêtait sur `ocd_business/views/ocd_business_templates.xml`
(« Element … cannot be located in parent view ») : la page de paiement d'OCD Business visait la phrase
d'aide de « J'ai payé » telle que l'écrit `ocd_live` 20.0.1.25.0, alors que le serveur avait encore la page
d'avant. Elle vise maintenant la première phrase d'aide du formulaire, présente dans les deux versions :
le module s'installe avant ou après la mise à jour d'`ocd_live`. `ocd_business` 20.0.1.1.0, sans
migration (seule la vue change). Reproduit puis vérifié sur une copie de la base de test remise dans le
même état (ancienne page de paiement, puis module resté « à installer ») ; un test nouveau (13 dans le
module) ; la suite complète sur une base neuve : **721 sans échec**, la démo : **22 sans
échec**.
**Sur le serveur** : reprendre l'installation, `-i ocd_business -u ocd_live,ocd_live_shop,ocd_express`.

### 19 novembre 2026 · OCD Business (chantier 12)
Maquette `OcdBusiness` validée avec ses choix recommandés, complétée de règles de robustesse (un paiement
une seule fois, la date calculée, le prix et la durée de la commande, le Mobile Money vérifié à la main,
le remboursement, le magasin de départ visible, les rappels, le lancement), et codée dans deux nouveaux
modules, `ocd_business` et `ocd_business_whatsapp` (20.0.1.0.0) ; `ocd_live_shop` (20.0.1.47.0) et
`ocd_express` (20.0.1.3.0) lisent la formule, `ocd_live` (20.0.1.25.0) corrige la page de paiement.
- **La formule** : une suite de périodes (payée, offerte par l'équipe avec un motif, offerte au
  lancement). Un paiement donne une seule période (index unique sur la ligne de commande), avec la
  durée et le prix de la commande même si les réglages changent ensuite ; elle commence le lendemain de
  la dernière, ou aujourd'hui si la formule est finie : aucun jour perdu. Le vendeur est verrouillé le
  temps de calculer les dates. « OCD Business jusqu'au » se lit dans les périodes : l'équipe offre des
  jours (1 à 400, avec un motif), ne tape jamais une date ; les dates mises à la main avant le module
  deviennent des périodes offertes. Une facture par paiement, liée à son paiement.
- **Le Mobile Money vérifié par l'équipe** : « J'ai payé » garde les fonctions 3 jours après la fin le
  temps de la vérification ; vérifié, les jours partent de la fin de la formule. **Un remboursement**
  (commande annulée) reprend les jours pas encore passés, jamais en arrière, et rapproche les périodes
  suivantes.
- **Le vendeur** : « OCD Business » dans Mon espace (ce que la formule ajoute, ce qui reste pour tous, 1,
  3 ou 12 mois au prix de son pays avec le mois par mois et l'économie, la formule en cours, renouveler,
  ses paiements et leurs factures, ce qui se met en pause si elle s'arrête) ; la ligne de Mon espace avant
  la fin (7 jours avant) et après ; chaque fonction gardée y mène (Mes chiffres, le magasin masqué, plus de
  magasin possible, Mon équipe). Une commande laissée avant de payer est reprise, jamais une deuxième.
  À la fin, rien n'est effacé : les magasins en plus sont masqués mais **le magasin de départ des colis
  reste visible**, l'équipe est en pause, les chiffres en détail sont cachés.
- **OCD Express compris** : avec la formule, le compte d'expéditeur s'ouvre tout de suite et le petit
  ramassage est gratuit.
- **Le lancement** : le jour choisi, les vendeurs qui utilisent les fonctions (plusieurs magasins ou une
  équipe) reçoivent une fois 2 mois offerts, puis les fonctions offertes à tous s'arrêtent.
- **WhatsApp** (au vendeur, « vous ») : la formule payée, la fin proche 7 jours avant et la veille (une
  fois par date de fin, jamais après un renouvellement), la fin, les mois offerts au lancement.
- **La page publique** `/business` pour les commerçants qui ne font pas de lives. **Le back-office** :
  Vendeurs › OCD Business (les périodes, « Remboursé : reprendre les jours »), l'onglet OCD Business de
  la fiche du vendeur et « Offrir des jours », Paramètres › OCD Business (prix, jour du lancement, mois
  offerts, premier rappel, grâce), deux automatisations.
- **Correctifs** : la page de paiement d'un pass de l'annuaire répondait « page introuvable » (seules
  les commandes avec une réservation l'ouvraient) ; elle ne parle plus de « ton heure » pour un pass ou
  une formule.
- Contrôlé dans le navigateur en français sur la démo (`ocd_base`) à 390, 820 et 1440 px, sans
  débordement : OCD Business (à acheter, en cours, fin proche), Mon espace avec la ligne de fin proche,
  Mes magasins, Mon équipe, Mes chiffres, la page de paiement, `/business` ; le back-office (la liste, la
  fiche du vendeur, « Offrir des jours »).
- Tests : 9 dans `ocd_business` (les règles), 3 pour ses pages, 2 dans `ocd_business_whatsapp`, 2 dans
  `ocd_express`, 1 dans `ocd_live_shop` ; **la suite complète** sur une base neuve (tous les modules OCD
  avec les deux nouveaux, et les tests de `payment_cinetpay` et `whatsapp_cloud`) : **720 sans
  échec** ; la démo sur une autre base neuve, installée en une fois avec tous les modules : **22
  sans échec**.
- **À installer sur un serveur** : `-i ocd_business` (`ocd_business_whatsapp` s'installe avec), et **à
  mettre à jour** : `-u ocd_live,ocd_live_shop,ocd_express`. **Modèles WhatsApp à soumettre à Meta** :
  `ocd_business_payee`, `ocd_business_fin_proche`, `ocd_business_terminee`, `ocd_business_lancement`
  (français et anglais).

### 19 novembre 2026 · OCD Business (chantier 12) : la maquette, à valider
Pas de maquette pour ce chantier : proposée avant tout code, dans
[`prototype/design-valide/OcdBusiness.dc.html`](../prototype/design-valide/OcdBusiness.dc.html), relue avec
ce qui existe (l'interrupteur « Formule Business » du chantier 17 que lisent déjà les magasins, l'équipe,
les chiffres et les nouveautés ; le pass de l'annuaire, des jours prépayés avec rappel et renouvellement ;
le paiement d'OCD Live ; les factures ; WhatsApp).
- **Le vendeur** : la formule (plusieurs magasins et leur stock, son équipe, ses chiffres en détail, ses
  nouveautés chaque semaine, OCD Express ; ce qui fait vendre reste pour tous), 1, 3 ou 12 mois payés
  d'avance, jamais prélevés ; la formule active, renouveler (des jours ajoutés après la date), ses
  paiements et leurs factures ; la fin qui approche, et ce qui se met en pause sans rien effacer ;
  l'entrée vers la formule depuis chaque fonction réservée.
- **WhatsApp** : la formule payée, la fin qui approche (7 jours avant et la veille), la fin.
- **La page publique** `/business` pour les commerçants qui ne font pas de lives. **Le back-office** : les
  formules, « Offrir des jours » avec un motif, les réglages (prix, offre de lancement, rappels, limites).
- **Choix à valider** (en bas de la maquette) : le prix, une commission plus basse, OCD Express compris, le
  lancement, les rappels, les limites, la page publique.
- Contrôlée en la rendant dans un navigateur. Aucun module ne change : rien à mettre à jour sur un serveur,
  aucun modèle WhatsApp à soumettre.

### 19 novembre 2026 · Correctif : `ocd_debranding` ne s'installait pas sur une base déjà réglée
Sur le serveur de préproduction, l'installation s'arrêtait sur `ocd_debranding/data/ocd_debranding_data.xml`
(« duplicate key value violates unique constraint ir_config_parameter_key_uniq ») : le nom de
l'application (`web.web_app_name`) existait déjà, enregistré depuis les Paramètres d'Odoo, et le module
le créait une deuxième fois. Le module ne crée plus ce paramètre : une fonction appelée à chaque
installation et mise à jour met « OCD Live » seulement quand aucun nom n'est choisi (vide ou « Odoo ») et
garde le nom choisi par l'équipe. `ocd_debranding` 20.0.1.2.0, sans migration (le paramètre existant est
gardé). Reproduit puis vérifié sur une base de test dans le même état ; un test nouveau (6 dans le module) ;
la suite complète sur une base neuve : **704 sans échec**.
**Sur le serveur** : reprendre l'installation ou `-u ocd_debranding`.

### 19 novembre 2026 · Ambassadeurs (chantier 11)
Maquette `Ambassadeurs` validée avec ses choix recommandés (« robuste, optimisé et fonctionnel »), codée
dans deux nouveaux modules, `ocd_ambassadors` et `ocd_ambassadors_whatsapp` (20.0.1.0.0), et un point
d'accroche dans `ocd_live_shop` (20.0.1.46.0 : le détail d'un reversement ne compte comme ventes ni les
gains des ambassadeurs, ni ceux des points relais).
- **L'ambassadeur** : `/ambassadeurs` (nom, WhatsApp, Mobile Money, la charte) ; le code reçu sur
  WhatsApp prouve le numéro et ouvre le compte ; « Mon espace ambassadeur » (à verser lundi, en attente,
  les 7 derniers jours, ses ventes : en route, livrée, retour demandé, confirmée, retournée, pas de gain et
  pourquoi ; le prénom et le quartier des clients, jamais leur numéro), « Mon argent » (le prochain
  versement ligne par ligne, pourquoi il attend, les versements faits, changer de numéro), « Produits à
  partager » (plus vendus, promos, en live ce soir, nouveautés, recherche, ce qu'on gagne, ceux de son
  pays d'abord, en stock, jamais ses propres produits), « Partager » (l'image dessinée par OCD Live au prix
  du moment avec son lien et son QR, le texte modifiable, statut WhatsApp, un contact, copier, enregistrer,
  le clip du live quand il existe), « Mes liens » (le lien du shop, celui de n'importe quelle page).
- **Le lien** `/a/<code>` : le dernier lien ouvert compte 7 jours sur le téléphone, puis sur le panier,
  pour tous les articles ; à la confirmation, l'ambassadeur, le taux et le plafond du jour sont inscrits
  sur la commande. Une visite par téléphone et par jour ; ni les aperçus des liens, ni l'ambassadeur, ni
  la vendeuse sur ses produits, ni l'équipe. La fiche produit dit « Grâce te recommande ce produit » par
  son script, à partir d'un petit cookie : la page reste en mémoire pour les foules.
- **L'argent** : un gain par colis (index unique), confirmé 7 jours après la livraison avec le code par
  une facture d'achat de l'ambassadeur (une seule par gain, index unique), un retour plus tard repris par
  un avoir ; versé avec les reversements du shop chaque lundi dès 2 000 F, jamais un solde négatif.
- **Contre la fraude** : jamais sur ses propres achats (numéro, Mobile Money, contact, sa boutique), 5
  commandes par mois d'un même client, pause automatique au-delà de 30 % de retours sur 10 colis, un
  Mobile Money par personne (sinon « À vérifier »), nouveau numéro retenu 48 h et dit au numéro du
  compte, pièce d'identité au-delà de 50 000 F gagnés, comptes jamais vérifiés effacés après 7 jours.
- **Le vendeur** voit « Vendu grâce aux ambassadeurs » dans « Mes chiffres » (combien, pas qui). **Le
  back-office** : Shop › Ambassadeurs (la liste et ses chiffres, l'onglet Ambassadeur de la fiche, « Voir
  son espace », les gains colis par colis), la colonne Ambassadeurs de « À vérifier » (compte demandé, à
  vérifier, en pause, pièce d'identité, retour demandé), Paramètres › Ambassadeurs, trois automatisations.
- **WhatsApp** : un message le soir, une fois par jour, avec les colis livrés depuis le dernier ; le
  versement fait ; le numéro de versement changé.
- Contrôlé dans le navigateur en français sur la démo (`ocd_base`, où Grâce Mbia a quatre ventes
  d'exemple) à 390, 820 et 1440 px, sans débordement : `/ambassadeurs`, la fiche produit ouverte par un
  lien, « Mon espace ambassadeur », « Mon argent », « Produits à partager », « Partager », « Mes liens »,
  « Mes chiffres » d'une vendeuse.
- Tests : 15 dans `ocd_ambassadors` (les règles), 5 pour ses pages, 4 dans `ocd_ambassadors_whatsapp` ;
  **la suite complète** sur une base neuve (tous les modules OCD avec les deux nouveaux, et les tests de
  `payment_cinetpay` et `whatsapp_cloud`) : **703 sans échec** ; la démo sur une autre base neuve,
  installée en une fois avec tous les modules : **22 sans échec**.
- **À installer sur un serveur** : `-i ocd_ambassadors` (`ocd_ambassadors_whatsapp` s'installe avec), et
  **à mettre à jour** : `-u ocd_live_shop`. **Modèles WhatsApp à soumettre à Meta** :
  `ocd_ambassadeur_livres`, `ocd_ambassadeur_versement`, `ocd_ambassadeur_numero` (français et anglais).

### 19 novembre 2026 · Ambassadeurs (chantier 11) : la maquette, à valider
Pas de maquette pour ce chantier : proposée avant tout code, dans
[`prototype/design-valide/Ambassadeurs.dc.html`](../prototype/design-valide/Ambassadeurs.dc.html), relue avec
ce qui existe (partage d'un produit et son image, lien court et visites sans les robots des clips, code de
livraison, reversements, connexion par numéro, nouveau numéro de versement retenu, « Signaler » et « À
vérifier »), et pensée pour tenir face à la fraude.
- **L'ambassadeur** : `/ambassadeurs` pour s'inscrire (WhatsApp, Mobile Money, la charte), « Mon espace
  ambassadeur » (à verser lundi, en attente, ses ventes et leur état), « Mon argent », « Produits à
  partager » (ce qu'on gagne sur chacun), « Partager » (l'image faite par OCD au prix du moment, avec son
  lien, pour le statut WhatsApp, un contact, TikTok, et le clip du live).
- **Le client** : le même prix, « Grâce te recommande ce produit » ; le dernier lien ouvert compte 7 jours,
  pour tous les articles de la commande, et l'ambassadeur est inscrit sur la commande à sa confirmation.
- **L'argent** : 5 % des articles payés par OCD sur sa commission (au plus 3 000 F par colis, jamais plus
  que la commission), gagnés quand le colis est livré avec son code, confirmés 7 jours après, versés
  chaque lundi dès 2 000 F ; un retour plus tard est retiré du versement suivant ; chaque gain est une
  facture d'achat, un retour un avoir, jamais un solde négatif versé.
- **Contre la fraude** : jamais sur ses propres achats (numéro, Mobile Money, compte, sa boutique), 5
  commandes par mois au plus d'un même client, pause automatique au-delà de 30 % de retours sur 10 colis,
  un Mobile Money par personne, pièce d'identité au-delà de 50 000 F gagnés, nouveau numéro retenu 48 h.
- **Le vendeur** ne paie rien et voit « Vendu grâce aux ambassadeurs » dans Mes chiffres ; **le
  back-office** : les ambassadeurs, une colonne dans « À vérifier », les réglages.
- **Choix à valider** (en bas de la maquette) : qui, combien et payé par qui, sur quoi, quand c'est gagné,
  le versement, la fraude, ce que voit le client, les vendeurs, les impôts.
- Contrôlée en la rendant dans un navigateur. Aucun module ne change : rien à mettre à jour sur un serveur,
  aucun modèle WhatsApp à soumettre.

### 19 novembre 2026 · Points relais (chantier 10)
Maquette `PointsRelais` validée avec ses choix recommandés, codée dans `ocd_live_shop` (20.0.1.45.0),
`ocd_live_shop_whatsapp` (20.0.1.29.0), `ocd_express` (20.0.1.2.0) et `ocd_express_whatsapp` (20.0.1.1.0).
Un point relais est un **lieu** (`ocd.vendor.place`, la fiche des magasins) marqué « point relais » : une
boutique partenaire tenue par un contact « tient un point relais », ou le magasin vérifié d'un vendeur.
- **Le client** : à la livraison, « Livrée chez moi » ou « **En point relais** » (500 F au lieu de 1 000 F à
  Douala, tarif « point relais » de la ville), les points relais de sa ville, ceux de son quartier
  d'abord, ouverts, pas en congé et pas pleins ; seulement pour les colis portés par les livreurs OCD.
  Sa page de suivi : le point relais, l'itinéraire, l'appeler, jusqu'à quand, le **code et le QR** à
  montrer au comptoir, « Je ne pourrai pas y aller : livrez-la chez moi » (OCD Live sur WhatsApp).
  WhatsApp quand le point relais a compté le colis, et 2 jours avant la fin (sans le code).
- **Le point relais** (`/ocd/point-relais`, connexion par son numéro et un code WhatsApp, ou depuis son
  espace pour un vendeur) : colis gardés sur ses places, gains du mois, « En congé », horaires ;
  « Recevoir » (cocher chaque colis compté, refuser un colis abîmé qui reste au livreur comme problème) ;
  « Remettre » (le QR du client lu par la caméra, ou le colis et son code ; à payer d'abord sur le
  téléphone du client, QR de paiement au comptoir ; 3 codes faux bloquent le colis) ; « À rendre » au
  livreur. Pas d'espèces : le point relais ne garde jamais l'argent des autres.
- **Le livreur** : un arrêt par point relais dans sa tournée, « Je pars au point relais » (le point relais
  est prévenu une fois), puis « J'ai repris ces colis » pour ceux pas retirés.
- **L'argent** : 150 F par colis remis, une facture du point relais versée chaque mois avec les
  reversements ; un colis perdu : OCD rembourse (le client par l'équipe, l'expéditeur Express au plus le
  plafond des réglages) et un avoir le retient sur ses gains ; en pause pour l'équipe après 2 pertes.
  Après 7 jours (jusqu'à la fermeture du dernier jour), le colis repart : remboursé s'il était payé en
  ligne, rendu à l'expéditeur Express contre son code.
- **Devenir point relais** : la page `/points-relais` (une demande dans « À vérifier », colonne Points
  relais, ouverte par l'équipe après sa visite) ; dans « Mes magasins », « **Mon magasin est un point
  relais** » pour un magasin vérifié ouvert au public (A.6, réglable).
- **OCD Express** : l'expéditeur choisit « En point relais (moins cher) » dans le quartier de son client,
  le client peut aussi le choisir sur sa page tant que le livreur n'est pas parti (« Pas là ? Je le
  retire en point relais ») ; la page de suivi montre le point relais, le code et le QR une fois le colis
  compté ; le message vient du numéro d'OCD Express.
- **Back-office** : OCD Live › Livraisons › **Points relais** (colis gardés, à recevoir, à reprendre,
  pertes, mettre en pause, « Perdu au point relais » sur le colis), « À vérifier », le dispatch et le
  tableau de bord comptent les colis au point relais, Paramètres › **Points relais** (gain, jours, rappel,
  places, magasins des vendeurs, pause après), trois automatisations.
- Contrôlé dans le navigateur en français sur la démo (`ocd_base`) à 390, 820 et 1440 px, sans
  débordement : l'étape de livraison (le choix et la liste), la page de suivi au point relais, Mon point
  relais, Recevoir, Remettre, la tournée avec l'arrêt au point relais, `/points-relais`, et pour OCD
  Express « Nouveau colis » (le point relais et son prix), Mes colis, la page du client au point relais
  et le choix d'un point relais.
- Tests : 14 nouveaux dans `ocd_live_shop` (le prix et qui peut y aller, de la livraison à la remise, un
  colis refusé, le rappel puis le retour, plein, congé ou en pause, la perte et la pause, le versement
  du mois, la demande, et les pages), 7 dans `ocd_express`, 1 dans `ocd_express_whatsapp` ; **la suite
  complète** sur une base neuve (tous les modules OCD avec `ocd_express`, `ocd_express_whatsapp`,
  `attachment_s3`, et les tests de `payment_cinetpay` et `whatsapp_cloud`) : **679 sans échec** ; la
  démo sur une autre base neuve, installée en une fois avec tous les modules : **22 sans échec**.
- **À mettre à jour sur un serveur** : `-u ocd_live_shop,ocd_live_shop_whatsapp,ocd_express,ocd_express_whatsapp`,
  puis un tarif « point relais » par ville (Livraisons › Tarifs de livraison) et les premiers points
  relais. **Modèles WhatsApp à soumettre à Meta** : `ocd_colis_point_relais`, `ocd_colis_rappel_relais`,
  `ocd_colis_non_retire_relais`, `ocd_relais_arrivage` (français et anglais), et sur le numéro d'OCD
  Express `ocd_express_point_relais` (français et anglais).

### 18 novembre 2026 · Points relais (chantier 10) : la maquette, à valider
Pas de maquette pour ce chantier : proposée avant tout code, dans
[`prototype/design-valide/PointsRelais.dc.html`](../prototype/design-valide/PointsRelais.dc.html), relue avec
ce qui existe (fiche « lieu » des magasins, retrait en magasin et son code, connexion par numéro de l'équipe
d'un vendeur, tournée et dispatch, tarifs, reversements, OCD Express).
- **Le client** : « Au point relais » à la livraison (500 F au lieu de 1 000 F à Douala), les points
  relais proches, ouverts et pas pleins ; sa page avec le code de retrait et le QR, jusqu'à quand (7 jours),
  l'itinéraire ; WhatsApp quand le colis arrive et deux jours avant la fin (sans le code dans le message).
- **Le point relais** : « Mon point relais » (colis en garde sur ses places, gains du mois à 150 F par colis
  remis, congé, horaires) ; recevoir les colis du livreur en les comptant un par un ; remettre contre le
  code, payé avant ou sur le téléphone du client au comptoir, jamais en espèces.
- **Le livreur** : un arrêt par point relais (déposer, reprendre les colis pas retirés). **OCD Express** :
  livrer au point relais. **Devenir point relais** : la page des partenaires, et « Mon magasin est point
  relais » pour les vendeuses (A.6). **Le back-office** : points relais, dispatch, réglages.
- **Choix à valider** (en bas de la maquette) : qui peut être point relais, le prix, ce qu'il gagne, payer
  au comptoir, le délai, les places, OCD Express, un colis perdu, où commencer.
- Contrôlée en la rendant dans un navigateur. Aucun module ne change : rien à mettre à jour sur un serveur,
  aucun modèle WhatsApp à soumettre.

### 18 novembre 2026 · La démo installée en une fois, OCD Express dans la démo
Les deux points laissés ouverts par le chantier 9, avant le chantier 10.
- **`test_a_day_of_the_shop` corrigé** : Odoo 20 ne charge le plan comptable qu'à la toute fin d'une
  installation (`_register_hook` de `ir.module.module`), après le `post_init_hook` de la démo. Installée en
  une fois avec les modules (comme pour les tests), la démo livrait donc les colis des jours d'avant sans
  facture : aucun reversement avant le lendemain des premières factures, et le test échouait selon l'heure.
  La démo charge maintenant elle-même le plan comptable qu'Odoo allait charger ; le test de la boutique
  vérifie aussi que chaque colis livré les jours d'avant a sa facture et que les reversements des jours
  d'avant sont payés.
- **OCD Express dans la démo** (`ocd_live_demo` 20.0.1.6.0, quand `ocd_express` est installé, avant ou
  après elle) : **Nadège Mode** (Akwa, Instagram et TikTok, sans boutique), ses colis rejoués chaque jour
  ouvré avec la boutique de Douala (9 par jour : espèces, téléphone, déjà payé, refusé à la porte puis
  rendu contre son code, souci signalé puis vérifié, client absent puis second passage, colis au-dessus
  de sa limite vérifié par l'équipe, colis du soir), deux passages de Junior par jour, la caisse de
  19 h 30, son argent préparé à 7 h et versé à 10 h (enregistré dans la comptabilité : « Mon argent » est
  juste) ; **Linda Cosmétiques**, une demande d'ouverture dans « À vérifier » ; Douala ouvert, point OCD et
  Mobile Money d'OCD d'exemple s'ils manquent. Ses clients ont des numéros d'exemple : aucun WhatsApp ne
  leur part. Désinstaller la démo retire colis, passages, clients, versements et paiements, et remet les
  réglages d'OCD Express comme avant. Scénario dans [`DEMO.md`](DEMO.md).
- **`ocd_express`** (20.0.1.1.0), vu en jouant la démo : « **Voir son espace** » sur la fiche d'un
  expéditeur (lien signé pour la personne de l'équipe, comme pour un vendeur) ; un colis déjà payé dont le
  client paie la livraison restait « attend l'argent » pour toujours (rien n'est dû à l'expéditeur) : il est
  « compté » une fois l'argent arrivé ; « Mon argent » montre une ligne par colis retenu par un souci (et
  non l'encaissement et les frais séparés) ; la page de suivi rappelle au client le souci qu'il a signalé,
  puis sa vérification ; « 389 000 FCFA » ne se coupe plus au milieu du mot sur téléphone.
- Contrôlé dans le navigateur en français sur la démo (`ocd_base`) à 390, 820 et 1440 px, sans débordement :
  Mes colis, Mon argent, un colis et son code de retour, la page de suivi (en route, souci signalé), la
  tournée de Junior, `/express`, la fiche de Nadège dans le back-office.
- Tests : **la suite complète** sur une base neuve (tous les modules OCD avec `ocd_express`,
  `ocd_express_whatsapp`, `attachment_s3`, et les tests de `payment_cinetpay` et `whatsapp_cloud`) :
  **657 sans échec** (3 nouveaux dans `ocd_express`) ; la démo sur une autre base neuve, installée en une
  fois avec tous les modules : **22 sans échec** (dont `test_a_day_of_the_shop`, et 3 nouveaux pour OCD
  Express : la démo installée, une journée heure par heure, un colis laissé ouvert les jours d'avant).
- **À mettre à jour sur un serveur** : `-u ocd_express,ocd_live_demo` (la mise à jour de la démo y met
  OCD Express). Aucun nouveau modèle WhatsApp à soumettre à Meta.

### 18 novembre 2026 · OCD Express (chantier 9)
Maquette `OcdExpress` validée, codée dans deux nouveaux modules, `ocd_express` et
`ocd_express_whatsapp`, avec des points d'accroche dans `ocd_live_shop` et `ocd_live`.
- **L'expéditeur** : `/express` (prix réglés par l'équipe), la demande (invités au lancement, puis tout le
  monde), la connexion par numéro et code WhatsApp (un vendeur d'OCD Live garde son espace, avec « Envoyer
  un colis »), « Nouveau colis » (récapitulatif « Tu reçois » en direct), le colis et son étiquette avec QR,
  modifier ou annuler avant le ramassage, « Mes colis », « Mon argent » (versé le jour ouvré suivant, ce
  qui attend, ce qu'on doit et le régler, changer le numéro avec un code, retenu 48 h).
- **Le client** : un WhatsApp dès la création puis au départ, sa page de suivi (code, montant, payer sur
  son téléphone, « Je confirme », « Pas là ? », « Envoyer ma position », souci dans les 48 h, « Ce n'est
  pas pour moi » qui arrête tous les messages vers ce numéro).
- **Le livreur** : dans sa tournée, un passage par expéditeur (cocher les colis pris, photo, « pas pris »
  avec la raison, « l'expéditeur est absent »), les livraisons comme celles du shop sans Mobile Money
  « déclaré » et sur le téléphone seulement au-delà de 100 000 F, espèces plafonnées, les retours rendus
  contre le code de retour de l'expéditeur.
- **L'équipe** : les colis Express dans le dispatch (le passage entier donné à un livreur), un menu OCD
  Express (colis, ramassages, expéditeurs), la fiche de l'expéditeur (solde, retours, « A payé ce qu'il
  doit »), « À vérifier » (demandes, colis retenus, soucis), « Reçu au point OCD », « Perdu ou abîmé par
  OCD », la section OCD Express des Paramètres, 8 automatisations.
- **L'argent** : compté une fois chez OCD (caisse ou fournisseur), en factures et avoirs dans les
  reversements du shop ; jamais d'avance ; souci ouvert, nouveau numéro et solde négatif retenus.
- `ocd_live_shop` : le manque de caisse d'un livreur devient une dette (migration : les écarts déjà comptés
  sont notés réglés) ; un colis sans commande a la devise de la société ; points d'accroche des
  reversements et de la tournée. `ocd_live` : les pages de connexion des modules réunies (OCD Vote et OCD
  Express installés ensemble).
- Contrôlé dans le navigateur en français à 390, 820 et 1440 px, sans débordement.
- **La suite complète** sur une base neuve (tous les modules OCD avec `ocd_express`, `ocd_express_whatsapp`,
  `attachment_s3`, et les tests de `payment_cinetpay` et `whatsapp_cloud`) : **654 tests sans échec** (49
  nouveaux : 39 pour les règles d'OCD Express, 4 pour ses pages, 5 pour ses messages WhatsApp, 1 pour le
  manque de caisse). Le test des modèles WhatsApp de `ocd_live_whatsapp` a trouvé deux variables séparées
  par une seule ponctuation : textes corrigés avant de les soumettre. Démo sur une autre base neuve : 19
  tests, 18 sans échec ; `test_a_day_of_the_shop` (pas de reversement du lendemain quand la démo est
  installée avec les modules en une fois) échoue aussi sur le code d'avant ce chantier : connu, à regarder.
- Pas fait : des colis Express dans les données de démonstration ; le versement automatique par Mobile
  Money (comme les reversements des vendeurs, il est payé par l'équipe avec la référence du transfert).
- Aucun WhatsApp ne part sans l'approbation de Meta : 6 modèles (français et anglais) à soumettre, sur le
  numéro d'OCD Express.

### 18 novembre 2026 · OCD Express (chantier 9) : la maquette validée
Maquette `OcdExpress` relue avec ce qui existe (colis du shop, code, paiement à la porte, dispatch,
tournée, caisse, reversements, tarifs, fiche « lieu », connexion par numéro, WhatsApp des colis), complétée
puis validée avec ses choix ; les trois décisions ouvertes de la feuille de route sont tranchées (prix,
espèces, livreurs). Détail dans [`DECISIONS.md`](DECISIONS.md) (Shop et livraisons, OCD Express).
- **Corrigé dans la maquette** : les chiffres de « Mon argent » (4 livraisons à 1 000 F, retour à 500 F,
  un même nombre de colis partout) ; « la tournée se garde dans le téléphone » était faux (seuls les
  brouillons de « Mes produits » marchent sans réseau).
- **Ajouté** : le colis annoncé au client dès la création (« Je confirme »), l'accord du client pour les
  messages, ouvrir avant de payer, la valeur d'un colis déjà payé, les deux vagues, le ramassage payant
  sous 3 colis, le retour rendu contre un code de l'expéditeur, la photo du colis fermé, « Envoyer ma
  position », un souci signalé pendant 48 h, ce que doit un expéditeur, les espèces plafonnées sur le
  livreur et ses manques de caisse, le numéro WhatsApp à part, l'effacement des clients après 6 mois, le
  coût réel par colis, ce qu'un juriste doit vérifier avant d'ouvrir au public ; les réglages de l'équipe.
- Différences avec le shop à coder : la facture de l'expéditeur attend l'argent (celle du vendeur du shop
  est faite à la livraison), pas de Mobile Money « déclaré », une dette du livreur pour les manques de
  caisse. Effort revu : ~5 semaines.
- Contrôlée dans le navigateur à 390, 820 et 1440 px, sans débordement. Aucun module ne change : rien à
  mettre à jour sur un serveur, aucun modèle WhatsApp à soumettre pour l'instant.

### 18 novembre 2026 · Le script d'installation de l'environnement
- `tools/setup_odoo20.sh` : Odoo 20 dans `/opt/odoo20` (source, environnement Python, `odoo.conf`),
  PostgreSQL et son rôle, `wkhtmltopdf`, `ffmpeg` ; les étapes déjà faites sont sautées. C'est le script de
  l'environnement cloud « projet_ocd » créé pour les sessions de Claude Code (Odoo prêt dès le début d'une
  session) ; marche à suivre dans [`DEVELOPPEMENT.md`](DEVELOPPEMENT.md) (Environnement).
- Aucun module ne change : rien à mettre à jour sur un serveur.

### 18 novembre 2026 · Clips automatiques (chantier 8)
Maquette `ClipsAutomatiques` validée avec ses choix et ses recommandations « Pour que ça tienne en vrai »,
puis codée dans deux nouveaux modules, `ocd_clips` et `ocd_clips_whatsapp`, avec « Le live commence » dans
la régie (`ocd_live_shop`) et un en-tête vidéo pour les modèles WhatsApp (`whatsapp_cloud`).
- **Avant tout, la suite complète** sur une base neuve, attendue pour les deux commits poussés avant elle
  (`attachment_s3` et la régie) : tous les modules OCD avec `attachment_s3` et `payment_cinetpay`,
  **506 tests sans échec**.
- **La régie** : « Le live commence » (de 30 minutes avant l'heure réservée jusqu'à la fin du live) ; les
  moments du replay comptent depuis ce vrai début, et ceux déjà notés sont recomptés : un live qui
  commence en retard ne décale plus son replay ni ses clips (`ocd_live_shop` 20.0.1.43.0). À la fin du
  live, « Envoyer la vidéo du live » à côté de « Publier le replay », avec où en sont ses clips.
- **La vidéo du live** (écran « Vidéo du live et clips » : bouton « Clips » du live, ou la régie) :
  envoyée par morceaux de 8 Mo, reprise après une coupure du réseau ou en choisissant le même fichier
  après avoir fermé la page, 4 Go au plus, place vérifiée avant ; vérifiée à l'arrivée (lisible, image et
  son, sa durée face au dernier moment : « la vidéo dure 25:00, le dernier moment est à 43:23 ») ; en
  plusieurs parties, chacune avec son début, réglable de 5 s en 5 s avec l'aperçu du premier moment ;
  effacée après 7 jours, les clips restent ; les envois abandonnés effacés après 24 h.
- **Les clips** : un par produit et par live, de 3 s avant le moment noté à 30 s au plus, coupé avant le
  produit suivant, 12 s au moins sinon « Pas de clip » ; vertical 720 × 1280 (une vidéo horizontale posée
  sur un fond flou), le son du live, le logo « Vu en live », le produit, le vendeur et sa ville et le lien
  court hors des zones cachées de TikTok, Reels et des statuts, les 2 dernières secondes avec le QR. Faits
  sur le serveur l'un après l'autre par une tâche planifiée (environ 10 s par clip), 3 essais, reprise
  après un redémarrage, ffmpeg en basse priorité ; « Refaire » et « Masquer » pour l'équipe ;
  OCD Live › Lives › Clips ; dans « À faire », les lives sans vidéo et les clips pas faits.
- **Le vendeur** : « Tes clips sont prêts » en haut de Mon espace ; « Mes clips » (par live, du plus
  récent au plus ancien, grille de 5 sur ordinateur) ; la page d'un clip : « Partager » (la vidéo
  elle-même avec son texte au prix du moment), « Enregistrer », « M'envoyer le clip sur WhatsApp » (10 par
  jour), « Masquer », « Vidéo de ma carte du fil », ses lectures, visites et ventes ; « ▶ 3 clips » sous
  chaque produit de Mes produits et « Mes clips » dans son menu « Plus » ; « Venus des clips » dans Mes
  chiffres.
- **Le public** : « Vu en live » sur la fiche du produit (l'image du clip, la vidéo chargée seulement au
  toucher, le replay à ce moment) ; un clip par produit sur le replay ; le lien court `/p/K7Q2AB` vers le
  produit avec la couleur montrée (sinon la boutique ou le shop), une visite par téléphone et par jour,
  sans les robots ; une vente comptée pour un clip si la commande arrive dans les 7 jours après sa visite,
  depuis le même téléphone.
- **WhatsApp** (`ocd_clips_whatsapp`) : `ocd_clips_prets` au vendeur une fois par live, quand ses clips
  sont prêts ; `ocd_clip_video`, le clip lui-même en tête du message. `whatsapp_cloud` sait maintenant
  envoyer et soumettre à Meta un modèle avec une vidéo en tête.
- **Réglages** (Paramètres › Clips automatiques) : durées, vidéo gardée, clips d'un produit retiré,
  qualité (720 ou 1080), adresse des liens courts, clips envoyés sur WhatsApp par jour ; « Pas de clips »
  sur la fiche d'un vendeur ; automatisations « Clips prêts : prévenir le vendeur », « Vidéo du live pas
  envoyée : dans À faire » et la tâche « Faire les clips des lives ».
- Tests : base neuve, tous les modules OCD avec `ocd_clips`, `ocd_clips_whatsapp`, `attachment_s3`,
  `payment_cinetpay` et les tests de `whatsapp_cloud` : **605 sans échec** (23 nouveaux : 18 dans `ocd_clips`, avec de
  vraies vidéos faites par ffmpeg, 3 dans `ocd_clips_whatsapp`, 2 pour l'en-tête vidéo de WhatsApp) ; essayé de bout en bout sur la démo en
  français : une vidéo de 45 minutes en deux parties envoyée par l'écran de l'équipe, les 3 clips faits
  par la tâche planifiée, partagés, lus sur la fiche et le replay, le lien court ; contrôlé dans un
  navigateur en trois tailles (390, 820, 1440 px) : Mon espace, Mes clips, un clip, Mes produits, Mes
  chiffres, la fiche produit, le replay, l'écran de l'équipe ; aucun débordement.
- **À installer sur un serveur** : `apt-get install -y ffmpeg` (ffprobe compris) ; `-u whatsapp_cloud`
  (20.0.2.10.0), puis `-i ocd_clips,ocd_clips_whatsapp` (nouveaux modules). Puis soumettre à Meta
  `ocd_clips_prets` et `ocd_clip_video` (Utilitaire, français et anglais ; le second avec la vidéo d'un
  clip en exemple : à soumettre après le premier clip fait, ou avec une vidéo d'exemple sur le modèle).

### 18 novembre 2026 · Fichiers sur Cloudflare R2 (module `attachment_s3`)
Demandé par l'équipe pendant le chantier 8 : les fichiers de toute la plateforme sur un stockage objet,
en saisissant seulement les clés, dans un module à part utilisable ailleurs.
- Nouveau module générique `attachment_s3` (Cloudflare R2, AWS S3, Backblaze B2, MinIO) : Paramètres ›
  Paramètres généraux › Fichiers sur un stockage S3 ; « Tester la connexion » ; chaque nouveau fichier
  copié sur le bucket juste après son enregistrement et vérifié (taille, MD5), renvoyé plus tard si le
  réseau coupe ; les fichiers déjà là envoyés en arrière-plan avec leur progression ; un fichier qui
  manque sur le serveur repris du bucket à la lecture ; « Garder sur le serveur » (tout, ou les fichiers
  lus récemment jusqu'à une taille) ; un fichier supprimé dans Odoo supprimé du bucket un jour après ;
  « Rapatrier les fichiers sur ce serveur ». Marche à suivre dans [`DEVELOPPEMENT.md`](DEVELOPPEMENT.md).
- Tests : 7 sans échec (bucket en mémoire), et un essai de bout en bout avec le vrai client boto3 contre
  un serveur S3 de test (envoi vérifié, reprise, test de connexion, suppression) ; écran des paramètres
  contrôlé en français.
- **À installer sur un serveur** : `pip install boto3`, puis `-i attachment_s3` ; rien ne change tant que
  le stockage n'est pas activé dans les paramètres.

### 18 novembre 2026 · Programme et événements (chantier 7), prix promo (3.1)
Dessiné d'abord (maquette `ProgrammeSoirees`, validée avec ses choix), puis codé dans `ocd_live_shop`
(prix promo, programme des lives) et deux nouveaux modules, `ocd_soirees` et `ocd_soirees_whatsapp`.
- **Le prix promo** : « Mettre en promo » dans le menu « Plus » de Mes produits (-10 %, -20 %, -25 %,
  -30 % ou un autre prix ; 7, 14 ou 30 jours ; l'aperçu de ce que voient les clients ; « Arrêter la
  promo »). Le prix barré et « -24 % » sur les cartes du shop, de la boutique et des lives, la fiche
  (« Promo jusqu'au samedi 28 novembre »), la régie et le panier ; le filtre « En promo » du shop. Le
  prix barré est le prix le plus bas des 14 derniers jours ; 50 % de remise et 30 jours au plus
  (réglages) ; OCD Live › Shop › Promos pour l'équipe.
- **Le programme des lives** (`/lives/programme`, « Programme des lives » depuis le fil) : les 7
  prochains jours, par heure, « En direct maintenant », la cloche (« Suivre » le vendeur) ; filtres pays
  et catégorie ; sur ordinateur, le guide télé, une ligne par compte d'OCD Live.
- **Les grands événements** (`/evenements`) : une soirée, une journée ou plusieurs jours de suite
  (14 jours au plus, réglable ; les événements de plusieurs jours ajoutés à la demande de l'équipe après
  la maquette). L'étiquette vient des heures (« Grande soirée », « Grande journée », « Grand événement ·
  6 jours ») ; la page : compte à rebours, vendeurs, promos, le programme jour par jour, les promos par
  catégorie, « Me prévenir sur WhatsApp », partager ; chaque jour de l'événement est marqué sur le
  programme des lives, avec son bandeau.
- **Le vendeur invité** : l'invitation dans Mon espace et sur WhatsApp, « Participer » (son live pendant
  l'événement, la réservation habituelle ; une remise par produit) ; l'équipe vérifie (« À vérifier »,
  colonne « Grands événements ») ; les promos de l'événement s'affichent ensuite, pendant ses heures
  seulement, sans coupure.
- **Back-office** : OCD Live › Lives › Grands événements et Participations aux événements (ouvrir les
  inscriptions, annuler, la page, les promos) ; réglages « Grands événements » (fin des inscriptions,
  durée au plus, « Me prévenir ») ; automatisations « Grand événement : inviter les vendeurs » et
  « Grand événement : prévenir ceux qui l'ont demandé ».
- **Choix faits pendant le chantier** (détail dans [`DECISIONS.md`](DECISIONS.md)) : un seul calcul des
  prix pour tout le site, toutes les devises comprises ; deux promos en même temps : le prix le plus bas ;
  le prix revient tout seul à l'heure (pas de tâche « fin des promos ») ; un panier commencé en promo la
  garde 2 heures, puis reprend le prix du moment et le dit ; un prix baissé sous la promo l'arrête ; les
  étiquettes imprimées gardent le prix habituel ; les promos d'un événement le suivent s'il est déplacé
  et s'arrêtent s'il est annulé ; aucun message « ça commence » pour un événement sans vendeur accepté ;
  les anciennes adresses `/soirees` mènent à `/evenements` ; « jours » traduit dans les réglages du shop
  (c'était « days »).
- Tests : base neuve, tous les modules OCD avec `ocd_soirees`, `ocd_soirees_whatsapp` et
  `payment_cinetpay` : **499 sans échec** (18 nouveaux) ; contrôlé dans un navigateur en français en trois tailles (390,
  820, 1440 px) : le programme, les grands événements, une soirée, un événement de six jours, le shop et
  son filtre « En promo », une fiche en promo, le panier, la boutique, Mes produits, « Mettre en promo »,
  Mon espace et « Participer » ; aucun débordement.
- **À installer sur un serveur** : `-u ocd_live_shop,ocd_live_whatsapp` (20.0.1.42.0 et 20.0.1.9.3), puis
  `-i ocd_soirees,ocd_soirees_whatsapp` (nouveaux modules). Puis soumettre à Meta `ocd_soiree_invitation`
  et `ocd_soiree_commence` (Utilitaire, français et anglais).

### 18 novembre 2026 · OCD Tickets (chantier 6)
Dessiné d'abord (maquette `OcdTickets`, validée avec ses choix), puis codé dans deux nouveaux modules,
`ocd_tickets` et `ocd_tickets_whatsapp`, sur l'application Événements d'Odoo (gratuite).
- **Les événements** (`/billets`, « Billets » dans le menu des grands écrans quand un événement est en
  vente) et **la page d'un événement** (`/billets/<événement>`) : l'affiche, « Organisateur vérifié »,
  la date et l'ouverture des portes à l'heure du lieu, le lieu et l'itinéraire, les billets vendus et ce
  qui reste, les types de billets (« Plus que 12 », « Épuisé »), la garantie, « Signaler » ; sur
  ordinateur, les − / + et le total à droite.
- **Acheter** (`/billets/<événement>/acheter`) : un nombre par type (10 au plus par commande), le nom sur
  les billets, le WhatsApp, « Payer 10 000 F », puis le formulaire de paiement d'OCD Live ; les places
  sont gardées 10 minutes, puis remises en vente.
- **Mes billets** : l'attente du paiement (« J'ai payé » pour le Mobile Money vérifié par l'équipe),
  puis « C'est payé : 2 billets », un billet par personne (QR signé, code « NAF-7K2Q-41 »), le PDF,
  « Donner ce billet » (nouveau QR, l'ancien ne marche plus) ; après un report, « Je ne peux pas venir :
  me rembourser » pendant 7 jours.
- **L'entrée** (`/billets/entree`, connexion des contrôleurs par numéro et code) : la caméra du
  téléphone lit les QR, ou le code tapé ; « Entrée OK », « Déjà entré » (heure, porte, contrôleur), « Pas
  pour ce soir », « Billet inconnu » ; le compteur des entrés ; hors réseau, la liste reste dans le
  téléphone et les entrées partent au retour du réseau ; « Vendre à l'entrée » (espèces ou Mobile Money).
- **Pendant un live** : la régie met un type de billet à l'écran comme un produit ; la boutique mène à
  l'achat, au prix du live jusqu'à la fin du live.
- **L'organisateur** (le même espace que pour OCD Vote) : ses billets vendus, l'encaissé (dont pendant les
  lives), sa part (90 %), les entrés, les ventes par type, partager, « Vendre pendant un live », les
  étapes, « Envoyer mon événement à OCD Live » ; ses contrôleurs (ajouter avec leur porte, vend à
  l'entrée ou non, retirer).
- **WhatsApp** : billets prêts (aussi pour un billet donné), rappel la veille, événement annulé ou déplacé,
  contrôleur ajouté ; les messages des commandes du shop ne partent pas pour des billets.
- **Back-office** : OCD Live › Billets (Événements, Billets vendus, Contrôleurs, Organisateurs) ; la fiche
  d'un événement d'Odoo avec l'onglet « OCD Live » et les boutons « Vérifier et mettre en vente »,
  « Déplacer », « Annuler et rembourser », « Reversement versé », les billets et les entrées ; « À
  vérifier » : les événements envoyés ; réglages « Billets » ; automatisations « Billets payés : les
  envoyer », « La veille : rappel aux acheteurs », « Événement annulé ou déplacé : prévenir les
  acheteurs », « Après l'événement : reversement à l'organisateur ».
- Tests : base neuve, tous les modules OCD avec `ocd_tickets`, `ocd_tickets_whatsapp` et
  `payment_cinetpay` : **481 sans échec** (15 nouveaux) ; contrôlé dans un navigateur en français
  en trois tailles (390, 820, 1440 px) : les événements, un événement, acheter, le paiement, Mes billets,
  un billet, l'entrée, la vente à l'entrée, l'espace de l'organisateur et ses contrôleurs ; aucun
  débordement ; la fiche de l'événement dans le back-office.
- **À installer sur un serveur** : `-i ocd_tickets,ocd_tickets_whatsapp` (nouveaux modules, avec
  l'application Événements d'Odoo et `event_sale`), et `-u ocd_live_whatsapp` (20.0.1.9.2, un test
  seulement). Puis soumettre à Meta les 5 modèles `ocd_billets_*` (Utilitaire, français et anglais).

### 18 novembre 2026 · Paiement automatique dans l'UEMOA (chantier 5)
CinetPay et Flutterwave, choisis par l'équipe. Le code est prêt avant les contrats : chaque fournisseur
s'ouvre quand ses clés sont saisies.
- **CinetPay** (nouveau module `payment_cinetpay`) : le client choisit Mobile Money, Wave ou la carte
  dans le formulaire de paiement d'OCD Live, puis paie sur la page de CinetPay ; Côte d'Ivoire, Sénégal,
  Togo, Bénin, Mali, Burkina Faso, Niger, Cameroun, Guinée, RD Congo. Le montant demandé est un multiple
  de 5 en francs CFA (arrondi de quelques francs au plus), la commande est payée pour son montant.
  L'état est toujours lu chez CinetPay (au retour du client, à la notification, puis toutes les 10
  minutes pendant un jour pour un paiement resté en attente).
- **Flutterwave** : le module d'Odoo, installé avec `ocd_live` ; la carte partout, le Mobile Money en
  Côte d'Ivoire, au Sénégal, au Mali et au Cameroun une fois activé sur sa fiche.
- **Le Mobile Money vérifié par l'équipe s'efface** dans un pays et une devise où CinetPay, Flutterwave
  ou CamPay prend le Mobile Money en production ; il reste en mode test et là où rien d'automatique
  n'est ouvert (Guinée-Bissau, par exemple). Les votes d'OCD Vote, les réservations et le shop en
  profitent sans changement.
- **Paramètres › Paiements** : pour chaque fournisseur, ses pays et ses devises, puis « Ses clés ne sont
  pas encore saisies » ou « En mode test » ; l'avertissement des pays sans paiement en ligne nomme
  CinetPay et Flutterwave.
- Tests : base neuve, tous les modules OCD avec `payment_cinetpay` : **466 sans échec**
  (7 nouveaux : 5 pour CinetPay, sans jamais lui parler, 1 pour le Mobile Money de l'équipe qui s'efface,
  1 pour les Paramètres). Aucun nouvel écran sur le site (la page de paiement est celle de CinetPay).
- **À installer sur un serveur** : `-u ocd_live,ocd_live_shop` (20.0.1.23.0 et 20.0.1.40.0) : la mise à
  jour d'`ocd_live` installe `payment_cinetpay` et `payment_flutterwave`. Aucun modèle WhatsApp nouveau.

### 18 novembre 2026 · OCD Vote (chantier 4)
Dessiné d'abord (maquette `OcdVote`, validée avec ses choix), puis codé dans deux nouveaux modules,
`ocd_vote` et `ocd_vote_whatsapp`.
- **Le concours** (`/vote`, `/vote/<concours>`) : le nom, l'organisateur (« Organisateur vérifié »), la fin
  à l'heure du pays, les candidats, les voix, le temps qui reste ; « Comment voter » ; chercher un numéro
  ou un nom ; « Classement » ou « Par numéro » ; le prix, le règlement, « Signaler » ; sur ordinateur, le
  classement et la finale à droite. « Votes » est dans le menu des grands écrans quand un concours est
  ouvert.
- **Voter** (`/vote/<concours>/<numéro>`) : la photo et le numéro, le rang et les voix, « Partager sa
  page », 1 voix, les paquets (« 1 offerte », « 10 offertes ») ou un autre nombre, le numéro Mobile Money,
  « Payer 900 F pour 10 voix », puis le formulaire de paiement d'OCD Live. **Mes voix** : l'attente du
  paiement (« J'ai payé » pour le Mobile Money vérifié par l'équipe), puis « 10 voix pour Aïcha, c'est
  compté », le reçu (moyen, date, référence), « Revoter », « J'ai voté », le classement ; paiement pas
  reçu ou arrivé après la fin : dit tel quel.
- **Seules les voix payées comptent** : une ligne par paiement, comptée quand le paiement confirme la
  commande ; remboursée, elle ne compte plus ; commencée après la fin, elle est « à rembourser » ; non payée
  en 10 minutes (réglable), annulée.
- **Classement en direct** (`/vote/<concours>/classement`, mis à jour toutes les 10 secondes), les nombres
  cachés les dernières heures ; **bandeau de la finale** (une adresse secrète par concours, pour OBS :
  les 5 premiers, le temps qui reste, le lien, le QR et « VOTE + numéro ») ; **résultats certifiés**
  (`/vote/<concours>/resultats` et PDF, avec la signature des résultats) ; « Préviens-moi sur WhatsApp »
  pour la finale.
- **L'organisateur** (`/vote/organisateur`, connexion par numéro et code) : ses voix, l'encaissé, sa part,
  les voix du jour, les étapes, « Envoyer mon concours à OCD Live », partager, le bandeau ; ses candidats
  (ajouter avec une photo, numérotés dans l'ordre ; après l'ouverture, une nouvelle photo ou phrase est
  vérifiée et le nom ne change plus).
- **WhatsApp** : « VOTE 12 » au bot d'OCD Live, le candidat et ses voix, le nombre de voix en boutons, puis
  la demande CamPay sur le téléphone (numéro camerounais) ou le lien du paiement ; le message des voix
  comptées (`ocd_vote_comptee`) et celui de la finale (`ocd_vote_finale`) ; les messages des commandes du
  shop ne partent pas pour des voix.
- **Back-office** : OCD Live › Votes (Concours, Voix, Organisateurs) ; la fiche d'un concours (vérifier et
  ouvrir, fermer, publier les résultats certifiés, le PDF, le reversement versé, la page, le bandeau) ; une
  ligne par paiement (« Remboursées », groupées par téléphone) ; « À vérifier » : les concours envoyés et
  les candidats ajoutés ou changés après l'ouverture ; réglages « Votes » ; automatisations « Voix
  payées : prévenir le votant », « Concours fermé : résultats et reversement », « Finale : prévenir ceux qui
  l'ont demandé ».
- Tests : base neuve, tous les modules OCD avec `ocd_vote` et `ocd_vote_whatsapp` : **459 sans échec**
  (9 nouveaux) ; contrôlé dans un navigateur en français en trois tailles (390, 820, 1440 px) : les
  concours, un concours, un candidat et ses voix, le paiement, Mes voix, le classement, les résultats,
  l'espace de l'organisateur et ses candidats ; aucun débordement.
- **À installer sur un serveur** : `-i ocd_vote,ocd_vote_whatsapp` (nouveaux modules), et `-u
  ocd_live_whatsapp` (20.0.1.9.1, un test seulement). Puis soumettre à Meta `ocd_vote_comptee` et
  `ocd_vote_finale` (Utilitaire, français et anglais).

### 17 novembre 2026 · Statistiques du vendeur, « Mes chiffres » (chantier 3, avec 3.3)
Dessiné d'abord (maquette `MesChiffres`, validée), puis codé.
- **Pour tous les vendeurs** : la carte « Mes chiffres » de Mon espace (« Ce mois : 186 500 F · 27 pièces
  ▲ 18 % », comparé aux mêmes jours du mois d'avant) et, sous chaque produit de Mes produits, « Vendu : 14
  en 30 jours · dernière vente hier ».
- **« Mes chiffres »** (`/ocd/espace/moi/chiffres`, aussi dans le menu de l'espace, avec « Mes avis ») :
  avec OCD Business (offert pendant le lancement), une période au choix (7 jours, 30 jours, 3 mois) ; les
  ventes, les pièces, les visites de la boutique et les contacts WhatsApp, avec leur évolution ; une phrase
  d'aide (« 76 % de tes ventes viennent de tes lives. Ton live du lundi 9 novembre a fait à lui seul 34 %
  de ces 30 jours. ») ; **Mes lives** (ouvert depuis OCD, visites de la boutique, pièces et montant vendus,
  nouveaux abonnés, produit phare, « Meilleur live », replay ; en tableau sur ordinateur) ; **Mes
  meilleures heures** (jour × tranche, à l'heure du vendeur, sur 3 mois) et « Réserver un live samedi
  19 h », qui ouvre la réservation sur ce créneau ; **Mes clients fidèles** (2 commandes ou plus en 12 mois,
  prénom et initiale, jamais le numéro) ; **Ventes par produit** (« Plus vendus », « Pas vendus », le
  conseil « Beaucoup d'intérêt, pas de vente » et « Ajouter à mon prochain live », qui met le produit dans
  la préparation du live) ; **Mes magasins** (itinéraires, appels, WhatsApp, retraits au comptoir, colis
  partis) ; l'interrupteur « Recevoir le résumé de ma semaine » ; « Comment c'est compté ». Sans OCD
  Business : les ventes et les pièces sur 30 jours, puis le détail annoncé.
- **Un seul calcul** (`ocd.vendor.figures`) pour la page, Mon espace, Mes produits, les magasins et le
  résumé. Les ventes : commandes confirmées, sans les annulées ni les colis rendus, la part du vendeur
  sans la livraison.
- **Nouveaux comptages, jour par jour** (`ocd.vendor.count`, écrits toutes les 5 secondes comme les visites
  de la régie) : « Ouvert depuis OCD » (les boutons « Regarder » des cartes du fil, de la boutique et le
  message aux abonnés pendant un live passent par une adresse qui compte, puis ouvre le live), les visites
  de la boutique (une par téléphone et par jour, jamais celles du vendeur ; la page les dit une fois
  affichée, elle reste ainsi gardée en mémoire pour les foules), les contacts WhatsApp (produit et
  boutique en vente directe).
- **Ventes d'un live** : le panier retient les lives dont le visiteur a vu la boutique pendant le live
  (pendant, puis 3 heures après, réglable) ; à la confirmation, les lignes du vendeur sont notées avec le
  live.
- **WhatsApp du lundi** : nouveau modèle `ocd_resume_semaine` (français et anglais, Utilitaire), le lundi
  dès 9 h à l'heure du vendeur, seulement s'il l'a allumé (STOP l'arrête), rien quand rien ne s'est passé ;
  son bouton ouvre « Mes chiffres ». Automatisation « Résumé de la semaine aux vendeurs ».
- **Back-office** : bouton « Chiffres » sur la fiche du vendeur (ouvre sa page, comme « Voir son espace ») ;
  réglages (Produits et magasins des vendeurs) : ventes d'un live (3 heures après sa fin), clients fidèles
  (2 commandes), jour et heure du résumé.
- Amélioré au passage : sur tablette, l'onglet de la page ouverte reste visible dans le menu de l'espace ;
  « Regarder le live » de la boutique prend aussi le lien du compte d'OCD Live du live.
- Tests : base neuve, tous les modules OCD : **450 sans échec** (9 nouveaux ; deux tests suivent les boutons « Regarder » comptés) ; contrôlé dans un navigateur en français en trois
  tailles (390, 820, 1440 px) : Mes chiffres (30 jours, 7 jours et « Pas vendus »), Mon espace, Mes
  produits, Mes avis, et le bouton « Chiffres » du back-office ; aucun débordement.
- **À mettre à jour sur un serveur** : `ocd_live` 20.0.1.22.0, `ocd_live_shop` 20.0.1.39.0,
  `ocd_live_shop_whatsapp` 20.0.1.28.0 (`-u ocd_live,ocd_live_shop,ocd_live_shop_whatsapp`), puis soumettre à
  Meta le modèle `ocd_resume_semaine` (français et anglais).

### 17 novembre 2026 · Le bouton de langue garde le choix sur toutes les pages
- **Le défaut** : sur certaines pages, « Français » rechargeait la page en anglais. Le lien vers `/fr/…`
  perdait son code (Odoo l'enlève des liens quand le français est la langue du site), puis le navigateur
  qui avait choisi l'anglais revenait à l'anglais ; et un navigateur qui n'avait jamais choisi gardait la
  langue devinée par Odoo (son téléphone), écrite après le choix.
- **Corrigé** : le bouton passe par `/ocd/langue/<code>?r=<page>`, qui garde le choix (le dernier mot de la
  réponse) puis ouvre la même page dans cette langue. Contrôlé sur 26 pages (publiques et espace du
  vendeur, depuis l'anglais), et pour un navigateur neuf dans les deux sens (téléphone en anglais qui
  choisit le français, et l'inverse) : la page suivante garde la langue choisie.
- **À mettre à jour sur un serveur** : `ocd_live` (`-u ocd_live`).

### 17 novembre 2026 · Garantie OCD et avis (chantier 2)
Dessiné d'abord (maquette `GarantieAvis`, validée), puis codé.
- **La garantie, visible** : sur la fiche produit et la boutique, « Garantie OCD Live » : le vendeur n'est
  payé qu'une fois le colis livré, quand le client donne son code ; pas livré : remboursé ; retour
  possible pendant N jours (le réglage des retours). Un vendeur qui encaisse lui-même (vente directe) est
  dit « hors de la garantie OCD Live ». La page `/ocd/garantie` explique les trois promesses.
- **Les avis des acheteurs** : un avis par colis livré (donc par vendeur d'une commande), sur la page de
  suivi de la commande (« Ton avis sur Brenda Wax » : étoiles et un mot, à changer ensuite) ; la note
  donnée sur WhatsApp ou sur l'ancienne note de la commande devient l'avis de chaque colis livré.
  Seuls le prénom et l'initiale du nom sont montrés (« Estelle N. »), jamais le numéro ; chaque avis est
  un « Achat vérifié ». La note du vendeur (« ★ 4,8 · 12 avis ») s'affiche dès **3 avis** ; avant :
  « Nouveau vendeur ». Elle est sur la boutique (avec les derniers avis et « Voir les N avis »), la fiche
  produit, les cartes du fil des lives, et dans « Mes produits » pour chaque produit.
- **Le vendeur** : « Mes avis » dans Mon espace, et « Signaler cet avis » avec un mot ; l'avis reste
  affiché jusqu'à la décision de l'équipe (garder ou masquer, dans « À vérifier ») ; un avis masqué ne
  compte plus dans la note.
- **Vendeur vérifié** : une case de la fiche du vendeur (qui et quand), proposée quand l'équipe valide un
  nouveau vendeur ; le badge est sur la boutique, la fiche produit et les cartes du fil.
- **Signaler** un produit ou un vendeur (lien en bas de la fiche produit et de la boutique) : ce qui ne va
  pas (contrefaçon, prix ou description trompeurs, arnaque ou jamais livré, produit interdit ou choquant,
  autre chose avec un mot), son WhatsApp si on veut ; une fois par jour et par personne (ou par téléphone
  sans numéro). Le vendeur ne sait jamais qui a signalé. **L'équipe** voit les signalements dans
  « À vérifier » (colonne « Signalements », groupés par produit ou vendeur) : « Rien à faire », ou le
  produit retiré de la vente avec une raison envoyée au vendeur (comme un refus) ; un vendeur signalé :
  « Vu » (« Voir le vendeur » ouvre sa fiche). Back-office : Shop › « Avis des acheteurs » et « Signalements des
  clients », boutons « Avis » et « Signalements » sur la fiche du vendeur.
- Tests : base neuve, tous les modules OCD : **441 sans échec** (8 nouveaux ; le test de l'ancienne note
  de la commande suit les avis) ; contrôlé dans un navigateur en français en trois tailles (390, 820,
  1440 px) : la boutique et ses avis, la fiche produit et sa garantie, la page Signaler, la page de la
  garantie, la page des avis, Mes avis du vendeur ; aucun débordement.
- **À mettre à jour sur un serveur** : `ocd_live` 20.0.1.21.0, `ocd_live_shop` 20.0.1.38.0,
  `ocd_live_shop_whatsapp` 20.0.1.27.0 (`-u ocd_live,ocd_live_shop,ocd_live_shop_whatsapp`). Aucun nouveau
  modèle WhatsApp à soumettre à Meta : la note demandée après la livraison reste le même message.

### 17 novembre 2026 · Suivre un vendeur et ses nouveautés (chantier 1, A.8)
Dessiné d'abord (maquette `SuivreVendeur`, validée), puis codé.
- **Suivre** remplace « Me prévenir sur WhatsApp » (un seul live) : sur la boutique (sous le nom, avec le
  nombre d'abonnés, et dans « Prochain live »), les cartes des lives, le replay et la fiche d'un produit.
  La page `/ocd/suivre/<vendeur>` demande le numéro (sauf pour une personne connue sur ce téléphone) et
  deux choix : « À chaque live », « Ses nouveautés ». « Suivie » ouvre la même page pour changer ou
  « Ne plus suivre ». Suivre vaut accord pour ces messages ; STOP les arrête comme les autres.
- **À chaque live** : au début de chaque live, les abonnés reçoivent le WhatsApp `ocd_vendeur_en_live`
  (le même modèle qu'avant, son bouton ouvre la boutique sur leur téléphone) ; 2 lives par jour au plus et
  par vendeur (réglage « Lives annoncés aux abonnés ») ; un abonné arrivé pendant le live n'est pas
  prévenu de ce live.
- **Nouveautés** (A.8) : le vendredi (réglage) dès 10 h à l'heure du vendeur, les produits mis en vente
  depuis le dernier envoi (« Robe en wax, Sac en raphia et 1 autre ») ; rien de nouveau, rien d'envoyé ;
  une fois par mois (le premier vendredi) pour tous, chaque semaine avec OCD Business. Le bouton ouvre la
  boutique avec ces produits en premier, marqués « Nouveau » (les produits de la semaine le sont toujours).
- **Mes vendeurs suivis** (`/ocd/suivis`, aussi depuis la page du numéro) : un interrupteur par choix et
  « Ne plus suivre ». Un numéro tapé n'est pas vérifié : ce téléphone ne retrouve que les abonnements faits
  sur lui ; le bouton d'un message ouvre tous ceux de son numéro.
- **Le vendeur** : « Mes abonnés » dans Mon espace (combien, +N cette semaine, jamais les numéros), les
  prochaines nouveautés et « Partager ma boutique pour avoir des abonnés ». **Back-office** : bouton
  « Abonnés » sur la fiche du vendeur, menu Shop › « Abonnés des vendeurs », automatisation « Nouveautés
  d'un vendeur : prévenir ses abonnés ».
- Les « Me prévenir » en attente deviennent des abonnements aux lives (sans les nouveautés).
- Tests : base neuve, tous les modules OCD : **433 sans échec** (9 nouveaux) ; contrôlé dans
  un navigateur en français en trois tailles (390, 820, 1440 px) : la boutique, la page Suivre, Mes
  vendeurs suivis, les cartes des lives, Mon espace du vendeur.
- **À mettre à jour sur un serveur** : `ocd_live` 20.0.1.18.0, `ocd_live_shop` 20.0.1.35.0,
  `ocd_live_shop_whatsapp` 20.0.1.25.0 (`-u ocd_live,ocd_live_shop,ocd_live_shop_whatsapp`). À soumettre à
  Meta (**Marketing**, français et anglais) : `ocd_vendeur_nouveautes`. Le modèle `ocd_vendeur_en_live`
  ne change pas chez Meta.

### 17 novembre 2026 · L'équipe du vendeur (chantier 22)
Dessiné d'abord (maquette `EquipeDuVendeur`, validée), puis codé.
- **Mon équipe** (Mon espace et menu du vendeur) : les personnes qui tiennent ses magasins, leur
  WhatsApp, leur magasin, « Active », « Pas encore venu » ou « En pause », leur dernière visite ;
  « Renvoyer son lien » (une fois par minute au plus), « Changer de magasin », « Retirer ». Ajouter :
  son nom, son WhatsApp, son magasin, puis son lien part sur WhatsApp ; si le WhatsApp d'OCD Live ne peut
  pas partir, le vendeur l'envoie lui-même depuis son WhatsApp (bouton prérempli). 5 personnes au plus
  (réglage « Personnes dans l'équipe d'un vendeur, au plus », modifiable sur la fiche du vendeur). Refusés :
  le numéro d'un vendeur ou d'un livreur, une personne déjà dans une autre équipe. OCD Business : à la fin
  de la formule l'équipe est en pause, rien n'est supprimé, elle revient avec la formule.
- **Mon magasin** (`/ocd/mon-magasin`) : elle se connecte avec son numéro comme le vendeur (son lien, ou
  un code ; la page des vendeurs et celle des colis répondent aussi à son numéro, « Moi » la mène à son
  magasin). Accueil : ses colis (à préparer, retraits, à essayer) et son stock (produits, stock bas), côte
  à côte sur tablette et ordinateur. **Le stock du magasin** : les − / + de chaque taille et couleur de son
  magasin seulement, sans les prix ; un produit dont le stock n'est pas compté reste ainsi (le vendeur le
  décide) ; le vendeur voit qui a changé le stock dans « Mon stock » (« …, par Aïcha »). **Les colis du
  magasin** : l'app des colis limitée aux colis qui partent de son magasin, ses retraits (encaisser puis le
  code du client, l'argent revient au vendeur) et ses pièces à essayer (d'accord, refuser, puis ce qui
  s'est passé ; débloquer un client reste au vendeur), sans les reversements ; ce qu'elle fait est tracé
  sur le colis et la mise de côté. Retirée de l'équipe ou nouveau lien : son téléphone redemande le numéro.
- **WhatsApp** : son lien (« Mon magasin »), puis, si elle l'accepte depuis son accueil, un message quand
  un colis est à préparer ou qu'un client veut essayer une pièce dans son magasin ; le bouton ouvre la
  bonne page. Le vendeur reçoit toujours ses messages. Automatisation « Équipe d'un vendeur ».
- **Back-office** : onglet « Équipe » de la fiche du vendeur (ajouter, renvoyer le lien, retirer), menu
  Shop › « Équipes des vendeurs ». Le lien personnel d'un livreur ou d'une personne d'une équipe n'ouvre
  jamais un espace de vendeur.
- Tests : base neuve, tous les modules OCD : **424 sans échec** (11 nouveaux) ; contrôlé dans un
  navigateur en français en trois tailles (390, 820, 1440 px) : Mon équipe, Mon magasin, le stock du
  magasin, les colis du magasin.
- **À mettre à jour sur un serveur** : `ocd_live` 20.0.1.17.0, `ocd_live_shop` 20.0.1.33.0,
  `ocd_live_shop_whatsapp` 20.0.1.23.0 (`-u ocd_live,ocd_live_shop,ocd_live_shop_whatsapp`). À soumettre à
  Meta (Utility, français et anglais) : `ocd_equipe_lien`, `ocd_equipe_colis`, `ocd_equipe_essai`. Tant que
  `ocd_equipe_lien` attend Meta, la page « Mon magasin » demande un code.

### 17 novembre 2026 · Vendre plus (chantier 21)
Dessiné d'abord (maquettes `PreparerLive`, `TaillesCouleurs`, `StockBas`, validées), puis codé.
- **Alerte de stock bas** : quand une commande laisse une taille ou une couleur à 2 pièces ou moins (mais
  pas à 0), le vendeur reçoit un WhatsApp avec le bouton « Mes produits », une fois par passage sous le
  seuil. Réglage « Alerte de stock bas » (0 : jamais), modifiable sur la fiche du vendeur ; automatisation
  « Stock bas : prévenir le vendeur ». Mes produits : « Stock bas · plus que 2 » (ou les tailles et
  couleurs concernées) et un filtre « Stock bas ».
- **Préparer son prochain live** : sur la carte du live dans Mon espace, « Préparer mon live » : cocher
  les produits, chercher, les mettre dans l'ordre (↑ ↓, aussi sans JavaScript), un mot pour
  l'animatrice ; modifiable jusqu'à la fin du live. La régie montre le mot, « Préparés par Brenda · 3 »
  numérotés, puis « Ses autres produits » ; rien de préparé : tous ses produits comme avant. La
  réservation le montre dans le back-office.
- **Tailles et couleurs dès la création** : en ajoutant un produit, « Plusieurs tailles ou couleurs »
  montre les valeurs des attributs « Proposé aux vendeurs » (à l'installation, la Taille et la Couleur
  d'Odoo, avec des valeurs courantes si elles n'en ont pas) ; chaque valeur cochée dessine la grille du
  stock (couleurs en lignes, tailles en colonnes, le total). Le produit reçoit ses variantes et leur
  stock, vérifié comme avant ; sa ligne s'ouvre ensuite sur les photos des couleurs. Un produit gardé
  dans le téléphone sans réseau garde ses tailles et couleurs. Sur un produit en vente : « Ajouter une
  taille ou une couleur » (sans stock, à remplir dans Mon stock).
- Tests : base neuve, tous les modules OCD : **413 sans échec** (9 nouveaux) ; contrôlé dans un navigateur
  en français en trois tailles (390, 820,
  1440 px) : formulaire avec tailles et couleurs, préparer mon live, Mon espace, Mes produits (stock bas),
  et la régie sur ordinateur.
- **À mettre à jour sur un serveur** : `ocd_live_shop` 20.0.1.31.0, `ocd_live_shop_whatsapp` 20.0.1.21.0
  (`-u ocd_live_shop,ocd_live_shop_whatsapp`). Le WhatsApp est le modèle `ocd_stock_bas` soumis à Meta le
  16 novembre : rien de nouveau à soumettre. Dans les Paramètres d'OCD Live (Shop et livraisons › « Tailles et couleurs des vendeurs » ›
  Attributs), l'équipe coche « Proposé aux vendeurs » sur les tailles, couleurs ou pointures à proposer.

### 17 novembre 2026 · Autour des magasins (chantier 20)
Dessiné d'abord (maquettes `VacancesProximite`, `RetraitMagasin`, `MettreDeCote`, validées), puis codé en
cinq étapes.
- **Mode vacances** (Mon espace › « Mode vacances ») : « De retour le » un jour (60 jours au plus,
  réglable) et un mot pour les clients. Les produits restent visibles, les commandes sont en pause
  partout (bouton du produit, panier même rempli avant, paiement, WhatsApp d'un vendeur en contact
  direct) ; « Préviens-moi à son retour » sur la boutique et le produit ; le jour du retour (ou « Revenir
  maintenant »), les commandes reprennent et les clients sont prévenus sur WhatsApp.
- **Vendeurs près de chez moi** : « Où ? » dans le shop et dans les lives d'un pays, par ville et
  quartier, ou « Près de moi » avec la position du téléphone (jamais gardée) : les produits du vendeur le
  plus proche d'abord, « Akwa · 700 m » sur les cartes ; dans les lives, où vend chaque vendeur ou ses
  vacances.
- **Le bot WhatsApp d'OCD donne les magasins** : « Où êtes-vous ? » reçoit les magasins du vendeur du
  produit ou de la boutique dont parle le client (sinon de sa dernière commande) : adresse, ouvert ou
  fermé, horaires, téléphone, puis la position à ouvrir dans les cartes.
- **Retrait en magasin** : à l'étape « Livraison », par vendeur qui a un magasin, « Livrée chez moi » ou
  « Je passe la récupérer » dans un magasin qui a toute la commande (« Pas toute ta commande ici » pour
  les autres) : gratuit, sans adresse quand tout est retiré ; « Payer au comptoir » au paiement. Le
  vendeur touche « C'est prêt » (onglet « Retrait » de Mes colis) : le client reçoit un WhatsApp avec la
  date limite, son code est sur le suivi (« Prête au magasin », itinéraire). Au comptoir, l'argent
  d'abord (Mobile Money sur son téléphone, ou espèces chez un vendeur qui encaisse déjà), puis le code.
  Rappel la veille ; pas venu à temps (3 jours, réglable) : annulé, pièces rendues au magasin, avoir s'il
  a payé en ligne. Le vendeur reçoit un message à part (« X passe chercher sa commande »).
- **Mettre de côté pour essayer** : sur la fiche produit, sous chaque magasin qui a la couleur et la
  taille choisies ; le client donne son WhatsApp, la pièce est réservée tout de suite (24 h, réglable,
  jusqu'à la prochaine fermeture si le magasin est fermé à cette heure) ; sa page dit où et jusqu'à quand,
  avec l'itinéraire et « Je ne viens plus ». Le vendeur répond dans l'onglet « À essayer » (d'accord ou
  refuser, le client est prévenu), puis : achetée (la pièce sort du stock), pas achetée ou pas venu (de
  nouveau en vente). Une à la fois chez un vendeur ; après 2 absences, plus possible chez lui (le vendeur
  peut débloquer). Délai passé : la pièce revient seule, sans compter d'absence. Back-office : « Pièces
  mises de côté ».
- Corrigé au passage : les onglets de Mes colis restent sur une ligne quel que soit leur nombre. Le
  contrôle des modèles WhatsApp (base neuve) a fait réécrire les nouveaux messages selon les règles de
  Meta : des mots entre deux variables, pas le mot « code » (le bouton d'un colis prêt est « Ma
  commande », le code est sur cette page), assez de mots pour les variables.
- Tests : base neuve, tous les modules OCD : **404 sans échec** (28 nouveaux) ; contrôlé dans un
  navigateur en français en trois tailles (390, 820, 1440 px) : mode vacances, shop « Près de moi », lives
  d'un pays, étape « Livraison » avec retrait, paiement au comptoir, suivi « Prête au magasin », fiche
  produit et ses magasins, demande et page de mise de côté, Mes colis (« Retrait », « À essayer »).
- **À mettre à jour sur un serveur** : `ocd_live` 20.0.1.16.0, `ocd_live_shop` 20.0.1.27.0,
  `ocd_live_shop_whatsapp` 20.0.1.18.0 (`-u ocd_live,ocd_live_shop,ocd_live_shop_whatsapp`), puis soumettre à
  Meta les modèles `ocd_vendeur_de_retour`, `ocd_colis_a_preparer_magasin`, `ocd_colis_pret_magasin`,
  `ocd_colis_rappel_magasin`, `ocd_colis_non_retire`, `ocd_essai_demande`, `ocd_essai_garde`,
  `ocd_essai_refuse` (français et anglais).

### 17 novembre 2026 · Gérer ses produits (chantier 19)
Dessiné d'abord (maquette `GererProduits`, validée), puis codé.
- **Modifier un produit en vente** : le nouveau nom est vérifié par l'équipe pendant que le produit reste
  en vente comme avant ; « Mes produits » dit « Modification en vérification » ou « Modification refusée »
  avec son motif et « Corriger et renvoyer ». Le prix change tout de suite ; au-delà de 50 % d'écart
  (réglage « Écart de prix à confirmer »), le vendeur confirme : « Tu passes de 15 000 F à 1 500 F, c'est
  bien ça ? ». Chaque prix va dans l'historique du produit (onglet « Prix » du back-office).
- **Plusieurs photos** : jusqu'à 8 (réglage), réduites dans le téléphone ; une nouvelle photo est
  vérifiée avant d'être montrée ; « ← » avance une photo, la première devient la photo des cartes ;
  « × » retire une photo, un produit en garde une. Les nouvelles photos des couleurs d'un produit en
  vente sont aussi vérifiées (avant, elles s'affichaient tout de suite).
- **Retirer de la vente** (menu « Plus », ou en bas de la page du produit) : plus montré, jamais effacé,
  « Remettre en vente » d'un geste ; filtre « Retirés ».
- **Sans réseau** : un produit ajouté reste dans le téléphone avec sa photo (« Dans ton téléphone ») et
  part tout seul quand le réseau revient, ou à la prochaine visite de « Mes produits ». Odoo désactivait
  les boutons sans réseau : celui de l'ajout reste utilisable. Essayé dans un navigateur de téléphone :
  réseau coupé, produit ajouté, réseau revenu, produit envoyé et montré.
- **Back-office** : « À vérifier » montre la modification, avant et maintenant côte à côte (nom, photos,
  photos des couleurs, prix déjà changé) ; accepter ou refuser avec un motif. WhatsApp : une modification
  acceptée envoie « produit accepté » ; une modification refusée a son propre message, envoyé une fois
  approuvé par Meta.
- Corrigé au passage : sur téléphone, « Mon stock par magasin » passe sous le produit, en pleine largeur
  comme dans la maquette `DispoMagasins` (il serrait le nom et les chiffres dans une colonne étroite).
- Tests : base neuve, tous les modules OCD : **376 sans échec** (11 nouveaux) ; contrôlé dans un navigateur
  en français en trois tailles (390, 820, 1440 px) : page de modification, question du prix, Mes produits,
  « À vérifier ».
- **À mettre à jour sur un serveur** : `ocd_live` 20.0.1.15.1, `ocd_live_shop` 20.0.1.21.1,
  `ocd_live_shop_whatsapp` 20.0.1.11.1 (`-u ocd_live,ocd_live_shop,ocd_live_shop_whatsapp`), puis soumettre à
  Meta le modèle `ocd_modification_refusee`.

### 16 novembre 2026 · Le stock par magasin (chantier 18)
Dessiné d'abord (maquettes `MonStock`, `EnvoyerStock`, `DispoMagasins`, et le tableau sur ordinateur dans
`RespEspace`), puis codé.
- **Un emplacement de stock par lieu**, dans le stock de l'entrepôt de la boutique : le site compte
  toujours le total, chaque magasin a le sien. Le premier lieu d'un vendeur reçoit les pièces qu'il avait ;
  un lieu retiré rend ses pièces libres au lieu de départ des colis ; chaque mouvement est un transfert
  interne tracé. À la mise à jour, le lieu de départ de chaque vendeur reçoit ses pièces (migration).
- **Mon stock** (Mes produits › « Mon stock par magasin ») : les tailles et les couleurs d'un produit,
  magasin par magasin, avec les − / + qui comptent tout de suite ; les pièces réservées pour une commande
  restent ; « Épuisé ici · 1 à Marché central » ; les derniers changements (ajouté, retiré, envoyé,
  vendu). Les magasins côte à côte sur ordinateur. Dans la liste de Mes produits : « 10 en stock · Akwa 7
  · Marché central 3 ».
- **Envoyer des pièces** d'un magasin à l'autre : seulement les pièces libres, une note, le stock change
  tout de suite dans les deux magasins.
- **Le magasin qui sert une commande** : celui de la ville du client qui a toute la commande, sinon le lieu
  de départ des colis, sinon un autre magasin qui a tout, sinon un colis par magasin, chacun avec son
  code. Le livreur prend chaque colis à son magasin, le prix de la livraison est compté depuis le magasin
  qui servira le panier, et la livraison payée reste sur le premier colis.
- **Pour le client** : la fiche produit dit, pour la couleur et la taille choisies, « Disponible »,
  « Disponible · plus que 2 » ou « Épuisé » dans chaque magasin (jamais le nombre exact d'un magasin),
  ouvert ou fermé, avec « Itinéraire et horaires ». « Préviens-moi » nomme les magasins où le produit est
  revenu, dès que Meta approuve ce message.
- **Back-office** : le stock par lieu sur la fiche produit, les pièces de chaque lieu sur la fiche du lieu
  et l'onglet « Magasins » du vendeur, l'emplacement de chaque lieu pour les gestionnaires du stock.
- Tests : base neuve, tous les modules OCD : **365 sans échec** (16 nouveaux) ; contrôlé dans un
  navigateur en français en trois tailles (390, 820, 1440 px) : fiche produit, Mes produits, Mon stock,
  Envoyer des pièces. Sur ordinateur, la note « 1 réservée pour une commande » passe sous les − / + (elle
  débordait sur le magasin voisin).
- **À mettre à jour sur un serveur** : `ocd_live_whatsapp` 20.0.1.9.0, `ocd_live_shop` 20.0.1.17.1,
  `ocd_live_shop_whatsapp` 20.0.1.10.1 (`-u ocd_live_whatsapp,ocd_live_shop,ocd_live_shop_whatsapp`), puis
  soumettre à Meta le modèle `ocd_produit_de_retour_magasin`.

### 16 novembre 2026 · Tout le site sur tablette et ordinateur, plus de tiret cadratin
Sur ordinateur, la plupart des pages tenaient dans une colonne étroite entre deux bandes vides. Quatre
organisations dessinées puis validées (`RespListes`, `RespFiche`, `RespParcours`, `RespEspace`),
appliquées à toutes les pages ; le téléphone garde son design.
- **Les espaces** : le menu de l'espace (Mon espace, Mes produits, Mes magasins, Mes colis, Mes prix de
  livraison, Ma carte dans le fil, Voir ma boutique, Réserver un live) reste à gauche sur ordinateur,
  en onglets sur tablette. Mon espace en deux colonnes (les lives à gauche ; l'annuaire, la carte et
  la boutique à droite), Ma carte avec son aperçu à gauche, Mes colis côte à côte, la tournée du
  livreur avec l'étape en cours à droite.
- **Les listes** : le shop avec ses catégories à gauche et 5 produits par ligne, le fil des lives en
  grille de cartes, la boutique d'un vendeur (le vendeur, son live et le contact à gauche ; ses
  produits, 4 par ligne, et ses magasins à droite).
- **Les fiches** : la fiche produit (photos à gauche, choix et panier à droite, « Du même vendeur » 6 par
  ligne), le replay (la vidéo à gauche, les moments à droite), le suivi de commande, le ticket (l'image
  pour annoncer le live à droite), la page d'un live (sa carte au centre).
- **Les parcours** : panier et livraison avec le récapitulatif et son bouton à droite dès la tablette,
  l'adresse sur deux colonnes ; le paiement ; la connexion, le code, le pass, le lien d'un live, son
  suivi, le live à distance et le paiement d'un colis avec le titre et son explication à gauche.
- Contrôlé sur 25 pages en trois tailles (390, 820, 1440 px) avec les données de la démo : aucun
  débordement, aucune erreur du navigateur. La façon de faire est dans
  [`DEVELOPPEMENT.md`](DEVELOPPEMENT.md) (section « Grand écran »).
- **Plus de tiret cadratin** dans le projet (documentation, écrans, maquettes) ; un test d'`ocd_live`
  le vérifie sur tout le dépôt.
- La ville d'un lieu n'apparaissait pas dans son formulaire quand le vendeur n'avait pas de pays.
- **Versions** : les modules changés depuis leur dernière version la montent (oublis des derniers
  jours). À mettre à jour sur un serveur : `ocd_live` 20.0.1.14.0, `ocd_live_shop` 20.0.1.12.0,
  `ocd_live_recruitment` 20.0.1.1.0, `ocd_delivery_togo` 20.0.1.0.1, `whatsapp_cloud` 20.0.2.9.0,
  `whatsapp_cloud_sale` 20.0.2.5.0. `tools/versions.py --check` le vérifie avant chaque commit.

### 16 novembre 2026 · Les magasins des vendeurs (chantier 17)
Dessiné d'abord (maquettes `MesMagasins`, `MonMagasin`, `VitrineMagasins`, `BoVerificationMagasins`,
validées), puis codé.
- **Les lieux d'un vendeur** : un magasin ouvert au public, ou « je vends depuis chez moi ». Un magasin est
  vérifié par l'équipe avant d'être montré (photo de la devanture avec l'enseigne, position prise dans le
  magasin) ; seuls l'adresse, la position et la photo repassent à la vérification, et le magasin est caché
  pendant ce temps ; horaires, téléphone et « fermé jusqu'au… » changent tout de suite. Un domicile est
  montré aussitôt, son quartier seulement. Un refus envoie son motif (devanture absente, position loin de
  l'adresse, adresse introuvable) : le vendeur corrige et renvoie.
- **Mes magasins** (espace vendeur) : ajouter, modifier, retirer ; « Je suis dans mon magasin » prend la
  position du téléphone (refusée au-delà de 200 m de précision) ; photo réduite dans le téléphone ;
  horaires par jour (proposés par l'équipe) ; fermé pour un temps ; « Cette semaine : 18 itinéraires,
  6 appels, 4 messages WhatsApp » ; un seul envoi même si le formulaire part deux fois. Le démarrage du
  vendeur a une étape de plus : « Dis où te trouver ».
- **Ses magasins** dans la boutique : « 2 magasins à Douala » sous le nom, puis pour chaque magasin la
  photo, le quartier et le repère, « Ouvert · ferme à 19:00 » ou « Fermé · ouvre lundi à 08:00 » à l'heure
  du magasin, les horaires repliés, et Itinéraire (Google Maps ou OpenStreetMap, au choix de l'équipe),
  Appeler, WhatsApp. Chaque appui est compté une fois par visiteur toutes les 10 minutes. La fiche produit
  dit « Aussi en magasin : Akwa, Bonapriso ». L'en-tête de la boutique ne montre plus le repère personnel
  du vendeur.
- **À imprimer** : l'affiche QR d'un magasin (A4 à 300 points par pouce, claire pour économiser l'encre,
  texte réglé par l'équipe) et une feuille d'étiquettes de prix avec le QR de chaque produit (3 × 8 par
  page A4, nombre d'exemplaires au choix, imprimée depuis le téléphone ou envoyée en PDF à un imprimeur).
- **Départ des colis** : le vendeur choisit le lieu d'où partent ses colis ; le prix de la livraison est
  compté depuis sa ville, le colis garde le lieu où le livreur le prend (même si le vendeur change d'avis
  ensuite), et l'appli du livreur montre ce lieu, son repère et l'itinéraire.
- **OCD Business** : un lieu sans la formule, plusieurs avec (date de fin sur la fiche du vendeur) ; à la
  fin, rien n'est effacé, les lieux au-delà du premier ne sont plus montrés. Tant que la formule n'est pas
  lancée, l'interrupteur « Fonctions OCD Business offertes à tous » les ouvre à chacun.
- **Back-office** : menu « Magasins des vendeurs » (filtres par ville, vendeur, état, carte), onglet
  « Magasins » sur la fiche du vendeur, colonne « Nouveaux magasins » de l'écran « À vérifier » (avant /
  maintenant après un changement d'adresse), nombre de magasins à vérifier au tableau de bord, et dans les
  Paramètres : vente depuis chez soi, vérification, devanture et position obligatoires, cartes, texte de
  l'affiche, horaires proposés, lieux par vendeur.
- **WhatsApp au vendeur** quand l'équipe accepte ou refuse un magasin ou un produit (avancé du chantier 19,
  même mécanique) : un message par vendeur quand l'équipe en vérifie plusieurs à la fois, interrupteur dans
  les Automatisations. Rien ne part tant que Meta n'a pas approuvé le modèle.
- Un test d'`ocd_live` comptait les passages d'une tâche planifiée depuis zéro : le planificateur du
  serveur la lance parfois pendant les tests ; il compte maintenant à partir des passages déjà faits.
- Tests : base neuve, tous les modules OCD : **348 sans échec** (12 nouveaux : magasins, affiche,
  étiquettes, départ des colis, messages) ; vérifié dans un navigateur de téléphone (Pixel 7), en
  français : boutique, fiche produit, Mes magasins, affiche, étiquettes à l'écran et à l'impression.

### 16 novembre 2026 · « Mes produits » aide à vendre (chantier 16, étape 1 du plan)
- **Ce que les produits ont rapporté**, sous chaque produit : « 7 personnes t'ont écrit sur WhatsApp »
  (compté par OCD, vu jusqu'ici seulement par l'équipe), et sur un produit épuisé « 2 clients attendent
  son retour » (les « Préviens-moi »). Une requête pour toute la page.
- **Un menu « Plus »** sous chaque produit, replié sur le téléphone, sans JavaScript : le voir dans ma
  boutique, partager, faire une copie, mettre en premier, monter, descendre.
- **L'ordre de la boutique** : « Mes produits » montre les produits comme les voient les clients ; un
  nouveau produit ou une copie arrive en premier ; un déplacement n'écrit qu'un ou deux produits, ceux des
  autres vendeurs gardent leur place ; le menu reste ouvert après un déplacement.
- **Faire une copie** (même modèle, autre tissu) : sans stock ni historique, vérifiée par l'équipe comme un
  nouveau produit ; le vendeur arrive sur sa fiche pour changer le nom ou la photo.
- **Filtres par état** dès 5 produits dans au moins deux états (Tout, En vente, Épuisés, À vérifier,
  Refusés) : des liens qui marchent sans JavaScript, appliqués aussitôt avec, l'adresse garde le filtre.
- **Partager un produit avec son image** : une image au format du statut WhatsApp (1080 × 1350 : photo,
  nom, prix, boutique, QR code de la page), dessinée comme l'annonce d'un live ; publique comme la page du
  produit, gardée un an par son adresse. Le téléphone la prépare dès l'ouverture du menu (il n'ouvre sa
  feuille de partage que juste après le toucher).
- **Catalogue pour mon statut** : les produits en vente avec du stock, dans l'ordre de la boutique, 4 par
  image (réglable, 1 à 4), répartis équitablement, avec le QR code de la boutique ; partagés d'un coup, un
  par un ou téléchargés.
- **Démarrage du vendeur** dans « Mon espace » : « Ta boutique est prête à 75 % », avec les étapes (premier
  produit, 5 produits en vente, boutique partagée, première vente ou, en contact direct, premier client
  sur WhatsApp) et un lien vers chacune ; le bloc disparaît quand tout est fait. Le téléphone signale un
  partage réussi (balise, sans formulaire).
- Tests : base neuve, tous les modules OCD : **336 sans échec** ; vérifié dans un navigateur de téléphone
  (Pixel 7), en français.

### 16 novembre 2026 · « Mes produits » fiable (chantier 15, étape 0 du plan)
Premier chantier de [`PLAN_MES_PRODUITS.md`](PLAN_MES_PRODUITS.md) : les corrections de la page du
vendeur, avant les ajouts.
- **Boutons − / + du stock** : la page montrait le stock libre (moins les pièces réservées par les
  commandes) mais l'enregistrait comme stock total : avec 5 en stock dont 2 réservées, la page montrait
  3, « + » posait 4 et la page montrait 2 ; et le chiffre de la page écrasait une vente faite entre-temps.
  Les boutons envoient maintenant +1 ou −1, ajoutés au stock du moment : les pièces des commandes ne
  sont jamais retirées, chaque changement reste tracé (ajustement d'inventaire), deux appuis rapides
  comptent deux fois. Le stock de toute la page se calcule en une requête, quel que soit le nombre de
  produits. Chaque méthode prend l'emplacement : prête pour le stock par magasin.
- **Prix** : « 2500,50 » devenait 250 050, « 3000-5000 » 30 005 000 (tous les chiffres gardés). Un seul
  lecteur de montant (`tools.parse_amount`, le même dans le téléphone) lit « 3 000 », « 3.000 F »,
  « 15 000 FCFA », « 3000frs », les centimes seulement dans une devise qui en a, et refuse le reste avec
  un message clair. Aussi pour les prix de livraison des vendeurs, qui avaient le même défaut.
- **Le formulaire sur un réseau lent** : le téléphone vérifie le nom, le prix et la photo avant l'envoi
  (plus de rechargement pour un oubli) ; une erreur vue par le serveur garde la photo reçue (plus besoin
  de la reprendre) ; un second appui ne crée plus un second produit (bouton « Envoi… », jeton du
  formulaire verrouillé par le serveur) ; la photo est réduite dans le téléphone avant l'envoi (une photo
  de 10,9 Mo partie en 946 Ko).
- **Galerie ou appareil photo** : « Ajouter une photo » ; nouvelle raison de refus « Photo qui n'est pas
  la tienne ».
- **Un refus dit pourquoi** (la décision de l'équipe le prévoyait, le code non) : le motif reste sur le
  produit (le bouton « Refuser » de la fiche l'exige), le vendeur le lit sous le produit, le corrige et
  le renvoie ; l'équipe voit « Renvoyé après un refus : … ». Le vendeur voit enfin la photo d'un produit
  pas encore en ligne (son adresse publique donnait l'image par défaut d'Odoo).
- **Voix et aide** de la page (prévues par le design validé), lues par la voix du téléphone tant que
  l'équipe n'a pas enregistré la sienne.
- **Paramètres › Produits et magasins des vendeurs** (nouvelle section) : photos de la galerie, photo la
  plus lourde (10 Mo, auparavant écrit dans le code), taille de réduction (1600 px).
- **Trois modèles WhatsApp à soumettre à Meta** (*Utility*, français et anglais) : produit accepté,
  produit refusé avec son motif, stock bas. Leur bouton ouvre « Mes produits » par le lien personnel.
  Ils partiront avec les chantiers 19 et 21 ; les soumettre dès maintenant.
- Tests : base neuve, tous les modules OCD (`ocd_live`, shop, WhatsApp, recrutement, Togo,
  `ocd_debranding`) : **329 sans échec** ; vérifié dans un navigateur de téléphone (Pixel 7), en
  français et en anglais.

### 15 novembre 2026 · Les étapes d'une réservation sur le téléphone : où l'on est, la sortie, l'aide
- Sur le téléphone, le menu laisse la place aux étapes de la réservation (parcours fermé : moins de
  distractions, la place pour le résumé et le bouton). Trois manques comblés :
  - **où l'on est** : le nom de l'étape sous la barre, « 2/5 · Heure » (Jour, Heure, Paquet, Tes infos,
    Paiement), aussi lu par les lecteurs d'écran ;
  - **une sortie** : une croix en haut à droite ramène à l'accueil ; un formulaire déjà rempli demande
    « Quitter la réservation ? Ce que tu as écrit sera perdu. » avant de partir (sur tablette et
    ordinateur, le logo et le menu restent, sans croix) ;
  - **l'aide** : « Une question ? Écris-nous sur WhatsApp » à chaque étape, paiement compris (sauf quand
    la page propose déjà d'écrire à l'équipe), avec un message prêt et l'adresse de la page, pour que
    l'équipe voie où en est le vendeur. Pas de lien sans le téléphone de l'entreprise.
- Les textes des scripts d'`ocd_live` sur le site (« Pause the video »…) restaient en anglais : le site
  n'envoyait pas leurs traductions à ses pages. Corrigé (`ir.http`). Vérifié avec un navigateur de
  téléphone, en français.

### 15 novembre 2026 · Les robots hors du calendrier des réservations
- Un robot parcourait une à une les étapes de réservation de la préproduction (chaque mois, jour, heure
  et formule, en chaque langue : des milliers de formulaires, 32 requêtes et ~0,2 s chacun, jamais gardés
  en mémoire), malgré le `noindex` de la plateforme : `noindex` empêche d'apparaître dans les résultats,
  pas d'être visité.
- `robots.txt` interdit `/reserver/` et `/*/reserver/` (la page « Réserver » reste ouverte) ; les étapes
  portent `noindex, nofollow`, les liens du calendrier (mois, jours, heures, formules) `rel="nofollow"`.
- Le visiteur continue ensuite par rafales (jusqu'à ~9 pages/s, les deux workers de la préproduction
  occupés), en rejouant une liste d'adresses de la dernière étape, une nouvelle session à chaque vague :
  il ne lit pas `robots.txt`. Une ligne de journal (adresse et navigateur de chaque étape demandée) a
  servi le temps que la plateforme transmette l'adresse réelle des visiteurs, puis a été retirée.
- La plateforme a corrigé `proxy_mode` : le journal d'Odoo montre l'adresse réelle des visiteurs (et non
  plus celle de son entrée, 10.42.2.1), et la base GeoIP (GeoLite2) est installée : le pays du visiteur
  vient de nouveau de son adresse dès la première page (`geoip_country_code` vérifié de l'extérieur).

### 15 novembre 2026 · Test de charge refait pour 3 millions de visiteurs par jour
- Coût de chaque page mesuré en processeur (Odoo et PostgreSQL), gardée en mémoire et construite, et le
  parcours refait : ~570 pages/s sur la machine de test, 95 % depuis la mémoire, aucune erreur jusqu'à 32
  visiteurs à la fois. Détail dans [`RAPPORT_DE_CHARGE.md`](RAPPORT_DE_CHARGE.md#7-3-millions-de-visiteurs-par-jour-15-novembre-2026-après-le-cdn).
- Ce que ça dit : chaque worker garde sa propre copie des pages ; avec un vrai catalogue et ~260 workers,
  29 % des pages viennent de la mémoire et la pointe d'un live demande ~130 cœurs pour Odoo et ~35 pour
  PostgreSQL. Une mémoire commune aux workers descend à ~50 cœurs ; la page d'un produit (124 ms à
  construire) est la plus chère. La plateforme envoie les pages sans compression.
- Nouvel outil `tools/charge/dimensionnement.py` : les cœurs pour N visiteurs par jour, à refaire avec
  les chiffres d'un vrai soir.

### 15 novembre 2026 · CDN en place : le type des vidéos des cartes, des exemples qui ne visent personne
- Le CDN tourne (Cloudflare devant `ocd.my.rollbackk.app`, sur une adresse à part) : vérifié avec un
  navigateur de téléphone, les fichiers, les polices, les photos et la vidéo d'une carte viennent du CDN,
  gardés un an (`MISS` puis `HIT`, aussi par morceaux), les pages restent sur le serveur.
- Les vidéos des cartes partaient en `application/octet-stream` (Odoo sans libmagic ne reconnaît pas un
  MP4) : elles partent en `video/mp4` ou `video/webm`, selon leur nom. Chrome les jouait, Safari joue une
  vidéo selon son type. Cloudflare garde les en-têtes avec la vidéo : vider son cache une fois après la
  mise à jour (Caching › Configuration › Purge Cache).
- Les exemples d'adresses (`ocdlive.com`, un domaine qui n'est pas à OCD Live) deviennent `example.com` :
  l'aide de l'adresse du CDN, les tests, les commandes du test de charge (copiées telles quelles, elles
  auraient chargé le serveur de quelqu'un d'autre).

### 15 novembre 2026 · CDN : les polices des icônes, la marche à suivre avec Cloudflare
- Servies depuis l'adresse du CDN pour une page du site, les polices des icônes auraient été refusées par
  les navigateurs (une police ne se prend sur une autre adresse qu'avec `Access-Control-Allow-Origin`, qu'Odoo
  n'envoie pas). Les fichiers, les photos et les vidéos demandés sans session portent maintenant cet
  en-tête : aucune règle à ajouter chez le CDN. Vérifié avec un navigateur, le site pointant vers une
  autre adresse : fichiers, photos, vidéos et polices chargés, aucune erreur.
- La marche à suivre avec Cloudflare (DNS, certificat, règle de cache, nginx, Paramètres) est dans
  [`DEVELOPPEMENT.md`](DEVELOPPEMENT.md#mise-en-production-pour-le-grand-public).

### 15 novembre 2026 · tenir les foules d'un live : pages en mémoire, médias à part, rapport de charge
- **Pages publiques gardées en mémoire** : le fil des lives, la page d'un live, les boutiques, le shop et
  les produits sont construits une fois, puis redonnés pendant 10 à 60 secondes aux visiteurs qui n'ont
  encore rien à eux sur le site (pas connectés, sans vendeur ni livreur sur leur téléphone, sans panier).
  Le jeton des formulaires est remis pour chaque visiteur ; les liens venus de Facebook ou TikTok
  (`fbclid`, `utm_…`) reçoivent la même page. Réglable : Paramètres › Vitesse du site. Mesuré sur la
  machine de test : de 23 à 76 pages par seconde selon la page à 250 à 500, réponse médiane de 200 à
  700 ms à 30 à 60 ms ; le parcours complet passe de ~45 à ~300 pages par seconde.
- **Questions répétées** : une page cachée (autre appli, autre onglet) ne demande plus les nouveaux
  lives, le produit à l'écran ou l'état d'un paiement : elle le fait dès qu'on revient. Les nouveaux lives
  et le produit à l'écran sont lus une fois pour tous les visiteurs.
- **Médias servis à part** : photos et vidéos des cartes, photos des produits avec leur version dans
  l'adresse, gardées un an par les téléphones et par le CDN, sans cookie ; adresse du CDN dans
  Paramètres › Vitesse du site (Odoo y envoie aussi ses propres fichiers). Capture :
  `backoffice-12d-parametres-vitesse.png`.
- **Visites d'une boutique pendant un live** : écrites toutes les 5 secondes par chaque serveur. Avant, en
  pointe, chaque visite attendait les autres (60 conflits pour 2 000 visites, 10 pages en erreur) ;
  maintenant aucun, et 172 pages par seconde au lieu de 45.
- **Modèle de rapport de charge** ([`RAPPORT_DE_CHARGE.md`](RAPPORT_DE_CHARGE.md)) : objectifs (600 pages
  par seconde en pointe pour 1 million de visiteurs par jour, 1 800 pour 3 millions), méthode, tableaux à
  remplir sur la préproduction et la production, mesures de référence ; outil `tools/charge/charge.py`.
  Réglages des serveurs pour le grand public dans [`DEVELOPPEMENT.md`](DEVELOPPEMENT.md).

### 13 novembre 2026 · le lien partagé d'un live ouvre ce live
- **Avant** : l'image et le message « Je passe en live » donnaient `domaine/lives/cm` (la boutique du vendeur
  une fois validé, sinon les lives de tout son pays) : un ami tombait sur les lives du pays entier.
- **Maintenant** : `domaine/lives/cm/<numéro du live>`, la page de ce live : avant, « Prochain live », le
  jour et l'heure dans le fuseau du visiteur et « Reviens à l'heure du live » ; pendant, « Regarder » (le
  compte d'OCD Live ou le lien du live) ; après, son replay, sinon « Live terminé ». Aussi pour un vendeur
  pas encore validé (ses initiales, pas de boutique). Un live annulé renvoie aux lives du pays ; sans le
  numéro, l'adresse donne les lives du pays. Le bouton de partage des cartes du fil donne aussi la page
  du live. Capture : `site-phone-d-5-page-d-un-live.png`.

### 13 novembre 2026 · page d'erreur juste après un paiement, ticket pas reçu sur WhatsApp
- **Page 500 après le paiement** (`/payment/status`, vu sur le staging après un paiement CamPay de démo) :
  la page d'attente du paiement (réservation, pass, boutique) est une page d'Odoo dans le cadre d'OCD Live.
  Depuis le bouton de langue (9 novembre), le cadre lisait la liste des langues des pages d'OCD, absente de
  cette page : erreur juste après chaque paiement en ligne, alors que le paiement était bien enregistré.
  La page reçoit maintenant les valeurs des pages d'OCD, et le cadre tolère leur absence.
- **CamPay : la vérification du paiement ne peut plus se bloquer** : la page qui attend la confirmation
  sur le téléphone faisait traiter le paiement dans sa propre requête, dont le traitement attendait les
  verrous (la requête pouvait rester bloquée jusqu'à être coupée). Le résultat de CamPay est mis en file,
  et la page d'attente d'Odoo le traite dans une autre requête, comme pour les autres fournisseurs.
- **Ticket pas reçu sur WhatsApp, modèle pourtant approuvé** : pour un modèle soumis par Odoo puis approuvé
  (seule la décision est relue chez Meta), Odoo ne savait pas que le bouton attend la fin de son adresse
  et ne l'envoyait pas : Meta refusait le message. Tous les messages à bouton soumis depuis Odoo étaient
  concernés (ticket, « Mon espace », « Suivre mon colis »…). La fin de l'adresse part dès que le bouton du
  modèle se termine par une variable.
- Reproduit de bout en bout sur une copie de la démo, avec un faux CamPay et un faux Meta : paiement de
  démo à 25 F CFA, page d'attente, retour sur la réservation payée, ticket avec son bouton. Tests : CamPay,
  WhatsApp et pages du site, 174 sans échec ; boutique, 108 sans échec.

### 12 novembre 2026 · modèles WhatsApp refusés par Meta (INCORRECT_CATEGORY)
- **Le motif** : Meta prenait quatre modèles *Utilitaires* pour des messages d'*Authentification* (réservés
  au code à usage unique) : « colis en route » (le code à donner au livreur, même sans le donner), « ticket
  du live » (un numéro « que l'équipe vous demandera »), « lien personnel » (« gardez-le pour vous ») et
  « choisir un mot de passe » (un compte à activer, un identifiant). En français et en anglais.
- **Nouveaux textes**, qui disent ce qui s'est passé : « votre colis … est en route avec … Le livreur vous
  appellera avant de passer » (le code reste sur la page de suivi) ; « votre ticket … est joint à ce
  message … Référence du ticket » ; « vous avez demandé votre espace vendeur » ; « l'équipe d'OCD Live a créé
  votre espace vendeur », bouton « Terminer mon inscription ». Par prudence, même chose pour le lien de
  l'appli de livraison et « livraison pas possible » (ils avaient les mêmes mots).
- **Mise à jour des bases** (`ocd_live_whatsapp` 20.0.1.8.0, `ocd_live_shop_whatsapp` 20.0.1.7.0) : les
  modèles refusés (ou en attente, ou pas encore synchronisés) prennent les nouveaux textes ; un modèle
  approuvé garde le sien.
- **Odoo prévient avant Meta** (`whatsapp_cloud` 20.0.2.8.0) : un texte Utilitaire avec « code », « mot de
  passe », « identifiant », « lien personnel »… n'est pas soumis, le message dit pourquoi. **Soumission
  groupée** : WhatsApp › Modèles, cocher les modèles, Action › « Soumettre à Meta ».
- **La connexion ne dépend plus de la décision de Meta** : tant que le modèle du lien personnel est refusé
  ou en attente, la page de connexion des vendeurs (et celle des livreurs) envoie un code, par le modèle
  d'authentification ; le lien revient quand Meta l'approuve.
- Tests : WhatsApp (`whatsapp_cloud`, `whatsapp_cloud_sale`, `ocd_live_whatsapp`, `ocd_live_shop_whatsapp`) et
  pages du site, 178 tests, un seul échec, connu (« commande confirmée puis expédiée ») ; boutique, 108 sans
  échec. Base de démo mise à jour : les 12 modèles ont leurs nouveaux textes.

### 12 novembre 2026 · devises par pays et paiements de démo CamPay
- **Devises par pays** (Paramètres › Devises par pays, bouton « Mettre en place les devises par pays ») :
  quatre listes de prix par groupe de pays. Les prix restent écrits en XOF ; l'UEMOA les voit en XOF, la
  CEMAC en XAF (donc CamPay est proposé au Cameroun), l'Europe et le reste de l'Afrique en euros, les
  Amériques, l'Asie et l'Océanie en dollars. Les francs et l'euro sont à leur parité fixe (655,957), le
  dollar est lu chaque jour auprès de la BCE. Prix et frais de livraison arrondis à l'unité en euros et
  en dollars : Découverte 15 000 F CFA = 15 000 FCFA = 23 € = 25 $. La section montre les zones, les taux
  et cet exemple ; un bouton relit le dollar du jour.
- **Shop** : le pays affiché est celui du visiteur dans sa zone (plus le drapeau du premier pays de la
  liste).
- **Paiements de démo CamPay** (Paramètres › Paiements et reversements) : chaque paiement CamPay encaisse
  25 F CFA (montant au choix) au lieu du prix, pour tous les numéros ou pour une liste, jusqu'au dernier
  jour. Les pages gardent les vrais prix ; la commande est payée comme d'habitude, la comptabilité
  enregistre les 25 F CFA reçus, une note le dit sur la commande ; ligne rouge sur le tableau de bord,
  filtre « Paiements de démo » dans les transactions. Le module CamPay dépend maintenant
  d'`account_payment` (sans quoi la comptabilité aurait pu enregistrer le prix au lieu de l'argent reçu).
- **Démo** : les devises par pays sont en place (Brenda à Douala en FCFA, Kadi à Paris en euros).

### 12 novembre 2026 · « Ma carte dans le fil » : la photo et la vidéo d'un vendeur pas encore validé
- **La photo cassée** : les médias d'une carte n'étaient servis que pour un vendeur validé ; un vendeur
  qui vient de s'inscrire voyait des images cassées dans « Ma carte dans le fil ». Avant la validation,
  le vendeur et l'équipe voient ses médias ; le fil public, seulement après.
- **La vidéo pas gardée** : en production, chaque requête d'Odoo est limitée (60 s de calcul, mémoire) et
  ffmpeg, lancé par elle, prenait ces limites : la conversion d'une vraie vidéo de téléphone pouvait être
  coupée. ffmpeg tourne maintenant sans elles (avec sa propre durée maximale), et la vidéo est préparée
  **en arrière-plan** : la page répond tout de suite, dit « En préparation » et se met à jour seule ; un
  refus dit pourquoi, et reste affiché.
- **Envoi avec sa progression** (pourcentage), jusqu'à 200 Mo (une à deux minutes filmées au téléphone) ;
  un refus du proxy (« 413 ») ou du réseau dit quoi faire. Les erreurs d'un envoi restent sur la page
  rouverte (la recharger n'envoie rien deux fois).

### 12 novembre 2026 · liens courts des vidéos acceptés
- Un lien court de TikTok (« Partager › Copier le lien » : `vt.tiktok.com/ZS…`, `vm.tiktok.com/…`,
  `tiktok.com/t/…`) ou de Facebook (`fb.watch/…`) était refusé pour la vidéo des replays : il ne contient
  pas le numéro de la vidéo, que la page du replay doit avoir pour la lire. Il est maintenant suivi
  jusqu'à l'adresse complète (sans les paramètres de suivi), gardée à sa place : réglages de la démo,
  régie (« Publier le replay »), fiche du live. Si la plateforme ne répond pas, le message dit de coller
  l'adresse complète de la vidéo.

### 12 novembre 2026 · page produit : « Ajouter au panier » et « Écrire sur WhatsApp » réparés ; ffmpeg par pip
- **Les boutons du bas de la page produit ne faisaient plus rien** dans un navigateur, depuis
  « Préviens-moi quand il revient » : son formulaire était dans celui du produit, le navigateur coupait
  alors celui du produit avant ses boutons. Il est maintenant à part (relié à ses champs par
  `form="…"`) : « Ajouter au panier » ajoute au panier, « Écrire à Awa sur WhatsApp » ouvre WhatsApp avec
  le message (produit, choix, lien), « Préviens-moi » note la demande. Les tests envoyaient les formulaires
  directement : un test vérifie maintenant qu'aucun formulaire n'est dans un autre et que chaque bouton
  envoie le sien.
- **ffmpeg par pip** : `imageio-ffmpeg` (dans `requirements.txt`) donne un ffmpeg sans
  `apt-get` ; les vidéos des cartes se convertissent avec lui quand le serveur n'a pas le sien (il n'a
  pas ffprobe : ffmpeg lit lui-même la durée et les pistes).

### 12 novembre 2026 · cartes du fil claires, médias des vendeurs, lives à distance sur les comptes d'OCD
- **Cartes du fil épurées** : fond blanc et sable, textes à l'encre, la couleur seulement pour l'état du
  live (rouge en live, orange pour le prochain, violet pour le replay) et le bouton principal. En haut le
  média, en bas l'état, le nom, la catégorie et les boutons : ils ne se chevauchent plus et restent
  lisibles quelle que soit la photo (le nom était noir sur la photo à cause d'une règle commune).
- **Le média de la carte, au choix** (espace du vendeur › « Ma carte dans le fil », ou fiche du vendeur ›
  « Carte dans le fil ») : une **vidéo courte** (30 s au plus, jouée sans le son quand la carte est à
  l'écran, le son et la pause au toucher, jamais quand la personne a demandé moins d'animations ou
  d'économiser ses données), le **carrousel de ses produits** (en vente, vérifiés, avec photo, les épuisés
  à la fin ; un toucher ouvre le produit ; il défile seul jusqu'à ce qu'on le touche) ou une **image**.
  « Automatique » : la vidéo, sinon les produits, sinon l'image ; ce qui manque laisse la place au suivant.
  La page montre la carte telle que le fil la montre.
- **Vidéo robuste** : avec ffmpeg sur le serveur, toute vidéo de téléphone (MP4, MOV, 3GP, WebM…) est
  rendue lisible partout (MP4, 720 px, 30 s, démarrage immédiat) avec son affiche ; sans ffmpeg, MP4 et
  WebM sont gardés tels quels (15 Mo au plus). Le type est reconnu même sans libmagic. Les téléphones la
  lisent par morceaux (requêtes partielles).
- **« Regarder sur TikTok » n'est plus imposé** : les plateformes sont une liste de l'équipe (Configuration
  › Plateformes de live) ; un lien est reconnu par son adresse et la carte dit « Regarder sur » + son nom.
- **Comptes de live d'OCD Live** (Configuration › Comptes de live) : plusieurs comptes (un par pays, un pour
  le studio…). Chaque live prend le premier compte de son mode et du pays du vendeur, libre à son heure ;
  l'équipe peut le changer ; les lives déjà réservés prennent un compte ajouté ensuite.
- **Live à distance, le vendeur invité sur le compte d'OCD** : 30 min avant, l'animatrice a une activité
  « Appeler le vendeur » (un essai) ; 15 min avant, le vendeur reçoit sur WhatsApp « Rejoindre mon live »
  (nouveaux modèles `ocd_live_rejoindre` et `ocd_live_animatrice`, français et anglais) : les trois gestes,
  « Je suis prêt », « J'ai un problème », son nom sur TikTok, l'animatrice à appeler ; 5 min avant, s'il
  n'a pas dit être prêt, l'animatrice est alertée. Le choix de l'animatrice est annoncé au vendeur. La
  fiche du live et la régie montrent où il en est (prêt, invité, problème) avec Appeler, WhatsApp et
  « Vendeur appelé ». Sans WhatsApp, le lien à donner au vendeur est noté sur le live.
- Corrigé : la règle du contrôle des tickets donnait un cadre sable à toutes les cases à cocher du site
  (« Recevoir mon ticket sur WhatsApp »).
- Démo : Awa a sa vidéo, Ama son image, les autres le carrousel de leurs produits ; les comptes OCD Live
  Togo et OCD Live Afrique sur TikTok ; les noms TikTok des vendeurs, les téléphones des animatrices.

### 12 novembre 2026 · la boutique de Douala tenue à jour, textes des modules après une mise à jour
- **La boutique de Douala avance chaque jour**, comme les lives : six commandes par jour (heure de
  Douala), chaque colis selon son histoire : livré en espèces ou payé sur le téléphone, une vendeuse en
  retard (Brenda rappelée à 13 h 10, dispatch alerté à 15 h 10, livré le lendemain), un client absent
  (Bertrand, livré le lendemain après 17 h), Fatou qui livre elle-même (le lendemain matin pour une
  commande du soir). Les livreurs remettent leurs espèces à 19 h 30 ; les reversements de Brenda et Fatou
  (chaque jour, par Mobile Money) sont prêts à 7 h et payés par l'équipe le lendemain à 10 h.
- **Les conversations WhatsApp suivent les colis** : commande confirmée, colis en route avec le code,
  livraison manquée, colis à préparer et rappel à la vendeuse, et les questions des clients avec les
  réponses de l'équipe, à leur heure. Le tableau de bord ne montre plus un client « qui attend depuis
  1 250 minutes ».
- Chaque étape n'a lieu qu'une fois (`ocd.live.demo.event`), à son heure, même si l'action planifiée
  passe en retard ou après un arrêt du serveur ; ce que l'équipe fait pendant une présentation (livrer
  avec le code, signaler un problème) reste tel quel. Le stock reste à son niveau (« Plus que 3 »),
  sans mouvement de stock : la démo se retire toujours entièrement (remises de caisse comprises).
- Une démo installée avant : la mise à jour livre les colis restés figés de l'ancien scénario le soir de
  leur commande (leurs espèces partent avec la caisse de ce soir-là).
- **Textes des modules dans Applications** : le nom, le résumé et la description suivent leurs
  traductions à chaque mise à jour d'un module. Odoo gardait ceux de la première installation (les fiches
  des modules sont « à ne pas mettre à jour »), même avec `--i18n-overwrite` : un résumé changé restait
  ancien en français.
- `ocd_live_shop` : la règle « vendeur en retard » (rappel, puis alerte du dispatch) se lance aussi sur un
  colis à un moment donné (`_ocd_escalate`) ; la tâche planifiée fait la même chose qu'avant.
- `ocd_live_demo` 20.0.1.2.0 (Brenda et Fatou payées chaque jour, Fatou prépare le lendemain matin les
  commandes du soir).
- **Une vraie vidéo et un vrai compte pour présenter** (OCD Live › Configuration › Paramètres › Démo) :
  la vidéo des replays (YouTube, TikTok ou Facebook, refusée si elle ne se lit pas dans la page) et sa
  durée, le lien des lives de la démo. Tous les replays et lives de la démo les prennent aussitôt, ceux
  des jours suivants aussi ; les produits montrés sont placés le long de la vidéo ; un lien collé à la
  main reste ; vides, les liens d'exemple reviennent. `ocd_live_demo` 20.0.1.3.0.

### 12 novembre 2026 · démo de présentation : 8 pays, tenue à jour
- **15 vendeurs dans 8 pays**, chacun avec une histoire cohérente (ville, ce qu'il vend, produits avec
  photos, lien de live, heures) : Togo (Awa, Ama Pagnes, Kossi Tech, Yao à vérifier), Cameroun (Brenda,
  Fatou, Papa Ndolé), Côte d'Ivoire (Junior, Adjoua Attiéké), Sénégal (Aminata, Moussa Bazin), Bénin
  (Mireille), Ghana (Akua Kente), Nigeria (Chioma Hair), Paris (Kadi Épices, la diaspora). 16 produits
  de plus, dessinés dans le style des photos de la démo.
- **Tenue à jour** par une action planifiée (toutes les 15 minutes), quel que soit le jour de la
  présentation : lives de l'annuaire dans la fenêtre du moment (un lien attend toujours l'équipe), semaine
  du studio (les vendeurs de Lomé au studio, les autres à distance avec une animatrice ; samedi complet et
  liste d'attente ; un live sans animatrice), replays de la semaine passée avec les produits montrés, un
  paiement Mobile Money de Kossi à vérifier, les pass rachetés. Chaque live est payé à sa réservation
  (prix de l'heure compris) et daté comme en vrai : le tableau de bord et le graphique sont réalistes.
  Elle n'ajoute que ce qui manque : ce que l'équipe fait pendant une présentation reste.
- **Deux fenêtres de vérification de plus dans la démo** (Midi 11 h – 14 h 30, Après-midi 14 h 30 – 18 h) :
  l'annuaire a des lives de 8 h à 21 h, chacun d'environ trois heures. Les réservations n'ont plus de
  date d'ouverture dans la démo (remise à la désinstallation).
- **Aucun WhatsApp vers les contacts de la démo** (`ocd_live_demo_whatsapp`, installé avec elle quand
  WhatsApp est là) : avec le vrai compte connecté, les tickets, rappels et messages des colis de ces
  numéros d'exemple partaient chez des inconnus. La fenêtre d'envoi de WhatsApp dit pourquoi.
- **Fil des lives** : un seul prochain live et un seul replay par vendeur (les autres sont dans sa
  boutique). Avec les données réalistes, un visiteur de Lomé voyait 2 lives puis 14 prochains lives
  togolais avant le premier live d'un autre pays.
- **Correction trouvée grâce à la démo** : « Paiement reçu : marquer payé » (planning) échouait sur un
  Mobile Money choisi par le vendeur (Odoo 20 protège les transactions) ; il confirme maintenant le
  paiement et le live.
- **Scénario de présentation** dans [`DEMO.md`](DEMO.md) : les vendeurs, qui est en live à quelle heure,
  le parcours du visiteur, du vendeur et de l'équipe en 20 minutes, ce qu'il faut savoir avant de
  présenter (liens et numéros d'exemple).
- Mise à jour d'une démo installée avant : `-u ocd_live_demo` met le scénario en place, installe
  `ocd_live_demo_whatsapp` et retire l'ancien live de Brenda au studio (elle est à Douala).
  `ocd_live_demo` 20.0.1.1.0, `ocd_live_demo_whatsapp` 20.0.1.0.0 (nouveau).

### 11 novembre 2026 · photos des produits, replay lu dans la page, retour en stock
- **Photos du produit** : la photo s'ouvre en plein écran (glisser d'une photo à l'autre, pincer ou
  toucher deux fois pour zoomer, le bouton retour du téléphone la ferme) ; sans JavaScript, elle s'ouvre
  dans un nouvel onglet. Galerie avec des points : la photo principale, puis les autres photos du produit
  (la copie de la photo principale qu'Odoo 20 garde parmi elles n'est montrée qu'une fois).
- **La couleur change la photo** : une photo par couleur (« Photo de la couleur »), ajoutée par le vendeur
  dans « Mes produits » (« Photos des couleurs », une photo par couleur, envoyée dès qu'elle est choisie,
  notée dans l'historique du produit) ou par l'équipe (Configurer, sur les valeurs de l'attribut). Elle
  s'affiche aussitôt (photos chargées à l'avance), la taille choisie reste ; une variante qui a sa propre
  photo passe avant ; une couleur sans photo garde la photo principale. L'adresse garde le choix
  (`?v=…`) : un lien partagé ouvre la robe rouge, déjà choisie.
- **Choix lisibles** : « Couleur : Bleu », « Taille : S ». **Taille épuisée** : case barrée en diagonale
  (le « L » barré se lisait « Ł ») ; elle reste au toucher : « Rouge, L : épuisé pour l'instant » et
  **« Préviens-moi quand c'est de retour »** (numéro WhatsApp, ou un seul bouton pour un vendeur ou un
  client connu).
- **Retour en stock** (`ocd.stock.alert`) : dès qu'un stock revient (réception, quantité du vendeur), puis
  toutes les 30 minutes (automatisation « Produit de retour »), les clients reçoivent sur WhatsApp le
  modèle « produit de retour » (français et anglais), avec le lien du produit dans cette couleur et cette
  taille. Un produit retiré du shop termine ses alertes.
- **Page produit** : « Vu en live sur OCD · voir le moment » ouvre le replay à la minute du produit ;
  « Du même vendeur » en bas de page ; « Partager » dans l'en-tête ; la barre du bas ne garde que
  « Ajouter au panier » (la question à OCD Live passe dans les informations du produit).
- **Replay lu dans la page** : YouTube et TikTok (vidéo publiée) se lisent dans la page et vont au moment
  d'un produit touché ; Facebook se lit dans la page et repart du moment touché. Le lecteur n'est chargé
  qu'au premier toucher (rien n'est demandé à la plateforme avant). La barre sous la vidéo a un repère
  par produit (on touche un repère pour y aller) ; pendant la lecture, le produit à l'écran s'allume et
  « Commander » le suit. Instagram et les autres liens : un bouton « Ouvrir sur Instagram » et une
  consigne honnête (« va au moment du produit »). `?t=` ouvre le replay à une seconde ; `?live=` un replay
  précis du vendeur. Les minutes après une heure s'écrivent « 1:05:30 ».
- **Couleur montrée pendant le live** : sur les moments de la réservation (back-office), l'équipe choisit
  la couleur ou la taille montrée ; « Voir » et « Commander » ouvrent le produit sur elle.
- **Replay** : « Le prochain live de Brenda » avec « Préviens-moi sur WhatsApp » (le même accord que sur la
  boutique, retour sur le replay), « Partager » dans l'en-tête.
- **Back-office** : OCD Live › Shop › Alertes de retour en stock (ce que les clients attendent, groupé par
  produit).
- **Démo** : la Robe en wax a sa photo rouge.
- **Versions** : `ocd_live_shop` 20.0.1.5.0, `ocd_live_shop_whatsapp` 20.0.1.6.0.
- **À faire (équipe)** : soumettre à Meta le modèle « produit de retour » (`ocd_produit_de_retour`, français
  et anglais).

### 11 novembre 2026 · tous les pays d'Afrique et du monde, paiement par carte, fil des lives
- **Pays proposés** (OCD Live › Configuration › Pays) : les 54 pays d'Afrique et les plus connus d'Europe
  (23), d'Amérique (14) et d'Asie (21), soit 112 pays au lieu de 5. L'équipe en ajoute ou en retire
  (boutons « Proposer », « Retirer », ou plusieurs à la fois depuis la liste) ; les pays des vendeurs déjà
  inscrits restent proposés. Les Paramètres résument « Pays ouverts : 112 (54 en Afrique…) ».
- **Champ du numéro** : la liste du téléphone, groupée (suggérés, puis chaque continent), marche sans
  JavaScript ; avec JavaScript, une feuille avec les drapeaux et une recherche par nom ou par indicatif
  (« cam », « +237 »), au clavier aussi. Le pays de la personne vient en premier (adresse de connexion,
  sinon fuseau du téléphone), puis les pays où OCD Live a commencé. L'exemple de numéro suit le pays.
  Drapeaux d'Odoo pour tous les pays.
- **Numéros de tous les pays** vérifiés avec `phonenumbers` (0 de tête en Côte d'Ivoire, 0 à retirer en
  France, 10 chiffres au Bénin) ; règle simple si la bibliothèque manque. Les numéros déjà enregistrés
  gardent leur forme (« +228 90000007 »).
- **Paiement par carte** : `payment_stripe` est installé ; il prend les paiements de tous les pays (francs
  CFA compris) une fois ses clés saisies. **Sans moyen de paiement pour le pays**, la page de paiement le
  dit et propose « Demander à l'équipe de m'aider à payer » (note sur la commande, message dans le canal
  des lives, activité pour le responsable ; l'heure reste gardée le temps réglé pour l'équipe) et
  « Écrire à OCD Live sur WhatsApp ».
- **Fil des lives** (`/lives`), comme TikTok : une carte par écran, qui s'arrête à chaque geste. D'abord
  le pays de la personne (vendeur : le sien ; visiteur : celui de sa connexion ou de son téléphone ; ou le
  pays touché dans la barre), puis les autres pays, les plus actifs d'abord, chacun annoncé par sa carte.
  Lives en cours (lien vérifié, live au studio), puis prochains lives réservés, puis replays : hors des
  créneaux, la première carte dit quand les lives reviennent (avec « Me prévenir ») et le fil montre les
  prochains lives et les replays, jamais vide. Cartes suivantes chargées avant la fin, sans doublon ;
  barre des pays qui suit la carte à l'écran ; l'adresse garde la carte (retour, actualiser) ; flèches
  et Page haut/bas au clavier ; pastille « nouveaux lives » ; sans JavaScript, « Voir plus de lives ».
  Photo du vendeur ou de ses produits, sinon ses initiales ; boutons « Regarder sur TikTok », « Sa
  boutique », « Partager ». Les pages par pays (`/lives/tg`) restent.
- **Versions** : `ocd_live` 20.0.1.7.0 (migration : pays proposés sur les bases existantes).
- **À faire (équipe)** : saisir les clés Stripe et publier le paiement par carte ; vérifier la liste des
  pays (Configuration › Pays) ; installer `phonenumbers` sur le serveur (`pip install -r
  requirements.txt`).

### 11 novembre 2026 · ticket en PDF, image pour annoncer son live, heures de chacun
- **Ticket du live en PDF** (une page de 10 × 18 cm, lisible au téléphone ou imprimée) : envoyé sur
  WhatsApp dès le paiement confirmé, téléchargeable sur la page du ticket (« Télécharger mon ticket
  (PDF) ») et imprimable par l'équipe depuis la réservation. Il est **personnel** : jamais partagé, jamais
  gardé par un proxy. Contre les copies et les faux :
  - son **QR code est signé** par la base (vendeur, jour et heure du live) : il ouvre la page de
    vérification ; un ticket modifié, ou celui d'un live déplacé depuis, est « non valable » ;
  - l'équipe le scanne à l'entrée : la page lui montre à qui il est et le bouton **« Faire entrer »**
    (« Valider le ticket » pour un live à distance) ; un second passage du même ticket affiche
    « Ticket déjà utilisé » avec l'heure et la personne de l'équipe ; un visiteur ne voit que si le ticket
    est valable, sans le nom du vendeur ;
  - un **sceau** imprimé (ex. 9562-2ED5) vient de la même signature ; le fond porte des lignes de sécurité
    et un micro-texte propres à chaque ticket.
  Les polices et le logo sont dans le PDF (aucune demande au site) ; le wkhtmltopdf « Qt non patché »
  (Ubuntu) est reconnu et corrigé, la version patchée et les autres moteurs n'ont rien à faire.
- **WhatsApp avec le PDF** : après le paiement, le message « ticket » part avec son PDF ; tant que ce modèle
  attend Meta ou est en pause, la confirmation du live part à la place (le vendeur est toujours prévenu).
  Après un déplacement (par le vendeur ou l'équipe), le nouveau ticket part. Le PDF est fait au moment de
  l'envoi, en arrière-plan (`whatsapp_cloud` 20.0.2.7.0) : le paiement n'attend jamais le moteur PDF ; s'il
  échoue, le message dit pourquoi, est réessayé, puis passe en échec avec une note sur la réservation.
  L'exemple envoyé à Meta pour l'examen du modèle ne contient aucun vrai vendeur.
- **Annonce du live** : une image (1080 × 1350, format des statuts) **sans donnée personnelle** (ni numéro,
  ni ticket, ni référence) : nom public, ce que vend le vendeur, jour et heure, QR code et lien de sa
  boutique (ou des lives de son pays). Bouton **« Partager »** : l'image elle-même part vers WhatsApp, les
  statuts, Facebook… (sinon le texte et le lien, sinon l'image est téléchargée), et **« Télécharger »**.
  Sur la page du ticket et depuis « Annoncer » de l'espace vendeur.
- **Une heure non payée ne bloque plus les autres** : un live gardé dont le temps est passé est libéré
  tout de suite (sans attendre la tâche de 5 minutes), dès qu'un autre vendeur regarde ou réserve l'heure.
  Un paiement commencé garde l'heure le temps réglé (10 minutes) ; le Mobile Money vérifié par l'équipe
  la garde 24 heures seulement après « J'ai payé » (numéro ou référence du transfert), avec une note pour
  l'équipe. Sans cela, l'heure est de nouveau proposée.
- **Les heures de chacun** : un vendeur, un livreur ou un client voit les heures **dans son fuseau
  horaire** : celui de son téléphone (lu par le site, retenu sur sa fiche pour ses messages), sinon celui
  de son pays. Calendrier de réservation, résumé, paiement, ticket et PDF, image d'annonce, espace vendeur,
  annuaire, messages WhatsApp (et le rappel de la veille à 18:00 chez lui), appli des colis, boutique et
  suivi. Le nom du fuseau est écrit (« Heure : Cameroun »). Un live au studio vu d'un autre fuseau donne
  aussi l'heure du studio (« 10:00 – 11:30 au studio (Heure : Togo) »). L'équipe garde l'heure du studio
  dans le back-office ; les adresses des pages gardent l'heure du studio (un lien partagé reste juste).
- **Versions** : `ocd_live` 20.0.1.6.0, `ocd_live_shop` 20.0.1.4.0, `ocd_live_whatsapp` 20.0.1.6.0
  (migration : le PDF dans l'en-tête des modèles « ticket » pas encore approuvés, l'heure de fin du créneau
  de l'annuaire dans l'heure du vendeur), `whatsapp_cloud` 20.0.2.7.0.
- **À faire (équipe)** : soumettre à Meta le modèle « ticket » avec son PDF (WhatsApp › Modèles ; l'App ID
  de l'application Meta est demandé pour l'exemple de PDF). Un modèle « ticket » déjà approuvé sans PDF
  reste tel quel : y mettre l'en-tête « Document PDF » (document : Ticket du live), puis le soumettre à
  nouveau.

### 11 novembre 2026 · trois modèles refusés par Meta, navigation sans rechargement
- **Refusés par Meta** : « ticket du live », « colis en route », « choisir un mot de passe ». Le courriel
  de Meta ne donne pas de motif. Textes revus pour ce que Meta refuse dans un modèle *Utilitaire* :
  - plus de « code » : un code dans un modèle Utilitaire est pris pour un code à usage unique, réservé aux
    modèles *Authentification*. Le ticket donne son **numéro de ticket** ; le message « colis en route »
    n'écrit plus le code, son bouton **« Suivre mon colis »** ouvre la page de suivi de la commande, où le
    client le lit (« Votre code pour ce colis ») ;
  - plus de phrase entière dans une variable : le ticket a la même phrase pour le studio et à distance
    (« Gardez ce message, l'équipe d'OCD Live vous le demandera le jour du live ») ;
  - plus de « mot de passe » avec un lien (pris pour de l'hameçonnage) : « votre compte vendeur OCD Live est
    créé. Touchez le bouton pour l'activer », bouton « Activer mon compte ».
- **Mise à jour des bases** (`ocd_live_whatsapp`, `ocd_live_shop_whatsapp` 20.0.1.5.0) : la migration lit
  d'abord la décision de Meta, puis donne les nouveaux textes aux modèles refusés, même encore « en attente »
  dans Odoo (variables et boutons compris). Testé sur la base de démo.
- **Décisions de Meta lues sans le webhook** (`whatsapp_cloud` 20.0.2.6.0) : toutes les 30 minutes, les
  modèles en attente reçoivent leur statut et le motif d'un refus ; les responsables sont prévenus.
  « Synchroniser les modèles » ne remet plus le texte refusé par-dessus le texte corrigé : pour un modèle
  refusé, seule la décision de Meta est lue.
- **Navigation sans rechargement, pour les vendeurs et les livreurs** connus du navigateur : un lien des
  pages d'OCD Live affiche tout de suite le squelette de la page, la page se charge en arrière-plan, puis
  seul le contenu change (l'en-tête et le menu du bas restent, l'adresse et le bouton retour suivent). Le
  chargement commence dès que le doigt touche le lien. Les formulaires, le paiement, les pages d'un autre
  type et toute erreur chargent la page normalement. Les visiteurs gardent les pages normales.
- **Versions anglaises** (correction : elles sont voulues) : les 7 versions anglaises des modules WhatsApp,
  archivées par la version précédente, sont de nouveau actives à la mise à jour ; les 20 modèles d'OCD Live
  ont maintenant leur version anglaise (même nom chez Meta, langue anglais, mêmes variables et boutons ;
  dates, lieux et textes des variables en anglais). Un contact anglophone reçoit la version anglaise une fois
  approuvée par Meta, la française en attendant : une version pas encore soumise ne passe plus avant une
  version approuvée (ses messages auraient échoué).
- **Titres des onglets en français** : « Mon espace | OCD Live », « Mes colis », « Lives par pays »… au lieu
  des noms techniques anglais (« OCD Live: my space »). Versions : `ocd_live` 20.0.1.5.0, `ocd_live_shop`
  20.0.1.3.0.
- **À faire** : mettre à jour les modules, puis soumettre à Meta les trois modèles corrigés et les versions
  anglaises (WhatsApp › Modèles, filtre de langue « en »).

### 11 novembre 2026 · le téléphone retient le vendeur et le livreur ; messages en français seulement
- **Vendeur « plus connecté » après Accueil puis Moi** : pas reproduit en local, avec chaque façon de se
  connecter (lien personnel, code WhatsApp, mot de passe, vue de l'équipe, administrateur connecté dans le
  même navigateur) ; la session reste la même sur Accueil, Moi, Lives, la boutique, le retour arrière et le
  rechargement. La cause est donc côté serveur : session d'Odoo perdue ou remplacée (requête arrivée sans
  le cookie, proxy, plusieurs bases), ou lien « Changer de numéro » chargé à l'avance par le navigateur ou
  un proxy (ce lien déconnectait).
- **Correction, pour les vendeurs et les livreurs** : en plus de la session d'Odoo, un cookie du
  navigateur (180 jours, inaccessible aux scripts de la page, signé avec le secret du lien personnel)
  retrouve le vendeur ou le livreur quand la session l'a perdu. Il s'arrête avec « Changer de numéro » /
  « Se déconnecter » ou un nouveau lien personnel. Le journal du serveur l'écrit (« opened again by the
  cookie of the browser ») : s'il apparaît, la session d'Odoo se perd bien sur ce serveur.
- **Se déconnecter est un bouton** (formulaire) : « Changer de numéro », « Ce n'est pas moi » (la même étape
  de la réservation redemande le nom et le numéro, au lieu de la page du numéro), « Se déconnecter » du
  livreur, « Quitter » la vue de l'équipe. Ouverts comme liens (préchargement, ancien lien), ils ne font
  plus rien.
- **« Se déconnecter » d'un compte avec mot de passe ne marchait plus** : Odoo 20 refuse la déconnexion
  par lien (erreur 405) ; c'est maintenant un formulaire, comme Odoo l'attend.
- **Messages WhatsApp en français seulement** : les versions anglaises des modèles fournis par les modules
  WhatsApp (commande reçue, confirmée, prête, expédiée, devis, satisfaction, reprise de conversation) sont
  archivées : jamais envoyées, hors des listes, rien à soumettre à Meta. Un contact anglophone reçoit la
  version française. `ocd_live_shop_whatsapp` dépend maintenant de `whatsapp_cloud_sale` (déjà installé).
- Versions : `ocd_live`, `ocd_live_whatsapp`, `ocd_live_shop_whatsapp` 20.0.1.4.0.
- Tests : session perdue puis retrouvée par le cookie (lien et code, vendeur et livreur), lien chargé à
  l'avance sans effet, cookie fabriqué refusé, nouveau lien personnel qui arrête le cookie, déconnexion du
  compte Odoo, modèles anglais archivés.

### 11 novembre 2026 · modèles WhatsApp encore refusés : textes corrigés jusque dans les bases
- **Ce qui bloquait** : les modèles fournis sont chargés une seule fois, à l'installation (pour garder les
  textes changés par l'équipe). Les textes corrigés juste avant n'arrivaient donc pas dans une base déjà
  installée : « lien refusé », « ticket du live » et « colis en route » gardaient leur ancien texte, bloqué
  par la vérification d'Odoo. Et « lien reçu » finissait par « : {{2}}. » : pour Meta, le point ne compte
  pas comme du texte, le modèle finit par une variable (refusé par Meta).
- **Vérification d'Odoo alignée sur Meta** (`whatsapp_cloud`) : seuls les lettres et les chiffres comptent
  comme du texte. Pas de variable au début ni à la fin, même suivie d'un point ou d'une parenthèse ; des
  mots entre deux variables (une virgule seule ne suffit pas). Le message dit quoi corriger.
- **Textes réécrits**, mêmes variables : lien reçu, live confirmé, rappel du live, ticket du live (aussi
  plus de texte autour de ses 7 variables : Meta refuse un texte trop court pour ses variables), colis à
  préparer, livraison impossible, commande reçue en français et en anglais (`whatsapp_cloud_sale`).
- **Les bases existantes reçoivent les nouveaux textes** à la mise à jour des modules : un modèle qui a
  encore un ancien texte du module et que Meta n'a pas approuvé prend le nouveau texte. Un texte changé par
  l'équipe et un modèle approuvé ou en cours de revue chez Meta ne bougent pas. Le code de connexion prend le
  texte que Meta écrit lui-même. Versions : `whatsapp_cloud` 20.0.2.5.0, `whatsapp_cloud_sale` 20.0.2.4.0,
  `ocd_live_whatsapp` et `ocd_live_shop_whatsapp` 20.0.1.3.0. Testé sur la base de démo, restée aux anciens
  textes comme toute base installée avant : les 11 modèles concernés ont leur nouveau texte, leurs
  variables sont gardées, et les 34 modèles passent la vérification.
- Tests : chaque modèle fourni passe les règles de Meta, avec au moins 3 mots par variable (Meta ne publie
  pas sa limite) ; les migrations donnent les nouveaux textes et laissent un modèle approuvé tel quel.
- **À faire** : mettre à jour les modules (commande dans [`DEVELOPPEMENT.md`](DEVELOPPEMENT.md), elle
  comprend maintenant `whatsapp_cloud` et `whatsapp_cloud_sale`), puis soumettre de nouveau à Meta les
  modèles qui ne sont pas encore approuvés (WhatsApp › Modèles › « Soumettre à Meta »). Un modèle déjà refusé
  par Meta est renvoyé comme une modification du modèle refusé.

### 11 novembre 2026 · l'appli installée porte le logo d'OCD Live
- « Installer l'appli » du navigateur montrait l'icône et les couleurs d'Odoo (le module de l'OCA
  `web_pwa_customize` n'existe pas encore pour Odoo 20). `ocd_debranding` donne maintenant au manifeste de
  l'appli les icônes d'OCD Live (192 et 512 px, marge pour les téléphones qui découpent l'icône en rond),
  le fond blanc et la couleur encre ; l'icône de l'iPhone aussi. Icônes redessinées nettes depuis le logo.
- L'icône des onglets n'a plus de coins noirs (logo rond sur fond transparent) ; le site existant la
  reçoit à la mise à jour, sauf si l'équipe avait mis la sienne. `ocd_debranding` 20.0.1.1.0.
- Une appli déjà installée garde l'ancienne icône : la désinstaller puis la réinstaller.

### 11 novembre 2026 · modèles WhatsApp acceptés par Meta
- **Code de connexion refusé par Meta** (« le composant BODY a un champ inattendu : text ») : un modèle de
  catégorie *Authentification* n'a pas de texte chez Meta, qui écrit lui-même « <code> est votre code de
  vérification » dans la langue du modèle. `whatsapp_cloud` soumet maintenant ces modèles comme Meta
  l'attend (conseil de sécurité, durée du code en pied de message, bouton « Copier le code ») et envoie le
  code dans le texte et dans le bouton ; nouveau champ « Code valable (minutes) » (10 pour OCD Live).
- **Modèles qui finissaient par une variable** (refusés par Meta) : « lien refusé », « ticket du live » et
  « colis en route » finissent maintenant par du texte, mêmes variables. Tous les modèles du dépôt passent
  les règles de Meta (début et fin sans variable, pas deux variables collées).
- Après la mise à jour des modules WhatsApp, soumettre de nouveau ces quatre modèles à Meta.
- `whatsapp_cloud` vient du dépôt tchokos-projet : ce changement est à reporter là-bas si le module y est
  encore suivi.
- Point connu : le test « commande confirmée puis expédiée » de `whatsapp_cloud_sale` échoue quand les
  modules d'OCD sont installés, car OCD remplace volontairement « commande expédiée » par « colis livré ».

### 11 novembre 2026 · les livreurs entrent avec leur numéro
- Page « Tes colis à livrer » (`/ocd/livrer`, « Espace livreurs » dans le pied de page) : le livreur
  tape le numéro de sa fiche et reçoit sur WhatsApp son lien (mode lien) ou un code (mode code, et mode
  mot de passe : il n'a pas de compte). Les vendeurs qui livrent y entrent aussi. Le numéro d'un livreur
  tapé sur « Mon espace » reçoit aussi l'appli de livraison.
- Seulement un contact actif coché « Livreur » ; même réponse pour tout numéro ; un compte de l'équipe
  n'envoie rien ; un lien au plus par minute et par numéro (vendeurs compris : avant, chaque demande
  renvoyait un message).
- Le téléphone retient le livreur (plus besoin de garder le message) ; « Se déconnecter » dans l'appli.
  En mode code, un lien personnel n'ouvre plus l'appli : il mène à la page du numéro (avant : page
  introuvable pour un vendeur).
- « Nouveau lien personnel » sur la fiche d'un livreur ; pour les livreurs comme pour les vendeurs, il
  coupe aussi les téléphones et navigateurs déjà ouverts (ils redemandent le numéro une fois après la mise
  à jour). Décocher « Livreur » coupe l'accès tout de suite.
- Après une action dans l'appli (colis prêt, code…), recharger la page réaffiche l'appli.
- Versions : `ocd_live` 20.0.1.3.0, `ocd_live_shop` 20.0.1.2.0. Captures `site-phone-l-*`.

### 11 novembre 2026 · 404 sur « Moi » en administrateur, pages restées en anglais
- **404 sur « Moi »** (staging) : le code des derniers changements était en place, mais `ocd_live` n'avait pas
  été mis à jour dans la base : la page de l'équipe (`ocd_live.space_team`) n'y existait pas, Odoo répond
  alors « Page introuvable ». Reproduit à l'identique. Remède : mettre à jour `ocd_live` après chaque
  récupération du code (voir [`DEVELOPPEMENT.md`](DEVELOPPEMENT.md)) ; la version de `ocd_live` passe à
  20.0.1.2.0 pour les outils qui ne mettent à jour qu'un module dont la version change.
- **Pages en anglais** : Odoo montre le site dans la langue du téléphone (ou du compte connecté) quand le
  site la propose ; l'anglais, langue de base d'Odoo, reste proposé. Le bouton « FR » des pages d'OCD ne
  changeait que la voix. Maintenant, ce bouton est la **langue de la page et de la voix** : il montre la
  langue de la page ; Français ou English affiche la page dans cette langue, et le choix reste pour tout le
  parcours ; une langue seulement parlée (éwé…) ne change que la voix. Les pages sans voix (espace,
  connexion, shop…) ont le bouton de la langue de la page.

### 11 novembre 2026 · « Moi » quand on est déjà connecté à Odoo
Constat : connecté à Odoo, « Moi » demandait quand même le numéro pour recevoir un lien.
1. **Compte relié à un vendeur** (accès avec mot de passe, ou personne de la société du vendeur) :
   l'espace s'ouvre directement, dans tous les modes ; on en sort par « Se déconnecter ».
2. **Compte de l'équipe** : plus de formulaire ; une page dit que l'espace est pour les vendeurs, avec
   « Ouvrir les vendeurs » (back-office). Un numéro envoyé avec ce compte n'envoie rien.
3. **« Voir son espace »** sur la fiche vendeur (et l'onglet OCD Live des contacts) : l'espace du vendeur
   s'ouvre dans un nouvel onglet, comme le vendeur le voit ; lien signé pour la personne de l'équipe
   (modifié, ou ouvert par un autre : rien) ; barre « Vue de l'équipe · vendeur · Quitter » sur toutes les
   pages d'OCD Live pendant la vue ; « Quitter » ramène à la fiche du vendeur.
4. **Client connecté qui n'est pas vendeur** : le formulaire reste, avec son nom et son numéro préremplis.
   En mode « mot de passe », une page dit que ce compte n'est pas un compte vendeur (avant : la page de
   connexion et l'espace se renvoyaient l'un à l'autre).
Captures `site-phone-v-*`.

### 11 novembre 2026 · thème du site « OCD Live », plus de page 404 après « Confirmer »
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

### 11 novembre 2026 · le site est celui d'OCD Live dès l'installation
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

### 11 novembre 2026 · branche fusionnée dans main, modules complémentaires dans le dépôt
- `whatsapp_cloud`, `whatsapp_cloud_sale`, `payment_campay` et `delivery_cameroon` sont dans le dépôt
  (plus de « dépendance absente » dans les Applications). Seul `disable_odoo_online` (OCA) s'ajoute à
  part.
- Le travail de la branche `claude/serene-johnson-x7ucgf` (boutique, replay, appli de livraison, toutes les
  pages du shop, frais de livraison, démo, paramètres, automatisations, conversations WhatsApp, sans la
  marque Odoo) est dans `main`.

### 11 novembre 2026 · paramètres, automatisations, conversations WhatsApp, sans la marque Odoo
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

### 11 novembre 2026 · démo qui remplit tous les écrans
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

### 11 novembre 2026 · guide des livraisons
- [`docs/LIVRAISONS.md`](LIVRAISONS.md) : comment le prix d'un colis est choisi, exemples, ce que voient
  le client et le vendeur, l'argent, la mise en route pas à pas, les questions fréquentes, le code.

### 11 novembre 2026 · frais de livraison selon le vendeur
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

### 10 novembre 2026 · toutes les pages du shop fidèles au design
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

### 10 novembre 2026 · appli des colis et tournée du livreur fidèles au design
- Vendeur (`Livrer`) : « Bonjour Fatou », reversement à venir, onglets « À faire » et « Livrés », une
  carte par colis : étape, adresse, produits, paiement (payé en ligne ou à encaisser), livreur OCD qui
  passe, et le bouton du moment (c'est prêt, je pars livrer, paiement à la porte, code, problème).
- Livreur OCD (`Tournee`) : en service ou non, espèces sur soi, étapes numérotées (récupérer chez le
  vendeur, puis livrer), dernières livraisons du jour, « Appeler le dispatch ».
- Le message ou l'erreur d'une action s'affiche dans la carte du colis ; « Reprendre la livraison »
  après un problème ; un vendeur qui n'encaisse pas peut montrer le paiement sur le téléphone du client.

### 10 novembre 2026 · boutique d'un vendeur et replay fidèles au design
- Boutique (`/ocd/boutique/<vendeur>`) : vendeur, mode de vente, adresse ; en live (depuis combien de
  temps, sur quelle plateforme, produit à l'écran) ou prochain live ; dernier replay ; bouton WhatsApp
  (OCD Live quand OCD vend, le vendeur sinon) ; produits avec « Plus que N » et « Épuisé ».
- « Me prévenir sur WhatsApp » : `ocd.boutique.alert`, envoyé par une tâche automatique (toutes les
  5 minutes) quand le live commence ; message `ocd_vendeur_en_live` dans `ocd_live_shop_whatsapp`.
- Replay (`/ocd/boutique/<vendeur>/replay`) : moments du live, bouton du bas selon le moment choisi.
- Bouton « Partager » dans l'en-tête des pages (partage du téléphone, ou lien copié) ; « Shop » dans le
  menu du bas.
- Captures : `tools/captures/site-shop.js`.

### 10 novembre 2026 · outils Odoo dans la documentation, shop du site commencé
- La page « Outils Odoo utilisés » quitte le back-office : elle devient `docs/OUTILS_ODOO.md`, avec ce
  que chaque outil fait concrètement pour OCD Live.
- Dépôt GitHub `projet_ocd` en place : tout y est envoyé à chaque évolution.

### 10 novembre 2026 · back-office fidèle au design
- Couleurs et polices dans un seul fichier, partagé par les deux thèmes (site et back-office).
- Barre sombre avec le logo et les sections, onglets de la section dessous, menus nommés comme le design.
- Tableau de bord, planning des réservations, régie en direct, à vérifier, commandes, dispatch, fiche
  d'une livraison, livreurs et caisse, fiche vendeur, reversements, recrutement, outils Odoo utilisés.
- Motifs de refus par type (liens, vendeurs, produits), visites de la boutique pendant le live.
- Traductions françaises de tous les modules.
- Documents de suivi (`docs/`), prototype complet (`prototype/`), outils de traduction et de captures (`tools/`).

### 10 novembre 2026 · site fidèle au design, paiements génériques
- Pages de réservation, annuaire et espace vendeur fidèles au design, responsives.
- Paiement par le formulaire d'Odoo : aucun fournisseur figé, devise selon le pays.
- Prix selon l'heure et la date ; barre du bas toujours en bas de l'écran.
- Module de démonstration désinstallable.

### Avant · modules de base
- Réservations, crédits, annuaire, shop avec colis par vendeur, WhatsApp, Togo, recrutement.
