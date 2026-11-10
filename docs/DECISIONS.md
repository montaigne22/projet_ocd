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
- **Voix des pages** en plusieurs langues (français, éwé, etc.), enregistrées par l'équipe.

## Réservations

- Parcours par défaut : **jour → heure → paquet** (réglable : paquet d'abord).
- **Un seul calendrier** pour le studio et la distance (réglable : un calendrier par mode).
- Studio ouvert de **8:30 à 22:00**, 9 lives de 1 h 30 par jour (réglable : heure, durée, nombre, jours).
- Ouverture des réservations le **1er décembre 2026** (réglable).
- Un créneau est **gardé pendant le paiement**, puis libéré et proposé à la liste d'attente.
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

## Vendeurs et annuaire

- Connexion du vendeur **par lien personnel envoyé sur WhatsApp** (réglable : code à 6 chiffres, ou mot de passe).
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
