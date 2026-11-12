# Décisions validées avec l'équipe OCD

Ces choix ont été validés pendant le projet. Ceux marqués « réglable » se changent dans
**OCD Live › Configuration › Paramètres**, sans toucher au code.

## Produit

- **Odoo 20 Community**, sans application payante. `ocd_live` fonctionne seul ; le shop, WhatsApp, le
  recrutement et le Togo sont des modules à part.
- **Fidèle au design validé**, pour le site comme pour le back-office.
- **Mobile d'abord**, mais très à l'aise aussi sur tablette et ordinateur.
- **Deux thèmes** : celui du site (vendeurs, clients) et celui du back-office (équipe). Ils lisent les
  mêmes couleurs et polices, dans un seul fichier : `ocd_live/static/src/scss/ocd_tokens.scss`.
- **Données de démonstration** dans un module à part, `ocd_live_demo` : le désinstaller retire tout.
  La démo est **tenue à jour** par une action planifiée : une présentation montre toujours des lives
  en cours, la semaine du studio et les replays récents, quel que soit le jour. Ses vendeurs ont des
  histoires cohérentes (ville, produits, heures, plateforme ; studio pour Lomé, à distance ailleurs) et
  **ne reçoivent jamais de WhatsApp** (numéros d'exemple, `ocd_live_demo_whatsapp`). Elle ajoute deux
  fenêtres de vérification (midi, après-midi) pour avoir des lives de 8 h à 21 h. Scénario : `DEMO.md`.
- **Voix des pages** en plusieurs langues (français, éwé, etc.), enregistrées par l'équipe.
- **L'adresse du site (`/`) ouvre l'accueil d'OCD Live** (`/ocd`), et non la page vide d'Odoo.
- **Le site est en français par défaut** quand le français est installé ; les autres langues restent
  au choix du visiteur. Odoo suit la langue du téléphone ou du compte connecté quand le site la propose.
- **Un seul bouton de langue sur les pages d'OCD** : la langue de la page et de la voix. Français ou
  English change la page (et le choix reste) ; une langue seulement parlée (éwé, mina…) change la voix.
- **Les pages d'Odoo gardées telles quelles** (recrutement, connexion, portail, contact) portent le logo,
  le nom et les coordonnées d'OCD Live : pied de page d'OCD, téléphone et e-mail de la société, aucun
  texte d'exemple d'Odoo. Ce que l'équipe a déjà choisi (page d'accueil, langue, logo, nom) n'est jamais
  remplacé.
- **Un thème de site « OCD Live »** (`theme_ocd`) dans le choix des thèmes d'Odoo : polices Bricolage
  Grotesque et Figtree, orange, encre et sable, boutons arrondis, en-tête blanc avec « Réserver un live »,
  pied de page sombre. Les pages d'OCD Live gardent leur propre cadre ; le thème habille les pages d'Odoo
  et celles que l'équipe crée avec l'éditeur du site (palette « OCD Live » proposée).

