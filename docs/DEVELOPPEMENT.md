# Développer et tester OCD Live

## Environnement

- **Odoo 20 Community** (Python 3.13, PostgreSQL 16).
- Chemin des modules (`addons_path`) : les modules d'Odoo, **ce dépôt**, et le dossier des modules
  complémentaires `whatsapp_cloud`, `whatsapp_cloud_sale`, `payment_campay`, `delivery_cameroon`.
- Exemple de `odoo.conf` :

```ini
[options]
addons_path = /opt/odoo20/src/addons,/opt/odoo20/src/odoo/addons,/chemin/modules-complementaires,/chemin/projet_ocd
db_host = localhost
db_port = 5432
data_dir = /opt/odoo20/data
```

## Lancer une base de démonstration

```bash
odoo -c odoo.conf -d ocd_demo -i ocd_live,ocd_live_shop,ocd_live_whatsapp,ocd_live_shop_whatsapp,ocd_live_recruitment,ocd_delivery_togo,ocd_live_demo --load-language=fr_FR --stop-after-init
odoo -c odoo.conf -d ocd_demo
```

Mettre ensuite l'utilisateur en français (Préférences) et la devise de la société en franc CFA.
Le site : `/ocd` (réserver), `/lives` (annuaire). Le back-office : application **OCD Live**.

## Tests

Chaque module a ses tests (`tests/`). Lancer tous les tests OCD sur une base neuve :

```bash
odoo -c odoo.conf -d ocd_tests -i ocd_live,ocd_live_shop,ocd_live_whatsapp,ocd_live_recruitment \
     --test-tags /ocd_live,/ocd_live_shop,/ocd_live_whatsapp,/ocd_live_recruitment --stop-after-init
```

Les tests du site (HttpCase) ont besoin du port 8069 libre.

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
le jeton est celui de `_ocd_get_space_token()`, pour l'appli des colis et la tournée).

## Repères dans le code

- Couleurs et polices communes : `ocd_live/static/src/scss/ocd_tokens.scss`.
- Thème du site : `ocd_live/static/src/scss/ocd_app.scss` (pages sous `.o_ocd_app`).
- Thème du back-office : `ocd_live/static/src/backend/` (barre, onglets, cartes, widget de choix).
- Écrans sur mesure du back-office : un modèle abstrait Python qui prépare les données
  (`ocd.live.dashboard`, `ocd.live.planning`, `ocd.live.verification`, `ocd.live.regie`,
  `ocd.live.dispatch`, `ocd.live.orders`, `ocd.live.couriers`) et un composant OWL
  dans `static/src/<écran>/`. Les modules ajoutent leurs chiffres en héritant des méthodes `_ocd_*`.
- Icônes : Odoo 20 n'a plus Font Awesome ; utiliser `<i class="oi" data-icon="nom"/>` ou `icon="nom"`
  sur les boutons (noms Material, ex. `refresh`, `payments`, `videocam`).
