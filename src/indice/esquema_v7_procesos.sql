-- Esquema v7: proceso al que sirve cada evidencia.
--   acreditacion    -> acreditación de alta calidad (CNA): presentaciones de factores y sesión de inicio, documento maestro 2019
--   resignificacion -> resignificación curricular / renovación de registro calificado: documento maestro RRC 2025 y sus anexos
--   ambos           -> Planes de Aprendizaje Digital (ruta vigente, anexados también a la renovación)
ALTER TABLE evidencia ADD COLUMN proceso TEXT;
CREATE INDEX IF NOT EXISTS evidencia_proceso ON evidencia(proceso);
