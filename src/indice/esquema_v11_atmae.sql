-- Esquema v11: marco ATMAE 2027 (Association of Technology, Management, and Applied Engineering).
-- Categoría de cada curso en la estructura curricular del estándar 3.1 (tabla A-2 de pregrado):
--   educacion_general, matematicas, ciencias_fisicas, ciencias_vida, gestion, tecnica, electivas
ALTER TABLE curso ADD COLUMN categoria_atmae TEXT;

CREATE VIEW IF NOT EXISTS v_cobertura_atmae AS
SELECT n.codigo, n.nombre, n.tipo,
  SUM(CASE WHEN en.rol='principal' THEN 1 ELSE 0 END) AS principales,
  SUM(CASE WHEN en.rol='parcial' THEN 1 ELSE 0 END) AS parciales,
  SUM(CASE WHEN en.rol='apoyo' THEN 1 ELSE 0 END) AS apoyo,
  (SELECT COUNT(*) FROM brecha b WHERE b.nodo_id=n.id AND b.estado<>'cerrada') AS brechas_abiertas
FROM nodo n JOIN marco m ON m.id=n.marco_id AND m.codigo='ATMAE-2027'
LEFT JOIN evidencia_nodo en ON en.nodo_id=n.id AND en.estado<>'descartada'
  AND en.evidencia_id NOT IN (SELECT id FROM evidencia WHERE estado_revision='obsoleta')
GROUP BY n.id ORDER BY n.orden;

-- Créditos por área ATMAE frente a los mínimos y máximos de pregrado (1 crédito colombiano ≈ 1 hora semestral)
CREATE VIEW IF NOT EXISTS v_creditos_atmae AS
SELECT a.area, COALESCE(SUM(c.creditos), 0) AS creditos, COUNT(c.id) AS cursos, a.minimo, a.maximo
FROM (SELECT 'educacion_general' area, 18 minimo, 36 maximo UNION ALL SELECT 'matematicas', 6, 18
      UNION ALL SELECT 'ciencias', 6, 18 UNION ALL SELECT 'gestion_tecnica', 42, 60 UNION ALL SELECT 'electivas', 0, 18) a
LEFT JOIN curso c ON a.area = CASE c.categoria_atmae WHEN 'ciencias_fisicas' THEN 'ciencias' WHEN 'ciencias_vida' THEN 'ciencias'
                                    WHEN 'gestion' THEN 'gestion_tecnica' WHEN 'tecnica' THEN 'gestion_tecnica' ELSE c.categoria_atmae END
GROUP BY a.area ORDER BY a.minimo DESC;
