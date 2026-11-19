# Décisions validées avec l'équipe OCD

Ces choix ont été validés pendant le projet. Ceux marqués « réglable » se changent dans
**OCD Live › Configuration › Paramètres**, sans toucher au code.

## Produit

- **Odoo 20 Community**, sans application payante. `ocd_live` fonctionne seul ; le shop, WhatsApp, le
  recrutement et le Togo sont des modules à part.
- **Fidèle au design validé**, pour le site comme pour le back-office.
- **Mobile d'abord**, mais très à l'aise aussi sur tablette et ordinateur. **Depuis le 16 novembre 2026** :
  chaque nouvel écran est dessiné et vérifié en trois tailles (téléphone 390 px, tablette 820 px,
  ordinateur 1440 px) ; sur grand écran, la page occupe la largeur (pas de colonne étroite entre deux
  bandes vides). Quatre organisations, une par type de page (maquettes `RespListes`, `RespFiche`,
  `RespParcours`, `RespEspace`) : les listes en grilles larges, les fiches photo à gauche et
  informations à droite, les parcours formulaire à gauche et récapitulatif à droite, les espaces avec
  leur menu à gauche (des onglets sur tablette). Le téléphone garde le design validé.
- **Les écrans qui grandissent avec les données tiennent à toute taille** (le 19 novembre 2026, après
  des captures de l'équipe) : aussi un portable (1366 × 657) et un zoom à 125 %, contrôlés par
  `tools/captures/mise-en-page.js` qui échoue si une règle casse.
  - **le fil des lives** sur tablette et ordinateur : la page défile, jamais une boîte dans la page (sa
    hauteur coupait les cartes d'un écran bas) ; des colonnes de 320 px au moins (la photo du produit
    garde sa moitié, les textes passent sur deux lignes au lieu d'être coupés), alignées sur l'en-tête ;
    chaque pays commence sa ligne sous un bandeau à son nom, et choisir un pays amène à ce bandeau ;
    la barre des pays reste en haut avec « Je suis en live », jamais posé sur les cartes ; le téléphone
    ne change pas ;
  - **l'accueil** nomme les pays où il y a un live (les plus actifs d'abord), puis celui du visiteur
    même sans live, puis « Tous les pays » : jamais la liste des 112 pays proposés, presque tous à 0 ;
    la page gardée en mémoire l'est déjà par pays du visiteur. **« Cherche ton pays »** trouve un pays
    au fil de la frappe, par son nom sans les accents, son nom anglais, son code ou un nom courant
    (Ivory Coast, RDC, USA…) ; Entrée ouvre le premier ; sans JavaScript, la page de tous les pays ;
  - **la page d'un pays** montre les mêmes cartes que l'onglet Lives (ses lives, au studio, ses prochains
    lives, ses replays), l'une sous l'autre sous ses filtres, la page défile, sur téléphone aussi (une
    boîte sous les filtres laissait trop peu de place à une carte) ; avec « Programme des lives » du pays ;
  - **les catégories dans l'onglet Lives**, sous les pays, plus discrètes : une catégorie montre ses lives
    dans tous les pays, le pays choisi gardé, et les cartes suivantes sont de la même catégorie ;
  - **« À vérifier »** : seules les colonnes qui ont quelque chose à vérifier prennent une place, 280 px
    au moins ; les autres sont nommées en une ligne au-dessus (« Rien en attente : … ») ; quand les
    colonnes ne tiennent pas, le tableau défile de côté, une carte n'est jamais écrasée. Chaque chantier
    peut ajouter sa colonne sans rien casser.
- **Deux thèmes** : celui du site (vendeurs, clients) et celui du back-office (équipe). Ils lisent les
  mêmes couleurs et polices, dans un seul fichier : `ocd_live/static/src/scss/ocd_tokens.scss`.
- **Données de démonstration** dans un module à part, `ocd_live_demo` : le désinstaller retire tout.
  La démo est **tenue à jour** par une action planifiée : une présentation montre toujours des lives
  en cours, la semaine du studio, les replays récents et la journée de la boutique de Douala (colis,
  caisse des livreurs, reversements, conversations WhatsApp), quel que soit le jour. Ses vendeurs ont des
  histoires cohérentes (ville, produits, heures, plateforme ; studio pour Lomé, à distance ailleurs) et
  **ne reçoivent jamais de WhatsApp** (numéros d'exemple, `ocd_live_demo_whatsapp`). Elle ajoute deux
  fenêtres de vérification (midi, après-midi) pour avoir des lives de 8 h à 21 h. Scénario : `DEMO.md`.
  - **OCD Express dans la démo** (18 novembre 2026) : dans `ocd_live_demo` même, quand `ocd_express` est
    installé (avant ou après la démo : l'action planifiée le rattrape), comme WhatsApp ; pas de module de
    plus. Une expéditrice (Nadège Mode, Akwa) et une demande en attente ; ses colis rejoués chaque jour
    ouvré avec la boutique de Douala, par les vraies fonctions d'OCD Express, datés au moment du scénario
    (une étape jouée en retard ne planifie jamais depuis maintenant) ; ses clients ont des numéros
    d'exemple reconnus par `ocd_live_demo_whatsapp`. Ses reversements sont **payés dans la comptabilité**
    (« Mon argent » ne compte que l'argent non payé) ; ceux des vendeurs du shop restent marqués payés
    sans écriture, comme avant. Ses étapes de 7 h et de 19 h 30 sont à elle : installé après la démo,
    OCD Express rejoue aussi l'argent et la caisse des jours d'avant.
  - **La démo installée en une fois avec les modules** charge elle-même le plan comptable qu'Odoo
    allait charger à la fin de l'installation (Odoo 20 le charge après les `post_init_hook`) : sans lui,
    les colis des jours d'avant étaient livrés sans facture et les reversements ne commençaient que le
    lendemain des premières factures (le test `test_a_day_of_the_shop` échouait).
- **Voix des pages** en plusieurs langues (français, éwé, etc.), enregistrées par l'équipe.
- **L'adresse du site (`/`) ouvre l'accueil d'OCD Live** (`/ocd`), et non la page vide d'Odoo.
- **Le site est en français par défaut** quand le français est installé ; les autres langues restent
  au choix du visiteur. Odoo suit la langue du téléphone ou du compte connecté quand le site la propose.
- **Un seul bouton de langue sur les pages d'OCD** : la langue de la page et de la voix. Français ou
  English change la page (et le choix reste) ; une langue seulement parlée (éwé, mina…) change la voix.
  Le bouton passe par `/ocd/langue/<code>` : le choix est gardé même par un navigateur qui n'avait
  jamais choisi (sinon Odoo reprend la langue du téléphone), puis la même page s'ouvre dans la langue.
- **Les pages d'Odoo gardées telles quelles** (recrutement, connexion, portail, contact) portent le logo,
  le nom et les coordonnées d'OCD Live : pied de page d'OCD, téléphone et e-mail de la société, aucun
  texte d'exemple d'Odoo. Ce que l'équipe a déjà choisi (page d'accueil, langue, logo, nom) n'est jamais
  remplacé.
- **Un thème de site « OCD Live »** (`theme_ocd`) dans le choix des thèmes d'Odoo : polices Bricolage
  Grotesque et Figtree, orange, encre et sable, boutons arrondis, en-tête blanc avec « Réserver un live »,
  pied de page sombre. Les pages d'OCD Live gardent leur propre cadre ; le thème habille les pages d'Odoo
  et celles que l'équipe crée avec l'éditeur du site (palette « OCD Live » proposée).

- **Qui ouvre l'espace vendeur (« Moi »)** : un compte Odoo relié à un vendeur l'ouvre directement, quel
  que soit le mode de connexion des vendeurs ; un compte de l'équipe ne voit pas le formulaire du numéro
  (un numéro tapé avec ce compte n'envoie rien) ; l'équipe voit l'espace d'un vendeur depuis sa fiche
  (« Voir son espace », lien signé pour la personne, barre « Vue de l'équipe » tant que dure la vue) ;
  un client connecté qui n'est pas vendeur garde le formulaire, avec son numéro prérempli.

- **Les livreurs entrent comme les vendeurs** : page « Tes colis à livrer » (`/ocd/livrer`, lien
  « Espace livreurs » en pied de page), leur numéro, puis leur lien (mode lien) ou un code (mode code ;
  en mode mot de passe aussi, ils n'ont pas de compte) sur WhatsApp. Seulement un contact que l'équipe a
  coché « Livreur » ; même réponse pour tout numéro ; un lien au plus par minute et par numéro. Le
  téléphone retient le livreur jusqu'à « Se déconnecter » ; « Nouveau lien personnel » (fiche du livreur,
  et des vendeurs) coupe aussi les téléphones déjà ouverts ; décocher « Livreur » coupe tout de suite.

## Réservations

- Parcours par défaut : **jour → heure → paquet** (réglable : paquet d'abord).
- **Un seul calendrier** pour le studio et la distance (réglable : un calendrier par mode).
- Studio ouvert de **8:30 à 22:00**, 9 lives de 1 h 30 par jour (réglable : heure, durée, nombre, jours).
- Ouverture des réservations le **1er décembre 2026** (réglable).
- Un créneau est **gardé pendant le paiement**, puis libéré et proposé à la liste d'attente. Un live gardé
  dont le temps est passé est libéré **tout de suite** pour les autres (même avant la tâche de 5 minutes).
  Le Mobile Money vérifié par l'équipe garde l'heure 24 heures **seulement après « J'ai payé »** (numéro ou
  référence du transfert donnés par le vendeur).
- **Ticket du live : un PDF personnel**, jamais partagé (WhatsApp, téléchargement). Son QR code est signé
  et ouvre la vérification de l'équipe, qui fait entrer **une seule fois** ; le ticket d'un live déplacé
  n'est plus valable (le nouveau part sur WhatsApp). Pour parler de son live, le vendeur partage une
  **image d'annonce sans donnée personnelle** (ni numéro, ni ticket).
- **Chacun voit les heures dans son fuseau horaire** (vendeur, livreur, client) : celui de son téléphone,
  sinon celui de son pays ; le nom du fuseau est écrit (« Heure : Cameroun »). Un live au studio vu d'un
  autre fuseau donne aussi l'heure du studio. L'équipe et les adresses des pages gardent l'heure du studio.
- **Prix selon l'heure et la date** : l'équipe crée des règles (+25 % le samedi soir, −15 % le lundi
  matin, une période…) ; la première règle qui correspond s'applique. Un live déplacé ne peut pas aller
  sur une heure plus chère.
- **Pas d'enchères** pour l'instant. Possible plus tard : offre sous pli sur 1 ou 2 créneaux prestige,
  sans paiement d'avance.

## Paiements et devises

- **Aucun fournisseur de paiement figé dans le code** : le site propose les moyens configurés dans
  Odoo pour le pays, la devise et le montant. CamPay au Cameroun ; CinetPay et Flutterwave dans l'UEMOA ;
  la carte (Stripe) partout ; le Mobile Money vérifié par l'équipe là où rien d'automatique n'est ouvert.
- **Paiement automatique dans l'UEMOA (chantier 5, 18 novembre 2026) : CinetPay et Flutterwave**, choisis
  par l'équipe. Le code est prêt avant les contrats : chaque fournisseur ne s'affiche qu'une fois ses clés
  saisies et publié, et ne prend de vrai argent qu'en production (« Live » coché) ; les Paramètres disent
  ce qui manque pour chacun.
  - **CinetPay** (module `payment_cinetpay`, écrit pour OCD Live) : Côte d'Ivoire, Sénégal, Togo, Bénin,
    Mali, Burkina Faso, Niger, et aussi Cameroun, Guinée et RD Congo ; Mobile Money (Orange, MTN, Moov,
    Free, T-Money, Flooz…), Wave et les portefeuilles (Côte d'Ivoire, Sénégal) et la carte, sur la page de
    paiement de CinetPay ;
  - **Flutterwave** (module d'Odoo, sans changement) : la carte partout, le Mobile Money en Côte
    d'Ivoire, au Sénégal, au Mali et au Cameroun ; en second, ou pour la diaspora ;
  - **la Guinée-Bissau** n'est couverte par aucun des deux : la carte, le Mobile Money vérifié par
    l'équipe ou le paiement à la porte, comme aujourd'hui ; les Paramètres la nomment parmi les pays sans
    paiement en ligne ;
  - **le montant** : CinetPay prend des multiples de 5 en francs CFA ; le montant demandé est arrondi au
    multiple de 5 supérieur (quelques francs au plus) et la commande est payée pour son propre montant ;
  - **l'état d'un paiement est toujours lu chez CinetPay** (API de vérification), jamais dans la
    notification ou le retour du client ; un paiement en attente est revérifié toutes les 10 minutes
    pendant un jour, au cas où la notification se perdrait ;
  - **le Mobile Money vérifié par l'équipe s'efface** dans un pays et une devise où CinetPay, Flutterwave
    ou CamPay prend le Mobile Money en production ; en mode test, les deux sont proposés ;
  - **les reversements** restent faits par l'équipe (avec la référence du transfert), comme au Cameroun ;
    les transferts automatiques de CinetPay viendront plus tard.
- **La devise suit le pays** via les listes de prix d'Odoo (franc CFA BCEAO au Togo, BEAC au Cameroun).
- **Devises par pays : quatre zones**, mises en place par un bouton (Paramètres › Devises par pays), jamais
  d'elles-mêmes en production (la démo, elle, les met en place) :
  - **XOF** : les 8 pays de l'UEMOA (Togo, Bénin, Côte d'Ivoire, Sénégal, Mali, Burkina Faso, Niger,
    Guinée-Bissau) ;
  - **XAF** : les 6 pays de la CEMAC (Cameroun, Gabon, Congo, Tchad, Centrafrique, Guinée équatoriale) :
    c'est la devise de CamPay ;
  - **EUR** : l'Europe, le reste de l'Afrique (Ghana, Nigeria, Maroc…) et la France hors d'Europe
    (Guadeloupe, Martinique, Guyane, Réunion, Mayotte…) ;
  - **USD** : les Amériques, l'Asie et l'Océanie.
- **Les prix s'écrivent en XOF, la conversion est automatique** : XAF = XOF et 1 € = 655,957 F CFA
  (parité fixe depuis 1999, remise d'office sur un taux saisi à tort) ; le dollar est lu chaque jour
  auprès de la Banque centrale européenne (le dernier taux reste si elle ne répond pas). Les prix en euros
  et en dollars sont **arrondis à l'unité** (15 000 F CFA → 23 € et 25 $), les frais de livraison aussi ;
  les francs restent tels quels. Une commande garde la devise et le taux de son jour.
- **Paiements de démo CamPay** (Paramètres › Paiements et reversements), pour une présentation ou un test
  avec de vrais téléphones : chaque paiement CamPay encaisse le montant de démo (25 F CFA par défaut, au
  choix) au lieu du prix, **pour tous les numéros ou seulement pour une liste de numéros** ; les pages
  gardent les vrais prix. Il s'arrête tout seul après le dernier jour (activé sans date : ce soir). Au
  retour, CamPay doit avoir encaissé exactement le montant demandé (tout autre montant est refusé) ; la
  commande est alors payée comme d'habitude, la comptabilité enregistre l'argent reçu (25 F CFA), une note
  le dit sur la commande ou la facture, une ligne rouge le rappelle sur le tableau de bord et un filtre
  « Paiements de démo » les retrouve dans les transactions.

## Pays et paiement

- **Pays proposés : tous les pays d'Afrique et les plus connus d'Europe, d'Amérique et d'Asie** (112),
  réglables par l'équipe (OCD Live › Configuration › Pays). Le pays de la personne vient en premier dans
  les listes, puis les pays où OCD Live a commencé (Togo, Cameroun, Bénin, Côte d'Ivoire, Sénégal).
- **Numéros vérifiés avec les règles de Google** (`phonenumbers`), une règle simple sans elle.
- **Paiement par carte avec Stripe** pour les pays sans Mobile Money ; jamais de page de paiement sans
  issue : sans moyen de paiement, l'équipe est appelée à l'aide et l'heure reste gardée.

## Vendeurs et annuaire

- Connexion du vendeur **par lien personnel envoyé sur WhatsApp** (réglable : code à 6 chiffres, ou mot de passe).
- **Le téléphone retient le vendeur et le livreur** (lien ou code) jusqu'à « Changer de numéro » /
  « Se déconnecter » ou un nouveau lien personnel : un cookie du navigateur (180 jours) le retrouve même
  quand la session d'Odoo se termine ou est remplacée. Se déconnecter est toujours un bouton (formulaire),
  jamais un simple lien : un navigateur ou un proxy qui charge les liens à l'avance ne déconnecte personne.
- **Navigation sans rechargement pour les vendeurs et les livreurs** : squelette de la page au toucher
  d'un lien, puis le contenu change seul ; les visiteurs, les formulaires et le paiement gardent les pages
  normales.
- **Fil des lives comme TikTok** : une carte par écran, le pays de la personne d'abord, puis les autres
  pays (les plus actifs d'abord) ; prochains lives et replays quand aucun live n'est vérifié. **Un seul
  prochain live et un seul replay par vendeur** (le plus proche, le plus récent ; les autres sont dans sa
  boutique) : un pays où les vendeurs réservent beaucoup ne repousse pas les lives des autres pays. Les lives
  restent sur TikTok, Facebook… (ces plateformes ne laissent pas lire un live ailleurs) : la carte y mène.
- **Cartes du fil claires et épurées**, la couleur seulement pour l'état du live et le bouton principal ;
  le média en haut, les textes et les boutons en bas, sans chevauchement. **Le média est au choix du
  vendeur** : vidéo courte (30 s, sans le son à l'écran), carrousel de ses produits (un toucher ouvre le
  produit) ou image ; « Automatique » prend la vidéo, sinon les produits, sinon l'image.
- **Aucune plateforme imposée** : les plateformes de live sont une liste de l'équipe ; un lien est reconnu
  par son adresse, la carte dit « Regarder sur » et son nom.
- **Les lives réservés passent sur les comptes d'OCD Live**, plusieurs possibles (par pays, studio, à
  distance) ; **TikTok d'abord**. Le vendeur d'un live à distance **rejoint le compte d'OCD en invité**
  (sur TikTok, lancer un live demande souvent 1 000 abonnés : le compte d'OCD les a, pas toujours le
  vendeur).
- **Avant un live à distance, les deux** : l'animatrice appelle le vendeur (30 min avant, un essai) **et** un
  message automatique l'invite 15 min avant (« Rejoindre mon live ») ; 5 min avant, s'il n'a pas dit être
  prêt, l'animatrice est alertée.
- Annuaire : liens vérifiés pendant les **créneaux de vérification** (8:00–11:00 et 18:00–21:00 par défaut),
  retirés à la fin du créneau. **Pass de 30 jours** pour envoyer ses liens (5 000 F par défaut).
- Un nouveau vendeur, un nouveau produit et un lien de live sont **vérifiés par l'équipe** ; un refus
  envoie un motif au vendeur.

## Shop et livraisons

- **Mode de vente choisi par l'équipe pour chaque vendeur** : contact direct sur WhatsApp, ou vendu par OCD.
- Vendu par OCD : **qui livre** est choisi pour chaque vendeur : le vendeur lui-même, un livreur OCD qui
  passe chercher, ou le stock OCD.
- **Un colis par vendeur** ; le client reçoit un **code à 4 chiffres** : pas de colis livré sans le code,
  3 codes faux bloquent le colis.
- Paiement à la porte : espèces, paiement sur le téléphone du client, ou Mobile Money déclaré (réglable).
- **Reversements** au rythme de chaque vendeur, seulement pour les colis confirmés par le code.
- **Pas de remise sans paiement** : dans l'appli des colis, le code du client n'est accepté qu'une fois
  l'argent à la porte encaissé ; un vendeur qui n'encaisse pas montre le paiement sur le téléphone du
  client, sinon il appelle l'équipe (qui peut valider sans code, avec un motif).
- **Reprise de livraison par le livreur** après un problème, tracée dans l'historique du colis (qui, après
  quel problème). Le nombre d'échecs compte toujours : au-delà du réglage, le colis retourne au vendeur.
- **« Mes produits »** (16 novembre 2026, [`PLAN_MES_PRODUITS.md`](PLAN_MES_PRODUITS.md)) :
  - le vendeur règle le **stock libre** (les pièces réservées par les commandes ne sont jamais retirées) ;
    − et + ajoutent au stock du moment, chaque changement est tracé ;
  - un **prix** se lit avec ou sans espaces, points et devise (« 3 000 F ») ; ce qui n'est pas un seul
    prix est refusé, jamais deviné ; centimes seulement dans une devise qui en a ;
  - **photo de la galerie ou prise** (réglable) : l'authenticité vient de la vérification de l'équipe
    (raison de refus « Photo qui n'est pas la tienne ») ; réduite dans le téléphone (1600 px, réglable),
    10 Mo au plus (réglable) ;
  - **un refus dit toujours pourquoi** : le vendeur lit le message du motif, corrige le produit (nom,
    prix, photo) et le renvoie à la vérification ; un produit en vente ne se corrige pas ainsi (son
    nouveau nom ou sa nouvelle photo seront vérifiés pendant que l'ancienne version reste en vente).
  - **« Mes produits » suit l'ordre de la boutique** : un nouveau produit et une copie arrivent en
    premier ; le vendeur met un produit en premier, le monte ou le descend ;
  - **une copie** n'a ni stock ni historique (contacts, refus) et passe à la vérification ;
  - **partager un produit** donne une image au format du statut WhatsApp (photo, nom, prix, QR code) ;
    **le catalogue** met 4 produits en vente par image (réglable), avec le QR code de la boutique ;
  - **le démarrage du vendeur** (« Ta boutique est prête à … % ») reste dans « Mon espace » tant qu'une
    étape manque.
- **Une photo par couleur** (le vendeur dans « Mes produits », ou l'équipe) : la page change de photo avec
  la couleur ; la photo s'ouvre en plein écran. Une taille ou une couleur épuisée se choisit encore, pour
  **« Préviens-moi quand c'est de retour »** (WhatsApp, dès que le stock revient).
- **Le replay se lit dans la page** quand la plateforme le permet (YouTube, TikTok, Facebook) : un produit
  touché fait aller la vidéo à son moment. Le lecteur ne se charge qu'au premier toucher. Ailleurs
  (Instagram…), la vidéo s'ouvre sur son site, avec le moment du produit écrit.
- **Contact direct** : le produit a sa fiche sur le site, sans panier (bloqué aussi côté serveur) ; le
  bouton WhatsApp envoie au vendeur le choix (couleur, taille…) et le lien du produit.
- **Voix des pages** gardée partout, même là où le design n'a pas de bouton ; sur téléphone, « Partager »
  ne garde alors que son icône.
- **Commande sans e-mail** : le client donne son nom, son WhatsApp, sa ville, son quartier et un point de
  repère ; il suit sa commande sur WhatsApp et sur la page de suivi.
- **Retour** demandé par le client depuis la page de suivi pendant **30 jours** après la livraison
  (réglable, 0 = pas de retour) ; l'équipe reçoit une activité pour l'organiser.
- **Magasins des vendeurs** (chantier 17, [`PLAN_MES_PRODUITS.md`](PLAN_MES_PRODUITS.md)) :
  - **un magasin est vérifié avant d'être montré** : photo de la devanture avec l'enseigne et position
    prise dans le magasin (au plus 200 m de précision). Seuls l'adresse, la position et la photo
    repassent à la vérification, et le magasin est caché aux clients pendant ce temps (jamais une
    adresse non vérifiée à l'écran) ; horaires, téléphone et « fermé jusqu'au… » changent tout de suite ;
    un refus envoie son motif ;
  - **un vendeur qui vend depuis chez lui** est montré aussitôt, sans vérification : son quartier,
    « Sur rendez-vous » et WhatsApp, jamais sa position, son repère ni sa photo. L'en-tête de la
    boutique ne montre plus le repère personnel du vendeur (seulement son quartier et sa ville) ;
    l'équipe et le livreur voient l'adresse complète ;
  - **ouvert ou fermé à l'heure du magasin**, même pour un client à l'étranger ; « fermé jusqu'au 18 »
    compte le 18 ;
  - **les appuis sur Itinéraire, Appeler et WhatsApp** sont comptés pour le vendeur, une fois par
    visiteur toutes les 10 minutes, gardés 400 jours ;
  - **un lieu sans OCD Business, plusieurs avec** ; à la fin de la formule rien n'est effacé, les lieux
    au-delà du premier ne sont plus montrés ; offerts à tous jusqu'au lancement de la formule ;
  - **l'affiche QR** est une image A4 claire (peu d'encre), envoyable à un imprimeur par WhatsApp ; **les
    étiquettes de prix** sont une page à imprimer (3 × 8 par A4), le prix étant celui du site ;
  - **le lieu de départ des colis** est choisi par le vendeur (sinon son seul lieu, sinon son adresse) :
    le prix de la livraison part de sa ville, et le colis garde le lieu où le livreur le prend, même si
    le vendeur en change ensuite.
- **Stock par magasin** (chantier 18, [`PLAN_MES_PRODUITS.md`](PLAN_MES_PRODUITS.md), section S) :
  - **un emplacement de stock par lieu, dans le stock de l'entrepôt de la boutique**, pas un entrepôt par
    magasin : le site compte toujours toutes les pièces d'un produit (un entrepôt par magasin ferait
    paraître épuisés les produits des autres magasins), et chaque lieu a les siennes. Le premier lieu
    reçoit les pièces que le vendeur avait ; un lieu retiré rend ses pièces libres au lieu de départ des
    colis ; chaque mouvement est un transfert interne tracé. Les produits gardés dans le stock d'OCD ne
    sont pas concernés ;
  - **montré à partir de 2 lieux** : avec un seul, rien ne change pour le vendeur ni pour le client
    (« Aussi en magasin : Akwa ») ; « Mon stock » sert aussi, avec un seul lieu, aux produits qui ont
    des tailles ou des couleurs ;
  - **les − / + et l'envoi d'un magasin à l'autre comptent tout de suite**, dans les deux magasins
    pour un envoi : pas d'étape « en route », les pièces réservées pour une commande ne bougent pas ;
  - **le client voit « Disponible », « Disponible · plus que 2 » ou « Épuisé » par magasin**, jamais le
    nombre exact d'un magasin (la page reçoit au plus 4) ; le bloc est caché quand le choix est épuisé
    partout, « Préviens-moi » le dit déjà. « Préviens-moi » nomme les magasins où le produit est revenu,
    une fois ce message approuvé par Meta (l'ancien part jusque-là) ;
  - **le magasin qui sert une commande** est choisi quand son colis est fait, avant que ses pièces soient
    réservées : un magasin de la ville du client qui a toute la commande, sinon le lieu de départ des
    colis s'il a tout, sinon un autre magasin qui a tout, sinon un colis par magasin (chaque produit du
    premier qui l'a, sinon de celui qui en a le plus). Le prix de la livraison est compté depuis ce
    magasin ; le client a payé une livraison : elle reste sur le premier colis du vendeur.
- **Gérer ses produits** (chantier 19, [`PLAN_MES_PRODUITS.md`](PLAN_MES_PRODUITS.md), étape 2) :
  - **un produit en vente reste en vente pendant sa vérification** : le nouveau nom et les nouvelles photos
    (photos de couleur comprises) attendent l'équipe, la version d'aujourd'hui reste à l'écran. Acceptée,
    la modification s'affiche tout de suite ; refusée, avec un motif, la version d'avant reste et le vendeur
    corrige ; revenu au nom d'aujourd'hui et sans nouvelle photo, il n'y a plus rien à vérifier ;
  - **le prix change tout de suite, sans vérification** ; au-delà d'un écart de 50 % (réglable, 0 : jamais
    demandé), le vendeur le confirme. Chaque prix d'un produit de vendeur va dans son historique (par le
    vendeur, l'équipe ou à la création), les grands écarts en couleur ; **le stock n'est jamais vérifié** ;
  - **les photos suivent l'ordre d'Odoo** : la première est la photo principale (celle des cartes) ; une
    photo non vérifiée ne passe jamais en premier ; un produit garde au moins une photo vérifiée ; 8 photos
    au plus (réglable) ;
  - **retirer de la vente ne supprime rien** : le produit n'est plus montré, les commandes passées le
    gardent, le vendeur le remet d'un geste ; un produit caché par l'équipe ne peut pas être remis par le
    vendeur ; les clients qui attendent son retour sont prévenus quand il est remis et en stock ;
  - **un produit ajouté sans réseau reste dans le téléphone** (base du navigateur), photo comprise, et part
    quand le réseau revient ou à la prochaine visite de « Mes produits » ; le jeton du formulaire évite
    qu'il soit ajouté deux fois. Pas de *service worker* : il ne part pas tant que la page n'est pas
    rouverte, et la page ne s'ouvre pas sans réseau ;
  - **WhatsApp** : une modification acceptée envoie le message « produit accepté » ; une modification
    refusée a son propre message (`ocd_modification_refusee`), envoyé une fois approuvé par Meta (le message
    « produit refusé » dirait qu'il n'est pas en ligne).
- **Autour des magasins** (chantier 20, [`PLAN_MES_PRODUITS.md`](PLAN_MES_PRODUITS.md), A.1 à A.3, A.5,
  A.7 ; maquettes `VacancesProximite`, `RetraitMagasin`, `MettreDeCote` validées le 17 novembre 2026) :
  - **mode vacances** : 60 jours au plus (réglable) ; les produits restent visibles, les commandes sont en
    pause partout (bouton du produit, panier même rempli avant, paiement, WhatsApp d'un vendeur en contact
    direct) ; les commandes reprennent le jour du retour, à l'heure du vendeur, ou avec « Revenir
    maintenant » ; les clients qui ont demandé sont prévenus sur WhatsApp ; un « Préviens-moi » de produit
    attend aussi le retour du vendeur ;
  - **près de chez moi** : la position du téléphone, arrondie à environ 100 m, n'est que dans l'adresse de
    la page (jamais gardée, une telle page n'est jamais mise en mémoire) ; un vendeur qui vend depuis chez
    lui ne montre jamais sa position : il est classé par ville ;
  - **le bot d'OCD donne les magasins** du vendeur dont parle le client (lien d'un produit ou d'une
    boutique dans la conversation, sinon sa dernière commande), sinon il répond comme avant ;
  - **retrait en magasin** : seulement dans un magasin ouvert au public qui a toute la commande du vendeur
    (les autres sont montrés, pas choisis) ; gratuit ; sans adresse demandée quand tous les colis sont
    retirés ; le colis part de ce magasin avec son vendeur, aucun livreur ne lui est jamais donné.
    « C'est prêt » donne la date limite : la fermeture du magasin après 3 jours (réglable), son jour
    ouvert suivant s'il est fermé. Au comptoir, **l'argent d'abord, puis le code** : Mobile Money sur le
    téléphone du client chez tous les vendeurs, espèces seulement chez un vendeur qui encaisse déjà à la
    porte (commission retenue sur le reversement). **Le code de retrait n'est pas dans le WhatsApp** (Meta
    prend un code dans un modèle Utility pour une authentification) : le bouton ouvre le suivi, où il est.
    Pas venu : rappel la veille, puis annulé comme un colis retourné (pièces rendues au magasin, avoir s'il
    a payé en ligne) ;
  - **mettre de côté pour essayer** : la pièce est réservée tout de suite dans le magasin (une livraison
    du magasin au client, en attente : elle n'est plus libre pour les autres), faite si le client l'achète
    au magasin, annulée sinon ; OCD ne prend rien sur cette vente faite au magasin. 24 h (réglable),
    jusqu'à la prochaine fermeture si le magasin est fermé à cette heure. Le vendeur répond d'accord ou
    refuser ; sans réponse, la pièce reste de côté. **Un délai passé n'est pas une absence** : seul « Pas
    venu » du vendeur compte ; après 2 absences (réglable) chez un vendeur, plus de mise de côté chez lui,
    le vendeur peut débloquer. Une mise de côté à la fois chez un vendeur. Un vendeur qui n'a qu'un
    magasin montre maintenant le stock du choix dans ce magasin, pour qu'on puisse y mettre de côté.
- **Vendre plus** (chantier 21, [`PLAN_MES_PRODUITS.md`](PLAN_MES_PRODUITS.md), 3.2, 3.4, 3.5 ; maquettes
  `PreparerLive`, `TaillesCouleurs`, `StockBas` validées le 17 novembre 2026) :
  - **préparer son live** : le vendeur coche et ordonne ses produits jusqu'à la fin du live, avec un mot
    pour l'animatrice ; la régie les montre d'abord, numérotés, puis les autres ; rien de préparé : comme
    avant. Toujours sans numéros de produits ni page « Je prends » ;
  - **stock bas** : compté à la confirmation d'une commande depuis le stock libre d'avant, pour chaque
    taille et couleur : un WhatsApp quand elle passe au seuil ou moins mais pas à 0 (« Épuisé » le dit
    déjà) ; une fois par passage sous le seuil, sans rien garder ; seuil 2 (réglable, 0 : jamais),
    modifiable par vendeur ; une mise de côté n'est pas une vente ;
  - **tailles et couleurs** : seulement les valeurs choisies par l'équipe (attribut « Proposé aux
    vendeurs ») ; une valeur qui manque se demande à l'équipe ; le même prix pour toutes ; 100 choix au
    plus ; le produit est vérifié comme avant, ses photos de couleur aussi. Sur un produit en vente, on
    ajoute des valeurs d'un attribut qu'il a déjà (jamais un nouvel attribut : ses pièces d'aujourd'hui
    perdraient leur stock) ; une valeur ne se retire pas, à 0 pièce elle est « Épuisé ». À
    l'installation, la Taille et la Couleur d'Odoo sont proposées, avec des valeurs courantes si elles
    n'en ont pas.
- **L'équipe du vendeur** (chantier 22, [`PLAN_MES_PRODUITS.md`](PLAN_MES_PRODUITS.md), A.9 ; maquette
  `EquipeDuVendeur` validée le 17 novembre 2026) :
  - la personne qui tient un magasin a **son propre accès**, avec son numéro WhatsApp comme le vendeur
    (son lien en mode lien, un code sinon ; jamais de mot de passe). Elle voit et change le stock de **son
    magasin seulement**, prépare les colis qui en partent, remet les retraits au comptoir (l'argent
    encaissé revient au vendeur) et répond aux pièces à essayer. Jamais : les prix, l'ajout ou la
    modification d'un produit, les reversements, les autres magasins, débloquer un client ; un produit
    dont le stock n'est pas compté le reste (c'est au vendeur de le décider) ;
  - **une personne, une équipe** : le numéro d'un vendeur ou d'un livreur est refusé, comme celui d'une
    personne déjà dans l'équipe d'un autre vendeur. Un téléphone ouvre une seule personne : sa connexion
    oublie le vendeur ou le livreur ouvert avant ;
  - **5 personnes au plus** (réglable, et par vendeur) ; **OCD Business** seulement : à la fin de la
    formule, l'équipe est en pause (elle voit « L'équipe est en pause »), rien n'est supprimé ; retirée,
    elle perd l'accès tout de suite et son historique reste ;
  - **ce qu'elle fait est tracé** : sur le colis (« Fait par Aïcha, équipe de Brenda »), sur la mise de
    côté (« Répondu par »), et dans les derniers changements de « Mon stock » du vendeur (« …, par
    Aïcha ») ;
  - **WhatsApp** : son lien part quand le vendeur l'ajoute ou le renvoie (comme un message demandé) ; les
    nouvelles de son magasin (colis à préparer, pièce à essayer) seulement **si elle les accepte** depuis
    son accueil, le même accord que partout (STOP les arrête). Le vendeur continue de tout recevoir ;
  - le lien personnel d'un livreur ou d'une personne d'une équipe n'ouvre jamais un espace de vendeur.
- **Suivre un vendeur** (chantier 1 et A.8 du plan ; maquette `SuivreVendeur` validée le 17 novembre 2026) :
  - « Suivre » remplace « Me prévenir sur WhatsApp » : **un WhatsApp à chaque live** du vendeur, au début
    du live, 2 lives par jour au plus et par vendeur (réglable) ; un abonné arrivé pendant le live n'est
    pas prévenu de celui-ci. Les « Me prévenir » en attente sont devenus des abonnements aux lives ;
  - **les nouveautés** : le vendredi (réglable) dès 10 h à l'heure du vendeur, les produits mis en vente
    (vérifiés, en vente) depuis le dernier envoi ; rien de nouveau, rien d'envoyé. **Une fois par mois**
    (le premier vendredi) pour tous, **chaque semaine avec OCD Business**. Modèle **Marketing** chez Meta,
    seulement aux abonnés qui ont coché « Ses nouveautés » ;
  - **suivre vaut accord** pour ces messages (la case d'OCD Live et celle de WhatsApp), jamais après STOP ;
    STOP arrête tout, « Ne plus suivre » arrête un vendeur ;
  - **un numéro tapé n'est pas vérifié** : un téléphone ne retrouve que les abonnements faits sur lui
    (cookie signé) ; le bouton d'un message (son secret) ouvre tous les abonnements de ce numéro. Une
    personne connue (vendeur, compte, abonné venu d'un message) suit sans retaper son numéro ;
  - **le vendeur voit combien** d'abonnés (et les nouveaux de la semaine), **jamais leurs numéros** ;
    l'équipe les voit dans le back-office ;
  - « Nouveau » sur la boutique : un produit mis en vente dans les 7 derniers jours ; depuis le message des
    nouveautés, ses produits passent en premier.
- **Garantie OCD et avis** (chantier 2 ; maquette `GarantieAvis` validée le 17 novembre 2026) :
  - **la garantie dit ce qui est vrai** : le vendeur n'est payé qu'après le code de livraison, pas livré :
    remboursé, retour possible pendant le nombre de jours réglé (rien sur le retour s'il est à 0). Un
    vendeur en vente directe (il encaisse lui-même) est dit hors de la garantie ;
  - **un avis par colis livré** : seul celui qui a reçu le colis le donne, une fois, et peut le changer ;
    la note de WhatsApp ou de l'ancienne page devient l'avis de chaque colis livré de la commande (le mot
    écrit avant est gardé). Le nom montré est le prénom et l'initiale, jamais le numéro ;
  - **la note dès 3 avis**, avant : « Nouveau vendeur » (une seule note ne dit rien) ;
  - **le vendeur ne supprime pas un avis** : il le signale avec un mot, l'avis reste affiché jusqu'à la
    décision de l'équipe (garder ou masquer) ; un avis masqué ne compte plus ;
  - **« Vendeur vérifié » est une décision de l'équipe** (qui et quand sont gardés), proposée à la
    validation d'un nouveau vendeur, retirée en décochant ;
  - **signaler** : une fois par jour et par personne (ou par téléphone sans numéro, sous une signature,
    jamais l'adresse en clair) ; le vendeur ne sait jamais qui a signalé ; un produit retiré à la suite
    d'un signalement l'est comme un refus de l'équipe, avec sa raison envoyée au vendeur.
- **Statistiques du vendeur, « Mes chiffres »** (chantier 3, avec 3.3 « Ventes par produit » ; maquette
  `MesChiffres` validée le 17 novembre 2026) :
  - **un seul calcul** (`ocd.vendor.figures`) pour la page, la carte « Mes chiffres » de Mon espace, la
    ligne « Vendu » de Mes produits, les chiffres des magasins et le résumé du lundi ;
  - **pour tous** : les ventes du mois dans Mon espace (comparées aux mêmes jours du mois d'avant) et la
    ligne « Vendu : N en 30 jours · dernière vente … » ; **avec OCD Business** (offert pendant le
    lancement) : la période (7 jours, 30 jours, 3 mois), les visites, les contacts WhatsApp, les lives, les
    meilleures heures, les clients fidèles, les ventes par produit, les magasins. Sans la formule, le
    détail est annoncé ;
  - **ventes** : les commandes confirmées, sans les annulées ni les colis rendus (tous les colis de la
    ligne revenus ou annulés), le prix payé des produits du vendeur (taxes comprises, sans la livraison),
    converti dans la devise de la société ; l'évolution compare à la période d'avant de même durée ;
  - **ventes d'un live** : le panier retient les lives dont le visiteur a vu la boutique pendant le live,
    tant que le live compte (pendant, puis 3 heures après sa fin, réglable) ; à la confirmation, chaque
    ligne d'un vendeur est notée avec son dernier live retenu. Une commande confirmée plus tard (Mobile
    Money vérifié par l'équipe) compte donc encore pour le live ;
  - **nouveaux comptages, jour par jour** (`ocd.vendor.count`, une ligne par vendeur, jour, type et
    live ou produit, jamais une ligne par appui) : « Ouvert depuis OCD » (les « Regarder » passent par
    `/ocd/regarder/…`, qui compte puis ouvre le live), les visites de la boutique (une par téléphone et par
    jour, jamais celles du vendeur ; dites par la page une fois affichée, pour qu'elle reste la même pour
    tous et gardée en mémoire pendant les foules d'un live), les contacts WhatsApp. Écrits comme les visites de la régie : en
    mémoire, puis toutes les 5 secondes dans une transaction à part. Gardés 400 jours ;
  - **meilleures heures** : les commandes des 3 derniers mois à l'heure du vendeur ; les tranches « Matin
    jusqu'à 12 h · Midi 12 h à 15 h · Après-midi 15 h à 18 h · Soir dès 18 h » (aucune commande laissée
    de côté, la nuit compte avec le soir ou le matin). « Réserver un live » ouvre la réservation sur le
    prochain jour et l'heure du studio qui correspondent, sinon sur le jour ;
  - **clients fidèles** : 2 commandes ou plus en 12 mois (réglable), le prénom et l'initiale, jamais le
    numéro ;
  - **résumé du lundi** : seulement si le vendeur l'a allumé (l'interrupteur vaut accord, STOP l'arrête),
    le lundi dès 9 h à son heure (jour et heure réglables), rien quand rien ne s'est passé ;
  - **l'équipe** voit la page comme le vendeur (bouton « Chiffres » de la fiche, comme « Voir son
    espace »).
- **OCD Vote** (chantier 4 ; maquette `OcdVote` validée le 17 novembre 2026, avec ses choix) :
  - **qui crée un concours** : un organisateur (vérifié par l'équipe : « Organisateur vérifié » sur la fiche
    du contact) ou OCD Live ; l'équipe crée le concours dans le back-office avec l'organisateur, il ajoute
    ses candidats dans son espace et l'envoie à vérifier ; l'équipe le vérifie et l'ouvre (« À vérifier »,
    colonne « Concours »). L'organisateur se connecte avec son numéro et un code WhatsApp, comme les
    vendeurs (pas de lien personnel : aucun nouveau modèle à faire approuver pour lui) ;
  - **prix** : 100 F la voix, 10 voix à 900 F, 50 voix à 4 000 F, un autre nombre au prix de la voix
    (réglable pour un nouveau concours, puis sur le concours avant l'ouverture) ; après l'ouverture, le
    prix, les paquets, les dates et la part ne changent plus (ils sont dans le règlement) ;
  - **seules les voix payées comptent** : une ligne par paiement (`ocd.vote`), comptée quand le paiement
    confirme la commande, jamais par le navigateur ; un paiement remboursé retire ses voix ; un paiement
    commencé après la fin ne compte pas (« à rembourser ») ; une demande non payée en 10 minutes
    (réglable) est annulée, sauf un Mobile Money envoyé et vérifié par l'équipe ; pas de voix gratuites,
    pas de limite par personne (l'équipe voit les paiements d'un même téléphone d'un coup) ;
  - **le paiement** : le formulaire de paiement d'OCD Live (les moyens du pays et de la devise, comme pour
    les réservations) ; sur WhatsApp, « VOTE 12 » au bot, puis le nombre de voix (boutons), puis la
    demande CamPay sur le téléphone quand le numéro est camerounais, sinon le lien de la page du paiement ;
  - **classement** : les nombres cachés les 2 dernières heures (réglable par concours, 0 pour toujours
    montrer), l'ordre reste ; le bandeau de la finale suit la même règle. Des voix égales ont le même rang ;
  - **résultats certifiés** : publiés par l'équipe après la fermeture (automatique à l'heure de fin), avec
    une signature du serveur sur le PDF et sur la page des résultats, pour comparer ;
  - **partage** : 60 % des sommes encaissées pour l'organisateur, 40 % pour OCD Live (frais du Mobile
    Money compris), versés sous 3 jours après les résultats ; le reversement est noté sur le concours
    (à verser, versé avec la référence du transfert), l'écriture comptable reste à l'équipe ;
  - **écriture neutre** : « candidat » est générique (un concours peut avoir des hommes et des femmes),
    les rangs « 1er, 2e, 3e » ; rien n'est deviné d'après un prénom ;
  - **à vérifier avant d'ouvrir dans un pays** : le cadre légal des votes payants (pas de tirage au sort,
    rien à gagner pour les votants : le règlement de chaque concours le dit) ; d'abord le Cameroun avec
    CamPay, l'UEMOA avec CinetPay ou Flutterwave (chantier 5).
- **OCD Tickets** (chantier 6 ; maquette `OcdTickets` validée le 18 novembre 2026, avec ses choix) :
  - **l'événement est celui de l'application Événements d'Odoo** (gratuite) : sa date, son fuseau, son
    lieu, ses types de billets et leurs places ; l'onglet « OCD Live » ajoute l'organisateur, sa part,
    l'affiche, la vente à l'entrée, les lives qui vendent les billets et leurs prix du live, les
    contrôleurs. Un billet est une inscription d'Odoo, créée quand son paiement est confirmé ; les e-mails
    de l'application Événements sont coupés (tout part sur WhatsApp) ;
  - **qui vend** : des organisateurs vérifiés par l'équipe (le même compte et le même espace que pour OCD
    Vote) et OCD Live ; l'équipe crée l'événement avec l'organisateur, qui l'envoie à vérifier depuis son
    espace ; l'équipe le vérifie et le met en vente (« À vérifier », colonne « Événements ») ;
  - **partage** : 90 % pour l'organisateur, 10 % pour OCD Live (frais du Mobile Money compris), aucun frais
    en plus pour l'acheteur ; noté « à verser » 3 jours après l'événement, versé avec la référence du
    transfert, comme pour OCD Vote ;
  - **billets** : un QR par personne, au nom de l'acheteur, signé par le serveur (comme le ticket du live) et
    un code à taper (« NAF-7K2Q-41 ») ; 10 billets au plus par commande (réglable) ; « Donner ce billet » à
    un ami : un nouveau QR et un nouveau code, l'ancien ne marche plus. Un billet « table » est un QR pour la
    table : le groupe entre ensemble ;
  - **places** : gardées 10 minutes pendant le paiement (réglable), plus longtemps si un paiement est en
    route (Mobile Money vérifié par l'équipe) ; puis remises en vente. Deux acheteurs qui paient la dernière
    place en même temps ont tous les deux leur billet : l'argent est reçu, l'équipe le voit ;
  - **contrôle** : les contrôleurs ajoutés par l'organisateur (nom, WhatsApp, porte) se connectent avec leur
    numéro et un code WhatsApp, et scannent avec la caméra de leur téléphone sur une page d'OCD Live (le
    lecteur de QR du navigateur ; sans lui, ils tapent le code). La réponse : « Entrée OK », « Déjà entré »
    (heure, porte, contrôleur), « Pas pour ce soir », « Billet inconnu ». Hors réseau, la liste des billets
    reste dans le téléphone et les entrées partent au retour du réseau avec leur heure (risque accepté :
    deux portes hors réseau pourraient laisser entrer la même copie une fois chacune) ;
  - **en live** : un billet passe à l'écran comme un produit (régie, boutique du vendeur du live) ; un prix
    du live possible, jusqu'à la fin du live ; les billets vendus pendant un live sont comptés à part ;
  - **vente à l'entrée** : si l'organisateur l'autorise, ses contrôleurs vendent sur place, en espèces
    (comptées avec eux à la fin, comme la caisse des livreurs) ou en Mobile Money (le formulaire de
    paiement d'OCD Live) ; le billet part sur le WhatsApp du client et entre aussitôt ;
  - **annulé ou déplacé** : annulé, chaque billet payé est à rembourser et les acheteurs sont prévenus ;
    déplacé (« Déplacer », jamais en changeant la date à la main une fois des billets vendus), les billets
    restent valables et l'acheteur demande le remboursement depuis « Mes billets » pendant 7 jours
    (réglable) ; pas de remboursement pour un acheteur qui ne vient pas ;
  - **ventes en ligne** : jusqu'à l'heure du début (réglable : quelques heures avant) ; la vente à l'entrée
    continue jusqu'à la fin ;
  - **pays** : le formulaire de paiement d'OCD Live, donc CamPay au Cameroun, CinetPay et Flutterwave dans
    l'UEMOA (chantier 5), la carte partout.
- **Programme et événements** (chantier 7, avec le prix promo 3.1 ; maquette `ProgrammeSoirees` validée le
  18 novembre 2026) :
  - **le prix promo passe par le seul calcul des prix d'Odoo** : la boutique, le shop, la fiche, les
    cartes des lives, la régie, le panier et la commande ont le même prix, dans toutes les devises. Le prix
    barré est le prix le plus bas du produit des 14 derniers jours (réglable), gardé à la création de la
    promo : un prix monté juste avant ne fait pas une promo. 50 % de remise au plus et 30 jours au plus
    (réglables) ; la promo du vendeur s'affiche tout de suite, sans vérification de l'équipe ;
  - **deux promos qui se croisent** (celle du vendeur et celle d'un événement) : le prix le plus bas
    s'applique, le prix ne monte jamais pendant un événement ;
  - **la fin d'une promo** : le prix revient tout seul à l'heure (aucune tâche à lancer). Un panier
    commencé en promo la garde 2 heures après la fin, le temps de payer ; ensuite, le panier et la page de
    paiement reprennent le prix du moment et le disent. Le vendeur qui baisse son prix sous la promo
    l'arrête ; les étiquettes de prix imprimées gardent le prix habituel ;
  - **le programme des lives** : les 7 prochains jours à l'heure du téléphone, les lives connus d'avance
    (studio ou à distance, sur les comptes d'OCD Live) ; les lives des vendeurs sur leurs propres comptes
    s'ajoutent quand ils commencent. Sur ordinateur, un guide télé par compte d'OCD Live ; deux lives du
    même compte en même temps passent l'un sous l'autre. La cloche est « Suivre » le vendeur (chantier 1) ;
  - **les grands événements** (créés par l'équipe) : **une soirée, une journée ou plusieurs jours de
    suite** (14 jours au plus, réglable), demandé par l'équipe après la maquette. Leur étiquette vient de
    leurs heures : « Grande soirée » (un jour, à partir de 16 h ; une soirée qui finit avant 6 h le
    lendemain reste une soirée), « Grande journée », « Grand événement · 6 jours ». Les pages s'appellent
    « Grands événements » (`/evenements` ; les premières adresses `/soirees` y mènent) ; les noms
    techniques gardent « evening » ;
  - **les promos d'un événement** valent pendant toutes ses heures, sans coupure (pas de créneaux par
    jour : un prix qui change chaque soir serait difficile à suivre pour les clients) ; elles s'affichent
    seulement après la vérification de la participation par l'équipe, suivent l'événement s'il est
    déplacé et s'arrêtent s'il est annulé ;
  - **les inscriptions** des vendeurs ferment 3 jours avant le début (réglable), ou plus tard au choix de
    l'équipe, au plus tard avant la fin : un vendeur peut rejoindre un événement de plusieurs jours en
    cours. Un vendeur participe avec un live pendant l'événement (la réservation habituelle, au prix
    habituel) ou au moins une promo ;
  - **« Me prévenir sur WhatsApp »** : un message un peu avant le début (15 minutes, réglable), qui donne
    la fin des promos (« jusqu'à dimanche 7 décembre à 23 h » pour plusieurs jours) ; aucun message pour
    un événement sans vendeur accepté. Les textes des modèles marchent pour un seul vendeur comme pour
    plusieurs (« Vendeurs en live : 1 »).
- **Clips automatiques** (chantier 8 ; maquette `ClipsAutomatiques` validée le 18 novembre 2026, avec ses
  choix et ses recommandations « Pour que ça tienne en vrai ») :
  - **la vidéo vient de l'équipe** (l'enregistrement du studio, ou la vidéo téléchargée du compte d'OCD
    Live), jamais téléchargée automatiquement des plateformes. Envoyée par morceaux de 8 Mo, 4 Go au plus ;
    un envoi coupé reprend en choisissant le même fichier ; la place sur le serveur est vérifiée avant ; un
    envoi abandonné est effacé après 24 h. Les vidéos des lives restent hors de la base et des sauvegardes
    et sont effacées après 7 jours (réglable) ; les clips restent ;
  - **le vrai début du live** : « Le live commence » dans la régie (de 30 minutes avant l'heure réservée
    jusqu'à la fin) ; sans lui, l'heure réservée. Les moments déjà notés sont recomptés ;
  - **une vidéo en plusieurs parties** : chaque partie commence où la précédente finit, réglable à 5 s près
    avec un aperçu du premier moment ; un réglage ne refait que les clips de cette partie ;
  - **un clip par produit et par live** : le moment du produit qui a le plus de place avant le produit
    suivant ; 3 s avant le moment, 30 s au plus, coupé 1 s avant le produit suivant, 12 s au moins, sinon
    « Pas de clip » (réglables). Un clip refait garde son lien court (il est peut-être déjà partagé) ;
  - **le lien court** : `/p/` et 6 lettres sans 0, O, 1, I ni L ; l'adresse du site, ou une adresse plus
    courte réglable. Il mène au produit avec la couleur montrée, sinon à la boutique, sinon au shop, jamais
    à une erreur. Les clips d'un produit retiré de la vente depuis 3 mois (réglable) perdent leur vidéo mais
    gardent leur lien ;
  - **ce qui s'affiche** : un clip seulement si son produit est en vente, son vendeur actif et sans « Pas de
    clips » ; le vendeur ou l'équipe le masque ; sur la fiche produit, le clip le plus récent, lu au
    toucher (rien ne se charge avant) ;
  - **des chiffres honnêtes** : une visite par téléphone et par jour, sans les robots (aperçus de WhatsApp,
    TikTok, Facebook, navigateurs sans écran), ni le vendeur ni l'équipe ; une lecture comptée une fois par
    page vue. Une vente compte pour un clip si la commande arrive dans les 7 jours après la visite par son
    lien, depuis le même téléphone (le panier garde le clip) ; avec plusieurs clips, la dernière visite ;
    « Venus des clips » dans Mes chiffres (OCD Business) ;
  - **un serveur qui reste rapide** : chaque clip est une tâche notée en base, prise par un seul serveur
    (son essai compté dès qu'il la prend), 3 essais à des passages différents de la tâche planifiée, reprise
    après 30 minutes si le serveur s'est arrêté ; une erreur imprévue sur un clip n'arrête pas les autres ;
    ffmpeg en basse priorité, 2 threads. Les messages d'erreur s'écrivent dans la langue de la personne
    qui les lit ;
  - **le partage** : « Partager » envoie la vidéo elle-même et son texte (copié aussi : TikTok et Reels ne
    gardent que la vidéo) au prix du moment, promo comprise ; une vidéo trop longue à préparer demande un
    second toucher. « M'envoyer le clip sur WhatsApp » part même sans l'accord aux notifications (le
    vendeur le demande), 10 par jour au plus, et ne s'affiche que quand son modèle peut partir. Un clip
    devient la vidéo de la carte du fil tel quel (il est déjà au bon format) ;
  - **WhatsApp** : un nouveau type d'en-tête « vidéo » dans `whatsapp_cloud` : la vidéo est prise du
    document au moment de l'envoi (une copie, 16 Mo au plus), l'exemple pour Meta est la vidéo donnée sur
    le modèle ou celle du dernier document.
- **Frais de livraison : un prix par colis** (un colis par vendeur), selon la ville d'où part le colis et
  le quartier du client ; le client paie la somme des colis.
- **Le vendeur qui livre fixe ses prix**, dans les bornes fixées par l'équipe (réglable) ; OCD garde une
  part réglable de ses livraisons (**0 %** au départ). Les livraisons des livreurs OCD et des agences
  reviennent à OCD.
- **Vers une autre ville ou un autre pays : seulement par un tarif « agence »** prévu par l'équipe, sans
  paiement à la porte. Une adresse qu'aucun tarif ne couvre est refusée avant le paiement.
- **OCD Express** (chantier 9 ; maquette `OcdExpress` validée le 18 novembre 2026, avec ses choix et
  « Pour que ça tienne en vrai ») :
  - **qui envoie** : tout vendeur avec un numéro WhatsApp, même sans boutique, connecté comme les vendeurs
    (lien ou code sur WhatsApp) ; un vendeur d'OCD Live garde son espace, avec « Envoyer un colis » en plus ;
    le numéro d'un livreur ne devient pas celui d'un expéditeur. D'abord **20 à 30 expéditeurs invités** à
    Douala, puis la page `/express` pour tous (réglage « Ouvert à ») ;
  - **où** : les villes où OCD a des livreurs, Douala d'abord ; vers une autre ville ou un autre pays, par
    agence, payé d'avance, sans paiement à la porte ;
  - **le prix** : le tarif « livreur OCD » de la ville du client (1 000 F dans Douala), payé par
    l'expéditeur ou ajouté au montant à encaisser ; **encaissement 1,5 %, 150 F au moins**, rien pour un
    colis déjà payé ; **retour 500 F** ; **ramassage gratuit dès 3 colis** dans le même passage, 500 F en
    dessous, dépôt au point OCD gratuit ; second passage gratuit ; deux ramassages ratés chez l'expéditeur
    facturés. Tout est réglable ; prix revu après 4 semaines avec le coût réel par colis. Moins cher avec
    OCD Business (chantier 12) ;
  - **payer à la porte** : en espèces au livreur, ou sur le téléphone du client ; **pas de Mobile Money
    « déclaré »** pour Express ; au-dessus de 100 000 F, sur le téléphone seulement ; jamais sur le numéro
    personnel du livreur. Le client peut **ouvrir le colis devant le livreur avant de payer** (oui par
    défaut, au choix de l'expéditeur pour chaque colis). Tout ou rien ;
  - **les espèces** : le colis contre l'argent et le code (comme le shop) ; **150 000 F au plus sur un
    livreur** (au-dessus, dépôt au point OCD) ; un fond de caisse pour rendre la monnaie ; la caisse du soir
    avec celle du shop ; **un manque à la caisse devient une dette du livreur** (retenue ou réglée), plus
    seulement une note ;
  - **l'argent de l'expéditeur** : versé par Mobile Money le **jour ouvré suivant**, seulement l'argent
    arrivé chez OCD (espèces remises à la caisse, paiement confirmé par le fournisseur), moins ses frais :
    la facture attend l'argent, alors que celle du vendeur du shop est faite à la livraison. Jamais
    d'avance. Ce qu'il doit (retour, ramassage, livraison d'un colis déjà payé) est retiré du versement
    suivant, **10 000 F au plus** ; au-delà, il règle par Mobile Money avant de créer un colis. Un nouveau
    numéro de versement attend **48 h** et l'ancien numéro est prévenu ;
  - **les plafonds** : 50 000 F à encaisser par colis pour un nouvel expéditeur, 200 000 F après 20 colis
    livrés sans souci ; au-delà, l'équipe valide le colis ; pièce d'identité au-delà d'un montant par jour ;
  - **la responsabilité** : OCD transporte, ne vend pas. Perdu ou abîmé par OCD : la valeur déclarée (le
    montant à encaisser, ou la valeur écrite pour un colis déjà payé) remboursée jusqu'à **50 000 F** ;
    jamais le contenu (la photo du colis fermé, prise au ramassage, fait foi). Les colis Express sont **hors
    de la garantie d'OCD Live**. « Un souci avec mon colis ? » pendant **48 h** après la livraison : le
    montant attend s'il n'est pas versé ; si l'équipe donne raison au client, la somme est retirée des
    versements suivants de l'expéditeur. 30 % de retours : un avertissement, puis la suspension (réglable) ;
  - **le ramassage** : chez l'expéditeur (son lieu, comme les magasins du chantier 17, vérifié la première
    fois) ou au point OCD (le studio) ; le livreur scanne ou tape le numéro EX et photographie les colis
    fermés ; **deux vagues** : créé avant 10 h, livré l'après-midi ; avant 15 h, livré le lendemain matin
    (réglables). La nuit, les colis dorment au point OCD, scannés à chaque passage de main ;
  - **les échecs** : 2 appels et 10 minutes d'attente avant « absent » ; le client envoie sa position depuis
    sa page ; 2 passages, puis le retour ; un refus à la porte est un retour ; **un retour est rendu contre
    le code de retour de l'expéditeur** ;
  - **les livreurs** : les livreurs OCD actuels de Douala ; **20 colis par livreur et par jour**, ramassages
    compris ; 20 % de la capacité gardés pour le shop ; l'expéditeur voit une journée pleine avant de créer ;
    un livreur de plus quand la ville dépasse 80 % de sa capacité 5 jours de suite (tableau de bord) ;
  - **hors réseau** : pas de remise contre des espèces ; seulement contre un paiement sur le téléphone du
    client, vu « Payé » sur son écran, le code partant au retour du réseau ;
  - **le client qui reçoit** : un WhatsApp dès la création (« Je confirme », « Changer le moment », « Ce
    n'est pas pour moi », qui arrête tout), puis au départ du colis avec la page de suivi (code, montant,
    « Pas là ? », « Envoyer ma position »), sans compte ; rien d'autre ; le code n'est jamais montré à
    l'expéditeur ni au livreur ; son nom et son numéro sont **effacés après 6 mois** (le montant et les
    dates restent) ; le livreur voit son adresse et son numéro le jour de sa tournée ;
  - **« Voir son espace »** sur la fiche d'un expéditeur (onglet OCD Express), comme pour un vendeur : un
    lien signé pour la personne de l'équipe connectée, qui ouvre « Mes envois » et « Mon argent » tels que
    l'expéditeur les voit (aider au téléphone, présenter la démo sans code WhatsApp), jusqu'à « Se
    déconnecter » ; rien n'est gardé dans le navigateur (18 novembre 2026).
  - **WhatsApp** : **un numéro à part pour OCD Express** (des blocages n'abaissent pas la note du numéro
    d'OCD Live) ; l'expéditeur coche l'accord de son client à chaque colis ; cinq modèles Utilitaire
    (français et anglais) : colis annoncé et en route (au client), colis pris, livré ou problème, versement
    fait (à l'expéditeur) ;
  - **avant d'ouvrir au public** : les règles des services de paiement de la CEMAC et la loi camerounaise
    de 2024 sur les données personnelles vérifiées avec un juriste ; seuls les frais sont le chiffre
    d'affaires d'OCD (facture des frais chaque mois avec le relevé) ;
  - **plus tard** : les points relais (chantier 10), plusieurs colis d'un coup, un lien pour les boutiques en
    ligne, l'assurance d'un colis de valeur, la tournée gardée dans le téléphone ;
  - **fait avec le code (18 novembre 2026)** : un colis Express est un colis du shop sans commande (numéros
    `EX-0001`), dans le même dispatch, la même tournée et la même caisse ; un passage de ramassage par
    expéditeur et par moment de la journée, fait par le livreur du quartier de l'expéditeur, qui livre aussi
    ses colis (le dispatch donne le passage entier à un autre livreur) ; un colis pas pris part au passage
    suivant ; le premier passage réussi marque le lieu de l'expéditeur vérifié ; la capacité compte tous les
    livreurs × 20 colis, moins la part du shop, et un colis va à la vague suivante quand la journée est
    pleine ; pas de ramassage le dimanche. L'argent passe par des factures et des avoirs d'achat, réunis
    dans les reversements du shop ; un vendeur qui est aussi expéditeur est versé chaque jour ouvré. Une
    vérification de l'équipe aussi au-delà de 300 000 F à encaisser en un jour sans pièce d'identité vue,
    et au-delà de 10 colis le premier jour (réglables). Un code de retour à 6 chiffres, 3 essais. « Ce
    n'est pas pour moi » avant le ramassage annule le colis (sans frais), après il retourne (500 F).
    L'accord du client coché par l'expéditeur vaut accord WhatsApp pour les messages de son colis ; « Ce
    n'est pas pour moi » arrête tous les messages vers ce numéro. Un **sixième modèle**
    (`ocd_express_numero`) prévient le numéro du compte quand le numéro de versement change. Les villes
    ouvertes se choisissent sur la société, le reste dans les Paramètres d'OCD Live ;
  - **manque de caisse d'un livreur** (pour tous les colis, pas seulement Express) : un écart négatif à la
    caisse du soir devient une dette du livreur, avec une activité pour le responsable, jusqu'à « Manque
    réglé ».
- **Points relais** (chantier 10 ; maquette `PointsRelais` validée le 19 novembre 2026 avec les choix
  recommandés) :
  - **qui** : des boutiques partenaires (kiosques de transfert et de crédit, pressings, boutiques de
    téléphones) choisies et **visitées par l'équipe** avant d'ouvrir ; et le **magasin vérifié et ouvert au
    public** d'un vendeur qui le veut (plan, A.6), pour tous les vendeurs (réglable), jamais chez un vendeur
    qui vend depuis chez lui. Un point relais est un **lieu** (la fiche des magasins), pas un nouveau
    modèle : ses horaires, son itinéraire et son téléphone sont ceux du lieu ; le partenaire est un
    contact « tient un point relais » qui se connecte par son numéro, comme l'équipe d'un vendeur ;
  - **le prix** : un tarif « point relais » par ville dans les Tarifs de livraison (500 F à Douala, 1 000 F
    à la porte), pour le shop et pour OCD Express ; seulement pour les colis portés par les livreurs OCD
    (ni un vendeur qui livre lui-même, ni une agence), et seulement quand le colis part de la ville du point
    relais. Sans tarif pour une ville, ses points relais ne sont pas proposés ;
  - **ce que gagne le point relais** : 150 F par colis remis au client, rien pour un colis repris ; une
    facture d'achat par colis (`ocd_relay_kind` = `earning`), versée **chaque mois** avec les reversements
    (un vendeur point relais, avec les siens) ;
  - **payer au point relais** : payé avant, ou **sur le téléphone du client au comptoir** (le QR de
    paiement à l'écran du point relais, le code accepté après le paiement) ; **jamais d'espèces** au
    lancement : le point relais ne garde l'argent de personne (sinon une caisse du soir chez chaque
    partenaire). À revoir si les clients le demandent ;
  - **le délai** : 7 jours, jusqu'à la fermeture du point relais le dernier jour, rappel 2 jours avant ;
    puis le colis repart (shop : comme un colis retourné, remboursé s'il était payé en ligne ; Express :
    rendu à l'expéditeur contre son code, 500 F), il attend au point relais que le livreur le reprenne ;
  - **les places** : 25 colis par défaut, réglable par point relais ; plein, en congé ou en pause, il n'est
    plus proposé ; les colis qu'il garde attendent leurs clients ;
  - **le code, pas le nom** : le code de livraison (ou le QR de la page du client, qui le porte) donne le
    colis, quelqu'un d'autre peut venir pour le client ; 3 codes faux bloquent le colis ; le code n'est
    jamais dans le WhatsApp (règle de Meta) ; le client est prévenu quand le point relais a **compté** le
    colis, pas quand le livreur part ; le point relais coche chaque colis qu'il a en main, un colis abîmé
    refusé reste au livreur comme problème ;
  - **OCD Express** : livrer au point relais, au choix de l'expéditeur (le quartier du point relais
    devient celui du client) ou du client sur sa page tant que le livreur n'est pas parti (le prix du point
    relais remplace celui de la porte) ; le message vient du numéro d'OCD Express. Déposer ses colis à un
    point relais au lieu du ramassage : plus tard ;
  - **un colis perdu au point relais** : OCD rembourse (le client par l'équipe ; l'expéditeur Express au
    plus le plafond des réglages) et le retient sur les gains du point relais (un avoir, `loss`) ; **en
    pause après 2 pertes**, rouvert par l'équipe seulement ; **pas de caution** au lancement (un reversement
    négatif n'est jamais payé, il attend les colis suivants) ;
  - **où commencer** : Douala, 5 ou 6 points relais dans les quartiers des livreurs, avec un accord signé
    (modèle à faire relire par un juriste) ;
  - **dans `ocd_live_shop`** et non dans un nouveau module : le point relais touche le choix de la
    livraison, le colis, la tournée, le dispatch et les reversements du shop ; OCD Express et WhatsApp
    l'étendent dans leurs modules.
- **Ambassadeurs** (chantier 11 ; maquette `Ambassadeurs` validée le 19 novembre 2026 avec les choix
  recommandés, pensée d'abord pour tenir face à la fraude) :
  - **qui** : tout le monde avec un numéro WhatsApp dans un pays où le shop livre, dès 18 ans (la
    charte cochée) ; le compte s'ouvre quand le code reçu sur WhatsApp prouve le numéro (programme
    ouvert à tous, sur invitation ou fermé : réglage) ; un vendeur ou un livreur aussi, jamais sur ses
    propres produits. Un ambassadeur est un **contact à part**, trouvé par son numéro parmi les
    ambassadeurs seulement : le client, le vendeur ou le livreur qu'il est aussi gardent leur contact,
    les contrôles comparent les numéros ;
  - **combien, payé par qui** : 5 % des articles (pas la livraison), au plus 3 000 F par colis, jamais
    plus que la commission d'OCD sur l'article (un vendeur à 3 % donne 3 %), **payés par OCD sur sa
    commission** : le client paie le prix du site, le vendeur ne paie rien. Plus tard : un bonus d'un
    vendeur sur ses produits ;
  - **sur quoi** : le **dernier lien ouvert** sur le téléphone compte 7 jours (la session, puis le
    panier), pour **tous les articles** de la commande ; à la confirmation, l'ambassadeur, le taux et
    le plafond du jour sont **inscrits sur la commande** et n'en changent plus ; seulement les produits
    vendus sur le site (pas les vendeurs en contact direct) ; les aperçus des liens (robots), les
    propres visites de l'ambassadeur, la vendeuse sur ses produits et l'équipe ne comptent pas ;
  - **quand c'est gagné** : **un gain par colis** (index unique), rien avant la livraison avec le
    code, confirmé 7 jours après s'il est gardé : alors une **facture d'achat de l'ambassadeur** (une
    seule fois par gain, index unique sur les pièces) ; un retour demandé avant la confirmation la
    retient pour l'équipe ; un retour fait après (garantie, 30 jours) donne un **avoir** retiré du
    versement suivant. Les montants de l'espace se relisent dans ces pièces, jamais dans un compteur ;
  - **le versement** : avec les reversements du shop, **chaque lundi**, dès 2 000 F, sur son Mobile
    Money ; jamais un solde négatif (il attend les gains suivants), ni à un compte en pause ou à
    vérifier, ni sur un nouveau numéro avant 48 h (le numéro du compte est prévenu sur WhatsApp), ni
    au-delà de 50 000 F gagnés sans pièce d'identité vue (une fois) ;
  - **contre la fraude** : jamais sur ses propres achats (son numéro, son Mobile Money, son contact,
    sa boutique) ; **5 commandes par mois** d'un même client pour un même ambassadeur (le contact ou
    le numéro) ; **pause automatique** au-delà de 30 % de colis refusés ou retournés sur ses 10
    derniers colis au moins (ses liens marchent, rien ne se gagne, les gains dus sont gardés) ;
    **un Mobile Money par personne** (partagé : « À vérifier ») ; les comptes demandés dont le numéro
    n'est jamais vérifié sont effacés après 7 jours. L'équipe ouvre, met en pause ou ferme dans « À
    vérifier » (colonne Ambassadeurs) ;
  - **ce que voit le client** : « Grâce te recommande ce produit » (le prénom seulement), écrit par le
    script de la fiche à partir d'un petit cookie du lien : la page reste la même pour tous, gardée en
    mémoire pour les foules ;
  - **les vendeurs** : tous leurs produits vendus sur OCD Live sont à partager, sans rien payer et sans
    refus possible ; ils voient « Vendu grâce aux ambassadeurs » dans « Mes chiffres », jamais qui ;
  - **les messages** : un WhatsApp par jour au plus (le soir, les colis livrés depuis le dernier),
    le versement fait, le numéro de versement changé ; jamais un message par colis ;
  - **les impôts** : des commissions versées à des particuliers, à voir avec le comptable avant
    d'ouvrir (retenue ou non, relevé de l'année) ;
  - **dans deux modules** (`ocd_ambassadors`, `ocd_ambassadors_whatsapp`), qui s'appuient sur les
    commandes, les colis et les reversements du shop sans les changer, sauf un point d'accroche du
    détail des reversements (`_ocd_breakdown_bills`).
- **OCD Business** (chantier 12 ; maquette `OcdBusiness` validée le 19 novembre 2026 avec les choix
  recommandés et ses règles de robustesse) :
  - **ce qui reste pour tous** : ce qui fait vendre (la boutique, les produits, un magasin, le retrait
    en magasin, les promos, les lives, les clips, les ambassadeurs, les reversements) ; **la formule
    ajoute** plusieurs magasins et leur stock, l'équipe, les chiffres en détail, les nouveautés chaque
    semaine, et OCD Express (compte ouvert tout de suite, petit ramassage gratuit) ; **pas de commission
    plus basse** ;
  - **le prix** : 10 000 F pour 1 mois, 27 000 F pour 3 mois, 100 000 F pour 12 mois (réglables, dans
    la devise de chaque pays comme le pass de l'annuaire, sans taxe ajoutée : le prix des réglages est le
    prix payé) ; **payé d'avance, jamais prélevé** ;
  - **des périodes, pas une date** : une période par paiement (index unique sur la ligne de commande),
    avec la durée et le prix de la commande même si les réglages changent après ; elle commence le
    lendemain de la dernière, ou aujourd'hui : aucun jour perdu. « Jusqu'au » se calcule, ne se tape
    jamais ; l'équipe offre des jours avec un motif (1 à 400) ; le vendeur est verrouillé le temps du
    calcul ; une facture par paiement ;
  - **le Mobile Money vérifié par l'équipe est accepté** (choix 1) : « J'ai payé » garde les fonctions
    **3 jours** après la fin, le temps de la vérification ; vérifié, les jours partent de la fin de la
    formule (jamais de jours perdus ni gagnés par l'attente) ; refusé, la grâce s'arrête ;
  - **un remboursement** (la commande annulée) reprend les jours pas encore passés, jamais en arrière ;
    les périodes suivantes se rapprochent ;
  - **à la fin, rien n'est effacé** : les magasins au-delà du premier sont masqués aux clients (les
    commandes partent toujours de leur stock), mais **le magasin de départ des colis reste visible** ;
    l'équipe est en pause ; les chiffres en détail se cachent ; les nouveautés partent une fois par mois ;
  - **les rappels** : 7 jours avant et la veille, à l'heure du vendeur, une fois par date de fin, jamais
    après un renouvellement ; la fin est dite une fois ;
  - **le lancement** : le jour choisi par l'équipe, les vendeurs qui utilisent les fonctions (au moins
    deux magasins vérifiés ou une équipe) reçoivent une fois **2 mois offerts**, puis les fonctions
    offertes à tous s'arrêtent ; **limites** : 5 magasins et 5 personnes, réglables ;
  - **la page publique** `/business` pour les commerçants sans lives : ouvrir sa boutique en écrivant à
    OCD Live sur WhatsApp, puis la formule depuis son espace ;
  - **dans deux modules** (`ocd_business`, `ocd_business_whatsapp`) : l'interrupteur du chantier 17
    (`ocd_business_until`) devient le résultat des périodes ; `ocd_live_shop` et `ocd_express` lisent
    la formule propre du vendeur (`_ocd_business_formula`), sans l'offre à tous, pour OCD Express.

## WhatsApp

- **Un seul accord** : la case d'OCD Live (réservation, espace vendeur, commande du shop) et l'accord de
  WhatsApp (changé aussi par STOP et START) restent identiques. Un refus n'est jamais contourné.
- **Les messages demandés par le contact partent toujours** (code de connexion, lien, ticket, alerte
  « Préviens-moi ») : la demande vaut accord pour ce message.
- Les colis d'OCD ont leurs propres messages : le « commande expédiée » du shop n'est pas envoyé pour eux,
  et la demande de note part une fois par commande, après son dernier colis.
- **Le vendeur apprend la décision de l'équipe** sur un produit ou un magasin (accepté, ou refusé avec son
  motif), avec un bouton vers « Mes produits » ou « Mes magasins » : un seul message par vendeur quand
  l'équipe en vérifie plusieurs à la fois ; rien pour un domicile, montré sans vérification ; interrupteur
  dans les Automatisations.
- **Rien qui ressemble à une connexion dans un modèle Utilitaire** : Meta le refuse comme
  `INCORRECT_CATEGORY` (il y voit un message d'*Authentification*, dont le seul format est un code à usage
  unique). Ni « code » (même nommé sans le donner), ni « mot de passe », ni « identifiant », ni « lien
  personnel », ni « gardez-le pour vous », ni numéro « que l'équipe vous demandera ». Les messages disent ce
  qui s'est passé, comme ceux des réservations : le colis est en route (le code est sur la page de suivi,
  ouverte par le bouton), le ticket est joint avec sa référence, l'espace vendeur demandé, l'inscription à
  terminer. Odoo refuse de soumettre un texte Utilitaire qui contient ces mots.
- **Connexion jamais bloquée par Meta** : tant que le modèle du lien personnel est refusé, en attente ou en
  pause, la page de connexion (vendeurs et livreurs) demande un code, envoyé par le modèle
  d'*Authentification* (le seul que Meta accepte pour une connexion) ; le lien revient dès que Meta
  l'approuve. La page répond pareil pour tous les numéros.
- **Messages en français et en anglais** : chaque modèle existe dans les deux langues (même nom chez Meta).
  Un contact dont la langue est l'anglais reçoit la version anglaise une fois approuvée par Meta, la
  version française en attendant.
- **Textes des modèles** : chargés à l'installation, puis à l'équipe. Une nouvelle version d'un module ne
  change que les textes restés tels que le module les avait écrits, et jamais celui d'un modèle approuvé par
  Meta (c'est le texte que Meta envoie). Odoo refuse de soumettre un texte que Meta refuserait (variable au
  début ou à la fin, deux variables sans mots entre elles).

## Back-office

- **Paramètres** à sections, lus par les automatisations ; les responsables d'OCD Live les changent sans
  être administrateurs d'Odoo ; seuls les réglages de la page sont écrits, après leurs contrôles.
- **Automatisations** : règles que l'équipe met en pause, tâches à heure fixe, et règles du code (argent,
  preuves de livraison) **jamais coupées** ; les tâches techniques sont toujours actives.
- **Aucune mention d'Odoo** pour l'équipe, les vendeurs et les clients (module `ocd_debranding`, avec
  `disable_odoo_online` de l'OCA).
- **Les adresses du back-office gardent `/odoo/`** : ce préfixe est écrit en dur dans le cœur d'Odoo
  (routeur du navigateur, liens des menus et des fiches, routes du serveur, liens des e-mails) ; le
  changer demanderait de remplacer des fichiers du cœur à chaque mise à jour. Les vendeurs et les clients
  ne le voient jamais (le site utilise `/ocd`, `/lives`, `/shop`). Pour une adresse à la marque : un
  sous-domaine pour l'équipe (ex. `equipe.example.com`).


## Grand public

- **Pages publiques gardées en mémoire quelques secondes** (réglable : Paramètres › Vitesse du site) :
  le fil des lives, la page d'un live, les boutiques, le shop et les produits sont construits une fois,
  puis redonnés aux visiteurs suivants (de 10 à 60 secondes selon la page). Chaque serveur les garde
  lui-même : aucun logiciel de plus à installer et à surveiller. Un cache devant Odoo (nginx, CDN) ne
  saurait pas remettre le jeton des formulaires de chaque visiteur ni reconnaître un vendeur ou un client
  avec un panier : les pages restent construites par Odoo, et seulement pour les visiteurs qui n'ont
  encore rien à eux sur le site. Un changement (produit, prix, live vérifié) se voit au plus après ces
  secondes ; les vendeurs, les livreurs et l'équipe voient toujours leurs pages à jour.
- **Les photos, les vidéos et les fichiers du site partent d'un CDN** (réglable : son adresse), sur son
  propre domaine : ils sont gardés un an par les téléphones et par le CDN grâce à leur version dans
  l'adresse, et le serveur ne fait plus que les pages.
- **Une page cachée ne pose plus de questions** (nouveaux lives, produit à l'écran, attente d'un
  paiement) : elle les reprend dès qu'on revient dessus.
- **Visites des boutiques pendant un live écrites toutes les 5 secondes** par chaque serveur : en pointe,
  les visiteurs ne s'attendent plus les uns les autres ; le compteur de la régie a quelques secondes de
  retard.
- **La preuve se fait par la mesure** : un modèle de rapport ([`RAPPORT_DE_CHARGE.md`](RAPPORT_DE_CHARGE.md))
  et un outil (`tools/charge/charge.py`), à refaire sur les vrais serveurs avant l'ouverture au grand
  public.
