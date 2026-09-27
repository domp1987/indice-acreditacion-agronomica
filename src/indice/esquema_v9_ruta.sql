-- Esquema v9: ruta de formación y aprendizaje 2020-2027 (plan-estudios-agronomica-v4.pdf).
-- curso.numero: posición del curso en la ruta (1-60; los diagnósticos y nivelatorios de 0 créditos no son cursos).
ALTER TABLE curso ADD COLUMN numero INTEGER;
-- Prerrequisitos. requisito_id es nulo cuando el requisito es un diagnóstico y nivelatorio (0 créditos).
CREATE TABLE IF NOT EXISTS curso_prerrequisito (
  curso_id INTEGER NOT NULL REFERENCES curso(id),
  requisito_id INTEGER REFERENCES curso(id),
  requisito TEXT NOT NULL,
  PRIMARY KEY (curso_id, requisito)
);
