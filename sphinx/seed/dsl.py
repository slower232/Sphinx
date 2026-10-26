"""Funciones auxiliares para escribir preguntas y bloques de forma compacta."""


def mcq(prompt, options, correct, expl, comp, diff=1):
    return {"kind": "mcq", "prompt": prompt, "options": options, "correct": correct, "explanation": expl, "comp": comp, "diff": diff}


def tf(prompt, answer, expl, comp, diff=1):
    return {"kind": "tf", "prompt": prompt, "options": ["Verdadero", "Falso"], "correct": 0 if answer else 1,
            "explanation": expl, "comp": comp, "diff": diff}


def num(prompt, answer, expl, comp, diff=1, tol="0"):
    return {"kind": "numeric", "prompt": prompt, "data": {"answer": str(answer), "tolerance": tol}, "explanation": expl, "comp": comp, "diff": diff}


def short(prompt, accepted, expl, comp, diff=1):
    return {"kind": "short", "prompt": prompt, "data": {"accepted": accepted}, "explanation": expl, "comp": comp, "diff": diff}


def match(prompt, pairs, expl, comp, diff=2):
    return {"kind": "match", "prompt": prompt, "data": {"pairs": pairs}, "explanation": expl, "comp": comp, "diff": diff}


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
