# Développer et tester OCD Live

## Environnement

- **Odoo 20 Community** (Python 3.13, PostgreSQL 16).
- Chemin des modules (`addons_path`) : les modules d'Odoo, **ce dépôt** (qui contient aussi
  `whatsapp_cloud`, `whatsapp_cloud_sale`, `payment_campay`, `payment_cinetpay` et `delivery_cameroon`), et son dossier
  `marketplace/oca_server_brand` (modules de l'OCA, dont `disable_odoo_online`, nécessaire à
  `ocd_debranding`).
- Exemple de `odoo.conf` :

```ini
[options]
addons_path = /opt/odoo20/src/addons,/opt/odoo20/src/odoo/addons,/chemin/projet_ocd/marketplace/oca_server_brand,/chemin/projet_ocd
db_host = localhost
db_port = 5432
data_dir = /opt/odoo20/data
```

- **Tout installer d'un coup** (Linux, en root) : `bash tools/setup_odoo20.sh` met Odoo 20 dans
  `/opt/odoo20` (la source de la branche 20.0, son environnement Python avec les bibliothèques du dépôt,
  `odoo.conf` ci-dessus), démarre PostgreSQL avec un rôle `root`, installe `wkhtmltopdf` et `ffmpeg`. Une
  étape déjà faite est sautée : il se relance sans risque. C'est le script d'installation de
  l'environnement cloud « projet_ocd » des sessions de Claude Code (claude.ai, Settings › Environments) :
  changer les deux ensemble. Ensuite :
  `cd /opt/odoo20 && . venv/bin/activate && python src/odoo-bin -c odoo.conf -d <base> ...`.
- Moteur PDF d'Odoo (`wkhtmltopdf`, ex. `apt-get install -y wkhtmltopdf`) : la confirmation d'une
  commande du shop envoie un PDF, le ticket du live est un PDF. La version « avec Qt patché » est la
  meilleure ; celle d'Ubuntu (Qt non patché) marche aussi, le ticket corrige son échelle.
- **ffmpeg** : la vidéo courte d'un vendeur, filmée sur son téléphone (MP4, MOV, 3GP, WebM…), est rendue
  lisible par tous les téléphones (MP4 720 px, 30 s au plus) et son affiche en est tirée. Deux façons de
  l'avoir :
  - avec pip, sans accès administrateur : `imageio-ffmpeg` est dans `requirements.txt`
    (`pip install -r requirements.txt` le pose dans l'environnement d'Odoo, avec son propre ffmpeg) ;
  - ou celui du système : `apt-get install -y ffmpeg` (pris en premier quand il est là).

  Sans ffmpeg, seules les vidéos MP4 et WebM de 15 Mo au plus sont acceptées, telles quelles.

  La vidéo envoyée (200 Mo au plus) est préparée **en arrière-plan** par l'action planifiée « OCD Live :
  préparer les vidéos des cartes », lancée aussitôt l'envoi : la page répond tout de suite, dit « en
  préparation » et se met à jour seule ; une vidéo refusée dit pourquoi dans l'espace du vendeur. ffmpeg
  tourne sans les limites des workers d'Odoo (`limit_time_cpu`, `limit_memory_hard`, qui le couperaient),
  avec 2 threads et 100 s au plus.
- **Le proxy devant Odoo** (nginx…) doit laisser passer les vidéos des téléphones, par ex. pour nginx :
  `client_max_body_size 220m;`. Sinon il les refuse avant Odoo (« 413 ») ; la page le dit au vendeur
  (« Le serveur refuse un fichier aussi lourd »).
