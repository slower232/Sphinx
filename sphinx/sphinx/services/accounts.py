"""Cuentas: registro, autenticación, adopción de progreso anónimo, exportación, eliminación y recuperación."""
import hashlib
import logging
import re
import secrets
import smtplib
from email.message import EmailMessage

from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import ex, q1, qa, tx

ALIAS_RE = re.compile(r"^[\w.\-]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
_DUMMY_HASH = generate_password_hash("sphinx-dummy-password")
log = logging.getLogger("sphinx")


def validate_registration(form):
    """Valida en el servidor. Devuelve (datos_limpios, errores{campo: clave_i18n})."""
    alias = (form.get("alias") or "").strip()
    email = (form.get("email") or "").strip() or None
    password = form.get("password") or ""
    errors = {}
    if not ALIAS_RE.match(alias):
        errors["alias"] = "val.alias"
    elif q1("SELECT 1 FROM users WHERE alias=?", (alias,)):
        errors["alias"] = "val.alias_taken"
    if email and (len(email) > 120 or not EMAIL_RE.match(email)):
        errors["email"] = "val.email"
    elif email and q1("SELECT 1 FROM users WHERE email=?", (email,)):
        errors["email"] = "val.email_taken"
    if len(password) < 8 or len(password) > 200:
        errors["password"] = "val.password"
    elif password.casefold() == alias.casefold():
        errors["password"] = "val.password_alias"
    if form.get("password2", password) != password:
        errors["password2"] = "val.password_match"
    if not form.get("consent"):
        errors["consent"] = "val.consent"
    return {"alias": alias, "email": email, "password": password}, errors


def create_user(alias, email, password, role="student", consent=True):
    cfg = current_app.config
    cur = ex("INSERT INTO users(alias, email, password_hash, role, consent_version, consent_at) "
             "VALUES (?,?,?,?,?, CASE WHEN ? THEN datetime('now') END)",
             (alias, email, generate_password_hash(password), role, cfg["CONSENT_VERSION"] if consent else None, 1 if consent else 0))
    return cur.lastrowid


def authenticate(identifier, password):
    row = q1("SELECT * FROM users WHERE alias=? OR email=?", (identifier.strip(), identifier.strip()))
    ok = check_password_hash(row["password_hash"] if row else _DUMMY_HASH, password)   # tiempo similar si no existe
    return row if (row and ok and row["is_active"]) else None


def has_progress(anon_id):
    if not anon_id:
        return False
    return bool(q1("SELECT 1 FROM attempts WHERE anon_id=? UNION SELECT 1 FROM lesson_progress WHERE anon_id=? LIMIT 1",
                   (anon_id, anon_id)))


def adopt_anonymous(user_id, anon_id):
    """Traslada el progreso de la sesión anónima a la cuenta, sin duplicar. Solo se llama con el anon_id
    de la PROPIA sesión firmada del navegador, y la fila anónima desaparece al terminar (no se puede reutilizar)."""
    if not anon_id or not q1("SELECT 1 FROM anon_sessions WHERE id=?", (anon_id,)):
        return False
    with tx():
        for table, cols in (("lesson_progress", "lesson_id, completed_at"),
                            ("enrollments", "course_id, started_at, last_activity_at, completed_at"),
                            ("xp_events", "kind, ref_key, points, created_at"),
                            ("user_achievements", "achievement_id, earned_at"),
                            ("learner_goals", "subject_id, competency_id, created_at")):
            ex(f"INSERT OR IGNORE INTO {table}(user_id, {cols}) SELECT ?, {cols} FROM {table} WHERE anon_id=?",
               (user_id, anon_id))
        ex("UPDATE attempts SET user_id=?, anon_id=NULL WHERE anon_id=?", (user_id, anon_id))
        ex("DELETE FROM anon_sessions WHERE id=?", (anon_id,))   # elimina por cascada lo que quede
    return True


def export_user(user_id):
    u = q1("SELECT alias, email, role, created_at, consent_version, consent_at FROM users WHERE id=?", (user_id,))
    rows = lambda sql: [dict(r) for r in qa(sql, (user_id,))]
    return {
        "perfil": dict(u),
        "lecciones_completadas": rows("SELECT lesson_id, completed_at FROM lesson_progress WHERE user_id=?"),
        "intentos": rows("SELECT id, assessment_id, kind, status, score_pct, passed, started_at, submitted_at FROM attempts WHERE user_id=?"),
        "respuestas": rows("SELECT r.attempt_id, r.question_id, r.response, r.is_correct, r.points FROM responses r "
                           "JOIN attempts a ON a.id=r.attempt_id WHERE a.user_id=?"),
        "xp": rows("SELECT kind, ref_key, points, created_at FROM xp_events WHERE user_id=?"),
        "insignias": rows("SELECT a.code, ua.earned_at FROM user_achievements ua JOIN achievements a ON a.id=ua.achievement_id WHERE ua.user_id=?"),
        "objetivos": rows("SELECT subject_id, competency_id FROM learner_goals WHERE user_id=?"),
        "certificados": rows("SELECT code, course_id, display_name, score_pct, issued_at FROM certificates WHERE user_id=?"),
    }


def delete_user(user_id):
    ex("DELETE FROM users WHERE id=?", (user_id,))      # las claves foráneas con CASCADE borran todo lo asociado


# --- Recuperación de contraseña ---
def send_mail(to, subject, body):
    cfg = current_app.config
    if not cfg["SMTP_HOST"]:
        if cfg["ENV"] != "production":
            log.warning("SMTP no configurado. Correo para %s: %s\n%s", to, subject, body)   # solo en desarrollo
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = cfg["SMTP_FROM"], to, subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=15) as s:
            s.starttls()
            if cfg["SMTP_USER"]:
                s.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
            s.send_message(msg)
        return True
    except (OSError, smtplib.SMTPException):
        log.exception("Error al enviar correo")
        return False


def _hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_reset_token(user_id):
    token = secrets.token_urlsafe(32)
    ex("UPDATE password_resets SET used_at=datetime('now') WHERE user_id=? AND used_at IS NULL", (user_id,))
    ex("INSERT INTO password_resets(user_id, token_hash, expires_at) VALUES (?,?, datetime('now','+1 hour'))",
       (user_id, _hash_token(token)))
    return token


def reset_password(token, new_password):
    with tx():
        row = q1("SELECT * FROM password_resets WHERE token_hash=? AND used_at IS NULL AND expires_at > datetime('now')",
                 (_hash_token(token),))
        if not row or len(new_password) < 8 or len(new_password) > 200:
            return False
        ex("UPDATE users SET password_hash=?, updated_at=datetime('now') WHERE id=?",
           (generate_password_hash(new_password), row["user_id"]))
        ex("UPDATE password_resets SET used_at=datetime('now') WHERE id=?", (row["id"],))
        return True


def token_valid(token):
    return bool(q1("SELECT 1 FROM password_resets WHERE token_hash=? AND used_at IS NULL AND expires_at > datetime('now')",
                   (_hash_token(token),)))
