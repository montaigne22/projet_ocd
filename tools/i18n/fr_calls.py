# The WhatsApp calls (whatsapp_cloud_call): the call server, the phone of the agents, the calls
CALLS = {
    " (until %s)": " (jusqu'au %s)",
    "%(hours)s h %(minutes)02d min": "%(hours)s h %(minutes)02d min",
    "%(minutes)s min %(seconds)02d s": "%(minutes)s min %(seconds)02d s",
    "%s s": "%s s",
    "%(type)s: %(reason)s": "%(type)s : %(reason)s",
    "<span class=\"o_form_label me-2\">Last report:</span>": "<span class=\"o_form_label me-2\">Dernier signe :</span>",
    "A customer who calls allows the company to call them back (Meta, 7 days).":
        "Un client qui appelle permet à l'entreprise de le rappeler (Meta, 7 jours).",
    "A customer who waits this long without an agent leaves a message.":
        "Un client qui attend aussi longtemps sans conseiller laisse un message.",
    "Address of the Call Server": "Adresse du serveur d'appels",
    "<span class=\"o_form_label me-2\">Agents connected then:</span>": "<span class=\"o_form_label me-2\">Conseillers connectés alors :</span>",
    "Connected Agents": "Conseillers connectés",
    "Files Waiting": "Fichiers en attente",
    "Last Report": "Dernier signe",
    "Logins, one per line.": "Identifiants, un par ligne.",
    "Messages and records of calls kept on the call server until Odoo takes them.":
        "Messages et fiches d'appels gardés sur le serveur d'appels jusqu'à ce qu'Odoo les prenne.",
    "Number of Connected Agents": "Nombre de conseillers connectés",
    "Silence Alerted": "Silence signalé",
    "Version": "Version",
    "WhatsApp Call Server": "Serveur d'appels WhatsApp",
    "Port of the TURN Relay (TLS)": "Port du relais TURN (TLS)",
    "443 (passes almost every firewall), or 5349 when another program (nginx) holds the port 443 on the call server. The same as TURN_TLS_PORT in its .env.":
        "443 (passe presque tous les pare-feu), ou 5349 quand un autre programme (nginx) tient le port 443 sur le serveur d'appels. Le même que TURN_TLS_PORT dans son .env.",
    "Agent": "Conseiller",
    "Close": "Fermer",
    "Company": "Société",
    "Config Settings": "Paramètres de configuration",
    "Created by": "Créé par",
    "Created on": "Créé le",
    "Customer": "Client",
    "Discussion Channel": "Canal de discussion",
    "Error": "Erreur",
    "Last Updated by": "Dernière mise à jour par",
    "Last Updated on": "Dernière mise à jour le",
    "User": "Utilisateur",
    "Agent Cut Off": "Conseiller coupé",
    "Agent cut off %s time(s), the call came back.": "Conseiller coupé %s fois, l'appel est revenu.",
    "Answer": "Décrocher",
    "Answered by": "Pris par",
    "Answered by %s.": "Pris par %s.",
    "Answered by a colleague.": "Pris par un collègue.",
    "Answered on": "Décroché le",
    "At Meta": "Chez Meta",
    "Call ID at Meta": "Identifiant de l'appel chez Meta",
    "Call ID on the Call Server": "Identifiant de l'appel sur le serveur d'appels",
    "Call Icon": "Icône d'appel",
    "Call Limit Warning": "Alerte de limite pour les appels",
    "Call Hours Warning": "Alerte sur les heures d'appel",
    "Call back the Customers who Called": "Rappeler les clients qui ont appelé",
    "Call failed (%s).": "Appel échoué (%s).",
    "Call lost: the call server did not take it. Call the customer back or write to them.":
        "Appel perdu : le serveur d'appels ne l'a pas pris. Rappelez le client ou écrivez-lui.",
    "Call of %(duration)s, answered by %(agent)s (waited %(wait)s).":
        "Appel de %(duration)s, pris par %(agent)s (attente %(wait)s).",
    "Call of %s": "Appel de %s",
    "WhatsApp ID of the Customer": "Identifiant WhatsApp du client",
    "Allow the microphone when the browser asks (at the top, at the left of the address).":
        "Autorisez le micro quand le navigateur le demande (en haut, à gauche de l'adresse).",
    "Connecting...": "Connexion...",
    "Call Back": "Rappeler",
    "Call the customer through WhatsApp from your phone of the top bar (a call of the company, paid; the customer must have allowed it).":
        "Appeler le client par WhatsApp depuis votre téléphone de la barre du haut (un appel de l'entreprise, payant ; le client doit l'avoir accepté).",
    "Call through WhatsApp": "Appeler par WhatsApp",
    "Call to %s": "Appel à %s",
    "Call to the customer by %(agent)s: it did not go through (%(cause)s).":
        "Appel au client par %(agent)s : il n'a pas abouti (%(cause)s).",
    "Call to the customer by %s: hung up before they answered.":
        "Appel au client par %s : raccroché avant sa réponse.",
    "Call to the customer by %s: no answer.": "Appel au client par %s : pas de réponse.",
    "Call to the customer of %(duration)s, by %(agent)s.": "Appel au client de %(duration)s, par %(agent)s.",
    "Calling through WhatsApp...": "Appel par WhatsApp...",
    "Finish the current call first.": "Terminez d'abord l'appel en cours.",
    "It rings at the customer's...": "Ça sonne chez le client...",
    "Meta does not allow more calls to this customer for now (limit of calls): try again later.":
        "Meta ne permet pas d'autres appels vers ce client pour le moment (limite d'appels) : réessayez plus tard.",
    "No answer from the customer.": "Pas de réponse du client.",
    "Take the WhatsApp calls first (phone of the top bar): the call leaves from it.":
        "Prenez d'abord les appels WhatsApp (téléphone de la barre du haut) : l'appel part de lui.",
    "The browser refuses the microphone: allow it for this site, then call again.":
        "Le navigateur refuse le micro : autorisez-le pour ce site, puis appelez de nouveau.",
    "The call did not go through (%s).": "L'appel n'a pas abouti (%s).",
    "The call did not leave: %s": "L'appel n'est pas parti : %s",
    "The customer declined the call.": "Le client a refusé l'appel.",
    "The customer did not allow the company to call them on WhatsApp: ask them first (Ask to call them).":
        "Le client n'a pas accepté que l'entreprise l'appelle sur WhatsApp : demandez-lui d'abord (Demander l'accord pour appeler).",
    "The customer hides their number behind a WhatsApp username: the company cannot call them.":
        "Le client cache son numéro derrière un nom d'utilisateur WhatsApp : l'entreprise ne peut pas l'appeler.",
    "This call has no conversation.": "Cet appel n'a pas de conversation.",
    "You do not take the WhatsApp calls of this account (Team tab).":
        "Vous ne prenez pas les appels WhatsApp de ce compte (onglet Équipe).",
    "Allowed": "Accordé",
    "Allowed for a while": "Accordé pour un temps",
    "Ask to call them": "Demander l'accord pour appeler",
    "Asked": "Demandé",
    "Call Permission": "Accord pour appeler",
    "Call Permission Asked on": "Accord demandé le",
    "Call Permission until": "Accord jusqu'au",
    "Calling the Customer": "Appeler le client",
    "May %(company)s call you on WhatsApp? It is about your request.":
        "%(company)s peut-il vous appeler sur WhatsApp ? C'est au sujet de votre demande.",
    "Meta allows 1 request to call a customer per 24 hours, and 2 per 7 days: try again later (the limits restart after a call between the customer and the company).":
        "Meta permet 1 demande d'appel par client en 24 heures, et 2 en 7 jours : réessayez plus tard (les limites repartent de zéro après un appel entre le client et l'entreprise).",
    "Meta does not answer: %s": "Meta ne répond pas : %s",
    "More than 24 hours since the last message of the customer: the permission to call can only be asked in the 24 hours after a message of the customer.":
        "Plus de 24 heures depuis le dernier message du client : l'accord pour appeler ne peut se demander que dans les 24 heures qui suivent un message du client.",
    "Not asked": "Pas demandé",
    "Permission to call asked, no answer yet.": "Accord pour appeler demandé, pas encore de réponse.",
    "Refused": "Refusé",
    "The calls are not enabled on this WhatsApp account (Calls tab).":
        "Les appels ne sont pas activés sur ce compte WhatsApp (onglet Appels).",
    "The company may not call the customer on WhatsApp yet: ask them first.":
        "L'entreprise ne peut pas encore appeler ce client sur WhatsApp : demandez-lui d'abord son accord.",
    "The customer allows the company to call them on WhatsApp until %s.":
        "Le client accepte que l'entreprise l'appelle sur WhatsApp jusqu'au %s.",
    "The customer allows the company to call them on WhatsApp.":
        "Le client accepte que l'entreprise l'appelle sur WhatsApp.",
    "The customer called: %s": "Le client a appelé : %s",
    "The customer does not want to be called on WhatsApp.":
        "Le client ne veut pas être appelé sur WhatsApp.",
    "WhatsApp Message": "Message WhatsApp",
    "WhatsApp withdrew the permission to call the customer (calls not answered).":
        "WhatsApp a retiré l'accord pour appeler ce client (appels sans réponse).",
    "Whatsapp Call Permission Reply": "Dernière réponse à la demande d'accord",
    "Agents who took the calls and were free when the call came.":
        "Conseillers qui prenaient les appels et étaient libres quand l'appel est arrivé.",
    "Average Wait (s)": "Attente moyenne (s)",
    "Average wait of the calls answered during the call hours of the last 14 days. To open the calls to all: under 60 seconds.":
        "Attente moyenne des appels pris pendant les heures d'appel des 14 derniers jours. Pour ouvrir les appels à tous : moins de 60 secondes.",
    "Calls (14 days)": "Appels (14 jours)",
    "Calls Cut": "Appels coupés",
    "Calls ended missed or in the voicemail although an agent taking the calls was free, among the calls of the call hours of the last 14 days. To open the calls to all: under 5 %.":
        "Appels finis manqués ou en messagerie alors qu'un conseiller qui prenait les appels était libre, parmi les appels des heures d'appel des 14 derniers jours. Pour ouvrir les appels à tous : moins de 5 %.",
    "Calls lost or failed, and calls where the agent was cut off (network, closed page), among the calls of the last 14 days. To open the calls to all: under 2 %.":
        "Appels perdus ou en échec, et appels où le conseiller a été coupé (réseau, page fermée), parmi les appels des 14 derniers jours. Pour ouvrir les appels à tous : moins de 2 %.",
    "During the Call Hours": "Pendant les heures d'appel",
    "Free Agents": "Conseillers libres",
    "The call came while the team works (opening hours of the account).":
        "L'appel est arrivé pendant que l'équipe travaille (horaires d'ouverture du compte).",
    "Thresholds Met": "Seuils atteints",
    "Thresholds to Open the Calls to All (14 days)": "Seuils pour ouvrir les appels à tous (14 jours)",
    "Under 2 % of calls cut, under 5 % of voicemail while an agent was free, an average wait under 1 minute during the call hours.":
        "Moins de 2 % d'appels coupés, moins de 5 % de messageries alors qu'un conseiller était libre, une attente moyenne de moins d'une minute pendant les heures d'appel.",
    "Voicemail while an Agent was Free": "Messagerie alors qu'un conseiller était libre",
    "Diagnostic of the Phone": "Diagnostic du téléphone",
    "Phone": "Téléphone",
    "The browser asks for the microphone: click Allow (at the top, at the left of the address).":
        "Le navigateur demande le micro : cliquez sur Autoriser (en haut, à gauche de l'adresse).",
    "The browser refuses the microphone: the calls cannot be answered. Allow it for this site (icon at the left of the address), then reload the page.":
        "Le navigateur refuse le micro : les appels ne peuvent pas être pris. Autorisez-le pour ce site (icône à gauche de l'adresse), puis rechargez la page.",
    "What the phone of each agent who answered did (version, microphone, network addresses, answer sent, end), to understand a call that did not connect.":
        "Ce qu'a fait le téléphone de chaque conseiller qui a décroché (version, micro, adresses réseau, réponse envoyée, fin), pour comprendre un appel qui n'a pas abouti.",
    "The voice relay of the call server (STUN/TURN, ports 3478 and 5349) does not answer: the call cannot go through. Tell the administrator (coturn on the call server, firewall).":
        "Le relais de la voix du serveur d'appels (STUN/TURN, ports 3478 et 5349) ne répond pas : l'appel ne peut pas passer. Prévenez l'administrateur (coturn sur le serveur d'appels, pare-feu).",
    "ID of the customer for the company at WhatsApp (BSUID), given by Meta also when the customer hides their number behind a WhatsApp username.":
        "Identifiant du client pour l'entreprise chez WhatsApp (BSUID), donné par Meta même quand le client cache son numéro derrière un nom d'utilisateur WhatsApp.",
    "Call server": "Serveur d'appels",
    "Call: %s": "Appel : %s",
    "Called on": "Appelé le",
    "Calls": "Appels",
    "Calls at Meta": "Appels chez Meta",
    "Calls during the Opening Hours Only": "Appels seulement aux heures d'ouverture",
    "Calls: settings sent to Meta (%s).": "Appels : réglages envoyés à Meta (%s).",
    "Click anywhere on the page to allow the ringing.": "Cliquez n'importe où sur la page pour permettre la sonnerie.",
    "Company calls": "L'entreprise appelle",
    "Completed": "Fini",
    "Connecting to the call server...": "Connexion au serveur d'appels...",
    "Connection lost: the call comes back to you or goes to a colleague.":
        "Connexion perdue : l'appel vous revient ou passe à un collègue.",
    "Connection unstable...": "Connexion instable...",
    "Conversation": "Conversation",
    "Customer calls": "Le client appelle",
    "DTLS (WebRTC)": "DTLS (WebRTC)",
    "Day": "Jour",
    "Decline": "Refuser",
    "Declined by": "Refusé par",
    "Direction": "Sens",
    "Disabled": "Désactivés",
    "Duration": "Durée",
    "Duration (s)": "Durée (s)",
    "Duration at Meta (s)": "Durée chez Meta (s)",
    "Enabled at Meta": "Activés chez Meta",
    "Encryption of the Voice": "Chiffrement de la voix",
    "End": "Fin",
    "End Cause": "Cause de la fin",
    "Ended By": "Fini par",
    "Ended on": "Fini le",
    "Enter the address of the call server first (Settings > WhatsApp > Calls).":
        "Saisissez d'abord l'adresse du serveur d'appels (Paramètres › WhatsApp › Appels).",
    "Failed": "Échoué",
    "Given by Meta when the SIP server is set: Meta signs its calls with it, and the call server checks it.":
        "Donné par Meta quand le serveur SIP est réglé : Meta signe ses appels avec, le serveur d'appels le vérifie.",
    "Hang up": "Raccrocher",
    "How Meta and the call server agree on the keys of the encrypted voice.":
        "Comment Meta et le serveur d'appels s'accordent sur les clés de la voix chiffrée.",
    "I take the WhatsApp calls": "Je prends les appels WhatsApp",
    "In call ·": "En ligne ·",
    "In progress": "En cours",
    "Keep this page open: the calls ring while it is open. Your colleagues get the call if you do not answer.":
        "Gardez cette page ouverte : les appels sonnent tant qu'elle est ouverte. Vos collègues prennent l'appel si vous ne décrochez pas.",
    "Key of the Call Server": "Clé du serveur d'appels",
    "Last Exchange with Meta": "Dernier échange avec Meta",
    "Last Report of the Call Server": "Dernier signe du serveur d'appels",
    "Lost": "Perdu",
    "Lost or Failed": "Perdus ou échoués",
    "Message": "Message",
    "Message of %(name)s.%(ext)s": "Message de %(name)s.%(ext)s",
    "Message of Meta": "Message de Meta",
    "Meta enables the calls only for a number that may send templates to 2,000 customers a day or more (limit now: %s). Check the account to read it again.":
        "Meta n'active les appels que pour un numéro qui peut envoyer des modèles à 2 000 clients par jour ou plus (limite aujourd'hui : %s). Vérifiez le compte pour la relire.",
    "The opening hours (Team tab) give a number of hours a day but not when: Meta would get hours placed around noon by Odoo (10 hours: 7:00 to 17:00). In the opening hours, show the columns Work from and Work to of the list (icon at the right of its header) and set them on each day; or untick Calls during the Opening Hours Only.":
        "Les horaires d'ouverture (onglet Équipe) donnent un nombre d'heures par jour mais pas lesquelles : Meta recevrait des heures placées par Odoo autour de midi (10 heures : de 7 h à 17 h). Dans les horaires d'ouverture, affichez les colonnes Heure de début et Heure de fin de la liste (icône à droite de son en-tête) et remplissez-les pour chaque jour ; ou décochez « Appels seulement aux heures d'ouverture ».",
    "Meta gave no SIP password: check the SIP server in the settings, then send them again.":
        "Meta n'a donné aucun mot de passe SIP : vérifiez le serveur SIP dans les réglages, puis renvoyez-les.",
    "Meta takes the calls only during the opening hours of the team (Team tab), public holidays closed. Without opening hours, the calls are taken at any time.":
        "Meta ne prend les appels qu'aux heures d'ouverture de l'équipe (onglet Équipe), fermé les jours fériés. Sans heures d'ouverture, les appels sont pris à toute heure.",
    "Microphone off": "Micro coupé",
    "Missed": "Manqué",
    "Missed call (waited %s): call the customer back or write to them.":
        "Appel manqué (attente %s) : rappelez le client ou écrivez-lui.",
    "Missed call (waited %s): the customer left a message.":
        "Appel manqué (attente %s) : le client a laissé un message.",
    "Mute": "Couper le micro",
    "Name of the call server (FreeSWITCH), e.g. calls.example.com: its certificate must be for this name (Meta checks it).":
        "Nom du serveur d'appels (FreeSWITCH), par ex. appels.exemple.com : son certificat doit être à ce nom (Meta le vérifie).",
    "Name of the call server (FreeSWITCH): Meta sends the calls to it, the agents connect to it.":
        "Nom du serveur d'appels (FreeSWITCH) : Meta lui envoie les appels, les conseillers s'y connectent.",
    "Never": "Jamais",
    "New Key": "Nouvelle clé",
    "No call yet": "Aucun appel pour l'instant",
    "Nobody answers: the customer leaves a message, posted in their conversation.":
        "Personne ne décroche : le client laisse un message, posé dans sa conversation.",
    "Not connected": "Pas connecté",
    "Notice Message": "Ligne dans la conversation",
    "Now": "En ce moment",
    "Number of Calls": "Nombre d'appels",
    "Number of the Customer": "Numéro du client",
    "Open the Conversation": "Ouvrir la conversation",
    "Open the conversation": "Ouvrir la conversation",
    "Password of the Phone": "Mot de passe du téléphone",
    "Password of the agent on the call server, given to their phone in Odoo.":
        "Mot de passe du conseiller sur le serveur d'appels, donné à son téléphone dans Odoo.",
    "Phone icon in the conversation with the company, in WhatsApp.":
        "Icône du téléphone dans la conversation avec l'entreprise, dans WhatsApp.",
    "Port of the Agents (WSS)": "Port des conseillers (WSS)",
    "Read the State at Meta": "Lire l'état chez Meta",
    "Restricted by Meta": "Limités par Meta",
    "SDES (recommended with FreeSWITCH)": "SDES (conseillé avec FreeSWITCH)",
    "SIP Password of Meta": "Mot de passe SIP de Meta",
    "SIP Port (Meta)": "Port SIP (Meta)",
    "Same value as static-auth-secret in the configuration of coturn on the call server.":
        "Même valeur que static-auth-secret dans la configuration de coturn sur le serveur d'appels.",
    "Secret of the TURN Relay": "Secret du relais TURN",
    "Seen by": "Vu par",
    "Seen by Meta": "Vu par Meta",
    "Seen by the Call Server": "Vu par le serveur d'appels",
    "Send the Calls to Meta": "Envoyer les appels à Meta",
    "Shown": "Visible",
    "Hidden": "Cachée",
    "State": "État",
    "Status": "Statut",
    "Status at Meta": "Statut chez Meta",
    "Takes the WhatsApp Calls": "Prend les appels WhatsApp",
    "The agent takes the calls (phone of the top bar): the calls ring for them while their page is open.":
        "Le conseiller prend les appels (téléphone de la barre du haut) : les appels sonnent chez lui tant que sa page est ouverte.",
    "The browser refuses the microphone: allow it for this site, then answer again.":
        "Le navigateur refuse le micro : autorisez-le pour ce site, puis décrochez à nouveau.",
    "The call could not be answered: %s": "L'appel n'a pas pu être pris : %s",
    "The call server does not answer": "Le serveur d'appels ne répond pas",
    "The call server has not reported since %s: the WhatsApp calls may not ring. Check that FreeSWITCH and the copy of the agents (ocd-call-sync) run on it.":
        "Le serveur d'appels ne donne plus signe depuis %s : les appels WhatsApp risquent de ne pas sonner. Vérifiez que FreeSWITCH et la copie des conseillers (ocd-call-sync) y tournent.",
    "The call server refused the connection (%s).": "Le serveur d'appels a refusé la connexion (%s).",
    "The call server stops working until the new key is entered in its configuration. Continue?":
        "Le serveur d'appels s'arrête de fonctionner tant que la nouvelle clé n'est pas dans sa configuration. Continuer ?",
    "The call server took the call (else only Meta told it).":
        "Le serveur d'appels a pris l'appel (sinon, seul Meta l'a signalé).",
    "The calls ring for the agents of the Team tab who take the calls (phone of the top bar). The address of the call server is in Settings &gt; WhatsApp &gt; Calls. In the webhook of the Meta app, also subscribe to the field calls: Odoo then sees the calls that the call server did not take.":
        "Les appels sonnent chez les conseillers de l'onglet Équipe qui prennent les appels (téléphone de la barre du haut). L'adresse du serveur d'appels est dans Paramètres › WhatsApp › Appels. Dans le webhook de l'app Meta, abonnez-vous aussi au champ calls : Odoo voit alors les appels que le serveur d'appels n'a pas pris.",
    "The customers call the WhatsApp number of the company; each call, answered or not, is recorded here and in the conversation of the customer.":
        "Les clients appellent le numéro WhatsApp de l'entreprise ; chaque appel, pris ou non, est noté ici et dans la conversation du client.",
    "The customers call the company from WhatsApp: a FreeSWITCH call server between Meta and the agents, queue, agents who answer in Odoo, history in the conversations":
        "Les clients appellent l'entreprise depuis WhatsApp : un serveur d'appels FreeSWITCH entre Meta et les conseillers, file d'attente, conseillers qui décrochent dans Odoo, historique dans les conversations",
    "The customers can call this number from WhatsApp; the calls go through the call server of the company (Settings > WhatsApp > Calls).":
        "Les clients peuvent appeler ce numéro depuis WhatsApp ; les appels passent par le serveur d'appels de l'entreprise (Paramètres › WhatsApp › Appels).",
    "The settings changed: send them to Meta (button at the top).":
        "Les réglages ont changé : envoyez-les à Meta (bouton en haut).",
    "The voice of the agents passes through the relay when their network blocks it (coturn on the call server).":
        "La voix des conseillers passe par le relais quand leur réseau la bloque (coturn sur le serveur d'appels).",
    "This call is already recorded.": "Cet appel est déjà noté.",
    "Times the agent was cut off (network, closed page) and the call came back while the customer waited.":
        "Fois où le conseiller a été coupé (réseau, page fermée) et où l'appel est revenu pendant que le client attendait.",
    "To Call Back": "À rappeler",
    "To enter in /etc/ocd-call-sync.conf on the call server: it reads the agents with it and tells Odoo the calls.":
        "À saisir dans /etc/ocd-call-sync.conf sur le serveur d'appels : il lit les conseillers avec et signale les appels à Odoo.",
    "To send to Meta": "À envoyer à Meta",
    "Today": "Aujourd'hui",
    "Unknown": "Inconnu",
    "Voice message left after a call.": "Message vocal laissé après un appel.",
    "Voicemail": "Messagerie",
    "Waiting": "Attente",
    "Waiting (s)": "Attente (s)",
    "Waiting before the Voicemail (seconds)": "Attente avant la messagerie (secondes)",
    "WhatsApp Account": "Compte WhatsApp",
    "WhatsApp Business Account": "Compte WhatsApp Business",
    "WhatsApp Call": "Appel WhatsApp",
    "WhatsApp Calls": "Appels WhatsApp",
    "WhatsApp Webhook Event": "Notification de Meta",
    "WhatsApp account %(name)s, calls: %(details)s": "Compte WhatsApp %(name)s, appels : %(details)s",
    "WhatsApp account %(name)s: %(count)s call(s) of customers did not reach the call server (lost). Check the call server and its connection with Meta (port, certificate, SIP password); the customers are to call back or to write to.":
        "Compte WhatsApp %(name)s : %(count)s appel(s) de clients ne sont pas arrivés au serveur d'appels (perdus). Vérifiez le serveur d'appels et sa liaison avec Meta (port, certificat, mot de passe SIP) ; les clients sont à rappeler ou à qui écrire.",
    "WhatsApp call": "Appel WhatsApp",
    "WhatsApp calls": "Appels WhatsApp",
    "WhatsApp: check the calls and the call server": "WhatsApp : vérifier les appels et le serveur d'appels",
    "You do not take the calls": "Vous ne prenez pas les appels",
    "You take the calls": "Vous prenez les appels",
    "an agent": "un conseiller",
    "call server": "serveur d'appels",
    "disabled": "désactivés",
    "e.g. calls.example.com": "par ex. appels.exemple.com",
    "enabled": "activés",
    "its installation": "son installation",
    "previous call(s)": "appel(s) avant",
}

