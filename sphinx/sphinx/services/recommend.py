"""Recomendaciones basadas en reglas transparentes (documentadas en el README)."""
from ..db import q1, qa
from ..i18n import t
from . import grading, progress


def mastery(owner):
    """Dominio por competencia, usando solo el intento ENVIADO MÁS RECIENTE de cada evaluación."""
    if not owner:
        return []
    sql, p = owner.where()
    rows = qa(f"""SELECT q.competency_id, c.name, c.subject_id, SUM(r.points) AS got, SUM(q.points) AS tot, COUNT(*) AS n
                  FROM responses r JOIN questions q ON q.id=r.question_id JOIN competencies c ON c.id=q.competency_id
                  WHERE r.attempt_id IN (SELECT MAX(id) FROM attempts WHERE status='submitted' AND {sql}
                                         GROUP BY COALESCE(assessment_id, -id))
                  GROUP BY q.competency_id ORDER BY c.subject_id, c.id""", p)
    return [{**dict(r), "got": round(r["got"], 1), "level": grading.mastery_level(r["got"], r["tot"], r["n"])} for r in rows]


def _lesson_for_competency(cid):
    return q1("""SELECT l.id AS lesson_id, l.title, c.slug FROM questions q JOIN lessons l ON l.id=q.lesson_id
                 JOIN units u ON u.id=l.unit_id JOIN courses c ON c.id=u.course_id
                 WHERE q.competency_id=? AND c.status='published' ORDER BY l.id LIMIT 1""", (cid,))


def recommendations(owner, limit=5):
    recs, seen = [], set()

    def add(title, url, reason):
        if url not in seen and len(recs) < limit:
            seen.add(url)
            recs.append({"title": title, "url": url, "reason": reason})

    ms = mastery(owner)
    for m in ms:                                                   # 1) refuerzo de competencias débiles
        if m["level"] == "reforzar":
            les = _lesson_for_competency(m["competency_id"])
            if les:
                add(t("reco.review", title=les["title"]), f"/cursos/{les['slug']}/lecciones/{les['lesson_id']}",
                    t("reco.weak", got=m["got"], tot=int(m["tot"]), name=m["name"]))
    if owner:                                                      # 2) cursos empezados
        for c in qa("SELECT id, slug, title FROM courses WHERE status='published' ORDER BY id"):
            pr = progress.progress_for_courses(owner, [c["id"]])[c["id"]]
            if pr["started"] and not pr["completed"]:
                add(t("reco.continue", title=c["title"]), f"/cursos/{c['slug']}", t("reco.progress", pct=pr["percent"]))
    goals = []
    if owner:
        sql, p = owner.where()
        goals = qa(f"SELECT DISTINCT subject_id FROM learner_goals WHERE {sql}", p)
    for g in goals:                                                # 3) objetivos elegidos
        subj = q1("SELECT name FROM subjects WHERE id=?", (g["subject_id"],))
        subj_ms = [m for m in ms if m["subject_id"] == g["subject_id"] and m["level"] != "sin_datos"]
        high = bool(subj_ms) and sum(m["got"] for m in subj_ms) / max(1, sum(m["tot"] for m in subj_ms)) >= 0.8
        order = "DESC" if high else "ASC"
        for c in qa(f"SELECT id, slug, title FROM courses WHERE status='published' AND subject_id=? "
                    f"ORDER BY difficulty {order}, id", (g["subject_id"],)):
            if not progress.progress_for_courses(owner, [c["id"]])[c["id"]]["started"]:
                add(t("reco.start", title=c["title"]), f"/cursos/{c['slug']}",
                    t("reco.goal_high" if high else "reco.goal", subject=subj["name"]))
                break
    if not recs:                                                   # 4) sin datos: punto de partida
        c = q1("SELECT slug, title FROM courses WHERE status='published' ORDER BY difficulty, id LIMIT 1")
        if c:
            add(t("reco.start", title=c["title"]), f"/cursos/{c['slug']}", t("reco.nodata"))
    return recs
