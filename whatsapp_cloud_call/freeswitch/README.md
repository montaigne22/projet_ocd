# Serveur d'appels WhatsApp (FreeSWITCH)

Installer le serveur qui reçoit les appels WhatsApp de Meta et fait sonner l'équipe dans Odoo. Le
pourquoi et la feuille de route : [`docs/APPELS_WHATSAPP.md`](../../docs/APPELS_WHATSAPP.md).

```
Meta ──SIP/TLS 5061, voix SRTP──► FreeSWITCH ──WSS 7443, WebRTC──► navigateurs des agents (Odoo)
                                       │
                                       ├── ocd-call-sync : agents et mots de passe depuis Odoo (30 s)
                                       ├── scripts Lua : file d'attente, demande à Odoo qui faire sonner
                                       └── mod_json_cdr : la fiche de chaque appel vers Odoo
```

Deux façons d'installer, aussi robustes l'une que l'autre :

- **Docker (conseillé)** : trois conteneurs (FreeSWITCH, ocd-call-sync, coturn), une commande pour
  installer et pour mettre à jour, retour arrière en changeant d'image. FreeSWITCH est compilé depuis
  ses sources dans l'image : **aucun compte ni jeton SignalWire**.
- **Sur le serveur** (paquets Debian de SignalWire, avec un compte et un jeton gratuits).

Kubernetes n'est pas conseillé : la voix demande des milliers de ports UDP et l'IP publique fixe du
serveur, et déplacer un pod coupe les appels en cours.

| Dossier | Contenu |
|---|---|
| `docker/` | image de FreeSWITCH (`Dockerfile`), image d'ocd-call-sync (`Dockerfile.sync`), `docker-compose.yml`, `.env.example`, coturn |
| `conf/` | profils SIP (Meta, agents), plan d'appel, domaine, modules, socket d'événements, musique, fiches d'appels |
| `scripts/` | file d'attente (`ocd_whatsapp_inbound.lua`), événements et veille du conseiller, `ocd/` |
| `sync/` | `ocd_call_sync.py` et son service systemd |
| `tls/` | certificat Let's Encrypt pour FreeSWITCH et coturn (les deux façons) |
| `coturn/` | relais TURN des agents, installation sur le serveur |
| `tests/` | tests sans FreeSWITCH (`python3 -m unittest`, `lua5.3`) ; `tests/e2e/` : essai de bout en bout avec Odoo |

## 1. Le serveur

Toutes les commandes de ce guide se lancent en root : `sudo -i` d'abord. Avec `sudo` devant chaque
commande, les `>` ne marchent pas (la redirection est faite sans les droits de root : « Permission
denied »).

- Debian 12, 2 cœurs, 2 Go de mémoire, IP publique fixe, dans un datacenter (Europe de l'Ouest ou
  Afrique de l'Ouest, au plus près des clients et de l'équipe).
- Un nom, par ex. `appels.rollbackk.app`, qui pointe sur cette IP (enregistrement DNS A).
- Rien d'autre sur ce serveur : coturn y prend le port 443.

