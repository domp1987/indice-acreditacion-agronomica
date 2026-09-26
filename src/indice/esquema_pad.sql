-- Planes de Aprendizaje Digital (PAD) de cada CADI (esquema v3). Se reconstruyen en cada carga desde PADs/.
-- Las listas (lugares, instrumentos, dimensiones…) van como arreglos JSON; se consultan con json_each.
CREATE TABLE IF NOT EXISTS pad (
  id INTEGER PRIMARY KEY,
  codigo TEXT UNIQUE NOT NULL,           -- código del CAD (del nombre del archivo o del PDF); '-EN' si es la versión en inglés
  evidencia_id INTEGER REFERENCES evidencia(id),   -- el PAD completo como evidencia 'PAD-<codigo>'
  curso_id INTEGER REFERENCES curso(id), -- según datos/semillas/pad_curso.csv
  nombre TEXT NOT NULL,
  programa TEXT,
  plantilla TEXT,                        -- V1.9 o V2
  idioma TEXT,
  semestre INTEGER,
  creditos INTEGER,
  prerrequisitos TEXT,
  justificacion TEXT,
  rea_general TEXT,
  acciones TEXT CHECK (acciones IS NULL OR json_valid(acciones)),   -- postulados, mejoras, transformaciones
  archivo TEXT,
  paginas INTEGER
);
CREATE TABLE IF NOT EXISTS pad_rea (
  pad_id INTEGER NOT NULL REFERENCES pad(id),
  consecutivo INTEGER NOT NULL,
  texto TEXT NOT NULL,
  PRIMARY KEY (pad_id, consecutivo)
);
CREATE TABLE IF NOT EXISTS pad_experiencia (
  id INTEGER PRIMARY KEY,
  pad_id INTEGER NOT NULL REFERENCES pad(id),
  orden INTEGER NOT NULL,
  tipo TEXT NOT NULL CHECK (tipo IN ('vive_experiencia','soluciona_problema')),
  nombre TEXT,
  rea TEXT,                              -- REA específico al que apunta (texto o consecutivo)
  descripcion TEXT,
  dimensiones TEXT CHECK (dimensiones IS NULL OR json_valid(dimensiones)),
  integrantes INTEGER,
  competencias TEXT CHECK (competencias IS NULL OR json_valid(competencias)),   -- competencias genéricas Saber Pro
  componentes TEXT CHECK (componentes IS NULL OR json_valid(componentes)),
  unidad_regional TEXT,
  lineas_translocales TEXT
);
CREATE TABLE IF NOT EXISTS pad_actividad (
  id INTEGER PRIMARY KEY,
  experiencia_id INTEGER NOT NULL REFERENCES pad_experiencia(id),
  orden INTEGER NOT NULL,
  etapa TEXT,                            -- en 'Soluciona un problema': Analicemos, Planifiquemos, Solucionemos, Evidenciemos
  nombre TEXT,
  descripcion TEXT,
  trabajo_estudiante TEXT,
  trabajo_profesor TEXT,
  semana_inicio INTEGER,
  duracion_semanas INTEGER,
  fase TEXT,
  tipo_actividad TEXT,
  lugares TEXT CHECK (lugares IS NULL OR json_valid(lugares)),
  instrumentos TEXT CHECK (instrumentos IS NULL OR json_valid(instrumentos)),   -- instrumentos de recolección (evaluación)
  descripcion_instrumentos TEXT,
  recursos_cgca TEXT CHECK (recursos_cgca IS NULL OR json_valid(recursos_cgca)),
  recursos_externos TEXT CHECK (recursos_externos IS NULL OR json_valid(recursos_externos))
);
CREATE TABLE IF NOT EXISTS pad_bibliografia (
  pad_id INTEGER NOT NULL REFERENCES pad(id),
  orden INTEGER NOT NULL,
  autor TEXT,
  titulo TEXT NOT NULL,
  anio INTEGER,
  editorial TEXT,
  edicion TEXT,
  isbn TEXT,                             -- V1.9: número ISBN
  identificador TEXT,                    -- V2: tipo de identificador (ISBN, DOI, ISSN, NA)
  PRIMARY KEY (pad_id, orden)
);
CREATE TABLE IF NOT EXISTS pad_recurso (
  pad_id INTEGER NOT NULL REFERENCES pad(id),
  orden INTEGER NOT NULL,
  nombre TEXT NOT NULL,
  tipo TEXT,
  area TEXT,
  PRIMARY KEY (pad_id, orden)
);

-- Cada curso del plan con su PAD: créditos del plan frente a los del PAD, semestre y volumen de actividades
CREATE VIEW IF NOT EXISTS v_pad_curso AS
SELECT c.nombre AS curso, c.creditos AS creditos_plan, p.codigo AS pad, p.creditos AS creditos_pad, p.semestre,
       (SELECT COUNT(*) FROM pad_actividad a JOIN pad_experiencia e ON e.id = a.experiencia_id WHERE e.pad_id = p.id) AS actividades,
       CASE WHEN p.id IS NULL THEN 'sin PAD' WHEN p.creditos <> c.creditos THEN 'créditos distintos' ELSE 'ok' END AS estado
FROM curso c LEFT JOIN pad p ON p.curso_id = c.id
ORDER BY p.semestre, c.nombre;

-- Espacios donde ocurren las actividades (insumo para el Criterio 7 de ABET)
CREATE VIEW IF NOT EXISTS v_pad_lugar AS
SELECT p.codigo AS pad, p.nombre AS curso, a.nombre AS actividad, j.value AS lugar
FROM pad_actividad a JOIN pad_experiencia e ON e.id = a.experiencia_id JOIN pad p ON p.id = e.pad_id, json_each(a.lugares) j;

-- Instrumentos de recolección de datos por actividad (insumo para la evaluación directa del Criterio 4)
CREATE VIEW IF NOT EXISTS v_pad_instrumento AS
SELECT p.codigo AS pad, p.nombre AS curso, e.nombre AS experiencia, a.nombre AS actividad, j.value AS instrumento,
       a.descripcion_instrumentos
FROM pad_actividad a JOIN pad_experiencia e ON e.id = a.experiencia_id JOIN pad p ON p.id = e.pad_id, json_each(a.instrumentos) j;
