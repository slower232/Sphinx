import json
import unittest
from unittest import mock

from sphinx.services import grading
from tests.base import Base


class GradingTests(unittest.TestCase):
    def test_numeric_fraction_and_decimal(self):
        q = {"kind": "numeric", "data": {"answer": "3/4", "tolerance": "0"}, "options": []}
        self.assertTrue(grading.grade_question(q, "3/4")[1])
        self.assertTrue(grading.grade_question(q, "0,75")[1])
        self.assertTrue(grading.grade_question(q, "6/8")[1])
        self.assertFalse(grading.grade_question(q, "1/2")[1])
        self.assertFalse(grading.grade_question(q, "1e999999999")[1])     # sin explosión de memoria

    def test_short_ignores_case_and_accents(self):
        q = {"kind": "short", "data": {"accepted": ["fusión"]}, "options": []}
        self.assertTrue(grading.grade_question(q, "  FUSION ")[1])
        self.assertFalse(grading.grade_question(q, "")[1])

    def test_match_partial(self):
        q = {"kind": "match", "data": {"pairs": [["a", "1"], ["b", "2"]]}, "options": []}
        self.assertEqual(grading.grade_question(q, ["1", "x"]), (0.5, False))
        self.assertEqual(grading.grade_question(q, ["1", "2"]), (1.0, True))


class CoursesAndContent(Base):
    def test_published_courses_shown_and_filters(self):
        r = self.c.get("/cursos")
        self.assertIn("Fracciones desde cero".encode(), r.data)
        self.assertIn("El agua y sus cambios".encode(), r.data)
        self.assertNotIn(b"Fracciones desde cero", self.c.get("/cursos?materia=espanol").data)
        self.assertIn("Leer con propósito".encode(), self.c.get("/cursos?q=PROPOSITO").data)   # sin acentos
        self.assertIn("No encontramos cursos".encode(), self.c.get("/cursos?q=zzzz").data)

    def test_draft_not_public_and_admin_can_preview(self):
        adm = self.make_admin()
        self.post("/admin/cursos/1/estado", {"action": "unpublish"}, adm)
        self.assertEqual(self.c.get("/cursos/fracciones-desde-cero").status_code, 404)
        self.assertNotIn(b"Fracciones desde cero", self.c.get("/cursos").data)
        self.assertEqual(adm.get("/cursos/fracciones-desde-cero").status_code, 200)

    def test_lessons_in_order(self):
        r = self.c.get("/cursos/fracciones-desde-cero").data.decode()
        pos = [r.index(f">{t}</a>") for t in ("¿Qué es una fracción?", "Fracciones equivalentes y simplificación", "Sumar y restar fracciones")]
        self.assertEqual(pos, sorted(pos))

    def test_error_pages_do_not_leak(self):
        r = self.c.get("/no-existe")
        self.assertEqual(r.status_code, 404)
        self.assertNotIn(b"Traceback", r.data)


