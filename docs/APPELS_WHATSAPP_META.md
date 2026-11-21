# Appels WhatsApp : ce qu'il faut activer chez Meta

Pour la personne qui administre le compte Meta d'OCD (le « portefeuille d'entreprise » Meta Business).
Compter 30 minutes, plus le temps d'attente de Meta si la limite d'envoi est trop basse (étape 4).

Le reste (le serveur d'appels, Odoo) est dans le [guide du serveur d'appels](../whatsapp_cloud_call/freeswitch/README.md)
et la [feuille de route](APPELS_WHATSAPP.md).

## Avant de commencer

Il faut être **administrateur** du portefeuille d'entreprise Meta d'OCD, et avoir accès à
l'**app Meta** déjà utilisée pour les messages WhatsApp (celle dont l'ID est dans Odoo, compte
WhatsApp, onglet Connexion).

On passe par trois endroits de Meta. Les menus changent de nom selon la langue : le nom anglais est
entre parenthèses.

| Endroit | Adresse | Sert à |
|---|---|---|
| **Paramètres de l'entreprise** (Business settings) | business.facebook.com › roue dentée « Paramètres » | Les utilisateurs système, leurs droits, les paiements |
| **WhatsApp Manager** | business.facebook.com › WhatsApp Manager (ou business.facebook.com/wa/manage) | Le numéro, sa limite d'envoi, ses réglages d'appel |
| **Tableau de bord de l'app** (App Dashboard) | developers.facebook.com › Mes apps › l'app d'OCD | Le webhook, le mode de l'app |

Les étapes 1, 2 et 5 servent déjà aux messages WhatsApp : si les messages marchent, il suffit de les
**vérifier**. Les étapes 3, 4 et 6 sont propres aux appels.

> **Ne pas activer les appels soi-même dans WhatsApp Manager** (interrupteur de l'onglet « Appels » du
> numéro). Meta le refuse tant que le webhook des appels ou le serveur SIP n'est pas réglé (erreur
> 2593151 : « To use WhatsApp calling features, you need to configure webhooks or set up Session
> Initiation Protocol »). Et s'il l'accepte (webhook seul), les appels arrivent sans serveur d'appels
> pour les faire sonner chez l'équipe : les clients voient l'icône, leurs appels sonnent dans le vide.
> C'est **Odoo** qui active les appels, à l'étape 7, en même temps qu'il déclare le serveur d'appels,
> une fois celui-ci installé et démarré.

---

## Étape 1 · Le numéro est sur la Cloud API

**Pourquoi** : les appels par l'API n'existent que pour un numéro utilisé avec la Cloud API, pas
avec l'application WhatsApp Business d'un téléphone.

**Où** : WhatsApp Manager › Outils du compte (Account tools) › **Numéros de téléphone** (Phone numbers).

**Ce qu'on doit voir** : le numéro d'OCD, au statut « Connecté » (Connected). Si les messages
WhatsApp partent déjà depuis Odoo, c'est bon.

---

## Étape 2 · L'utilisateur système et son jeton ont les bons droits

Odoo parle à Meta avec le **jeton d'un utilisateur système** (saisi dans Odoo, compte WhatsApp,
onglet Connexion, « Jeton d'accès »). Pour les appels, ce jeton a besoin de trois autorisations :

| Autorisation | Sert à |
|---|---|
| `whatsapp_business_messaging` | recevoir les appels et leurs notifications (webhook « calls ») |
| `whatsapp_business_management` | envoyer les réglages d'appel au numéro et lire son mot de passe SIP |
| `business_management` | gérer les éléments du portefeuille (demandée par Meta pour ce type de jeton) |

**Vérifier l'utilisateur système** :

1. Paramètres de l'entreprise › Utilisateurs (Users) › **Utilisateurs système** (System users).
2. Cliquer sur l'utilisateur système utilisé par Odoo. Son rôle : « Admin » (le plus simple : il a
   alors accès à tout le portefeuille).
3. Onglet des éléments attribués (Assigned assets) :
   - l'**app** d'OCD, avec « Contrôle total » (Full control / Manage app) ;
   - le **compte WhatsApp** (WhatsApp account) d'OCD, avec « Contrôle total ».

   S'il manque l'un des deux : « Attribuer des éléments » (Assign assets), choisir l'élément, cocher le
   contrôle total, enregistrer.

**Vérifier le jeton** : un jeton garde les autorisations choisies quand il a été créé. En cas de doute,
en créer un nouveau :

