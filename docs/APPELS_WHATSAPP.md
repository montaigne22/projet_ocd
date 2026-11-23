# Appels WhatsApp : feuille de route

Les clients appellent OCD Live depuis WhatsApp (l'icône du téléphone dans la conversation), sur le même
numéro que les messages. L'équipe décroche dans Odoo, dans son navigateur. Plusieurs appels en même temps
sur le numéro, une file d'attente quand tout le monde est pris, l'historique dans la conversation.

Choix du 20 novembre 2026 : **la solution la plus robuste**, un serveur d'appels FreeSWITCH entre Meta et
l'équipe, piloté par Odoo. Le détail des options écartées est en fin de page.

## Comment ça marche

```
Client WhatsApp
      │  (appli WhatsApp : WhatsApp Web ne prend pas les appels vers une entreprise)
      ▼
Meta (wa.meta.vc)
      │  SIP sur TLS (port 5061), voix chiffrée (SRTP), Opus
      ▼
Serveur d'appels OCD : FreeSWITCH, IP publique, certificat Let's Encrypt
      │  file d'attente, musique, sonnerie des agents, reprise d'un appel coupé, messagerie
      │  SIP sur WebSocket sécurisé (WSS, port 7443), WebRTC, Opus
      ▼
Navigateur de l'agent : Odoo, le téléphone dans la barre du haut

Odoo ◄── FreeSWITCH : qui faire sonner, appel pris, fini, message laissé (HTTPS)
Odoo ──► Meta        : appels activés, serveur SIP, heures d'appel (Graph API)
Odoo ◄── Meta        : appel tenté, appel fini (webhook « calls ») : un appel que le serveur n'a pas vu
```

- **La voix ne passe jamais par Odoo.** Un redémarrage d'Odoo ne coupe aucun appel.
- **Le lien avec Meta part du serveur**, dont la connexion est stable : Meta ne reconnecte pas un appel
  côté entreprise, c'est le point le plus fragile quand on décroche directement dans le navigateur.
- **Le serveur continue sans Odoo** : il garde la dernière liste des agents et leurs mots de passe
  (recopiée chaque minute) ; si Odoo ne répond pas, il fait sonner tous les agents connectés.
- **Odoo voit les appels que le serveur n'a pas vus** : Meta envoie aussi « appel tenté » et « appel fini »
  au webhook. Un appel sans nouvelle du serveur est noté « perdu », les responsables sont prévenus.

## Phase 0 : les préalables (équipe OCD, avant tout code en production)

| # | Quoi | Qui | Bloquant |
|---|---|---|---|
| 0.1 | **Limite d'envoi du numéro ≥ 2 000 destinataires par jour** (WhatsApp › Comptes, « Limite d'envoi » : `TIER_2K` ou plus). Sans elle, Meta n'active pas les appels | Équipe | Oui |
| 0.2 | Moyen de paiement ou ligne de crédit sur le compte WhatsApp Business (Meta Business Suite) | Équipe | Oui |
| 0.3 | Droits et réglages chez Meta : jeton de l'utilisateur système avec ses trois autorisations, app Meta en mode « Live » (exigé pour le SIP), webhook abonné au champ `calls` ; pas à pas : [`APPELS_WHATSAPP_META.md`](APPELS_WHATSAPP_META.md) | Équipe | Oui |
| 0.4 | Vérifier que le Togo et le Cameroun sont dans la liste des pays de Meta pour les appels | Équipe | Oui |
| 0.5 | Un serveur (VPS) Debian 12, 2 cœurs, IP publique fixe, dans un datacenter proche (Europe de l'Ouest ou Afrique) ; un nom, par ex. `appels.rollbackk.app` | Équipe | Oui |
| 0.6 | Ports ouverts sur ce serveur : 5061/TCP (Meta), 7443/TCP (agents), 16384-29999/UDP (voix), 3478/UDP+TCP et 443/TCP, ou 5349/TCP quand Traefik ou nginx tient le 443 (relais TURN), 49152-65535/UDP (voix relayée) | Équipe | Oui |
| 0.7 | Docker sur le serveur (conseillé : FreeSWITCH compilé dans l'image, sans compte), sinon un compte SignalWire gratuit pour les paquets | Équipe | Oui |
| 0.8 | Trois messages enregistrés (voix de l'équipe, français) : accueil, attente, messagerie | Équipe | Non (une tonalité sinon) |

## Phase 1 : les clients appellent OCD (fait dans ce dépôt)

Module `whatsapp_cloud_call` (générique, comme `whatsapp_cloud`) et dossier
`whatsapp_cloud_call/freeswitch/` (configuration du serveur, installation pas à pas dans son
[`README.md`](../whatsapp_cloud_call/freeswitch/README.md)).

| # | Chantier | Ce que c'est |
|---|---|---|
| 1.1 | **Réglages des appels chez Meta** | Sur le compte WhatsApp, onglet « Appels » : appels activés, icône visible, heures d'appel (celles de l'équipe, jours fériés compris), serveur SIP, chiffrement SDES, webhook des appels ; « Envoyer à Meta », « Lire l'état chez Meta » (restrictions de Meta montrées) ; le mot de passe SIP donné par Meta, gardé pour le serveur |
| 1.2 | **Le serveur d'appels** | FreeSWITCH : la liaison avec Meta (TLS, mot de passe de Meta demandé à chaque appel), les agents en WebRTC, la file d'attente en Lua : musique, tous les agents libres sonnent ensemble, le premier qui décroche prend l'appel |
| 1.3 | **Rien ne se perd** | Agent coupé (réseau, onglet fermé) : le client reste en ligne, entend « nous vous reconnectons », l'appel revient d'abord à cet agent puis aux autres ; 3 minutes sans agent ou personne en ligne : messagerie (2 minutes), le message arrive dans la conversation comme un message vocal |
| 1.4 | **Odoo pilote, le serveur tient seul** | Odoo dit qui faire sonner (l'agent de la conversation d'abord, puis les moins chargés) et le nom du client ; s'il ne répond pas en 2 secondes, le serveur fait sonner tous les agents connectés. La liste des agents et leurs mots de passe sont recopiés chaque minute sur le serveur |
| 1.5 | **Le téléphone dans Odoo** | Barre du haut : « Je prends les appels » ou non, la sonnerie, le nom du client et sa conversation, Décrocher, Refuser, Couper le micro, Raccrocher, la durée ; deuxième appel refusé (« occupé ») pendant un appel ; avertissement avant de quitter la page pendant un appel ; reconnexion automatique |
| 1.6 | **L'historique** | Chaque appel : qui, quand, attente, durée, agent, fin (fini, manqué, messagerie, perdu) ; une ligne dans la conversation (« Appel de 3 min 12 s, pris par Awa ») ; appel manqué ou message laissé : la conversation attend une réponse, avec les rappels et l'escalade de `whatsapp_cloud` ; l'agent qui décroche prend la conversation |
| 1.7 | **Surveillance** | Le serveur se signale chaque minute : sans nouvelle depuis 5 minutes, les responsables sont prévenus ; un appel vu par Meta et pas par le serveur est « perdu » et signalé ; le dernier contact du serveur et les agents connectés sur la fiche du compte |
| 1.8 | **Relais TURN** | coturn sur le serveur, ports 3478 et 443 (ou 5349 à côté de Traefik) : la voix passe même quand le réseau du studio bloque l'UDP ; des identifiants de 12 h donnés par Odoo à chaque agent |
| 1.9 | **Docker** | `docker compose` : FreeSWITCH 1.11.3 compilé depuis ses sources dans l'image (aucun compte), ocd-call-sync (socket d'événements de FreeSWITCH), coturn ; réseau du serveur ; santé de chaque conteneur ; certificat renouvelé la nuit sans couper d'appel |
| 1.10 | **Veille du conseiller** | Pendant une conversation, le conseiller est-il toujours connecté ? Page fermée ou réseau tombé : au bout de 9 secondes l'appel passe aux collègues (FreeSWITCH seul ne le remarque pas toujours) |

**Vu de bout en bout le 21 novembre 2026** (sans Meta : un faux Meta qui appelle comme Meta le décrit,
la vraie pile Docker, Odoo, des agents dans Chromium) : appel pris et raccroché, voix dans les deux
sens ; agent coupé (page fermée), le collègue sonne 8 secondes après ; messagerie ; appel pris pendant
qu'Odoo était arrêté, sa fiche arrivée dans Odoo à son retour ; relais TURN avec les identifiants
d'Odoo ; renouvellement du certificat. Rejouable : `whatsapp_cloud_call/freeswitch/tests/e2e/`.

**Premier vrai appel le 21 novembre 2026** (un client, l'appli WhatsApp, serveur `appels.rollbackk.app`) :
reçu de Meta, signé, décroché dans Odoo, voix dans les deux sens. À la fin, le raccroché du client
n'est arrivé chez le conseiller qu'une minute plus tard : le serveur d'appels ne lisait pas le « BYE »
de Meta tant que la voix du client ne venait plus (profils sans horloge de la voix). Corrigé dans la
version 20.0.1.4.2, vérifié avec un faux Meta et un faux conseiller ; en plus, le téléphone du
conseiller raccroche quand Meta dit à Odoo que l'appel est fini. À revoir au prochain vrai appel.

**Essai avant d'ouvrir à tous** (2 semaines au studio de Lomé, quelques clients). Chaque essai depuis
l'appli WhatsApp d'un téléphone (pas WhatsApp Web), pendant les heures d'appel. Après chacun : la fiche
de l'appel (WhatsApp › Appels) et le journal du serveur d'appels, dans `/home/ubuntu/freeswitch/docker` :
`docker compose logs --since 15m freeswitch | grep -aE "\[ocd\]|Hangup"`.

| # | Essai | Comment | Ce qu'on doit voir |
|---|---|---|---|
| 1 | Appel simple | Un conseiller décroche, parle 30 s, raccroche. Puis un 2e appel où le client raccroche | L'appel se coupe aussitôt de l'autre côté, les deux fois. Fiche : « Fini », durée, « Fini par » conseiller puis client ; une ligne dans la conversation. Journal : `end: completed, ended by agent` puis `ended by customer` |
| 2 | Trois appels, deux conseillers | Trois téléphones appellent à la suite ; les deux conseillers décrochent les deux premiers | Le 3e entend la musique d'attente, puis sonne chez le premier conseiller qui raccroche. Fiche du 3e : attente, pris par |
| 3 | Wi-Fi du conseiller coupé | Pendant l'appel, le conseiller coupe son Wi-Fi 20 s (ou ferme l'onglet) | Le client entend « nous vous reconnectons » ; l'appel revient au conseiller s'il revient dans les 30 s, sinon sonne chez un collègue (8 à 9 s après). Fiche : « Conseiller coupé » 1. Journal : `cut off (...)` |
| 4 | Odoo arrêté | En heure creuse, Odoo arrêté 2 minutes (k3s : son déploiement à 0), puis un appel | L'appel sonne quand même chez les conseillers connectés (journal : `Odoo did not answer`). Au retour d'Odoo, la fiche de l'appel arrive (copiée par ocd-call-sync) |
| 5 | Serveur d'appels arrêté | `docker compose stop freeswitch`, un appel, puis `docker compose start freeswitch` | L'appel n'aboutit pas chez le client. Dans Odoo, il passe « Perdu » au bout de 10 minutes et les responsables sont prévenus ; le silence du serveur est aussi signalé au bout de 5 minutes |
| 6 | Personne de disponible | Tous les conseillers décochent « Je prends les appels », un appel | Accueil, puis la messagerie au bout de 30 s ; le message arrive dans la conversation, qui attend une réponse. Fiche : « Messagerie » |
| 7 | Réseau qui bloque l'UDP | Sur le PC du conseiller (PowerShell administrateur) : `New-NetFirewallRule -DisplayName "Essai OCD UDP" -Direction Outbound -Protocol UDP -RemotePort 1-52,54-65535 -Action Block`, un appel, puis `Remove-NetFirewallRule -DisplayName "Essai OCD UDP"` | La voix passe dans les deux sens, par le relais. « Diagnostic du téléphone » de la fiche : `address relay tcp`, `answer sent (relay)`, `established` |

**Seuils pour ouvrir** : moins de 2 % d'appels coupés, moins de 5 % de messageries quand un conseiller
est libre, attente moyenne sous 1 minute pendant les heures d'appel. Odoo les calcule sur les 14 derniers
jours : compte WhatsApp, onglet Appels, « Seuils pour ouvrir les appels à tous » (vert quand le seuil est
tenu). Le détail : WhatsApp › Appels, vues graphique et tableau croisé (par conseiller, par jour).

- Appels coupés : les appels perdus ou en échec, et ceux où le conseiller a été coupé (même si l'appel
  est revenu).
- Messagerie alors qu'un conseiller était libre : chaque appel note les conseillers libres à son arrivée
  et s'il tombe pendant les heures d'appel.
- Attente moyenne : celle des appels pris pendant les heures d'appel.

## Phase 2 : OCD appelle les gens (payant, avec leur accord)

| # | Chantier | Ce que c'est |
|---|---|---|
| 2.1 | **Accord du client** | « Demander l'accord pour appeler » dans la conversation (message de Meta, dans les 24 h) ou un modèle ; la réponse notée sur le contact (7 jours ou pour toujours) ; les limites de Meta respectées (1 demande par 24 h, 2 par 7 jours) |
| 2.2 | **Rappeler** | « Rappeler » sur un appel manqué ou coupé : l'accord est donné par Meta quand le client a appelé (rappel de l'appel) ; le serveur appelle par `wa.meta.vc` |
| 2.3 | **Le livreur appelle le client** | Depuis sa tournée, par le numéro d'OCD : le livreur ne voit pas le numéro du client ; les 2 appels avant « absent » comptés |
| 2.4 | **L'animatrice appelle le vendeur** | 30 minutes avant un live à distance |
| 2.5 | **Coût** | Durée facturée par tranches de 6 s selon le pays appelé, rapport mensuel ; pas vers le Nigeria, les États-Unis, le Canada, l'Égypte, le Vietnam (refusés par Meta) |

