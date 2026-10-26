import os
import tempfile
import unittest

from sphinx import create_app
from sphinx.seed.loader import seed_all
from sphinx.services import accounts


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.app = create_app({"DATABASE_PATH": os.path.join(self.tmp, "t.db"), "TESTING": True, "ENV": "testing",
                               "SECRET_KEY": "test-key", "ANTHROPIC_API_KEY": "", "SMTP_HOST": ""})
        with self.app.app_context():
            seed_all()
        self.c = self.app.test_client()

    def tok(self, client=None):
        client = client or self.c
        with client.session_transaction() as s:
            s.setdefault("_csrf", "tok")
            return s["_csrf"]

    def post(self, url, data=None, client=None, follow=False, **kw):
        client = client or self.c
        data = dict(data or {}, csrf_token=self.tok(client))
        return client.post(url, data=data, follow_redirects=follow, **kw)

    def register(self, alias="ana", password="clave-segura-1", client=None, extra=None):
        data = {"alias": alias, "password": password, "password2": password, "consent": "1", **(extra or {})}
        return self.post("/registro", data, client)

    def make_admin(self, alias="root", password="admin-clave-larga-1"):
        with self.app.app_context():
            accounts.create_user(alias, None, password, role="admin")
        cl = self.app.test_client()
        r = self.post("/ingresar", {"identifier": alias, "password": password}, cl)
        self.assertEqual(r.status_code, 302)
        return cl

    def q(self, sql, args=()):
        with self.app.app_context():
            from sphinx.db import get_db
            return get_db().execute(sql, args).fetchall()

    def answers_for(self, attempt_id, correct=True):
        """Construye el formulario de respuestas leyendo la base (solo para pruebas)."""
        import json
        from sphinx.services import assessments
        with self.app.app_context():
            from sphinx.db import q1
            att = q1("SELECT question_ids FROM attempts WHERE id=?", (attempt_id,))
            qs = assessments.load_questions(json.loads(att["question_ids"]))
        form = {}
        for qid, q in qs.items():
            if q["kind"] in ("mcq", "tf"):
                opt = next(o for o in q["options"] if o["is_correct"] == correct)
                form[f"q_{qid}"] = opt["id"]
            elif q["kind"] == "numeric":
                form[f"q_{qid}"] = q["data"]["answer"] if correct else "9999"
            elif q["kind"] == "short":
                form[f"q_{qid}"] = q["data"]["accepted"][0] if correct else "nada"
            else:
                for i, (l, r) in enumerate(q["data"]["pairs"]):
                    form[f"q_{qid}_{i}"] = r if correct else "x"
        return form

    def start(self, aid, client=None):
        r = self.post(f"/evaluaciones/{aid}/iniciar", client=client)
        self.assertEqual(r.status_code, 302, r.data)
        return int(r.headers["Location"].rstrip("/").split("/")[-1])
