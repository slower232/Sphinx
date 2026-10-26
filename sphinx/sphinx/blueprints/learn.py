import json
import math

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from ..db import q1, qa
from ..i18n import t
from ..security import login_required
from ..services import assessments, blocks, certificates, gamification as gam, grading, progress, recommend
from ..services.owner import get_owner

bp = Blueprint("learn", __name__)
LEVELS = ("inicial", "basico", "intermedio", "avanzado")


def _is_admin():
    return bool(g.user and g.user["role"] == "admin")


def _course(slug):
    c = q1("""SELECT c.*, s.name AS subject_name, s.slug AS subject_slug, s.icon, s.color FROM courses c
              JOIN subjects s ON s.id=c.subject_id WHERE c.slug=?""", (slug,))
    if not c or (c["status"] != "published" and not _is_admin()):     # los borradores no son públicos
        abort(404)
    return c


@bp.get("/cursos")
def courses():
    q = request.args.get("q", "").strip()[:80]
    subject, level, comp = request.args.get("materia", ""), request.args.get("nivel", ""), request.args.get("competencia", "")
    diff = request.args.get("dificultad", "")
    try:
        page = max(1, int(request.args.get("pagina", 1)))
    except ValueError:
        page = 1
    sql, params = ("SELECT c.*, s.name AS subject_name, s.icon, s.color FROM courses c JOIN subjects s ON s.id=c.subject_id "
                   "WHERE c.status='published'"), []
    if subject:
        sql += " AND s.slug=?"; params.append(subject)
    if level in LEVELS:
        sql += " AND c.level=?"; params.append(level)
    if diff in ("1", "2", "3"):
        sql += " AND c.difficulty=?"; params.append(int(diff))
    if comp:
        sql += (" AND c.id IN (SELECT cc.course_id FROM course_competencies cc "
                "JOIN competencies k ON k.id=cc.competency_id WHERE k.slug=?)"); params.append(comp)
    rows = qa(sql + " ORDER BY s.position, c.difficulty, c.title", params)
    if q:                                  # búsqueda sin distinguir mayúsculas ni acentos
        nq = grading.normalize_text(q)
        rows = [r for r in rows if nq in grading.normalize_text(r["title"] + " " + r["description"])]
    per = 9
    pages = max(1, math.ceil(len(rows) / per))
    page = min(page, pages)
    rows = rows[(page - 1) * per: page * per]
    prog = progress.progress_for_courses(get_owner(), [r["id"] for r in rows])
    return render_template("courses.html", courses=rows, progress=prog, page=page, pages=pages, q=q,
                           f={"materia": subject, "nivel": level, "dificultad": diff, "competencia": comp},
                           subjects=qa("SELECT * FROM subjects ORDER BY position"),
                           competencies=qa("SELECT slug, name FROM competencies ORDER BY subject_id, id"), levels=LEVELS)


@bp.get("/cursos/<slug>")
def course(slug):
    c = _course(slug)
    owner = get_owner()
    done = progress.completed_lesson_ids(owner, c["id"])
    units = []
    for u in qa("SELECT * FROM units WHERE course_id=? ORDER BY position, id", (c["id"],)):
        ls = qa("SELECT * FROM lessons WHERE unit_id=? ORDER BY position, id", (u["id"],))
        units.append({"unit": u, "lessons": ls})
    final = q1("""SELECT s.id, (SELECT COUNT(*) FROM assessment_questions WHERE assessment_id=s.id) AS n
                  FROM assessments s WHERE s.kind='final' AND s.course_id=?""", (c["id"],))
    cert = q1("SELECT code FROM certificates WHERE user_id=? AND course_id=?", (g.user["id"], c["id"])) if g.user else None
    can_cert = bool(g.user) and certificates.eligibility(g.user["id"], c)[0]
    return render_template(
        "course.html", c=c, units=units, done=done, final=final, cert=cert, can_cert=can_cert,
        objectives=json.loads(c["objectives"] or "[]"), pr=progress.progress_for_courses(owner, [c["id"]])[c["id"]],
        nxt=progress.next_lesson(owner, c["id"]) if owner else None,
        comps=qa("SELECT k.name FROM competencies k JOIN course_competencies cc ON cc.competency_id=k.id WHERE cc.course_id=?", (c["id"],)),
        quizzes={r["lesson_id"] for r in qa("SELECT lesson_id FROM assessments s WHERE kind='formative' AND course_id=? "
                                            "AND EXISTS (SELECT 1 FROM assessment_questions WHERE assessment_id=s.id)", (c["id"],))})


