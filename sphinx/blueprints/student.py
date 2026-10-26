import json

from flask import Blueprint, Response, abort, current_app, flash, g, make_response, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from ..db import q1, qa
from ..i18n import t
from ..security import PREF_ALLOWED, PREF_DEFAULTS, login_required, safe_next
from ..services import accounts, certificates, gamification as gam, progress, recommend
from ..services.owner import get_owner

bp = Blueprint("student", __name__)


@bp.get("/panel")
def dashboard():
    owner = get_owner()
    data = {"xp": gam.level_info(0), "streak": 0, "badges": [], "courses": [], "mastery": [], "history": [],
            "compare": [], "certs": [], "recs": recommend.recommendations(owner), "has_activity": False}
    if owner:
        data["xp"] = gam.level_info(gam.total_xp(owner))
        data["streak"] = gam.streak_days(owner) if g.prefs["streak"] == "on" else None
        s, p = owner.where("ua")
        data["badges"] = qa(f"SELECT a.name, a.description, a.icon, ua.earned_at FROM user_achievements ua "
                            f"JOIN achievements a ON a.id=ua.achievement_id WHERE {s} ORDER BY ua.earned_at", p)
        pubs = qa("SELECT c.id, c.slug, c.title, s.color FROM courses c JOIN subjects s ON s.id=c.subject_id WHERE c.status='published'")
        prog = progress.progress_for_courses(owner, [c["id"] for c in pubs])
        data["courses"] = [{"c": c, "p": prog[c["id"]]} for c in pubs if prog[c["id"]]["started"]]
        data["mastery"] = recommend.mastery(owner)
        s, p = owner.where("a")
        data["history"] = qa(f"""SELECT a.id, a.kind, a.score_pct, a.passed, a.submitted_at, m.title FROM attempts a
                                 LEFT JOIN assessments m ON m.id=a.assessment_id WHERE a.status='submitted' AND {s}
                                 ORDER BY a.id DESC LIMIT 15""", p)
        # Diagnóstico inicial vs última evaluación final de cada materia (pruebas distintas: comparación aproximada)
        for subj in qa("SELECT id, name FROM subjects ORDER BY position"):
            d = q1(f"""SELECT a.score_pct FROM attempts a JOIN assessments m ON m.id=a.assessment_id
                       WHERE a.kind='diagnostic' AND a.status='submitted' AND m.subject_id=? AND {s} ORDER BY a.id LIMIT 1""", (subj["id"],) + p)
            f = q1(f"""SELECT a.score_pct FROM attempts a JOIN assessments m ON m.id=a.assessment_id JOIN courses c ON c.id=m.course_id
                       WHERE a.kind='final' AND a.status='submitted' AND c.subject_id=? AND {s} ORDER BY a.id DESC LIMIT 1""", (subj["id"],) + p)
            if d or f:
                data["compare"].append({"name": subj["name"], "diag": d["score_pct"] if d else None, "final": f["score_pct"] if f else None})
        data["has_activity"] = bool(data["history"] or data["courses"] or data["badges"])
    if g.user:
        data["certs"] = qa("SELECT c.code, c.issued_at, k.title FROM certificates c JOIN courses k ON k.id=c.course_id "
                           "WHERE c.user_id=? AND c.revoked_at IS NULL ORDER BY c.issued_at DESC", (g.user["id"],))
    return render_template("dashboard.html", **data)


@bp.route("/preferencias", methods=["GET", "POST"])
def prefs():
    if request.method == "POST":
        new = {k: (request.form.get(k) if request.form.get(k) in PREF_ALLOWED[k] else PREF_DEFAULTS[k]) for k in PREF_DEFAULTS}
        resp = make_response(redirect(safe_next(request.form.get("next")) or url_for("student.prefs")))
        resp.set_cookie("prefs", "&".join(f"{k}={v}" for k, v in new.items()), max_age=31536000, samesite="Lax",
                        secure=current_app.config["ENV"] == "production")
        flash(t("prefs.saved"), "success")
        return resp
    return render_template("prefs.html")


@bp.get("/panel/cuenta")
@login_required
def account():
    return render_template("account.html")


@bp.get("/panel/exportar")
@login_required
def export():
    body = json.dumps(accounts.export_user(g.user["id"]), ensure_ascii=False, indent=2)
    return Response(body, mimetype="application/json",
                    headers={"Content-Disposition": "attachment; filename=sphinx-mis-datos.json"})


@bp.post("/panel/eliminar")
@login_required
def delete_account():
    row = q1("SELECT password_hash, role FROM users WHERE id=?", (g.user["id"],))
    if row["role"] == "admin":
        flash(t("account.admin_delete"), "error")
        return redirect(url_for("student.account"))
    if not check_password_hash(row["password_hash"], request.form.get("password") or ""):
        flash(t("account.bad_password"), "error")
        return redirect(url_for("student.account"))
    accounts.delete_user(g.user["id"])
    session.clear()
    flash(t("account.deleted"), "info")
    return redirect(url_for("public.home"))


@bp.post("/cursos/<slug>/certificado")
@login_required
def issue_certificate(slug):
    course = q1("SELECT * FROM courses WHERE slug=? AND status='published'", (slug,))
    if not course:
        abort(404)
    name = (request.form.get("display_name") or g.user["alias"]).strip()[:60] or g.user["alias"]
    cert, missing = certificates.issue(g.user["id"], course, name)
    if not cert:
        for key in missing:
            flash(t(key), "error")
        return redirect(url_for("learn.course", slug=slug))
    return redirect(url_for("student.certificate", code=cert["code"]))


def _own_cert(code):
    row = q1("""SELECT c.*, k.title AS course_title FROM certificates c JOIN courses k ON k.id=c.course_id
                WHERE c.code=? AND c.user_id=? AND c.revoked_at IS NULL""", (code, g.user["id"]))
    if not row:
        abort(404)
    return row


@bp.get("/certificados/<code>")
@login_required
def certificate(code):
    cert = _own_cert(code)
    return render_template("certificate.html", cert=cert, verify_url=f"{current_app.config['PUBLIC_BASE_URL']}/verificar/{cert['code']}")


@bp.get("/certificados/<code>.pdf")
@login_required
def certificate_pdf(code):
    cert = _own_cert(code)
    texts = {k: t(f"cert.pdf_{k}") for k in ("title", "awarded", "completed", "score", "date", "code", "verify", "disclaimer")}
    pdf = certificates.build_pdf(cert, cert["course_title"], f"{current_app.config['PUBLIC_BASE_URL']}/verificar/{cert['code']}", texts)
    return Response(pdf, mimetype="application/pdf", headers={"Content-Disposition": f"attachment; filename={cert['code']}.pdf"})
