-- Esquema v6: documento maestro RRC 2025 (ruta de aprendizaje propuesta). Tablas derivadas: se reconstruyen en cada carga.
ALTER TABLE tabla_diapositiva ADD COLUMN leyenda TEXT;   -- p. ej. 'Tabla 23. Ruta de Aprendizaje…' (documento maestro)

-- Ruta de aprendizaje propuesta (Tabla 'Ruta de Aprendizaje del programa académico … 2025')
CREATE TABLE IF NOT EXISTS plan_2025 (
  id INTEGER PRIMARY KEY,
  orden INTEGER NOT NULL,
  periodo INTEGER NOT NULL,
  nombre TEXT NOT NULL,
  tipo TEXT NOT NULL CHECK (tipo IN ('disciplinar','institucional')),
  obligatorio INTEGER,
  creditos INTEGER,
  horas_acompanamiento INTEGER,
  horas_independiente INTEGER,
  horas_total INTEGER,
  max_estudiantes INTEGER,
  creditos_distribucion INTEGER,        -- créditos según la tabla 'Distribución de los CADI' (para contrastar)
  evidencia_id INTEGER REFERENCES evidencia(id)
);

-- Plan de transición ruta 2020 → 2026 (homologación H o curso complementario C**)
CREATE TABLE IF NOT EXISTS transicion_2025 (
  id INTEGER PRIMARY KEY,
  orden INTEGER NOT NULL,
  curso_vigente TEXT,
  semestre_vigente INTEGER,
  creditos_vigente INTEGER,
  curso_propuesto TEXT NOT NULL,
  semestre_propuesto INTEGER,
  creditos_propuesto INTEGER,
  tipo TEXT
);

-- REA específicos de cada CADI de la ruta propuesta, con el perfil (P1–P3) al que aporta
CREATE TABLE IF NOT EXISTS plan_2025_rea (
  id INTEGER PRIMARY KEY,
  codigo_cadi TEXT NOT NULL,
  campo TEXT,
  creditos INTEGER,
  perfil TEXT,
  consecutivo INTEGER,
  texto TEXT
);

-- Inconsistencias internas del plan propuesto: horas que no son créditos × 48 y créditos distintos entre tablas
CREATE VIEW IF NOT EXISTS v_plan_2025_inconsistencias AS
SELECT periodo, nombre, creditos, horas_total, creditos_distribucion,
  TRIM(CASE WHEN horas_total IS NOT NULL AND creditos IS NOT NULL AND horas_total <> creditos * 48
            THEN 'horas totales ' || horas_total || ' ≠ ' || creditos || ' créditos × 48; ' ELSE '' END ||
       CASE WHEN creditos_distribucion IS NOT NULL AND creditos_distribucion <> creditos
            THEN 'la tabla de distribución de CADI dice ' || creditos_distribucion || ' créditos' ELSE '' END) AS problema
FROM plan_2025
WHERE (horas_total IS NOT NULL AND creditos IS NOT NULL AND horas_total <> creditos * 48)
   OR (creditos_distribucion IS NOT NULL AND creditos_distribucion <> creditos);
