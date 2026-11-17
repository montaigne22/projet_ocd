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
- **Deux thèmes** : celui du site (vendeurs, clients) et celui du back-office (équipe). Ils lisent les
  mêmes couleurs et polices, dans un seul fichier : `ocd_live/static/src/scss/ocd_tokens.scss`.
- **Données de démonstration** dans un module à part, `ocd_live_demo` : le désinstaller retire tout.
  La démo est **tenue à jour** par une action planifiée : une présentation montre toujours des lives
  en cours, la semaine du studio, les replays récents et la journée de la boutique de Douala (colis,
  caisse des livreurs, reversements, conversations WhatsApp), quel que soit le jour. Ses vendeurs ont des
  histoires cohérentes (ville, produits, heures, plateforme ; studio pour Lomé, à distance ailleurs) et
  **ne reçoivent jamais de WhatsApp** (numéros d'exemple, `ocd_live_demo_whatsapp`). Elle ajoute deux
  fenêtres de vérification (midi, après-midi) pour avoir des lives de 8 h à 21 h. Scénario : `DEMO.md`.
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
  Odoo pour le pays, la devise et le montant. Aujourd'hui Campay au Cameroun ; au Togo, Mobile Money
  vérifié par l'équipe en attendant un second connecteur.
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
- **Frais de livraison : un prix par colis** (un colis par vendeur), selon la ville d'où part le colis et
  le quartier du client ; le client paie la somme des colis.
- **Le vendeur qui livre fixe ses prix**, dans les bornes fixées par l'équipe (réglable) ; OCD garde une
  part réglable de ses livraisons (**0 %** au départ). Les livraisons des livreurs OCD et des agences
  reviennent à OCD.
- **Vers une autre ville ou un autre pays : seulement par un tarif « agence »** prévu par l'équipe, sans
  paiement à la porte. Une adresse qu'aucun tarif ne couvre est refusée avant le paiement.

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
