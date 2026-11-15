"""Combien de cœurs pour N visiteurs par jour (docs/RAPPORT_DE_CHARGE.md, partie 7).

Part des coûts mesurés (temps de processeur d'Odoo et de PostgreSQL pour une page donnée depuis la
mémoire et pour une page construite) et d'une audience (pages par visiteur, poids des pages, adresses
différentes, durée de la mémoire de chaque page), et calcule la pointe d'un live : pages et questions
par seconde, part donnée depuis la mémoire, cœurs d'Odoo et de PostgreSQL (occupés à 70 %).

Chaque worker d'Odoo garde ses propres pages : une adresse demandée r fois par seconde, gardée T
secondes, sur W workers, est construite r / (1 + r·T/W) fois par seconde. Plus il y a de workers et
d'adresses différentes (produits, boutiques, pays, langues), moins les pages viennent de la mémoire.

Exemples :
    python3 tools/charge/dimensionnement.py                 # 3 millions de visiteurs par jour
    python3 tools/charge/dimensionnement.py 1000000 --catalogue demo
    python3 tools/charge/dimensionnement.py --partagee     # une mémoire des pages commune aux workers

Les chiffres d'audience sont des hypothèses : les remplacer par ceux d'un vrai soir (journal de nginx,
tableau de bord du CDN), et les coûts par ceux des vrais serveurs (partie 6 du rapport).
"""

import argparse

# Coût en millisecondes de processeur (Odoo, PostgreSQL), mesuré le 15 novembre 2026 sur la machine de
# test (Odoo 20, 4 workers, base de démo) : (depuis la mémoire, construite)
COUTS = {
    "fil": ((2.4, 0.6), (42.2, 9.3)),
    "live": ((2.3, 0.6), (12.9, 2.6)),
    "shop": ((2.4, 0.7), (48.6, 13.3)),
    "produit": ((5.8, 1.4), (97.1, 27.3)),
    "boutique": ((3.8, 1.2), (38.3, 8.1)),
    "reservation": ((22.7, 4.3), (22.7, 4.3)),  # jamais gardée en mémoire
    "q_nouveaux": ((2.1, 0.6), (2.1, 0.6)),  # jamais gardée (une question légère)
    "q_flux": ((2.2, 0.5), (51.3, 16.1)),
    "q_ecran": ((2.2, 0.6), (4.3, 1.5)),
}

# L'audience : part des pages, durée de la mémoire (s), et comment les visites se partagent entre les
# adresses : [(part des visites, nombre d'adresses)], chaque adresse existant en autant de variantes
# que de couples langue × pays des visiteurs (VARIANTES)
CATALOGUES = {
    # Un vrai catalogue : 20 lives à la fois (10 produits chacun), 300 boutiques, 6 000 produits
    "grand": {
        "fil": (0.30, 20, [(1.0, 2)]),  # le fil, et sa seconde page
        "live": (0.15, 15, [(1.0, 20)]),
        "shop": (0.20, 60, [(0.6, 1), (0.4, 40)]),  # le shop, puis ses catégories et ses pages
        "produit": (0.20, 30, [(0.6, 200), (0.4, 6000)]),  # les produits des lives du moment, puis les autres
        "boutique": (0.10, 15, [(0.8, 20), (0.2, 300)]),
        "reservation": (0.05, 0, [(1.0, 1)]),
    },
    # La démo, comme le parcours de charge.py
    "demo": {
        "fil": (0.30, 20, [(1.0, 1)]),
        "live": (0.15, 15, [(1.0, 1)]),
        "shop": (0.20, 60, [(1.0, 1)]),
        "produit": (0.20, 30, [(1.0, 1)]),
        "boutique": (0.10, 15, [(1.0, 1)]),
        "reservation": (0.05, 0, [(1.0, 1)]),
    },
}
# Part des visiteurs de chaque couple langue × pays (le pays et la langue font une autre page)
VARIANTES = [0.30, 0.25, 0.12, 0.08, 0.06, 0.05, 0.04, 0.04, 0.03, 0.03]

# Les questions que les pages posent seules, pendant qu'elles sont à l'écran
SECONDES_SUR_LE_FIL = 60  # une question « nouveaux lives » par minute
SECONDES_DANS_UNE_BOUTIQUE = 180  # pendant un live : « produit à l'écran » toutes les 20 s
CARTES_SUIVANTES_PAR_FIL = 1  # le fil qu'on fait défiler demande les cartes suivantes


