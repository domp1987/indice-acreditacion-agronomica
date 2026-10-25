-- Esquema v15: Sello SOFÍA de la Fundación madri+d (acreditación institucional internacional, marco SOFIA).
-- Cada estándar se lee desde la autoevaluación institucional: valoración de las características CNA-INST que le
-- responden (correspondencias parcial o equivalente de sus apartados), evidencias y brechas abiertas.
DROP VIEW IF EXISTS v_valoracion_sofia;
CREATE VIEW v_valoracion_sofia AS
WITH apartados AS (
  SELECT e.id AS estandar_id, a.id AS nodo_id FROM nodo e JOIN marco m ON m.id=e.marco_id AND m.codigo='SOFIA'
  JOIN nodo a ON a.id=e.id OR a.padre_id=e.id WHERE e.padre_id IS NULL
), inst AS (
  SELECT DISTINCT ap.estandar_id, o.codigo FROM apartados ap
  JOIN correspondencia c ON c.destino_id=ap.nodo_id AND c.estado<>'descartada' AND c.tipo IN ('equivalente','parcial')
  JOIN nodo o ON o.id=c.origen_id JOIN marco mo ON mo.id=o.marco_id AND mo.codigo='CNA-INST'
)
SELECT e.codigo, e.nombre,
  (SELECT ROUND(AVG(v.valoracion), 2) FROM inst JOIN v_valoracion_cna_inst v ON v.codigo=inst.codigo WHERE inst.estandar_id=e.id) AS valoracion_inst,
  (SELECT MIN(v.valoracion) FROM inst JOIN v_valoracion_cna_inst v ON v.codigo=inst.codigo WHERE inst.estandar_id=e.id) AS minima_inst,
  (SELECT GROUP_CONCAT(inst.codigo || '=' || COALESCE(v.valoracion, 's.d.'), ' ') FROM inst LEFT JOIN v_valoracion_cna_inst v ON v.codigo=inst.codigo WHERE inst.estandar_id=e.id) AS caracteristicas,
  (SELECT COUNT(DISTINCT en.evidencia_id) FROM apartados ap JOIN evidencia_nodo en ON en.nodo_id=ap.nodo_id AND en.estado<>'descartada'
     JOIN evidencia ev ON ev.id=en.evidencia_id AND ev.estado_revision<>'obsoleta' WHERE ap.estandar_id=e.id) AS evidencias,
  (SELECT COUNT(*) FROM apartados ap JOIN brecha b ON b.nodo_id=ap.nodo_id AND b.estado<>'cerrada' WHERE ap.estandar_id=e.id AND b.severidad IN ('alta','media')) AS brechas_media_alta,
  (SELECT COUNT(*) FROM apartados ap JOIN brecha b ON b.nodo_id=ap.nodo_id AND b.estado<>'cerrada' WHERE ap.estandar_id=e.id) AS brechas
FROM nodo e JOIN marco m ON m.id=e.marco_id AND m.codigo='SOFIA'
WHERE e.padre_id IS NULL ORDER BY e.orden;
