# Développer et tester OCD Live

## Environnement

- **Odoo 20 Community** (Python 3.13, PostgreSQL 16).
- Chemin des modules (`addons_path`) : les modules d'Odoo, **ce dépôt** (qui contient aussi
  `whatsapp_cloud`, `whatsapp_cloud_sale`, `payment_campay` et `delivery_cameroon`), et son dossier
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
odoo -c odoo.conf -d ocd_demo -i ocd_live,ocd_live_shop,ocd_live_whatsapp,ocd_live_shop_whatsapp,ocd_live_recruitment,ocd_delivery_togo,ocd_debranding --load-language=fr_FR --stop-after-init
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
tailles épuisées). Une action planifiée (toutes les 15 minutes) la tient sur les jours autour
d'aujourd'hui : rien à refaire avant une présentation. Une vraie vidéo pour ses replays et un vrai compte pour ses lives se
règlent dans OCD Live › Configuration › Paramètres › Démo. Le scénario de présentation, vendeur par
vendeur et heure par heure, est dans [`DEMO.md`](DEMO.md).

Elle publie le paiement à la livraison, active le Mobile Money vérifié par l'équipe (numéros d'exemple)
et ouvre les réservations sans date d'ouverture. Aucun message WhatsApp ne part vers ses contacts, dont
les numéros sont des exemples : `ocd_live_demo_whatsapp` s'installe avec elle quand WhatsApp est là.
Le stock est posé sans mouvement de stock et les colis livrés ne valident pas le transfert : la
désinstallation de `ocd_live_demo` retire tout (contacts, produits, photos, stocks, lives, commandes,
paiements, factures, reversements, tarifs, fenêtres) et remet les moyens de paiement et la date
d'ouverture comme avant.

Le site : `/ocd` (réserver), `/lives` (annuaire), `/shop`. Le back-office : application **OCD Live**.

## Mettre à jour un serveur déjà installé

Après un `git pull` du dépôt : redémarrer Odoo, puis mettre à jour les modules OCD (Applications ›
module › Mettre à jour, ou en ligne de commande) :

```bash
odoo -c odoo.conf -d <base> -u whatsapp_cloud,whatsapp_cloud_sale,ocd_live,ocd_live_shop,ocd_live_whatsapp,ocd_live_shop_whatsapp,ocd_live_recruitment,ocd_delivery_togo,ocd_debranding --stop-after-init
```

**À chaque récupération du code, mettre à jour les modules.** Sans cela, le code appelle des pages qui
n'existent pas encore dans la base, et le site répond « Page introuvable » (404) ; c'est arrivé sur « Moi »
avec la page de l'équipe. La version d'un module augmente quand ses vues ou ses données changent, pour les
outils qui ne mettent à jour qu'un module dont la version a changé.

Avec la démo, ajouter `ocd_live_demo` à la liste : sa mise à jour met le nouveau scénario en place et
installe `ocd_live_demo_whatsapp` (voir [`DEMO.md`](DEMO.md)). Avec CamPay, ajouter `payment_campay`.

Les changements à faire une seule fois sur une base existante sont dans `migrations/` de chaque module
(ex. `ocd_live` 20.0.1.1.0 : accueil d'OCD Live sur `/`, site en français, logo, menus traduits).

Un nouveau module (ex. `theme_ocd`) n'apparaît qu'après **Applications › Mettre à jour la liste des
applications** (mode développeur). Le thème se choisit ensuite dans Site Web › Configuration ›
Paramètres › Choisir un thème › « OCD Live » : Odoo l'installe et l'applique au site.

## Tests

Chaque module a ses tests (`tests/`). Lancer tous les tests OCD sur une base neuve :

```bash
odoo -c odoo.conf -d ocd_tests -i ocd_live,ocd_live_shop,ocd_live_whatsapp,ocd_live_shop_whatsapp,ocd_live_recruitment,ocd_delivery_togo,ocd_debranding \
     --test-tags /ocd_live,/ocd_live_shop,/ocd_live_whatsapp,/ocd_live_shop_whatsapp,/ocd_live_recruitment,/ocd_delivery_togo,/ocd_debranding --stop-after-init
```

Ajouter `/whatsapp_cloud,/whatsapp_cloud_sale` pour les tests de WhatsApp eux-mêmes. Avec OCD, un test de
`whatsapp_cloud_sale` échoue, c'est voulu : « commande expédiée » y est remplacé par les messages des colis.

Puis la démo sur une autre base neuve : les mêmes modules et `ocd_live_demo`, avec
`--test-tags /ocd_live_demo,/ocd_live_demo_whatsapp` (la démo change les fenêtres et remplit le fil : les
tests d'`ocd_live` se lancent sur une base sans elle).
Les tests du site (HttpCase) ont besoin d'un port libre (`--http-port=8079` si la démo tourne sur 8069).

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
- Couleurs et polices communes : `ocd_live/static/src/scss/ocd_tokens.scss`.
- Thème du site : `ocd_live/static/src/scss/ocd_app.scss` (pages sous `.o_ocd_app`).
- Thème du back-office : `ocd_live/static/src/backend/` (barre, onglets, cartes, widget de choix).
- Écrans sur mesure du back-office : un modèle abstrait Python qui prépare les données
  (`ocd.live.dashboard`, `ocd.live.planning`, `ocd.live.verification`, `ocd.live.regie`,
  `ocd.live.dispatch`, `ocd.live.orders`, `ocd.live.couriers`) et un composant OWL
  dans `static/src/<écran>/`. Les modules ajoutent leurs chiffres en héritant des méthodes `_ocd_*`.
- Icônes : Odoo 20 n'a plus Font Awesome ; utiliser `<i class="oi" data-icon="nom"/>` ou `icon="nom"`
  sur les boutons (noms Material, ex. `refresh`, `payments`, `videocam`).
