"""Write the .pot and fr.po of the OCD modules from the exports in pot/ and the dictionaries."""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import potlib  # noqa: E402

ns = {}
for name in ("fr_web.py", "fr_rest.py", "fr_shop.py", "fr_other.py", "fr_bo2.py", "fr_bo3.py", "fr_site_shop.py", "fr_rates.py", "fr_bo4.py", "fr_site_frame.py", "fr_ticket.py", "fr_countries.py", "fr_media.py"):
    exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), name), encoding="utf-8").read(), ns)

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
# Texts of other modules or of the demo database, not of these modules
SKIP = {"Create a Customer", "Next Activity Calendar Event", "Ratings"}
SKIP_PREFIX = ("Envoie le montant par Mobile Money",)
# Settings, automations and WhatsApp conversations: their texts are spread over the modules
SCREENS = [ns["SETTINGS"], ns["SHOP_SETTINGS"], ns["AUTOMATIONS"], ns["WHATSAPP_SCREENS"], ns["SHOP_WHATSAPP_SCREENS"],
           ns["NO_ODOO"], ns["PAGES_AND_ENGLISH"]]
MODULES = {
    "ocd_live": [ns["WEB"], ns["REST"], ns["BO"], ns["BO2"], ns["BO3"], ns["SITE"], ns["SITE_FRAME"], ns["TICKET"], ns["COUNTRIES"], *SCREENS],
    "ocd_live_shop": [ns["SHOP"], ns["SHOP2"], ns["SHOP3"], ns["SITE_SHOP"], ns["RATES"], ns["SHOP_COURIER_LOGIN"], ns["SHOP_COUNTRIES"], ns["MEDIA_SHOP"], *SCREENS],
    "ocd_live_whatsapp": [ns["WHATSAPP"], *SCREENS],
    "ocd_live_shop_whatsapp": [ns["SHOP_WHATSAPP"], ns["MEDIA_SHOP_WHATSAPP"], *SCREENS],
    "ocd_live_recruitment": [ns["RECRUITMENT"], ns["RECRUITMENT3"], ns["RECRUITMENT_FRAME"]],
    "ocd_delivery_togo": [ns["TOGO"]],
    "ocd_live_demo": [ns["DEMO"], ns["RATES_DEMO"]],
    "ocd_debranding": [ns["NO_ODOO"]],
    "theme_ocd": [ns["THEME"]],
}
ns["DESCRIPTIONS"]["theme_ocd"] = ns["THEME_DESCRIPTION"]
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
    # The long description of the module, as written in its manifest
    manifest = ast.literal_eval(open(os.path.join(ROOT, module, "__manifest__.py"), encoding="utf-8").read())
    if manifest.get("description") and module in ns["DESCRIPTIONS"]:
        translations[manifest["description"]] = ns["DESCRIPTIONS"][module]
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
