-- Esquema v8: peso de cada evidencia como fuente para ABET (independiente del proceso).
--   principal       -> base de la proyección ABET: presentaciones CNA (OneDrive_1_9-23-2026), PAD y documento maestro 2019
--   complementaria  -> fuente de consulta, anterior a la base: anexos del RRC (ANEXOS/). Hacia ABET solo infiere 'apoyo'
--   escenario       -> ruta no confirmada: documento maestro RRC 2025 (solo renovación, sin acreditación de alta calidad).
--                      Se indexa y etiqueta con CNA para consulta, pero no infiere etiquetas ABET
ALTER TABLE evidencia ADD COLUMN nivel TEXT;
CREATE INDEX IF NOT EXISTS evidencia_nivel ON evidencia(nivel);
