-- Esquema v5: auditoría de las decisiones del comité (tarea 5). Esta tabla nunca se vacía ni se reconstruye.
CREATE TABLE IF NOT EXISTS decision (
  id INTEGER PRIMARY KEY,
  fecha TEXT NOT NULL,                   -- UTC, ISO 8601
  validador TEXT NOT NULL,
  objeto TEXT NOT NULL CHECK (objeto IN ('correspondencia','etiqueta')),
  referencia TEXT NOT NULL,              -- legible y estable: 'CNA/C10 → ABET-EAC/C6' o 'F05-P027 → ABET-EAC/SO6'
  correspondencia_id INTEGER,
  evidencia_id INTEGER,
  nodo_id INTEGER,
  accion TEXT NOT NULL CHECK (accion IN ('validar','descartar','reabrir','agregar')),
  estado_anterior TEXT,
  estado_nuevo TEXT,
  rol TEXT,
  comentario TEXT
);
CREATE INDEX IF NOT EXISTS decision_fecha ON decision(fecha);

-- Cobertura ABET con el estado de validación de sus etiquetas (sin evidencias obsoletas)
CREATE VIEW IF NOT EXISTS v_validacion_abet AS
SELECT n.codigo, n.nombre, n.orden,
  SUM(CASE WHEN en.estado='validada' AND en.validado_por IS NOT NULL THEN 1 ELSE 0 END) AS validadas_comite,
  SUM(CASE WHEN en.estado='propuesta' THEN 1 ELSE 0 END) AS propuestas,
  SUM(CASE WHEN en.estado='descartada' THEN 1 ELSE 0 END) AS descartadas,
  SUM(CASE WHEN en.origen='manual' THEN 1 ELSE 0 END) AS manuales
FROM nodo n JOIN marco m ON m.id=n.marco_id AND m.codigo='ABET-EAC'
LEFT JOIN evidencia_nodo en ON en.nodo_id=n.id
  AND en.evidencia_id NOT IN (SELECT id FROM evidencia WHERE estado_revision='obsoleta')
GROUP BY n.id ORDER BY n.orden;
