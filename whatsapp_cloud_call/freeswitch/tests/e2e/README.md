# Essai de bout en bout des appels WhatsApp

Un vrai appel, sans Meta : un **faux Meta** (FreeSWITCH, l'image du serveur d'appels lancée autrement)
appelle le serveur d'appels comme Meta le fait (SIP sur TLS au port 5061, signé avec le numéro et le
mot de passe SIP de Meta, voix en SDES, numéro du client dans `From`, en-têtes `x-wa-meta-*`). Le
serveur demande à Odoo qui faire sonner, les agents décrochent dans Odoo (Chromium, le vrai téléphone
de la barre du haut, WebRTC), l'appel est vérifié dans Odoo.

| Fichier | Rôle |
|---|---|
| `fake_meta/entrypoint.sh` | démarre l'image du serveur d'appels en faux Meta (port 5081, socket d'événements 8022, voix 40000-41000) |
| `fake_meta/meta.xml` | son profil, avec la passerelle vers le serveur d'appels |
| `fake_meta/meta_call.lua` | le client : envoie une tonalité de 440 Hz, enregistre ce qu'il entend, raccroche au bout de N secondes |
| `agent_calls.js` | les deux scénarios dans Chromium (Playwright) |
| `fake_agent/` | un faux conseiller (l'image en SIP simple sur le port 5090), qui décroche et envoie une tonalité |
| `company_calls.js` | l'entreprise appelle : le conseiller appelle le client depuis Chromium, le serveur vérifie avec Odoo, appelle le faux Meta (passerelle TLS) ; un appel non préparé est refusé |
| `fake_meta/customer.xml` | le client que l'entreprise appelle : décroche, envoie une tonalité, enregistre ce qu'il entend |
| `customer_hangs_up.sh` | sans Odoo : le client raccroche pendant qu'il parle au conseiller ; le serveur et le conseiller doivent le voir aussitôt |

## Préparer

1. Une base Odoo avec `whatsapp_cloud_call`, lancée (ex. port 8079), où :
   - Paramètres › WhatsApp › Appels : adresse `calls.ocd.test`, une clé, un secret TURN ;
   - un compte WhatsApp avec appels, ID du numéro `1110001`, numéro `+228 90 00 00 01`, mot de passe
     SIP de Meta `meta-test-pw` (champ « Mot de passe SIP de Meta », en mode développeur ou par
     `odoo shell`), sans heures d'ouverture ;
   - deux agents (ex. `admin` et `kossi`), et un contact `+237 670000000` (le client).
2. Un certificat de test pour `calls.ocd.test` (une autorité de test et `openssl`), dans un dossier
   `certs/` : `agent.pem` (certificat, chaîne et clé), `cafile.pem`, `fullchain.pem`, `privkey.pem`.
3. `calls.ocd.test` vers l'IP de la machine dans `/etc/hosts` (pas 127.0.0.1 : FreeSWITCH écoute
   sur l'IP de la machine).
4. La pile du serveur d'appels (`docker/`), avec dans `.env` : `OCD_SIP_DOMAIN=calls.ocd.test`,
   `EXTERNAL_IP=<IP de la machine>`, `OCD_ODOO_URL=http://127.0.0.1:8079`, la clé, `OCD_CERTS_DIR=<certs>`,
   `OCD_AGENT_CANDIDATE_ACL=localnet.auto` (les agents sont sur la même machine), puis
   `docker compose up -d`.
5. Le faux Meta :

   ```bash
   docker run -d --name fake-meta --network host -e META_PASSWORD=meta-test-pw \
     -e OCD_TEST_PROXY=<IP de la machine>:5061 \
     -v <certs>:/run/ocd-certs:ro -v $PWD/fake_meta:/opt/fake_meta:ro -v /tmp/meta:/tmp/meta \
     --entrypoint /opt/fake_meta/entrypoint.sh ocd-freeswitch:1.11.3-ocd1
   ```

## Lancer

```bash
SERVER_CONTAINER=ocd-calls-freeswitch-1 OCD_URL=http://127.0.0.1:8079 META_RECORDINGS=/tmp/meta node agent_calls.js
```

1. **Appel pris** : l'agent prend les appels, le client appelle, le téléphone sonne avec le nom du
   client, l'agent décroche (Odoo : en cours), la voix passe dans les deux sens (paquets et niveau
   dans le navigateur, et enregistrement du faux Meta), l'agent raccroche (Odoo : fini par l'agent,
   durée, ligne dans la conversation).
2. **Agent coupé** : un deuxième agent prend aussi les appels ; le premier décroche, puis sa page se
   ferme sans raccrocher (réseau perdu) ; le collègue sonne quelques secondes après, décroche,
   entend le client, raccroche (Odoo : fini par le collègue, une coupure).

Un message laissé (personne de connecté) : `docker exec fake-meta fs_cli -x "bgapi originate
{meta_name=vm1,meta_seconds=50,sip_h_x-wa-meta-wacid=wacid.VM1,sip_h_x-wa-meta-phone-number-id=1110001,origination_caller_id_number=+237670000000,rtp_secure_media=mandatory:AES_CM_128_HMAC_SHA1_80,absolute_codec_string=OPUS}sofia/gateway/ocd/+22890000001
&lua(/opt/fake_meta/meta_call.lua)"` : au bout de 30 secondes la messagerie, le message dans la
conversation (environ 18 secondes de tonalité).

## L'entreprise appelle le client

Avec `OCD_META_SIP=<IP de la machine>:5081` dans le `.env` du serveur d'appels (sa passerelle vers Meta
va au faux Meta ; à ne jamais mettre en production), puis :

```bash
OCD_URL=http://127.0.0.1:8079 ODOO_DB=e2e META_RECORDINGS=/tmp/meta node company_calls.js
```

L'appel préparé par Odoo (après les vérifications de Meta, testées dans les tests d'Odoo) est écrit
avec psql : l'API de Meta n'est pas jointe dans cet essai.

## Le client raccroche pendant la conversation

Sans Odoo ni navigateur, avec l'image du serveur d'appels déjà construite :

```bash
CERTS=<certs> IP=<IP de la machine> sh customer_hangs_up.sh
```

Les trois heures affichées (le client raccroche, le serveur le voit, le conseiller le voit) doivent
être à quelques millisecondes l'une de l'autre. Avant la version 20.0.1.4.2, sans l'horloge de la
voix (`rtp-timer-name`) dans les profils, le serveur le voyait 5 secondes plus tard avec ce faux Meta,
et avec le vrai Meta seulement quand le conseiller raccrochait à son tour (premier vrai appel, le
21 novembre 2026).

## Ce qui a été vu le 21 novembre 2026

Sur cette pile (FreeSWITCH 1.11.3 compilé dans l'image, ocd-call-sync, coturn 4.18, Odoo 20) : les
deux scénarios sans échec, la messagerie, un appel pris pendant qu'Odoo était arrêté (sa fiche
arrivée dans Odoo à son retour, par ocd-call-sync), le relais TURN avec les identifiants donnés par
Odoo (refusés avec un mauvais secret), le renouvellement du certificat (attendu pendant un appel,
appliqué après).
