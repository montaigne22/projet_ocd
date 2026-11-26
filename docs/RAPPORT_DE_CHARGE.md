# Rapport de test de charge d'OCD Live

Modèle à remplir à chaque campagne de mesure : sur le serveur de préproduction, puis sur celui de
production avant l'ouverture au grand public. Les parties 1 à 5 sont à remplir (les `…`) ; la partie 6
donne les mesures de référence de la machine de test du 15 novembre 2026, faites avec le même outil
(`tools/charge/charge.py`) ; la partie 7, ce qu'il faut pour 3 millions de visiteurs par jour. Le fonctionnement et les réglages du serveur sont dans
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

- Date : … · Fait par : …
- Version du code (commit) : … · Modules et versions : …
- Base : … vendeurs, … produits, … lives du moment, … commandes (une copie de la production, sinon la
  démo).

| Rôle | Machine (cœurs, mémoire) | Nombre | Réglages |
|---|---|---|---|
| Odoo, pages du site | … | … | `workers = …`, `max_cron_threads = 0`, `db_name = …` sans `dbfilter`, `proxy_mode = True` |
| Odoo, actions planifiées | … | 1 | `max_cron_threads = …` |
| PostgreSQL | … | … | `max_connections = …`, `shared_buffers = …` |
| nginx ou répartiteur | … | … | gzip, … |
| CDN | - | - | adresse : …, règles : … |

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
| … | … | … | … | … | … | … | - |

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

## 7. 3 millions de visiteurs par jour (15 novembre 2026, après le CDN)

### Ce qu'il faut tenir