class AssessmentTests(Base):
    def test_guest_flow_grading_and_no_answers_leak(self):
        aid = self.q("SELECT id FROM assessments WHERE kind='formative' ORDER BY id LIMIT 1")[0]["id"]
        att = self.start(aid)
        page = self.c.get(f"/intentos/{att}").data.decode()
        self.assertNotIn("is_correct", page)
        r = self.post(f"/intentos/{att}/enviar", self.answers_for(att, True), follow=True)
        self.assertIn("100%".encode(), r.data)
        row = self.q("SELECT passed, score_pct FROM attempts WHERE id=?", (att,))[0]
        self.assertEqual((row["passed"], row["score_pct"]), (1, 100.0))
        # lección completada y XP concedido una vez
        self.assertEqual(len(self.q("SELECT 1 FROM lesson_progress")), 1)
        xp = self.q("SELECT SUM(points) s FROM xp_events")[0]["s"]
        self.assertEqual(xp, 30)

    def test_client_cannot_inject_score(self):
        aid = self.q("SELECT id FROM assessments WHERE kind='formative' ORDER BY id LIMIT 1")[0]["id"]
        att = self.start(aid)
        form = self.answers_for(att, False)
        form.update({"score_pct": "100", "passed": "1", "points": "999"})
        self.post(f"/intentos/{att}/enviar", form)
        row = self.q("SELECT passed, score_pct FROM attempts WHERE id=?", (att,))[0]
        self.assertEqual(row["passed"], 0)
        self.assertEqual(row["score_pct"], 0.0)
        self.assertEqual(len(self.q("SELECT 1 FROM lesson_progress")), 0)

    def test_double_submit_is_idempotent_and_xp_not_farmed(self):
        aid = self.q("SELECT id FROM assessments WHERE kind='formative' ORDER BY id LIMIT 1")[0]["id"]
        att = self.start(aid)
        form = self.answers_for(att, True)
        self.post(f"/intentos/{att}/enviar", form)
        self.post(f"/intentos/{att}/enviar", form)
        self.assertEqual(len(self.q("SELECT 1 FROM responses WHERE attempt_id=?", (att,))), 3)
        att2 = self.start(aid)                              # repetir la actividad
        self.post(f"/intentos/{att2}/enviar", self.answers_for(att2, True))
        self.assertEqual(self.q("SELECT SUM(points) s FROM xp_events")[0]["s"], 30)

    def test_other_user_cannot_see_attempt(self):
        aid = self.q("SELECT id FROM assessments WHERE kind='formative' ORDER BY id LIMIT 1")[0]["id"]
        att = self.start(aid)
        other = self.app.test_client()
        self.assertEqual(other.get(f"/intentos/{att}").status_code, 404)
        self.assertEqual(self.post(f"/intentos/{att}/enviar", {}, other).status_code, 404)

    def test_final_attempt_limits_and_pass_threshold(self):
        adm = self.make_admin()
        self.post("/admin/cursos/1", {"title": "Fracciones desde cero", "subject_id": 1, "description": "d", "objectives": "o",
                                       "level": "basico", "difficulty": 1, "est_minutes": 30, "pass_pct": 70, "max_attempts": 1,
                                       "competencies": [1, 2, 3]}, adm)
        final = self.q("SELECT id FROM assessments WHERE kind='final' AND course_id=1")[0]["id"]
        att = self.start(final)
        self.post(f"/intentos/{att}/enviar", self.answers_for(att, False))
        self.assertEqual(self.q("SELECT passed FROM attempts WHERE id=?", (att,))[0]["passed"], 0)
        r = self.post(f"/evaluaciones/{final}/iniciar")      # sin intentos restantes
        self.assertEqual(len(self.q("SELECT 1 FROM attempts WHERE kind='final'")), 1)

    def test_diagnostic_and_recommendations_react_to_results(self):
        diag = self.q("SELECT id FROM assessments WHERE kind='diagnostic' AND subject_id=1")[0]["id"]
        att = self.start(diag)
        r = self.post(f"/intentos/{att}/enviar", self.answers_for(att, False), follow=True)
        self.assertIn("Por reforzar".encode(), r.data)
        self.assertIn("Repasa:".encode(), r.data)
        self.assertEqual(self.q("SELECT kind FROM attempts")[0]["kind"], "diagnostic")
        att2 = self.start(self.q("SELECT id FROM assessments WHERE kind='diagnostic' AND subject_id=2")[0]["id"])
        r = self.post(f"/intentos/{att2}/enviar", self.answers_for(att2, True), follow=True)
        self.assertIn("Dominada".encode(), r.data)

    def test_review_challenge_uses_wrong_answers(self):
        diag = self.q("SELECT id FROM assessments WHERE kind='diagnostic' AND subject_id=1")[0]["id"]
        att = self.start(diag)
        self.post(f"/intentos/{att}/enviar", self.answers_for(att, False))
        r = self.post("/repaso")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/intentos/", r.headers["Location"])


