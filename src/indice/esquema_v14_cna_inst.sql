-- Esquema v14: autoevaluación institucional de la Universidad (modelo institucional del CNA, marco CNA-INST).
-- Valoraciones de las tablas «Valoración interpretativa» de cada presentación institucional (octubre de 2025).
DROP VIEW IF EXISTS v_valoracion_cna_inst;
CREATE VIEW v_valoracion_cna_inst AS
SELECT n.codigo, n.nombre, p.codigo AS factor, p.nombre AS factor_nombre,
  (SELECT m.valor FROM medicion m JOIN indicador i ON i.id=m.indicador_id WHERE i.codigo='CNA_INST_POND' AND m.desagregacion=n.codigo) AS ponderacion,
  (SELECT m.valor FROM medicion m JOIN indicador i ON i.id=m.indicador_id WHERE i.codigo='CNA_INST_VAL' AND m.desagregacion=n.codigo) AS valoracion,
  (SELECT COUNT(DISTINCT en.evidencia_id) FROM evidencia_nodo en JOIN evidencia e ON e.id=en.evidencia_id
     WHERE en.nodo_id=n.id AND en.estado<>'descartada' AND e.estado_revision<>'obsoleta') AS evidencias
FROM nodo n JOIN marco mc ON mc.id=n.marco_id AND mc.codigo='CNA-INST' JOIN nodo p ON p.id=n.padre_id
WHERE n.tipo='caracteristica' ORDER BY n.orden;

-- Coherencia programa–institución: cada característica institucional frente a la del programa que respalda
DROP VIEW IF EXISTS v_cna_inst_programa;
CREATE VIEW v_cna_inst_programa AS
SELECT i.codigo AS inst, i.nombre AS inst_nombre, vi.valoracion AS val_inst,
       d.codigo AS programa, d.nombre AS programa_nombre, vp.valoracion AS val_programa, c.tipo,
       ROUND(vp.valoracion - vi.valoracion, 1) AS diferencia
FROM correspondencia c
JOIN nodo i ON i.id=c.origen_id JOIN marco mi ON mi.id=i.marco_id AND mi.codigo='CNA-INST'
JOIN nodo d ON d.id=c.destino_id JOIN marco md ON md.id=d.marco_id AND md.codigo='CNA'
LEFT JOIN v_valoracion_cna_inst vi ON vi.codigo=i.codigo
LEFT JOIN v_valoracion_cna vp ON vp.codigo=d.codigo
WHERE c.estado<>'descartada'
ORDER BY ABS(vp.valoracion - vi.valoracion) DESC;
