-- Juegos: pregunta tipo "order", bloque de contenido "scene" y emoji por opción de respuesta.
-- SQLite no permite cambiar un CHECK, así que se reconstruyen las tablas (receta oficial de 12 pasos;
-- migrate() ejecuta esto con las claves foráneas desactivadas y verifica la integridad al terminar).
ALTER TABLE answer_options ADD COLUMN emoji TEXT NOT NULL DEFAULT '';

CREATE TABLE questions_new (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('mcq','tf','numeric','short','match','order')),
  prompt TEXT NOT NULL, explanation TEXT NOT NULL DEFAULT '',
  difficulty INTEGER NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 3),
  points REAL NOT NULL DEFAULT 1 CHECK (points > 0),
  data TEXT NOT NULL DEFAULT '{}',      -- + scene (emoji decorativo), layout ('images'), order: {items}
  competency_id INTEGER NOT NULL REFERENCES competencies(id),
  lesson_id INTEGER REFERENCES lessons(id) ON DELETE SET NULL,
  language TEXT NOT NULL DEFAULT 'es',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT INTO questions_new (id, kind, prompt, explanation, difficulty, points, data, competency_id, lesson_id, language, created_at)
  SELECT id, kind, prompt, explanation, difficulty, points, data, competency_id, lesson_id, language, created_at FROM questions;
DROP TABLE questions;
ALTER TABLE questions_new RENAME TO questions;
CREATE INDEX ix_questions_comp ON questions(competency_id);

CREATE TABLE content_blocks_new (
  id INTEGER PRIMARY KEY, lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
  position INTEGER NOT NULL DEFAULT 0,
  type TEXT NOT NULL CHECK (type IN ('text','example','tip','mistakes','summary','flashcards','scene')),
  data TEXT NOT NULL DEFAULT '{}'
);
INSERT INTO content_blocks_new (id, lesson_id, position, type, data) SELECT id, lesson_id, position, type, data FROM content_blocks;
DROP TABLE content_blocks;
ALTER TABLE content_blocks_new RENAME TO content_blocks;
