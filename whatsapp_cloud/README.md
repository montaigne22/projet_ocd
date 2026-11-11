# WhatsApp Cloud API (`whatsapp_cloud`, `whatsapp_cloud_sale`)

WhatsApp Business pour Odoo 20 Community, directement par l’API Cloud de Meta (sans intermédiaire payant) : notifications des commandes, conversations avec les clients dans Discussion, réponses automatiques, modèles soumis à Meta depuis Odoo.

- `whatsapp_cloud` : comptes, conversations (onglet **WhatsApp** de Discussion), équipe et attribution, réponses automatiques, modèles, action « Envoyer un WhatsApp » (règles d’automatisation, actions serveur, bouton sur les documents), envoi en arrière-plan avec nouvelles tentatives, santé du numéro.
- `whatsapp_cloud_sale` (installé automatiquement avec la boutique) : consentement à la commande, modèles et règles des commandes, suivi de commande automatique, devis avec lien de paiement, satisfaction après livraison, bouton « Commander sur WhatsApp » des fiches produit.

## 1. Côté Meta (une seule fois)

1. Sur [business.facebook.com](https://business.facebook.com), dans le portefeuille Meta Business de l’entreprise, ouvrir **WhatsApp Manager** et vérifier que le numéro WhatsApp Business est enregistré et approuvé. Ajouter un **moyen de paiement** : depuis le 1ᵉʳ octobre 2026, Meta facture les modèles, et les réponses hors modèle (réponses des agents, menu d’accueil, message d’absence) au-delà de 1 000 par mois et par numéro ; sans moyen de paiement, ces réponses ne partent plus une fois les 1 000 atteintes.
2. Sur [developers.facebook.com](https://developers.facebook.com), dans l’app Meta reliée à ce compte (produit **WhatsApp**), relever :
   - **WhatsApp > Configuration de l’API** : l’**ID du numéro de téléphone** et l’**ID du compte WhatsApp Business** ;
   - **Paramètres de l’app > Général** : l’**ID de l’app** et la **clé secrète de l’app**.
3. Dans **Paramètres d’entreprise > Utilisateurs système**, créer un utilisateur système (administrateur), lui attribuer l’app et le compte WhatsApp, puis **générer un jeton** permanent avec les autorisations `whatsapp_business_messaging` et `whatsapp_business_management`.
4. Mettre l’app en mode **Live** (en mode développement, Meta n’envoie pas toutes les notifications).

Ces clés ne doivent jamais être envoyées par e-mail ou par messagerie : elles se saisissent uniquement dans Odoo.

## 2. Côté Odoo

### Compte

1. **WhatsApp > Configuration > Comptes > Nouveau**, onglet **Connexion** : saisir l’ID du numéro, l’ID du compte WhatsApp Business, le jeton d’accès, l’ID de l’app et la clé secrète de l’app.
2. Copier l’**URL de rappel** et le **jeton de vérification** affichés, puis dans l’app Meta, **WhatsApp > Configuration > Webhook** : les coller, valider, et s’abonner aux champs **messages**, **message_template_status_update**, **message_template_quality_update**, **template_category_update**, **phone_number_quality_update** et **account_update**. L’URL doit être en HTTPS (adresse publique du site).
3. **Vérifier le compte** : Odoo lit chez Meta le numéro, le nom affiché, la qualité et la limite d’envoi (onglet **Santé**). Cette vérification est refaite toutes les 6 heures ; les responsables sont alertés si le jeton expire, si la qualité baisse ou si Meta n’envoie plus rien alors que des messages partent.
4. **Envoyer un message de test** (modèle `hello_world` de Meta) vers votre numéro.

### Droits

Dans **Paramètres > Utilisateurs**, rubrique **WhatsApp** :

- **Agent** : répond aux conversations qui lui sont attribuées et à celles qui ne le sont pas encore ;
- **Responsable** : voit toutes les conversations, les attribue, et configure les comptes, les modèles et les réponses automatiques.

### Activer ou désactiver les fonctions

**Paramètres > WhatsApp** (ou **WhatsApp > Configuration > Paramètres**) : chaque fonction se coche ou se décoche, puis **Enregistrer**. Tout est activé à l’installation.

| Rubrique | Fonction | Décochée |
| --- | --- | --- |
| Conversations | **Conversations WhatsApp** | Pas de conversation dans Discussion ni de réponse automatique : le message du client est seulement noté sur sa fiche contact (ou sur le document auquel il répond) et gardé dans **WhatsApp > Messages**. STOP / START et les notes de satisfaction restent pris en compte. Les notifications continuent de partir. |
| | **Accusés de lecture** | Le client ne voit plus les coches bleues ni « en train d’écrire… ». |
| | **Relances de réponse** | Ni relance des agents ni alerte des responsables. |
| Réponses automatiques | **Menu d’accueil** | Les messages vont directement à l’équipe. |
| | **Message d’absence** | Aucun message en dehors des horaires. |
| Boutique en ligne | **Numéro WhatsApp** | (vide : le numéro du compte vérifié chez Meta) |
| | **Commander sur WhatsApp** | Le bouton disparaît des fiches produit. |
| | **Consentement à la commande** | La case n’est plus proposée ; si le compte exige le consentement, seuls les clients ayant déjà accepté reçoivent les notifications. |
| Notifications des commandes | **Commande reçue**, **confirmée**, **expédiée**, **Satisfaction après la livraison** | La règle d’automatisation correspondante est archivée : le message ne part plus. |
| Ventes | **Suivi des commandes** | L’option *Suivre ma commande* disparaît du menu et les numéros de commande ne reçoivent plus de réponse automatique. |
| | **Devis sur WhatsApp** | Le bouton **Envoyer sur WhatsApp** disparaît des devis. |

Les fonctions des rubriques Conversations et Ventes valent pour la société ; Menu d’accueil et Message d’absence s’appliquent à tous ses comptes (réglables aussi compte par compte) ; celles de la boutique valent pour le site.

### Plusieurs numéros (plusieurs comptes)

Chaque compte correspond à un numéro WhatsApp, avec sa propre équipe, ses horaires d’ouverture, son menu d’accueil et son message d’absence. Pour en ajouter un, créer un compte de plus avec l’ID du nouveau numéro. Si le numéro est dans le même compte WhatsApp Business chez Meta, l’URL de rappel et l’abonnement du webhook restent les mêmes.

- **Messages reçus** : ils vont au compte du numéro que le client a contacté, y compris quand plusieurs numéros partagent le même compte WhatsApp Business chez Meta. Un client qui écrit à deux numéros a deux conversations.
- **Réponses des agents** : elles partent du numéro de la conversation. Un modèle envoyé depuis une conversation (ou un devis envoyé sur WhatsApp) part aussi de ce numéro, si le modèle existe dans son compte WhatsApp Business.
- **Notifications automatiques** (commandes, satisfaction) : elles partent du compte du modèle, sinon du **premier compte de la société** dans la liste des comptes (ordre réglable par glisser-déposer).
- **Bouton « Commander sur WhatsApp »** : numéro réglé dans les paramètres (Boutique en ligne), sinon celui du premier compte.
- **Paramètres > WhatsApp** : *Menu d’accueil* et *Message d’absence* s’appliquent à tous les comptes de la société ; chaque compte reste réglable séparément.
- **Modèles** : chez Meta, ils appartiennent au compte WhatsApp Business. Des numéros du même compte WhatsApp Business les partagent ; un numéro d’un autre compte WhatsApp Business doit avoir les siens (bouton **Synchroniser les modèles** sur son compte).
- **Plusieurs sociétés** : chaque compte appartient à une société ; les documents d’une société partent du premier compte de cette société.

### Équipe (onglet du compte)

- **Agents** : utilisateurs qui répondent pour ce numéro (vide : tous les agents WhatsApp).
- **Attribution** :
  - *Prise en charge par un agent* : tous les agents voient la nouvelle conversation, le premier qui répond (ou la prend) la garde ;
  - *Chaque agent à tour de rôle* : la conversation va à l’agent qui a le moins de conversations ouvertes, les agents en ligne d’abord ;
  - *Vendeur du client* : le vendeur de sa dernière commande s’il est agent, sinon chacun son tour.
- **Horaires d’ouverture** : l’horaire de travail (avec ses jours fériés dans les congés) ; il compte les délais et déclenche le message d’absence.
- **Répondre sous** (15 min par défaut) : l’agent est relancé ; **Alerter les responsables après** (60 min) : les responsables sont ajoutés à la conversation et prévenus. Seules les heures d’ouverture comptent.

### Réponses automatiques (onglet du compte)

- **Menu d’accueil** : une nouvelle conversation commence par le message d’accueil et les options en boutons (3 options au plus, sinon une liste). Options fournies : *Suivre ma commande*, *Parler à l’équipe* ; on peut ajouter des options *Répondre par un texte* (horaires, magasins, livraison et retours…). Sans option active, le message d’accueil est envoyé et le message du client va directement à l’équipe.
- **Actions des options** (bouton **Voir** d’une option pour son formulaire et l’explication de son action) :
  - *Répondre par un texte* : envoie la réponse saisie (horaires, retours…) ;
  - *Ouvrir un sous-menu* : envoie le texte de l’option avec ses propres options et un choix « Menu principal » (9 options au plus), par exemple « Infos pratiques » regroupant Nos magasins, Frais de livraison et Retours ;
  - *Changer de langue* : le client reçoit ensuite réponses, menus et notifications dans cette langue (une option par langue installée, nommée dans sa langue ; non proposée aux clients qui l’utilisent déjà). Pour une langue installée plus tard, ajouter une option avec cette action ;
  - *Arrêter les notifications* / *Recevoir les notifications* : comme STOP et START, seule l’option utile est proposée ;
  - avec la boutique : *Statut des commandes*, *Payer une commande* (liens de paiement en ligne des devis envoyés et commandes à payer ; proposée seulement s’il y en a), *Nos magasins* (adresse, téléphone, horaires et position sur la carte des magasins du retrait en magasin publié), *Frais de livraison* (le bot propose les villes en choix, puis les quartiers, ou les zones de livraison avec leurs quartiers écrits sous leur nom quand ils sont nombreux, et « Autre quartier » à écrire ; « Autre ville » donne aussitôt les tarifs des autres villes ; la réponse donne les modes de livraison publiés avec leurs prix et le retrait en magasin ; une question attend sa réponse 2 heures) ;
  - *Passer à un agent*.
  Ces options sont créées désactivées : les activer (interrupteur **Actif**) pour les proposer.
- **Réponses guidées** : les réponses automatiques (texte d’une option, statut de commande, magasins, paiement, frais de livraison) se terminent par deux boutons, *Menu principal* et *Parler à l’équipe* : le client continue sans rien écrire.
- **Passage à l’équipe** : quand le client demande une personne (option, bouton ou « conseiller ») sans avoir encore écrit sa demande, l’*Invitation à écrire* l’invite à la décrire (numéro de commande, article, question, photo) ; quand il l’a déjà écrite, il reçoit le *Message de transfert*.
- Le client est confié à l’équipe quand il choisit *Parler à l’équipe*, écrit « conseiller » ou « humain », ou écrit quelque chose que le menu ne traite pas. « menu » renvoie le menu.
- **Message d’absence** : envoyé en dehors des horaires, au plus une fois toutes les 12 heures à un client.
- **STOP** / **START** : le client arrête ou reprend les notifications, avec un message de confirmation.
- **Lien pour laisser un avis** (avec la boutique) : envoyé aux clients qui notent leur commande 4 ou 5 sur 5.

Les textes se traduisent comme les autres champs d’Odoo (icône de langue) : chaque client reçoit la version dans sa langue.

## 3. Modèles de messages

Hors des 24 heures qui suivent le dernier message d’un client, WhatsApp n’accepte que des **modèles** approuvés par Meta.

**Soumettre depuis Odoo** (le plus simple) : **WhatsApp > Configuration > Modèles**, ouvrir le modèle, vérifier le texte, les exemples des variables et les boutons, puis **Soumettre à Meta**. Meta répond en 24 heures au plus ; sa décision arrive dans Odoo (statut *Approuvé*, ou *Refusé* avec le motif). Un modèle approuvé se modifie (**Soumettre les modifications à Meta**) 10 fois en 30 jours, une fois par jour au plus. Pour un modèle avec un document en en-tête, l’ID de l’app doit être saisi sur le compte.

**Ou créer chez Meta** (**WhatsApp Manager > Modèles de messages**) avec exactement les mêmes noms, langues et textes, puis **Synchroniser les modèles** sur le compte : les modèles fournis sont mis à jour au lieu d’être dupliqués.

Modèles fournis (en français, et en anglais pour les clients anglophones, sous le même nom) :

| Nom | Envoyé quand | Texte (français) |
| --- | --- | --- |
| `order_confirmed` | la commande est confirmée (payée en ligne, à payer à la livraison ou au magasin, ou confirmée par l’équipe) | Bonjour {{1}}, merci pour votre commande {{2}} d'un montant de {{3}}, elle est confirmée. Nous vous prévenons dès son expédition. |
| `order_received` | la commande attend un virement | Bonjour {{1}}, nous avons bien reçu votre commande {{2}} d'un montant de {{3}}. Elle sera confirmée dès réception de votre paiement ({{4}}). |
| `order_shipped` | le bon de livraison est validé (sauf retrait au magasin) | Bonjour {{1}}, votre commande {{2}} est en route ({{3}}). Le livreur vous appellera avant de passer. |
| `order_ready_for_pickup` | depuis la commande, **Action > Envoyer un WhatsApp** | Bonjour {{1}}, votre commande {{2}} est prête ! Vous pouvez la retirer au magasin {{3}}, aux heures d'ouverture, avec ce message. |
| `quotation_sent` | bouton **Envoyer sur WhatsApp** d’un devis, après 24 heures | Bonjour {{1}}, voici votre devis {{2}} d'un montant de {{3}}. Vous pouvez le consulter et le payer en ligne (MTN Mobile Money, Orange Money) avec le bouton ci-dessous. |
| `delivery_feedback` | 2 jours après la livraison (ou le retrait) | Bonjour {{1}}, votre commande {{2}} vous a-t-elle donné satisfaction ? Notez-la de 1 à 5 avec les boutons ci-dessous, cela nous aide beaucoup. |
| `conversation_follow_up` | depuis une conversation, après 24 heures | Bonjour {{1}}, nous revenons vers vous au sujet de votre message. Répondez à ce message pour poursuivre la conversation avec notre équipe. |

- Les modèles des commandes et du devis ont un bouton lien **Suivre ma commande** / **Voir et payer** (`{base_url}/{{1}}` : l’adresse du site est ajoutée à la soumission, Odoo remplit `{{1}}` avec le lien de la commande dans l’espace client, ouvert sans connexion).
- `delivery_feedback` a cinq réponses rapides (5 ⭐ Excellent … 1 ⭐ Mauvais) : la note est enregistrée sur la commande. Meta peut le classer en catégorie *Marketing*.
- Chaque client reçoit la version dans **sa langue** (langue de sa fiche contact, ou du site sur lequel il a commandé), sinon la version française. Une version refusée, en pause ou en attente n’est pas utilisée.
- Les déclencheurs se règlent dans **WhatsApp > Configuration > Règles d’automatisation** (délai de l’enquête de satisfaction, autres événements…).

## 4. Répondre aux clients

Les conversations sont dans **Discussion**, onglet **WhatsApp** (filtres *Non lues*, *Les miennes*, *Non attribuées*, *En attente de réponse*), et dans **WhatsApp > Conversations** (vue kanban et liste, avec les étiquettes et les retards).

- **Prendre la conversation** pour y répondre (ou répondre directement : l’agent qui répond la prend). Texte, photos, documents, réponses citées (le client voit le message cité) : tout part sur WhatsApp. Les coches indiquent envoyé, distribué, lu ; un échec est signalé avec sa raison et ce qu’il faut faire.
- Le client voit « en train d’écrire » et les coches bleues de lecture quand l’agent lit et écrit.
- **/note texte** : note interne, jamais envoyée au client.
- **Réponses rapides** : **WhatsApp > Configuration > Réponses rapides**, puis `::raccourci` dans la conversation. Dans une conversation WhatsApp, `{prenom}`, `{nom}`, `{conseiller}`, `{societe}`, `{commande}` et `{lien_commande}` sont remplacés (prénom et nom du client, nom de l’agent, de la société, dernière commande et son lien).
- Plus de 24 heures après le dernier message du client, la zone de saisie laisse place à **Envoyer un modèle** (`conversation_follow_up` pour reprendre la conversation, ou un autre modèle).
- Panneau **Client** (icône ℹ️) : coordonnées, consentement, statut et agent, étiquettes, commandes et leur statut, **Nouveau devis**, **Transférer**, **Résolue** / **Rouvrir**.
- **Numéro inconnu** : un contact est créé avec le nom WhatsApp du client ; **Contact existant** le fusionne avec la bonne fiche (conversation, messages et numéro compris), **Bon contact** le confirme.
- Le client qui reprend une conversation résolue dans les 12 heures retrouve son agent ; plus tard, la conversation repart du menu d’accueil.

## 5. Boutique (`whatsapp_cloud_sale`)

- **Suivre ma commande** (menu d’accueil), ou un numéro de commande écrit par le client (S00012…) : statut des dernières commandes avec leur lien. Seules les commandes du client (de son numéro) sont données.
- **Envoyer sur WhatsApp** sur un devis : dans la conversation si le client a écrit depuis moins de 24 heures, sinon avec le modèle `quotation_sent`. Le client consulte et paie le devis en ligne, avec les moyens de paiement du site (par exemple Mobile Money avec `payment_campay`) ; la confirmation part ensuite avec `order_confirmed`.
- **Satisfaction** : 2 jours après la livraison, `delivery_feedback` ; une note de 4 ou 5 reçoit le lien d’avis, une note de 1 ou 2 est confiée à l’équipe (« Client insatisfait »). Les notes se voient sur les commandes et dans le panneau Client.
- **Commander sur WhatsApp** : bouton des fiches produit, qui ouvre WhatsApp avec le produit, les options choisies (taille, couleur) et le lien de la page. Le numéro se règle dans **Paramètres > WhatsApp > Boutique en ligne** (vide : le numéro du compte vérifié chez Meta). Un thème peut utiliser le même numéro pour ses liens WhatsApp (`website._whatsapp_get_link()`).

## 6. Fonctionnement et fiabilité

- Chaque appel de Meta est vérifié (signature avec la clé secrète), enregistré et acquitté aussitôt, puis traité en arrière-plan : rien ne se perd si Odoo est lent, et un message renvoyé par Meta n’est jamais compté deux fois. Ces appels sont visibles 1 mois dans **WhatsApp > Configuration > Notifications de Meta** (bouton **Traiter à nouveau** en cas d’échec).
- Les messages partent en arrière-plan (la commande n’attend jamais Meta) ; en cas d’indisponibilité de Meta ou de limite de débit, 5 tentatives sont faites, puis le message passe en *Échec* (bouton **Renvoyer**).
- Les tâches planifiées (envoi, traitement des notifications, relances, vérification des comptes) demandent qu’Odoo tourne avec ses tâches planifiées actives (réglage par défaut).
- Les photos, notes vocales, vidéos et documents des clients sont téléchargés dès leur arrivée (le lien de Meta expire en quelques minutes) et joints à la conversation.
- Les clients qui cachent leur numéro derrière un **nom d’utilisateur WhatsApp** (2026) sont identifiés par leur identifiant WhatsApp (BSUID), et les réponses leur parviennent quand même.
- Consentement : par défaut, seuls les contacts qui ont accepté reçoivent les notifications (réglable par compte) ; les réponses aux clients qui écrivent sont toujours permises.
- Les numéros sans indicatif sont complétés avec celui du pays du contact (6 70 00 00 00 au Cameroun : +237 670 00 00 00), et envoyés avec le « + » comme le recommande Meta. Installer la bibliothèque Python `phonenumbers` améliore la validation des numéros.

## 7. Mise à jour depuis la version précédente

Mettre à jour `whatsapp_cloud` et `whatsapp_cloud_sale` (`-u whatsapp_cloud,whatsapp_cloud_sale`), puis :

1. donner le droit **Agent** ou **Responsable** WhatsApp aux utilisateurs concernés (l’administrateur est responsable) ;
2. compléter les onglets **Équipe** et **Réponses automatiques** du compte (textes et menu par défaut déjà créés) ;
3. abonner le webhook aux nouveaux champs (§ 2) et saisir l’ID de l’app ;
4. soumettre à Meta les nouveaux modèles `quotation_sent`, `delivery_feedback` et `conversation_follow_up` (FR et EN) ;
5. renseigner le numéro WhatsApp du site s’il diffère de celui du compte.
