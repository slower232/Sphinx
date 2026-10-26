"""Panel administrativo. TODAS las rutas exigen rol 'admin' validado en el servidor."""
import json
import math
import re

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from ..db import ex, q1, qa, tx
from ..i18n import t
from ..services import blocks, gamification as gam, grading, progress

bp = Blueprint("admin", __name__, url_prefix="/admin")
LEVELS = ("inicial", "basico", "intermedio", "avanzado")
KINDS = ("mcq", "tf", "numeric", "short", "match")
COLORS = ("green", "red", "blue", "orange", "purple")


@bp.before_request
def guard():
    if not g.user:
        return redirect(url_for("auth.login", next=request.path))
    if g.user["role"] != "admin":
        abort(403)


def audit(action, entity, entity_id=None, detail=""):
    ex("INSERT INTO audit_log(admin_id, action, entity, entity_id, detail) VALUES (?,?,?,?,?)",
       (g.user["id"], action, entity, entity_id, str(detail)[:300]))


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", grading.normalize_text(text).replace("/", " ")).strip("-")
    return s[:60] or "item"


def _int(value, default=None, lo=None, hi=None):
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    if (lo is not None and n < lo) or (hi is not None and n > hi):
        return default
    return n


def _move(table, row_id, scope_col, direction):
    assert (table, scope_col) in (("units", "course_id"), ("lessons", "unit_id"), ("content_blocks", "lesson_id"))
    row = q1(f"SELECT {scope_col} AS scope FROM {table} WHERE id=?", (row_id,))
    if not row:
        abort(404)
    ids = [r["id"] for r in qa(f"SELECT id FROM {table} WHERE {scope_col}=? ORDER BY position, id", (row["scope"],))]
    i = ids.index(row_id)
    j = i - 1 if direction == "up" else i + 1
    if 0 <= j < len(ids):
        ids[i], ids[j] = ids[j], ids[i]
    for pos, rid in enumerate(ids):
        ex(f"UPDATE {table} SET position=? WHERE id=?", (pos, rid))


# ------------------------------------------------------------------ panel
@bp.get("/")
def dashboard():
    c = lambda sql: q1(sql)["c"]
    stats = {
        "students": c("SELECT COUNT(*) c FROM users WHERE role='student'"),
        "guests": c("SELECT COUNT(*) c FROM anon_sessions WHERE last_seen_at > datetime('now','-30 days')"),
        "published": c("SELECT COUNT(*) c FROM courses WHERE status='published'"),
        "drafts": c("SELECT COUNT(*) c FROM courses WHERE status='draft'"),
        "attempts": c("SELECT COUNT(*) c FROM attempts WHERE status='submitted'"),
        "lessons_done": c("SELECT COUNT(*) c FROM lesson_progress"),
        "certs": c("SELECT COUNT(*) c FROM certificates"),
    }
    per_course = qa("""SELECT c.title,
        (SELECT COUNT(*) FROM enrollments e WHERE e.course_id=c.id) AS enrolled,
        (SELECT COUNT(*) FROM enrollments e WHERE e.course_id=c.id AND e.completed_at IS NOT NULL) AS completed,
        (SELECT ROUND(AVG(a.score_pct),1) FROM attempts a JOIN assessments s ON s.id=a.assessment_id
          WHERE s.course_id=c.id AND a.kind='final' AND a.status='submitted') AS avg_final
        FROM courses c WHERE c.status='published' ORDER BY c.title""")
    return render_template("admin/dashboard.html", stats=stats, per_course=per_course)


# ------------------------------------------------------------------ cursos
@bp.get("/cursos")
def courses():
    rows = qa("""SELECT c.*, s.name AS subject_name,
                 (SELECT COUNT(*) FROM lessons l JOIN units u ON u.id=l.unit_id WHERE u.course_id=c.id) AS n_lessons
                 FROM courses c JOIN subjects s ON s.id=c.subject_id ORDER BY c.status, c.title""")
    return render_template("admin/courses.html", courses=rows)


