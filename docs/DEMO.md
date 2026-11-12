# Présenter OCD Live avec la démo

La démo (`ocd_live_demo`) montre OCD Live **en service, le jour même de la présentation** : des
vendeurs dans 8 pays, des lives en cours, les lives de la semaine au studio, des replays, des colis à
Douala, et ce qui attend l'équipe. Une action planifiée la tient à jour toutes les 15 minutes : il n'y a
rien à refaire avant une présentation, quel que soit le jour.

## Les vendeurs de la démo

Chacun a une histoire cohérente : sa ville, ce qu'il vend, ses produits avec photos, son lien de live et
ses heures. Les vendeurs de Lomé viennent au studio ; les autres font leurs lives depuis chez eux, avec
une animatrice d'OCD (Dzifa Agbeko ou Kafui Amedome).

| Pays | Ville | Vendeur | Ce qu'il vend | Vente | Lives de l'annuaire | Lives réservés (heure de Lomé) |
|---|---|---|---|---|---|---|
| Togo | Lomé | Awa Mensah | Gâteaux et jus naturels | directe | matin, TikTok | studio (table) mar., ven. et sam. 10 h |
| Togo | Lomé | Ama Pagnes | Pagnes du Grand Marché | directe | après-midi, TikTok | studio (portant) mer. 17 h 30, sam. 14 h 30 |
| Togo | Lomé | Kossi Tech | Téléphones, écouteurs, chargeurs | directe | midi et soir, Facebook | studio (étagère) lun. et jeu. 10 h, sam. 13 h |
| Togo | Lomé | Yao Vaisselle | Vaisselle | nouveau vendeur, **à vérifier** | – | – |
| Cameroun | Douala, Akwa | Brenda Wax | Pagnes et robes en wax | **par OCD** (shop, livreurs OCD) | soir, TikTok | à distance lun., ven. et sam. 19 h |
| Cameroun | Douala, Makepe | Fatou Karité | Beurre de karité, savons | **par OCD** (elle livre) | midi, TikTok | à distance mer. 19 h, dim. 16 h |
| Cameroun | Douala | Papa Ndolé | Ndolé, poulet DG | directe | matin et après-midi, TikTok | à distance mer. 11 h 30, sam. 8 h 30 |
| Côte d'Ivoire | Abidjan | Junior Gadgets | Montres, smartphones | directe | midi, Facebook | à distance lun. 14 h 30, ven. 16 h |
| Côte d'Ivoire | Abidjan | Adjoua Attiéké | Attiéké, poisson braisé | directe | matin, TikTok | à distance jeu. 14 h 30 |
| Sénégal | Dakar | Aminata Déco | Paniers, service à thé | directe | après-midi, Instagram | à distance mar. 16 h, sam. 17 h 30 |
| Sénégal | Dakar | Moussa Bazin | Boubous en bazin brodé | directe | soir, TikTok | à distance jeu. 20 h 30, dim. 19 h |
| Bénin | Cotonou | Mireille Couture | Couture sur mesure | directe | soir, TikTok | à distance mar. 19 h, sam. 16 h |
| Ghana | Accra | Akua Kente | Kente tissé main | directe | après-midi, YouTube | à distance jeu. 19 h, sam. 20 h 30 |
| Nigeria | Lagos | Chioma Hair | Perruques, mèches | directe | midi, Instagram | à distance mar. 20 h 30 (**sans animatrice**) |
| France | Paris | Kadi Épices | Épicerie africaine (diaspora) | directe | matin, Instagram | à distance sam. 11 h 30 |

« Directe » : le client écrit au vendeur sur WhatsApp, paiement et livraison se voient avec lui.
« Par OCD » : le client paie sur le site, OCD livre à Douala.

Clients à Douala : Estelle Ngono (Akwa), Hervé Kuete (Bonabéri), Sandrine Fouda (Makepe), Ruth Mbarga
(Akwa), Bertrand Atangana (Bonamoussadi). Livreurs OCD : Junior Ekwalla, Raoul Nyobe, Christelle Mbarga
(en repos).

## Ce que la démo tient à jour

