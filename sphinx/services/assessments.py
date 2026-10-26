"""Intentos de evaluación: creación, calificación en el servidor, resultados."""
import json

from ..db import ex, q1, qa, tx
from . import gamification as gam, grading, progress


def load_questions(ids):
    ids = list(ids)
    if not ids:
        return {}
    ph = ",".join("?" * len(ids))
    out = {}
    for r in qa(f"SELECT * FROM questions WHERE id IN ({ph})", ids):
        d = dict(r)
        d["data"] = json.loads(r["data"] or "{}")
        d["options"] = []
        out[r["id"]] = d
    for o in qa(f"SELECT * FROM answer_options WHERE question_id IN ({ph}) ORDER BY position, id", ids):
        out[o["question_id"]]["options"].append({"id": o["id"], "text": o["text"], "is_correct": bool(o["is_correct"])})
    return out


def public_question(q):
    """Versión de la pregunta que se envía al navegador: SIN respuestas correctas."""
    p = {"id": q["id"], "kind": q["kind"], "prompt": q["prompt"], "points": q["points"],
         "options": [{"id": o["id"], "text": o["text"]} for o in q["options"]]}
    if q["kind"] == "match":
        pairs = q["data"].get("pairs", [])
        p["left"] = [l for l, _ in pairs]
        p["right"] = sorted({r for _, r in pairs}, key=grading.normalize_text)
    return p


def start_attempt(owner, assessment_id, preview=False):
    """Devuelve (attempt_id, clave_de_error). Reutiliza un intento abierto (evita duplicados)."""
    a = q1("""SELECT s.*, c.status AS course_status, c.max_attempts FROM assessments s
              LEFT JOIN courses c ON c.id=s.course_id WHERE s.id=?""", (assessment_id,))
    if not a or (a["course_id"] and a["course_status"] != "published" and not preview):
        return None, "err.not_found"
    qids = [r["question_id"] for r in qa(
        "SELECT question_id FROM assessment_questions WHERE assessment_id=? ORDER BY position, question_id", (assessment_id,))]
    if not qids:
        return None, "err.no_questions"
    sql, p = owner.where()
    with tx():
        open_ = q1(f"SELECT id FROM attempts WHERE assessment_id=? AND status='in_progress' AND {sql}", (assessment_id,) + p)
        if open_:
            return open_["id"], None
        if a["kind"] == "final" and a["max_attempts"]:
            n = q1(f"SELECT COUNT(*) c FROM attempts WHERE assessment_id=? AND status='submitted' AND {sql}", (assessment_id,) + p)["c"]
            if n >= a["max_attempts"]:
                return None, "err.max_attempts"
        cur = ex("INSERT INTO attempts(assessment_id, kind, user_id, anon_id, question_ids) VALUES (?,?,?,?,?)",
                 (assessment_id, a["kind"], owner.user_id, owner.anon_id, json.dumps(qids)))
        return cur.lastrowid, None


def start_review(owner, limit=5):
    """Reto de repaso: preguntas cuya respuesta MÁS RECIENTE fue incorrecta."""
    sql, p = owner.where("a")
    rows = qa(f"""SELECT r.question_id FROM responses r WHERE r.is_correct=0 AND r.id IN (
                    SELECT MAX(r2.id) FROM responses r2 JOIN attempts a ON a.id=r2.attempt_id
                    WHERE a.status='submitted' AND {sql} GROUP BY r2.question_id)
                  ORDER BY r.id DESC LIMIT ?""", p + (limit,))
    qids = [r["question_id"] for r in rows]
    if not qids:
        return None
    with tx():
        sql2, p2 = owner.where()
        open_ = q1(f"SELECT id FROM attempts WHERE kind='review' AND status='in_progress' AND {sql2}", p2)
        if open_:
            return open_["id"]
        return ex("INSERT INTO attempts(assessment_id, kind, user_id, anon_id, question_ids) VALUES (NULL,'review',?,?,?)",
                  (owner.user_id, owner.anon_id, json.dumps(qids))).lastrowid