3 millions de visiteurs × 5 pages = 15 millions de pages par jour ; à la pointe d'un live (10 fois la
moyenne), **~1 740 pages/s**. S'y ajoutent les questions que les pages à l'écran posent seules, que la
partie 1 ne comptait pas : ~2 600/s si le fil reste une minute à l'écran (une question « nouveaux lives »,
une demande des cartes suivantes) et une boutique trois minutes pendant un live (une question « produit à
l'écran » toutes les 20 s). Elles sont plus nombreuses que les pages, mais légères.

### Ce que coûte chaque page

Machine de test (4 cœurs, 16 Go, Odoo 20 avec 4 workers, PostgreSQL 16, base de démo), ApacheBench
16 à la fois, un nouveau visiteur à chaque page ; processeur d'Odoo et de PostgreSQL par page, relevé dans
`/proc` (Odoo + PostgreSQL). Ce coût sert au calcul : il dépend moins que les pages par seconde de ce qui
tourne à côté.

| Page | Depuis la mémoire | Construite pour le visiteur |
|---|---|---|
| Fil des lives | 1 280 pages/s, 3,0 ms (2,4 + 0,6) | 76 pages/s, 51 ms (42 + 9) |
| Page d'un live | 1 283 pages/s, 2,9 ms | 250 pages/s, 16 ms (13 + 3) |
| Shop | 1 235 pages/s, 3,1 ms | 63 pages/s, 62 ms (49 + 13) |
| **Page d'un produit** | 541 pages/s, 7,2 ms | **31 pages/s, 124 ms (97 + 27)** |
| Boutique d'un vendeur | 777 pages/s, 5,0 ms | 84 pages/s, 46 ms (38 + 8) |
| Réservation (`/reserver/studio`, jamais gardée) | - | 146 pages/s, 27 ms |
| Question « nouveaux lives » (jamais gardée) | - | 1 427/s, 2,7 ms |
| Question « cartes suivantes » | 1 397/s, 2,7 ms | 58/s, 67 ms (51 + 16) |
| Question « produit à l'écran » | 1 348/s, 2,8 ms | 671/s, 5,8 ms |

Les pages gardées en mémoire vont plus vite que dans le tableau du matin (partie 6) sur la même machine :
la base de démo a été refaite, la cause n'a pas été cherchée plus loin.

### Le parcours (`charge.py`)

| | Pages/s | Médiane | p95 | p99 | Erreurs | Depuis la mémoire | Processeur par page |
|---|---|---|---|---|---|---|---|
| 8 visiteurs à la fois | 544 | 12 ms | 33 ms | 43 ms | 0 % | 95 % | 7,3 ms |
| 32 visiteurs à la fois | 561 à 589 | 48 ms | 96 ms | 112 ms | 0 % | 95 % | 6,6 ms |
| 64 visiteurs à la fois | 565 | 53 ms | 180 ms | 1 132 ms | 0,01 % | 95 % | 6,7 ms |
| 32 nouveaux visiteurs à la fois | 282 | 77 ms | 184 ms | 372 ms | 0 % | 95 % | 7,4 ms |
| 32 à la fois, toute la démo (40 adresses), 4 workers | 563 | 53 ms | 89 ms | 116 ms | 0 % | 93 % | 6,6 ms |
| La même chose avec 16 workers | 372 | 63 ms | 241 ms | 413 ms | 0 % | **88 %** | **10,3 ms** |

La machine plafonne vers 570 pages/s (l'outil lui prend des cœurs) ; à 64 visiteurs, les premières
erreurs. Pour les nouveaux visiteurs, c'est l'outil qui limite : le serveur dépense autant par page.
**Les deux dernières lignes montrent la limite de la mémoire des pages** : chaque worker garde sa propre
copie, donc plus il y a de workers, plus chaque page est construite souvent (une page demandée r fois par
seconde, gardée T secondes, sur W workers, est construite r / (1 + r·T/W) fois par seconde).

### Le calcul (`tools/charge/dimensionnement.py`)

Il part des coûts ci-dessus, d'une audience (part des pages, adresses différentes, 10 couples langue ×
pays) et cherche l'équilibre entre workers et cœurs (deux workers par cœur, processeurs à 70 %). Il
retrouve la part des pages données depuis la mémoire du parcours (95, 94 et 88 % pour 95, 93 et 88 %
mesurés) et compte les cœurs avec 15 % de plus, l'écart avec le processeur mesuré.

| Pointe d'un live (1 740 pages/s et 2 600 questions/s) | Depuis la mémoire | Cœurs d'Odoo | Cœurs de PostgreSQL |
|---|---|---|---|
| Code d'aujourd'hui, catalogue de la démo (le meilleur cas) | 58 % | 44 | 12 |
| **Code d'aujourd'hui, vrai catalogue** (20 lives à la fois, 300 boutiques, 6 000 produits) | 29 % | **129** (~260 workers) | **35** |
| Mémoire des pages commune à tous les workers, vrai catalogue | 77 % | 50 | 13 |
| Et page d'un produit 3 fois moins chère, gardée 5 minutes | 79 % | 28 | 7 |
| Pour comparer : 1 million par jour, code d'aujourd'hui, vrai catalogue | 29 % | 43 | 12 |

Avec un vrai catalogue, **la page d'un produit fait 43 % du processeur** : ses adresses sont nombreuses
(chaque produit, en chaque langue et pays) et chacun des ~260 workers la construit pour lui-même.

### Ce qu'on en tire

1. **Le code d'aujourd'hui tient 3 millions de visiteurs par jour avec ~130 cœurs pour Odoo** (par exemple
   8 serveurs de 16 cœurs, ~260 workers, ~45 Go de mémoire à 173 Mo par worker) et **un PostgreSQL de 32 à
   40 cœurs**. C'est possible, mais cher, et la base devient la pièce la plus difficile à agrandir.
2. **Le levier le plus fort : une mémoire des pages commune à tous les workers** (par exemple Redis),
   au lieu d'une par worker : 50 cœurs au lieu de 129. Cela revient sur la décision « aucun logiciel de
   plus » ([`DECISIONS.md`](DECISIONS.md#grand-public)) : à décider avant d'aller au-delà d'un million de
   visiteurs par jour.
3. **La page d'un produit** : 124 ms de processeur à construire, la page la plus chère. La rendre moins
   chère, et la garder plus longtemps (un produit change rarement), descend à 28 cœurs avec le point 2.
4. **Compresser les pages** : la plateforme envoie les pages sans compression (`/lives` : 50 Ko, 5 Ko
   compressée). À la pointe, ~700 Mbit/s sortent du serveur au lieu de ~90. À activer sur la plateforme,
   ou en passant le site lui-même par Cloudflare (sans garder les pages).
5. **PostgreSQL** : chaque worker ouvre ses connexions : `max_connections` au moins deux fois le nombre de
   workers, ou PgBouncer devant la base.
6. **Le CDN** : un nouveau téléphone télécharge ~1,5 Mo (mesuré sur le site : 950 Ko pour le fil, 570 Ko
   pour le shop), un téléphone qui revient presque rien. 3 millions de visiteurs, c'est **~4,5 To par jour
   (~135 To par mois, ~4 Gbit/s à la pointe)**, sans les vidéos des cartes (720 px, 30 s : 2 à 3 Mo
   chacune, estimé). Bien au-delà de ce que l'offre gratuite de Cloudflare accepte pour des vidéos : un
   CDN payé au volume, à chiffrer.

### Ce que ce calcul ne dit pas

L'audience est supposée (catalogue, temps passé sur les pages, pointe de 10 fois la moyenne) : refaire le
calcul avec les chiffres d'un vrai soir (`python3 tools/charge/dimensionnement.py --help`). Ne sont pas
mesurés : les achats (panier, paiement), le back-office de l'équipe, les actions planifiées, le réseau
jusqu'en Afrique, et la plateforme qui héberge le site (son entrée est partagée avec d'autres sites).
**La preuve reste à faire sur les vrais serveurs** (parties 1 à 5), avec des machines de test près des
visiteurs, et en prévenant la plateforme avant.

## 8. Serveur de préproduction, 26 novembre 2026

`ocd.my.rollbackk.app` : **1 cœur, 2 Go**, Odoo 20, pages compressées par la plateforme, fichiers du site,
photos et vidéos par le CDN (Cloudflare). Mesuré depuis un serveur hors d'Afrique : environ 0,15 s par
aller-retour et 0,4 s pour ouvrir une connexion sécurisée ; chaque page de l'outil ouvre une nouvelle
connexion (un téléphone la garde) : la médiane d'environ 1,07 s est surtout ce trajet. Le serveur donne une
page gardée en mémoire en 50 à 100 ms. Parcours : fil des lives 30 %, accueil 10 %, shop 20 %, produits 20 %,
boutiques 10 %, réservation 5 % ; paliers de 30 s, visiteurs qui gardent leurs cookies.

| Visiteurs à la fois | 3 workers, sans compression | 3 workers, pages compressées | 4 workers | 3 workers, de nouveau |
|---|---|---|---|---|
| 32 | 28 pages/s, p95 1,7 s | 29 pages/s, p95 1,5 s | 22 pages/s, p95 2,3 s | 30 pages/s, p95 1,3 s |
| 64 | 38 pages/s, p95 3,7 s | 44 pages/s, p95 2,6 s | 30 pages/s, p95 3,4 s | **58 pages/s, p95 1,5 s** |
| 128 | 43 pages/s, p95 7,0 s, 0,23 % d'erreurs | 40 pages/s, p95 7,2 s, 0,17 % | 35 pages/s, p95 13 s, **45 % d'erreurs (503)** | **90 pages/s, p95 2,5 s, 0 erreur** |
| 32 nouveaux visiteurs | 26 pages/s, p95 2,4 s | 28 pages/s, p95 1,6 s | 23 pages/s, p95 2,5 s | - |

- **La compression** des pages par la plateforme : le shop passe de 33 Ko à 5,5 Ko (le fil des lives de
  60 Ko à environ 10 Ko) ; les fichiers du site arrivent déjà compressés du CDN (styles : 198 Ko au lieu de
  1,4 Mo).
- **4 workers sur 1 cœur font moins bien que 3** : le processeur est plein (1,00 cœur) pour moins de pages,
  les workers se disputent le cœur, chacun gardait alors sa propre mémoire des pages (moins de pages
  données depuis la mémoire), et la plateforme répond 503 sous forte charge. Avec 3 workers, le
  processeur reste vers 0,6 cœur. **Réglage retenu : 3 workers.**
- Les écarts entre les deux mesures à 3 workers (44 puis 90 pages/s à 64 et 128 visiteurs) viennent de la
  plateforme et du réseau ce jour-là, pas du code (le même) : refaire chaque mesure deux fois.
- **Le partage de la mémoire des pages entre les workers** (`ocd_live` 20.0.1.32.0, fichiers dans
  `/dev/shm`), mesuré ici avec 3 workers, le même jour, partage allumé puis coupé par le paramètre
  `ocd_live.page_cache_shared` :

  | Visiteurs à la fois | Partage allumé | Partage coupé |
  |---|---|---|
  | 32 | 25 pages/s, p95 1,9 s | 29 pages/s, p95 1,5 s |
  | 64 | 32 pages/s, p95 5,1 s, 25 % d'erreurs | **55 pages/s, p95 1,6 s, 0 erreur** |
  | 128 | 25 pages/s, p95 15 s, 1 % d'erreurs | **68 pages/s, p95 3,8 s, 0 erreur** |
  | 128 nouveaux visiteurs | 28 pages/s, 1 % d'erreurs | **63 pages/s, 0 erreur** |
  | 64 pendant 2 minutes | 33 pages/s, p95 3,5 s | **52 pages/s, p95 1,7 s, 0 erreur** |

  Le processeur était plein (0,9 à 1 cœur) avec le partage, pour deux fois moins de pages : sur cette
  plateforme, les fichiers partagés coûtent (dossier sans doute sur un disque et non en mémoire). Sur la
  machine de test, le partage ne coûtait rien (194 contre 190 pages/s). **Le partage est coupé par défaut
  depuis `ocd_live` 20.0.1.33.0** ; à n'allumer que là où une mesure montre qu'il aide.
- L'appel le plus léger d'Odoo (`/web/health`) passe à 135 par seconde depuis la même machine : le chemin
  réseau et la plateforme ne limitent pas les pages.

## 9. Dix fois plus de données : écrans de l'équipe et actions planifiées, 26 novembre 2026

Une copie de la démo grossie par `tools/charge/volume.py` (facteur 10) : 141 vendeurs, 343 produits, 1 875
clients, 3 490 commandes et 4 059 colis sur 30 jours (70 % livrés), 899 lives, 410 conversations WhatsApp,
1 000 abonnés. `tools/charge/requetes.py` mesure chaque écran comme un vrai appel (transaction neuve, rien
en mémoire) et lance chaque action planifiée une fois. Machine de test, un seul utilisateur.

| Écran | Démo | 10 fois plus | Après correction |
|---|---|---|---|
| Tableau de bord | 317 requêtes, 1,0 s | **3 333 requêtes, 6,7 s** | **168 requêtes, 1,3 s** |
| Commandes de la semaine | 60 requêtes, 0,15 s | **533 requêtes, 1,3 s** | **31 requêtes, 0,19 s** |
| Dispatch | 47 requêtes, 0,1 s | 48 requêtes, 0,7 s | (dix fois plus de colis du jour à lire) |
| Conversations WhatsApp | 254 requêtes, 0,34 s | 99 requêtes, 0,15 s (410 conversations) | |
| Réservations, À vérifier, Automatisations, Paramètres, Livreurs, Régie | 35 à 196 requêtes | les mêmes | |

- **La cause** : le taux de change d'une monnaie était demandé pour chaque montant additionné (deux fois
  par colis livré pour les commissions, une fois par commande) ; il l'est maintenant une fois par jour et
  par monnaie (`ocd_live/tools.py`, `converter`).
- **Ce qui reste** : le tableau de bord additionne « l'argent reçu » depuis le premier paiement, colis par
  colis (leurs montants sont calculés, pas enregistrés) : 1,3 s ici, et cela grandira avec l'historique. À
  traiter avant d'avoir des dizaines de milliers de colis (enregistrer ces montants, ou un total par mois).
- **Les actions planifiées** (toutes celles d'OCD Live, d'OCD Express, des concours, des billets, des
  événements et de WhatsApp) : de 7 à 98 requêtes et moins de 0,5 s chacune, les mêmes à dix fois plus de
  données. Seule celle de la démo (absente en production) est lourde (5,6 s).

## 10. Le parcours d'achat, 26 novembre 2026

Ces pages ne viennent jamais de la mémoire. `tools/charge/achat.py` : chaque client virtuel ouvre la fiche
d'un produit, l'ajoute au panier (première couleur, première taille), ouvre l'adresse, choisit le
Cameroun, la première ville et son premier quartier, envoie l'adresse et arrive à la page du paiement
(sans payer). Machine de test (4 cœurs, 3 workers), copie de la démo.

| Clients à la fois | Parcours jusqu'au paiement | Erreurs |
|---|---|---|
| 1 | 50 par minute | 0 |
| 4 | 184 par minute | 0 |
| 8 | 186 par minute | 0 |
| 16 | 192 par minute | 0 |
| 32 | 206 par minute | 0 |

Chaque parcours coûte environ 1,1 s de processeur : le plafond (environ 3 achats par seconde) est atteint
dès 4 clients à la fois. Sur le serveur de préproduction (1 cœur), on peut s'attendre à environ un achat par
seconde au plus, en plus des visites. Le coût de chaque étape (un client) :

| Étape | Requêtes | Temps |
|---|---|---|
| Fiche du produit | 30 | 0,14 s |
| Ajout au panier | 89 | 0,18 s |
| Panier | 48 | 0,08 s |
| Adresse (formulaire, deux fois avec le pays) | 55 | 0,09 s |
| Quartiers de la ville | 47 | 0,06 s |
| Envoi de l'adresse | 196 | 0,31 s |
| Page du paiement | 200 | 0,31 s |

Les deux dernières étapes sont les plus lourdes : à regarder avant une forte affluence d'acheteurs.

## 11. Commandes

```bash
# Un palier : 200 visiteurs pendant 5 minutes, 8 processus (machine de 8 cœurs)
python3 tools/charge/charge.py 200 300 --processes 8 --base https://preprod.example.com

# La pointe d'un live : chaque page par un nouveau téléphone
python3 tools/charge/charge.py 200 300 --processes 8 --nouveaux --base https://preprod.example.com

# Une seule page, avec ApacheBench (apt-get install apache2-utils)
ab -n 5000 -c 50 https://preprod.example.com/lives

# Les cœurs pour 3 millions de visiteurs par jour, puis avec une mémoire des pages commune aux workers
python3 tools/charge/dimensionnement.py 3000000
python3 tools/charge/dimensionnement.py 3000000 --partagee

# Dix fois plus de données, sur une copie de la démo (jamais la production)
createdb -T ocd_demo ocd_volume
VOLUME=10 odoo-bin shell -c odoo.conf -d ocd_volume --no-http < tools/charge/volume.py

# Le coût de chaque écran de l'équipe et de chaque action planifiée (sur la démo, puis sur la copie grossie)
odoo-bin shell -c odoo.conf -d ocd_volume --no-http < tools/charge/requetes.py

# Le parcours d'achat jusqu'au paiement (laisse un panier et un contact par parcours)
python3 tools/charge/achat.py 8 60 --base https://preprod.example.com --produit /shop/robe-en-wax-38
```