- **L'annuaire** a des lives de 8 h à 21 h (heure de Lomé), en quatre fenêtres de vérification : la
  démo ajoute « Midi » et « Après-midi » au matin et au soir d'OCD. Les vendeurs d'une fenêtre passent en
  live l'un après l'autre (les plats le matin pour les commandes de midi, téléphones et beauté à midi,
  maison et tissus l'après-midi, vêtements le soir). **Un lien attend toujours la vérification de
  l'équipe** (jamais un vendeur du Togo, pour que le visiteur de Lomé trouve ses vendeurs en live).
  Les liens de la fenêtre suivante sont envoyés une heure avant, ceux du matin la veille au soir.
- **La semaine du studio** (un live à la fois) : chaque live est payé à sa réservation (paquet
  Découverte, prix de l'heure : samedi soir +25 %, lundi matin −15 %). Le **samedi est complet** :
  Chioma Hair et Moussa Bazin sont sur la liste d'attente. Un live de Chioma n'a pas encore
  d'animatrice.
- **Les replays de la semaine passée**, publiés une heure après la fin du live, avec les produits
  montrés à la seconde près (3 par live au plus).
- **Un paiement à vérifier** : Kossi Tech a gardé un live au studio et dit avoir payé par Mobile Money
  (Flooz, numéro d'exemple). Quand l'équipe le confirme, un autre arrive le lendemain.
- **Brenda Wax** a acheté un Duo : un live placé à distance avec Dzifa, un live encore à placer.
- Chaque vendeur de l'annuaire a son pass ; un pass fini est racheté (certains finissent dans les jours
  qui viennent, pour le tableau de bord).

Ce que l'équipe fait pendant une présentation (refuser un lien, annuler ou déplacer un live) reste tel
quel : la démo n'ajoute que ce qui manque. Les liens finis depuis deux semaines et les lives non payés
annulés sont retirés.

## Scénario de présentation (20 minutes)

### 1. Le visiteur, sur son téléphone — `/lives`
- Le pays du visiteur vient d'abord (Togo à Lomé, Cameroun à Douala, France à Paris…), pour forcer un
  pays : `/lives?pays=sn`.
- Faire défiler comme sur TikTok : les lives en cours du pays, son prochain live et son dernier replay
  par vendeur, puis une carte par pays (« Sénégal · 2 lives en ce moment »).
- La barre des pays en haut : le nombre de lives en cours par pays ; toucher « Ghana » y mène.
- Sur une carte : « Regarder sur TikTok » (le live reste sur la plateforme), « Sa boutique », partager.

### 2. La boutique d'un vendeur
- **Ama Pagnes** ou **Kossi Tech** : prochain live et « Me prévenir sur WhatsApp », dernier replay,
  produits, « Écrire à Ama sur WhatsApp » (vente directe).
- **Brenda Wax** : boutique vendue par OCD, « Une question ? Écrire à OCD Live », paiement sur le site.

### 3. Le replay — boutique de Brenda › « Revoir »
- Le live se lit dans la page ; les produits montrés à la seconde : toucher « Robe en wax » saute au
  moment où elle est montrée, puis « Commander ».

### 4. Le shop, à Douala — `/shop`
- **Robe en wax** : la photo change avec la couleur (rouge), « Plus que 3 » en bleu M, taille L épuisée
  (« Préviens-moi sur WhatsApp »), le savon noir épuisé.
- Panier, adresse à Akwa (point de repère), un prix de livraison par colis, paiement à la livraison.

### 5. Le vendeur — `/ocd`
- Réserver un live : au studio ou chez soi, les heures dans le fuseau du vendeur, le samedi complet (liste
  d'attente), le paiement (Mobile Money vérifié par l'équipe, carte), le ticket PDF et l'image à partager.
- Pour montrer l'espace d'un vendeur de la démo : back-office › Vendeurs › Kossi Tech › **Voir son
  espace** (aucun code WhatsApp ne part vers un numéro de la démo).

### 6. L'équipe — back-office, application OCD Live
- **Tableau de bord** : lives du jour, pass actifs, colis, reversements, et « À traiter maintenant » :
  colis en retard, client absent, le lien à vérifier, le nouveau vendeur, le produit à vérifier, le
  live sans animatrice, les espèces d'un livreur.
- **Lives › Réservations** (planning) : la semaine pleine, le samedi complet ; le live de Kossi en
  « Paiement à vérifier » → « Paiement reçu : marquer payé ».
- **Lives › À vérifier** : publier le lien en attente ; il apparaît aussitôt dans le fil.
- **Livraisons** : dispatch des colis de Douala, caisse des livreurs, reversements.
- **WhatsApp** : les conversations (client qui attend une réponse, colis en route, plus de 24 h).

## Selon l'heure de la présentation (heure de Lomé, une heure de moins qu'à Douala et Paris en hiver)

| Heure | En live dans l'annuaire |
|---|---|
| 8 h – 11 h | Awa (Togo), Papa (Cameroun), Adjoua (Côte d'Ivoire), Kadi (France) |
| 11 h – 14 h 30 | Kossi (Togo), Fatou (Cameroun), Junior (Côte d'Ivoire), Chioma (Nigeria) |
| 14 h 30 – 18 h | Ama (Togo), Papa (Cameroun), Aminata (Sénégal), Akua (Ghana) |
| 18 h – 21 h | Kossi (Togo), Brenda (Cameroun), Mireille (Bénin), Moussa (Sénégal) |
| La nuit | Annuaire fermé : le fil le dit, puis les prochains lives et les replays |

S'y ajoute le live du studio en cours, d'après la semaine ci-dessus.

## Avant de présenter

- **Une démo installée avant le 12 novembre 2026** : mettre à jour `ocd_live_demo` (Applications ›
  Mettre à jour la liste des applications, puis le module › Mettre à jour). La mise à jour installe aussi
  `ocd_live_demo_whatsapp` et met le nouveau scénario en place.
- L'action planifiée **« Démo d'OCD Live : garder les lives de la démo à jour »** tourne toutes les 15
  minutes. Après un arrêt du serveur, son premier passage remet tout à jour (ou « Exécuter » dans
  Paramètres › Technique › Actions planifiées).
- **Les liens sont des exemples** : les comptes TikTok, Facebook, Instagram et YouTube des vendeurs
  n'existent pas. Pour un replay qui se lit vraiment, coller le lien d'une vraie vidéo d'OCD Live dans le
  replay d'un live (Lives › Réservations › le live › Lien du replay) : la démo ne le remplace pas.
- **Les numéros sont des exemples** : aucun message WhatsApp ne part vers les contacts de la démo, même
  avec le vrai compte WhatsApp connecté (`ocd_live_demo_whatsapp`). Pour montrer un vrai message,
  inscrire un vendeur avec son propre numéro.
- La démo ouvre les réservations sans date d'ouverture (les lives de la semaine passée ont eu lieu).

## Retirer la démo

Désinstaller `ocd_live_demo` (Applications) : contacts, produits, photos, lives, commandes, colis,
paiements, conversations et fenêtres de la démo sont retirés ; les moyens de paiement et la date
d'ouverture des réservations reviennent comme avant. `ocd_live_demo_whatsapp` part avec elle.
