"""Write the .pot and fr.po of the OCD modules from the exports in pot/ and the dictionaries."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import potlib  # noqa: E402

ns = {}
for name in ("fr_web.py", "fr_rest.py", "fr_shop.py", "fr_other.py", "fr_bo2.py", "fr_bo3.py", "fr_site_shop.py", "fr_rates.py"):
    exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), name), encoding="utf-8").read(), ns)

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
# Texts of other modules or of the demo database, not of these modules
SKIP = {"Create a Customer", "Next Activity Calendar Event", "Ratings"}
SKIP_PREFIX = ("Envoie le montant par Mobile Money",)
MODULES = {
    "ocd_live": [ns["WEB"], ns["REST"], ns["BO"], ns["BO2"], ns["BO3"], ns["SITE"]],
    "ocd_live_shop": [ns["SHOP"], ns["SHOP2"], ns["SHOP3"], ns["SITE_SHOP"], ns["RATES"]],
    "ocd_live_whatsapp": [ns["WHATSAPP"]],
    "ocd_live_shop_whatsapp": [ns["SHOP_WHATSAPP"]],
    "ocd_live_recruitment": [ns["RECRUITMENT"], ns["RECRUITMENT3"]],
    "ocd_delivery_togo": [ns["TOGO"]],
    "ocd_live_demo": [ns["DEMO"], ns["RATES_DEMO"]],
}
# Names of places and products: the same in French
IDENTITY = {"ocd_delivery_togo", "ocd_live_demo"}

for module, dicts in MODULES.items():
    exported = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pot", f"{module}.pot")
    if not os.path.exists(exported):
        # Not exported again: keep the template of the module
        exported = os.path.join(ROOT, module, "i18n", f"{module}.pot")
    header, entries = potlib.read(exported)
    entries = [e for e in entries if e["msgid"] not in SKIP and not e["msgid"].startswith(SKIP_PREFIX)]
    translations = {}
    po_path = os.path.join(ROOT, module, "i18n", "fr.po")
    if os.path.exists(po_path):
        _h, old = potlib.read(po_path)
        translations.update({e["msgid"]: e["msgstr"] for e in old if e["msgstr"]})
    translations.update(ns["COMMON"])
    for table in dicts:
        translations.update(table)
    for e in entries:
        if e["msgid"].replace("_", "").isalpha() and e["msgid"].islower() and e["msgid"] not in translations:
            translations[e["msgid"]] = e["msgid"]
    if module in IDENTITY:
        for e in entries:
            msgid = e["msgid"]
            if msgid not in translations and "\n" not in msgid:
                translations[msgid] = msgid
    os.makedirs(os.path.join(ROOT, module, "i18n"), exist_ok=True)
    potlib.write(os.path.join(ROOT, module, "i18n", f"{module}.pot"), header, entries, {}, language="")
    potlib.write(po_path, header, entries, translations)
    missing = [e["msgid"] for e in entries if not translations.get(e["msgid"])]
    print(f"{module}: {len(entries)} entries, {len(missing)} without translation")
    for msgid in missing:
        print("   ", repr(msgid[:90]))
