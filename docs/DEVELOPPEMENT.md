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
  commande du shop envoie un PDF.

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

La démo remplit tous les écrans : vendeurs et lives (payé, en attente, replay, liste d'attente),
annuaire, produits avec photos, robe en 2 couleurs et 4 tailles avec leur stock (« Plus que 3 »,
taille épuisée, savon épuisé), tarifs de livraison (Douala, agences, prix de Fatou), colis à préparer,
prêt, en route, livrés, en problème et en retard, espèces chez un livreur, factures des vendeuses et
reversements à vérifier (si la comptabilité existait avant la démo), trois livreurs dont un en repos.
Elle publie le paiement à la livraison (une commande du shop peut être payée de bout en bout) et active
le Mobile Money vérifié par l'équipe, avec des numéros d'exemple.
Le stock est posé sans mouvement de stock et les colis livrés ne valident pas le transfert : la
désinstallation de `ocd_live_demo` retire tout (contacts, produits, photos, stocks, commandes, factures,
reversements, tarifs) et remet les moyens de paiement comme avant.

Le site : `/ocd` (réserver), `/lives` (annuaire), `/shop`. Le back-office : application **OCD Live**.

## Mettre à jour un serveur déjà installé

Après un `git pull` du dépôt : redémarrer Odoo, puis mettre à jour les modules OCD (Applications ›
module › Mettre à jour, ou en ligne de commande) :

```bash
odoo -c odoo.conf -d <base> -u ocd_live,ocd_live_shop,ocd_live_whatsapp,ocd_live_shop_whatsapp,ocd_live_recruitment,ocd_delivery_togo,ocd_debranding --stop-after-init
```

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

Puis la démo sur une autre base neuve : les mêmes modules et `ocd_live_demo`, avec `--test-tags /ocd_live_demo`.
Les tests du site (HttpCase) ont besoin d'un port libre (`--http-port=8079` si la démo tourne sur 8069).

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

- Couleurs et polices communes : `ocd_live/static/src/scss/ocd_tokens.scss`.
- Thème du site : `ocd_live/static/src/scss/ocd_app.scss` (pages sous `.o_ocd_app`).
- Thème du back-office : `ocd_live/static/src/backend/` (barre, onglets, cartes, widget de choix).
- Écrans sur mesure du back-office : un modèle abstrait Python qui prépare les données
  (`ocd.live.dashboard`, `ocd.live.planning`, `ocd.live.verification`, `ocd.live.regie`,
  `ocd.live.dispatch`, `ocd.live.orders`, `ocd.live.couriers`) et un composant OWL
  dans `static/src/<écran>/`. Les modules ajoutent leurs chiffres en héritant des méthodes `_ocd_*`.
- Icônes : Odoo 20 n'a plus Font Awesome ; utiliser `<i class="oi" data-icon="nom"/>` ou `icon="nom"`
  sur les boutons (noms Material, ex. `refresh`, `payments`, `videocam`).
