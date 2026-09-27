-- Esquema v10: la matriz cursos × Student Outcomes viene de datos/semillas/curso_outcomes.csv (la edita el comité).
--   origen: pad (propuesta desde los PAD), nombre (curso sin PAD, por su nombre) o manual (la agregó el comité)
--   estado: propuesta, validada o descartada; validada exige validado_por. Nunca se valida desde código.
ALTER TABLE curso_outcome ADD COLUMN estado TEXT NOT NULL DEFAULT 'propuesta' CHECK (estado IN ('propuesta','validada','descartada'));
ALTER TABLE curso_outcome ADD COLUMN origen TEXT;
ALTER TABLE curso_outcome ADD COLUMN puntaje INTEGER;
ALTER TABLE curso_outcome ADD COLUMN justificacion TEXT;
ALTER TABLE curso_outcome ADD COLUMN validado_por TEXT;
