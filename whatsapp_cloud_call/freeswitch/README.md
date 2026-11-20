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

| Dossier | Contenu | Sur le serveur |
|---|---|---|
| `conf/` | profils SIP (Meta, agents), plan d'appel, domaine, fiches d'appels | `/etc/freeswitch/` |
| `scripts/` | file d'attente (`ocd_whatsapp_inbound.lua`), événements, `ocd/` | `/usr/share/freeswitch/scripts/` |
| `sync/` | `ocd_call_sync.py` et son service systemd | `/usr/local/lib/ocd/`, `/etc/systemd/system/` |
| `tls/` | certificat Let's Encrypt pour FreeSWITCH et coturn | `/usr/local/lib/ocd/`, `/etc/systemd/system/` |
| `coturn/` | relais TURN des agents | `/etc/turnserver.conf` |
| `tests/` | tests sans FreeSWITCH (`python3 -m unittest`, `lua5.3`) | |

## 1. Le serveur

- Debian 12, 2 cœurs, 2 Go de mémoire, IP publique fixe, dans un datacenter (Europe de l'Ouest ou
  Afrique de l'Ouest, au plus près des clients et de l'équipe).
- Un nom, par ex. `appels.ocdlive.com`, qui pointe sur cette IP (enregistrement DNS A).
- Rien d'autre sur ce serveur : coturn y prend le port 443.

