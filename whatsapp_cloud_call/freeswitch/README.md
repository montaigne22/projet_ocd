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

Le dossier copié depuis un PC Windows (sans git) : ses fichiers ont souvent les fins de ligne de
Windows, et les scripts ne démarrent pas (« cannot execute: required file not found »). Les remettre
au format de Linux, avant la suite :

```bash
find /opt/ocd-calls/src/whatsapp_cloud_call/freeswitch -type f ! -name '*.wav' ! -name '*.mp3' ! -name '*.MP3' ! -path '*/data/*' -exec sed -i 's/\r$//' {} +
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
- **Journaux** : `docker compose logs -f freeswitch` (sans les lignes DEBUG), `docker compose logs -f
  ocd-call-sync` ; le journal complet de FreeSWITCH (DEBUG et trace SIP compris, 10 fichiers de 50 Mo
  au plus) : `docker compose exec freeswitch tail -f /var/log/freeswitch/freeswitch.log` ; la console
  de FreeSWITCH : `docker compose exec freeswitch fs_cli`. Avant la version 20.0.1.4.0 du module,
  `docker compose logs freeswitch` ne montrait que le démarrage : lire le fichier.
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
| `OCD_SOUNDS_DIR` | `./sounds` | Le dossier des messages enregistrés (section 5) | Laisser la valeur, y poser les fichiers MP3 ou WAV (`docker/sounds/` et son README.md) |

Lignes facultatives, à ne pas mettre sauf besoin : `OCD_SYNC_INTERVAL` (secondes entre deux copies
des agents, 30 par défaut), `OCD_RTP_START` et `OCD_RTP_END` (ports UDP de la voix, 16384-29999 par
défaut : ouvrir la même plage dans le pare-feu) et `OCD_AGENT_CANDIDATE_ACL` (`wan_v4.auto` par
défaut : les adresses publiques des agents ; `localnet.auto` seulement pour un essai où les agents
sont sur le même réseau que le serveur). `OCD_META_SIP` sert seulement aux essais (le faux Meta) :
jamais en production, où les appels de l'entreprise vont à `wa.meta.vc`.

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
- **Les appels de l'entreprise** (phase 2) : le conseiller clique « Appeler par WhatsApp » (conversation)
  ou « Rappeler » (fiche d'un appel) ; Odoo vérifie l'accord du client chez Meta et prépare l'appel ; le
  téléphone du conseiller compose `out<numéro de la fiche>`. Le serveur demande alors à Odoo à qui et par
  quel numéro (`/whatsapp/call/server/outbound`) : sans sa réponse, il refuse (un appel de l'entreprise
  est payant). Il appelle le client par la passerelle `meta_<ID du numéro>` (vers `wa.meta.vc`, TLS,
  signée avec le numéro de l'entreprise et le mot de passe SIP de Meta), écrite par ocd-call-sync
  (`/var/lib/freeswitch/ocd/gateways_meta.xml`) et rechargée quand elle change (journal : `gateways to
  Meta: meta_...`). Vérifier : `docker compose exec freeswitch fs_cli -x "sofia status gateway"`. Le
  serveur doit pouvoir sortir vers `wa.meta.vc` port 5061 (TCP). Odoo donne aussi la durée maximale de
  l'appel (`max_talk`, compte WhatsApp, onglet Appels, 30 minutes par défaut) : le serveur arrête la
  ligne du client à cette durée après sa réponse (`sched_hangup`, cause `ALLOTTED_TIMEOUT`, fin notée
  « système »).
- **L'enregistrement des appels** (Odoo, compte WhatsApp, onglet Appels, « Enregistrer les appels ») :
  le client entend `enregistrement` (après l'accueil ; à son décroché pour un appel de l'entreprise,
  avant le conseiller) ; le serveur enregistre l'appel à partir du moment où le client et un conseiller
  sont mis ensemble (pas l'attente), jusqu'à la fin, les deux voix mêlées, 16 kHz
  (`/var/spool/ocd-calls/recordings/<uuid>.wav`). Une fois l'appel fini (fichier inchangé depuis
  30 secondes), ocd-call-sync le convertit en MP3 (32 kbit/s, environ 240 ko par minute) et l'envoie
  à Odoo (`/whatsapp/call/server/recording`), et le renvoie tant qu'Odoo ne l'a pas pris (refusé une
  semaine : mis de côté en `.refused.wav`). Journal : « Recording ... sent to Odoo ».
- **Jamais de boucle** : un conseiller qui décroche mais dont la voix ne passe pas (sa branche
  coupée moins de 15 secondes après le décroché, deux fois dans le même appel) n'est plus appelé
  pour cet appel : les collègues sonnent, sinon la messagerie (journal : `cut off again ... not rung
  again for this call`). Au-delà de 3 coupures dans un appel, on n'attend plus un conseiller seul.
- **Le décroché** : le téléphone d'Odoo répond dès qu'il a l'adresse du relais TURN (le chemin de
  la voix quand le direct est bloqué), sinon 3 secondes après son adresse publique (STUN), au plus
  tard 8 secondes après le clic.
- **Le diagnostic du téléphone** : chaque décroché laisse sur la fiche de l'appel (WhatsApp ›
  Appels, « Diagnostic du téléphone ») ce qu'a fait le téléphone du conseiller : sa version, le
  micro, les adresses réseau obtenues (host, srflx = STUN, relay = TURN) et quand, la réponse
  envoyée, l'appel établi, la fin. La version du téléphone est aussi dans son menu (barre du haut) :
  après une mise à jour, Ctrl+F5 sur la page du conseiller pour la charger.
- **La veille du conseiller** : pendant une conversation, toutes les 3 secondes, le conseiller est-il
  toujours connecté ? Page fermée ou réseau tombé, au bout de 9 secondes sa branche est coupée et
  l'appel passe aux collègues pendant que le client entend « nous vous reconnectons » (vérifié : le
  collègue sonne 8 secondes après la fermeture de la page). FreeSWITCH seul ne le remarque pas
  toujours (à travers le relais TURN en particulier). Le navigateur d'un conseiller dont la voix ne
  passe plus raccroche avec une cause « réseau » : l'appel revient aussi.

## 5. Les messages enregistrés

**Le plus simple : dans Odoo**, compte WhatsApp, onglet Appels, « Messages des appels » : un message
par ligne (Accueil, Annonce d'enregistrement, Voix d'attente, Musique d'attente, Conseiller coupé,
Messagerie, Personne de disponible), un fichier MP3 ou WAV, « Écouter » pour l'entendre ; et « Voix
d'attente toutes les (secondes) ». Choisir le message remplit sa colonne « Texte » avec le texte
proposé ci-dessous, en français puis en anglais, avec le nom du numéro chez WhatsApp : l'équipe le
garde ou l'écrit à sa façon, puis l'enregistre. Chaque numéro WhatsApp a les siens. ocd-call-sync les prend dans la
minute : il télécharge les fichiers changés (vérifiés par leur empreinte), les convertit (sox : mono,
16 kHz, volume égalisé) dans `/var/lib/freeswitch/ocd/sounds/<ID du numéro>/`, et met à jour le flux
d'attente du numéro (`local_stream://ocd_<ID du numéro>` : sa musique et ses voix) sans redémarrer
FreeSWITCH ni couper les appels (un client qui attend entend au plus une seconde de silence quand sa
musique change). Odoo montre l'état de chaque message : « En cours d'envoi », « Sur le serveur
d'appels », ou « Refusé » avec la raison (pas un MP3 ou un WAV, illisible). Journal :
`docker compose logs ocd-call-sync | grep -E "Message|hold stream"`.