@bp.post("/cursos/<slug>/comenzar")
def start_course(slug):
    c = _course(slug)
    owner = get_owner(create=True)
    progress.ensure_enrollment(owner, c["id"])
    nxt = progress.next_lesson(owner, c["id"]) or (progress.course_lessons(c["id"]) or [None])[0]
    if not nxt:
        return redirect(url_for("learn.course", slug=slug))
    return redirect(url_for("learn.lesson", slug=slug, lesson_id=nxt["id"]))


def _lesson_row(c, lesson_id):
    l = q1("""SELECT l.*, u.title AS unit_title FROM lessons l JOIN units u ON u.id=l.unit_id
              WHERE l.id=? AND u.course_id=?""", (lesson_id, c["id"]))
    if not l:
        abort(404)
    return l


@bp.get("/cursos/<slug>/lecciones/<int:lesson_id>")
def lesson(slug, lesson_id):
    c = _course(slug)
    l = _lesson_row(c, lesson_id)
    owner = get_owner()
    all_l = progress.course_lessons(c["id"])
    idx = next(i for i, x in enumerate(all_l) if x["id"] == lesson_id)
    bl = [{"type": b["type"], "data": blocks.parse(b)} for b in
          qa("SELECT * FROM content_blocks WHERE lesson_id=? ORDER BY position, id", (lesson_id,))]
    return render_template("lesson.html", c=c, l=l, blocks=bl, idx=idx, total=len(all_l),
                           prev=all_l[idx - 1] if idx else None, nxt=all_l[idx + 1] if idx + 1 < len(all_l) else None,
                           done=lesson_id in progress.completed_lesson_ids(owner, c["id"]),
                           quiz_id=progress.lesson_quiz_id(lesson_id), pass_pct=gam.setting("formative_pass_pct"))


@bp.post("/cursos/<slug>/lecciones/<int:lesson_id>/completar")
def complete(slug, lesson_id):
    c = _course(slug)
    _lesson_row(c, lesson_id)
    if progress.lesson_quiz_id(lesson_id):            # si hay comprobación, hay que aprobarla
        flash(t("lesson.need_quiz"), "error")
        return redirect(url_for("learn.lesson", slug=slug, lesson_id=lesson_id))
    owner = get_owner(create=True)
    new, xp = progress.complete_lesson(owner, lesson_id, c["id"])
    if new:
        gam.check_achievements(owner)
        flash(t("lesson.completed", xp=xp), "success")
    return redirect(url_for("learn.lesson", slug=slug, lesson_id=lesson_id))


@bp.route("/objetivos", methods=["GET", "POST"])
def goals():
    subjects = qa("SELECT * FROM subjects ORDER BY position")
    comps = qa("SELECT * FROM competencies ORDER BY subject_id, id")
    owner = get_owner()
    if request.method == "POST":
        owner = get_owner(create=True)
        sql, p = owner.where()
        from ..db import ex, tx
        valid_c = {c["id"]: c["subject_id"] for c in comps}
        valid_s = {s["id"] for s in subjects}
        with tx():
            ex(f"DELETE FROM learner_goals WHERE {sql}", p)
            for s in request.form.getlist("subject"):
                if s.isdigit() and int(s) in valid_s:
                    ex("INSERT OR IGNORE INTO learner_goals(user_id, anon_id, subject_id) VALUES (?,?,?)", (owner.user_id, owner.anon_id, int(s)))
            for c in request.form.getlist("competency"):
                if c.isdigit() and int(c) in valid_c:
                    ex("INSERT OR IGNORE INTO learner_goals(user_id, anon_id, subject_id, competency_id) VALUES (?,?,?,?)",
                       (owner.user_id, owner.anon_id, valid_c[int(c)], int(c)))
        flash(t("goals.saved"), "success")
        return redirect(url_for("learn.goals"))
    sel_s, sel_c = set(), set()
    if owner:
        sql, p = owner.where()
        for g_ in qa(f"SELECT subject_id, competency_id FROM learner_goals WHERE {sql}", p):
            (sel_c.add(g_["competency_id"]) if g_["competency_id"] else sel_s.add(g_["subject_id"]))
    diag = {r["subject_id"]: r["id"] for r in qa("SELECT id, subject_id FROM assessments s WHERE kind='diagnostic' "
                                                  "AND EXISTS (SELECT 1 FROM assessment_questions WHERE assessment_id=s.id)")}
    return render_template("goals.html", subjects=subjects, comps=comps, sel_s=sel_s, sel_c=sel_c, diag=diag,
                           recs=recommend.recommendations(owner, 3))