def _parse_course(form, course_id=None):
    errors, d = {}, {}
    d["title"] = (form.get("title") or "").strip()
    if not d["title"] or len(d["title"]) > 120:
        errors["title"] = "adm.val.title"
    d["slug"] = slugify(form.get("slug") or d["title"])
    if q1("SELECT 1 FROM courses WHERE slug=? AND id IS NOT ?", (d["slug"], course_id)):
        errors["slug"] = "adm.val.slug_taken"
    d["subject_id"] = _int(form.get("subject_id"))
    if not d["subject_id"] or not q1("SELECT 1 FROM subjects WHERE id=?", (d["subject_id"],)):
        errors["subject_id"] = "adm.val.subject"
    d["description"] = (form.get("description") or "").strip()
    if not d["description"] or len(d["description"]) > 1000:
        errors["description"] = "adm.val.description"
    obj = [x.strip() for x in (form.get("objectives") or "").splitlines() if x.strip()]
    if not obj or len(obj) > 8 or any(len(x) > 200 for x in obj):
        errors["objectives"] = "adm.val.objectives"
    d["objectives"] = json.dumps(obj, ensure_ascii=False)
    d["level"] = form.get("level") if form.get("level") in LEVELS else None
    d["difficulty"] = _int(form.get("difficulty"), lo=1, hi=3)
    d["est_minutes"] = _int(form.get("est_minutes"), lo=1, hi=600)
    d["pass_pct"] = _int(form.get("pass_pct"), lo=1, hi=100)
    d["max_attempts"] = _int(form.get("max_attempts", 0), lo=0, hi=20)
    for k in ("level", "difficulty", "est_minutes", "pass_pct", "max_attempts"):
        if d[k] is None:
            errors[k] = "adm.val.number"
    d["prerequisites"] = (form.get("prerequisites") or "").strip()[:300]
    d["resources"] = (form.get("resources") or "").strip()[:600]
    comps = {_int(x) for x in form.getlist("competencies")}
    valid = {r["id"] for r in qa("SELECT id FROM competencies WHERE subject_id=?", (d["subject_id"] or 0,))}
    d["competencies"] = sorted(c for c in comps if c in valid)
    return d, errors


def _course_render(course, errors=None, values=None):
    cid = course["id"] if course else None
    units = []
    if cid:
        for u in qa("SELECT * FROM units WHERE course_id=? ORDER BY position, id", (cid,)):
            units.append({"unit": u, "lessons": qa("SELECT * FROM lessons WHERE unit_id=? ORDER BY position, id", (u["id"],))})
    final = q1("SELECT id FROM assessments WHERE kind='final' AND course_id=?", (cid,)) if cid else None
    sel = {r["competency_id"] for r in qa("SELECT competency_id FROM course_competencies WHERE course_id=?", (cid,))} if cid else set()
    v = values or (dict(course) if course else {"level": "basico", "difficulty": 1, "est_minutes": 30, "pass_pct": 70, "max_attempts": 0})
    if course and not values:
        v["objectives"] = "\n".join(json.loads(course["objectives"] or "[]"))
    return render_template("admin/course_form.html", course=course, v=v, errors=errors or {}, units=units, final=final, sel=sel,
                           subject_opts=[(r["id"], r["name"]) for r in qa("SELECT id, name FROM subjects ORDER BY position")],
                           comps=qa("SELECT k.*, s.name AS subject FROM competencies k JOIN subjects s ON s.id=k.subject_id ORDER BY s.position, k.id"),
                           level_opts=[(l, t("level." + l)) for l in LEVELS])


