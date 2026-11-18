# Chantier 5: the automatic payments of the UEMOA (CinetPay, Flutterwave), the settings of OCD Live
PAYMENTS_SHOP = {
    "%s In test mode: no real payment until « Live » is ticked on the provider.":
        "%s En mode test : aucun vrai paiement tant que « Live » n'est pas coché sur le fournisseur.",
    "%s Its keys are not entered yet: Website › Configuration › Payment providers.":
        "%s Ses clés ne sont pas encore saisies : Site Web › Configuration › Fournisseurs de paiement.",
    "The vendors and the customers of these countries pay with the payments checked by the team (Mobile Money, cash at the studio) or at the door. CinetPay (UEMOA, Cameroon) and Flutterwave take the Mobile Money once their keys are entered and they are published; the card payment (Stripe) takes every country.":
        "Les vendeurs et les clients de ces pays paient avec les paiements vérifiés par l'équipe (Mobile Money, espèces au studio) ou à la livraison. CinetPay (UEMOA, Cameroun) et Flutterwave prennent le Mobile Money une fois leurs clés saisies et publiés ; la carte (Stripe) prend tous les pays.",
}

CINETPAY = {
    "API Key": "Clé d'API",
    "Amount Asked To CinetPay": "Montant demandé à CinetPay",
    "Card": "Carte",
    "CinetPay": "CinetPay",
    "CinetPay API Key": "Clé d'API CinetPay",
    "CinetPay Secret Key": "Clé secrète CinetPay",
    "CinetPay Site ID": "Identifiant du site CinetPay",
    "CinetPay Transaction": "Transaction CinetPay",
    "CinetPay did not open the payment: %s": "CinetPay n'a pas ouvert le paiement : %s",
    "CinetPay: check the payments still waiting": "CinetPay : vérifier les paiements encore en attente",
    "Mobile Money (Orange, MTN, Moov, Free, Wave...) and cards in the UEMOA and Central Africa with CinetPay":
        "Mobile Money (Orange, MTN, Moov, Free, Wave…) et cartes dans l'UEMOA et en Afrique centrale avec CinetPay",
    "Mobile Money (Orange, MTN, Moov, T-Money, Flooz...)": "Mobile Money (Orange, MTN, Moov, T-Money, Flooz…)",
    "Order %(reference)s on %(company)s": "Commande %(reference)s sur %(company)s",
    "Payment Provider: CinetPay": "Fournisseur de paiement : CinetPay",
    "Code": "Code",
    "Payment Provider": "Fournisseur de paiement",
    "Payment Transaction": "Transaction de paiement",
    "Your payment has been authorized.": "Ton paiement a été autorisé.",
    "Your payment has been cancelled.": "Ton paiement a été annulé.",
    "Your payment has been processed.": "Ton paiement a été traité.",
    "Secret Key": "Clé secrète",
    "Site ID": "Identifiant du site",
    "The amount of the transaction, rounded up to a multiple of 5 in CFA francs (rule of CinetPay).":
        "Le montant de la transaction, arrondi au multiple de 5 supérieur en francs CFA (règle de CinetPay).",
    "The identifier given to CinetPay: the reference with letters, numbers and dashes only.":
        "L'identifiant donné à CinetPay : la référence avec seulement des lettres, des chiffres et des tirets.",
    "The identifier of the site, in « Integration » of the dashboard of CinetPay.":
        "L'identifiant du site, dans « Intégration » du tableau de bord de CinetPay.",
    "The keys of the site are in « Integration » of the dashboard of CinetPay. The notifications go to\n                        <code>https://your-domain/payment/cinetpay/webhook</code>, given with each payment. In CFA francs,\n                        CinetPay takes multiples of 5: the amount is rounded up by a few francs at most.":
        "Les clés du site sont dans « Intégration » du tableau de bord de CinetPay. Les notifications vont à\n                        <code>https://votre-domaine/payment/cinetpay/webhook</code>, donnée avec chaque paiement. En francs CFA,\n                        CinetPay prend des multiples de 5 : le montant est arrondi de quelques francs au plus.",
    "The payment was refused or cancelled, or the balance was insufficient (%s).":
        "Le paiement a été refusé ou annulé, ou le solde était insuffisant (%s).",
    "The secret key of the site (signature of the notifications); the state of a payment is read from CinetPay anyway.":
        "La clé secrète du site (signature des notifications) ; l'état d'un paiement est de toute façon lu chez CinetPay.",
    "The technical code of this payment provider.": "Le code technique de ce fournisseur de paiement.",
    "Wave and the wallets": "Wave et les portefeuilles",
    "Your payment is being confirmed by CinetPay. Your order is confirmed as soon as the payment is received.":
        "Ton paiement est en cours de confirmation par CinetPay. Ta commande est confirmée dès que le paiement est reçu.",
}

CINETPAY_DESCRIPTION = """
Fournisseur de paiement CinetPay
===============================

- Le Mobile Money de l'UEMOA (Côte d'Ivoire, Sénégal, Togo, Bénin, Mali, Burkina
  Faso, Niger) et du Cameroun, de la Guinée et de la RD Congo : Orange Money, MTN,
  Moov, Free, T-Money, Flooz…, Wave et les autres portefeuilles, et les cartes,
  sur la page de paiement de CinetPay.
- Le montant demandé à CinetPay est un multiple de 5 en francs CFA (règle de
  CinetPay) : arrondi de quelques francs au plus, la commande est payée pour son
  propre montant.
- L'état d'un paiement est toujours lu chez CinetPay (API de vérification),
  jamais dans les paramètres de la notification ou du retour.
- Les paiements encore en attente sont vérifiés de nouveau toutes les 10 minutes
  pendant un jour, au cas où une notification se serait perdue.
"""
