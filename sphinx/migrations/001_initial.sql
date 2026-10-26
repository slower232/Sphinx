-- Sphinx: esquema inicial. Las fechas se guardan en UTC (datetime('now')).
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  alias TEXT NOT NULL UNIQUE COLLATE NOCASE,
  email TEXT UNIQUE COLLATE NOCASE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('student','admin')),
  is_active INTEGER NOT NULL DEFAULT 1,
  consent_version TEXT,
  consent_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE anon_sessions (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  last_seen_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE subjects (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '', icon TEXT NOT NULL DEFAULT '📘', position INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE competencies (
  id INTEGER PRIMARY KEY, subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT ''
);
CREATE TABLE courses (
  id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE,
  subject_id INTEGER NOT NULL REFERENCES subjects(id),
  title TEXT NOT NULL, description TEXT NOT NULL,
  objectives TEXT NOT NULL DEFAULT '[]',
  level TEXT NOT NULL DEFAULT 'basico' CHECK (level IN ('inicial','basico','intermedio','avanzado')),
  difficulty INTEGER NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 3),
  est_minutes INTEGER NOT NULL DEFAULT 30,
  prerequisites TEXT NOT NULL DEFAULT '', resources TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','published','archived')),
  pass_pct INTEGER NOT NULL DEFAULT 70 CHECK (pass_pct BETWEEN 1 AND 100),
  max_attempts INTEGER NOT NULL DEFAULT 0 CHECK (max_attempts >= 0),   -- 0 = ilimitados
  version INTEGER NOT NULL DEFAULT 1,
  language TEXT NOT NULL DEFAULT 'es',
  is_demo INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX ix_courses_status ON courses(status, subject_id);
CREATE TABLE course_competencies (
  course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  competency_id INTEGER NOT NULL REFERENCES competencies(id) ON DELETE CASCADE,
  PRIMARY KEY (course_id, competency_id)
);
CREATE TABLE units (
  id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  title TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE lessons (
  id INTEGER PRIMARY KEY, unit_id INTEGER NOT NULL REFERENCES units(id) ON DELETE CASCADE,
  title TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '', est_minutes INTEGER NOT NULL DEFAULT 10,
  position INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE content_blocks (
  id INTEGER PRIMARY KEY, lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
  position INTEGER NOT NULL DEFAULT 0,
  type TEXT NOT NULL CHECK (type IN ('text','example','tip','mistakes','summary','flashcards')),
  data TEXT NOT NULL DEFAULT '{}'      -- JSON validado en services/blocks.py
);
CREATE TABLE questions (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('mcq','tf','numeric','short','match')),
  prompt TEXT NOT NULL, explanation TEXT NOT NULL DEFAULT '',
  difficulty INTEGER NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 3),
  points REAL NOT NULL DEFAULT 1 CHECK (points > 0),
  data TEXT NOT NULL DEFAULT '{}',      -- numeric: {answer,tolerance}; short: {accepted}; match: {pairs}
  competency_id INTEGER NOT NULL REFERENCES competencies(id),
  lesson_id INTEGER REFERENCES lessons(id) ON DELETE SET NULL,
  language TEXT NOT NULL DEFAULT 'es',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX ix_questions_comp ON questions(competency_id);
CREATE TABLE answer_options (
  id INTEGER PRIMARY KEY, question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  position INTEGER NOT NULL DEFAULT 0, text TEXT NOT NULL, is_correct INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE assessments (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('diagnostic','formative','final')),
  title TEXT NOT NULL,
  course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
  lesson_id INTEGER REFERENCES lessons(id) ON DELETE CASCADE,
  subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
  CHECK ((kind='diagnostic' AND subject_id IS NOT NULL AND course_id IS NULL AND lesson_id IS NULL)
      OR (kind='formative' AND lesson_id IS NOT NULL AND course_id IS NOT NULL)
      OR (kind='final' AND course_id IS NOT NULL AND lesson_id IS NULL))
);
CREATE UNIQUE INDEX ux_asm_final ON assessments(course_id) WHERE kind='final';
CREATE UNIQUE INDEX ux_asm_formative ON assessments(lesson_id) WHERE kind='formative';
CREATE UNIQUE INDEX ux_asm_diag ON assessments(subject_id) WHERE kind='diagnostic';
CREATE TABLE assessment_questions (
  assessment_id INTEGER NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
  question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  position INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (assessment_id, question_id)
);
-- Intentos: el "dueño" es una cuenta (user_id) o una sesión anónima (anon_id), nunca ambos.
CREATE TABLE attempts (
  id INTEGER PRIMARY KEY,
  assessment_id INTEGER REFERENCES assessments(id) ON DELETE CASCADE,   -- NULL en retos de repaso
  kind TEXT NOT NULL CHECK (kind IN ('diagnostic','formative','final','review')),
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  anon_id TEXT REFERENCES anon_sessions(id) ON DELETE CASCADE,
  question_ids TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress','submitted')),
  started_at TEXT NOT NULL DEFAULT (datetime('now')),
  submitted_at TEXT, score_pct REAL, points REAL, max_points REAL, passed INTEGER,
  CHECK ((user_id IS NULL) != (anon_id IS NULL))
);
CREATE INDEX ix_attempts_user ON attempts(user_id, status);
CREATE INDEX ix_attempts_anon ON attempts(anon_id, status);
CREATE TABLE responses (
  id INTEGER PRIMARY KEY, attempt_id INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
  question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE RESTRICT,
  response TEXT NOT NULL, is_correct INTEGER NOT NULL, points REAL NOT NULL,
  UNIQUE (attempt_id, question_id)
);
CREATE TABLE lesson_progress (
  id INTEGER PRIMARY KEY, lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  anon_id TEXT REFERENCES anon_sessions(id) ON DELETE CASCADE,
  completed_at TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK ((user_id IS NULL) != (anon_id IS NULL))
);
CREATE UNIQUE INDEX ux_lp ON lesson_progress(COALESCE(user_id,-1), COALESCE(anon_id,''), lesson_id);
CREATE TABLE enrollments (
  id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  anon_id TEXT REFERENCES anon_sessions(id) ON DELETE CASCADE,
  started_at TEXT NOT NULL DEFAULT (datetime('now')),
  last_activity_at TEXT NOT NULL DEFAULT (datetime('now')),
  completed_at TEXT,
  CHECK ((user_id IS NULL) != (anon_id IS NULL))
);
CREATE UNIQUE INDEX ux_enr ON enrollments(COALESCE(user_id,-1), COALESCE(anon_id,''), course_id);
CREATE TABLE learner_goals (
  id INTEGER PRIMARY KEY, subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
  competency_id INTEGER REFERENCES competencies(id) ON DELETE CASCADE,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  anon_id TEXT REFERENCES anon_sessions(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK ((user_id IS NULL) != (anon_id IS NULL))
);
CREATE UNIQUE INDEX ux_goal ON learner_goals(COALESCE(user_id,-1), COALESCE(anon_id,''), subject_id, COALESCE(competency_id,0));
-- XP: un evento por (dueño, tipo, referencia) => repetir una acción no suma puntos.
CREATE TABLE xp_events (
  id INTEGER PRIMARY KEY, kind TEXT NOT NULL, ref_key TEXT NOT NULL, points INTEGER NOT NULL,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  anon_id TEXT REFERENCES anon_sessions(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK ((user_id IS NULL) != (anon_id IS NULL))
);
CREATE UNIQUE INDEX ux_xp ON xp_events(COALESCE(user_id,-1), COALESCE(anon_id,''), kind, ref_key);
CREATE TABLE achievements (
  id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
  description TEXT NOT NULL, icon TEXT NOT NULL DEFAULT '🏅'
);
CREATE TABLE user_achievements (
  id INTEGER PRIMARY KEY, achievement_id INTEGER NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  anon_id TEXT REFERENCES anon_sessions(id) ON DELETE CASCADE,
  earned_at TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK ((user_id IS NULL) != (anon_id IS NULL))
);
CREATE UNIQUE INDEX ux_ua ON user_achievements(COALESCE(user_id,-1), COALESCE(anon_id,''), achievement_id);
CREATE TABLE certificates (
  id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  display_name TEXT NOT NULL, score_pct REAL NOT NULL,
  issued_at TEXT NOT NULL DEFAULT (datetime('now')), revoked_at TEXT,
  UNIQUE (user_id, course_id)
);
CREATE TABLE audit_log (
  id INTEGER PRIMARY KEY, admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  action TEXT NOT NULL, entity TEXT NOT NULL, entity_id INTEGER, detail TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE login_attempts (id INTEGER PRIMARY KEY, key TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE INDEX ix_login_key ON login_attempts(key, created_at);
CREATE TABLE password_resets (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE, expires_at TEXT NOT NULL, used_at TEXT
);
-- Solo se guarda CUÁNDO se usó el tutor (para límites), nunca el contenido de los mensajes.
CREATE TABLE tutor_usage (
  id INTEGER PRIMARY KEY,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  anon_id TEXT REFERENCES anon_sessions(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK ((user_id IS NULL) != (anon_id IS NULL))
);
CREATE INDEX ix_tutor_user ON tutor_usage(user_id, created_at);
CREATE INDEX ix_tutor_anon ON tutor_usage(anon_id, created_at);
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
