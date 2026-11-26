"""Test de charge du parcours d'achat (docs/RAPPORT_DE_CHARGE.md, partie 10) : ces pages ne viennent
jamais de la mémoire. Chaque client virtuel, comme un téléphone qui garde ses cookies : la fiche d'un
produit, l'ajout au panier (première couleur, première taille), le panier, l'adresse de livraison
(le pays --pays, sa première ville et son premier quartier, un numéro WhatsApp du pays), la page du
paiement. Il s'arrête avant de
payer : aucune commande n'est confirmée, mais chaque parcours laisse un panier et un contact.
Seulement sur une copie de la démo ou un serveur de test, jamais en production.

    python3 tools/charge/achat.py 8 60 --base http://127.0.0.1:8069 --produit /shop/robe-en-wax-38 --pays Cameroun

À la fin : parcours finis par minute, temps de chaque étape (médiane, p95), erreurs.
"""
import argparse
import html.parser
import json
import http.cookiejar
import random
import statistics
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


class Form(html.parser.HTMLParser):
    """The fields of the form whose action is `action`, as a browser would send them: the hidden and
    the text fields with their value, the first choice of each group of radio buttons (or the one
    checked), the first option of each list (or the one selected)."""

    def __init__(self, action):
        super().__init__()
        self.action, self.inside, self.select, self.fields, self.radios = action, False, None, {}, {}
        self.options, self.option = {}, None  # each list: [(value, label)]

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.inside = attrs.get("action", "").split("?")[0] == self.action
        if not self.inside or not attrs.get("name"):
            if tag == "option" and self.inside and self.select:
                name, chosen = self.select
                value = attrs.get("value", "")
                self.option = [value, ""]
                self.options.setdefault(name, []).append(self.option)
                if value and (name not in self.fields or ("selected" in attrs and not chosen)):
                    self.fields[name] = value
                    self.select = (name, "selected" in attrs)
            return
        name = attrs["name"]
        if tag == "input":
            kind = attrs.get("type", "text")
            if kind in ("radio", "checkbox"):
                if name not in self.radios or "checked" in attrs:
                    self.radios[name] = attrs.get("value", "on")
            elif kind not in ("submit", "button", "file"):
                self.fields.setdefault(name, attrs.get("value", ""))
        elif tag == "select":
            self.select = (name, False)
        elif tag == "textarea":
            self.fields.setdefault(name, "")

    def handle_data(self, data):
        if self.option is not None:
            self.option[1] += data.strip()

    def handle_endtag(self, tag):
        if tag == "option":
            self.option = None
        if tag == "form":
            self.inside = False
        if tag == "select":
            self.select = None

    def values(self):
        return {**self.fields, **self.radios}


def fields(page, action):
    form = Form(action)
    form.feed(page)
    return form.values()


def options(page, action, name):
    form = Form(action)
    form.feed(page)
    return form.options.get(name, [])


def journey(base, product, number, country):
    """One purchase until the page of the payment: the time of each step."""
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    steps = []

    def step(name, path, data=None):
        start = time.time()
        with opener.open(base + path, urllib.parse.urlencode(data).encode() if data is not None else None, timeout=60) as response:
            page = response.read().decode("utf-8", "replace")
            final = response.geturl()
        steps.append((name, time.time() - start))
        return page, final

    page, _final = step("fiche produit", product)
    values = fields(page, "/ocd/panier/ajouter")
    values["quantity"] = "1"
    page, final = step("ajout au panier", "/ocd/panier/ajouter", values)
    if "/shop/cart" not in final:
        raise RuntimeError(f"ajout refusé ({final})")
    page, _final = step("adresse (formulaire)", "/shop/checkout")
    countries = dict((label, value) for value, label in options(page, "/ocd/livraison", "delivery_country_id"))
    if country in countries and fields(page, "/ocd/livraison").get("delivery_country_id") != countries[country]:
        page, _final = step("adresse (pays)", f"/shop/checkout?pays={countries[country]}")
    values = fields(page, "/ocd/livraison")
    if not values.get("city_id"):
        raise RuntimeError(f"aucune ville pour le pays {values.get('delivery_country_id')}")
    start = time.time()
    request = urllib.request.Request(base + "/ocd/livraison/tarif", json.dumps({"jsonrpc": "2.0", "method": "call", "params": {
        "country_id": int(values["delivery_country_id"]), "city_id": int(values["city_id"])}}).encode(),
        {"Content-Type": "application/json"})
    with opener.open(request, timeout=60) as response:
        districts = (json.loads(response.read()).get("result") or {}).get("districts") or []
    steps.append(("quartiers de la ville", time.time() - start))
    if districts:
        values["district_id"] = str(districts[0]["id"])
    values.update({"name": f"Client test {number}", "phone": f"6{number % 100000000:08d}",
                   "country_id": values["delivery_country_id"], "delivery_landmark": "Test de charge"})
    page, final = step("adresse (envoi)", "/ocd/livraison", values)
    if "/shop/payment" not in final:
        page, final = step("paiement", "/shop/payment")
    if "/shop/payment" not in final or "o_ocd_error" in page:
        raise RuntimeError(f"pas arrivé au paiement ({final})")
    return steps


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("clients", type=int, help="clients à la fois")
    parser.add_argument("secondes", type=int, help="durée")
    parser.add_argument("--base", default="http://127.0.0.1:8069")
    parser.add_argument("--produit", default="/shop/robe-en-wax-38", help="adresse de la fiche d'un produit")
    parser.add_argument("--pays", default="Cameroun", help="pays de livraison, tel qu'écrit dans la liste")
    args = parser.parse_args()
    end = time.time() + args.secondes
    times, done, errors, kinds = {}, [0], [0], {}
    lock = threading.Lock()

    def client(index):
        number = index * 100000 + random.randint(0, 99999)
        while time.time() < end:
            number += 1
            try:
                steps = journey(args.base, args.produit, number, args.pays)
            except Exception as error:  # noqa: BLE001 (un parcours qui n'arrive pas au paiement)
                with lock:
                    errors[0] += 1
                    kind = getattr(error, "code", None) or type(error).__name__
                    kinds[kind] = kinds.get(kind, 0) + 1
                continue
            with lock:
                done[0] += 1
                for name, duration in steps:
                    times.setdefault(name, []).append(duration)

    threads = [threading.Thread(target=client, args=(index,)) for index in range(args.clients)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    print(f"{args.clients} clients à la fois, {args.secondes} s : {done[0]} parcours jusqu'au paiement "
          f"({done[0] * 60 / args.secondes:.0f} par minute), {errors[0]} en erreur {kinds or ''}")
    for name, values in times.items():
        values.sort()
        print(f"  {name:<22} médiane {statistics.median(values) * 1000:6.0f} ms, p95 {values[int(len(values) * 0.95)] * 1000:6.0f} ms")


if __name__ == "__main__":
    main()
