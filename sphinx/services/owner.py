"""El 'dueño' del progreso: una cuenta (user_id) o una sesión anónima (anon_id)."""
import secrets

from flask import g, session

from ..db import ex, q1


class Owner:
    def __init__(self, user_id=None, anon_id=None):
        self.user_id = user_id
        self.anon_id = anon_id

    @property
    def is_user(self):
        return self.user_id is not None

    def where(self, alias=""):
        """Devuelve (fragmento SQL, parámetros) para filtrar filas de este dueño."""
        p = f"{alias}." if alias else ""
        if self.is_user:
            return f"{p}user_id = ?", (self.user_id,)
        return f"{p}anon_id = ?", (self.anon_id,)


def get_owner(create=False):
    """Dueño actual. Con create=True, crea una sesión anónima la primera vez que se guarda progreso."""
    if g.get("user"):
        return Owner(user_id=g.user["id"])
    aid = session.get("anon")
    if aid and q1("SELECT 1 FROM anon_sessions WHERE id=?", (aid,)):
        if create:
            ex("UPDATE anon_sessions SET last_seen_at=datetime('now') "
               "WHERE id=? AND last_seen_at < datetime('now','-1 hour')", (aid,))
        return Owner(anon_id=aid)
    if create:
        aid = secrets.token_urlsafe(24)
        ex("INSERT INTO anon_sessions(id) VALUES (?)", (aid,))
        session["anon"] = aid
        session.permanent = True
        return Owner(anon_id=aid)
    return None
