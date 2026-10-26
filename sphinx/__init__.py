"""Sphinx: plataforma educativa gratuita. Fábrica de la aplicación Flask."""
from flask import Flask, render_template
from werkzeug.middleware.proxy_fix import ProxyFix

from . import db as database, i18n, richtext, security
from .config import load_config


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.update(load_config(overrides))
    if app.config["TRUST_PROXY"]:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    database.migrate(app.config["DATABASE_PATH"])                    # migraciones versionadas
    database.purge_anonymous(app.config["DATABASE_PATH"], app.config["ANON_RETENTION_DAYS"])
    app.teardown_appcontext(database.close_db)
    i18n.init_app(app)
    richtext.init_app(app)
    security.init_app(app)

    from .blueprints import admin, api, auth, learn, public, student
    for mod in (public, auth, learn, student, api, admin):
        app.register_blueprint(mod.bp)

    @app.context_processor
    def inject():
        from flask import g
        from .services import tutor
        return {"user": g.get("user"), "prefs": g.get("prefs"), "tutor_available": tutor.available()}

    def error(code, key):
        def handler(_e):
            return render_template("error.html", code=code, message_key=key), code
        return handler
    for code, key in ((400, "err.400"), (403, "err.403"), (404, "err.404"), (413, "err.413"), (500, "err.500")):
        app.register_error_handler(code, error(code, key))   # nunca se muestran trazas internas
    return app