class AccountsAndPermissions(Base):
    def test_register_login_logout_and_session(self):
        r = self.register()
        self.assertEqual(r.status_code, 302)
        self.assertIn(b"ana", self.c.get("/panel").data)
        self.post("/salir")
        self.assertEqual(self.c.get("/panel/cuenta").status_code, 302)
        r = self.post("/ingresar", {"identifier": "ana", "password": "mala"})
        self.assertIn("incorrectos".encode(), r.data)
        r = self.post("/ingresar", {"identifier": "ana", "password": "clave-segura-1"})
        self.assertEqual(r.status_code, 302)
        row = self.q("SELECT password_hash FROM users")[0]["password_hash"]
        self.assertNotIn("clave-segura", row)

    def test_registration_validation(self):
        r = self.post("/registro", {"alias": "a", "password": "123", "password2": "x"})
        for msg in ("alias debe tener", "entre 8 y 200", "no coinciden", "aviso de privacidad"):
            self.assertIn(msg.encode(), r.data)
        self.assertEqual(self.q("SELECT COUNT(*) c FROM users")[0]["c"], 0)

    def test_csrf_required(self):
        self.assertEqual(self.c.post("/registro", data={"alias": "zoe"}).status_code, 400)

    def test_role_cannot_be_set_from_browser(self):
        self.register("mal", extra={"role": "admin", "is_admin": "1"})
        self.assertEqual(self.q("SELECT role FROM users WHERE alias='mal'")[0]["role"], "student")
        self.assertEqual(self.c.get("/admin/").status_code, 403)
        self.assertEqual(self.post("/admin/cursos/1/estado", {"action": "archive"}).status_code, 403)
        self.assertEqual(self.app.test_client().get("/admin/").status_code, 302)   # anónimo -> login

    def test_login_rate_limit(self):
        self.register("ana")
        self.post("/salir")
        for _ in range(5):
            self.post("/ingresar", {"identifier": "ana", "password": "mal"})
        r = self.post("/ingresar", {"identifier": "ana", "password": "clave-segura-1"})
        self.assertIn("Demasiados intentos".encode(), r.data)

    def test_student_cannot_read_another_students_data(self):
        a, b = self.app.test_client(), self.app.test_client()
        self.register("ana", client=a)
        self.register("beto", client=b)
        aid = self.q("SELECT id FROM assessments WHERE kind='formative' ORDER BY id LIMIT 1")[0]["id"]
        att = self.start(aid, a)
        self.assertEqual(b.get(f"/intentos/{att}").status_code, 404)
        self.assertEqual(self.post("/panel/exportar", client=b).status_code, 405)
        exp = json.loads(b.get("/panel/exportar").data)
        self.assertEqual(exp["intentos"], [])

    def test_progress_persists_for_accounts_and_adoption_without_duplicates(self):
        aid = self.q("SELECT id FROM assessments WHERE kind='formative' ORDER BY id LIMIT 1")[0]["id"]
        att = self.start(aid)
        self.post(f"/intentos/{att}/enviar", self.answers_for(att, True))
        self.register("ana", extra={"adopt": "1"})
        self.assertEqual(self.q("SELECT COUNT(*) c FROM lesson_progress WHERE user_id IS NOT NULL")[0]["c"], 1)
        self.assertEqual(self.q("SELECT COUNT(*) c FROM attempts WHERE user_id IS NOT NULL")[0]["c"], 1)
        self.assertEqual(self.q("SELECT COUNT(*) c FROM anon_sessions")[0]["c"], 0)
        # otro dispositivo
        d2 = self.app.test_client()
        self.post("/ingresar", {"identifier": "ana", "password": "clave-segura-1"}, d2)
        self.assertEqual(self.q("SELECT SUM(points) s FROM xp_events WHERE user_id IS NOT NULL")[0]["s"], 30)
        self.assertIn(b"30 XP", d2.get("/panel").data)

    def test_guest_progress_is_not_adopted_without_consent(self):
        aid = self.q("SELECT id FROM assessments WHERE kind='formative' ORDER BY id LIMIT 1")[0]["id"]
        self.start(aid)
        self.register("ana")
        self.assertEqual(self.q("SELECT COUNT(*) c FROM attempts WHERE user_id IS NOT NULL")[0]["c"], 0)

    def test_deactivated_account_loses_access(self):
        adm = self.make_admin()
        self.register("ana")
        uid = self.q("SELECT id FROM users WHERE alias='ana'")[0]["id"]
        self.post(f"/admin/usuarios/{uid}/acceso", {"action": "revoke"}, adm)
        self.assertEqual(self.c.get("/panel/cuenta").status_code, 302)

    def test_delete_account_removes_data(self):
        self.register("ana")
        r = self.post("/panel/eliminar", {"password": "clave-segura-1"})
        self.assertEqual(self.q("SELECT COUNT(*) c FROM users")[0]["c"], 0)

    def test_password_reset_flow(self):
        from sphinx.services import accounts
        self.register("ana", extra={"email": "ana@example.org"})
        self.post("/salir")
        with self.app.app_context():
            uid = accounts.authenticate("ana", "clave-segura-1")["id"]
            token = accounts.create_reset_token(uid)
        self.assertEqual(self.c.get(f"/recuperar/{token}").status_code, 200)
        r = self.post(f"/recuperar/{token}", {"password": "nueva-clave-9", "password2": "nueva-clave-9"})
        self.assertEqual(r.status_code, 302)
        self.assertIn(b"no es v", self.c.get(f"/recuperar/{token}").data)        # un solo uso
        self.assertEqual(self.post("/ingresar", {"identifier": "ana", "password": "nueva-clave-9"}).status_code, 302)

    def test_open_redirect_blocked(self):
        self.register("ana")
        self.post("/salir")
        r = self.post("/ingresar?next=//evil.com", {"identifier": "ana", "password": "clave-segura-1", "next": "//evil.com"})
        self.assertNotIn("evil.com", r.headers["Location"])


