"""XP, niveles, insignias y rachas. Todo se calcula en el servidor a partir de acciones verificadas."""
from datetime import date, timedelta

from ..db import ex, q1, qa

DEFAULTS = {"xp_lesson": 10, "xp_formative": 20, "xp_diagnostic": 15, "xp_course": 100,
            "xp_review": 5, "formative_pass_pct": 60}


def setting(key):
    row = q1("SELECT value FROM settings WHERE key=?", (key,))
    try:
        return int(row["value"]) if row else DEFAULTS[key]
    except ValueError:
        return DEFAULTS[key]


def award(owner, kind, ref_key, points):
    """Concede XP una sola vez por (tipo, referencia). Devuelve los puntos realmente concedidos."""
    cur = ex("INSERT OR IGNORE INTO xp_events(user_id, anon_id, kind, ref_key, points) VALUES (?,?,?,?,?)",
             (owner.user_id, owner.anon_id, kind, ref_key, points))
    return points if cur.rowcount == 1 else 0


def total_xp(owner):
    sql, p = owner.where()
    return q1(f"SELECT COALESCE(SUM(points),0) AS xp FROM xp_events WHERE {sql}", p)["xp"]


def level_info(xp):
    """Nivel n empieza en 40*(n-1)^2 XP (1: 0, 2: 40, 3: 160, 4: 360...)."""
    level = int((xp / 40) ** 0.5) + 1
    start, nxt = 40 * (level - 1) ** 2, 40 * level ** 2
    return {"level": level, "xp": xp, "into": xp - start, "span": nxt - start, "next_at": nxt}


def streak_days(owner):
    """Días consecutivos con actividad verificada (opcional; solo informativo)."""
    sql, p = owner.where()
    days = {date.fromisoformat(r["d"]) for r in qa(f"SELECT DISTINCT date(created_at) AS d FROM xp_events WHERE {sql}", p)}
    day, n = date.today(), 0
    if day not in days:
        day -= timedelta(days=1)
    while day in days:
        n += 1
        day -= timedelta(days=1)
    return n


def _count(sql, owner):
    cond, p = owner.where()
    return q1(sql.format(cond=cond), p)["c"]


CHECKS = {
    "primer_paso": lambda o, att: _count("SELECT COUNT(*) c FROM lesson_progress WHERE {cond}", o) >= 1,
    "explorador": lambda o, att: _count("SELECT COUNT(*) c FROM attempts WHERE kind='diagnostic' AND status='submitted' AND {cond}", o) >= 1,
    "constancia": lambda o, att: _count("SELECT COUNT(*) c FROM lesson_progress WHERE {cond}", o) >= 5,
    "precision": lambda o, att: bool(att and att["kind"] in ("formative", "final") and (att["score_pct"] or 0) >= 90),
    "graduado": lambda o, att: _count("SELECT COUNT(*) c FROM enrollments WHERE completed_at IS NOT NULL AND {cond}", o) >= 1,
}


def check_achievements(owner, att=None):
    """Concede las insignias cuyas condiciones se cumplen. Devuelve los nombres de las nuevas."""
    new = []
    for a in qa("SELECT * FROM achievements"):
        check = CHECKS.get(a["code"])
        if check and check(owner, att):
            cur = ex("INSERT OR IGNORE INTO user_achievements(user_id, anon_id, achievement_id) VALUES (?,?,?)",
                     (owner.user_id, owner.anon_id, a["id"]))
            if cur.rowcount == 1:
                new.append(a["name"])
    return new
