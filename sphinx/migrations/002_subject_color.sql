-- Color de identidad por materia (se usa como clase CSS c-<color>).
ALTER TABLE subjects ADD COLUMN color TEXT NOT NULL DEFAULT 'green' CHECK (color IN ('green','red','blue','orange','purple'));
UPDATE subjects SET color='red' WHERE slug='matematicas';
UPDATE subjects SET color='blue' WHERE slug='espanol';
UPDATE subjects SET color='green' WHERE slug='ciencias-naturales';
