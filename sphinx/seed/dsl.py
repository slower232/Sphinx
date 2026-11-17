"""Funciones auxiliares para escribir preguntas y bloques de forma compacta."""


def _data(base, scene="", layout=""):
    if scene:
        base["scene"] = scene          # emoji decorativo: el enunciado siempre contiene la información completa
    if layout:
        base["layout"] = layout
    return base


def mcq(prompt, options, correct, expl, comp, diff=1, scene="", emojis=None, layout=""):
    """layout='images' muestra las opciones como tarjetas grandes con su emoji (elegir la imagen correcta)."""
    return {"kind": "mcq", "prompt": prompt, "options": options, "emojis": emojis or [], "correct": correct,
            "explanation": expl, "comp": comp, "diff": diff, "data": _data({}, scene, layout)}


def tf(prompt, answer, expl, comp, diff=1, scene=""):
    return {"kind": "tf", "prompt": prompt, "options": ["Verdadero", "Falso"], "emojis": ["✅", "❌"], "correct": 0 if answer else 1,
            "explanation": expl, "comp": comp, "diff": diff, "data": _data({}, scene)}


def num(prompt, answer, expl, comp, diff=1, tol="0", scene=""):
    return {"kind": "numeric", "prompt": prompt, "data": _data({"answer": str(answer), "tolerance": tol}, scene),
            "explanation": expl, "comp": comp, "diff": diff}


def short(prompt, accepted, expl, comp, diff=1, scene=""):
    return {"kind": "short", "prompt": prompt, "data": _data({"accepted": accepted}, scene), "explanation": expl, "comp": comp, "diff": diff}


def match(prompt, pairs, expl, comp, diff=2, scene=""):
    """Arrastrar y soltar: cada par es [elemento fijo, elemento que se arrastra]."""
    return {"kind": "match", "prompt": prompt, "data": _data({"pairs": pairs}, scene), "explanation": expl, "comp": comp, "diff": diff}


def order(prompt, items, expl, comp, diff=2, scene=""):
    """Ordenar: `items` va en el orden CORRECTO (la pantalla los muestra revueltos)."""
    return {"kind": "order", "prompt": prompt, "data": _data({"items": items}, scene), "explanation": expl, "comp": comp, "diff": diff}


def scene(emoji, caption):
    return {"type": "scene", "data": {"emoji": emoji, "caption": caption}}


def text(title, body):
    return {"type": "text", "data": {"title": title, "body": body}}


def example(title, problem, steps, answer):
    return {"type": "example", "data": {"title": title, "problem": problem, "steps": steps, "answer": answer}}


def tip(body):
    return {"type": "tip", "data": {"body": body}}


def mistakes(*items):
    return {"type": "mistakes", "data": {"items": list(items)}}


def summary(*items):
    return {"type": "summary", "data": {"items": list(items)}}


def cards(*pairs):
    return {"type": "flashcards", "data": {"cards": [{"front": f, "back": b} for f, b in pairs]}}
