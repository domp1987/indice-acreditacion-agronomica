-- Esquema v13: análisis CNA de alta calidad (Acuerdo CESU 02 de 2020) sobre la autoevaluación del programa.
-- Grado de cumplimiento inferido de los propios informes de valoración del programa (12 presentaciones):
--   >= 4,5 "Se cumple plenamente"; 3,7 a 4,4 "Se cumple en alto grado". No hay valores por debajo de 3,7, así que los
--   demás grados no se infieren (la escala institucional no está en las fuentes).
-- Señales externas: brechas abiertas de ABET, ATMAE o ANECA en los nodos a los que la característica se proyecta por una
-- correspondencia equivalente o parcial (no se heredan de los nodos padre: allí están brechas de elegibilidad o de la agencia). Riesgo de sobrevaloración: valoración alta con brechas externas de severidad alta.
DROP VIEW IF EXISTS v_valoracion_cna;
CREATE VIEW v_valoracion_cna AS
WITH val AS (
  SELECT n.id, n.codigo, n.nombre, p.codigo AS factor, p.nombre AS factor_nombre, n.orden,
    (SELECT m.valor FROM medicion m JOIN indicador i ON i.id=m.indicador_id WHERE i.codigo='CNA_POND' AND m.desagregacion=n.codigo) AS ponderacion,
    (SELECT m.valor FROM medicion m JOIN indicador i ON i.id=m.indicador_id WHERE i.codigo='CNA_VAL' AND m.desagregacion=n.codigo) AS valoracion,
    (SELECT COUNT(DISTINCT en.evidencia_id) FROM evidencia_nodo en JOIN evidencia e ON e.id=en.evidencia_id
       WHERE en.nodo_id=n.id AND en.estado<>'descartada' AND e.estado_revision<>'obsoleta' AND COALESCE(e.nivel,'principal')<>'escenario') AS evidencias,
    (SELECT COUNT(DISTINCT b.id) FROM correspondencia c JOIN nodo d ON d.id=c.destino_id
       JOIN brecha b ON b.nodo_id=d.id AND b.estado<>'cerrada' AND b.severidad='alta'
       WHERE c.origen_id=n.id AND c.estado<>'descartada' AND c.tipo IN ('equivalente','parcial')) AS senales_altas,
    (SELECT COUNT(DISTINCT b.id) FROM correspondencia c JOIN nodo d ON d.id=c.destino_id
       JOIN brecha b ON b.nodo_id=d.id AND b.estado<>'cerrada' AND b.severidad='media'
       WHERE c.origen_id=n.id AND c.estado<>'descartada' AND c.tipo IN ('equivalente','parcial')) AS senales_medias,
    (SELECT COUNT(*) FROM brecha b WHERE b.nodo_id IN (n.id, n.padre_id) AND b.estado<>'cerrada') AS brechas_cna
  FROM nodo n JOIN marco m ON m.id=n.marco_id AND m.codigo='CNA' JOIN nodo p ON p.id=n.padre_id
  WHERE n.tipo='caracteristica'
)
SELECT codigo, nombre, factor, factor_nombre, ponderacion, valoracion,
  CASE WHEN valoracion >= 4.5 THEN 'Se cumple plenamente' WHEN valoracion >= 3.7 THEN 'Se cumple en alto grado'
       WHEN valoracion IS NULL THEN 'sin valoración' ELSE 'por debajo de 3,7' END AS grado,
  evidencias, senales_altas, senales_medias, brechas_cna,
  CASE WHEN valoracion >= 4.5 AND senales_altas >= 2 THEN 'alto'
       WHEN valoracion >= 4.0 AND senales_altas >= 1 THEN 'medio'
       ELSE 'bajo' END AS riesgo_sobrevaloracion
FROM val ORDER BY orden;
