# Progression du projet OCD Live

Ce fichier est mis à jour à chaque évolution. Le plus récent est en haut.

## Où en est le projet (12 novembre 2026)

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
| Annuaire des lives (pass, envoi du lien, vérification par créneau, statut) | ✅ fait, testé |
| Espace vendeur sans mot de passe (lien ou code WhatsApp) | ✅ fait, testé |
| « Moi » pour les comptes Odoo connectés : vendeur, équipe (« Voir son espace »), client | ✅ fait, testé |
| Livreurs : leur numéro, puis lien ou code sur WhatsApp, comme les vendeurs ; déconnexion | ✅ fait, testé |
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
| Démo de présentation tenue à jour : 15 vendeurs dans 8 pays, lives en cours, semaine du studio, replays, boutique de Douala heure par heure (colis, caisse, reversements, WhatsApp), scénario ([`DEMO.md`](DEMO.md)) ; aucun WhatsApp vers ses contacts | ✅ fait, testé |
| Traductions françaises de tous les modules, descriptions longues comprises | ✅ faites (à compléter à chaque nouvel écran) |

Derniers tests lancés (12 novembre 2026, base neuve, tous les modules OCD sauf la démo, avec
`ocd_debranding`, plus les tests de `whatsapp_cloud` et `whatsapp_cloud_sale`) : **354 tests, un seul
échec, connu** (« commande confirmée puis expédiée » de `whatsapp_cloud_sale` : OCD remplace ce message par
ceux des colis). Nouveaux tests des cartes, des plateformes, des comptes et des lives à distance : 24 sans échec. Sur
une base neuve avec la démo, 17 tests sans échec : la démo remplit les écrans et se
tient à jour (semaine du studio, annuaire fenêtre par fenêtre, fil de chaque pays, paiement à vérifier,
journée de la boutique heure par heure, le lendemain, rien ne s'empile), prend la vidéo et le compte des
paramètres, aucun WhatsApp ne part vers ses contacts, puis elle se désinstalle sans rien laisser.

## Reste à faire, par priorité

1. **Tarifs à saisir par l'équipe avant l'ouverture**, pas à pas dans [`LIVRAISONS.md`](LIVRAISONS.md)
   (OCD Live › Livraisons › Tarifs de livraison) :
   livreurs OCD par ville, agences vers les autres villes et pays, bornes des prix des vendeurs, part
   d'OCD sur les livraisons des vendeurs, ville du stock. Les modes de livraison sans prix ont donné des
   tarifs archivés : les compléter puis les activer. Sans tarif, le shop refuse l'adresse (jamais de
   livraison à un prix inconnu).
2. **WhatsApp chez Meta** (équipe) : connecter le numéro d'OCD Live (WhatsApp › Comptes), puis soumettre
   (le code de connexion est un modèle *Authentification* : Meta en écrit le texte, Odoo envoie le code)
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
- Le module `disable_odoo_online` de l'OCA est dans `marketplace/oca_server_brand/` : ce dossier doit être
  dans le chemin des modules, `ocd_debranding` en dépend.
- La confirmation d'une commande envoie un PDF : le serveur a besoin du moteur PDF d'Odoo
  (`wkhtmltopdf`), sinon la commande reste « en attente du paiement ».
- Odoo publie au départ sa « Livraison standard » (gratuite, partout) : l'équipe ne publie que les
  modes de livraison d'OCD Live, sinon elle passe avant elles.

## Journal

### 12 novembre 2026 — page produit : « Ajouter au panier » et « Écrire sur WhatsApp » réparés ; ffmpeg par pip
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

### 12 novembre 2026 — cartes du fil claires, médias des vendeurs, lives à distance sur les comptes d'OCD
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

### 12 novembre 2026 — la boutique de Douala tenue à jour, textes des modules après une mise à jour
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

### 12 novembre 2026 — démo de présentation : 8 pays, tenue à jour
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

### 11 novembre 2026 — photos des produits, replay lu dans la page, retour en stock
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

### 11 novembre 2026 — tous les pays d'Afrique et du monde, paiement par carte, fil des lives
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

### 11 novembre 2026 — ticket en PDF, image pour annoncer son live, heures de chacun
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

### 11 novembre 2026 — trois modèles refusés par Meta, navigation sans rechargement
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

### 11 novembre 2026 — le téléphone retient le vendeur et le livreur ; messages en français seulement
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

### 11 novembre 2026 — modèles WhatsApp encore refusés : textes corrigés jusque dans les bases
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

### 11 novembre 2026 — l'appli installée porte le logo d'OCD Live
- « Installer l'appli » du navigateur montrait l'icône et les couleurs d'Odoo (le module de l'OCA
  `web_pwa_customize` n'existe pas encore pour Odoo 20). `ocd_debranding` donne maintenant au manifeste de
  l'appli les icônes d'OCD Live (192 et 512 px, marge pour les téléphones qui découpent l'icône en rond),
  le fond blanc et la couleur encre ; l'icône de l'iPhone aussi. Icônes redessinées nettes depuis le logo.
- L'icône des onglets n'a plus de coins noirs (logo rond sur fond transparent) ; le site existant la
  reçoit à la mise à jour, sauf si l'équipe avait mis la sienne. `ocd_debranding` 20.0.1.1.0.
- Une appli déjà installée garde l'ancienne icône : la désinstaller puis la réinstaller.

### 11 novembre 2026 — modèles WhatsApp acceptés par Meta
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

### 11 novembre 2026 — les livreurs entrent avec leur numéro
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

### 11 novembre 2026 — 404 sur « Moi » en administrateur, pages restées en anglais
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

### 11 novembre 2026 — « Moi » quand on est déjà connecté à Odoo
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
