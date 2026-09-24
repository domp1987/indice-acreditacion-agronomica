-- Índice de evidencias para acreditación (CNA -> ABET y otros marcos)
-- Programa Ingeniería Agronómica, UCundinamarca (Fusagasugá / ALD Facatativá)
PRAGMA foreign_keys = ON;

-- Marcos de acreditación o de referencia (CNA, ABET, resultados del programa, etc.)
CREATE TABLE marco (
  id INTEGER PRIMARY KEY,
  codigo TEXT UNIQUE NOT NULL,
  nombre TEXT NOT NULL,
  version TEXT,
  descripcion TEXT
);

-- Jerarquía de cada marco: factor > característica, criterio > subcriterio / outcome
CREATE TABLE nodo (
  id INTEGER PRIMARY KEY,
  marco_id INTEGER NOT NULL REFERENCES marco(id),
  codigo TEXT NOT NULL,
  nombre TEXT NOT NULL,
  descripcion TEXT,
  tipo TEXT NOT NULL,              -- factor, caracteristica, criterio, subcriterio, outcome, rea
  padre_id INTEGER REFERENCES nodo(id),
  orden INTEGER,
  UNIQUE (marco_id, codigo)
);

-- Correspondencias entre nodos de marcos distintos (la "reproyección")
CREATE TABLE correspondencia (
  id INTEGER PRIMARY KEY,
  origen_id INTEGER NOT NULL REFERENCES nodo(id),
  destino_id INTEGER NOT NULL REFERENCES nodo(id),
  tipo TEXT NOT NULL CHECK (tipo IN ('equivalente','parcial','apoyo')),
  estado TEXT NOT NULL DEFAULT 'propuesta' CHECK (estado IN ('propuesta','validada','descartada')),
  nota TEXT,
  UNIQUE (origen_id, destino_id)
);

-- Unidad básica: una evidencia (diapositiva, acuerdo, acta, documento, dato)
CREATE TABLE evidencia (
  id INTEGER PRIMARY KEY,
  codigo TEXT UNIQUE NOT NULL,     -- p.ej. F05-P027
  titulo TEXT NOT NULL,
  tipo TEXT NOT NULL,              -- diapositiva, valoracion, logros, plan_mejora, normativa, documento, dato
  texto TEXT,
  fuente TEXT,                     -- oficina que produce el dato
  archivo TEXT,
  pagina INTEGER,
  sede TEXT,                       -- Fusagasugá, Facatativá, Programa
  periodo TEXT,
  url_sharepoint TEXT,
  idioma TEXT DEFAULT 'es',
  responsable TEXT,
  estado_revision TEXT NOT NULL DEFAULT 'sin_revisar'
    CHECK (estado_revision IN ('sin_revisar','revisada','requiere_traduccion','obsoleta'))
);

-- Etiquetado evidencia <-> nodo. origen: extraccion (del PDF), inferida (vía correspondencia), manual
CREATE TABLE evidencia_nodo (
  evidencia_id INTEGER NOT NULL REFERENCES evidencia(id),
  nodo_id INTEGER NOT NULL REFERENCES nodo(id),
  rol TEXT NOT NULL CHECK (rol IN ('principal','parcial','apoyo')),
  origen TEXT NOT NULL CHECK (origen IN ('extraccion','inferida','manual')),
  estado TEXT NOT NULL DEFAULT 'propuesta' CHECK (estado IN ('propuesta','validada','descartada')),
  PRIMARY KEY (evidencia_id, nodo_id)
);

-- Indicadores y sus mediciones (series por periodo y sede)
CREATE TABLE indicador (
  id INTEGER PRIMARY KEY,
  codigo TEXT UNIQUE NOT NULL,
  nombre TEXT NOT NULL,
  unidad TEXT,
  descripcion TEXT
);
CREATE TABLE medicion (
  id INTEGER PRIMARY KEY,
  indicador_id INTEGER NOT NULL REFERENCES indicador(id),
  periodo TEXT NOT NULL,
  sede TEXT NOT NULL DEFAULT 'Programa',
  valor REAL NOT NULL,
  desagregacion TEXT NOT NULL DEFAULT '',   -- p.ej. característica C01, línea, cohorte
  evidencia_id INTEGER REFERENCES evidencia(id),
  nota TEXT
);
CREATE TABLE indicador_nodo (
  indicador_id INTEGER NOT NULL REFERENCES indicador(id),
  nodo_id INTEGER NOT NULL REFERENCES nodo(id),
  rol TEXT NOT NULL DEFAULT 'principal',
  PRIMARY KEY (indicador_id, nodo_id)
);

