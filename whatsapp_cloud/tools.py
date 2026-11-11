"""Conversions between the HTML of Odoo messages and the text of WhatsApp messages.

WhatsApp formats the text with *bold*, _italic_, ~strikethrough~ and ```monospace```.
"""
import re
import unicodedata

from lxml import html as lxml_html
from markupsafe import Markup, escape

INLINE_MARKS = {
    "b": "*", "strong": "*",
    "i": "_", "em": "_",
    "s": "~", "strike": "~", "del": "~",
    "code": "```",
}
BLOCK_TAGS = {"p", "div", "li", "ul", "ol", "blockquote", "pre", "h1", "h2", "h3", "h4", "h5", "h6"}


def html_to_whatsapp(body):
    """Text of a WhatsApp message from the HTML body of an Odoo message."""
    if not body or not str(body).strip():
        return ""
    root = lxml_html.fragment_fromstring(str(body), create_parent="div")
    parts = []

    def walk(element):
        tag = element.tag if isinstance(element.tag, str) else ""
        if tag == "br":
            parts.append("\n")
        elif tag == "li":
            parts.append("- ")
        mark = INLINE_MARKS.get(tag, "")
        content_start = len(parts)
        if element.text:
            parts.append(element.text)
        for child in element:
            walk(child)
            if child.tail:
                parts.append(child.tail)
        if mark:
            content = "".join(parts[content_start:])
            stripped = content.strip()
            del parts[content_start:]
            if stripped:
                # the marks must touch the text: "*bold* " and not "* bold *"
                leading = content[:len(content) - len(content.lstrip())]
                trailing = content[len(content.rstrip()):]
                parts.append(f"{leading}{mark}{stripped}{mark}{trailing}")
        if tag == "a":
            href = element.get("href") or ""
            text = (element.text_content() or "").strip()
            if href and not href.startswith(("mailto:", "#")) and href not in text:
                parts.append(f" ({href})")
        if tag in BLOCK_TAGS:
            parts.append("\n")

    walk(root)
    text = "".join(parts).replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def whatsapp_to_html(text):
    """HTML body of an Odoo message from the text of a WhatsApp message: escaped, with the
    WhatsApp formatting, the line breaks and the links."""
    if not text:
        return Markup("")
    html = str(escape(text))
    html = re.sub(r"```(.+?)```", r"<code>\1</code>", html, flags=re.S)
    html = re.sub(r"(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])", r"<b>\1</b>", html)
    html = re.sub(r"(?<![\w_])_(?!\s)([^_\n]+?)(?<!\s)_(?![\w_])", r"<i>\1</i>", html)
    html = re.sub(r"(?<![\w~])~(?!\s)([^~\n]+?)(?<!\s)~(?![\w~])", r"<s>\1</s>", html)
    html = re.sub(
        r"(?<![\"'=])\b(https?://[^\s<]+[^\s<.,;:!?)\]'\"])",
        r'<a href="\1" target="_blank" rel="noreferrer noopener">\1</a>',
        html,
    )
    return Markup(html.replace("\n", "<br/>"))


def normalize_keyword(text):
    """A short text of a customer reduced to its words, to compare with keywords."""
    text = (text or "").strip().lower()
    return re.sub(r"[^\w\s]", "", text).strip()


def simplify(text):
    """A name written by a customer, without accents, case nor punctuation: to compare with
    the names of the records (cities, districts...)."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(char for char in text if not unicodedata.combining(char)).lower()
    return " ".join(re.sub(r"[^\w]+", " ", text).split())