@bp.route("/cursos/nuevo", methods=["GET", "POST"])
def course_new():
    if request.method == "POST":
        d, errors = _parse_course(request.form)
        if not errors:
            with tx():
                cid = ex("""INSERT INTO courses(slug, subject_id, title, description, objectives, level, difficulty, est_minutes,
                            prerequisites, resources, pass_pct, max_attempts) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (d["slug"], d["subject_id"], d["title"], d["description"], d["objectives"], d["level"], d["difficulty"],
                          d["est_minutes"], d["prerequisites"], d["resources"], d["pass_pct"], d["max_attempts"])).lastrowid
                for k in d["competencies"]:
                    ex("INSERT INTO course_competencies(course_id, competency_id) VALUES (?,?)", (cid, k))
                ex("INSERT INTO assessments(kind, title, course_id) VALUES ('final', ?, ?)", (f"Evaluación final: {d['title']}", cid))
                audit("create", "course", cid, d["title"])
            flash(t("adm.saved"), "success")
            return redirect(url_for("admin.course_edit", course_id=cid))
        return _course_render(None, errors, request.form.to_dict() | {"objectives": request.form.get("objectives", "")})
    return _course_render(None)


@bp.route("/cursos/<int:course_id>", methods=["GET", "POST"])
def course_edit(course_id):
    course = q1("SELECT * FROM courses WHERE id=?", (course_id,))
    if not course:
        abort(404)
    if request.method == "POST":
        d, errors = _parse_course(request.form, course_id)
        if errors:
            return _course_render(course, errors, request.form.to_dict())
        with tx():
            ex("""UPDATE courses SET slug=?, subject_id=?, title=?, description=?, objectives=?, level=?, difficulty=?, est_minutes=?,
                  prerequisites=?, resources=?, pass_pct=?, max_attempts=?, updated_at=datetime('now'),
                  version=version + (status='published') WHERE id=?""",
               (d["slug"], d["subject_id"], d["title"], d["description"], d["objectives"], d["level"], d["difficulty"], d["est_minutes"],
                d["prerequisites"], d["resources"], d["pass_pct"], d["max_attempts"], course_id))
            ex("DELETE FROM course_competencies WHERE course_id=?", (course_id,))
            for k in d["competencies"]:
                ex("INSERT INTO course_competencies(course_id, competency_id) VALUES (?,?)", (course_id, k))
            audit("update", "course", course_id, d["title"])
        flash(t("adm.saved"), "success")
        return redirect(url_for("admin.course_edit", course_id=course_id))
    return _course_render(course)


def publish_problems(course_id):
    problems = []
    lessons = progress.course_lessons(course_id)
    if not lessons:
        problems.append(t("adm.pub.no_lessons"))
    for l in lessons:
        if not q1("SELECT 1 FROM content_blocks WHERE lesson_id=?", (l["id"],)):
            problems.append(t("adm.pub.lesson_empty", title=l["title"]))
    n = q1("""SELECT COUNT(*) c FROM assessment_questions aq JOIN assessments s ON s.id=aq.assessment_id
              WHERE s.kind='final' AND s.course_id=?""", (course_id,))["c"]
    if not n:
        problems.append(t("adm.pub.no_final"))
    if not q1("SELECT 1 FROM course_competencies WHERE course_id=?", (course_id,)):
        problems.append(t("adm.pub.no_comps"))
    return problems


@bp.post("/cursos/<int:course_id>/estado")
def course_status(course_id):
    course = q1("SELECT * FROM courses WHERE id=?", (course_id,))
    if not course:
        abort(404)
    action = request.form.get("action")
    new = {"publish": "published", "unpublish": "draft", "archive": "archived", "restore": "draft"}.get(action)
    if not new:
        abort(400)
    if new == "published":
        problems = publish_problems(course_id)
        if problems:                       # un curso incompleto no se puede publicar por accidente
            for p in problems:
                flash(p, "error")
            return redirect(url_for("admin.course_edit", course_id=course_id))
    with tx():
        ex("UPDATE courses SET status=?, updated_at=datetime('now'), version=version + (?='published') WHERE id=?", (new, new, course_id))
        audit(action, "course", course_id, course["title"])
    flash(t("adm.status_done"), "success")
    return redirect(request.referrer or url_for("admin.courses"))


@bp.post("/cursos/<int:course_id>/eliminar")
def course_delete(course_id):
    course = q1("SELECT * FROM courses WHERE id=?", (course_id,))
    if not course:
        abort(404)
    if course["status"] != "draft":
        flash(t("adm.delete_only_draft"), "error")
        return redirect(url_for("admin.course_edit", course_id=course_id))
    with tx():
        ex("DELETE FROM courses WHERE id=?", (course_id,))
        audit("delete", "course", course_id, course["title"])
    flash(t("adm.deleted"), "success")
    return redirect(url_for("admin.courses"))


# ------------------------------------------------------------------ unidades y lecciones
@bp.post("/cursos/<int:course_id>/unidades")
def unit_add(course_id):
    title = (request.form.get("title") or "").strip()[:120]
    if not q1("SELECT 1 FROM courses WHERE id=?", (course_id,)):
        abort(404)
    if not title:
        flash(t("adm.val.title"), "error")
    else:
        pos = q1("SELECT COALESCE(MAX(position)+1,0) p FROM units WHERE course_id=?", (course_id,))["p"]
        uid = ex("INSERT INTO units(course_id, title, position) VALUES (?,?,?)", (course_id, title, pos)).lastrowid
        audit("create", "unit", uid, title)
    return redirect(url_for("admin.course_edit", course_id=course_id))


@bp.post("/unidades/<int:unit_id>")
def unit_update(unit_id):
    u = q1("SELECT * FROM units WHERE id=?", (unit_id,))
    if not u:
        abort(404)
    action = request.form.get("action")
    if action in ("up", "down"):
        _move("units", unit_id, "course_id", action)
    elif action == "delete":
        with tx():
            ex("DELETE FROM units WHERE id=?", (unit_id,))
            audit("delete", "unit", unit_id, u["title"])
    else:
        title = (request.form.get("title") or "").strip()[:120]
        if title:
            ex("UPDATE units SET title=? WHERE id=?", (title, unit_id))
            audit("update", "unit", unit_id, title)
    return redirect(url_for("admin.course_edit", course_id=u["course_id"]))


@bp.post("/unidades/<int:unit_id>/lecciones")
def lesson_add(unit_id):
    u = q1("SELECT * FROM units WHERE id=?", (unit_id,))
    if not u:
        abort(404)
    title = (request.form.get("title") or "").strip()[:120]
    if title:
        with tx():
            pos = q1("SELECT COALESCE(MAX(position)+1,0) p FROM lessons WHERE unit_id=?", (unit_id,))["p"]
            lid = ex("INSERT INTO lessons(unit_id, title, position) VALUES (?,?,?)", (unit_id, title, pos)).lastrowid
            ex("INSERT INTO assessments(kind, title, course_id, lesson_id) VALUES ('formative', ?, ?, ?)",
               (f"Comprueba: {title}", u["course_id"], lid))
            audit("create", "lesson", lid, title)
        return redirect(url_for("admin.lesson_edit", lesson_id=lid))
    flash(t("adm.val.title"), "error")
    return redirect(url_for("admin.course_edit", course_id=u["course_id"]))


def _lesson(lesson_id):
    l = q1("""SELECT l.*, u.course_id, c.title AS course_title, c.slug AS course_slug FROM lessons l
              JOIN units u ON u.id=l.unit_id JOIN courses c ON c.id=u.course_id WHERE l.id=?""", (lesson_id,))
    if not l:
        abort(404)
    return l


@bp.route("/lecciones/<int:lesson_id>", methods=["GET", "POST"])
def lesson_edit(lesson_id):
    l = _lesson(lesson_id)
    if request.method == "POST":
        action = request.form.get("action")
        if action in ("up", "down"):
            _move("lessons", lesson_id, "unit_id", action)
            return redirect(url_for("admin.course_edit", course_id=l["course_id"]))
        if action == "delete":
            with tx():
                ex("DELETE FROM lessons WHERE id=?", (lesson_id,))
                audit("delete", "lesson", lesson_id, l["title"])
            return redirect(url_for("admin.course_edit", course_id=l["course_id"]))
        title = (request.form.get("title") or "").strip()[:120]
        minutes = _int(request.form.get("est_minutes"), lo=1, hi=240)
        if not title or minutes is None:
            flash(t("adm.val.title"), "error")
        else:
            ex("UPDATE lessons SET title=?, summary=?, est_minutes=? WHERE id=?",
               (title, (request.form.get("summary") or "").strip()[:500], minutes, lesson_id))
            audit("update", "lesson", lesson_id, title)
            flash(t("adm.saved"), "success")
        return redirect(url_for("admin.lesson_edit", lesson_id=lesson_id))
    bl = [{"row": b, "data": blocks.parse(b)} for b in qa("SELECT * FROM content_blocks WHERE lesson_id=? ORDER BY position, id", (lesson_id,))]
    quiz = q1("SELECT id FROM assessments WHERE kind='formative' AND lesson_id=?", (lesson_id,))
    return render_template("admin/lesson_form.html", l=l, blocks=bl, quiz=quiz, types=blocks.BLOCK_TYPES, f=blocks.to_form("text", {}))


@bp.post("/lecciones/<int:lesson_id>/bloques")
def block_add(lesson_id):
    _lesson(lesson_id)
    btype = request.form.get("type", "")
    try:
        data = blocks.from_form(btype, request.form)
    except ValueError as e:
        flash(t(str(e)) if str(e).startswith("block.") else t("block.need_body"), "error")
        return redirect(url_for("admin.lesson_edit", lesson_id=lesson_id))
    pos = q1("SELECT COALESCE(MAX(position)+1,0) p FROM content_blocks WHERE lesson_id=?", (lesson_id,))["p"]
    bid = ex("INSERT INTO content_blocks(lesson_id, position, type, data) VALUES (?,?,?,?)",
             (lesson_id, pos, btype, json.dumps(data, ensure_ascii=False))).lastrowid
    audit("create", "block", bid, btype)
    flash(t("adm.saved"), "success")
    return redirect(url_for("admin.lesson_edit", lesson_id=lesson_id))


@bp.route("/bloques/<int:block_id>", methods=["GET", "POST"])
def block_edit(block_id):
    b = q1("SELECT * FROM content_blocks WHERE id=?", (block_id,))
    if not b:
        abort(404)
    if request.method == "POST":
        action = request.form.get("action")
        if action in ("up", "down"):
            _move("content_blocks", block_id, "lesson_id", action)
        elif action == "delete":
            ex("DELETE FROM content_blocks WHERE id=?", (block_id,))
            audit("delete", "block", block_id, b["type"])
        else:
            try:
                data = blocks.from_form(b["type"], request.form)
            except ValueError as e:
                flash(t(str(e)) if str(e).startswith("block.") else t("block.need_body"), "error")
                return redirect(url_for("admin.block_edit", block_id=block_id))
            ex("UPDATE content_blocks SET data=? WHERE id=?", (json.dumps(data, ensure_ascii=False), block_id))
            audit("update", "block", block_id, b["type"])
            flash(t("adm.saved"), "success")
            return redirect(url_for("admin.block_edit", block_id=block_id))
        return redirect(url_for("admin.lesson_edit", lesson_id=b["lesson_id"]))
    return render_template("admin/block_form.html", b=b, f=blocks.to_form(b["type"], blocks.parse(b)))


# ------------------------------------------------------------------ preguntas y evaluaciones
def _parse_question(form):
    errors, d, data, options = {}, {}, {}, []
    d["kind"] = form.get("kind") if form.get("kind") in KINDS else None
    d["prompt"] = (form.get("prompt") or "").strip()
    d["explanation"] = (form.get("explanation") or "").strip()[:1000]
    d["difficulty"] = _int(form.get("difficulty"), lo=1, hi=3)
    try:
        d["points"] = float(form.get("points") or 1)
        if not 0 < d["points"] <= 10:
            raise ValueError
    except ValueError:
        d["points"] = None
    d["competency_id"] = _int(form.get("competency_id"))
    d["lesson_id"] = _int(form.get("lesson_id"))
    if not d["kind"]:
        errors["kind"] = "adm.val.kind"
    if not d["prompt"] or len(d["prompt"]) > 2000:
        errors["prompt"] = "adm.val.prompt"
    if d["difficulty"] is None or d["points"] is None:
        errors["difficulty"] = "adm.val.number"
    if not d["competency_id"] or not q1("SELECT 1 FROM competencies WHERE id=?", (d["competency_id"],)):
        errors["competency_id"] = "adm.val.competency"
    if d["lesson_id"] and not q1("SELECT 1 FROM lessons WHERE id=?", (d["lesson_id"],)):
        d["lesson_id"] = None
    k = d["kind"]
    if k == "mcq":
        raw = [(form.get(f"opt{i}") or "").strip() for i in range(4)]
        correct = _int(form.get("correct"), lo=0, hi=3)
        if sum(1 for x in raw if x) < 2 or correct is None or not raw[correct] or any(len(x) > 300 for x in raw):
            errors["options"] = "adm.val.options"
        options = [(x, i == correct) for i, x in enumerate(raw) if x]
    elif k == "tf":
        if form.get("tf_correct") not in ("true", "false"):
            errors["options"] = "adm.val.tf"
        options = [("Verdadero", form.get("tf_correct") == "true"), ("Falso", form.get("tf_correct") == "false")]
    elif k == "numeric":
        tol = form.get("tolerance") or "0"
        if grading.parse_number(form.get("answer")) is None or grading.parse_number(tol) is None or grading.parse_number(tol) < 0:
            errors["answer"] = "adm.val.numeric"
        data = {"answer": (form.get("answer") or "").strip(), "tolerance": tol.strip()}
    elif k == "short":
        acc = [x.strip() for x in (form.get("accepted") or "").splitlines() if x.strip()]
        if not acc or len(acc) > 10:
            errors["accepted"] = "adm.val.accepted"
        data = {"accepted": acc}
    elif k == "match":
        pairs = []
        for ln in (form.get("pairs") or "").splitlines():
            if "=" in ln:
                a, b = (x.strip() for x in ln.split("=", 1))
                if a and b:
                    pairs.append([a, b])
        rights = {grading.normalize_text(b) for _, b in pairs}
        if not 2 <= len(pairs) <= 8 or len(rights) != len(pairs):
            errors["pairs"] = "adm.val.pairs"
        data = {"pairs": pairs}
    return d, data, options, errors


def _save_question(qid, d, data, options):
    with tx():
        if qid:
            ex("UPDATE questions SET kind=?, prompt=?, explanation=?, difficulty=?, points=?, data=?, competency_id=?, lesson_id=? WHERE id=?",
               (d["kind"], d["prompt"], d["explanation"], d["difficulty"], d["points"], json.dumps(data, ensure_ascii=False),
                d["competency_id"], d["lesson_id"], qid))
        else:
            qid = ex("INSERT INTO questions(kind, prompt, explanation, difficulty, points, data, competency_id, lesson_id) VALUES (?,?,?,?,?,?,?,?)",
                     (d["kind"], d["prompt"], d["explanation"], d["difficulty"], d["points"], json.dumps(data, ensure_ascii=False),
                      d["competency_id"], d["lesson_id"])).lastrowid
        old = qa("SELECT id FROM answer_options WHERE question_id=? ORDER BY position, id", (qid,))
        for pos, (text, ok) in enumerate(options):          # se actualizan en sitio para no romper intentos anteriores
            if pos < len(old):
                ex("UPDATE answer_options SET text=?, is_correct=?, position=? WHERE id=?", (text, int(ok), pos, old[pos]["id"]))
            else:
                ex("INSERT INTO answer_options(question_id, position, text, is_correct) VALUES (?,?,?,?)", (qid, pos, text, int(ok)))
        for extra in old[len(options):]:
            ex("DELETE FROM answer_options WHERE id=?", (extra["id"],))
        audit("save", "question", qid, d["prompt"][:80])
    return qid


@bp.get("/preguntas")
def questions():
    subject, page = request.args.get("materia", ""), _int(request.args.get("pagina"), 1, 1)
    sql = ("SELECT q.id, q.kind, q.prompt, q.difficulty, k.name AS comp, "
           "(SELECT COUNT(*) FROM responses r WHERE r.question_id=q.id) AS n_resp "
           "FROM questions q JOIN competencies k ON k.id=q.competency_id JOIN subjects s ON s.id=k.subject_id")
    params = []
    if subject:
        sql += " WHERE s.slug=?"; params.append(subject)
    rows = qa(sql + " ORDER BY q.id DESC", params)
    per, pages = 20, max(1, math.ceil(len(rows) / 20))
    page = min(page, pages)
    return render_template("admin/questions.html", rows=rows[(page - 1) * per: page * per], page=page, pages=pages, subject=subject,
                           subjects=qa("SELECT * FROM subjects ORDER BY position"))


def _question_render(qid, errors=None, values=None):
    q, opts = None, []
    if qid:
        q = q1("SELECT * FROM questions WHERE id=?", (qid,))
        if not q:
            abort(404)
        opts = qa("SELECT * FROM answer_options WHERE question_id=? ORDER BY position, id", (qid,))
    v = values or ({} if not q else _question_values(q, opts))
    return render_template("admin/question_form.html", q=q, v=v, errors=errors or {},
                           comps=qa("SELECT k.*, s.name AS subject FROM competencies k JOIN subjects s ON s.id=k.subject_id ORDER BY s.position, k.id"),
                           lessons=qa("SELECT l.id, l.title, c.title AS course FROM lessons l JOIN units u ON u.id=l.unit_id JOIN courses c ON c.id=u.course_id ORDER BY c.title, u.position, l.position"),
                           kinds=KINDS)


def _question_values(q, opts):
    data = json.loads(q["data"] or "{}")
    v = {"kind": q["kind"], "prompt": q["prompt"], "explanation": q["explanation"], "difficulty": q["difficulty"], "points": q["points"],
         "competency_id": q["competency_id"], "lesson_id": q["lesson_id"], "answer": data.get("answer", ""), "tolerance": data.get("tolerance", "0"),
         "accepted": "\n".join(data.get("accepted", [])), "pairs": "\n".join(f"{a} = {b}" for a, b in data.get("pairs", []))}
    for i, o in enumerate(opts[:4]):
        v[f"opt{i}"] = o["text"]
        if o["is_correct"]:
            v["correct"] = str(i)
            v["tf_correct"] = "true" if o["text"] == "Verdadero" else "false"
    return v


@bp.route("/preguntas/nueva", methods=["GET", "POST"])
@bp.route("/preguntas/<int:qid>", methods=["GET", "POST"])
def question_edit(qid=None):
    if request.method == "POST":
        d, data, options, errors = _parse_question(request.form)
        if errors:
            return _question_render(qid, errors, request.form.to_dict())
        qid = _save_question(qid, d, data, options)
        flash(t("adm.saved"), "success")
        return redirect(url_for("admin.question_edit", qid=qid))
    return _question_render(qid)


@bp.post("/preguntas/<int:qid>/eliminar")
def question_delete(qid):
    if q1("SELECT 1 FROM responses WHERE question_id=?", (qid,)):
        flash(t("adm.question_in_use"), "error")
        return redirect(url_for("admin.question_edit", qid=qid))
    with tx():
        ex("DELETE FROM questions WHERE id=?", (qid,))
        audit("delete", "question", qid)
    flash(t("adm.deleted"), "success")
    return redirect(url_for("admin.questions"))


@bp.get("/evaluaciones")
def assessments_list():
    rows = qa("""SELECT s.*, c.title AS course_title, sb.name AS subject_name, l.title AS lesson_title,
                 (SELECT COUNT(*) FROM assessment_questions WHERE assessment_id=s.id) AS n
                 FROM assessments s LEFT JOIN courses c ON c.id=s.course_id LEFT JOIN subjects sb ON sb.id=s.subject_id
                 LEFT JOIN lessons l ON l.id=s.lesson_id ORDER BY s.kind, s.id""")
    return render_template("admin/assessments.html", rows=rows)


@bp.route("/evaluaciones/<int:aid>", methods=["GET", "POST"])
def assessment_edit(aid):
    a = q1("""SELECT s.*, COALESCE(s.subject_id, c.subject_id) AS subj FROM assessments s LEFT JOIN courses c ON c.id=s.course_id WHERE s.id=?""", (aid,))
    if not a:
        abort(404)
    cands = qa("""SELECT q.id, q.prompt, q.kind, q.difficulty, k.name AS comp FROM questions q JOIN competencies k ON k.id=q.competency_id
                  WHERE k.subject_id=? ORDER BY k.id, q.difficulty, q.id""", (a["subj"],))
    if request.method == "POST":
        valid = {c["id"]: c["difficulty"] for c in cands}
        chosen = sorted({_int(x) for x in request.form.getlist("q")} & set(valid), key=lambda i: (valid[i], i))
        if len(chosen) > 30:
            flash(t("adm.val.too_many"), "error")
        else:
            with tx():
                ex("DELETE FROM assessment_questions WHERE assessment_id=?", (aid,))
                for pos, qid in enumerate(chosen):
                    ex("INSERT INTO assessment_questions(assessment_id, question_id, position) VALUES (?,?,?)", (aid, qid, pos))
                audit("update", "assessment", aid, a["title"])
            flash(t("adm.saved"), "success")
        return redirect(url_for("admin.assessment_edit", aid=aid))
    sel = {r["question_id"] for r in qa("SELECT question_id FROM assessment_questions WHERE assessment_id=?", (aid,))}
    return render_template("admin/assessment_form.html", a=a, cands=cands, sel=sel)


# ------------------------------------------------------------------ taxonomía, usuarios, ajustes, auditoría
@bp.get("/materias")
def taxonomy():
    subjects = [{"s": s, "comps": qa("SELECT * FROM competencies WHERE subject_id=? ORDER BY id", (s["id"],)),
                 "diag": q1("SELECT id FROM assessments WHERE kind='diagnostic' AND subject_id=?", (s["id"],))}
                for s in qa("SELECT * FROM subjects ORDER BY position, id")]
    return render_template("admin/taxonomy.html", subjects=subjects, colors=COLORS)


@bp.post("/materias")
def taxonomy_post():
    action, f = request.form.get("action"), request.form
    name = (f.get("name") or "").strip()[:80]
    if action == "add_subject" and name:
        slug = slugify(name)
        if q1("SELECT 1 FROM subjects WHERE slug=?", (slug,)):
            flash(t("adm.val.slug_taken"), "error")
        else:
            color = f.get("color") if f.get("color") in COLORS else "green"
            sid = ex("INSERT INTO subjects(slug, name, description, icon, position, color) VALUES (?,?,?,?, (SELECT COALESCE(MAX(position)+1,0) FROM subjects), ?)",
                     (slug, name, (f.get("description") or "")[:300], (f.get("icon") or "📘")[:4], color)).lastrowid
            audit("create", "subject", sid, name)
    elif action == "add_competency" and name and q1("SELECT 1 FROM subjects WHERE id=?", (_int(f.get("subject_id")),)):
        slug = slugify(name)
        n = 2
        while q1("SELECT 1 FROM competencies WHERE slug=?", (slug,)):
            slug, n = f"{slugify(name)}-{n}", n + 1
        cid = ex("INSERT INTO competencies(subject_id, slug, name, description) VALUES (?,?,?,?)",
                 (_int(f.get("subject_id")), slug, name, (f.get("description") or "")[:300])).lastrowid
        audit("create", "competency", cid, name)
    elif action == "delete_competency":
        cid = _int(f.get("id"))
        if q1("SELECT 1 FROM questions WHERE competency_id=?", (cid,)) or q1("SELECT 1 FROM course_competencies WHERE competency_id=?", (cid,)):
            flash(t("adm.in_use"), "error")
        else:
            ex("DELETE FROM competencies WHERE id=?", (cid,))
            audit("delete", "competency", cid)
    elif action == "delete_subject":
        sid = _int(f.get("id"))
        if q1("SELECT 1 FROM courses WHERE subject_id=?", (sid,)) or q1("SELECT 1 FROM competencies WHERE subject_id=?", (sid,)):
            flash(t("adm.in_use"), "error")
        else:
            ex("DELETE FROM subjects WHERE id=?", (sid,))
            audit("delete", "subject", sid)
    elif action == "add_diagnostic":
        s = q1("SELECT * FROM subjects WHERE id=?", (_int(f.get("id")),))
        if s and not q1("SELECT 1 FROM assessments WHERE kind='diagnostic' AND subject_id=?", (s["id"],)):
            aid = ex("INSERT INTO assessments(kind, title, subject_id) VALUES ('diagnostic', ?, ?)", (f"Diagnóstico de {s['name']}", s["id"])).lastrowid
            audit("create", "assessment", aid, "diagnostic")
            return redirect(url_for("admin.assessment_edit", aid=aid))
    else:
        flash(t("adm.val.title"), "error")
    return redirect(url_for("admin.taxonomy"))


@bp.get("/usuarios")
def users():
    page = _int(request.args.get("pagina"), 1, 1)
    rows = qa("SELECT id, alias, (email IS NOT NULL) AS has_email, role, is_active, created_at FROM users ORDER BY id DESC")
    per, pages = 25, max(1, math.ceil(len(rows) / 25))
    page = min(page, pages)
    return render_template("admin/users.html", rows=rows[(page - 1) * per: page * per], page=page, pages=pages)


@bp.post("/usuarios/<int:uid>/acceso")
def user_access(uid):
    u = q1("SELECT * FROM users WHERE id=?", (uid,))
    if not u:
        abort(404)
    if uid == g.user["id"]:
        flash(t("adm.self_action"), "error")
    else:
        active = 1 if request.form.get("action") == "activate" else 0
        ex("UPDATE users SET is_active=?, updated_at=datetime('now') WHERE id=?", (active, uid))
        audit("activate" if active else "revoke", "user", uid, u["alias"])
        flash(t("adm.saved"), "success")
    return redirect(url_for("admin.users"))


@bp.route("/ajustes", methods=["GET", "POST"])
def settings():
    keys = list(gam.DEFAULTS)
    if request.method == "POST":
        vals = {k: _int(request.form.get(k), lo=1 if k == "formative_pass_pct" else 0, hi=100 if k == "formative_pass_pct" else 1000) for k in keys}
        if None in vals.values():
            flash(t("adm.val.number"), "error")
        else:
            with tx():
                for k, v in vals.items():
                    ex("INSERT INTO settings(key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, str(v)))
                audit("update", "settings", None, json.dumps(vals))
            flash(t("adm.saved"), "success")
        return redirect(url_for("admin.settings"))
    return render_template("admin/settings.html", values={k: gam.setting(k) for k in keys})


@bp.get("/auditoria")
def audit_log():
    rows = qa("SELECT a.*, u.alias FROM audit_log a LEFT JOIN users u ON u.id=a.admin_id ORDER BY a.id DESC LIMIT 200")
    return render_template("admin/audit.html", rows=rows)