CALLS_DESCRIPTION = """
Appels WhatsApp pour Odoo Community
===================================

Les clients appellent le numéro WhatsApp de l'entreprise (l'icône du téléphone dans WhatsApp). Les
appels passent par un serveur d'appels de l'entreprise (FreeSWITCH, SIP sur TLS avec Meta), qui fait
sonner les conseillers dans leur navigateur, dans Odoo (WebRTC) :

- Réglages des appels chez Meta depuis le compte WhatsApp : appels activés, icône d'appel, heures
  d'appel (les heures d'ouverture de l'équipe et ses jours fériés), serveur SIP, SRTP, webhook des
  appels ; le mot de passe SIP donné par Meta gardé pour le serveur d'appels.
- File d'attente sur le serveur d'appels : musique, tous les conseillers libres sonnent ensemble, le
  conseiller de la conversation d'abord ; un conseiller coupé (réseau, onglet fermé) récupère l'appel
  pendant que le client attend ; messagerie quand personne ne décroche, posée dans la conversation.
- Le serveur d'appels marche sans Odoo : les conseillers et leurs mots de passe sont recopiés chaque
  minute sur le serveur ; quand Odoo ne répond pas, tous les conseillers connectés sonnent.
- Téléphone des conseillers dans la barre du haut : prendre les appels ou non, sonnerie, nom du client
  et sa conversation, décrocher, refuser, couper le micro, raccrocher ; un deuxième appel est refusé
  pendant un appel.
- Historique : chaque appel (attente, durée, conseiller, fin) et une ligne dans la conversation ; un
  appel manqué ou un message attend une réponse de l'équipe (rappels de WhatsApp).
- Surveillance : le serveur d'appels se signale chaque minute, les responsables sont prévenus quand il
  se tait ; un appel vu par Meta et pas par le serveur d'appels est « perdu » et signalé.
- Identifiants TURN pour les conseillers (coturn), valables 12 heures.

La configuration du serveur d'appels est dans le dossier freeswitch du module.
"""

# WhatsApp Cloud API (whatsapp_cloud): texts added with the calls
WA_CLOUD_CALLS = {
    "(Message of the customer without text: %s)": "(Message du client sans texte : %s)",
}
