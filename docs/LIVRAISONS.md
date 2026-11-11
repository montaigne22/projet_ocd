# Frais de livraison : un prix par colis

Ce guide explique comment OCD Live calcule le prix de la livraison, ce que l'équipe doit régler avant
l'ouverture, et où le code se trouve. Le module concerné est `ocd_live_shop`.

## En bref

- Une commande du shop donne **un colis par vendeur**. Chaque colis a **son propre prix de livraison**,
  calculé de la **ville d'où il part** (celle du vendeur, ou du stock OCD) jusqu'au **quartier, à la
  ville ou au pays du client**.
- Le client paie **la somme des colis**. Le détail s'affiche sur les pages « On livre où ? » et « Payer ».
- Une adresse qu'un colis ne peut pas atteindre est **refusée avant le paiement**, avec la raison et un
  bouton pour retirer les produits de ce vendeur. Une commande n'est jamais payée pour un colis que
  personne ne peut livrer.

## Exemples

Panier avec deux vendeuses de Douala : Brenda (un livreur OCD passe chez elle) et Fatou (elle livre
elle-même et a ses prix pour Akwa et Makepe). Tarifs d'OCD : livreur OCD dans Douala 1 000 F, agence vers
les autres villes du Cameroun 2 500 F, agence vers le Togo 6 000 F.

| Client à… | Colis de Brenda | Colis de Fatou | Total | Paiement à la livraison |
|---|---|---|---|---|
| Douala, Akwa | 1 000 F (livreur OCD) | 800 F (son prix pour Akwa) | **1 800 F** | oui |
| Douala, Makepe | 1 000 F (livreur OCD) | 500 F (son prix pour Makepe) | **1 500 F** | oui |
| Douala, Bonabéri (hors des zones de Fatou) | 1 000 F (livreur OCD) | 1 000 F (un livreur OCD prend le relais) | **2 000 F** | oui |
| Yaoundé | 2 500 F (agence) | 2 500 F (agence) | **5 000 F** | non |
| Lomé (Togo) | 6 000 F (agence) | 6 000 F (agence) | **12 000 F** | non |

## Les tarifs

Un tarif se règle dans **OCD Live › Livraisons › Tarifs de livraison** (ou, pour un vendeur, sur sa fiche
et dans son espace).

| Qui livre | Qui fixe le prix | Part de | Vers |
|---|---|---|---|
| **Le vendeur** | le vendeur (dans son espace) ou l'équipe (fiche du vendeur) | la ville du vendeur | des quartiers ou des villes |
| **Un livreur OCD** | l'équipe | une ville (« Depuis la ville ») | des quartiers ou des villes |
| **Une agence de voyage** | l'équipe | un pays ou une ville | une ville ou un pays entier (autre ville, autre pays) |

Champs d'un tarif :

- **Vers** : le pays, puis éventuellement des villes, puis éventuellement des quartiers. Vide veut dire
  « tout » : pas de ville = tout le pays ; pas de quartier = toutes les villes choisies.
- **Prix**, dans une devise (celle de la société par défaut ; Odoo convertit dans la devise du client).
- **Offerte à partir de** : la livraison est gratuite quand les produits du colis coûtent au moins ce
  montant (0 = jamais).
- **Pour le client** : le texte affiché, par exemple « Livré sous 24 à 48 h ».
- **Paiement à la porte** : autorisé ou non pour ce tarif.
- **Séquence** : entre deux tarifs aussi précis l'un que l'autre, le premier est utilisé.
- Un tarif **archivé** n'est plus utilisé ; les commandes déjà payées gardent leur prix.

## Comment le prix d'un colis est choisi

Pour chaque colis, dans cet ordre :

1. **Le vendeur livre lui-même** (« qui livre » = le vendeur) et a un prix pour l'adresse : son prix.
2. Sinon, si l'adresse est **dans ses zones** (les quartiers de sa fiche, ou toute sa ville s'il n'a pas
   de zone) : il livre au **prix du livreur OCD** de sa ville.