class CertificatesAndGamification(Base):
    def _complete_course(self, client):
        lessons = self.q("SELECT s.id FROM assessments s WHERE kind='formative' AND course_id=1 ORDER BY id")
        for a in lessons:
            att = self.start(a["id"], client)
            self.post(f"/intentos/{att}/enviar", self.answers_for(att, True), client)

    def test_certificate_requires_requirements(self):
        self.register("ana")
        r = self.post("/cursos/fracciones-desde-cero/certificado", follow=True)
        self.assertIn("Falta completar".encode(), r.data)
        self.assertEqual(self.q("SELECT COUNT(*) c FROM certificates")[0]["c"], 0)
        self._complete_course(self.c)
        self.post("/cursos/fracciones-desde-cero/certificado")            # lecciones sin final
        self.assertEqual(self.q("SELECT COUNT(*) c FROM certificates")[0]["c"], 0)

    def test_certificate_issue_verify_pdf_and_badges(self):
        self.register("ana")
        self._complete_course(self.c)
        final = self.q("SELECT id FROM assessments WHERE kind='final' AND course_id=1")[0]["id"]
        att = self.start(final)
        self.post(f"/intentos/{att}/enviar", self.answers_for(att, True))
        r = self.post("/cursos/fracciones-desde-cero/certificado", {"display_name": "Ana P."})
        self.assertEqual(r.status_code, 302)
        code = self.q("SELECT code FROM certificates")[0]["code"]
        self.assertTrue(code.startswith("SPX-"))
        v = self.app.test_client().get(f"/verificar/{code}").data.decode()
        self.assertIn("Certificado válido", v)
        self.assertIn("Ana P.", v)
        self.assertNotIn("ana@", v)
        self.assertNotIn("100", v)                                         # no expone la calificación
        self.assertIn("No encontramos un certificado", self.app.test_client().get("/verificar/SPX-0000-0000-0000").data.decode())
        pdf = self.c.get(f"/certificados/{code}.pdf")
        self.assertEqual(pdf.mimetype, "application/pdf")
        self.assertTrue(pdf.data.startswith(b"%PDF"))
        self.assertEqual(self.app.test_client().get(f"/certificados/{code}.pdf").status_code, 302)   # requiere sesión
        badges = {r["code"] for r in self.q("SELECT a.code FROM user_achievements ua JOIN achievements a ON a.id=ua.achievement_id")}
        self.assertTrue({"primer_paso", "graduado", "precision"} <= badges)
        self.assertIsNotNone(self.q("SELECT completed_at FROM enrollments WHERE course_id=1")[0]["completed_at"])

    def test_cannot_download_someone_elses_certificate(self):
        self.register("ana")
        self._complete_course(self.c)
        final = self.q("SELECT id FROM assessments WHERE kind='final' AND course_id=1")[0]["id"]
        att = self.start(final)
        self.post(f"/intentos/{att}/enviar", self.answers_for(att, True))
        self.post("/cursos/fracciones-desde-cero/certificado")
        code = self.q("SELECT code FROM certificates")[0]["code"]
        other = self.app.test_client()
        self.register("beto", client=other)
        self.assertEqual(other.get(f"/certificados/{code}.pdf").status_code, 404)

    def test_manual_completion_only_without_quiz(self):
        r = self.post("/cursos/fracciones-desde-cero/lecciones/1/completar", follow=True)
        self.assertIn("debes aprobar".encode(), r.data)
        self.assertEqual(self.q("SELECT COUNT(*) c FROM lesson_progress")[0]["c"], 0)