- Bibliothèques Python du dépôt (`requirements.txt`) : `pip install -r requirements.txt` dans
  l'environnement d'Odoo. `phonenumbers` vérifie les numéros de tous les pays (règles de Google) ; sans
  elle, une règle simple garde les formulaires utilisables (indicatif d'Odoo, 6 à 14 chiffres).
- Paiement par carte : le module `payment_stripe` d'Odoo est installé avec `ocd_live` ; l'équipe saisit
  les clés de son compte Stripe (Facturation › Configuration › Moyens de paiement › Stripe), puis le
  publie. Sans moyen de paiement pour un pays, la page de paiement propose l'aide de l'équipe.

## Lancer une base de démonstration

En deux temps : les modules d'abord (Odoo met en place la comptabilité), puis la démo. Entre les deux,
régler la société pendant qu'aucune écriture n'existe encore (pays, devise en franc CFA).

```bash
odoo -c odoo.conf -d ocd_demo -i ocd_live,ocd_live_shop,ocd_live_whatsapp,ocd_live_shop_whatsapp,ocd_live_recruitment,ocd_delivery_togo,ocd_debranding,ocd_vote,ocd_vote_whatsapp,ocd_tickets,ocd_tickets_whatsapp,ocd_soirees,ocd_soirees_whatsapp,ocd_clips,ocd_clips_whatsapp,ocd_express,ocd_express_whatsapp --load-language=fr_FR --stop-after-init
```

Puis, dans Odoo : la société (pays, devise **XOF** ou **XAF**, téléphone et e-mail : ils s'affichent
dans le pied de page du site) et l'utilisateur en français (Préférences). Le site est déjà en français,
avec l'accueil d'OCD Live sur `/` (fait par `ocd_live` à l'installation). Enfin :

```bash
odoo -c odoo.conf -d ocd_demo -i ocd_live_demo --stop-after-init
odoo -c odoo.conf -d ocd_demo
```

La démo montre OCD Live **en service le jour même** : 15 vendeurs dans 8 pays (Togo, Cameroun, Côte
d'Ivoire, Sénégal, Bénin, Ghana, Nigeria, diaspora à Paris), chacun avec ses produits, son lien de live et
ses heures ; les lives de l'annuaire dans la fenêtre du moment (la démo ajoute les fenêtres « Midi » et
« Après-midi » : des lives de 8 h à 21 h), la semaine du studio (samedi complet, liste d'attente, un live
sans animatrice), les replays de la semaine passée avec les produits montrés, un paiement Mobile Money à
vérifier ; la boutique de Douala heure par heure (six commandes par jour, colis à chaque étape, un colis
en retard, un client absent, espèces remises chaque soir, reversements préparés et payés chaque jour si la
comptabilité existe, conversations WhatsApp du jour ; robe en 2 couleurs et 4 tailles, « Plus que 3 »,
tailles épuisées ; magasins de Brenda à Akwa et Bonapriso avec son équipe, retrait au magasin, point relais,
pièce à essayer, ventes pendant les lives, avis, abonnés, promo et signalement de la semaine, 90 jours de
chiffres) ; avec `ocd_express` (installé avant ou après la démo), une expéditrice d'OCD Express et
ses colis de chaque jour ouvré (deux passages du livreur, un retour rendu contre le code, un souci
signalé, un colis au-dessus de sa limite à vérifier, son argent versé chaque jour ouvré) et une demande
d'ouverture de compte ; avec les autres modules (installés avant ou après elle) : les formules OCD
Business des vendeurs, une ambassadrice et ses gains versés le lundi, « Vendredi wax » chaque vendredi,
les clips des replays d'Awa, un concours OCD Vote et ses votes, un concert chaque samedi et ses billets
(`ocd_live_demo/modules_life.py`). Une action planifiée (toutes les 15 minutes) la tient sur les jours autour
d'aujourd'hui : rien à refaire avant une présentation. Une vraie vidéo pour ses replays et un vrai compte pour ses lives se
règlent dans OCD Live › Configuration › Paramètres › Démo. Le scénario de présentation, vendeur par
vendeur et heure par heure, est dans [`DEMO.md`](DEMO.md).

Elle publie le paiement à la livraison, active le Mobile Money vérifié par l'équipe (numéros d'exemple)
et ouvre les réservations sans date d'ouverture. Aucun message WhatsApp ne part vers ses contacts, dont
les numéros sont des exemples : `ocd_live_demo_whatsapp` s'installe avec elle quand WhatsApp est là.
Le stock est posé sans mouvement de stock et les colis livrés ne valident pas le transfert : la
désinstallation de `ocd_live_demo` retire tout (contacts, produits, photos, stocks, lives, commandes,
paiements, factures, reversements, tarifs, fenêtres, magasins, équipe, avis, abonnés, chiffres) et remet
les moyens de paiement, la date d'ouverture et les réglages de la boutique qu'elle avait activés
(retrait au magasin, pièces à essayer, points relais) comme avant. Ce qui ne se fait qu'une fois
(un magasin, l'équipe, les abonnés…) est noté `setup:…` dans `ocd.live.demo.event` et jamais purgé :
un magasin retiré par l'équipe pendant une présentation ne revient pas.

Installée **en une fois** avec les modules (ce que font les tests), la démo charge elle-même le plan
comptable qu'Odoo n'aurait chargé qu'à la fin de l'installation : les colis des jours passés ont leurs
factures et leurs reversements.

Le site : `/ocd` (réserver), `/lives` (annuaire), `/shop`. Le back-office : application **OCD Live**.

## Mettre à jour un serveur déjà installé

Après un `git pull` du dépôt : redémarrer Odoo, puis mettre à jour les modules OCD (Applications ›
module › Mettre à jour, ou en ligne de commande) :

```bash
odoo -c odoo.conf -d <base> -u whatsapp_cloud,whatsapp_cloud_sale,ocd_live,ocd_live_shop,ocd_live_whatsapp,ocd_live_shop_whatsapp,ocd_live_recruitment,ocd_delivery_togo,ocd_debranding,ocd_vote,ocd_vote_whatsapp,ocd_tickets,ocd_tickets_whatsapp,ocd_soirees,ocd_soirees_whatsapp,ocd_clips,ocd_clips_whatsapp,ocd_express,ocd_express_whatsapp --stop-after-init
```

Avec les appels WhatsApp, ajouter `whatsapp_cloud_call`.

**À chaque récupération du code, mettre à jour les modules.** Sans cela, le code appelle des pages qui
n'existent pas encore dans la base, et le site répond « Page introuvable » (404) ; c'est arrivé sur « Moi »
avec la page de l'équipe. La version d'un module augmente quand ses vues ou ses données changent, pour les
outils qui ne mettent à jour qu'un module dont la version a changé.

Avec la démo, ajouter `ocd_live_demo` à la liste : sa mise à jour met le nouveau scénario en place et
installe `ocd_live_demo_whatsapp` (voir [`DEMO.md`](DEMO.md)). Avec CamPay, ajouter `payment_campay`.
`ocd_live` installe lui-même `payment_cinetpay` (dans ce dépôt) et `payment_flutterwave` (module d'Odoo).

Les changements à faire une seule fois sur une base existante sont dans `migrations/` de chaque module
(ex. `ocd_live` 20.0.1.1.0 : accueil d'OCD Live sur `/`, site en français, logo, menus traduits).

## Paiement dans l'UEMOA : ouvrir CinetPay et Flutterwave

Les deux fournisseurs sont installés avec `ocd_live`, ni publiés ni en production : rien ne change pour
les clients tant que l'équipe ne les ouvre pas (Site Web › Configuration › Fournisseurs de paiement).

1. **CinetPay** : dans le tableau de bord de CinetPay, « Intégration », copier l'identifiant du site, la
   clé d'API et la clé secrète dans la fiche « CinetPay ». L'adresse des notifications est donnée avec
   chaque paiement (`https://<domaine>/payment/cinetpay/webhook`) : rien à saisir chez CinetPay. Le
   serveur doit joindre `api-checkout.cinetpay.com`.
2. **Flutterwave** : dans le tableau de bord de Flutterwave, « Settings › API Keys », copier la clé
   publique et la clé secrète, et la clé de hachage du webhook (Webhook secret hash) ; l'adresse du
   webhook chez Flutterwave est `https://<domaine>/payment/flutterwave/webhook`. Activer le moyen
   « Mobile money » de la fiche (onglet Configuration) : au départ, seule la carte l'est.
3. Publier le fournisseur, faire un vrai paiement de 100 F en mode test, puis cocher « Live ». Les
   Paramètres d'OCD Live (Paiements) disent pour chacun : ses pays, ses devises, les clés manquantes, le
   mode test. En production, le Mobile Money vérifié par l'équipe disparaît de lui-même du formulaire dans
   les pays et les devises qu'ils prennent.

Un nouveau module (ex. `theme_ocd`) n'apparaît qu'après **Applications › Mettre à jour la liste des
applications** (mode développeur). Le thème se choisit ensuite dans Site Web › Configuration ›
Paramètres › Choisir un thème › « OCD Live » : Odoo l'installe et l'applique au site.

## Grand public : tenir les foules d'un live

Un live partagé sur TikTok envoie des milliers de personnes sur les mêmes pages en quelques minutes. Le
code les tient de trois façons ; les mesures et le modèle de rapport pour les vrais serveurs sont dans
[`RAPPORT_DE_CHARGE.md`](RAPPORT_DE_CHARGE.md).

**Pages publiques gardées en mémoire** (`ocd_live/page_cache.py`, appelé par `ir.http._dispatch`). Pour
un visiteur qui n'a encore rien à lui sur le site, une page publique est la même pour tous ceux de même
langue, même pays et même fuseau : chaque worker garde la page qu'il a construite quelques secondes et la
redonne aux visiteurs suivants. Une route le demande avec des options de `@http.route` :

- `ocd_cache=20` : combien de secondes ;
- `ocd_cache_params=("pays", "page")` : les paramètres de l'adresse (de l'appel, pour une route jsonrpc)
  qui font une autre page. Une adresse avec un autre paramètre est construite pour son visiteur
  (`?noted=1` après un formulaire) ; ceux des réseaux et des publicités (`fbclid`, `utm_…`) ne changent
  pas la page ;
- `ocd_cache_hit="_count_live_visit"` : une méthode du contrôleur appelée quand la page vient de la
  mémoire, pour ce qui doit se faire à chaque visite (compter la visite du live).

| Route | Gardée |
|---|---|
| `/ocd`, `/reserver` | 30 s |
| `/lives` (`pays`, `page`), `/lives/<pays>` (`categorie`), `/lives/flux` (`offset`, `pays`) | 20 s |
| `/lives/<pays>/<live>` | 15 s |
| `/shop` (`categorie`) | 60 s |
| page d'un produit (`v`) | 30 s |
| `/ocd/boutique/<vendeur>` (la visite du live est comptée) | 15 s |
| `/ocd/boutique/<vendeur>/live` (produit à l'écran) | 10 s |
| `/ocd/boutique/<vendeur>/replay` (`live`, `t`) | 60 s |

Ce qui est à un seul visiteur n'est jamais donné à un autre :

- seulement pour un visiteur pas connecté, sans vendeur ni livreur sur ce navigateur (cookies de
  `page_cache.PERSONAL_COOKIES`), dont la session n'a que les clés de `page_cache.SESSION_KEYS` : un
  panier, une commande, un vendeur ouvert… et ses pages sont construites pour lui. **Une nouvelle clé de
  session qui change une page publique reste hors de `SESSION_KEYS`** ;
- la page est rangée selon l'adresse, la langue, le pays (GeoIP : devise, taxes, pays d'abord), le fuseau
  du téléphone (cookie `tz`) et la liste de prix choisie dans le shop ;
- le jeton des formulaires (CSRF) est remis pour chaque visiteur ;
- une page pendant laquelle le visiteur reçoit un cookie ou une clé de session à lui n'est pas gardée,
  ni une page qui montre un paramètre des réseaux (les boutons de langue gardent les paramètres).

Chaque worker a sa mémoire (500 pages au plus, les plus anciennes partent). L'en-tête `X-OCD-Cache` dit
d'où vient une page : `hit` (mémoire), `miss` (construite et gardée), `pass` (construite pour ce
visiteur). Un changement (nouveau produit, prix, live vérifié) se voit au plus après la durée de la page ;
les vendeurs, les livreurs et l'équipe voient toujours leurs pages à jour. La case « Pages publiques
gardées en mémoire » (Paramètres › Vitesse du site, champ `ocd_page_cache` du site) coupe tout, aussitôt.
Pendant les tests des modules, la mémoire est coupée : un test verrait les pages du précédent
(`page_cache.IN_TESTS` pour la tester, voir `test_page_cache.py`).

**Appels répétés.** Les questions que les pages posent seules s'arrêtent quand la page est cachée (autre
appli, autre onglet) et repartent à son retour : nouveaux lives du fil (chaque minute), produit à l'écran
de la boutique (toutes les 20 s), attente d'un paiement ou d'un lien vérifié (toutes les 5 s).
`/lives/nouveaux` relit l'heure des lives du moment au plus toutes les 10 s par worker ; le produit à
l'écran et les cartes suivantes du fil viennent de la mémoire.

**Médias servis à part.** Les photos et les vidéos des cartes (`/lives/image|carte|video`, avec `?v=`) et
les photos des produits des cartes (`/web/image/…?unique=`) portent leur version dans l'adresse : les
téléphones et le CDN les gardent un an (`Cache-Control: public, max-age=31536000, immutable`), un jour sans
version. Les fichiers, les photos et les vidéos partent sans cookie (`ir.http._post_dispatch`) ; demandés
sans session (par le CDN), ils sont `public`. Avec une adresse de CDN (Paramètres › Vitesse du site),
Odoo écrit vers le CDN les liens des fichiers du site (`/web/assets`), des images et des médias des
cartes (filtres du site, ceux des cartes ajoutés) ; les sources et les affiches des vidéos des cartes
passent par `website._ocd_cdn_url`. Les médias d'un vendeur pas encore validé restent privés.
Demandés sans session, ils portent aussi `Access-Control-Allow-Origin: *` : les navigateurs ne prennent
les polices des icônes sur l'adresse du CDN, pour une page du site, qu'avec cet en-tête.

**Visites des boutiques pendant un live** (régie) : chaque worker les compte et les écrit ensemble toutes
les 5 secondes, dans une transaction à part qui attend les autres au lieu d'échouer (READ COMMITTED).
Avant, chaque nouvelle visite écrivait la ligne du live : en pointe, les visiteurs s'attendaient et des
pages étaient refaites. Les visites d'un worker arrêté avant d'écrire sont perdues (une indication).

### Mise en production pour le grand public

- `odoo.conf` des serveurs des pages :

  ```ini
  db_name = ocd
  list_db = False
  proxy_mode = True
  workers = 9
  max_cron_threads = 0
  limit_time_real = 120
  ```

  `db_name` sans `dbfilter` : Odoo ne demande plus la liste des bases pour chaque nouveau visiteur
  (deux fois plus de nouveaux visiteurs par seconde, voir le rapport). `workers` : deux par cœur plus un
  (ici 4 cœurs). Les actions planifiées tournent sur un serveur (ou un processus) à part, avec
  `max_cron_threads = 2`.
- **Plusieurs serveurs d'Odoo** derrière un répartiteur : ils partagent la base et le dossier `data_dir`
  (pièces jointes et sessions, sur un disque partagé). La mémoire des pages est propre à chaque worker :
  rien à partager.
- **CDN** (Cloudflare, Bunny, CloudFront…) : une adresse à part, `https://cdn.<domaine>`, qui va chercher
  les fichiers sur le site et **respecte ses en-têtes** (`Cache-Control`), puis cette adresse dans
  Paramètres › Vitesse du site. Seuls les fichiers, les photos et les vidéos passent par le CDN, jamais
  les pages. Une adresse à part, parce que les téléphones n'y envoient pas leurs cookies : le CDN
  reçoit les photos telles que tout le monde les voit. Avec **Cloudflare** (domaine géré par
  Cloudflare) :
  1. DNS : `cdn` en CNAME vers `<domaine>`, proxy activé (nuage orange) ; le site lui-même reste comme
     il est ;
  2. SSL/TLS : mode « Full (strict) », et le certificat du serveur couvre aussi `cdn.<domaine>`
     (ex. `certbot --nginx -d <domaine> -d cdn.<domaine>`) ;
  3. Caching › Cache Rules : « Hostname equals cdn.<domaine> » → *Eligible for cache*, Edge TTL
     *Use cache-control header if present, bypass cache if not*, Browser TTL *Respect origin TTL*
     (sans cette règle, Cloudflare ne garde pas les adresses sans extension : `/lives/video/6?v=…`,
     `/web/image/…`) ;
  4. nginx : `server_name <domaine> cdn.<domaine>;` ;
  5. OCD Live › Paramètres › Vitesse du site › Adresse du CDN : `https://cdn.<domaine>`.

  Vérifier : les fichiers des pages commencent par `https://cdn.<domaine>/`, et un fichier de
  `/web/assets/` (adresse copiée du code source d'une page) passe de `MISS` à `HIT` au second appel
  (`curl -sI <adresse> | grep -i cf-cache-status`). Les conditions de Cloudflare réservent la diffusion
  de beaucoup de vidéos à ses offres payantes : à vérifier pour les vidéos des cartes.
- **nginx** devant Odoo : `gzip on;` avec `gzip_types text/css application/javascript application/json
  image/svg+xml; gzip_proxied any;`, et `client_max_body_size 220m;` (vidéos des téléphones).
- Mesurer avant d'ouvrir : [`RAPPORT_DE_CHARGE.md`](RAPPORT_DE_CHARGE.md), outil
  `tools/charge/charge.py`.

## Fichiers sur Cloudflare R2 (module `attachment_s3`)

Module générique (aucune dépendance à OCD Live), utilisable sur tout Odoo 20. Odoo garde ses fichiers
sur le disque comme avant ; chaque fichier est aussi copié sur un bucket S3 et vérifié (taille et MD5),
et un fichier qui manque sur le disque d'un serveur est repris du bucket quand il est lu.

1. `pip install boto3` (dans `requirements.txt`), puis `-i attachment_s3`.
2. Cloudflare › R2 › Créer un bucket (ex. `ocd-live-fichiers`, emplacement automatique). Ne pas le
   rendre public : Odoo sert les fichiers (droits d'accès gardés) et le CDN les garde.
3. R2 › Gérer les jetons d'API › Créer un jeton d'API : « Lecture et écriture d'objets », limité à ce
   bucket. Noter l'ID de la clé d'accès et la clé secrète (montrée une seule fois). L'ID du compte est
   sur la page R2 › Vue d'ensemble.
4. Paramètres › Paramètres généraux › Fichiers sur un stockage S3 : Stockage « Cloudflare R2 », l'ID du
   compte, le bucket, les deux clés ; « Tester la connexion » ; puis activer et enregistrer.
   Les clés peuvent être dans `odoo.conf` plutôt qu'en base (elles l'emportent) :
   `attachment_s3_endpoint`, `attachment_s3_bucket`, `attachment_s3_access_key`,
   `attachment_s3_secret_key`, `attachment_s3_region`, `attachment_s3_prefix`.
5. Les fichiers déjà là partent tout seuls, petit à petit (tâche planifiée toutes les 10 minutes) ; la
   progression est sur la même page (« 12 340 fichiers sur le bucket · 2 100 à envoyer »).
   « Envoyer les fichiers maintenant » les note tous à nouveau (sans danger : un fichier déjà envoyé
   n'est pas renvoyé).
6. « Garder sur le serveur » : tous les fichiers (par défaut, le plus sûr) ou les fichiers lus récemment
   jusqu'à une taille en Go (les autres reviennent du bucket quand on les lit).

Plusieurs serveurs Odoo peuvent partager le même bucket (un dossier par base). Pour quitter le bucket :
« Rapatrier les fichiers sur ce serveur », attendre la fin, puis désactiver. La base de données reste à
sauvegarder à part (elle n'est pas sur le bucket). Code : `attachment_s3/models/attachment_s3_object.py`
(envoi, reprise, nettoyage), `ir_attachment.py` (branchement sur `_file_write`, `_file_read`,
`_to_http_stream`) ; tests avec un bucket en mémoire (`tests/`).

## Clips automatiques (modules `ocd_clips` et `ocd_clips_whatsapp`)

Après un live, l'équipe envoie sa vidéo (bouton « Clips » du live, ou « Envoyer la vidéo du live » dans
la régie) ; chaque produit mis à l'écran dans la régie devient un clip vertical de 30 secondes avec son
lien court. Ce qu'il faut sur le serveur :

- **ffmpeg et ffprobe** (`apt-get install -y ffmpeg`) : ffprobe vérifie la vidéo reçue, ffmpeg fait les
  clips. Le ffmpeg de `imageio-ffmpeg` suffit (la vérification lit alors sa sortie) ; sans ffmpeg, la vidéo
  reçue attend (l'écran et les Paramètres le disent).
- **Le dossier des vidéos des lives** : `<ocd_recordings_path>/<base>` (`ocd_recordings_path` dans
  `odoo.conf`, ex. un disque à part), sinon `<data_dir>/ocd_recordings/<base>`. Ces fichiers (1 à 3 Go par live) restent hors de la base, hors des
  pièces jointes et donc hors des sauvegardes et du bucket S3 : ils ne durent que 7 jours (réglable),
  effacés par la tâche planifiée ; les clips restent. Prévoir la place de quelques lives, plus environ
  1 Go de clips par jour à 20 lives par jour (les clips sont des pièces jointes : avec `attachment_s3`,
  ils vont aussi sur le bucket). Avec plusieurs serveurs, ce dossier doit être partagé (comme `data_dir`).
- **L'envoi** se fait par morceaux de 8 Mo (`/ocd/clips/envoi/<partie>`) : le `client_max_body_size 220m`
  de nginx suffit ; un envoi coupé reprend en choisissant le même fichier, même après avoir fermé la page.
- **La tâche planifiée** « OCD Live : faire les clips des lives » : lancée dès qu'une vidéo arrive, et
  toutes les 10 minutes. Elle vérifie les vidéos reçues, puis fait les clips l'un après l'autre (environ
  10 secondes pour un clip de 30 s en 720 × 1280, ffmpeg en basse priorité avec 2 threads) ; elle tourne
  sur le serveur des tâches planifiées (`max_cron_threads`), jamais pendant une page. Un clip pris par un
  serveur arrêté est repris au bout de 30 minutes ; 3 essais, puis « Pas fait » avec la raison.
- **Les liens courts** `/p/<code>` : l'adresse du site par défaut, ou une adresse plus courte dans
  Paramètres › Clips automatiques (le domaine doit mener au même Odoo). `robots.txt` exclut `/p/` ; les
  aperçus des liens (WhatsApp, TikTok, Facebook) ne comptent pas de visite. Les vidéos et les images des
  clips passent par le CDN quand le site en a un (filtre `^/ocd/clips/` ajouté).
- **WhatsApp** : deux modèles à soumettre à Meta (`ocd_clips_prets` et `ocd_clip_video`, Utilitaire,
  français et anglais). `ocd_clip_video` a une **vidéo en tête** (nouveau type d'en-tête de
  `whatsapp_cloud`) : à la soumission, Meta reçoit en exemple le dernier clip fait (ou la vidéo donnée
  sur le modèle) ; à l'envoi, la vidéo du clip est envoyée à Meta (16 Mo au plus). Le bouton « M'envoyer
  le clip sur WhatsApp » ne s'affiche que quand le modèle peut partir.

Pour essayer à la main : un live confirmé, « Le live commence » dans la régie, des produits mis à
l'écran, puis la vidéo envoyée depuis l'écran « Vidéo du live et clips » (une vidéo de test :
`ffmpeg -f lavfi -i testsrc=size=640x360:rate=10:duration=600 -f lavfi -i sine=duration=600 -shortest live.mp4`).

Code : `ocd_clips/clip_video.py` (le montage, les textes, l'aperçu), `models/ocd_live_recording.py` (les
parties de la vidéo, leur envoi et leur vérification), `models/ocd_live_booking.py` (le découpage d'un
live en clips), `models/ocd_live_clip.py` (la file d'attente, le lien, le texte du partage, les pages),
`models/sale_order.py` (les ventes venues d'un clip), `controllers/` (envoi, médias, lien court, pages
du vendeur), `static/src/screen/` (l'écran de l'équipe).

## OCD Express (modules `ocd_express` et `ocd_express_whatsapp`)

La livraison avec code d'OCD Live pour tous les vendeurs des réseaux (décisions dans
[`DECISIONS.md`](DECISIONS.md), Shop et livraisons). Un colis Express est un colis du shop
(`stock.picking`, `ocd_is_parcel`) **sans commande** : type d'opération « OCD Express » (numéros
`EX-0001`), un produit non stocké « Colis OCD Express », l'expéditeur dans `ocd_express_sender_id`. Le
dispatch, la tournée, le code, le paiement à la porte, les problèmes et la caisse du soir sont ceux du shop.

Mise en route (avant d'inviter les premiers expéditeurs) :

1. **La société** (Paramètres › Sociétés, onglet de la société) : les **villes ouvertes à OCD Express**
   (Douala d'abord).
2. **OCD Live › Livraisons › Tarifs de livraison** : un tarif « livreur OCD » de la ville (il donne le prix,
   1 000 F dans Douala), un tarif « agence » vers les autres villes (payé d'avance par l'expéditeur).
3. **Les livreurs** : leurs quartiers (le livreur du quartier de l'expéditeur fait le passage et livre ses
   colis ; le dispatch peut donner un passage entier à un autre livreur).
4. **OCD Live › Paramètres › OCD Express** : ouvert à (invités, puis tout le monde), prix, plafonds, vagues,
   capacité, délais, **point OCD** (adresse du studio) et **Mobile Money d'OCD** (où un expéditeur envoie ce
   qu'il doit, avec la référence `EXD-<numéro>` de sa page).
5. **WhatsApp** : un numéro à part pour OCD Express (WhatsApp › Comptes : un second compte), choisi dans le
   champ « Compte » des 14 modèles d'OCD Express (7 en français, 7 en anglais), puis « Soumettre à Meta ».
6. **Inviter** : un expéditeur demande sur `/express/demande` ; l'équipe ouvre son compte dans « À
   vérifier » (colonne OCD Express) ou sur sa fiche (onglet OCD Express).

Pour aider un expéditeur (ou présenter la démo) : sa fiche › onglet OCD Express › **Voir son espace**
(`/express/equipe/<id>?signature=…`, signé pour la personne de l'équipe connectée) ouvre ses pages comme
il les voit, jusqu'à « Se déconnecter ».

Les pages : `/express` (prix, trois étapes), `/express/demande`, `/express/connexion` (numéro et code sur
WhatsApp), `/express/envois`, `/express/colis/nouveau`, `/express/colis/<id>` (étiquette avec QR,
`/etiquette` pour l'imprimer), `/express/argent` (et `/express/argent/regler` pour payer ce qu'on doit
avec le formulaire de paiement d'OCD Live) ; le client : `/express/suivi/<id>/<jeton>` ; le livreur : sa
tournée `/ocd/livrer/<jeton>` (le passage chez l'expéditeur, les livraisons, les retours). Un vendeur
d'OCD Live dont le compte Express est ouvert retrouve « Envoyer un colis » dans Mon espace.

L'argent : un colis livré compte pour son expéditeur **une fois l'argent chez OCD** (espèces remises à la
caisse du soir, ou paiement sur le téléphone confirmé par le fournisseur) : une facture d'achat de
l'argent encaissé pour lui (`ocd_express_kind` = `collected`), un avoir de la livraison qu'il paie et de
l'encaissement (`fees`). Les retours, les petits ramassages, un souci donné au client sont des avoirs ;
un colis perdu par OCD et ce que l'expéditeur a payé sont des factures. Les reversements du shop les
rassemblent (même écran) : chaque jour ouvré (lundi à samedi), sans l'argent d'un colis avec un souci
ouvert, ni après un nouveau numéro de versement (48 h), et jamais pour un solde négatif (il attend les
colis suivants). Un vendeur qui est aussi expéditeur est versé chaque jour ouvré.

Le manque de caisse d'un livreur (`ocd_live_shop`) : un écart négatif à la caisse devient une dette du
livreur (fiche du livreur, écran Livreurs et caisse) jusqu'à « Manque réglé » sur la remise.

Code : `ocd_express/models/stock_picking.py` (création, vérifications, plan des vagues, retour, souci,
argent, effacement), `ocd_express_pickup.py` (les passages), `res_company.py` (réglages, vagues,
capacité), `res_partner.py` (l'expéditeur, son solde, ses retours), `ocd_payout.py` (les reversements) ;
`controllers/sender.py`, `tracking.py`, `courier.py` ; dans `ocd_live_shop`, les points d'accroche
`_ocd_cash_remitted`, `_ocd_prepare_domain`, `_ocd_payable_moves`, `_ocd_may_pay`, `_ocd_after_paid`,
`_tour_step_list` (une étape avec son propre gabarit) ; dans `ocd_live`, `_login_pages` (les pages de
connexion de tous les modules réunies).

## Points relais (chantier 10, dans `ocd_live_shop`)

Un point relais est un **lieu** (`ocd.vendor.place`) avec `relay` coché : une boutique partenaire, tenue
par un contact « Tient un point relais » (`ocd_is_relay`), ou le magasin vérifié d'un vendeur (A.6).
Décisions dans [`DECISIONS.md`](DECISIONS.md), Shop et livraisons.

Mise en route :

1. **OCD Live › Livraisons › Tarifs de livraison** : un tarif « **Point relais** » par ville (ville de
   départ et villes servies, 500 F à Douala). Sans lui, les points relais de la ville ne sont pas proposés.
2. **OCD Live › Paramètres › Points relais** : allumer, gain par colis remis (150 F), jours de garde (7) et
   rappel (2 jours avant), places par défaut (25), magasins des vendeurs, pause après (2 colis perdus).
   La section dit combien de points relais sont ouverts, à visiter, et les tarifs « point relais ».
3. **Les points relais** : une boutique demande sur `/points-relais` (elle arrive dans « À vérifier »,
   colonne Points relais : l'équipe la visite, puis l'ouvre) ; ou l'équipe la crée dans OCD Live ›
   Livraisons › **Points relais** (le contact qui la tient, son téléphone et son Mobile Money pour les
   versements du mois, le quartier, les horaires, les places). Un vendeur coche « Mon magasin est un point
   relais » dans « Mes magasins » (magasin vérifié et ouvert au public).
4. **WhatsApp** : soumettre `ocd_colis_point_relais`, `ocd_colis_rappel_relais`,
   `ocd_colis_non_retire_relais`, `ocd_relais_arrivage` et, sur le numéro d'OCD Express,
   `ocd_express_point_relais` (français et anglais).

Le parcours d'un colis : à la livraison, le client choisit un point relais (`ocd_relay_id` sur la commande,
puis sur chaque colis) ; le livreur le prend chez le vendeur, puis « Je pars au point relais » sur sa
tournée (étape « Point relais » de `_tour_step_list`) ; le point relais compte les colis
(`_ocd_relay_receive` : étape `at_relay`, jusqu'au `ocd_relay_deadline`, WhatsApp au client) et les remet
contre le code (`_ocd_relay_hand_over`, ou le QR `OCD-<colis>-<code>` de la page du client), une fois payés
(en ligne ou sur le téléphone du client au comptoir). La tâche « OCD Live : colis aux points relais »
(`_cron_ocd_relay`, toutes les heures) relance et fait repartir les colis pas retirés
(`ocd_relay_back`) jusqu'à « J'ai repris ces colis » du livreur.

L'argent : un colis remis donne une facture d'achat au contact du point relais (`ocd_relay_kind` =
`earning`, produit « Colis remis par un point relais ») ; un colis perdu (« Perdu au point relais » sur le
colis, responsable d'OCD Live) donne un avoir (`loss`) et une activité de remboursement (OCD Express :
l'expéditeur est remboursé comme un colis perdu par OCD). Les reversements du shop les réunissent, chaque
mois pour un partenaire.

Les pages : `/ocd/point-relais/connexion` (numéro et code WhatsApp, ou depuis Mon espace pour un vendeur),
`/ocd/point-relais` (Mon point relais, `/conge`), `/ocd/point-relais/recevoir`, `/ocd/point-relais/remettre`
(`?colis=<id>`) ; `/points-relais` ; le choix au paiement par `/ocd/livraison/tarif` (`relay_mode`,
`relay_id`) et `/ocd/livraison` (`recevoir=relais`, `relais=<id>`) ; la tournée `/ocd/livrer/<jeton>/relais/<id>/partir`
et `/repris` ; Express : `/express/suivi/<id>/<jeton>/relais`.

Code : `ocd_live_shop/models/relay_point.py` (le lieu, le partenaire, la commande, le colis, les tarifs,
les factures), `relay_settings.py` (la section des Paramètres), `controllers/relay_space.py` (Mon point
relais, devenir point relais) ; dans `ocd_express`, `_ocd_express_relay_rate`, `_ocd_express_to_relay` et
les overrides `_ocd_relay_lost_*` ; dans les modules WhatsApp, `_ocd_relay_notify`.

## Ambassadeurs (modules `ocd_ambassadors` et `ocd_ambassadors_whatsapp`)

Chacun partage un produit avec son lien personnel et gagne une part des articles une fois le colis
livré avec son code et gardé (décisions dans [`DECISIONS.md`](DECISIONS.md), Shop et livraisons).

Mise en route :

1. **OCD Live › Paramètres › Ambassadeurs** : le programme (ouvert à tous, sur invitation, fermé), le
   gain (5 %), le plafond par colis (3 000 F), les jours du lien et de la confirmation (7 et 7), le
   versement minimum (2 000 F, le jour de versement du shop), la pièce d'identité (50 000 F), la pause
   (30 % de retours sur 10 colis), les commandes d'un client par mois (5), le nouveau numéro (48 h).
2. **WhatsApp** : soumettre `ocd_ambassadeur_livres`, `ocd_ambassadeur_versement` et
   `ocd_ambassadeur_numero` (français et anglais, Utilitaire) ; la connexion passe par le message
   d'Authentification déjà soumis.
3. **Le comptable** : les gains sont des factures d'achat des ambassadeurs (produit « Gain d'un
   ambassadeur »), les retours des avoirs (« Gain d'un ambassadeur repris ») ; la question d'une
   retenue sur les commissions versées à des particuliers est à poser avant d'ouvrir.
4. Faire connaître `/ambassadeurs` (un ambassadeur se connecte sur `/ambassadeur/connexion`).

Le parcours : `/a/<code>[/<produit>]` garde le lien dans la session du téléphone (clé `ocd_ambassador`,
dans les clés qui laissent les pages en mémoire) et pose le petit cookie `ocd_reco` que lit la fiche
produit ; le panier note l'ambassadeur (`_verify_cart_after_update`) ; à la confirmation,
`sale.order._ocd_ambassador_attribute` inscrit l'ambassadeur, le taux et le plafond, ou pourquoi la
commande ne compte pas, puis écrit un `ocd.ambassador.gain` par colis ; `stock.picking._ocd_deliver` et
`write` (étape `returned` ou `cancelled`) le font avancer ; la tâche « OCD Live : gains des ambassadeurs »
(`_cron_ocd_ambassadors`, toutes les heures) confirme les gains dus (une facture chacun), prévient le
soir les ambassadeurs (une fois par jour) et efface les comptes jamais vérifiés. Les reversements du shop
versent les gains chaque semaine (`ocd.payout._ocd_may_pay`) ; l'équipe tranche les retours dans « À
vérifier » ou sur le gain (Shop › Ambassadeurs › Gains des ambassadeurs).

Pour aider un ambassadeur : sa fiche › onglet Ambassadeur › **Voir son espace** (lien signé pour la
personne de l'équipe connectée).

Les pages : `/ambassadeurs`, `/ambassadeur/connexion`, `/ambassadeur` (ses ventes), `/ambassadeur/argent`
(et `/ambassadeur/numero`), `/ambassadeur/produits`, `/ambassadeur/partager/<produit>`, `/ambassadeur/liens`,
`/a/<code>/<produit>/image.jpg` (l'image de partage, dessinée une fois, versionnée par la photo et le
prix).

Code : `ocd_ambassadors/models/ocd_ambassador_gain.py` (les gains, leurs pièces, la tâche),
`sale_order.py` (le lien, l'attribution, les refus), `res_partner.py` (l'ambassadeur, l'inscription, le
Mobile Money, ce qui retient le versement, la pause), `ocd_payout.py`, `product_template.py` (les produits
à partager, ce qu'on gagne), `controllers/ambassador.py` ; `ocd_ambassadors_whatsapp` (les trois
messages).

## OCD Business (modules `ocd_business` et `ocd_business_whatsapp`)

La formule des vendeurs organisés : plusieurs magasins et leur stock, l'équipe, les chiffres en détail,
les nouveautés chaque semaine, OCD Express (décisions dans [`DECISIONS.md`](DECISIONS.md), Shop et
livraisons).

Mise en route :

1. **OCD Live › Paramètres › OCD Business** : les prix (1, 3, 12 mois ; ceux des autres pays suivent la
   conversion des devises comme le pass de l'annuaire), le jour du lancement, les mois offerts au
   lancement (2), le premier rappel (7 jours avant), la grâce d'un paiement vérifié (3 jours). Les
   limites (5 magasins, 5 personnes) restent dans les sections Magasins et Équipe.
2. **WhatsApp** : soumettre `ocd_business_payee`, `ocd_business_fin_proche`, `ocd_business_terminee` et
   `ocd_business_lancement` (français et anglais, Utilitaire).
3. **Le lancement** : choisir son jour. Ce jour-là, la tâche offre une fois les mois du réglage aux
   vendeurs qui utilisent les fonctions (au moins deux magasins vérifiés, ou une personne d'équipe), puis
   décoche « Fonctions OCD Business offertes à tous ». Sans jour choisi, les fonctions restent offertes.
4. Faire connaître `/business` aux commerçants qui ne font pas de lives.

Le parcours : `/ocd/espace/moi/business` crée une commande du vendeur (ou reprend celle laissée avant de
payer, ou celle dont le paiement est en route) et l'envoie sur `/ocd/payer/<commande>` ; à la
confirmation, `sale.order.line._ocd_process_confirmed_lines` écrit une `ocd.business.period` par ligne
(index unique sur la ligne) avec la durée du produit (`ocd_business_days`), fait la facture et prévient
le vendeur ; « J'ai payé » (Mobile Money vérifié par l'équipe) pose `ocd_business_grace_until` ;
l'annulation de la commande reprend les jours pas passés (`_ocd_cancel`). `res.partner.ocd_business_until`
est recalculé à partir des périodes (`_ocd_business_refresh`) ; `_ocd_business_formula()` dit si le
vendeur a sa formule (ou la grâce), `_ocd_business()` y ajoute l'offre à tous. La tâche « OCD Live :
formules OCD Business » (`_cron_ocd_business`, toutes les heures) fait avancer les périodes, le
lancement, les rappels et la fin.

Pour offrir des jours : la fiche du vendeur › onglet OCD Business › **Offrir des jours** (responsables
d'OCD Live, avec un motif). Pour rembourser : Vendeurs › OCD Business › la période › **Remboursé :
reprendre les jours** (ou annuler la commande).

Code : `ocd_business/models/ocd_business_period.py` (les périodes, le calcul des dates, la tâche),
`res_partner.py` (jusqu'au, la grâce, la ligne de Mon espace, les rappels), `res_company.py` (le
lancement), `sale_order.py` (le paiement, la facture, l'annulation), `controllers/business.py` ;
`ocd_business_whatsapp` (les quatre messages). `ocd_live_shop` garde le magasin de départ visible
(`_ocd_kept_first`) ; `ocd_express` ouvre le compte et offre le petit ramassage avec la formule.

## Tests

Chaque module a ses tests (`tests/`). Lancer tous les tests OCD sur une base neuve :

```bash
odoo -c odoo.conf -d ocd_tests -i ocd_live,ocd_live_shop,ocd_live_whatsapp,ocd_live_shop_whatsapp,ocd_live_recruitment,ocd_delivery_togo,ocd_debranding,ocd_vote,ocd_vote_whatsapp,ocd_tickets,ocd_tickets_whatsapp,ocd_soirees,ocd_soirees_whatsapp,ocd_clips,ocd_clips_whatsapp,ocd_express,ocd_express_whatsapp,ocd_ambassadors,ocd_ambassadors_whatsapp,ocd_business,ocd_business_whatsapp,attachment_s3,whatsapp_cloud_call \
     --test-tags /ocd_live,/ocd_live_shop,/ocd_live_whatsapp,/ocd_live_shop_whatsapp,/ocd_live_recruitment,/ocd_delivery_togo,/ocd_debranding,/ocd_vote,/ocd_vote_whatsapp,/ocd_tickets,/ocd_tickets_whatsapp,/ocd_soirees,/ocd_soirees_whatsapp,/ocd_clips,/ocd_clips_whatsapp,/ocd_express,/ocd_express_whatsapp,/ocd_ambassadors,/ocd_ambassadors_whatsapp,/ocd_business,/ocd_business_whatsapp,/attachment_s3,/payment_cinetpay,/whatsapp_cloud,/whatsapp_cloud_call --stop-after-init
```

Le serveur d'appels WhatsApp a ses tests sans FreeSWITCH ni Odoo (service de copie des conseillers,
échanges des scripts Lua avec Odoo, décisions de la file d'attente ; Lua avec `lua5.3` quand il est là) :

```bash
python3 -m unittest discover -s whatsapp_cloud_call/freeswitch/tests -p "test_*.py"
```

Le téléphone des conseillers se vérifie dans Chromium avec un appel simulé (JsSIP remplacé par un faux) :
`OCD_URL=http://127.0.0.1:8069 OCD_CALL_ID=<id d'un appel> node tools/captures/softphone.js` (admin
conseiller d'un compte avec appels, adresse du serveur d'appels saisie).

Les tests des clips font de vraies vidéos avec ffmpeg (sources `lavfi`, quelques secondes). Ajouter
`/whatsapp_cloud_sale` pour les tests de la commande sur WhatsApp. Avec OCD, un test de
`whatsapp_cloud_sale` échoue, c'est voulu : « commande expédiée » y est remplacé par les messages des colis.

Puis la démo sur une autre base neuve : les mêmes modules et `ocd_live_demo`, avec
`--test-tags /ocd_live_demo,/ocd_live_demo_whatsapp` (la démo change les fenêtres et remplit le fil : les
tests d'`ocd_live` se lancent sur une base sans elle).
Les tests du site (HttpCase) ont besoin d'un port libre (`--http-port=8079` si la démo tourne sur 8069).

La mise en page des écrans qui grandissent avec les données (le fil des lives, l'accueil, la page d'un
pays, « À vérifier »)
se contrôle sur la démo, serveur lancé, à 390, 820, 1024, 1366 × 657, 1440 et 1914 px, et à 125 % de
zoom pour le back-office ; le script échoue si une règle casse (carte coupée, débordement, colonne
écrasée, liste des pays trop longue) :

```bash
OCD_URL=http://127.0.0.1:8069 OCD_SPACE_LINK=/ocd/espace/<jeton> node tools/captures/mise-en-page.js
```

Avec `OCD_SPACE_LINK` (le lien personnel d'un vendeur de la démo), il contrôle aussi « Mon espace » : les
mêmes entrées de menu sur téléphone, tablette et ordinateur, aucun titre recouvert, aucun montant coupé
dans « Mes chiffres ».

## Modèles WhatsApp

Les textes des modèles (`data/whatsapp_template_data.xml`) suivent les règles de Meta, vérifiées par
« Soumettre à Meta » et par le test `test_templates_of_the_modules_follow_meta` (`ocd_live_whatsapp`) :
des mots avant la première variable et après la dernière (un point après la variable ne suffit pas), des
mots entre deux variables (pas seulement une virgule ou une parenthèse), au moins 3 mots par variable.
Dans un modèle *Utilitaire*, rien qui ressemble à une connexion : Meta le refuse comme `INCORRECT_CATEGORY`
(il le prend pour un message d'*Authentification*, réservé au code à usage unique). Ni « code », ni « mot de
passe », ni « identifiant », ni « lien personnel », ni « gardez-le pour vous » (`AUTHENTICATION_RE` de
`whatsapp_cloud`, vérifié à la soumission, boutons compris) : mettre le code sur une page ouverte par un
bouton, et dire ce qui s'est passé. Pas non plus de phrase entière dans une variable.
Plusieurs modèles se soumettent d'un coup : WhatsApp › Modèles, cocher, Action › « Soumettre à Meta » (les
nouveaux, et les changements des refusés ou en pause ; les approuvés et ceux en attente ne bougent pas).

Chaque modèle a sa version anglaise (`data/whatsapp_template_en_data.xml`, même nom chez Meta, langue `en`) :
changer les deux ensemble. Le test `test_english_versions` vérifie qu'elles vont par paires.

Les modèles sont des données `noupdate` : chargés à l'installation, jamais réécrits par une mise à jour
(l'équipe peut changer les textes). **Pour corriger le texte d'un modèle fourni** : changer le XML, monter
la version du module et ajouter une migration qui donne l'ancien texte, mot pour mot :

```python
# <module>/migrations/<version>/post-migration.py
from odoo import SUPERUSER_ID, api

OLD_TEXTS = {"<module>.<id du modèle>": ["<ancien texte>"]}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["whatsapp.template"]._update_module_texts("<module>", OLD_TEXTS)
```

Le modèle prend alors le texte du XML s'il a encore l'ancien texte et n'est ni approuvé ni en cours de
revue chez Meta (le texte approuvé est celui que Meta envoie). Pour un texte que Meta a refusé, passer
`statuses=("unknown", "rejected", "pending")` et appeler d'abord `_cron_read_pending_from_meta()`
(décisions de Meta) ; les boutons se changent dans la migration (exemples : `ocd_live_shop_whatsapp`
20.0.1.5.0, `ocd_live_whatsapp` 20.0.1.8.0). Garder les mêmes variables : celles que le
texte n'utilise plus sont retirées, une nouvelle variable est ajoutée sans valeur (la remplir dans la
migration). Ajouter le module et sa version à `test_migrations_give_the_new_texts`.

## Versions des modules

Chaque commit qui change un module monte sa version (`__manifest__.py`) : `20.0.X.Y.0` pour un ajout
(écran, fonction), `20.0.X.Y.Z` pour une correction. Un serveur sait ainsi quels modules mettre à jour
(`-u`), et le journal ([`PROGRESSION.md`](PROGRESSION.md)) le dit à chaque entrée. Avant de committer :

```bash
python3 tools/versions.py --check
```

Il liste les modules changés depuis leur version et échoue s'il en reste un.

**Sur un serveur**, après avoir récupéré le code, le même outil lit la base et donne la commande à
lancer (rien n'est écrit dans la base) :

```bash
python3 tools/versions.py --db <base> --conf /etc/odoo/odoo.conf
```

Il dit les modules dont la version installée est plus ancienne que le code (`-u`), les modules du projet
pas encore installés (à ajouter à `-i` s'ils sont voulus ; ceux qui s'installent seuls avec un autre sont
signalés, la démo jamais proposée), une commande arrêtée en route (modules restés « à installer » ou « à
mettre à jour ») et un code plus ancien que la base (mauvaise branche déployée), puis la commande `odoo`
complète. Il se connecte comme le serveur (`db_host`, `db_port`, `db_user`, `db_password` du fichier de
configuration, sinon `$ODOO_RC`, sinon les variables `PG*`), avec le Python d'Odoo (psycopg2) ou `psql`.
Ses tests : `python3 -m unittest tools/test_versions.py`.

## Grand écran : tablette et ordinateur

Le téléphone garde le design validé (`ocd_app.scss`, `ocd_live_shop.scss`) ; la tablette (768 px) et
l'ordinateur (1200 px) ont leurs règles à part : `ocd_live/static/src/scss/ocd_large.scss` (les
organisations) et `ocd_live_shop/static/src/scss/ocd_shop_large.scss` (les pages du shop). Une page
choisit son organisation par des classes, ses zones n'existant que sur grand écran (`display: contents`
en dessous, l'ordre du téléphone reste celui du gabarit) :

- `o_ocd_wide` sur le cadre (`o_ocd_frame o_ocd_narrow o_ocd_wide`) : la largeur de l'écran au lieu
  d'une colonne ;
- `o_ocd_panes` sur `main`, avec `o_ocd_pane_main` et `o_ocd_pane_side` : le contenu et ce qui va avec
  (récapitulatif, formulaire) côte à côte sur ordinateur, dès la tablette avec `o_ocd_panes_tablet` ;
  un bouton `o_ocd_side_cta` remplace alors celui du bas de l'écran ;
- `o_ocd_detail`, avec `o_ocd_detail_media` et `o_ocd_detail_info` : le média à gauche, les
  informations à droite (fiche produit, replay) ;
- `o_ocd_focus` sur le cadre, avec `o_ocd_focus_side` et `o_ocd_focus_main` : une page courte, le titre
  et son explication sur un panneau à gauche, le formulaire et son bouton à droite ;
- une page de l'espace vendeur passe `space_page="<page>"` à `common.page_values` : le menu de
  l'espace (`ocd_live.space_menu`, complété par `ocd_live_shop.space_menu`) s'affiche à gauche sur
  ordinateur et en onglets sur tablette.

Chaque écran est vérifié en trois tailles (390, 820, 1440 px), sans débordement horizontal.

## Écriture

Pas de tiret cadratin (U+2014) dans le projet, ni dans le code, les écrans, les maquettes, les
traductions ou la documentation : un deux-points, une virgule ou « · » dans une phrase, un tiret simple
(-) pour une valeur absente. Le test `ocd_live/tests/test_writing.py` le vérifie sur tout le dépôt
(sauf `marketplace/`, modules d'autres auteurs).

## Traductions

Le code et les vues sont en anglais ; le français est dans `<module>/i18n/fr.po`.
Les outils sont dans `tools/i18n/` :

1. Exporter les textes d'un module depuis une base où il est installé :
   `odoo i18n export -c odoo.conf -d <base> -o tools/i18n/pot/<module>.pot <module>`
2. Voir ce qui manque : `python3 tools/i18n/missing.py <module> tools/i18n/fr_*.py`
3. Ajouter les traductions dans un des dictionnaires `tools/i18n/fr_*.py`.
4. Écrire les `.pot` et `fr.po` de tous les modules : `python3 tools/i18n/build.py`
5. Charger : `odoo -c odoo.conf -d <base> -u <modules> --i18n-overwrite --stop-after-init`

Un même mot anglais peut avoir deux sens : utiliser alors un texte anglais différent (ex. « Table
view » pour le bouton « Tableau », « Table » restant le meuble du studio).

Le nom, le résumé et la description d'un module (écran Applications) suivent son `fr.po` à chaque mise à
jour du module (`ocd_live`, `ir_module_module.py`) : Odoo, lui, garde ceux de la première installation.

## Captures d'écran

`tools/captures/` contient des scripts Playwright (`npm i playwright` puis
`OCD_URL=http://127.0.0.1:8069 OUT=docs/captures/ node tools/captures/backoffice.js dashboard,planning`).
Ils se connectent avec admin/admin et prennent les écrans en français.
Pages du shop : `node tools/captures/site-shop.js <vendeur vendu par OCD> <vendeur en contact direct>
[jeton d'un vendeur] [jeton d'un livreur]` (ids des contacts, ex. Brenda Wax et Awa Mensah de la démo ;
le jeton est celui de `_ocd_get_space_token()`, pour l'appli des colis et la tournée : le créer dans
`odoo shell` puis `env.cr.commit()`). Sur téléphone, le script remplit aussi un panier de deux vendeuses
de Douala jusqu'au paiement (`8b`, `8c` ; produits et adresse dans `TWO_PARCELS`). Back-office : `dashboard,planning,regie,verify,orders,dispatch,parcel,
couriers,vendor,payouts,recruit,settings,autos,rates,whatsapp` (`VENDOR_ID`, `PARCEL_ID` pour les
fiches) ; `crons` et `odoo_settings` montrent les listes d'Odoo aux administrateurs.

## Repères dans le code

- Frais de livraison : `ocd_live_shop/models/ocd_delivery_rate.py` (tarifs et moteur : `_ocd_quote`,
  `_ocd_find_rate`, `_ocd_best`), `delivery_carrier.py` (livraison d'Odoo de type `ocd` : somme des
  colis, refus d'une adresse), `sale_order.py` (`ocd_delivery_line_ids` : la livraison de chaque colis
  telle que payée), `stock_picking.py` (`_ocd_parcel_from_delivery` : qui livre, prix exact du colis).

- Cartes du fil des lives : `ocd_live/controllers/feed.py` (`_card`, `_vendor_values`, `preview_card`),
  gabarit `ocd_live.feed_cards`, script `static/src/interactions/feed.js` (vidéo de la carte à l'écran,
  carrousel). Le média d'un vendeur : `res.partner._ocd_card_media()` (`_ocd_card_media_of`, étendu par
  `ocd_live_shop` pour le carrousel des produits) ; routes `/lives/video/<id>` (lecture par morceaux),
  `/lives/video/<id>/image` (affiche), `/lives/carte/<id>` (image) ; page `/ocd/espace/moi/carte`.
- Vidéos : `ocd_live/media.py` (`prepare` : contrôle, conversion MP4 avec ffmpeg et affiche ; `kind` :
  type reconnu par sa signature ; `ffmpeg()` : celui du système, sinon celui d'`imageio-ffmpeg` ; la
  durée et les pistes sont lues par ffprobe s'il est là, sinon par ffmpeg lui-même).
- Un formulaire ne doit jamais être dans un autre : le navigateur ignore celui de l'intérieur et ferme
  celui de l'extérieur à sa fin, les boutons d'après n'envoient plus rien. Un formulaire placé ailleurs
  dans la page se relie à ses champs par l'attribut `form="<id>"` (ex. « Préviens-moi » de la page
  produit ; `ocd_live.phone_field` prend `field_form`).
  `tools/demo/card_video.py` fabrique une vidéo de démo à partir de photos.
- Sans réseau, Odoo désactive tous les boutons de la page (`o_disabled_offline`, sauf ceux qui portent
  `data-available-offline`) : le bouton d'ajout d'un produit et les − / + de son formulaire le portent,
  pour garder le produit dans le téléphone (`ocd_live_shop/static/src/interactions/product_drafts.js`,
  base IndexedDB `ocd_live`, envoi au retour du réseau sous le jeton du formulaire).
- Photos d'un produit : Odoo 20 garde la photo principale comme la première des photos du produit
  (`product.image`, par `sequence`) ; changer l'ordre change la photo principale. Une photo ajoutée à un
  produit en vente est `ocd_review_state = "to_check"` et n'est montrée qu'une fois acceptée
  (`product.template._ocd_vendor_photos`, `_ocd_page_photos`).
- Plateformes et comptes de live : `ocd.live.platform` (`_ocd_for_url`, cache vidé à chaque changement),
  `ocd.live.account` (`_ocd_pick` : pays du vendeur d'abord, libre à l'heure). Lien d'un live :
  `booking._ocd_watch_url()` (le sien, sinon celui de son compte).
- Live à distance : `ocd_live/models/ocd_live_booking_remote.py` (tâche planifiée `_cron_remote_join`
  toutes les 5 minutes : appel 30 min avant, invitation 15 min avant via `_ocd_send_join_invitation`,
  surchargé par `ocd_live_whatsapp`, alerte 5 min avant), page `ocd_live/controllers/remote.py`
  (`/ocd/live/<id>/rejoindre/<secret>`, secret signé qui change si le live est déplacé).
- Devises par pays : `ocd_live/models/ocd_live_currencies.py` (`zone_of` : zone d'un pays ;
  `_ocd_setup` : devises, taux, groupes de pays `ocd_live.country_group_<zone>` et listes de prix
  `ocd_live.pricelist_<zone>` créés une fois puis mis à jour ; `_ocd_set_rates` : parité fixe des francs
  et de l'euro, dollar du jour ; tâche planifiée quotidienne `_cron_update_usd_rate`, qui lit la BCE).
  Les frais de livraison convertis sont arrondis par `ocd.delivery.rate._ocd_converted_price`.
- Paiements de démo CamPay : `payment_campay/models/payment_provider.py` (`_campay_demo_on`,
  `_campay_demo_amount` : montant pour un numéro), `payment_transaction.py` (`_campay_amount` garde le
  montant demandé, `_extract_amount_data` paie la transaction quand CamPay a encaissé exactement ce
  montant, `_create_payment` enregistre l'argent reçu). Réglages : `ocd_live_shop/models/ocd_live_settings.py`
  (`_ocd_campay_demo_items`), ligne du tableau de bord : `ocd.live.dashboard._ocd_demo_payment_todos`.
  Les tests de `payment_campay` se lancent sur une base où il est installé (`--test-tags /payment_campay`).
- Page d'un live (lien de son annonce) : `/lives/<pays>/<id>` (`OcdLiveDirectory.live_page`), carte faite par
  `feed.live_card` (prochain, en direct, replay, terminé) ; l'adresse vient de
  `ocd.live.booking._ocd_public_path()`.
- Une page d'Odoo affichée dans le cadre d'OCD Live (`ocd_live.app`), comme la page d'attente d'un
  paiement (`/payment/status`), reçoit les valeurs des pages d'OCD (`common.page_values`, voir
  `OcdLivePaymentStatus._get_payment_status_values`) : sans elles, le cadre n'a ni langues ni voix.
- Fournisseur de paiement : une route qui reçoit le résultat d'un paiement appelle seulement `_record()`
  (mise en file). Le traitement se fait dans une autre requête (`/payment/process`, appelée par la page
  d'attente) ou par la tâche planifiée, jamais par `_run_processing()` dans la même requête : il tourne
  avec son propre curseur et attendrait les verrous de la requête qui l'a lancé.
- Chiffres des vendeurs (chantier 3) : un seul calcul, `ocd_live_shop/models/vendor_figures.py`
  (`ocd.vendor.figures` : `_ocd_figures` pour la page, `_ocd_month` pour Mon espace,
  `_ocd_product_sales` pour la ligne « Vendu » de Mes produits, `_ocd_week_summary` pour le résumé du
  lundi) ; les comptages jour par jour dans `ocd_live/models/ocd_vendor_count.py` (`_ocd_add` : en
  mémoire, écrits toutes les 5 secondes) ; « Regarder » compté par `/ocd/regarder/<live>` et
  `/ocd/regarder/annonce/<annonce>` (`ocd_live/controllers/watch.py`). Une nouvelle façon d'ouvrir un
  live depuis OCD passe par ces adresses.
- OCD Vote (chantier 4) : `ocd_vote/models/ocd_vote_contest.py` (concours, paquets, classement
  `_ocd_ranking`, nombres cachés `_ocd_hidden`, signature des résultats `_ocd_signature`, tâche planifiée
  `_cron_ocd_vote`), `ocd_vote.py` (une ligne par paiement : `_ocd_create` crée la commande et ses voix,
  `_ocd_on_paid` les compte quand la commande est confirmée par le paiement), pages publiques
  `ocd_vote/controllers/contest.py` (la page du paiement reprend le formulaire d'Odoo comme `/ocd/payer`),
  espace de l'organisateur `organizer.py` (connexion par numéro et code, cible `vote` des pages de
  connexion). Le vote par WhatsApp (« VOTE 12 ») : `ocd_vote_whatsapp/models/discuss_channel.py` (demande
  CamPay sur le téléphone quand le numéro est camerounais, sinon le lien de la page du paiement).
- Paiement automatique dans l'UEMOA (chantier 5) : `payment_cinetpay` suit le modèle de
  `payment_campay`. `models/payment_transaction.py` : `_get_specific_rendering_values` ouvre le paiement
  chez CinetPay (API `payment`) et envoie le client sur sa page ; l'identifiant donné à CinetPay
  (`cinetpay_transaction_id`) est la référence sans espaces ni signes, plus le numéro de la transaction ;
  `_cinetpay_amount` arrondit au multiple de 5 en francs CFA ; `_cinetpay_fetch_status` lit l'état chez
  CinetPay (API `payment/check`), jamais dans les paramètres reçus ; tâche planifiée
  `_cron_cinetpay_check_pending` (toutes les 10 minutes, pendant 24 heures). Routes :
  `/payment/cinetpay/return` (retour du client) et `/payment/cinetpay/webhook` (notification, vérifie
  l'identifiant du site), dans `controllers/main.py`. Les tests de `payment_cinetpay` ne parlent jamais à
  CinetPay (`_send_api_request` remplacé). Flutterwave est le module d'Odoo, sans changement.
  Le Mobile Money vérifié par l'équipe s'efface devant un Mobile Money automatique en production pour
  le pays et la devise : `ocd_live/models/payment_provider.py` (`_find_available_providers`,
  `_ocd_takes_mobile_money`). Les clés manquantes et le mode test sont dits dans les Paramètres
  (`ocd_live_shop/models/ocd_live_settings.py`, `_ocd_provider_text`).
- OCD Tickets (chantier 6) : l'événement est `event.event` (application Événements d'Odoo, avec
  `event_sale`), complété par `ocd_tickets/models/event_event.py` (états `ocd_state`, places restantes
  `_ocd_left` moins les places gardées `_ocd_held`, annuler `action_ocd_cancel`, déplacer `_ocd_move`,
  tâche planifiée `_cron_ocd_tickets` : places non payées remises en vente, rappel la veille, reversement) ;
  un type de billet a son propre produit (`event_ticket.py`, `_ocd_ensure_product`) pour la régie et son
  prix du live (`_ocd_price`) ; une commande de billets se crée par `sale.order._ocd_ticket_create`, et
  ses billets (`event.registration`) naissent à la confirmation par le paiement (`action_confirm` :
  ouverts même si les dernières places sont parties entre-temps, codes, entrée immédiate pour une vente
  à l'entrée). Le billet : code `_ocd_new_code`, QR signé `_ocd_signature` (la page
  `/billets/billet/<id>/<signature>` est aussi l'adresse lue par le scanner), `_ocd_find` (QR ou code
  tapé), `_ocd_let_in`, `_ocd_give`. Pages : `controllers/tickets.py` (public), `entrance.py`
  (contrôleurs : connexion cible `billets`, scan en JSON `/billets/entree/<id>/scan`, liste pour le hors
  réseau `/liste`, vente à l'entrée), `organizer.py` (dans l'espace de l'organisateur d'OCD Vote),
  `boutique.py` (le billet à l'écran pendant un live). Le scanner et le hors réseau :
  `static/src/interactions/tickets.js` (`BarcodeDetector`, `localStorage`).
- Prix promo (chantier 7, 3.1) : `ocd_live_shop/models/product_promo.py`. Le modèle `ocd.product.promo`
  (prix, prix barré gardé à la création, début, fin, source « vendor », « team » ou « evening ») ; le prix
  passe par `_price_compute` de `product.template` et `product.product` (remplacé : le prix de liste
  multiplié par `_ocd_promo_ratio`), donc par toutes les listes de prix, le shop, le panier et la
  commande ; contexte `ocd_without_promo` pour le prix habituel (étiquettes, partage). Deux promos en
  même temps : `_ocd_priority` (le prix le plus bas). Une ligne de commande garde sa promo 2 heures après
  la fin (`PROMO_GRACE`, `ocd_promo_order_date`) ; `sale.order._ocd_refresh_promos` reprend les prix
  ensuite. Le vendeur : `controllers/vendor_promo.py` (`/ocd/espace/moi/produits/<id>/promo`).
- Programme des lives : `ocd_live_shop/controllers/programme.py` (`/lives/programme`, `jour`, `pays`,
  `categorie`), avec deux points d'accroche pour les grands événements (`_ocd_evening_days`,
  `_ocd_evening_band`).
- Grands événements (`ocd_soirees`, noms techniques en « evening ») : `ocd.evening` (une soirée, une
  journée ou plusieurs jours ; `_ocd_one_day`, `_ocd_days`, `_ocd_kind_text` et les textes
  `_ocd_when_text`, `_ocd_when_sentence`, `_ocd_until_text` décident d'après les heures, au fuseau de
  l'événement), `ocd.evening.participation` (`_ocd_submit` crée les promos « evening » inactives,
  `action_ocd_approve` les active), `ocd.evening.alert` (« Me prévenir »). Pages :
  `controllers/evening.py` (`/evenements`, `/evenements/<adresse>`, `/ocd/espace/moi/evenements/<id>` ;
  `/soirees` y mène). WhatsApp : `ocd_soirees_whatsapp` (`ocd_soiree_invitation`,
  `ocd_soiree_commence`).
- Dans Odoo 20, une variable posée dans le corps d'un `t-call` (`<t t-call="x"><t t-set="a" .../></t>`)
  n'arrive pas au gabarit appelé : la poser avant le `t-call`.
- Couleurs et polices communes : `ocd_live/static/src/scss/ocd_tokens.scss`.
- Thème du site : `ocd_live/static/src/scss/ocd_app.scss` (pages sous `.o_ocd_app`).
- Thème du back-office : `ocd_live/static/src/backend/` (barre, onglets, cartes, widget de choix).
- Écrans sur mesure du back-office : un modèle abstrait Python qui prépare les données
  (`ocd.live.dashboard`, `ocd.live.planning`, `ocd.live.verification`, `ocd.live.regie`,
  `ocd.live.dispatch`, `ocd.live.orders`, `ocd.live.couriers`) et un composant OWL
  dans `static/src/<écran>/`. Les modules ajoutent leurs chiffres en héritant des méthodes `_ocd_*`.
- Icônes : Odoo 20 n'a plus Font Awesome ; utiliser `<i class="oi" data-icon="nom"/>` ou `icon="nom"`
  sur les boutons (noms Material, ex. `refresh`, `payments`, `videocam`).