3. Sinon, si l'équipe l'autorise (« hors de ces quartiers, un livreur OCD passe chercher le colis ») :
   un **livreur OCD** ou une **agence** part de la ville du vendeur, au tarif d'OCD.
4. Les vendeurs dont un livreur OCD passe chercher les colis utilisent directement les tarifs d'OCD
   depuis leur ville ; les produits du **stock OCD** et ceux d'OCD Live partent de la **ville du stock**.

Entre plusieurs tarifs possibles, **le plus précis l'emporte** : un tarif pour le quartier passe avant
celui de la ville, qui passe avant celui du pays ; puis la ville de départ précise passe avant le pays de
départ ; puis la séquence ; puis le moins cher.

Garde-fous :

- **Jamais d'agence à l'intérieur d'une même ville** : sans tarif de livreur OCD dans une ville, l'adresse
  de cette ville est refusée plutôt que confiée à une agence.
- **Pas de paiement à la livraison** par agence, ni vers un autre pays. Le paiement à la livraison n'est
  proposé au client que si **tous** ses colis l'acceptent.
- **Prix des vendeurs dans les bornes** fixées par l'équipe : un prix hors bornes est refusé et n'est pas
  enregistré.
- Aucun tarif pour l'adresse : la commande est refusée avant le paiement (jamais une livraison à un prix
  inconnu ou gratuit par erreur).

## Ce que voit le client

- **Fiche produit** : « Envoyé depuis Douala », les principaux prix (par exemple « Douala : 1 000 F »,
  « Cameroun : 2 500 F ») et « Le prix exact pour ton quartier s'affiche à l'étape Livraison ».
- **On livre où ?** : le pays (celui choisi dans le shop par défaut), la ville, le quartier, le point de
  repère ; puis une ligne par colis, mise à jour pendant la saisie : « Colis de Brenda Wax · depuis Douala ·
  livré par un livreur OCD · 1 000 F ». Un vendeur qui ne livre pas l'adresse affiche la raison et
  « Retirer ses produits ».
- **Payer** : les produits, puis « Livraison du colis de… » pour chaque colis, puis le total.

## Ce que voit le vendeur

- **Mes prix de livraison** (dans son espace, `/ocd/espace/moi/livraison`) : ses prix par ville ou par
  quartiers, avec le délai, dans les bornes de l'équipe (affichées) ; il peut en retirer (le prix est
  archivé). Il voit aussi les prix d'OCD Live depuis sa ville.
- Un vendeur dont OCD livre les colis voit seulement les prix d'OCD Live.
- Chaque prix ajouté ou retiré est noté dans l'historique de la fiche du vendeur.

## L'argent

- Chaque colis garde **son prix exact**, tel que le client l'a payé (onglet « Livraison de chaque colis »
  de la commande). Si l'équipe change à la main la livraison d'une commande, les prix des colis sont
  ajustés dans la même proportion.
- **Le vendeur qui livre** touche le prix de son colis **moins la part d'OCD** (réglage, 0 % au départ) :
  ligne « Livraison » de sa facture, dans son prochain reversement.