class AdminTests(Base):
    def test_admin_creates_edits_publishes_course_and_persists(self):
        adm = self.make_admin()
        data = {"title": "Curso nuevo", "subject_id": 1, "description": "Desc", "objectives": "Aprender algo",
                "level": "basico", "difficulty": 1, "est_minutes": 20, "pass_pct": 60, "max_attempts": 0, "competencies": [1]}
        r = self.post("/admin/cursos/nuevo", data, adm)
        self.assertEqual(r.status_code, 302)
        cid = self.q("SELECT id FROM courses WHERE slug='curso-nuevo'")[0]["id"]
        # borrador: no publicable y no público
        self.post(f"/admin/cursos/{cid}/estado", {"action": "publish"}, adm)
        self.assertEqual(self.q("SELECT status FROM courses WHERE id=?", (cid,))[0]["status"], "draft")
        self.assertNotIn(b"Curso nuevo", self.c.get("/cursos").data)
        self.post(f"/admin/cursos/{cid}/unidades", {"title": "U1"}, adm)
        uid = self.q("SELECT id FROM units WHERE course_id=?", (cid,))[0]["id"]
        r = self.post(f"/admin/unidades/{uid}/lecciones", {"title": "L1"}, adm)
        lid = self.q("SELECT id FROM lessons WHERE unit_id=?", (uid,))[0]["id"]
        self.post(f"/admin/lecciones/{lid}/bloques", {"type": "text", "title": "T", "body": "Hola **mundo** <script>alert(1)</script>"}, adm)
        q = {"kind": "mcq", "prompt": "¿2+2?", "explanation": "cuatro", "difficulty": 1, "points": 1, "competency_id": 1,
             "opt0": "3", "opt1": "4", "correct": "1"}
        self.post("/admin/preguntas/nueva", q, adm)
        qid = self.q("SELECT id FROM questions ORDER BY id DESC LIMIT 1")[0]["id"]
        final = self.q("SELECT id FROM assessments WHERE kind='final' AND course_id=?", (cid,))[0]["id"]
        self.post(f"/admin/evaluaciones/{final}", {"q": [qid]}, adm)
        self.post(f"/admin/cursos/{cid}/estado", {"action": "publish"}, adm)
        self.assertEqual(self.q("SELECT status FROM courses WHERE id=?", (cid,))[0]["status"], "published")
        page = self.c.get(f"/cursos/curso-nuevo/lecciones/{lid}").data.decode()
        self.assertIn("<strong>mundo</strong>", page)
        self.assertNotIn("<script>alert", page)                           # HTML escapado
        self.assertIn("&lt;script&gt;", page)
        self.assertGreaterEqual(self.q("SELECT COUNT(*) c FROM audit_log")[0]["c"], 5)

    def test_validation_errors_shown(self):
        adm = self.make_admin()
        r = self.post("/admin/cursos/nuevo", {"title": "", "subject_id": 1}, adm)
        self.assertIn("Escribe un título".encode(), r.data)
        r = self.post("/admin/preguntas/nueva", {"kind": "mcq", "prompt": "x", "competency_id": 1, "difficulty": 1,
                                                  "opt0": "solo una", "correct": "0"}, adm)
        self.assertIn("al menos 2 opciones".encode(), r.data)

    def test_question_with_responses_cannot_be_deleted(self):
        adm = self.make_admin()
        aid = self.q("SELECT id FROM assessments WHERE kind='formative' ORDER BY id LIMIT 1")[0]["id"]
        att = self.start(aid)
        self.post(f"/intentos/{att}/enviar", self.answers_for(att, True))
        qid = self.q("SELECT question_id FROM responses LIMIT 1")[0]["question_id"]
        self.post(f"/admin/preguntas/{qid}/eliminar", client=adm)
        self.assertEqual(len(self.q("SELECT 1 FROM questions WHERE id=?", (qid,))), 1)

    def test_stats_are_computed_from_data(self):
        adm = self.make_admin()
        aid = self.q("SELECT id FROM assessments WHERE kind='formative' ORDER BY id LIMIT 1")[0]["id"]
        att = self.start(aid)
        self.post(f"/intentos/{att}/enviar", self.answers_for(att, True))
        r = adm.get("/admin/").data.decode()
        self.assertIn("Evaluaciones enviadas", r)
        self.assertNotIn("ana", r)