Pare-feu (nftables ou celui de l'hébergeur), tout le reste fermé :

| Port | Pour |
|---|---|
| 22/TCP | SSH de l'équipe technique (de ses adresses seulement, si possible) |
| 80/TCP | Let's Encrypt (renouvellement du certificat) |
| 5061/TCP | Meta (SIP sur TLS) |
| 7443/TCP | agents (SIP sur WebSocket sécurisé) |
| 16384-32768/UDP | voix (FreeSWITCH) |
| 3478/UDP+TCP, 443/TCP | relais TURN (coturn) |
| 49152-65535/UDP | voix relayée (coturn) |

Les ports 5070 et 5090 (SIP sans chiffrement des deux profils) et 8021 (event socket) restent
**fermés**.

## 2. FreeSWITCH

Les paquets demandent un compte SignalWire gratuit et un jeton personnel (`pat_...`) : signalwire.com,
créer un espace, puis « Personal Access Tokens ».

```bash
TOKEN=pat_...
apt-get update && apt-get install -y gnupg2 wget lsb-release curl python3 lua5.3
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

### Configuration de base

1. **Sécurité de la configuration de démonstration** : retirer les profils et les utilisateurs
   d'exemple (mots de passe connus de tous).

   ```bash
   cd /etc/freeswitch
   mkdir -p /root/freeswitch-exemple
   mv sip_profiles/internal.xml sip_profiles/external.xml sip_profiles/internal-ipv6.xml \
      sip_profiles/external-ipv6.xml sip_profiles/external sip_profiles/internal /root/freeswitch-exemple/ 2>/dev/null
   mv directory/default.xml directory/default /root/freeswitch-exemple/
   ```

2. **Event socket** (`autoload_configs/event_socket.conf.xml`) : `listen-ip` à `127.0.0.1`, un
   mot de passe long à la place de `ClueCon` (le même dans `/etc/ocd-call-sync.conf`, et pour
   `fs_cli` dans `/root/.fs_cli_conf` : `[default]` puis `password = ...`).
3. **Modules** (`autoload_configs/modules.conf.xml`) : `mod_lua`, `mod_json_cdr` et `mod_opus` chargés
   (décommenter ou ajouter `<load module="mod_json_cdr"/>`).
4. **Ports de la voix** (`autoload_configs/switch.conf.xml`) : `rtp-start-port` 16384,
   `rtp-end-port` 32768.
5. **Adresse publique** (`vars.xml`) : `external_rtp_ip` et `external_sip_ip` à l'IP publique du
   serveur (`stun:stun.freeswitch.org` marche aussi, mais l'IP fixe est plus sûre).

### Les fichiers d'OCD

```bash
SRC=/chemin/vers/projet_ocd/whatsapp_cloud_call/freeswitch
cp $SRC/conf/vars_ocd.xml /etc/freeswitch/
cp $SRC/conf/sip_profiles/*.xml /etc/freeswitch/sip_profiles/
cp $SRC/conf/dialplan/ocd.xml /etc/freeswitch/dialplan/
cp $SRC/conf/directory/ocd.xml /etc/freeswitch/directory/
cp $SRC/conf/autoload_configs/json_cdr.conf.xml /etc/freeswitch/autoload_configs/
cp -r $SRC/scripts/* /usr/share/freeswitch/scripts/
install -d -o freeswitch -g freeswitch -m 750 /etc/freeswitch/directory/ocd /var/lib/freeswitch/ocd \
  /var/spool/ocd-calls /var/spool/ocd-calls/voicemail /var/spool/ocd-calls/cdr-errors
```

- Dans `/etc/freeswitch/vars_ocd.xml` : `ocd_sip_domain` = le nom du serveur.
- À la fin de `/etc/freeswitch/vars.xml` : `<X-PRE-PROCESS cmd="include" data="vars_ocd.xml"/>`.

## 3. Le certificat (Let's Encrypt)

Meta vérifie que le certificat est à ce nom et signé par une autorité reconnue.

```bash
apt-get install -y certbot
install -d /usr/local/lib/ocd
cp $SRC/tls/ocd-freeswitch-certs.sh /usr/local/lib/ocd/ && chmod 750 /usr/local/lib/ocd/ocd-freeswitch-certs.sh
cp $SRC/tls/ocd-freeswitch-certs.service $SRC/tls/ocd-freeswitch-certs.timer /etc/systemd/system/
certbot certonly --standalone -d appels.ocdlive.com \
  --deploy-hook "/usr/local/lib/ocd/ocd-freeswitch-certs.sh copy"
/usr/local/lib/ocd/ocd-freeswitch-certs.sh copy
systemctl daemon-reload && systemctl enable --now ocd-freeswitch-certs.timer
```

Au renouvellement (tous les 2 mois environ), le certificat est copié, puis appliqué la nuit suivante à
un moment sans appel (un redémarrage des profils couperait les appels en cours).

Vérifier depuis un autre poste :

```bash
openssl s_client -quiet -verify_hostname appels.ocdlive.com -connect appels.ocdlive.com:5061
```

## 4. Le lien avec Odoo (ocd-call-sync)

1. Dans Odoo, **Paramètres › WhatsApp › Appels** : l'adresse du serveur d'appels, puis copier la
   **clé du serveur d'appels**.
2. Sur le serveur :

   ```bash
   cp $SRC/sync/ocd_call_sync.py /usr/local/lib/ocd/
   cp $SRC/sync/ocd-call-sync.conf.example /etc/ocd-call-sync.conf
   chown freeswitch:freeswitch /etc/ocd-call-sync.conf && chmod 600 /etc/ocd-call-sync.conf
   nano /etc/ocd-call-sync.conf   # odoo_url, token (la clé), fs_password (event socket)
   cp $SRC/sync/ocd-call-sync.service /etc/systemd/system/
   systemctl daemon-reload && systemctl enable --now ocd-call-sync
   systemctl restart freeswitch
   journalctl -u ocd-call-sync -f
   ```

Toutes les 30 secondes, il dit à Odoo que le serveur tourne (et quels agents sont connectés), recopie
les agents et leurs mots de passe, et renvoie à Odoo les messages et les fiches d'appels restés en
attente. Odoo arrêté : la dernière copie reste, les appels sonnent chez les agents copiés. Dans
Odoo, « Dernier signe » (Paramètres › WhatsApp › Appels) se met à jour ; sans signe pendant
5 minutes, les responsables WhatsApp sont prévenus.

## 5. Le relais TURN (coturn)

Pour les agents dont le réseau bloque la voix (UDP) : elle passe alors en TCP ou en TLS sur le
port 443.

```bash
apt-get install -y coturn
cp $SRC/coturn/turnserver.conf /etc/turnserver.conf
SECRET=$(openssl rand -hex 32); sed -i "s/CHANGE-ME/$SECRET/; s/calls.example.com/appels.ocdlive.com/" /etc/turnserver.conf
echo $SECRET   # à saisir dans Odoo : Paramètres › WhatsApp › Appels › Secret du relais TURN
install -d -o turnserver -g turnserver /etc/coturn
/usr/local/lib/ocd/ocd-freeswitch-certs.sh copy
systemctl enable --now coturn
```

Le service coturn de Debian a le droit d'ouvrir le port 443 ; sinon, ajouter
`AmbientCapabilities=CAP_NET_BIND_SERVICE` à son service (`systemctl edit coturn`).

## 6. Les messages enregistrés

Dans `/usr/share/freeswitch/sounds/ocd/` (WAV, mono, 16 kHz ; la voix de l'équipe, en français) :

| Fichier | Quand | Exemple |
|---|---|---|
| `accueil.wav` | dès que l'appel arrive | « Bonjour, bienvenue chez OCD Live, un conseiller va vous répondre. » |
| `reconnexion.wav` | le conseiller a été coupé | « Un instant, nous vous reconnectons. » |
| `messagerie.wav` | personne de disponible | « Nos conseillers sont occupés. Laissez votre message après le bip, nous vous rappelons. » |
| `indisponible.wav` | personne, et pas de messagerie | « Nos conseillers sont occupés. Écrivez-nous sur WhatsApp, nous vous répondons vite. » |

Sans fichier, une tonalité courte le remplace. La musique d'attente est celle de FreeSWITCH
(`local_stream://moh`, paquet `freeswitch-music-default`).

Convertir un enregistrement : `ffmpeg -i accueil.m4a -ac 1 -ar 16000 accueil.wav`.

## 7. Chez Meta

1. Dans l'app Meta, **WhatsApp › Configuration › Webhook** : s'abonner aussi au champ **calls**.
2. Dans Odoo, **WhatsApp › Configuration › Comptes**, le compte, onglet **Appels** : cocher
   « Appels », vérifier les heures (onglet Équipe), puis **Envoyer les appels à Meta**. Odoo envoie
   les réglages (serveur SIP, chiffrement SDES, heures, icône), puis relit l'état et le mot de passe SIP
   donné par Meta. « Activés chez Meta » : c'est prêt ; une limite de Meta s'affiche en rouge.
3. Dans la minute, ocd-call-sync recopie le mot de passe de Meta sur le serveur.

## 8. Vérifier

- `fs_cli -x "sofia status"` : profils `ocd_whatsapp` (5061, TLS) et `ocd_agents` (7443, WSS) en
  `RUNNING`.
- Un agent dans Odoo, téléphone de la barre du haut, « Je prends les appels » : point vert.
  `fs_cli -x "sofia status profile ocd_agents reg"` le montre.
- Test du micro et du réseau d'un poste : depuis un logiciel SIP connecté avec les identifiants d'un
  agent, appeler `*9196` (la voix revient).
- Un vrai appel depuis WhatsApp sur un téléphone (pas WhatsApp Web) : il sonne chez l'agent ; il
  apparaît dans **WhatsApp › Appels** et dans la conversation du client.
- `fs_cli -x "console loglevel debug"` puis `fs_cli` pour suivre un appel ; les lignes `[ocd]`
  viennent des scripts d'OCD.

Les essais avant d'ouvrir à tous (coupure du Wi-Fi, Odoo arrêté, serveur arrêté...) sont dans
[`docs/APPELS_WHATSAPP.md`](../../docs/APPELS_WHATSAPP.md).

## Ce qui reste à confirmer avec le vrai serveur

Ces points suivent la documentation de Meta, mais n'ont pas encore été vus avec un vrai appel :

- Le nom d'utilisateur que Meta met dans sa signature (le numéro avec ou sans `+`) : les deux sont
  créés.
- Le chiffrement SDES (`srtp_key_exchange_protocol`) : Meta le décrit comme à activer. S'il est
  refusé, passer le compte en DTLS (onglet Appels) et suivre la note de `vars_ocd.xml`.
- La signature des appels de Meta : FreeSWITCH la demande par un « 407 » (Meta dit accepter le « 401 »).
  Si les appels de Meta s'arrêtent là (`sofia global siptrace on` pour le voir), mettre `auth-calls` à
  `false` dans `sip_profiles/ocd_whatsapp.xml` et n'ouvrir le port 5061 qu'aux adresses de Meta.
- Les adresses IP de Meta pour le SIP, à ajouter au pare-feu du port 5061 si on veut le fermer à tous
  les autres (la signature de chaque appel suffit déjà).
