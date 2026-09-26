"""Genera data.json (insumo del tablero) y una tabla por CSV (UTF-8 con BOM, para Excel o Power BI)."""
import csv
import json
import sqlite3
import zipfile
from pathlib import Path

TABLAS = ['marco', 'nodo', 'correspondencia', 'evidencia', 'evidencia_nodo', 'indicador', 'medicion', 'indicador_nodo',
          'curso', 'curso_outcome', 'normativa', 'normativa_mencion', 'brecha', 'grafica', 'grafica_dato', 'tabla_diapositiva',
          'pad', 'pad_rea', 'pad_fase', 'pad_experiencia', 'pad_actividad', 'pad_bibliografia', 'pad_recurso', 'decision']


def datos_tablero(c):
    q = lambda s, *a: [dict(r) for r in c.execute(s, a)]
    abet = q("""SELECT n.id,n.codigo,n.nombre,n.tipo,n.descripcion,p.codigo padre FROM nodo n LEFT JOIN nodo p ON p.id=n.padre_id
                JOIN marco m ON m.id=n.marco_id AND m.codigo='ABET-EAC' ORDER BY n.orden""")
    for a in abet:
        a['ev'] = q("""SELECT e.codigo,en.rol,en.origen FROM evidencia_nodo en JOIN evidencia e ON e.id=en.evidencia_id
                       WHERE en.nodo_id=? AND en.estado<>'descartada' AND e.estado_revision<>'obsoleta'
                       ORDER BY CASE en.rol WHEN 'principal' THEN 0 WHEN 'parcial' THEN 1 ELSE 2 END, e.codigo""", a['id'])
        a['fuentes'] = q("""SELECT o.codigo,o.nombre,m.codigo marco,c.tipo,c.nota FROM correspondencia c JOIN nodo o ON o.id=c.origen_id JOIN marco m ON m.id=o.marco_id
                            WHERE c.destino_id=? ORDER BY m.id,o.codigo""", a['id'])
        a['brechas'] = q("SELECT titulo,descripcion,severidad,accion,estado FROM brecha WHERE nodo_id=?", a['id'])
        a['indicadores'] = q("SELECT i.codigo,i.nombre FROM indicador_nodo x JOIN indicador i ON i.id=x.indicador_id WHERE x.nodo_id=?", a['id'])
    cna = q("""SELECT n.codigo,n.nombre,n.tipo,p.codigo padre FROM nodo n LEFT JOIN nodo p ON p.id=n.padre_id
               JOIN marco m ON m.id=n.marco_id AND m.codigo='CNA' ORDER BY n.orden""")
    ev = q("SELECT id,codigo,titulo,tipo,texto,texto_ocr,fuente,archivo,pagina FROM evidencia WHERE estado_revision<>'obsoleta' ORDER BY codigo")
    tags = {}
    for r in q("SELECT en.evidencia_id,n.codigo,m.codigo marco,en.rol,en.origen FROM evidencia_nodo en JOIN nodo n ON n.id=en.nodo_id JOIN marco m ON m.id=n.marco_id"):
        tags.setdefault(r['evidencia_id'], []).append([r['marco'], r['codigo'], r['rol'], r['origen']])
    for e in ev:
        e['tags'] = tags.get(e.pop('id'), [])
        ocr = e.pop('texto_ocr')
        # El tablero muestra y busca en 'texto'; el OCR se agrega al final, marcado, para que también se encuentre
        e['texto'] = (e['texto'] or '')[:2200] + (f'\n[Texto en imágenes (OCR)]\n{ocr[:800]}' if ocr else '')
    ind = q("SELECT id,codigo,nombre,unidad FROM indicador")
    for i in ind:
        i['m'] = q("SELECT periodo,sede,valor,desagregacion d,nota FROM medicion WHERE indicador_id=? ORDER BY id", i.pop('id'))
    return dict(
        abet=abet, cna=cna, evidencias=ev, indicadores=ind,
        cursos=q("SELECT nombre,componente_cma,creditos,categoria_abet,confianza,nota FROM curso ORDER BY id"),
        inconsistencias=q("SELECT * FROM v_inconsistencias"),
        normativa=q("""SELECT n.tipo,n.numero,n.anio,n.organo,GROUP_CONCAT(e.codigo) evs FROM normativa n JOIN normativa_mencion m ON m.normativa_id=n.id
                       JOIN evidencia e ON e.id=m.evidencia_id GROUP BY n.id ORDER BY n.anio DESC,n.numero"""),
        brechas=q("""SELECT n.codigo nodo,b.titulo,b.descripcion,b.severidad,b.accion,b.estado FROM brecha b JOIN nodo n ON n.id=b.nodo_id
                     ORDER BY CASE b.severidad WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END"""),
        rea=q("SELECT n.codigo,n.descripcion FROM nodo n JOIN marco m ON m.id=n.marco_id AND m.codigo='REA-IA' ORDER BY n.orden"))


def exportar(db, data_json, carpeta_csv, csv_zip):
    db = Path(db)
    if not db.exists():
        raise SystemExit(f'No existe {db}. Ejecuta primero: indice cargar')
    c = sqlite3.connect(db); c.row_factory = sqlite3.Row
    try:
        data_json = Path(data_json)
        data_json.write_text(json.dumps(datos_tablero(c), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        carpeta_csv = Path(carpeta_csv); carpeta_csv.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(csv_zip, 'w', zipfile.ZIP_DEFLATED) as z:
            for t in TABLAS:
                cur = c.execute(f"SELECT * FROM {t}")
                archivo = carpeta_csv / f'{t}.csv'
                with open(archivo, 'w', newline='', encoding='utf-8-sig') as f:
                    w = csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(cur.fetchall())
                z.write(archivo, archivo.name)
        print(f'Exportación: {data_json} ({data_json.stat().st_size // 1024} KB), {len(TABLAS)} CSV → {csv_zip}')
    finally:
        c.close()