class TutorTests(Base):
    def test_unavailable_without_key(self):
        r = self.c.post("/api/tutor", json={"message": "hola"}, headers={"X-CSRF-Token": self.tok()})
        self.assertEqual(r.status_code, 503)
        self.assertIn("no está disponible".encode(), self.c.get("/cursos/fracciones-desde-cero/lecciones/1").data)

    def test_with_key_mocked_provider_limits_and_errors(self):
        import urllib.error
        self.app.config.update(ANTHROPIC_API_KEY="test", TUTOR_MINUTE_LIMIT=2)
        h = {"X-CSRF-Token": self.tok()}
        fake = {"content": [{"type": "text", "text": "Piensa: ¿qué es el denominador?"}]}
        with mock.patch("sphinx.services.tutor._post", return_value=fake) as m:
            r = self.c.post("/api/tutor", json={"message": "ayuda con fracciones", "lesson_id": 1}, headers=h)
            self.assertEqual(r.get_json()["text"], "Piensa: ¿qué es el denominador?")
            sent = m.call_args[0][0]
            self.assertIn("Fracciones desde cero", sent["system"])
            self.assertEqual(sent["messages"][-1]["role"], "user")
            self.c.post("/api/tutor", json={"message": "otra"}, headers=h)
            r = self.c.post("/api/tutor", json={"message": "tercera"}, headers=h)
            self.assertEqual(r.status_code, 429)
        self.app.config.update(TUTOR_MINUTE_LIMIT=99)
        with mock.patch("sphinx.services.tutor._post", side_effect=urllib.error.HTTPError("u", 429, "x", {}, None)):
            r = self.c.post("/api/tutor", json={"message": "hola"}, headers=h)
            self.assertIn("límite", r.get_json()["error"])
        with mock.patch("sphinx.services.tutor._post", side_effect=TimeoutError()):
            r = self.c.post("/api/tutor", json={"message": "hola"}, headers=h)
            self.assertIn("tardó", r.get_json()["error"])
        r = self.c.post("/api/tutor", json={"message": "x" * 700}, headers=h)
        self.assertEqual(r.status_code, 502)
        self.assertEqual(self.q("SELECT COUNT(*) c FROM tutor_usage")[0]["c"], 4)     # solo marcas de tiempo
        self.assertEqual(self.q("SELECT COUNT(*) c FROM pragma_table_info('tutor_usage') WHERE name LIKE '%message%'")[0]["c"], 0)

    def test_tutor_requires_csrf(self):
        self.app.config.update(ANTHROPIC_API_KEY="test")
        self.assertEqual(self.c.post("/api/tutor", json={"message": "hola"}).status_code, 400)