1. Sur la page de l'utilisateur système : « Générer un jeton » (Generate new token).
2. Choisir l'app d'OCD, une expiration « Jamais » (Never).
3. Cocher `business_management`, `whatsapp_business_management` et `whatsapp_business_messaging`.
4. Copier le jeton (il n'est montré qu'une fois) et le coller dans Odoo : compte WhatsApp, onglet
   Connexion, « Jeton d'accès », puis « Vérifier le compte » (le compte doit rester « OK »).

Le jeton ne se donne qu'à Odoo : jamais par message, e-mail ou conversation.

---

## Étape 3 · L'app Meta est « en ligne » (Live)

**Pourquoi** : Meta n'envoie les appels à un serveur SIP (le serveur d'appels d'OCD) que si l'app est
en mode « Live », pas en mode « Développement » (Development).

**Où** : Tableau de bord de l'app, en haut de la page : le sélecteur **Mode de l'app** (App mode).

**Ce qu'on doit voir** : « Live » (En ligne).

**Si l'app est en « Développement »** : basculer sur « Live ». Meta demande alors, s'ils manquent,
une adresse de politique de confidentialité (une page du site d'OCD), une catégorie et une icône :
les remplir dans Paramètres de l'app › Général (Basic), puis basculer.

---

## Étape 4 · La limite d'envoi est d'au moins 2 000 par jour

**Pourquoi** : Meta n'active les appels que pour un numéro dont la limite d'envoi est d'au moins
**2 000 destinataires par jour**. Sans elle, l'envoi des réglages d'appel depuis Odoo est refusé.

**Où** : WhatsApp Manager › Outils du compte (Account tools) › **Limites d'envoi** (Messaging limits).
Aussi dans Odoo : compte WhatsApp, onglet Santé, « Limite d'envoi » (après « Vérifier le compte ») :
`TIER_2K`, `TIER_10K`, `TIER_100K` ou `TIER_UNLIMITED` conviennent, `TIER_250` non.

Les paliers de Meta : 250, puis 2 000, 10 000, 100 000, illimité.

**Si elle est à 250**, deux façons de passer à 2 000 :

- **Faire vérifier l'entreprise par Meta** : Paramètres de l'entreprise › Centre de sécurité
  (Security center) › « Commencer la vérification » (documents de l'entreprise). C'est le plus sûr.
- **Ou envoyer des modèles** : 2 000 messages livrés en 30 jours, hors des conversations ouvertes
  par les clients, à 2 000 numéros différents, avec des modèles de bonne qualité. Meta monte alors
  la limite d'un palier, en 6 heures environ.

---

## Étape 5 · Un moyen de paiement est enregistré

**Pourquoi** : la FAQ de Meta sur les appels demande un moyen de paiement (ou une ligne de crédit)
sur le compte WhatsApp, même si les appels des clients vers OCD sont gratuits. Il sera de toute façon
nécessaire pour qu'OCD appelle les clients plus tard (payant à la minute).

**Où** : Paramètres de l'entreprise › **Facturation et paiements** (Billing & payments), compte
WhatsApp ; ou WhatsApp Manager › Vue d'ensemble › Moyen de paiement.

**Ce qu'on doit voir** : une carte de paiement valide sur le compte WhatsApp d'OCD. Si des modèles
de messages sont déjà facturés à OCD, c'est déjà fait.

---

## Étape 6 · Le webhook reçoit les appels

**Pourquoi** : Meta prévient Odoo de chaque appel tenté et terminé. Odoo voit ainsi les appels que
le serveur d'appels n'aurait pas pris (il les note « perdus » et prévient les responsables).

**Où** : Tableau de bord de l'app › **WhatsApp › Configuration**, partie « Webhook » (selon la
version du tableau de bord : Cas d'utilisation (Use cases) › Personnaliser (Customize) ›
Configuration).

**Faire** : dans la liste des champs du webhook (Webhook fields), cliquer « S'abonner » (Subscribe)
sur la ligne **`calls`**. Laisser les autres abonnements tels quels (`messages` et ceux déjà cochés
pour Odoo).

**Ce qu'on doit voir** : `calls` et `messages` « Abonné » (Subscribed). L'adresse du webhook est celle
déjà donnée par Odoo (compte WhatsApp, onglet Connexion, « URL de rappel »).

S'abonner au champ `calls` n'active pas les appels : les clients ne voient rien de nouveau tant que
l'étape 7 n'est pas faite.

---

## Étape 7 · Dans Odoo : envoyer les appels à Meta

Seulement quand le **serveur d'appels est installé et démarré** (avec son certificat) : sans lui, les
appels activés n'arriveraient nulle part.

Plus rien à activer à la main chez Meta : Odoo active les appels sur le numéro et lui déclare le
serveur d'appels, dans la même demande.

1. **Paramètres › WhatsApp › Appels** : l'adresse du serveur d'appels (ex. `
appels.rollbackk.app`) et le
   secret du relais TURN (les mêmes que dans le `.env` du serveur d'appels).
2. **WhatsApp › Configuration › Comptes**, le compte d'OCD, onglet **Appels** : cocher « Appels »,
   vérifier les heures d'ouverture (onglet Équipe) et les conseillers.
3. Bouton **Envoyer les appels à Meta**.

**Ce qu'on doit voir** : « Appels chez Meta » à **Activés chez Meta** (vert). Dans la minute, le
serveur d'appels reçoit le mot de passe SIP de Meta (copié par ocd-call-sync).

On peut aussi regarder chez Meta : WhatsApp Manager › Outils du compte › Numéros de téléphone ›
roue dentée à côté du numéro › onglet **Appels** (Calls) : les appels activés et, dans
« Paramètres développeur » (Developer settings), le serveur SIP d'OCD.

**L'icône d'appel** apparaît dans la conversation des clients avec OCD, sur l'application WhatsApp du
téléphone (pas WhatsApp Web). Meta prévient que les réglages peuvent mettre **jusqu'à 7 jours** à
arriver chez tous les clients (le plus souvent bien moins). Pour essayer tout de suite : un téléphone
de l'équipe, WhatsApp à jour, conversation avec OCD.

## Si Odoo affiche une erreur

Le message de Meta s'affiche en rouge sur l'onglet Appels du compte.

| Ce que dit Odoo ou Meta | À regarder |
|---|---|
| Dans WhatsApp Manager : « error 2593151 ... you need to configure webhooks or set up Session Initiation Protocol » | Les appels ont été activés à la main, avant le réglage. Laisser l'interrupteur désactivé, faire l'étape 6, puis l'étape 7 depuis Odoo |
| Alerte « limite d'envoi » sur l'onglet, ou Meta refuse (« not eligible ») | Étape 4 |
| Erreur de droit (« permission », « does not have permission », codes 10 ou 200) | Étape 2 : les trois autorisations du jeton, l'app et le compte WhatsApp en contrôle total. Si tout y est et que Meta refuse encore, demander l'**accès avancé** à `whatsapp_business_management` (Tableau de bord de l'app › Examen de l'app (App Review) › Autorisations et fonctionnalités) : Meta l'exige pour les apps qui servent d'autres entreprises, normalement pas pour celle d'OCD sur ses propres comptes |
| « Meta n'a donné aucun mot de passe SIP » | Étape 3 (app en Live), puis « Envoyer les appels à Meta » à nouveau |
| Restriction de Meta (« RESTRICTED_USER_INITIATED_CALLING »...) | Meta a limité les appels du numéro (qualité). Le message dit jusqu'à quand ; voir WhatsApp Manager › Numéros de téléphone |
| Les clients n'ont pas l'icône d'appel | Attendre (jusqu'à 7 jours), WhatsApp à jour, pas WhatsApp Web ; vérifier « Icône d'appel : Visible » et les heures d'ouverture sur l'onglet Appels |

## Récapitulatif

- [ ] 1. Numéro sur la Cloud API, « Connecté »
- [ ] 2. Utilisateur système : app et compte WhatsApp en contrôle total ; jeton avec
      `business_management`, `whatsapp_business_management`, `whatsapp_business_messaging`, saisi dans Odoo
- [ ] 3. App Meta en mode « Live »
- [ ] 4. Limite d'envoi : 2 000 ou plus
- [ ] 5. Moyen de paiement sur le compte WhatsApp
- [ ] 6. Webhook abonné au champ `calls`
- [ ] 7. Odoo : « Envoyer les appels à Meta » → « Activés chez Meta »

La vérification de l'entreprise par Meta n'est pas exigée pour les appels (elle est seulement une des
façons d'atteindre la limite de 2 000 à l'étape 4).

Sources (documentation de Meta, novembre 2026) : Cloud API Calling, Call settings, SIP, Access tokens,
Messaging limits, Webhooks overview, Calling FAQ (developers.facebook.com/documentation/business-messaging/whatsapp/).
