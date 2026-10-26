"""Configuración leída de variables de entorno (y de un archivo .env opcional)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv():
    path = BASE_DIR / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.split("  #")[0].strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)   # el entorno real tiene prioridad


def _int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def load_config(overrides=None):
    _load_dotenv()
    env = os.environ.get("SPHINX_ENV", "development")
    secret = os.environ.get("SECRET_KEY", "")
    if not secret:
        if env == "production":
            raise RuntimeError("Falta SECRET_KEY: es obligatoria en producción (ver .env.example).")
        secret = "dev-only-insecure-key"          # solo para desarrollo local
    cfg = {
        "ENV": env,
        "SECRET_KEY": secret,
        "DATABASE_PATH": os.environ.get("DATABASE_PATH", str(BASE_DIR / "instance" / "sphinx.db")),
        "TRUST_PROXY": os.environ.get("TRUST_PROXY", "0") == "1",
        "ANON_RETENTION_DAYS": _int("ANON_RETENTION_DAYS", 30),
        "PUBLIC_BASE_URL": os.environ.get("PUBLIC_BASE_URL", "http://127.0.0.1:5000").rstrip("/"),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": env == "production",
        "PERMANENT_SESSION_LIFETIME": 60 * 60 * 24 * 14,
        "MAX_CONTENT_LENGTH": 128 * 1024,         # límite de tamaño de las solicitudes
        "DEFAULT_LOCALE": "es",
        "SMTP_HOST": os.environ.get("SMTP_HOST", ""),
        "SMTP_PORT": _int("SMTP_PORT", 587),
        "SMTP_USER": os.environ.get("SMTP_USER", ""),
        "SMTP_PASSWORD": os.environ.get("SMTP_PASSWORD", ""),
        "SMTP_FROM": os.environ.get("SMTP_FROM", "sphinx@example.org"),
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
        "TUTOR_MODEL": os.environ.get("TUTOR_MODEL", "claude-haiku-5-5"),
        "TUTOR_DAILY_LIMIT": _int("TUTOR_DAILY_LIMIT", 20),
        "TUTOR_MINUTE_LIMIT": _int("TUTOR_MINUTE_LIMIT", 4),
        "CONSENT_VERSION": "2026-10",
    }
    if overrides:
        cfg.update(overrides)
    return cfg
