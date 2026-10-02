-- Esquema v12: marco ANECA (Sello Internacional de Calidad EUR-ACE).
-- Módulo de cada curso según la Orden CIN/323/2009 (referencia española de Ingeniero Técnico Agrícola):
--   basico, comun_agricola, tecnologia_especifica, tfg, transversal
ALTER TABLE curso ADD COLUMN modulo_cin TEXT;

CREATE VIEW IF NOT EXISTS v_cobertura_aneca AS
SELECT n.codigo, n.nombre, n.tipo,
  SUM(CASE WHEN en.rol='principal' THEN 1 ELSE 0 END) AS principales,
  SUM(CASE WHEN en.rol='parcial' THEN 1 ELSE 0 END) AS parciales,
  SUM(CASE WHEN en.rol='apoyo' THEN 1 ELSE 0 END) AS apoyo,
  (SELECT COUNT(*) FROM brecha b WHERE b.nodo_id=n.id AND b.estado<>'cerrada') AS brechas_abiertas
FROM nodo n JOIN marco m ON m.id=n.marco_id AND m.codigo='ANECA-EURACE'
LEFT JOIN evidencia_nodo en ON en.nodo_id=n.id AND en.estado<>'descartada'
  AND en.evidencia_id NOT IN (SELECT id FROM evidencia WHERE estado_revision='obsoleta')
GROUP BY n.id ORDER BY n.orden;

-- Créditos por módulo de la Orden CIN/323/2009 en ECTS equivalentes: 1 crédito colombiano = 48 h; 1 ECTS = 30 h (factor 1,6)
CREATE VIEW IF NOT EXISTS v_creditos_aneca AS
SELECT a.modulo, COALESCE(SUM(c.creditos), 0) AS creditos, ROUND(COALESCE(SUM(c.creditos), 0) * 1.6) AS ects, COUNT(c.id) AS cursos, a.minimo_ects
FROM (SELECT 'basico' modulo, 60 minimo_ects, 1 orden UNION ALL SELECT 'comun_agricola', 60, 2 UNION ALL SELECT 'tecnologia_especifica', 48, 3
      UNION ALL SELECT 'tfg', 12, 4 UNION ALL SELECT 'transversal', 0, 5) a
LEFT JOIN curso c ON c.modulo_cin = a.modulo
GROUP BY a.modulo ORDER BY a.orden;