-- Plan de estudios con clasificación para el Criterio 5 de ABET
CREATE TABLE curso (
  id INTEGER PRIMARY KEY,
  nombre TEXT NOT NULL,
  componente_cma TEXT NOT NULL,
  creditos INTEGER NOT NULL,
  periodo INTEGER,
  categoria_abet TEXT NOT NULL CHECK (categoria_abet IN
    ('matematicas','ciencias_basicas','ingenieria','educacion_general','otro','por_definir')),
  confianza TEXT NOT NULL CHECK (confianza IN ('alta','media','baja')),
  nota TEXT
);
-- Aporte de cada curso a los Student Outcomes: I introduce, R refuerza, E evalúa
CREATE TABLE curso_outcome (
  curso_id INTEGER NOT NULL REFERENCES curso(id),
  nodo_id INTEGER NOT NULL REFERENCES nodo(id),
  nivel TEXT NOT NULL CHECK (nivel IN ('I','R','E')),
  PRIMARY KEY (curso_id, nodo_id)
);

-- Normativa institucional citada en las evidencias
CREATE TABLE normativa (
  id INTEGER PRIMARY KEY,
  tipo TEXT NOT NULL,              -- Acuerdo, Resolución
  numero INTEGER NOT NULL,
  anio INTEGER NOT NULL,
  organo TEXT,
  UNIQUE (tipo, numero, anio)
);
CREATE TABLE normativa_mencion (
  normativa_id INTEGER NOT NULL REFERENCES normativa(id),
  evidencia_id INTEGER NOT NULL REFERENCES evidencia(id),
  PRIMARY KEY (normativa_id, evidencia_id)
);

-- Brechas y acciones (alimentan el Criterio 4 de ABET)
CREATE TABLE brecha (
  id INTEGER PRIMARY KEY,
  nodo_id INTEGER NOT NULL REFERENCES nodo(id),
  titulo TEXT NOT NULL,
  descripcion TEXT,
  severidad TEXT NOT NULL CHECK (severidad IN ('alta','media','baja')),
  accion TEXT,
  responsable TEXT,
  estado TEXT NOT NULL DEFAULT 'abierta' CHECK (estado IN ('abierta','en_curso','cerrada'))
);

-- Vistas
CREATE VIEW v_cobertura_abet AS
SELECT n.codigo, n.nombre, n.tipo,
  SUM(CASE WHEN en.rol='principal' THEN 1 ELSE 0 END) AS principales,
  SUM(CASE WHEN en.rol='parcial' THEN 1 ELSE 0 END) AS parciales,
  SUM(CASE WHEN en.rol='apoyo' THEN 1 ELSE 0 END) AS apoyo,
  (SELECT COUNT(*) FROM brecha b WHERE b.nodo_id=n.id AND b.estado<>'cerrada') AS brechas_abiertas
FROM nodo n JOIN marco m ON m.id=n.marco_id AND m.codigo='ABET-EAC'
LEFT JOIN evidencia_nodo en ON en.nodo_id=n.id AND en.estado<>'descartada'
GROUP BY n.id ORDER BY n.orden;

CREATE VIEW v_creditos_abet AS
SELECT categoria_abet, SUM(creditos) AS creditos, COUNT(*) AS cursos
FROM curso GROUP BY categoria_abet;

CREATE VIEW v_inconsistencias AS
SELECT i.codigo, i.nombre, m1.periodo, m1.sede, m1.valor AS valor_a, e1.codigo AS fuente_a,
       m2.valor AS valor_b, e2.codigo AS fuente_b
FROM medicion m1 JOIN medicion m2
  ON m1.indicador_id=m2.indicador_id AND m1.periodo=m2.periodo AND m1.sede=m2.sede AND m1.desagregacion=m2.desagregacion
 AND m1.id<m2.id AND ABS(m1.valor-m2.valor)>0.05
JOIN indicador i ON i.id=m1.indicador_id
LEFT JOIN evidencia e1 ON e1.id=m1.evidencia_id
LEFT JOIN evidencia e2 ON e2.id=m2.evidencia_id;
