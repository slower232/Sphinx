"""Acceso a SQLite: conexión por solicitud, transacciones y migraciones versionadas."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import g, current_app

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def connect(path):
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None, timeout=10)   # autocommit; usamos tx() explícito
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode=WAL")
    return conn


def migrate(path):
    """Aplica en orden las migraciones NNN_nombre.sql que aún no se han aplicado."""
    conn = connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations "
                 "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))")
    done = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if f.stem in done:
            continue
        sql = f.read_text(encoding="utf-8")
        conn.executescript(f"BEGIN;\n{sql}\nINSERT INTO schema_migrations(version) VALUES('{f.stem}');\nCOMMIT;")
    conn.close()


def purge_anonymous(path, days):
    """Borra sesiones anónimas inactivas (y, por cascada, su progreso)."""
    conn = connect(path)
    conn.execute("DELETE FROM anon_sessions WHERE last_seen_at < datetime('now', ?)", (f"-{int(days)} days",))
    conn.execute("DELETE FROM login_attempts WHERE created_at < datetime('now','-1 day')")
    conn.close()


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_PATH"])
        g._tx_depth = 0
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@contextmanager
def tx():
    """Transacción atómica (anidable: la más externa confirma o revierte todo)."""
    db = get_db()
    if g.get("_tx_depth", 0) > 0:
        yield db
        return
    db.execute("BEGIN IMMEDIATE")
    g._tx_depth = 1
    try:
        yield db
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    finally:
        g._tx_depth = 0


def q1(sql, args=()):
    return get_db().execute(sql, args).fetchone()


def qa(sql, args=()):
    return get_db().execute(sql, args).fetchall()


def ex(sql, args=()):
    return get_db().execute(sql, args)