class UiTests(Base):
    def test_pages_render_and_headers(self):
        for url in ("/", "/cursos", "/objetivos", "/diagnostico/matematicas", "/panel", "/preferencias", "/privacidad",
                    "/accesibilidad", "/contacto", "/verificar", "/registro", "/ingresar", "/recuperar",
                    "/cursos/el-agua-y-sus-cambios", "/cursos/leer-con-proposito/lecciones/7", "/salud"):
            r = self.c.get(url)
            self.assertEqual(r.status_code, 200, url)
        r = self.c.get("/")
        self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])
        self.assertNotIn(b"<script>", r.data)                              # sin scripts en línea (CSP)
        self.assertIn(b'<label for="q">', self.c.get("/cursos").data)

    def test_goals_saved_and_used_for_recommendations(self):
        self.post("/objetivos", {"subject": "2"})
        self.assertEqual(self.q("SELECT subject_id FROM learner_goals")[0]["subject_id"], 2)
        r = self.c.get("/panel").data.decode()
        self.assertIn("Elegiste aprender Ciencias naturales", r)

    def test_preferences_cookie_applies_and_ignores_garbage(self):
        r = self.post("/preferencias", {"theme": "dark", "size": "large", "motion": "reduce", "streak": "off"})
        self.assertIn("prefs=", r.headers["Set-Cookie"])
        page = self.c.get("/").data.decode()
        self.assertIn('data-theme="dark"', page)
        self.assertIn("size-large", page)
        self.c.set_cookie("prefs", "theme=<script>")
        self.assertIn('data-theme="light"', self.c.get("/").data.decode())

    def test_all_i18n_keys_exist(self):
        import glob, re
        d = json.load(open("sphinx/locales/es.json", encoding="utf-8"))
        miss = set()
        for f in glob.glob("sphinx/templates/**/*.html", recursive=True) + glob.glob("sphinx/blueprints/*.py"):
            for m in re.finditer(r"\bt\(\s*['\"]([a-z0-9_.]+)['\"]\s*[,)]", open(f, encoding="utf-8").read()):
                if m.group(1) not in d:
                    miss.add(m.group(1))
        self.assertEqual(miss, set())


if __name__ == "__main__":
    unittest.main()


class CspTests(Base):
    def test_templates_have_no_inline_styles_or_scripts(self):
        import glob
        for f in glob.glob("sphinx/templates/**/*.html", recursive=True):
            with open(f, encoding="utf-8") as fh:
                s = fh.read()
            self.assertNotIn(' style="', s, f)         # la CSP los bloquearía
            self.assertNotIn("<script>", s, f)


class SubjectColorTests(Base):
    def test_each_subject_has_its_color(self):
        colors = {r["slug"]: r["color"] for r in self.q("SELECT slug, color FROM subjects")}
        self.assertEqual(colors, {"matematicas": "red", "espanol": "blue", "ciencias-naturales": "green"})
        page = self.c.get("/cursos").data.decode()
        for slug, color in (("fracciones-desde-cero", "red"), ("leer-con-proposito", "blue"), ("el-agua-y-sus-cambios", "green")):
            card = page[: page.index(f"/cursos/{slug}")]
            self.assertIn(f"c-{color}", card[card.rindex("<article"):])
        self.assertIn('class="c-red"', self.c.get("/cursos/fracciones-desde-cero").data.decode())
        self.assertIn('class="c-blue"', self.c.get("/diagnostico/espanol").data.decode())

    def test_migration_colors_existing_database(self):
        import sqlite3
        from sphinx import db
        path = self.tmp + "/old.db"
        conn = sqlite3.connect(path)
        conn.executescript(open("sphinx/migrations/001_initial.sql", encoding="utf-8").read())
        conn.execute("CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))")
        conn.execute("INSERT INTO schema_migrations(version) VALUES ('001_initial')")
        conn.execute("INSERT INTO subjects(slug, name) VALUES ('matematicas','M'), ('espanol','E')")
        conn.commit(); conn.close()
        db.migrate(path)
        got = dict(sqlite3.connect(path).execute("SELECT slug, color FROM subjects").fetchall())
        self.assertEqual(got, {"matematicas": "red", "espanol": "blue"})
