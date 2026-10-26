"""Formato estructurado y validado de los bloques de contenido (no se guarda HTML)."""
import json

BLOCK_TYPES = ["text", "example", "tip", "mistakes", "summary", "flashcards"]
MAX_TEXT, MAX_ITEMS = 4000, 30


def _s(value, name, required=False):
    value = (value or "").strip()
    if required and not value:
        raise ValueError(name)
    if len(value) > MAX_TEXT:
        raise ValueError("block.too_long")
    return value


def _lines(text, name, required=True):
    items = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if required and not items:
        raise ValueError(name)
    if len(items) > MAX_ITEMS or any(len(i) > 600 for i in items):
        raise ValueError("block.too_long")
    return items


def from_form(btype, form):
    """Convierte los campos del formulario de administración en un dict validado."""
    if btype not in BLOCK_TYPES:
        raise ValueError("block.bad_type")
    if btype == "text":
        return {"title": _s(form.get("title"), ""), "body": _s(form.get("body"), "block.need_body", True)}
    if btype == "tip":
        return {"body": _s(form.get("body"), "block.need_body", True)}
    if btype == "example":
        return {"title": _s(form.get("title"), ""), "problem": _s(form.get("problem"), "block.need_problem", True),
                "steps": _lines(form.get("steps"), "block.need_steps"), "answer": _s(form.get("answer"), "block.need_answer", True)}
    if btype in ("mistakes", "summary"):
        return {"items": _lines(form.get("items"), "block.need_items")}
    cards = []
    for ln in _lines(form.get("cards"), "block.need_cards"):
        if "|" not in ln:
            raise ValueError("block.bad_card")
        front, back = (x.strip() for x in ln.split("|", 1))
        if not front or not back:
            raise ValueError("block.bad_card")
        cards.append({"front": front, "back": back})
    return {"cards": cards}


def to_form(btype, data):
    f = {"title": data.get("title", ""), "body": data.get("body", ""), "problem": data.get("problem", ""),
         "answer": data.get("answer", ""), "steps": "\n".join(data.get("steps", [])),
         "items": "\n".join(data.get("items", [])),
         "cards": "\n".join(f"{c['front']} | {c['back']}" for c in data.get("cards", []))}
    return f


def parse(row):
    try:
        return json.loads(row["data"])
    except (TypeError, ValueError):
        return {}