# Le calcul retrouve la part des pages données depuis la mémoire mesurée avec charge.py (95, 94 et 88 %
# pour 95, 93 et 88 % mesurés), mais compte environ 15 % de processeur de moins que la mesure
# (redirections, connexions) : les cœurs sont comptés avec cet écart
ECART = 1.15


def nombre(x):
    return f"{x:,.0f}".replace(",", " ")


def construites(r, ttl, workers):
    """Pages construites par seconde pour une adresse demandée r fois par seconde."""
    if not ttl:
        return r
    return r / (1 + r * ttl / workers)


def charge(rythme, ttl, partage, workers):
    """(pages par seconde, construites par seconde) d'un type de page."""
    total = built = 0.0
    for part, adresses in partage:
        for variante in VARIANTES:
            r = rythme * part * variante / adresses
            total += r * adresses
            built += construites(r, ttl, workers) * adresses
    return total, built


def calcul(pointe, catalogue, workers, partagee=False):
    """(lignes, secondes de processeur d'Odoo et de PostgreSQL par seconde). `partagee` : une mémoire
    des pages commune à tous les workers (une seule copie de chaque page)."""
    copies = 1 if partagee else workers
    lignes = {}
    for nom, (part, ttl, partage) in CATALOGUES[catalogue].items():
        lignes[nom] = charge(pointe * part, ttl, partage, copies)
    fil = pointe * CATALOGUES[catalogue]["fil"][0]
    boutique = pointe * CATALOGUES[catalogue]["boutique"][0]
    lignes["q_nouveaux"] = (fil * SECONDES_SUR_LE_FIL / 60, fil * SECONDES_SUR_LE_FIL / 60)
    lignes["q_flux"] = charge(fil * CARTES_SUIVANTES_PAR_FIL, 20, [(1.0, 4)], copies)
    lignes["q_ecran"] = charge(boutique * SECONDES_DANS_UNE_BOUTIQUE / 20, 10, [(0.8, 20), (0.2, 300)], copies)
    odoo = pg = 0.0
    for nom, (total, built) in lignes.items():
        (memoire_odoo, memoire_pg), (construite_odoo, construite_pg) = COUTS[nom]
        odoo += (total - built) * memoire_odoo + built * construite_odoo
        pg += (total - built) * memoire_pg + built * construite_pg
    return lignes, odoo / 1000, pg / 1000


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("visiteurs", type=int, nargs="?", default=3_000_000, help="visiteurs par jour")
    parser.add_argument("--pages", type=float, default=5, help="pages par visiteur")
    parser.add_argument("--pointe", type=float, default=10, help="la pointe d'un live, en fois la moyenne")
    parser.add_argument("--catalogue", choices=sorted(CATALOGUES), default="grand")
    parser.add_argument("--occupation", type=float, default=0.7, help="processeurs occupés au plus (0.7 : 70 %%)")
    parser.add_argument("--partagee", action="store_true", help="une mémoire des pages commune à tous les workers")
    args = parser.parse_args()

    pointe = args.visiteurs * args.pages / 86400 * args.pointe
    print(f"{nombre(args.visiteurs)} visiteurs par jour, {args.pages:g} pages chacun : pointe d'un live "
          f"{nombre(pointe)} pages/s (catalogue « {args.catalogue} »"
          f"{', mémoire commune aux workers' if args.partagee else ''})")
    # Les workers dépendent des cœurs, qui dépendent des pages construites : on cherche l'équilibre
    workers = 8
    for _ in range(50):
        lignes, odoo, pg = calcul(pointe, args.catalogue, workers, args.partagee)
        coeurs_odoo = odoo * ECART / args.occupation
        nouveaux = max(8, round(2 * coeurs_odoo))  # deux workers par cœur
        if nouveaux == workers:
            break
        workers = nouveaux
    pages = sum(total for nom, (total, _b) in lignes.items() if not nom.startswith("q_"))
    questions = sum(total for nom, (total, _b) in lignes.items() if nom.startswith("q_"))
    built = sum(b for _t, b in lignes.values())
    print(f"  questions des pages à l'écran : {nombre(questions)}/s ; workers d'Odoo : {workers}")
    for nom, (total, b) in lignes.items():
        print(f"  {nom:<12} {total:7.0f}/s, depuis la mémoire {100 * (1 - b / total) if total else 0:5.1f} %")
    print(f"  depuis la mémoire, en tout : {100 * (1 - built / (pages + questions)):.0f} %")
    print(f"  cœurs d'Odoo : {odoo * ECART / args.occupation:.0f} ; cœurs de PostgreSQL : "
          f"{pg * ECART / args.occupation:.0f} (occupés à {args.occupation:.0%})")


if __name__ == "__main__":
    main()
