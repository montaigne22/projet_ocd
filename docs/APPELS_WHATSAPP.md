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
| 0.3 | Droits chez Meta : jeton de l'utilisateur système avec `whatsapp_business_messaging` et `whatsapp_business_management` (déjà pour les messages), `whatsapp_business_management` en **accès avancé** dans l'app (sinon Meta ne donne pas le mot de passe SIP), webhook abonné au champ **`calls`** ; détail pas à pas : [guide du serveur, section 6](../whatsapp_cloud_call/freeswitch/README.md#6-chez-meta--les-droits-et-les-réglages-à-activer) | Équipe | Oui |
| 0.4 | Vérifier que le Togo et le Cameroun sont dans la liste des pays de Meta pour les appels | Équipe | Oui |
| 0.5 | Un serveur (VPS) Debian 12, 2 cœurs, IP publique fixe, dans un datacenter proche (Europe de l'Ouest ou Afrique) ; un nom, par ex. `appels.ocdlive.com` | Équipe | Oui |
| 0.6 | Ports ouverts sur ce serveur : 5061/TCP (Meta), 7443/TCP (agents), 16384-32768/UDP (voix), 3478 et 443 (relais TURN) | Équipe | Oui |
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
| 1.8 | **Relais TURN** | coturn sur le serveur, ports 3478 et 443 : la voix passe même quand le réseau du studio bloque l'UDP ; des identifiants de 12 h donnés par Odoo à chaque agent |
| 1.9 | **Docker** | `docker compose` : FreeSWITCH 1.11.3 compilé depuis ses sources dans l'image (aucun compte), ocd-call-sync (socket d'événements de FreeSWITCH), coturn ; réseau du serveur ; santé de chaque conteneur ; certificat renouvelé la nuit sans couper d'appel |
| 1.10 | **Veille du conseiller** | Pendant une conversation, le conseiller est-il toujours connecté ? Page fermée ou réseau tombé : au bout de 9 secondes l'appel passe aux collègues (FreeSWITCH seul ne le remarque pas toujours) |

**Vu de bout en bout le 21 novembre 2026** (sans Meta : un faux Meta qui appelle comme Meta le décrit,
la vraie pile Docker, Odoo, des agents dans Chromium) : appel pris et raccroché, voix dans les deux
sens ; agent coupé (page fermée), le collègue sonne 8 secondes après ; messagerie ; appel pris pendant
qu'Odoo était arrêté, sa fiche arrivée dans Odoo à son retour ; relais TURN avec les identifiants
d'Odoo ; renouvellement du certificat. Rejouable : `whatsapp_cloud_call/freeswitch/tests/e2e/`.

**Essai avant d'ouvrir à tous** (2 semaines au studio de Lomé, quelques clients) :

1. Appel simple, décroché, raccroché par l'agent puis par le client.
2. Trois appels en même temps avec deux agents : le troisième attend, puis passe au premier libre.
3. Coupure du Wi-Fi de l'agent pendant l'appel : le client entend « nous vous reconnectons », l'appel
   revient.
4. Odoo arrêté : un appel sonne quand même chez les agents connectés ; à son retour, l'appel est dans
   l'historique.
5. Serveur d'appels arrêté : l'appel est « perdu » dans Odoo, les responsables prévenus.
6. Personne de disponible : la messagerie, le message dans la conversation.
7. Réseau du studio qui bloque l'UDP : la voix passe par le relais TURN.

**Seuils pour ouvrir** : moins de 2 % d'appels coupés, moins de 5 % de messageries quand une personne
est disponible, attente moyenne sous 1 minute pendant les heures d'appel.

## Phase 2 : OCD appelle les gens (payant, avec leur accord)

| # | Chantier | Ce que c'est |
|---|---|---|
| 2.1 | **Accord du client** | « Demander l'accord pour appeler » dans la conversation (message de Meta, dans les 24 h) ou un modèle ; la réponse notée sur le contact (7 jours ou pour toujours) ; les limites de Meta respectées (1 demande par 24 h, 2 par 7 jours) |
| 2.2 | **Rappeler** | « Rappeler » sur un appel manqué ou coupé : l'accord est donné par Meta quand le client a appelé (rappel de l'appel) ; le serveur appelle par `wa.meta.vc` |
| 2.3 | **Le livreur appelle le client** | Depuis sa tournée, par le numéro d'OCD : le livreur ne voit pas le numéro du client ; les 2 appels avant « absent » comptés |
| 2.4 | **L'animatrice appelle le vendeur** | 30 minutes avant un live à distance |
| 2.5 | **Coût** | Durée facturée par tranches de 6 s selon le pays appelé, rapport mensuel ; pas vers le Nigeria, les États-Unis, le Canada, l'Égypte, le Vietnam (refusés par Meta) |

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
