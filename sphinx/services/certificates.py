"""Emisión (con verificación de requisitos en el servidor), verificación pública y PDF."""
import io
import secrets
from datetime import datetime

from ..db import ex, q1, tx
from . import progress


def eligibility(user_id, course):
    """Devuelve (ok, [claves de requisitos pendientes]). Se comprueba SIEMPRE en el servidor."""
    from .owner import Owner
    owner = Owner(user_id=user_id)
    missing = []
    lessons = progress.course_lessons(course["id"])
    done = progress.completed_lesson_ids(owner, course["id"])
    if not lessons or any(l["id"] not in done for l in lessons):
        missing.append("cert.need_lessons")
    final = progress.best_final(owner, course["id"])
    if not final:
        missing.append("cert.need_final")
    return (not missing), missing, final


def issue(user_id, course, display_name):
    """Emite el certificado si cumple los requisitos. Idempotente: devuelve el existente si ya se emitió."""
    with tx():
        existing = q1("SELECT * FROM certificates WHERE user_id=? AND course_id=?", (user_id, course["id"]))
        if existing:
            return existing, []
        ok, missing, final = eligibility(user_id, course)
        if not ok:
            return None, missing
        code = "SPX-" + "-".join(secrets.token_hex(2).upper() for _ in range(3))   # aleatorio: no revela datos
        ex("INSERT INTO certificates(code, user_id, course_id, display_name, score_pct) VALUES (?,?,?,?,?)",
           (code, user_id, course["id"], display_name[:60], final["score_pct"]))
        return q1("SELECT * FROM certificates WHERE code=?", (code,)), []


def verify(code):
    """Datos mínimos públicos: nombre/alias autorizado, curso y fecha."""
    return q1("""SELECT c.code, c.display_name, c.issued_at, k.title AS course_title FROM certificates c
                 JOIN courses k ON k.id=c.course_id WHERE c.code=? AND c.revoked_at IS NULL""", (code.strip().upper(),))


def build_pdf(cert, course_title, verify_url, texts):
    """PDF real con reportlab. `texts` trae los textos ya traducidos."""
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    w, h = landscape(A4)
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.setTitle(f"Sphinx – {cert['code']}")
    c.setStrokeColor(HexColor("#4f46e5"))
    c.setLineWidth(6)
    c.rect(24, 24, w - 48, h - 48)
    c.setFillColor(HexColor("#4f46e5"))
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(w / 2, h - 100, "SPHINX")
    c.setFillColor(HexColor("#111827"))
    c.setFont("Helvetica", 16)
    c.drawCentredString(w / 2, h - 135, texts["title"])
    c.setFont("Helvetica", 14)
    c.drawCentredString(w / 2, h - 195, texts["awarded"])
    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(w / 2, h - 245, cert["display_name"])
    c.setFont("Helvetica", 14)
    c.drawCentredString(w / 2, h - 285, texts["completed"])
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(w / 2, h - 320, course_title)
    c.setFont("Helvetica", 13)
    date = datetime.fromisoformat(cert["issued_at"]).strftime("%d/%m/%Y")
    c.drawCentredString(w / 2, h - 365, f"{texts['score']}: {cert['score_pct']:.0f}%   ·   {texts['date']}: {date}")
    c.setFont("Helvetica", 11)
    c.drawCentredString(w / 2, 95, f"{texts['code']}: {cert['code']}")
    c.drawCentredString(w / 2, 78, f"{texts['verify']}: {verify_url}")
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(HexColor("#6b7280"))
    c.drawCentredString(w / 2, 50, texts["disclaimer"])
    c.showPage()
    c.save()
    return buf.getvalue()