Pare-feu (nftables ou celui de l'hébergeur), tout le reste fermé :

| Port | Pour |
|---|---|
| 22/TCP | SSH de l'équipe technique (de ses adresses seulement, si possible) |
| 80/TCP | Let's Encrypt, seulement si rien d'autre ne tient le port 80 (sinon : section 2) |
| 5061/TCP | Meta (SIP sur TLS) |
| 7443/TCP | agents (SIP sur WebSocket sécurisé) |
| 16384-29999/UDP | voix (FreeSWITCH ; sous 30000, hors des ports NodePort de Kubernetes) |
| 3478/UDP+TCP, 443/TCP (ou 5349/TCP) | relais TURN (coturn) ; 5349 quand nginx tient déjà le 443 |
| 49152-65535/UDP | voix relayée (coturn) |

Les ports 5070 et 5090 (SIP sans chiffrement des deux profils) et 8021 (socket d'événements)
restent **fermés**.

**Pas de reverse proxy** devant le serveur d'appels : Meta parle SIP sur TLS au port 5061 (pas du
HTTP) et vérifie le certificat du serveur lui-même, la voix passe en UDP sur des milliers de ports, et
chaque appel porte l'IP publique du serveur. Les ports ci-dessus s'ouvrent directement sur lui. Le
reverse proxy d'Odoo ne change pas : le serveur d'appels joint Odoo par son adresse HTTPS publique.

**DNS** : un enregistrement A vers l'IP du serveur d'appels. Chez Cloudflare, en **« DNS only »
(nuage gris)**, jamais en nuage orange : Cloudflare ne relaie que le web sur quelques ports, il
bloquerait le SIP, le port 7443 et la voix.

**Sur une machine où nginx (ou un autre programme) tient déjà les ports 80 et 443** :
- le certificat s'obtient sans le port 80 (section 2) ;
- coturn prend le port **5349** au lieu de 443 : `TURN_TLS_PORT=5349` dans le `.env` (Docker) ou
  `tls-listening-port=5349` dans `/etc/turnserver.conf`, **et le même dans Odoo** : Paramètres ›
  WhatsApp › Appels › Port du relais TURN (TLS). Ouvrir 5349/TCP au lieu de 443. Le relais marche
  pareil ; seuls quelques réseaux très fermés (qui ne laissent sortir que le 443) ne le joindront pas.
- FreeSWITCH n'utilise ni le 80 ni le 443 : rien d'autre à changer.

### Sur une machine k3s (Traefik)

Traefik tient les ports 80 et 443 de la machine (par le répartiteur de k3s). Le serveur d'appels
tourne **à côté de k3s**, avec Docker (`docker compose`, section 3A), sur le réseau de la machine :
Traefik ne voit passer aucun appel, il n'y a ni Ingress ni IngressRoute à créer. Docker et k3s
cohabitent (k3s a son propre containerd) ; après l'installation de Docker, vérifier que les pods
répondent toujours (`kubectl get pods -A`, Odoo ouvert dans le navigateur).

1. **DNS** : `appels.rollbackk.app` vers l'IP de la machine, en « DNS only » chez Cloudflare.
2. **Certificat** : par le DNS (section 2, façon **c**, avec certbot sur la machine), ou par
   **cert-manager** s'il délivre déjà les certificats d'Odoo dans k3s (ci-dessous).
3. **Relais TURN** : `TURN_TLS_PORT=5349` dans le `.env`, et 5349 dans Odoo (Paramètres › WhatsApp ›
   Appels › Port du relais TURN (TLS)).
4. **Voix** : la plage 16384-29999 par défaut évite déjà les ports NodePort de k3s (30000-32767) ;
   ne pas la monter au-delà de 29999 (`OCD_RTP_START`, `OCD_RTP_END` du `.env`).
5. **Pare-feu** : celui de la section 1, avec 5349/TCP au lieu de 443/TCP.

**Le certificat par cert-manager** : un `Certificate` pour `appels.rollbackk.app` dans k3s (avec
l'émetteur déjà utilisé pour Odoo), dont cert-manager garde le certificat dans un secret. Un script le
recopie chaque nuit pour FreeSWITCH et coturn :

```bash
cp $SRC/tls/ocd-certs-from-k8s.sh /usr/local/lib/ocd/ && chmod 750 /usr/local/lib/ocd/ocd-certs-from-k8s.sh
cat >> /etc/default/ocd-freeswitch-certs <<'CONF'
OCD_K8S_SECRET=appels-rollbackk-tls
OCD_K8S_NAMESPACE=ocd
OCD_LIVE_DIR=/etc/ocd-calls/live
CONF
/usr/local/lib/ocd/ocd-certs-from-k8s.sh
echo '10 3 * * * root /usr/local/lib/ocd/ocd-certs-from-k8s.sh' > /etc/cron.d/ocd-certs-from-k8s
```

(Le nom du secret et son espace de noms sont ceux du `Certificate`, `spec.secretName`.) Le script
écrit le certificat comme certbot (`fullchain.pem`, `privkey.pem`, `chain.pem`) et lance la copie
quand il a changé ; l'application de la nuit (`ocd-freeswitch-certs.timer`, 3 h 20) le donne ensuite à
FreeSWITCH et à coturn sans couper d'appel. Il lit k3s avec `/etc/rancher/k3s/k3s.yaml`.

## 2. Le certificat (Let's Encrypt)

Meta vérifie que le certificat est à ce nom et signé par une autorité reconnue. Le même sert aux
agents (WSS) et au relais TURN.

D'abord le dépôt sur le serveur, dans `/opt/ocd-calls/src`. Le dépôt privé, git demande l'utilisateur
GitHub et, en mot de passe, un jeton GitHub « fine-grained » limité à ce dépôt, droit « Contents :
Read-only » (GitHub › Settings › Developer settings › Personal access tokens) :

```bash
apt-get install -y git
git clone --depth 1 https://github.com/montaigne22/projet_ocd.git /opt/ocd-calls/src
```

Puis le script du certificat :

```bash
SRC=/opt/ocd-calls/src/whatsapp_cloud_call/freeswitch
apt-get install -y certbot
install -d /usr/local/lib/ocd
cp $SRC/tls/ocd-freeswitch-certs.sh /usr/local/lib/ocd/ && chmod 750 /usr/local/lib/ocd/ocd-freeswitch-certs.sh
cp $SRC/tls/ocd-freeswitch-certs.service $SRC/tls/ocd-freeswitch-certs.timer /etc/systemd/system/
```

Avec Docker, dire au script où est la pile (`/etc/default/ocd-freeswitch-certs`) :

```bash
printf 'OCD_MODE=docker\nOCD_COMPOSE_FILE=%s/docker/docker-compose.yml\nOCD_SIP_DOMAIN=%s\n' \
  "$SRC" appels.rollbackk.app > /etc/default/ocd-freeswitch-certs
```

Puis obtenir le certificat. Trois façons, selon ce qui tient le port 80 de la machine :

**a. Le port 80 est libre** : certbot l'ouvre lui-même le temps de la vérification.

```bash
certbot certonly --standalone -d appels.rollbackk.app \
  --deploy-hook "/usr/local/lib/ocd/ocd-freeswitch-certs.sh copy"
```

**b. nginx tient le port 80** (le cas le plus courant) : nginx sert le petit fichier de vérification
de Let's Encrypt. Ajouter ce bloc à nginx (par ex. `/etc/nginx/conf.d/appels.conf`) :

```nginx
server {
    listen 80;
    server_name appels.rollbackk.app;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 404; }
}
```

```bash
mkdir -p /var/www/certbot && nginx -t && systemctl reload nginx
certbot certonly --webroot -w /var/www/certbot -d appels.rollbackk.app \
  --deploy-hook "/usr/local/lib/ocd/ocd-freeswitch-certs.sh copy"
```

(nginx dans un conteneur : monter `/var/www/certbot` dans ce conteneur.) Ce bloc ne sert qu'au
certificat : nginx ne fait passer aucun appel.

**c. Par le DNS** (aucun port à ouvrir, le domaine chez Cloudflare) : certbot prouve la possession du
domaine en écrivant un enregistrement DNS temporaire. Il faut un jeton d'API Cloudflare limité à la
zone, droit « DNS : Modifier » (Cloudflare › Mon profil › Jetons d'API), saisi sur le serveur
seulement : `read` le demande sans l'afficher ni le garder dans l'historique.

```bash
apt-get install -y python3-certbot-dns-cloudflare
install -d -m 700 /root/.secrets
install -m 600 /dev/null /root/.secrets/cloudflare.ini
read -rsp "Jeton Cloudflare : " CF; echo
printf 'dns_cloudflare_api_token = %s\n' "$CF" > /root/.secrets/cloudflare.ini; unset CF
certbot certonly --dns-cloudflare --dns-cloudflare-credentials /root/.secrets/cloudflare.ini \
  -d appels.rollbackk.app --deploy-hook "/usr/local/lib/ocd/ocd-freeswitch-certs.sh copy"
```

Dans les trois cas, ensuite :

```bash
/usr/local/lib/ocd/ocd-freeswitch-certs.sh copy
systemctl daemon-reload && systemctl enable --now ocd-freeswitch-certs.timer
```

certbot renouvelle tout seul, de la même façon qu'au premier certificat (`certbot renew --dry-run`
pour l'essayer).

Au renouvellement (tous les 2 mois environ), le certificat est copié, puis appliqué la nuit suivante à
un moment sans appel : un redémarrage des profils couperait les appels en cours, le script attend
qu'il n'y en ait aucun (vérifié : « Calls in progress », puis appliqué au passage suivant).

## 3A. Installation avec Docker (conseillé)

Docker Engine, depuis le dépôt de Docker (Debian 12 n'a pas `docker compose` dans ses paquets) :

```bash
install -m 0755 -d /etc/apt/keyrings
. /etc/os-release
curl -fsSL "https://download.docker.com/linux/$ID/gpg" -o /etc/apt/keyrings/docker.asc
echo "deb [signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/$ID $VERSION_CODENAME stable" > /etc/apt/sources.list.d/docker.list
apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Puis la pile :

```bash
SRC=/opt/ocd-calls/src/whatsapp_cloud_call/freeswitch
cd $SRC/docker
cp .env.example .env && chmod 600 .env
nano .env        # nom du serveur, IP publique, adresse d'Odoo, clé, mots de passe (voir les commentaires)
mkdir -p sounds  # les messages enregistrés (section 5)
docker compose build      # FreeSWITCH compilé depuis ses sources : une dizaine de minutes
docker compose up -d
docker compose ps         # freeswitch et ocd-call-sync « healthy »
```

- Le certificat est lu dans `OCD_CERTS_DIR` (par défaut `docker/data/certs`, écrit par le script de la
  section 2).
- Le réseau est celui du serveur (`network_mode: host`) : la voix utilise des milliers de ports UDP et
  chaque appel porte l'IP publique du serveur, que le réseau de Docker casserait.
- **Mettre à jour** : `git -C /opt/ocd-calls/src pull`, puis `docker compose build && docker compose up -d` (de
  préférence la nuit : le redémarrage de FreeSWITCH coupe les appels en cours).
- **Journaux** : `docker compose logs -f freeswitch`, `docker compose logs -f ocd-call-sync` ; la
  console de FreeSWITCH : `docker compose exec freeswitch fs_cli`.
- Les versions compilées (FreeSWITCH, sofia-sip, spandsp) sont fixées dans `docker/Dockerfile`
  (arguments `FREESWITCH_REF`...) : les monter pour une nouvelle version, puis reconstruire.

### Le fichier `.env`, ligne par ligne

Il reste sur le serveur (`chmod 600 .env`), jamais dans le dépôt (il est ignoré par git). Trois valeurs
viennent d'Odoo ou doivent y être recopiées à l'identique : elles sont marquées **Odoo**.

| Ligne | Exemple | Ce que c'est | D'où vient la valeur |
|---|---|---|---|
| `OCD_SIP_DOMAIN` | `appels.rollbackk.app` | Le nom du serveur d'appels. Meta lui envoie les appels, les navigateurs des agents s'y connectent, le certificat est à ce nom | Choisi par l'équipe, avec un enregistrement DNS A vers l'IP du serveur. **Odoo** : le même dans Paramètres › WhatsApp › Appels › Adresse du serveur d'appels |
| `EXTERNAL_IP` | `203.0.113.10` | L'IP publique fixe du serveur : FreeSWITCH l'écrit dans chaque appel pour que la voix revienne au bon endroit | Le tableau de bord de l'hébergeur (adresse IPv4 du serveur) |
| `OCD_ODOO_URL` | `https://odoo.ocdlive.com` | L'adresse d'Odoo, comme l'équipe l'ouvre (sans `/odoo` à la fin) : le serveur d'appels y lit les agents et y envoie les appels | L'adresse d'Odoo. Elle doit être en HTTPS et joignable depuis le serveur d'appels |
| `OCD_TOKEN` | `Xy3...` (43 caractères) | La clé du serveur d'appels : Odoo refuse toute demande sans elle | **Odoo** : Paramètres › WhatsApp › Appels › Clé du serveur d'appels (bouton copier). Après « Nouvelle clé » dans Odoo : la recopier ici, puis `docker compose up -d` |
| `OCD_ESL_PASSWORD` | `9f2c...` | Le mot de passe entre FreeSWITCH et ocd-call-sync, sur le serveur seulement (127.0.0.1) | À inventer : `openssl rand -hex 24`. Nulle part ailleurs, ni dans Odoo |
| `TURN_SECRET` | `4be1...` | Le secret du relais TURN : Odoo s'en sert pour donner à chaque agent des identifiants de 12 heures, coturn pour les vérifier | À inventer : `openssl rand -hex 32`. **Odoo** : le même dans Paramètres › WhatsApp › Appels › Secret du relais TURN |
| `TURN_TLS_PORT` | `443` | Le port du relais TURN en TLS | `443`, ou `5349` quand nginx tient déjà le 443 sur la machine. **Odoo** : le même dans Paramètres › WhatsApp › Appels › Port du relais TURN (TLS) |
| `OCD_SRTP` | `SDES` | Comment Meta et le serveur chiffrent la voix | Le même que dans Odoo, compte WhatsApp, onglet Appels, « Chiffrement de la voix » (SDES conseillé) |
| `OCD_CERTS_DIR` | `./data/certs` | Le dossier du certificat | Laisser la valeur : le script de la section 2 y écrit |
| `OCD_SOUNDS_DIR` | `./sounds` | Le dossier des messages enregistrés (section 5) | Laisser la valeur, y poser les fichiers WAV |

Lignes facultatives, à ne pas mettre sauf besoin : `OCD_SYNC_INTERVAL` (secondes entre deux copies
des agents, 30 par défaut), `OCD_RTP_START` et `OCD_RTP_END` (ports UDP de la voix, 16384-29999 par
défaut : ouvrir la même plage dans le pare-feu) et `OCD_AGENT_CANDIDATE_ACL` (`wan_v4.auto` par
défaut : les adresses publiques des agents ; `localnet.auto` seulement pour un essai où les agents
sont sur le même réseau que le serveur).

Après un changement du `.env` : `docker compose up -d` (les conteneurs concernés redémarrent ; de
préférence quand personne n'est en appel).

Derrière un proxy qui intercepte le TLS (réseau d'entreprise), donner son autorité à la construction :
`docker compose build` avec `DOCKER_BUILDKIT=1` et `--secret id=build_ca,src=ca.crt` (voir
`docker/build_ca.sh`) ; sinon rien à faire.

## 3B. Installation sur le serveur (paquets de SignalWire)

Les paquets demandent un compte SignalWire gratuit et un jeton personnel (`pat_...`) : signalwire.com,
créer un espace, puis « Personal Access Tokens ». Le jeton se tape sur le serveur, jamais dans une
conversation ni dans le dépôt.

```bash
TOKEN=pat_...
apt-get update && apt-get install -y gnupg2 wget lsb-release curl python3
wget --http-user=signalwire --http-password=$TOKEN -O /usr/share/keyrings/signalwire-freeswitch-repo.gpg \
  https://freeswitch.signalwire.com/repo/deb/debian-release/signalwire-freeswitch-repo.gpg
echo "machine freeswitch.signalwire.com login signalwire password $TOKEN" > /etc/apt/auth.conf
chmod 600 /etc/apt/auth.conf
echo "deb [signed-by=/usr/share/keyrings/signalwire-freeswitch-repo.gpg] https://freeswitch.signalwire.com/repo/deb/debian-release/ $(lsb_release -sc) main" \
  > /etc/apt/sources.list.d/freeswitch.list
apt-get update && apt-get install -y freeswitch-meta-vanilla freeswitch-mod-lua freeswitch-mod-json-cdr \
  freeswitch-mod-opus freeswitch-music-default
```

(Les commandes officielles du moment sont sur la page « Installing FreeSWITCH » de SignalWire : les
suivre si elles ont changé.)

Les fichiers d'OCD, et sans les exemples de FreeSWITCH (leurs mots de passe sont connus de tous) :

```bash
cd /etc/freeswitch
mkdir -p /root/freeswitch-exemple
mv sip_profiles/internal.xml sip_profiles/external.xml sip_profiles/internal-ipv6.xml \
   sip_profiles/external-ipv6.xml sip_profiles/external sip_profiles/internal directory/default.xml \
   directory/default /root/freeswitch-exemple/ 2>/dev/null
cp $SRC/conf/vars_ocd.xml /etc/freeswitch/
cp $SRC/conf/sip_profiles/*.xml /etc/freeswitch/sip_profiles/
cp $SRC/conf/dialplan/ocd.xml /etc/freeswitch/dialplan/
cp $SRC/conf/directory/ocd.xml /etc/freeswitch/directory/
cp $SRC/conf/autoload_configs/*.xml /etc/freeswitch/autoload_configs/
cp -r $SRC/scripts/* /usr/share/freeswitch/scripts/
install -d -o freeswitch -g freeswitch -m 750 /etc/freeswitch/directory/ocd /var/lib/freeswitch/ocd \
  /var/spool/ocd-calls /var/spool/ocd-calls/voicemail /var/spool/ocd-calls/cdr-errors
```

- `/etc/freeswitch/vars_ocd.xml` : `ocd_sip_domain` = le nom du serveur, `ocd_esl_password` = un mot
  de passe long (`openssl rand -hex 24`) pour le socket d'événements (127.0.0.1 seulement).
- `/etc/freeswitch/vars.xml` : ajouter à la fin, avant `</include>`, une ligne `X-PRE-PROCESS` d'inclusion
  de `vars_ocd.xml` (`cmd="include" data="vars_ocd.xml"`) ; et remplacer les deux lignes `stun-set`
  (`external_rtp_ip`, `external_sip_ip`) par des `set` à l'IP publique du serveur : sans cela,
  FreeSWITCH interroge un serveur STUN extérieur à chaque rechargement (10 secondes de blocage quand il
  ne répond pas).
- `fs_cli` avec ce mot de passe : `/etc/fs_cli.conf`, `[default]` puis `password => ...`.
- `/etc/freeswitch/autoload_configs/switch.conf.xml` : activer `rtp-start-port` à 16384 et
  `rtp-end-port` à 29999 (lignes en commentaire au départ), la plage ouverte dans le pare-feu.

Le lien avec Odoo (ocd-call-sync) :

```bash
cp $SRC/sync/ocd_call_sync.py /usr/local/lib/ocd/
cp $SRC/sync/ocd-call-sync.conf.example /etc/ocd-call-sync.conf
chown freeswitch:freeswitch /etc/ocd-call-sync.conf && chmod 600 /etc/ocd-call-sync.conf
nano /etc/ocd-call-sync.conf   # odoo_url, token (la clé), esl_password
cp $SRC/sync/ocd-call-sync.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now ocd-call-sync
systemctl restart freeswitch
journalctl -u ocd-call-sync -f
```

Le relais TURN :

```bash
apt-get install -y coturn
cp $SRC/coturn/turnserver.conf /etc/turnserver.conf
SECRET=$(openssl rand -hex 32); sed -i "s/CHANGE-ME/$SECRET/; s/calls.example.com/appels.rollbackk.app/" /etc/turnserver.conf
echo $SECRET   # à saisir dans Odoo : Paramètres › WhatsApp › Appels › Secret du relais TURN
install -d -o turnserver -g turnserver /etc/coturn
/usr/local/lib/ocd/ocd-freeswitch-certs.sh copy
systemctl enable --now coturn
```

Le service coturn de Debian a le droit d'ouvrir le port 443 ; sinon, ajouter
`AmbientCapabilities=CAP_NET_BIND_SERVICE` à son service (`systemctl edit coturn`).

## 4. Ce que fait le serveur

- **ocd-call-sync**, toutes les 30 secondes : dit à Odoo que le serveur tourne (agents connectés,
  version, fichiers en attente), recopie les agents et leurs mots de passe, renvoie à Odoo les
  messages et les fiches d'appels restés en attente. Odoo arrêté : la dernière copie reste, les appels
  sonnent chez les agents connectés (vérifié : appel pris pendant qu'Odoo était arrêté, sa fiche
  arrivée dans Odoo à son retour). Sans signe du serveur pendant 5 minutes, les responsables WhatsApp
  sont prévenus.
- **La file d'attente** : accueil, musique, le conseiller de la conversation d'abord puis tous les
  conseillers libres ensemble ; 3 minutes sans conseiller (30 secondes quand personne n'est connecté) :
  messagerie, posée dans la conversation.
- **La veille du conseiller** : pendant une conversation, toutes les 3 secondes, le conseiller est-il
  toujours connecté ? Page fermée ou réseau tombé, au bout de 9 secondes sa branche est coupée et
  l'appel passe aux collègues pendant que le client entend « nous vous reconnectons » (vérifié : le
  collègue sonne 8 secondes après la fermeture de la page). FreeSWITCH seul ne le remarque pas
  toujours (à travers le relais TURN en particulier). Le navigateur d'un conseiller dont la voix ne
  passe plus raccroche avec une cause « réseau » : l'appel revient aussi.

## 5. Les messages enregistrés

Dans `sounds/` (Docker) ou `/usr/share/freeswitch/sounds/ocd/` (sur le serveur) ; WAV, mono, 16 kHz,
la voix de l'équipe, en français :

| Fichier | Quand | Exemple |
|---|---|---|
| `accueil.wav` | dès que l'appel arrive | « Bonjour, bienvenue chez OCD Live, un conseiller va vous répondre. » |
| `reconnexion.wav` | le conseiller a été coupé | « Un instant, nous vous reconnectons. » |
| `messagerie.wav` | personne de disponible | « Nos conseillers sont occupés. Laissez votre message après le bip, nous vous rappelons. » |
| `indisponible.wav` | personne, et pas de messagerie | « Nos conseillers sont occupés. Écrivez-nous sur WhatsApp, nous vous répondons vite. » |

Sans fichier, une tonalité courte le remplace. La musique d'attente est celle de FreeSWITCH
(`local_stream://moh`, 16 kHz).

Convertir un enregistrement : `ffmpeg -i accueil.m4a -ac 1 -ar 16000 accueil.wav`.

## 6. Chez Meta

Les droits et les réglages à activer chez Meta, étape par étape (où cliquer, ce qu'on doit voir, que
faire si ça bloque) : **[`docs/APPELS_WHATSAPP_META.md`](../../docs/APPELS_WHATSAPP_META.md)**. En
bref : le numéro sur la Cloud API, le jeton de l'utilisateur système avec ses trois autorisations, l'app
Meta en mode « Live » (exigé pour le SIP), une limite d'envoi de 2 000 ou plus, un moyen de paiement, le
webhook abonné au champ `calls` ; puis, dans Odoo, « Envoyer les appels à Meta ».

## 7. Vérifier

- `fs_cli -x "sofia status"` (Docker : `docker compose exec freeswitch fs_cli -x "sofia status"`) :
  profils `ocd_whatsapp` (5061, TLS) et `ocd_agents` (7443, WSS) en `RUNNING`.
- Un agent dans Odoo, téléphone de la barre du haut, « Je prends les appels » : point vert ;
  `fs_cli -x "sofia status profile ocd_agents reg"` le montre.
- Le certificat vu de l'extérieur :
  `openssl s_client -quiet -verify_hostname appels.rollbackk.app -connect appels.rollbackk.app:5061`.
- Un vrai appel depuis WhatsApp sur un téléphone (pas WhatsApp Web) : il sonne chez l'agent ; il
  apparaît dans **WhatsApp › Appels** et dans la conversation du client.
- Les lignes `[ocd]` du journal de FreeSWITCH viennent des scripts d'OCD.

L'essai de bout en bout (un faux Meta, Odoo, un agent dans Chromium) se rejoue avec
[`tests/e2e/`](tests/e2e/README.md). Les essais au studio avant d'ouvrir à tous sont dans
[`docs/APPELS_WHATSAPP.md`](../../docs/APPELS_WHATSAPP.md).

## Ce qui reste à confirmer avec Meta

Tout le reste a été vu de bout en bout avec un faux Meta qui appelle comme la documentation de Meta le
décrit (TLS, signature, SDES, en-têtes `x-wa-meta-*`). Avec le vrai Meta, à regarder au premier appel :

- Le nom d'utilisateur que Meta met dans sa signature (le numéro avec ou sans `+`) : les deux sont
  créés.
- Le chiffrement SDES (`srtp_key_exchange_protocol`) : Meta le décrit comme à activer. S'il est
  refusé, passer le compte en DTLS (onglet Appels, `OCD_SRTP=DTLS` avec Docker) et suivre la note de
  `vars_ocd.xml`.
- La signature des appels de Meta : FreeSWITCH la demande par un « 407 » (Meta dit accepter le « 401 »).
  Si les appels de Meta s'arrêtent là (`sofia global siptrace on` pour le voir), mettre `auth-calls` à
  `false` dans `sip_profiles/ocd_whatsapp.xml` et n'ouvrir le port 5061 qu'aux adresses de Meta.
- Les adresses IP de Meta pour le SIP, à ajouter au pare-feu du port 5061 si on veut le fermer à tous
  les autres (la signature de chaque appel suffit déjà).