**2.1 fait (version 20.0.1.6.0)** : dans la conversation, panneau « Client », partie « Appeler le
client » : l'état de l'accord (pas demandé, demandé, accordé jusqu'au…, accordé, refusé) et le bouton
« Demander l'accord pour appeler ». Odoo lit d'abord l'état chez Meta (un client qui vient d'appeler a
déjà donné son accord pour 7 jours : rien n'est envoyé) et ses limites (1 demande par 24 h, 2 par
7 jours, remises à zéro par un appel), puis envoie le message de Meta (boutons Autoriser / Refuser),
seulement dans les 24 h qui suivent un message du client. La réponse du client est notée sur la
conversation, avec une ligne pour l'équipe ; elle ne compte pas comme un message à traiter. WhatsApp
retire l'accord après 4 appels sans réponse : noté aussi. À venir : la demande par un modèle (hors des
24 h), à faire approuver par Meta.

Ce que dit Meta pour la suite (novembre 2026) : un appel de l'entreprise part du serveur d'appels vers
`sip:+<numéro du client>@wa.meta.vc` (TLS), signé avec le numéro de l'entreprise (sans `+`) et le mot de
passe SIP de Meta ; 100 appels aboutis au plus par 24 h ; 2 appels sans réponse d'affilée : WhatsApp
propose au client de retirer son accord, 4 : il le retire. Facturation par tranches de 6 secondes
(une tranche commencée est due), selon le pays du client ; les appels des clients restent gratuits.

