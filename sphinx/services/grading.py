"""Calificación pura (sin base de datos): fácil de probar. SIEMPRE se ejecuta en el servidor."""
import re
import unicodedata
from fractions import Fraction

_NUM = re.compile(r"^-?\d{1,12}(\.\d{1,12})?(/\d{1,12})?$")


def normalize_text(s):
    s = unicodedata.normalize("NFKD", str(s or "").casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s/]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_number(s):
    s = str(s if s is not None else "").strip().replace(",", ".").replace(" ", "")
    if not _NUM.match(s):
        return None
    try:
        return Fraction(s)
    except (ValueError, ZeroDivisionError):
        return None


def grade_question(q, response):
    """Devuelve (fracción de acierto 0..1, es_correcta). `q` viene de assessments.load_questions."""
    kind, data = q["kind"], q["data"]
    if kind in ("mcq", "tf"):
        try:
            oid = int(response)
        except (TypeError, ValueError):
            return 0.0, False
        ok = any(o["id"] == oid and o["is_correct"] for o in q["options"])
        return (1.0 if ok else 0.0), ok
    if kind == "numeric":
        answer, given = parse_number(data.get("answer")), parse_number(response)
        tol = parse_number(data.get("tolerance", 0)) or Fraction(0)
        ok = answer is not None and given is not None and abs(given - answer) <= tol
    elif kind == "short":
        given = normalize_text(response)
        ok = bool(given) and given in {normalize_text(x) for x in data.get("accepted", [])}
    elif kind == "match":
        pairs = data.get("pairs", [])
        resp = response if isinstance(response, list) else []
        good = sum(1 for i, (_, right) in enumerate(pairs)
                   if i < len(resp) and normalize_text(resp[i]) == normalize_text(right))
        frac = good / len(pairs) if pairs else 0.0
        return frac, frac == 1.0
    else:
        ok = False
    return (1.0 if ok else 0.0), ok


def mastery_level(got, total, n):
    """Interpretación transparente de resultados: se necesitan al menos 2 preguntas."""
    if n < 2 or not total:
        return "sin_datos"
    acc = got / total
    return "dominada" if acc >= 0.75 else ("desarrollo" if acc >= 0.5 else "reforzar")