def get_attempt(owner, attempt_id):
    sql, p = owner.where()
    return q1(f"SELECT * FROM attempts WHERE id=? AND {sql}", (attempt_id,) + p)


def _extract(q, form):
    if q["kind"] == "match":
        return [form.get(f"q_{q['id']}_{i}", "") for i in range(len(q["data"].get("pairs", [])))]
    return form.get(f"q_{q['id']}", "")


def submit_attempt(owner, attempt_id, form):
    """Califica TODO en el servidor. Es idempotente: reenviar no duplica nada. Devuelve (intento, resumen)."""
    with tx():
        att = get_attempt(owner, attempt_id)
        if not att:
            raise LookupError("attempt")
        if att["status"] == "submitted":
            return att, None
        ids = json.loads(att["question_ids"])
        qs = load_questions(ids)
        got = total = 0.0
        for qid in ids:
            q = qs[qid]
            resp = _extract(q, form)
            frac, ok = grading.grade_question(q, resp)
            pts = q["points"] * frac
            got += pts
            total += q["points"]
            ex("INSERT INTO responses(attempt_id, question_id, response, is_correct, points) VALUES (?,?,?,?,?)",
               (attempt_id, qid, json.dumps(resp), 1 if ok else 0, pts))
        score = round(100 * got / total, 1) if total else 0.0
        passed = None
        if att["kind"] == "formative":
            passed = int(score >= gam.setting("formative_pass_pct"))
        elif att["kind"] == "final":
            pct = q1("SELECT c.pass_pct FROM assessments s JOIN courses c ON c.id=s.course_id WHERE s.id=?",
                     (att["assessment_id"],))["pass_pct"]
            passed = int(score >= pct)
        ex("UPDATE attempts SET status='submitted', submitted_at=datetime('now'), score_pct=?, points=?, max_points=?, passed=? "
           "WHERE id=?", (score, got, total, passed, attempt_id))
        att = get_attempt(owner, attempt_id)
        summary = progress.record_submission(owner, att)
        return att, summary


def _given_text(q, given):
    if q["kind"] in ("mcq", "tf"):
        for o in q["options"]:
            if str(o["id"]) == str(given):
                return o["text"]
        return ""
    if q["kind"] == "match":
        pairs = q["data"].get("pairs", [])
        given = given if isinstance(given, list) else []
        return "; ".join(f"{l} → {given[i] if i < len(given) and given[i] else '—'}" for i, (l, _) in enumerate(pairs))
    return str(given or "")


def _correct_text(q):
    if q["kind"] in ("mcq", "tf"):
        return "; ".join(o["text"] for o in q["options"] if o["is_correct"])
    if q["kind"] == "numeric":
        return str(q["data"].get("answer", ""))
    if q["kind"] == "short":
        return (q["data"].get("accepted") or [""])[0]
    return "; ".join(f"{l} → {r}" for l, r in q["data"].get("pairs", []))


def attempt_results(att):
    ids = json.loads(att["question_ids"])
    qs = load_questions(ids)
    resp = {r["question_id"]: r for r in qa("SELECT * FROM responses WHERE attempt_id=?", (att["id"],))}
    out = []
    for qid in ids:
        q, r = qs.get(qid), resp.get(qid)
        if not q:
            continue
        given = json.loads(r["response"]) if r else None
        out.append({"q": q, "given": _given_text(q, given), "correct": _correct_text(q),
                    "is_correct": bool(r and r["is_correct"]), "points": r["points"] if r else 0})
    return out


def competency_breakdown(results):
    """Agrupa los resultados de un intento por competencia, con el nivel interpretado."""
    names = {c["id"]: c["name"] for c in qa("SELECT id, name FROM competencies")}
    agg = {}
    for r in results:
        a = agg.setdefault(r["q"]["competency_id"], {"got": 0.0, "tot": 0.0, "n": 0})
        a["got"] += r["points"]
        a["tot"] += r["q"]["points"]
        a["n"] += 1
    return [{"name": names.get(cid, "?"), "got": round(a["got"], 1), "tot": a["tot"], "n": a["n"],
             "level": grading.mastery_level(a["got"], a["tot"], a["n"])} for cid, a in agg.items()]