## Phase 3 : la qualité

| # | Chantier | Ce que c'est |
|---|---|---|
| 3.1 | **Enregistrement** | Annoncé au client, gardé 30 jours, écouté par les responsables ; à valider avec le cadre légal du pays |
| 3.2 | **Chiffres** | Appels par jour et par heure, attente, manqués, durée par agent, sur le tableau de bord |
| 3.3 | **Transfert** | Passer l'appel à un collègue |
| 3.4 | **Deuxième serveur** | Une deuxième machine derrière le même nom, si les appels deviennent critiques |

## Options écartées

- **Décrocher directement dans le navigateur** (sans serveur, par l'API de Meta) : moins de choses à
  faire tourner, mais un agent qui change de réseau coupe l'appel, et aucune file d'attente : au-delà
  des agents libres, l'appel sonne dans le vide jusqu'à « sans réponse » (30 à 60 s).
- **Asterisk** : aussi solide, mais retiré de Debian 12, donc compilé à la main et plus lourd à mettre à
  jour.
- **Kubernetes** : la voix demande des milliers de ports UDP et l'IP publique fixe du serveur, et
  déplacer un pod coupe les appels en cours ; Docker sur un serveur dédié garde la mise à jour simple
  sans ces défauts.
- **Un service payant (Twilio et autres)** : plus d'abonnement, et la voix des clients chez un tiers.
