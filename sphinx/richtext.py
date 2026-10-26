"""Texto enriquecido seguro: se escapa TODO el HTML y solo se permite **negrita**, *cursiva* y listas '- '."""
import re

from markupsafe import Markup, escape


def _inline(text):
    s = str(escape(text))
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<em>\1</em>", s)
    return s


def rich(text):
    paragraphs = re.split(r"\n\s*\n", (text or "").strip())
    out = []
    for p in paragraphs:
        lines = [ln for ln in p.split("\n") if ln.strip()]
        if not lines:
            continue
        if all(ln.strip().startswith("- ") for ln in lines):
            out.append("<ul>" + "".join(f"<li>{_inline(ln.strip()[2:])}</li>" for ln in lines) + "</ul>")
        else:
            out.append("<p>" + "<br>".join(_inline(ln) for ln in lines) + "</p>")
    return Markup("".join(out))


def init_app(app):
    app.jinja_env.filters["rich"] = rich