- **Les livraisons des livreurs OCD et des agences** reviennent à OCD (tableau de bord : « Frais de
  livraison gardés par OCD », avec la part d'OCD sur les livraisons des vendeurs).
- **Colis par agence** : un livreur OCD de la ville de départ le porte à l'agence (l'appli lui indique
  « Porter à l'agence de voyage pour… ») ; l'équipe valide le colis (sans code, avec un motif) quand le
  client l'a retiré.

## Mise en route (avant l'ouverture)

1. **Paramètres › Prix de livraison** : cliquer sur « Créer les tarifs depuis les modes de
   livraison ». Les modes de livraison par ville (Douala, Lomé, autres villes…) deviennent des tarifs
   d'OCD : actifs s'ils étaient publiés avec un prix, **archivés** sinon. (C'est fait une première
   fois à l'installation ; le bouton sert pour les modes ajoutés ensuite.)
2. **OCD Live › Livraisons › Tarifs de livraison** : filtre « Archivé », mettre les prix, désarchiver.
   Ajouter les tarifs manquants : un tarif « livreur OCD » par ville où OCD a des livreurs, un tarif
   « agence » par pays de départ (autres villes du pays), et un tarif « agence » vers chaque autre pays
   servi.
3. **Paramètres › Prix de livraison** : les bornes des prix des vendeurs, la part d'OCD sur leurs
   livraisons, la **ville du stock OCD**.
4. Sur la fiche de chaque vendeur qui livre : sa **ville**, ses **zones**, et ses prix si l'équipe les
   saisit pour lui (sinon il les saisit dans son espace).
5. **Site Web › Configuration › eCommerce › Livraisons** : « Livraison OCD Live » doit être **publiée**
   (elle l'est à l'installation). Une fois publiée, c'est la seule proposée par le shop ; ne pas republier
   la « Livraison standard » d'Odoo ni les anciens modes par ville.
6. Pour le paiement à la livraison : publier le moyen de paiement « Paiement comptant à la livraison ».

## Questions fréquentes

**Le client voit « … ne livre pas encore à … ».** Aucun tarif ne couvre l'adresse pour ce vendeur :
ajouter un tarif (livreur OCD dans la ville, agence vers la ville ou le pays), ou autoriser un livreur OCD
hors des zones du vendeur sur sa fiche. Le client peut aussi retirer les produits de ce vendeur.

**L'adresse est refusée dans la ville du vendeur.** Il manque le tarif « livreur OCD » de cette ville : une
agence n'est jamais utilisée à l'intérieur d'une ville.

**Le paiement à la livraison n'apparaît pas.** Un des colis passe par une agence ou va vers un autre pays,
ou son tarif n'autorise pas le paiement à la porte. Ou le moyen de paiement n'est pas publié.

**Le vendeur n'arrive pas à enregistrer son prix.** Il est hors des bornes affichées sous le champ.

**Une ancienne commande n'a pas de détail par colis.** Elle a été payée avec un autre mode de
livraison : son prix est partagé à parts égales entre ses colis, comme avant.

**Un vendeur change son prix après une commande.** La commande garde le prix payé ; le nouveau prix vaut
pour les commandes suivantes.

## Pour les développeurs

| Où | Quoi |
|---|---|
| `models/ocd_delivery_rate.py` | Les tarifs et le moteur : `_ocd_quote` (le prix d'un colis), `_ocd_find_rate` (les règles 1 à 4), `_ocd_best` (le plus précis, pas d'agence dans la ville), `_ocd_price` (devise, offerte à partir de), `_ocd_allows_cod`, `_ocd_summary` (fiche produit), `_ocd_rates_from_carriers` |
| `models/delivery_carrier.py` | Type de mode de livraison `ocd` : `ocd_rate_shipment` (somme des colis ou refus), `_is_available_for_order` |
| `models/sale_order.py` | `_ocd_delivery_groups`, `_ocd_delivery_quotes`, `ocd_delivery_line_ids` (gardés par `set_delivery_line` et `_verify_cart_after_update`), `_get_delivery_methods` (seule la livraison d'OCD une fois publiée), `_ocd_cod_allowed`, `_ocd_parcel_delivery` |
| `models/ocd_order_delivery.py` | La livraison de chaque colis d'une commande, telle que payée |
| `models/payment_provider.py` | Paiement à la livraison seulement si chaque colis l'accepte |
| `models/stock_picking.py` | `_ocd_parcel_from_delivery` (qui livre, agence), `ocd_fee_amount` (prix exact), `ocd_vendor_fee_amount` (part du vendeur) |
| `controllers/shop.py` | Aperçu par colis (`/ocd/livraison/tarif`), refus et `/ocd/panier/retirer` |
| `controllers/vendor_rates.py` | « Mes prix de livraison » du vendeur |
| `tests/test_delivery_rates.py` | Les règles, l'argent, le paiement à la livraison, les pages |

Chaque règle est une méthode à part : un module peut en changer une sans recopier les autres (par
exemple un prix selon le poids dans `_ocd_price`, ou un plafond par commande dans `ocd_rate_shipment`).
