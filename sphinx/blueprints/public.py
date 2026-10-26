from flask import Blueprint, render_template, request

from ..db import q1, qa
from ..services import certificates

bp = Blueprint("public", __name__)


@bp.get("/")
def home():
    subjects = qa("""SELECT s.*, (SELECT COUNT(*) FROM courses c WHERE c.subject_id=s.id AND c.status='published') AS n_courses
                     FROM subjects s ORDER BY s.position, s.id""")
    featured = qa("""SELECT c.*, s.name AS subject_name, s.icon, s.color FROM courses c JOIN subjects s ON s.id=c.subject_id
                     WHERE c.status='published' ORDER BY c.difficulty, c.id LIMIT 3""")
    return render_template("home.html", subjects=subjects, featured=featured)


@bp.get("/privacidad")
def privacy():
    return render_template("pages/privacy.html")


@bp.get("/accesibilidad")
def accessibility():
    return render_template("pages/accessibility.html")


@bp.get("/contacto")
def contact():
    return render_template("pages/contact.html")


@bp.get("/verificar")
@bp.get("/verificar/<code>")
def verify(code=None):
    code = (code or request.args.get("codigo", "")).strip()[:30]
    cert = certificates.verify(code) if code else None
    return render_template("verify.html", code=code, cert=cert)


@bp.get("/salud")
def health():
    q1("SELECT 1")
    return {"status": "ok"}
