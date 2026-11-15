# Rapport de test de charge d'OCD Live

Modèle à remplir à chaque campagne de mesure : sur le serveur de préproduction, puis sur celui de
production avant l'ouverture au grand public. Les parties 1 à 5 sont à remplir (les `…`) ; la partie 6
donne les mesures de référence de la machine de test du 15 novembre 2026, faites avec le même outil
(`tools/charge/charge.py`). Le fonctionnement et les réglages du serveur sont dans
[`DEVELOPPEMENT.md`](DEVELOPPEMENT.md#grand-public--tenir-les-foules-dun-live).

## 1. Ce qu'on veut prouver

Un visiteur ouvre environ 5 pages. Les photos, les vidéos et les fichiers du site partent du CDN : ils
ne comptent pas ici, le serveur ne fait que les pages.

| Visiteurs par jour | Pages par jour | En moyenne | Le soir (×4) | Pointe d'un live (×10) |
|---|---|---|---|---|
| 1 million | 5 millions | 58 pages/s | ~230 pages/s | **~600 pages/s** |
| 3 millions | 15 millions | 175 pages/s | ~700 pages/s | **~1 800 pages/s** |

Critères de réussite au palier de pointe visé (à confirmer avec l'équipe) :

- 95 % des pages en moins d'une seconde (p95 < 1 s), mesuré depuis un centre de données en Afrique ;
- moins de 0,1 % d'erreurs ;
- processeurs des serveurs et de la base de données sous 70 % (de quoi absorber une pointe de plus) ;
- aucune requête de la base de données de plus de 2 s.

## 2. Ce qui est testé

- Date : … — Fait par : …
- Version du code (commit) : … — Modules et versions : …
- Base : … vendeurs, … produits, … lives du moment, … commandes (une copie de la production, sinon la
  démo).

| Rôle | Machine (cœurs, mémoire) | Nombre | Réglages |
|---|---|---|---|
| Odoo, pages du site | … | … | `workers = …`, `max_cron_threads = 0`, `db_name = …` sans `dbfilter`, `proxy_mode = True` |
| Odoo, actions planifiées | … | 1 | `max_cron_threads = …` |
| PostgreSQL | … | … | `max_connections = …`, `shared_buffers = …` |
| nginx ou répartiteur | … | … | gzip, … |
| CDN | — | — | adresse : …, règles : … |

Réglages d'OCD Live (OCD Live › Configuration › Paramètres › Vitesse du site) : pages gardées en
mémoire **oui / non** ; adresse du CDN : ….

## 3. Comment on mesure

- **Le parcours** : les pages et leur poids, comme l'audience d'un soir de lives : fil des lives 30 %,
  page d'un live 15 %, shop 20 %, page d'un produit 20 %, boutique d'un vendeur 10 %, réservation 5 %
  (à corriger avec les chiffres d'un vrai soir : journal de nginx, tableau de bord du CDN). Les adresses
  sont dans `PARCOURS` en tête de `tools/charge/charge.py`.
- **Deux sortes de visiteurs** : ceux qui reviennent (le téléphone garde ses cookies), et les nouveaux
  (`--nouveaux` : chaque page par un nouveau téléphone), qui font la pointe d'un live partagé sur TikTok.
- **Les paliers** : 50, 200, 500, 1 000, 2 000 visiteurs à la fois, 5 minutes chacun, puis plus haut
  jusqu'à la rupture (plus de 1 % d'erreurs ou p95 au-delà de 2 s) : le palier d'avant est la capacité.
- **D'où** : jamais depuis le serveur testé (l'outil lui prendrait ses cœurs). Une machine dans un centre
  de données proche des visiteurs (Lagos, Johannesburg, Paris) ; plusieurs au-delà de 500 visiteurs à la
  fois, en additionnant leurs résultats. Pour des milliers de visiteurs, k6 ou Locust avec le même
  parcours conviennent aussi.
- **Ce qu'on relève** : pages par seconde, temps médian, p95 et p99, erreurs, part des pages données
  depuis la mémoire (en-tête `X-OCD-Cache: hit`), processeur et mémoire de chaque serveur, connexions et
  requêtes lentes de PostgreSQL (`log_min_duration_statement = 500`), part des fichiers servis par le CDN.
- **Pour comparer** : un palier avec la case « Pages publiques gardées en mémoire » décochée, puis
  recochée.

## 4. Résultats

L'outil imprime une ligne prête pour ces tableaux.

### Visiteurs qui reviennent, pages gardées en mémoire

| Visiteurs à la fois | Durée | Pages/s | Médiane | p95 | p99 | Erreurs | Depuis la mémoire |
|---|---|---|---|---|---|---|---|
| 50 | 5 min | … | … | … | … | … | … |
| 200 | 5 min | … | … | … | … | … | … |
| 500 | 5 min | … | … | … | … | … | … |
| 1 000 | 5 min | … | … | … | … | … | … |
| 2 000 | 5 min | … | … | … | … | … | … |

### Nouveaux visiteurs (pointe d'un live), pages gardées en mémoire

| Visiteurs à la fois | Durée | Pages/s | Médiane | p95 | p99 | Erreurs | Depuis la mémoire |
|---|---|---|---|---|---|---|---|
| … | … | … | … | … | … | … | … |

### Pages construites pour chaque visiteur (case décochée), pour comparer

| Visiteurs à la fois | Durée | Pages/s | Médiane | p95 | p99 | Erreurs | Depuis la mémoire |
|---|---|---|---|---|---|---|---|
| … | … | … | … | … | … | … | — |

### Les serveurs au palier le plus haut

| Serveur | Processeur | Mémoire | Remarque |
|---|---|---|---|
| … | … | … | … |

## 5. Ce qu'on en tire

- Capacité d'un serveur d'Odoo (pages par seconde avec p95 < 1 s) : ….
- Serveurs d'Odoo pour 1 million de visiteurs par jour (600 pages/s en pointe) : … ; pour 3 millions
  (1 800 pages/s) : ….
- Ce qui a lâché en premier, et ce qu'on change : ….
- Décision : ….

## 6. Référence : la machine de test, 15 novembre 2026

Une machine de 4 cœurs et 16 Go : Odoo 20 avec 4 workers, PostgreSQL 16 sur la même machine, la base de
démo (15 vendeurs dans 8 pays). Les visiteurs partent de la même machine et lui prennent des cœurs : ce
sont des minimums. Sur cette machine, le plus petit appel d'Odoo (`/web/health`, sans base ni page) tient
environ 570 appels par seconde : c'est le plafond d'Odoo lui-même, quelle que soit la page.

### Chaque page seule (ApacheBench, 16 à la fois, chaque page par un nouveau visiteur)

| Page | Construite pour chaque visiteur | Gardée en mémoire | Gain |
|---|---|---|---|
| Fil des lives (`/lives`) | 47 pages/s, médiane 338 ms | 463 pages/s, médiane 32 ms | ×10 |
| Page d'un live (`/lives/cm/39`) | 76 pages/s, médiane 205 ms | 443 pages/s, médiane 35 ms | ×6 |
| Shop (`/shop`) | 42 pages/s, médiane 367 ms | 499 pages/s, médiane 31 ms | ×12 |
| Page d'un produit | 23 pages/s, médiane 688 ms | 250 pages/s, médiane 60 ms | ×11 |
| Boutique d'un vendeur | 53 pages/s, médiane 294 ms | 315 pages/s, médiane 49 ms | ×6 |

Une page gardée en mémoire coûte presque autant que le plus petit appel d'Odoo : ce n'est plus la
construction des pages qui limite, mais le nombre de workers. La page d'un produit et la boutique
gardent un peu de travail à chaque visite (Odoo vérifie le produit de l'adresse ; la boutique compte la
visite du live).

### Le parcours (`tools/charge/charge.py`, visiteurs qui gardent leurs cookies)

| | 8 visiteurs à la fois | 32 visiteurs à la fois |
|---|---|---|
| Avant (code du 14 novembre) | 42 pages/s, médiane 183 ms, p95 311 ms | 47 pages/s, médiane 683 ms, p95 871 ms |
| Case décochée | 46 pages/s, médiane 163 ms, p95 285 ms | 43 pages/s, médiane 749 ms, p95 963 ms |
| Pages gardées en mémoire | 200 à 330 pages/s (le plus souvent ~290), médiane 21 à 38 ms, p95 46 à 68 ms | ~200 pages/s, médiane ~150 ms, p95 ~200 ms |

95 % des pages viennent de la mémoire ; aucune erreur. À 32 visiteurs, l'outil lui-même occupe les cœurs
de la machine : le serveur seul fait plus (voir le tableau d'avant).

### Une boutique pendant un live, chaque page par un nouveau téléphone

Le pire cas : chaque page compte une visite du live (2 000 visites, 32 à la fois).

| | Avant | Maintenant |
|---|---|---|
| Pages par seconde | 45 | 172 |
| Médiane | 464 ms | 159 ms |
| Conflits d'écriture dans la base | 60 (pages refaites, 10 en erreur) | 0 |

Avant, chaque visite écrivait la ligne du live et les visiteurs s'attendaient les uns les autres ;
maintenant chaque worker les écrit ensemble toutes les 5 secondes, à part.

### Un réglage du serveur qui compte

Avec `db_name = <base>` et sans `dbfilter` dans `odoo.conf`, Odoo ne demande plus la liste des bases à
PostgreSQL pour chaque nouveau visiteur : le fil des lives gardé en mémoire passe de ~250 à ~460 pages/s
pour les nouveaux visiteurs.

### Ce que la machine de test ne dit pas

Les vrais serveurs (cœurs, réseau), la distance jusqu'aux téléphones en Afrique, le CDN, les questions
que les pages posent seules (nouveaux lives chaque minute, produit à l'écran toutes les 20 s) et les
achats (panier, paiement), qui ne viennent jamais de la mémoire : c'est l'objet des parties 1 à 5.

## 7. Commandes

```bash
# Un palier : 200 visiteurs pendant 5 minutes, 8 processus (machine de 8 cœurs)
python3 tools/charge/charge.py 200 300 --processes 8 --base https://preprod.ocdlive.com

# La pointe d'un live : chaque page par un nouveau téléphone
python3 tools/charge/charge.py 200 300 --processes 8 --nouveaux --base https://preprod.ocdlive.com

# Une seule page, avec ApacheBench (apt-get install apache2-utils)
ab -n 5000 -c 50 https://preprod.ocdlive.com/lives
```
