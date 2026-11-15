"""Test de charge des pages publiques d'OCD Live (docs/RAPPORT_DE_CHARGE.md).

N visiteurs à la fois pendant S secondes, répartis sur plusieurs processus (un processus Python
seul ne charge pas un serveur : il n'utilise qu'un cœur). Chaque visiteur garde ses cookies, comme
un téléphone, et ouvre les pages du parcours au hasard, selon leur poids. À la fin : pages par
seconde, temps médian, p95, p99, erreurs et part des pages données depuis la mémoire (en-tête
X-OCD-Cache: hit).

Exemples :
    python3 tools/charge/charge.py 32 60
    python3 tools/charge/charge.py 200 300 --processes 8 --base https://preprod.ocdlive.com
    python3 tools/charge/charge.py 32 60 --nouveaux    # chaque page par un nouveau visiteur

La machine qui lance le test ne doit pas être le serveur testé : elle lui prendrait ses cœurs.
Pour des milliers de visiteurs, lancer le test depuis plusieurs machines à la fois et additionner.
"""

import argparse
import http.cookiejar
import multiprocessing
import random
import statistics
import threading
import time
import urllib.request

# Le parcours : (page, poids). Les adresses sont celles de la démo ; les changer pour une autre base.
PARCOURS = [
    ("/lives", 30),
    ("/lives/cm/39", 15),
    ("/shop", 20),
    ("/shop/robe-en-wax-20", 20),
    ("/ocd/boutique/6", 10),
    ("/reserver/studio", 5),
]


def visiteurs(base, nombre, fin, nouveaux, pages, file):
    temps, erreurs, memoire = [], [0], [0]
    verrou = threading.Lock()

    def visiteur():
        ouvreur = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        while time.time() < fin:
            if nouveaux:
                ouvreur = urllib.request.build_opener()
            debut = time.time()
            ok = depuis_memoire = False
            try:
                with ouvreur.open(base + random.choice(pages), timeout=30) as reponse:
                    reponse.read()
                    ok = reponse.status == 200
                    depuis_memoire = reponse.headers.get("X-OCD-Cache") == "hit"
            except Exception:  # noqa: BLE001 (une page qui n'arrive pas est une erreur)
                pass
            duree = time.time() - debut
            with verrou:
                temps.append(duree)
                erreurs[0] += not ok
                memoire[0] += depuis_memoire

    fils = [threading.Thread(target=visiteur) for _ in range(nombre)]
    for fil in fils:
        fil.start()
    for fil in fils:
        fil.join()
    file.put((temps, erreurs[0], memoire[0]))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("visiteurs", type=int, help="visiteurs à la fois")
    parser.add_argument("secondes", type=int, help="durée du palier")
    parser.add_argument("--processes", type=int, default=4, help="processus (un par cœur de la machine de test)")
    parser.add_argument("--base", default="http://127.0.0.1:8069", help="adresse du site testé")
    parser.add_argument("--nouveaux", action="store_true", help="chaque page par un nouveau visiteur (sans cookies)")
    args = parser.parse_args()

    pages = [page for page, poids in PARCOURS for _ in range(poids)]
    fin = time.time() + args.secondes
    file = multiprocessing.Queue()
    parts = [args.visiteurs // args.processes + (i < args.visiteurs % args.processes) for i in range(args.processes)]
    jobs = [
        multiprocessing.Process(target=visiteurs, args=(args.base.rstrip("/"), part, fin, args.nouveaux, pages, file))
        for part in parts if part
    ]
    for job in jobs:
        job.start()
    temps, erreurs, memoire = [], 0, 0
    for _job in jobs:
        part_temps, part_erreurs, part_memoire = file.get()
        temps += part_temps
        erreurs += part_erreurs
        memoire += part_memoire
    for job in jobs:
        job.join()
    if not temps:
        print("Aucune page : le site répond-il ?")
        return
    temps.sort()
    total = len(temps)

    def quantile(q):
        return temps[min(int(total * q), total - 1)] * 1000

    print(f"{args.visiteurs} visiteurs à la fois, {args.secondes} s : {total} pages, {total / args.secondes:.0f} pages/s, "
          f"médiane {statistics.median(temps) * 1000:.0f} ms, p95 {quantile(0.95):.0f} ms, p99 {quantile(0.99):.0f} ms, "
          f"erreurs {erreurs} ({erreurs * 100 / total:.2f} %), depuis la mémoire {memoire * 100 / total:.0f} %")
    # Une ligne pour le tableau du rapport
    print(f"| {args.visiteurs} | {args.secondes} s | {total / args.secondes:.0f} | {statistics.median(temps) * 1000:.0f} ms "
          f"| {quantile(0.95):.0f} ms | {quantile(0.99):.0f} ms | {erreurs * 100 / total:.2f} % | {memoire * 100 / total:.0f} % |")


if __name__ == "__main__":
    main()
