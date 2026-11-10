import sys, json, os
sys.path.insert(0, os.path.dirname(__file__))
import potlib
module = sys.argv[1]
_, pot = potlib.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pot", f"{module}.pot"))
known = {}
po = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", module, "i18n", "fr.po")
if os.path.exists(po):
    _, entries = potlib.read(po)
    known = {e["msgid"]: e["msgstr"] for e in entries if e["msgstr"]}
extra = {}
for name in sys.argv[2:]:
    ns = {}
    exec(open(name).read(), ns)
    for key, value in ns.items():
        if isinstance(value, dict) and not key.startswith("__"):
            extra.update(value)
missing = [e["msgid"] for e in pot if e["msgid"] not in known and e["msgid"] not in extra]
print(len(pot), "entries,", len(missing), "missing")
for m in missing:
    print(json.dumps(m, ensure_ascii=False))
