"""Textos de interfaz centralizados en locales/<idioma>.json (con idioma alternativo si falta una clave)."""
import json
from pathlib import Path

from flask import current_app, g, request

_CACHE = {}
LOCALES_DIR = Path(__file__).parent / "locales"


def _load(lang):
    if lang not in _CACHE:
        path = LOCALES_DIR / f"{lang}.json"
        _CACHE[lang] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return _CACHE[lang]


def current_locale():
    default = current_app.config["DEFAULT_LOCALE"]
    lang = request.cookies.get("lang", default) if request else default
    return lang if (LOCALES_DIR / f"{lang}.json").exists() else default


def t(key, **kwargs):
    lang = current_locale()
    default = current_app.config["DEFAULT_LOCALE"]
    text = _load(lang).get(key) or _load(default).get(key) or key
    return text.format(**kwargs) if kwargs else text


def init_app(app):
    app.jinja_env.globals["t"] = t
    app.jinja_env.globals["locale"] = current_locale
