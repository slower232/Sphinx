from flask import Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for

from ..db import q1, tx
from ..i18n import t
from ..security import clear_failures, login_blocked, record_failure, safe_next
from ..services import accounts

bp = Blueprint("auth", __name__)


def _start_session(user_id):
    session.clear()                      # nueva sesión: evita fijación de sesión
    session["uid"] = user_id
    session.permanent = True


@bp.route("/registro", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("student.dashboard"))
    anon = session.get("anon")
    can_adopt = accounts.has_progress(anon)
    errors, values = {}, {}
    if request.method == "POST":
        values = request.form
        data, errors = accounts.validate_registration(request.form)
        if not errors:
            try:
                with tx():
                    uid = accounts.create_user(data["alias"], data["email"], data["password"])
                    if can_adopt and request.form.get("adopt"):
                        accounts.adopt_anonymous(uid, anon)
            except Exception:            # p. ej. carrera por alias duplicado
                current_app.logger.exception("registro")
                errors = {"alias": "val.alias_taken"}
            else:
                _start_session(uid)
                flash(t("auth.welcome"), "success")
                return redirect(url_for("student.dashboard"))
    return render_template("auth/register.html", errors=errors, values=values, can_adopt=can_adopt)


@bp.route("/ingresar", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("student.dashboard"))
    anon = session.get("anon")
    can_adopt = accounts.has_progress(anon)
    nxt = safe_next(request.args.get("next") or request.form.get("next"))
    error = None
    if request.method == "POST":
        ident = (request.form.get("identifier") or "")[:120]
        pw = request.form.get("password") or ""
        key, ipkey = f"login:{request.remote_addr}:{ident.lower()}", f"ip:{request.remote_addr}"
        if login_blocked(key) or login_blocked(ipkey, limit=30):
            error = "auth.too_many"
        else:
            user = accounts.authenticate(ident, pw)
            if not user:
                record_failure(key)
                record_failure(ipkey)
                error = "auth.bad_credentials"      # mensaje genérico: no revela si el usuario existe
            else:
                clear_failures(key)
                if can_adopt and request.form.get("adopt"):
                    accounts.adopt_anonymous(user["id"], anon)
                _start_session(user["id"])
                return redirect(nxt or url_for("student.dashboard"))
    return render_template("auth/login.html", error=error, can_adopt=can_adopt, next=nxt)


@bp.post("/salir")
def logout():
    session.clear()
    flash(t("auth.bye"), "info")
    return redirect(url_for("public.home"))


@bp.route("/recuperar", methods=["GET", "POST"])
def forgot():
    mail_ok = bool(current_app.config["SMTP_HOST"]) or current_app.config["ENV"] != "production"
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()[:120]
        user = q1("SELECT id FROM users WHERE email=? AND is_active=1", (email,)) if email else None
        if user and mail_ok:
            token = accounts.create_reset_token(user["id"])
            link = f"{current_app.config['PUBLIC_BASE_URL']}/recuperar/{token}"
            accounts.send_mail(email, t("mail.reset_subject"), t("mail.reset_body", link=link))
        flash(t("auth.reset_sent"), "info")       # misma respuesta exista o no el correo
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot.html", mail_ok=mail_ok)


@bp.route("/recuperar/<token>", methods=["GET", "POST"])
def reset(token):
    valid = accounts.token_valid(token)
    error = None
    if request.method == "POST" and valid:
        pw = request.form.get("password") or ""
        if pw != request.form.get("password2"):
            error = "val.password_match"
        elif accounts.reset_password(token, pw):
            flash(t("auth.reset_done"), "success")
            return redirect(url_for("auth.login"))
        else:
            error = "val.password"
    return render_template("auth/reset.html", valid=valid, error=error)
