"""Carga reproducible de materias, cursos de DEMOSTRACIÓN, insignias y ajustes. Es idempotente."""
import json

from ..db import ex, q1, tx
from . import math, science, spanish

ACHIEVEMENTS = [
    ("primer_paso", "Primer paso", "Completaste tu primera lección.", "🌱"),
    ("explorador", "Explorador", "Terminaste un diagnóstico.", "🧭"),
    ("constancia", "Constancia", "Completaste 5 lecciones.", "🔥"),
    ("precision", "Precisión", "Lograste 90% o más en una evaluación.", "🎯"),
    ("graduado", "Curso completado", "Completaste un curso entero.", "🎓"),
]


def _insert_question(q, comp_ids, lesson_id=None):
    cur = ex("INSERT INTO questions(kind, prompt, explanation, difficulty, data, competency_id, lesson_id) VALUES (?,?,?,?,?,?,?)",
             (q["kind"], q["prompt"], q["explanation"], q["diff"], json.dumps(q.get("data", {}), ensure_ascii=False),
              comp_ids[q["comp"]], lesson_id))
    qid = cur.lastrowid
    for pos, text in enumerate(q.get("options", [])):
        ex("INSERT INTO answer_options(question_id, position, text, is_correct) VALUES (?,?,?,?)",
           (qid, pos, text, 1 if pos == q["correct"] else 0))
    return qid


def _link(assessment_id, question_ids):
    for pos, qid in enumerate(question_ids):
        ex("INSERT INTO assessment_questions(assessment_id, question_id, position) VALUES (?,?,?)", (assessment_id, qid, pos))


def seed_all(force=False):
    """Carga el contenido inicial. Si ya existe contenido y force=False, no hace nada."""
    if q1("SELECT 1 FROM subjects LIMIT 1") and not force:
        return False
    with tx():
        for code, name, desc, icon in ACHIEVEMENTS:
            ex("INSERT OR IGNORE INTO achievements(code, name, description, icon) VALUES (?,?,?,?)", (code, name, desc, icon))
        for mod in (math, science, spanish):
            s = mod.SUBJECT
            if q1("SELECT 1 FROM subjects WHERE slug=?", (s["slug"],)):
                continue
            sid = ex("INSERT INTO subjects(slug, name, description, icon, position, color) VALUES (?,?,?,?,?,?)",
                     (s["slug"], s["name"], s["description"], s["icon"], s["position"], s["color"])).lastrowid
            comp_ids = {slug: ex("INSERT INTO competencies(subject_id, slug, name, description) VALUES (?,?,?,?)",
                                 (sid, slug, name, desc)).lastrowid for slug, name, desc in s["competencies"]}
            # Diagnóstico de la materia
            diag = ex("INSERT INTO assessments(kind, title, subject_id) VALUES ('diagnostic', ?, ?)",
                      (f"Diagnóstico de {s['name']}", sid)).lastrowid
            _link(diag, [_insert_question(q, comp_ids) for q in mod.DIAGNOSTIC])
            # Curso
            c = mod.COURSE
            minutes = sum(l["est"] for u in c["units"] for l in u["lessons"])
            cid = ex("""INSERT INTO courses(slug, subject_id, title, description, objectives, level, difficulty, est_minutes,
                        prerequisites, resources, status, pass_pct, max_attempts, is_demo) VALUES (?,?,?,?,?,?,?,?,?,?,'published',?,?,1)""",
                     (c["slug"], sid, c["title"], c["description"], json.dumps(c["objectives"], ensure_ascii=False), c["level"],
                      c["difficulty"], minutes, c["prerequisites"], c["resources"], c["pass_pct"], c["max_attempts"])).lastrowid
            for slug in c["competencies"]:
                ex("INSERT INTO course_competencies(course_id, competency_id) VALUES (?,?)", (cid, comp_ids[slug]))
            for upos, u in enumerate(c["units"]):
                uid = ex("INSERT INTO units(course_id, title, position) VALUES (?,?,?)", (cid, u["title"], upos)).lastrowid
                for lpos, les in enumerate(u["lessons"]):
                    lid = ex("INSERT INTO lessons(unit_id, title, summary, est_minutes, position) VALUES (?,?,?,?,?)",
                             (uid, les["title"], les["summary"], les["est"], lpos)).lastrowid
                    for bpos, b in enumerate(les["blocks"]):
                        ex("INSERT INTO content_blocks(lesson_id, position, type, data) VALUES (?,?,?,?)",
                           (lid, bpos, b["type"], json.dumps(b["data"], ensure_ascii=False)))
                    quiz = ex("INSERT INTO assessments(kind, title, course_id, lesson_id) VALUES ('formative', ?, ?, ?)",
                              (f"Comprueba: {les['title']}", cid, lid)).lastrowid
                    _link(quiz, [_insert_question(q, comp_ids, lid) for q in les["quiz"]])
            final = ex("INSERT INTO assessments(kind, title, course_id) VALUES ('final', ?, ?)",
                       (f"Evaluación final: {c['title']}", cid)).lastrowid
            _link(final, [_insert_question(q, comp_ids) for q in c["final"]])
    return True
