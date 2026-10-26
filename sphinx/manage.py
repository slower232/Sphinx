#!/usr/bin/env python3
"""Comandos de administración: python manage.py <comando>"""
import argparse
import getpass
import os
import sys

from sphinx import create_app
from sphinx.db import ex, q1
from sphinx.seed.loader import seed_all
from sphinx.services import accounts


def main():
    p = argparse.ArgumentParser(description="Administración de Sphinx")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db", help="Aplica las migraciones (también se aplican al iniciar la app)")
    s = sub.add_parser("seed", help="Carga materias y cursos de DEMOSTRACIÓN")
    s.add_argument("--force", action="store_true", help="Intenta cargar de nuevo aunque ya haya contenido (no duplica materias existentes)")
    a = sub.add_parser("create-admin", help="Crea una cuenta administradora (único camino para crearla)")
    a.add_argument("--alias", required=True)
    a.add_argument("--email", default=None)
    r = sub.add_parser("reset-password", help="Cambia la contraseña de una cuenta")
    r.add_argument("--alias", required=True)
    sub.add_parser("purge-anon", help="Borra sesiones de invitados inactivas")
    d = sub.add_parser("reset-db", help="⚠ BORRA toda la base de datos local")
    d.add_argument("--yes", action="store_true", help="Confirma que quieres borrar todo")
    args = p.parse_args()

    if args.cmd == "reset-db":
        from sphinx.config import load_config
        path = load_config()["DATABASE_PATH"]
        if not args.yes:
            sys.exit("Esto BORRA todos los datos de %s. Repite con --yes para confirmar." % path)
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(path + suffix):
                os.remove(path + suffix)
        print("Base de datos eliminada. Se recreará al iniciar la app o con: python manage.py seed")
        return

    app = create_app()
    with app.app_context():
        if args.cmd == "init-db":
            print("Migraciones aplicadas.")
        elif args.cmd == "seed":
            print("Contenido de demostración cargado." if seed_all(args.force) else "Ya existe contenido. Usa --force para reintentar.")
        elif args.cmd == "create-admin":
            pw = getpass.getpass("Contraseña (mínimo 12 caracteres): ")
            if len(pw) < 12 or pw != getpass.getpass("Repite la contraseña: "):
                sys.exit("Las contraseñas no coinciden o son demasiado cortas.")
            if q1("SELECT 1 FROM users WHERE alias=?", (args.alias,)):
                sys.exit("Ese alias ya existe.")
            uid = accounts.create_user(args.alias, args.email, pw, role="admin")
            print(f"Administrador creado (id {uid}).")
        elif args.cmd == "reset-password":
            from werkzeug.security import generate_password_hash
            pw = getpass.getpass("Nueva contraseña (mínimo 8 caracteres): ")
            if len(pw) < 8:
                sys.exit("Demasiado corta.")
            cur = ex("UPDATE users SET password_hash=? WHERE alias=?", (generate_password_hash(pw), args.alias))
            print("Contraseña actualizada." if cur.rowcount else "No existe ese alias.")
        elif args.cmd == "purge-anon":
            from sphinx.db import purge_anonymous
            purge_anonymous(app.config["DATABASE_PATH"], app.config["ANON_RETENTION_DAYS"])
            print("Listo.")


if __name__ == "__main__":
    main()