Ce qu'Odoo ne donne pas pour un numéro vient du dossier `sounds/` du serveur (ci-dessous), sinon une
tonalité courte (rien pour la voix d'attente, la musique de FreeSWITCH pour la musique).

**Le dossier du serveur** : `docker/sounds/` (Docker) ou `/usr/share/freeswitch/sounds/ocd/` (sur le
serveur). Avec Docker, le dossier vient avec le code, avec ses sous-dossiers `voix/` et `attente/` et
un README.md dans chacun, qui explique ce qu'on y met ; les fichiers audio restent hors de git. **MP3 ou WAV**, la voix
de l'équipe (ou une voix off), en français, puis en anglais si besoin. Au démarrage, le serveur prépare chaque fichier : un MP3 est
converti en WAV (mono, 16 kHz) ; un WAV et un MP3 du même nom : le WAV l'emporte. `docker compose logs
freeswitch` dit « Sounds ready: N file(s) » (et pourquoi un fichier est écarté).

**Les noms** :
- les messages du tableau ci-dessous (`accueil`, `enregistrement`, `reconnexion`, `messagerie`,
  `indisponible`), à la racine de `sounds/` : **ce nom exact, en minuscules**, suivi de `.mp3` ou
  `.wav` (`Accueil.mp3`, `accueil OCD.mp3` ne sont pas trouvés : une tonalité à la place) ;
- dans `voix/` et `attente/` : des noms libres, joués dans l'ordre alphabétique (les numéroter :
  `1-patientez.mp3`, `2-occupes.mp3`) ;
- partout : lettres sans accent, chiffres, `-`, `_`, `.` ; ni espace ni accent (le fichier est écarté,
  « Sounds: ... skipped » dans le journal) ;
- sous Windows, afficher les extensions (Explorateur › Affichage › « Extensions de noms de fichiers ») :
  sinon un fichier peut s'appeler en vrai `accueil.mp3.mp3`.

```
sounds/
├── accueil.mp3
├── enregistrement.mp3
├── messagerie.mp3
├── voix/
│   ├── 1-patientez.mp3
│   └── 2-occupes.mp3
└── attente/
    └── 1-musique.mp3
```

| Message dans Odoo (fichier du dossier) | Quand | Durée conseillée | Texte proposé | En anglais |
|---|---|---|---|---|
| Accueil (`accueil.mp3`) | dès que l'appel arrive | environ 6 s ; 12 s au plus avec les deux langues | « Bonjour et bienvenue chez OCD Live. Un conseiller va vous répondre dans un instant. » | “Hello and welcome to OCD Live. An advisor will be with you in a moment.” |
| Annonce d'enregistrement (`enregistrement.mp3`) | après l'accueil, et quand le client décroche un appel de l'entreprise, si l'enregistrement est activé (Odoo) | environ 4 s ; 8 s au plus avec les deux langues | « Pour la qualité de notre service, cet appel est enregistré. » | “To help us improve our service, this call is recorded.” |
| Voix d'attente (`voix/`, une ou plusieurs) | pendant l'attente, par-dessus la musique, toutes les 30 secondes, l'une après l'autre | environ 7 s chacune ; 15 s au plus avec les deux langues | « Merci de patienter, un conseiller va vous répondre dans un instant. » ; une deuxième : « Tous nos conseillers sont occupés. Merci de rester en ligne, votre appel est important pour nous. » | “Thank you for holding, an advisor will be with you in a moment.” ; a second one: “All our advisors are busy. Please stay on the line, your call is important to us.” |
| Musique d'attente (`attente/`, une ou plusieurs) | la musique d'attente (facultatif : sinon celle de FreeSWITCH) | 2 à 5 minutes par fichier | une musique libre de droits ou à OCD | (sans paroles) |
| Conseiller coupé (`reconnexion.mp3`) | le conseiller a été coupé | environ 3 s ; 8 s au plus avec les deux langues | « Un instant, nous vous reconnectons à votre conseiller. » | “One moment please, we are reconnecting you to your advisor.” |
| Messagerie (`messagerie.mp3`) | personne de disponible | environ 8 s ; 15 s au plus avec les deux langues | « Nos conseillers sont tous occupés. Laissez votre message après le bip : nous vous rappelons dès que possible. » | “All our advisors are busy. Please leave your message after the beep, and we will call you back as soon as possible.” |
| Personne de disponible (`indisponible.mp3`) | personne, et pas de messagerie | environ 8 s ; 15 s au plus avec les deux langues | « Nos conseillers sont tous occupés. Écrivez-nous sur WhatsApp, à ce même numéro : nous vous répondons rapidement. » | “All our advisors are busy. Send us a message on WhatsApp, at this same number, and we will reply quickly.” |

**En deux langues** : chaque message est un seul fichier par numéro. Pour des clients francophones et
anglophones, enregistrer les deux phrases dans le même fichier, le français d'abord, puis l'anglais
(par ex. « Bonjour et bienvenue chez OCD Live… » puis “Hello and welcome to OCD Live…”), avec une courte
pause entre les deux. Le client attend pendant qu'un message passe : rester sous la durée « au plus »
(sinon raccourcir le texte, ou garder une seule langue). Odoo mesure la durée de chaque fichier donné
(colonne « Durée (s) ») et la signale en orange au-delà ; le formulaire du message rappelle la durée
conseillée.

Sans fichier : une tonalité courte pour l'accueil et les messages, rien pour la voix d'attente, et
l'appel enregistré sans annonce (le journal le signale : « recorded without telling the customer »).

**L'attente** : les fichiers de `attente/` passent l'un après l'autre, dans l'ordre de leur nom, en
boucle (par ex. `1-musique.mp3`, `2-musique.mp3`) ; ceux de `voix/` passent par-dessus, toutes les
`OCD_HOLD_VOICE_EVERY` secondes (30 par défaut, dans `.env`). Le flux est le même pour tous les clients
qui attendent (comme une radio) : un client entend la voix au plus 30 secondes après son arrivée.
`docker compose logs freeswitch` dit « Music while waiting: the files of sounds/attente » et « Voice
while waiting: the files of sounds/voix, every 30 s ».

Après avoir posé ou changé des fichiers : `docker compose up -d --force-recreate freeswitch` (quand
personne n'est en appel).
Les fichiers copiés depuis Windows : la correction des fins de ligne (partie 3A) laisse de côté les
`.wav` et les `.mp3` ; sinon elle les abîmerait.

**Enregistrer la voix** : un téléphone suffit (pièce calme, à 20 cm, voix posée) ; ou une voix off
(comédien, service de voix de synthèse dont la licence permet l'usage commercial). Le MP3 est pris tel
quel ; un autre format : `ffmpeg -i accueil.m4a accueil.mp3`.

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
- Les lignes `[ocd]` du journal de FreeSWITCH viennent des scripts d'OCD. Chaque appel de Meta en
  donne trois : `call of +237... to +228..., phone number id ..., wacid ..., from <IP de Meta>, signed
  as <nom de la signature>`, puis `answered: codec opus, SRTP AES_CM_128_HMAC_SHA1_80`, et à la fin
  `end: completed, ended by customer, cause ...`. Quand le client raccroche, FreeSWITCH l'écrit aussi :
  `sofia.c:... Hangup sofia/ocd_whatsapp/... [NORMAL_CLEARING]` (le « BYE » de Meta est arrivé) ;
  quand le conseiller raccroche : `end: ..., hang-up sent to Meta`.

  ```bash
  docker compose logs --since 30m freeswitch | grep -aE "\[ocd\]|Hangup|BYE|TIMEOUT"
  ```

- **Le conseiller décroche, et ça resonne** (ou le message « Le relais de la voix du serveur d'appels
  ne répond pas ») : son navigateur ne joint pas coturn (STUN/TURN). Sans lui, le navigateur ne
  donne qu'une adresse masquée (`.local`), que FreeSWITCH refuse (journal : `no suitable candidates
  found`, `INCOMPATIBLE_DESTINATION`) ; avant la version 20.0.1.4.3, le navigateur attendait même
  10 à 40 secondes avant de décrocher (le temps que ses essais en UDP expirent), et le serveur
  refaisait sonner au bout de 20. À regarder :
  `docker compose ps` (coturn « Up »), `docker compose logs --tail 30 coturn`, les ports 3478 (UDP
  et TCP), 5349 (TCP) et 49152-65535 (UDP) ouverts dans le pare-feu du serveur et chez l'hébergeur.
  Depuis le PC du conseiller, la page « Trickle ICE » des exemples WebRTC
  (webrtc.github.io/samples/src/content/peerconnection/trickle-ice/), serveur
  `stun:appels.rollbackk.app:3478`, « Gather candidates » : une ligne `srflx` doit apparaître.
- **La fin d'un appel** : quand Meta dit à Odoo (webhook `calls`) qu'un appel est fini alors que le
  serveur d'appels le croit encore en cours, le téléphone du conseiller raccroche de lui-même, ce qui
  finit l'appel sur le serveur. Il le fait avec la raison `Q.850;cause=31;text="ended at Meta"` :
  le serveur compte alors l'appel fini par le client (pas par le conseiller) et ne fait jamais
  resonner les conseillers pour un client parti ; le diagnostic du téléphone dit « ended at Meta,
  told by Odoo before the call server ». Les deux avis (Meta par Odoo, le serveur par sa ligne)
  arrivent souvent à quelques centaines de millisecondes l'un de l'autre : le premier arrivé coupe le
  téléphone (premier vrai appel de l'entreprise, 23 novembre 2026). La trace SIP montre si les « BYE » passent entre Meta et le serveur :
  `docker compose exec freeswitch fs_cli -x "sofia profile ocd_whatsapp siptrace on"` avant l'appel,
  `... siptrace off` après ; elle est dans `/var/log/freeswitch/freeswitch.log` (elle contient les
  clés de la voix de cet appel : ne pas la laisser allumée).
- Le lien avec Odoo : `docker compose logs ocd-call-sync` dit « users reloaded (N agents) » quand la
  liste des agents change, et Paramètres › WhatsApp › Appels montre le dernier contact du serveur.
  « Odoo does not answer (HTTP Error 401…) » : la clé du `.env` n'est plus celle d'Odoo (« Nouvelle
  clé » cliqué : la recopier). « HTTP Error 403 » : Cloudflare (ou un pare-feu) devant Odoo bloque le serveur d'appels. Il se présente comme
  `ocd-call-sync` et `ocd-call-server` et n'appelle que les adresses `/whatsapp/call/server/` :
  les laisser passer (Cloudflare : Sécurité › WAF, une règle « Ignorer » sur ce chemin ; le « Bot Fight
  Mode » du plan gratuit ne s'ignore pas : le couper).

L'essai de bout en bout (un faux Meta, Odoo, un agent dans Chromium) se rejoue avec
[`tests/e2e/`](tests/e2e/README.md). Les essais au studio avant d'ouvrir à tous sont dans
[`docs/APPELS_WHATSAPP.md`](../../docs/APPELS_WHATSAPP.md).

## Ce qui reste à confirmer avec Meta

Tout le reste a été vu de bout en bout avec un faux Meta qui appelle comme la documentation de Meta le
décrit (TLS, signature, SDES, en-têtes `x-wa-meta-*`). **Premier vrai appel le 21 novembre 2026** :
reçu, signé, décroché dans Odoo, voix dans les deux sens. À la fin, le raccroché du client n'est
arrivé chez le conseiller qu'une minute plus tard, quand il a raccroché lui-même. La cause était chez
nous : sans horloge de la voix (`rtp-timer-name`, présent dans les profils d'exemple de FreeSWITCH,
absent des nôtres), FreeSWITCH attendait la voix du client, qui ne venait plus, et ne lisait pas le
« BYE » de Meta, pourtant arrivé. Corrigé dans la version 20.0.1.4.2 (les deux profils) ; l'essai
`tests/e2e/customer_hangs_up.sh` le vérifie. Avec le vrai Meta, encore à regarder :

- Le nom d'utilisateur que Meta met dans sa signature : sans `+` d'après l'exemple de Meta
  (`username="12145551869"`) ; les deux formes sont créées, la ligne `signed as` du journal le dit.
- Le chiffrement SDES (`srtp_key_exchange_protocol`, dans `calling` et non dans `calling.sip` : vu
  avec le vrai Meta, qui refuse la clé dans `sip`). S'il est refusé à l'appel, passer le compte en DTLS (onglet Appels, `OCD_SRTP=DTLS` avec Docker) et suivre la note de
  `vars_ocd.xml`.
- La signature des appels de Meta : FreeSWITCH la demande par un « 407 », comme dans l'exemple de Meta
  (vu au premier appel : il passe). Si les appels de Meta s'arrêtaient là (`sofia global siptrace on` pour le voir), mettre `auth-calls` à
  `false` dans `sip_profiles/ocd_whatsapp.xml` et n'ouvrir le port 5061 qu'aux adresses de Meta.
- Les adresses IP de Meta pour le SIP, à ajouter au pare-feu du port 5061 si on veut le fermer à tous
  les autres (la signature de chaque appel suffit déjà) : les mêmes que celles des webhooks d'après
  Meta ; la ligne `from` du journal donne celles vues.
- Les heures d'appel sont envoyées comme le tableau de Meta les décrit (`"0700"`, `"2000"`) ; un
  exemple de Meta écrit `"07:00"`. Meta a accepté l'envoi ; pour le voir : WhatsApp Manager › Numéros
  de téléphone › le numéro › Appels, les heures affichées.
- Un client qui cache son numéro derrière un nom d'utilisateur WhatsApp : Meta donne son identifiant
  (BSUID) au lieu du numéro (en-tête `x-wa-meta-user-id`, `from_user_id` du webhook). L'appel va à sa
  conversation (vu avec le faux Meta et dans les tests, pas encore avec un vrai client).