- **Qui ouvre l'espace vendeur (« Moi »)** : un compte Odoo relié à un vendeur l'ouvre directement, quel
  que soit le mode de connexion des vendeurs ; un compte de l'équipe ne voit pas le formulaire du numéro
  (un numéro tapé avec ce compte n'envoie rien) ; l'équipe voit l'espace d'un vendeur depuis sa fiche
  (« Voir son espace », lien signé pour la personne, barre « Vue de l'équipe » tant que dure la vue) ;
  un client connecté qui n'est pas vendeur garde le formulaire, avec son numéro prérempli.

- **Les livreurs entrent comme les vendeurs** : page « Tes colis à livrer » (`/ocd/livrer`, lien
  « Espace livreurs » en pied de page), leur numéro, puis leur lien (mode lien) ou un code (mode code ;
  en mode mot de passe aussi, ils n'ont pas de compte) sur WhatsApp. Seulement un contact que l'équipe a
  coché « Livreur » ; même réponse pour tout numéro ; un lien au plus par minute et par numéro. Le
  téléphone retient le livreur jusqu'à « Se déconnecter » ; « Nouveau lien personnel » (fiche du livreur,
  et des vendeurs) coupe aussi les téléphones déjà ouverts ; décocher « Livreur » coupe tout de suite.

## Réservations

- Parcours par défaut : **jour → heure → paquet** (réglable : paquet d'abord).
- **Un seul calendrier** pour le studio et la distance (réglable : un calendrier par mode).
- Studio ouvert de **8:30 à 22:00**, 9 lives de 1 h 30 par jour (réglable : heure, durée, nombre, jours).
- Ouverture des réservations le **1er décembre 2026** (réglable).
- Un créneau est **gardé pendant le paiement**, puis libéré et proposé à la liste d'attente. Un live gardé
  dont le temps est passé est libéré **tout de suite** pour les autres (même avant la tâche de 5 minutes).
  Le Mobile Money vérifié par l'équipe garde l'heure 24 heures **seulement après « J'ai payé »** (numéro ou
  référence du transfert donnés par le vendeur).
- **Ticket du live : un PDF personnel**, jamais partagé (WhatsApp, téléchargement). Son QR code est signé
  et ouvre la vérification de l'équipe, qui fait entrer **une seule fois** ; le ticket d'un live déplacé
  n'est plus valable (le nouveau part sur WhatsApp). Pour parler de son live, le vendeur partage une
  **image d'annonce sans donnée personnelle** (ni numéro, ni ticket).
- **Chacun voit les heures dans son fuseau horaire** (vendeur, livreur, client) : celui de son téléphone,
  sinon celui de son pays ; le nom du fuseau est écrit (« Heure : Cameroun »). Un live au studio vu d'un
  autre fuseau donne aussi l'heure du studio. L'équipe et les adresses des pages gardent l'heure du studio.
- **Prix selon l'heure et la date** : l'équipe crée des règles (+25 % le samedi soir, −15 % le lundi
  matin, une période…) ; la première règle qui correspond s'applique. Un live déplacé ne peut pas aller
  sur une heure plus chère.
- **Pas d'enchères** pour l'instant. Possible plus tard : offre sous pli sur 1 ou 2 créneaux prestige,
  sans paiement d'avance.

## Paiements et devises

- **Aucun fournisseur de paiement figé dans le code** : le site propose les moyens configurés dans
  Odoo pour le pays, la devise et le montant. Aujourd'hui Campay au Cameroun ; au Togo, Mobile Money
  vérifié par l'équipe en attendant un second connecteur.
- **La devise suit le pays** via les listes de prix d'Odoo (franc CFA BCEAO au Togo, BEAC au Cameroun).

## Pays et paiement

- **Pays proposés : tous les pays d'Afrique et les plus connus d'Europe, d'Amérique et d'Asie** (112),
  réglables par l'équipe (OCD Live › Configuration › Pays). Le pays de la personne vient en premier dans
  les listes, puis les pays où OCD Live a commencé (Togo, Cameroun, Bénin, Côte d'Ivoire, Sénégal).
- **Numéros vérifiés avec les règles de Google** (`phonenumbers`), une règle simple sans elle.
- **Paiement par carte avec Stripe** pour les pays sans Mobile Money ; jamais de page de paiement sans
  issue : sans moyen de paiement, l'équipe est appelée à l'aide et l'heure reste gardée.

## Vendeurs et annuaire

- Connexion du vendeur **par lien personnel envoyé sur WhatsApp** (réglable : code à 6 chiffres, ou mot de passe).
- **Le téléphone retient le vendeur et le livreur** (lien ou code) jusqu'à « Changer de numéro » /
  « Se déconnecter » ou un nouveau lien personnel : un cookie du navigateur (180 jours) le retrouve même
  quand la session d'Odoo se termine ou est remplacée. Se déconnecter est toujours un bouton (formulaire),
  jamais un simple lien : un navigateur ou un proxy qui charge les liens à l'avance ne déconnecte personne.
- **Navigation sans rechargement pour les vendeurs et les livreurs** : squelette de la page au toucher
  d'un lien, puis le contenu change seul ; les visiteurs, les formulaires et le paiement gardent les pages
  normales.
- **Fil des lives comme TikTok** : une carte par écran, le pays de la personne d'abord, puis les autres
  pays (les plus actifs d'abord) ; prochains lives et replays quand aucun live n'est vérifié. **Un seul
  prochain live et un seul replay par vendeur** (le plus proche, le plus récent ; les autres sont dans sa
  boutique) : un pays où les vendeurs réservent beaucoup ne repousse pas les lives des autres pays. Les lives
  restent sur TikTok, Facebook… (ces plateformes ne laissent pas lire un live ailleurs) : la carte y mène.
- Annuaire : liens vérifiés pendant les **créneaux de vérification** (8:00–11:00 et 18:00–21:00 par défaut),
  retirés à la fin du créneau. **Pass de 30 jours** pour envoyer ses liens (5 000 F par défaut).
- Un nouveau vendeur, un nouveau produit et un lien de live sont **vérifiés par l'équipe** ; un refus
  envoie un motif au vendeur.

## Shop et livraisons

- **Mode de vente choisi par l'équipe pour chaque vendeur** : contact direct sur WhatsApp, ou vendu par OCD.
- Vendu par OCD : **qui livre** est choisi pour chaque vendeur : le vendeur lui-même, un livreur OCD qui
  passe chercher, ou le stock OCD.
- **Un colis par vendeur** ; le client reçoit un **code à 4 chiffres** : pas de colis livré sans le code,
  3 codes faux bloquent le colis.
- Paiement à la porte : espèces, paiement sur le téléphone du client, ou Mobile Money déclaré (réglable).
- **Reversements** au rythme de chaque vendeur, seulement pour les colis confirmés par le code.
- **Pas de remise sans paiement** : dans l'appli des colis, le code du client n'est accepté qu'une fois
  l'argent à la porte encaissé ; un vendeur qui n'encaisse pas montre le paiement sur le téléphone du
  client, sinon il appelle l'équipe (qui peut valider sans code, avec un motif).
- **Reprise de livraison par le livreur** après un problème, tracée dans l'historique du colis (qui, après
  quel problème). Le nombre d'échecs compte toujours : au-delà du réglage, le colis retourne au vendeur.
- **Une photo par couleur** (le vendeur dans « Mes produits », ou l'équipe) : la page change de photo avec
  la couleur ; la photo s'ouvre en plein écran. Une taille ou une couleur épuisée se choisit encore, pour
  **« Préviens-moi quand c'est de retour »** (WhatsApp, dès que le stock revient).
- **Le replay se lit dans la page** quand la plateforme le permet (YouTube, TikTok, Facebook) : un produit
  touché fait aller la vidéo à son moment. Le lecteur ne se charge qu'au premier toucher. Ailleurs
  (Instagram…), la vidéo s'ouvre sur son site, avec le moment du produit écrit.
- **Contact direct** : le produit a sa fiche sur le site, sans panier (bloqué aussi côté serveur) ; le
  bouton WhatsApp envoie au vendeur le choix (couleur, taille…) et le lien du produit.
- **Voix des pages** gardée partout, même là où le design n'a pas de bouton ; sur téléphone, « Partager »
  ne garde alors que son icône.
- **Commande sans e-mail** : le client donne son nom, son WhatsApp, sa ville, son quartier et un point de
  repère ; il suit sa commande sur WhatsApp et sur la page de suivi.
- **Retour** demandé par le client depuis la page de suivi pendant **30 jours** après la livraison
  (réglable, 0 = pas de retour) ; l'équipe reçoit une activité pour l'organiser.
- **Frais de livraison : un prix par colis** (un colis par vendeur), selon la ville d'où part le colis et
  le quartier du client ; le client paie la somme des colis.
- **Le vendeur qui livre fixe ses prix**, dans les bornes fixées par l'équipe (réglable) ; OCD garde une
  part réglable de ses livraisons (**0 %** au départ). Les livraisons des livreurs OCD et des agences
  reviennent à OCD.
- **Vers une autre ville ou un autre pays : seulement par un tarif « agence »** prévu par l'équipe, sans
  paiement à la porte. Une adresse qu'aucun tarif ne couvre est refusée avant le paiement.

## WhatsApp

- **Un seul accord** : la case d'OCD Live (réservation, espace vendeur, commande du shop) et l'accord de
  WhatsApp (changé aussi par STOP et START) restent identiques. Un refus n'est jamais contourné.
- **Les messages demandés par le contact partent toujours** (code de connexion, lien, ticket, alerte
  « Préviens-moi ») : la demande vaut accord pour ce message.
- Les colis d'OCD ont leurs propres messages : le « commande expédiée » du shop n'est pas envoyé pour eux,
  et la demande de note part une fois par commande, après son dernier colis.
- **Pas de code ni de mot de passe dans un modèle Utilitaire** (refusés par Meta) : le code du colis est
  sur la page de suivi, ouverte par le bouton du message ; le ticket donne son numéro.
- **Messages en français et en anglais** : chaque modèle existe dans les deux langues (même nom chez Meta).
  Un contact dont la langue est l'anglais reçoit la version anglaise une fois approuvée par Meta, la
  version française en attendant.
- **Textes des modèles** : chargés à l'installation, puis à l'équipe. Une nouvelle version d'un module ne
  change que les textes restés tels que le module les avait écrits, et jamais celui d'un modèle approuvé par
  Meta (c'est le texte que Meta envoie). Odoo refuse de soumettre un texte que Meta refuserait (variable au
  début ou à la fin, deux variables sans mots entre elles).

## Back-office

- **Paramètres** à sections, lus par les automatisations ; les responsables d'OCD Live les changent sans
  être administrateurs d'Odoo ; seuls les réglages de la page sont écrits, après leurs contrôles.
- **Automatisations** : règles que l'équipe met en pause, tâches à heure fixe, et règles du code (argent,
  preuves de livraison) **jamais coupées** ; les tâches techniques sont toujours actives.
- **Aucune mention d'Odoo** pour l'équipe, les vendeurs et les clients (module `ocd_debranding`, avec
  `disable_odoo_online` de l'OCA).
- **Les adresses du back-office gardent `/odoo/`** : ce préfixe est écrit en dur dans le cœur d'Odoo
  (routeur du navigateur, liens des menus et des fiches, routes du serveur, liens des e-mails) ; le
  changer demanderait de remplacer des fichiers du cœur à chaque mise à jour. Les vendeurs et les clients
  ne le voient jamais (le site utilise `/ocd`, `/lives`, `/shop`). Pour une adresse à la marque : un
  sous-domaine pour l'équipe (ex. `equipe.ocdlive.com`).

