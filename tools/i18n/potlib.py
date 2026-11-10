"""Tiny reader and writer of .pot/.po files (enough for Odoo exports)."""
import re


def _unquote(line):
    body = line[line.index('"') + 1:line.rindex('"')]
    return bytes(body, "utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8")


def _quote(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t") + '"'


def read(path):
    """Return the header lines and the entries: dict(comments, msgid, msgstr)."""
    entries, current, field = [], None, None
    header = []
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().split("\n")
    for line in lines:
        if line.startswith("#"):
            if current is None or current.get("msgid") is not None:
                if current is not None:
                    entries.append(current)
                current = {"comments": [], "msgid": None, "msgstr": ""}
            current["comments"].append(line)
        elif line.startswith("msgid "):
            if current is None:
                current = {"comments": [], "msgid": None, "msgstr": ""}
            current["msgid"] = _unquote(line)
            field = "msgid"
        elif line.startswith("msgstr "):
            current["msgstr"] = _unquote(line)
            field = "msgstr"
        elif line.startswith('"') and current is not None:
            current[field] += _unquote(line)
    if current is not None:
        entries.append(current)
    if entries and entries[0]["msgid"] == "":
        header = entries.pop(0)
    return header, entries


def write(path, header, entries, translations, language="fr"):
    out = ["# Translation of Odoo Server.", "#", 'msgid ""', 'msgstr ""']
    for line in header["msgstr"].split("\n"):
        if line:
            if line.startswith("Language:") or line.startswith("Plural-Forms:"):
                continue
            out.append(_quote(line + "\n"))
    out.append(_quote(f"Language: {language}\n"))
    out.append(_quote("Plural-Forms: nplurals=2; plural=(n > 1);\n"))
    out.append("")
    for entry in entries:
        out.extend(entry["comments"])
        msgid = entry["msgid"]
        msgstr = translations.get(msgid, "")
        for key, text in (("msgid", msgid), ("msgstr", msgstr)):
            if "\n" in text and text.strip("\n"):
                out.append(f'{key} ""')
                parts = re.split(r"(?<=\n)", text)
                out.extend(_quote(part) for part in parts if part)
            else:
                out.append(f"{key} {_quote(text)}")
        out.append("")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(out))
