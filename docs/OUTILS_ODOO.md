# Outils Odoo utilisés par OCD Live

OCD Live tourne sur **Odoo 20 Community** : aucune application payante. Voici ce que chaque outil
fait concrètement pour OCD Live.

## Ce qu'Odoo fait pour OCD Live

| Outil d'Odoo | Ce qu'il fait chez OCD Live |
|---|---|
| **Site web** | Les pages des vendeurs et des clients : réserver un live, l'annuaire des lives par pays, l'espace vendeur, les boutiques, l'offre d'animatrice. |
| **Ventes** | Chaque réservation payée et chaque pass annuaire est une commande ; un paquet de lives payé devient des lives à placer. |
| **eCommerce** | Le panier et la commande du shop, avec les prix de la liste de prix du pays du client. |
| **Paiement** | Le formulaire de paiement propose les moyens configurés pour le pays (Campay au Cameroun, Mobile Money vérifié par l'équipe au Togo) ; la réservation est confirmée par le paiement, jamais par le navigateur. |
| **Inventaire** | Une commande du shop donne un colis par vendeur ; retours au vendeur ou au stock OCD (dépôt-vente). |
| **Livraison** | Les frais de livraison par quartier (Douala, Lomé…) et l'envoi par agence vers les autres villes. |
| **Facturation** | La part de chaque vendeur (facture fournisseur créée quand le code du client est vérifié), les avoirs, les reversements payés par Mobile Money. |
| **Employés** | La régie, les animatrices des lives à distance, les livreurs OCD. |
| **Recrutement** | L'offre « Animatrice live · Lomé » sur le site et ses 5 étapes ; l'embauchée devient animatrice. |
| **Discuss** | Les canaux de l'équipe : nouveaux lives réservés, colis en retard ou en problème, caisse du soir. |
| **Activités** | Les tâches de l'équipe : choisir l'animatrice d'un live, rappeler un client, rembourser un colis retourné. |
| **Tâches automatiques** | Libérer un créneau non payé, rappeler un live la veille, relancer un vendeur en retard, préparer les reversements du lundi, ouvrir et fermer les créneaux de l'annuaire. |
| **Portail** | L'appli de livraison des vendeurs et des livreurs, la page de suivi d'une commande avec le code. |

## Modules complémentaires

| Module | Ce qu'il fait chez OCD Live |
|---|---|
| `whatsapp_cloud` | Les conversations WhatsApp avec les vendeurs et les clients dans Odoo, les messages automatiques validés par Meta, STOP et START. |
| `whatsapp_cloud_sale` | Les messages de la commande du shop au client : commande reçue, suivi. |
| `payment_campay` | Le paiement au Cameroun : MTN MoMo, Orange Money, carte (francs CFA d'Afrique centrale). |
| `delivery_cameroon` | Les villes et quartiers du Cameroun et le point de repère obligatoire dans l'adresse. |

## Modules d'OCD Live

| Module | Ce qu'il apporte |
|---|---|
| `ocd_live` | Réservations, paquets et lives à placer, prix selon l'heure, liste d'attente, annuaire et pass, espace vendeur, voix des pages, écrans de l'équipe. |
| `ocd_live_shop` | Mode de vente et « qui livre » par vendeur, colis par vendeur, code de livraison, dispatch, livreurs et caisse, reversements, régie en direct. |
| `ocd_live_whatsapp` | Messages des lives et de l'annuaire sur WhatsApp. |
| `ocd_live_shop_whatsapp` | Messages des colis sur WhatsApp. |
| `ocd_live_recruitment` | Recrutement des animatrices. |
| `ocd_delivery_togo` | Villes et quartiers du Togo, livraison à Lomé et vers les autres villes. |
| `ocd_live_demo` | Données de démonstration, retirées en désinstallant le module. |

## Applications payantes : pas besoin

| Application payante | Remplacée par |
|---|---|
| Planning | Le planning de la semaine d'`ocd_live` (écran Réservations). |
| Rendez-vous | La réservation d'un live sur le site, par `ocd_live`. |
| Abonnements | Le pass annuaire de 30 jours, avec son rappel avant la fin. |
| Field Service | L'appli de livraison sur le portail, avec le code du client. |
| Comptabilité | La Facturation suffit : parts des vendeurs, avoirs, reversements. |
| Studio | Les modules d'OCD Live, écrits, testés et versionnés. |