@bp.get("/diagnostico/<subject_slug>")
def diagnostic(subject_slug):
    s = q1("SELECT * FROM subjects WHERE slug=?", (subject_slug,))
    if not s:
        abort(404)
    a = q1("""SELECT s.id, (SELECT COUNT(*) FROM assessment_questions WHERE assessment_id=s.id) AS n
              FROM assessments s WHERE kind='diagnostic' AND subject_id=?""", (s["id"],))
    if not a or not a["n"]:
        abort(404)
    return render_template("diagnostic.html", s=s, a=a)


@bp.post("/evaluaciones/<int:aid>/iniciar")
def start_assessment(aid):
    owner = get_owner(create=True)
    attempt_id, err = assessments.start_attempt(owner, aid, preview=_is_admin())
    if err:
        flash(t(err), "error")
        return redirect(request.referrer or url_for("learn.courses"))
    return redirect(url_for("learn.attempt", attempt_id=attempt_id))


@bp.post("/repaso")
def review():
    owner = get_owner()
    attempt_id = assessments.start_review(owner) if owner else None
    if not attempt_id:
        flash(t("review.none"), "info")
        return redirect(url_for("student.dashboard"))
    return redirect(url_for("learn.attempt", attempt_id=attempt_id))


def _context(att):
    ctx = {"title": t("review.title"), "back_url": url_for("student.dashboard"), "course": None, "lesson": None, "subject": None, "color": "green"}
    if att["assessment_id"]:
        a = q1("""SELECT s.*, c.slug AS course_slug, c.title AS course_title, c.pass_pct, sb.color AS color FROM assessments s
                  LEFT JOIN courses c ON c.id=s.course_id
                  LEFT JOIN subjects sb ON sb.id=COALESCE(s.subject_id, c.subject_id) WHERE s.id=?""", (att["assessment_id"],))
        ctx.update(title=a["title"], pass_pct=a["pass_pct"], color=a["color"])
        if a["course_slug"]:
            ctx["back_url"] = (url_for("learn.lesson", slug=a["course_slug"], lesson_id=a["lesson_id"])
                               if a["lesson_id"] else url_for("learn.course", slug=a["course_slug"]))
            ctx["course"] = {"slug": a["course_slug"], "title": a["course_title"], "id": a["course_id"]}
        else:
            ctx["back_url"] = url_for("learn.goals")
            ctx["subject"] = q1("SELECT * FROM subjects WHERE id=?", (a["subject_id"],))
    return ctx


@bp.get("/intentos/<int:attempt_id>")
def attempt(attempt_id):
    owner = get_owner()
    att = assessments.get_attempt(owner, attempt_id) if owner else None
    if not att:
        abort(404)
    ctx = _context(att)
    if att["status"] == "in_progress":
        qs = assessments.load_questions(json.loads(att["question_ids"]))
        questions = [assessments.public_question(qs[i]) for i in json.loads(att["question_ids"])]
        return render_template("attempt.html", att=att, questions=questions, ctx=ctx)
    results = assessments.attempt_results(att)
    pass_ = ctx.get("pass_pct") if att["kind"] == "final" else gam.setting("formative_pass_pct")
    extra = {}
    if att["kind"] in ("diagnostic", "review"):
        extra["breakdown"] = assessments.competency_breakdown(results)
        extra["recs"] = recommend.recommendations(owner, 3)
    if att["kind"] == "final" and att["passed"] and g.user:
        extra["can_cert"] = certificates.eligibility(g.user["id"], q1("SELECT * FROM courses WHERE id=?", (ctx["course"]["id"],)))[0]
    return render_template("results.html", att=att, results=results, ctx=ctx, pass_pct=pass_, **extra)


@bp.post("/intentos/<int:attempt_id>/enviar")
def submit(attempt_id):
    owner = get_owner()
    if not owner:
        abort(404)
    try:
        att, summary = assessments.submit_attempt(owner, attempt_id, request.form)
    except LookupError:
        abort(404)
    if summary and summary["xp"]:
        flash(t("xp.earned", xp=summary["xp"]), "success")
    for b in (summary or {}).get("badges", []):
        flash(t("badge.earned", name=b), "success")
    return redirect(url_for("learn.attempt", attempt_id=attempt_id))
