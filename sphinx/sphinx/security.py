"""Sesiones, CSRF, permisos, límites de intentos, preferencias y cabeceras de seguridad."""
import hmac
import secrets
from functools import wraps

from flask import abort, current_app, g, redirect, request, session, url_for

from .db import ex, q1

PREF_DEFAULTS = {"theme": "light", "size": "normal", "motion": "auto", "streak": "on"}
PREF_ALLOWED = {"theme": {"auto", "light", "dark"}, "size": {"normal", "large"},
                "motion": {"auto", "reduce"}, "streak": {"on", "off"}}


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


def check_csrf():
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""
        if not hmac.compare_digest(sent, session.get("_csrf", "")) or not sent:
            abort(400)


def load_user():
    g.user = None
    uid = session.get("uid")
    if uid:
        row = q1("SELECT id, alias, email, role, is_active FROM users WHERE id=?", (uid,))
        if row and row["is_active"]:
            g.user = row
        else:                                   # cuenta eliminada o con acceso revocado
            session.clear()


def load_prefs():
    prefs = dict(PREF_DEFAULTS)
    for part in request.cookies.get("prefs", "").split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            if k in PREF_ALLOWED and v in PREF_ALLOWED[k]:
                prefs[k] = v
    g.prefs = prefs


def safe_next(target):
    """Solo permite redirecciones internas (evita open redirect)."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return None


def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if not g.user:
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return view(*a, **kw)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if not g.user:
            return redirect(url_for("auth.login", next=request.path))
        if g.user["role"] != "admin":           # la autorización SIEMPRE se decide en el servidor
            abort(403)
        return view(*a, **kw)
    return wrapped


# --- Límite de intentos de acceso (persistente en la base de datos) ---
def login_blocked(key, limit=5, minutes=15):
    n = q1("SELECT COUNT(*) AS c FROM login_attempts WHERE key=? AND created_at > datetime('now', ?)",
           (key, f"-{minutes} minutes"))["c"]
    return n >= limit


def record_failure(key):
    ex("INSERT INTO login_attempts(key) VALUES (?)", (key,))


def clear_failures(key):
    ex("DELETE FROM login_attempts WHERE key=?", (key,))


def add_headers(resp):
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'")
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if current_app.config["ENV"] == "production":
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.endpoint != "static" and (g.get("user") or session.get("anon")):
        resp.headers["Cache-Control"] = "no-store"
    return resp


def init_app(app):
    app.before_request(load_user)
    app.before_request(load_prefs)
    app.before_request(check_csrf)
    app.after_request(add_headers)
    app.jinja_env.globals["csrf_token"] = csrf_token
