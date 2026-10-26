"""Progreso de lecciones y cursos, y orquestación de lo que ocurre al enviar una evaluación."""
from datetime import date

from ..db import ex, q1, qa
from . import gamification as gam


def ensure_enrollment(owner, course_id):
    ex("INSERT OR IGNORE INTO enrollments(user_id, anon_id, course_id) VALUES (?,?,?)",
       (owner.user_id, owner.anon_id, course_id))
    sql, p = owner.where()
    ex(f"UPDATE enrollments SET last_activity_at=datetime('now') WHERE course_id=? AND {sql}", (course_id,) + p)


def course_lessons(course_id):
    return qa("""SELECT l.id, l.title, l.summary, l.est_minutes, u.id AS unit_id, u.title AS unit_title
                 FROM lessons l JOIN units u ON u.id=l.unit_id WHERE u.course_id=?
                 ORDER BY u.position, u.id, l.position, l.id""", (course_id,))


def completed_lesson_ids(owner, course_id):
    if not owner:
        return set()
    sql, p = owner.where("lp")
    return {r["lesson_id"] for r in qa(
        f"""SELECT lp.lesson_id FROM lesson_progress lp JOIN lessons l ON l.id=lp.lesson_id
            JOIN units u ON u.id=l.unit_id WHERE u.course_id=? AND {sql}""", (course_id,) + p)}


def best_final(owner, course_id):
    """Mejor intento aprobado de la evaluación final (o None)."""
    sql, p = owner.where("a")
    return q1(f"""SELECT a.* FROM attempts a JOIN assessments s ON s.id=a.assessment_id
                  WHERE a.kind='final' AND a.passed=1 AND s.course_id=? AND {sql}
                  ORDER BY a.score_pct DESC, a.id DESC LIMIT 1""", (course_id,) + p)


def progress_for_courses(owner, ids):
    ids = list(ids)
    if not ids:
        return {}
    ph = ",".join("?" * len(ids))
    totals = {r["course_id"]: r["n"] for r in qa(
        f"SELECT u.course_id, COUNT(l.id) n FROM units u JOIN lessons l ON l.unit_id=u.id "
        f"WHERE u.course_id IN ({ph}) GROUP BY u.course_id", ids)}
    done, finals, enrolled = {}, set(), {}
    if owner:
        s1, p1 = owner.where("lp")
        done = {r["course_id"]: r["n"] for r in qa(
            f"SELECT u.course_id, COUNT(*) n FROM lesson_progress lp JOIN lessons l ON l.id=lp.lesson_id "
            f"JOIN units u ON u.id=l.unit_id WHERE u.course_id IN ({ph}) AND {s1} GROUP BY u.course_id", ids + list(p1))}
        s2, p2 = owner.where("a")
        finals = {r["course_id"] for r in qa(
            f"SELECT DISTINCT s.course_id FROM attempts a JOIN assessments s ON s.id=a.assessment_id "
            f"WHERE a.kind='final' AND a.passed=1 AND s.course_id IN ({ph}) AND {s2}", ids + list(p2))}
        s3, p3 = owner.where("e")
        enrolled = {r["course_id"]: r["completed_at"] for r in qa(
            f"SELECT e.course_id, e.completed_at FROM enrollments e WHERE e.course_id IN ({ph}) AND {s3}", ids + list(p3))}
    out = {}
    for cid in ids:
        total, d, f = totals.get(cid, 0), done.get(cid, 0), 1 if cid in finals else 0
        out[cid] = {"total": total, "done": d, "final_passed": bool(f),
                    "percent": round(100 * (d + f) / (total + 1)),
                    "started": cid in enrolled or d > 0, "completed": bool(enrolled.get(cid))}
    return out


def next_lesson(owner, course_id):
    done = completed_lesson_ids(owner, course_id)
    for l in course_lessons(course_id):
        if l["id"] not in done:
            return l
    return None


def lesson_quiz_id(lesson_id):
    """Id de la comprobación de la lección, solo si tiene preguntas."""
    row = q1("""SELECT s.id FROM assessments s JOIN assessment_questions aq ON aq.assessment_id=s.id
                WHERE s.kind='formative' AND s.lesson_id=? LIMIT 1""", (lesson_id,))
    return row["id"] if row else None


def update_course_completion(owner, course_id):
    lessons = course_lessons(course_id)
    done = completed_lesson_ids(owner, course_id)
    if lessons and all(l["id"] in done for l in lessons) and best_final(owner, course_id):
        sql, p = owner.where()
        ex(f"UPDATE enrollments SET completed_at=COALESCE(completed_at, datetime('now')) WHERE course_id=? AND {sql}",
           (course_id,) + p)
        return True
    return False


def complete_lesson(owner, lesson_id, course_id):
    """Marca una lección como completada (una sola vez). Devuelve (es_nueva, xp_concedido)."""
    ensure_enrollment(owner, course_id)
    cur = ex("INSERT OR IGNORE INTO lesson_progress(user_id, anon_id, lesson_id) VALUES (?,?,?)",
             (owner.user_id, owner.anon_id, lesson_id))
    new = cur.rowcount == 1
    xp = gam.award(owner, "lesson", f"lesson:{lesson_id}", gam.setting("xp_lesson")) if new else 0
    update_course_completion(owner, course_id)
    return new, xp


def record_submission(owner, att):
    """Efectos de enviar una evaluación (se llama dentro de la misma transacción)."""
    xp, kind = 0, att["kind"]
    asm = q1("SELECT * FROM assessments WHERE id=?", (att["assessment_id"],)) if att["assessment_id"] else None
    course_id = asm["course_id"] if asm else None
    if course_id:
        ensure_enrollment(owner, course_id)
    if kind == "diagnostic":
        xp += gam.award(owner, "diagnostic", f"subject:{asm['subject_id']}", gam.setting("xp_diagnostic"))
    elif kind == "formative" and att["passed"]:
        xp += gam.award(owner, "formative", f"assessment:{asm['id']}", gam.setting("xp_formative"))
        xp += complete_lesson(owner, asm["lesson_id"], course_id)[1]
    elif kind == "final" and att["passed"]:
        xp += gam.award(owner, "final", f"course:{course_id}", gam.setting("xp_course"))
        update_course_completion(owner, course_id)
    elif kind == "review" and (att["score_pct"] or 0) >= 60:
        xp += gam.award(owner, "review", f"day:{date.today().isoformat()}", gam.setting("xp_review"))
    return {"xp": xp, "badges": gam.check_achievements(owner, att)}
