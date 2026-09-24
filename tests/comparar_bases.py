"""Compara dos bases del índice por claves naturales (no por id interno).

Uso: python tests/comparar_bases.py legado/indice_acreditacion.sqlite salida/indice_acreditacion.sqlite
Devuelve {consulta: (solo_en_a, solo_en_b)} con las filas que difieren.
"""
import sqlite3
import sys

# Cada consulta devuelve filas sin ids internos; 'archivo' se omite porque cambió el nombre de los PDF
CONSULTAS = {
    'marco': "SELECT codigo,nombre,version,descripcion FROM marco",
    'nodo': """SELECT m.codigo,n.codigo,n.nombre,n.descripcion,n.tipo,p.codigo,n.orden FROM nodo n JOIN marco m ON m.id=n.marco_id
               LEFT JOIN nodo p ON p.id=n.padre_id""",
    'correspondencia': """SELECT o.codigo,d.codigo,c.tipo,c.estado,c.nota FROM correspondencia c JOIN nodo o ON o.id=c.origen_id
                          JOIN nodo d ON d.id=c.destino_id""",
    'evidencia': "SELECT codigo,titulo,tipo,fuente,pagina,sede,periodo,url_sharepoint,idioma,responsable,estado_revision FROM evidencia",
    'evidencia.texto': "SELECT codigo,texto FROM evidencia",
    'evidencia_nodo': """SELECT e.codigo,m.codigo,n.codigo,en.rol,en.origen,en.estado FROM evidencia_nodo en JOIN evidencia e ON e.id=en.evidencia_id
                         JOIN nodo n ON n.id=en.nodo_id JOIN marco m ON m.id=n.marco_id""",
    'indicador': "SELECT codigo,nombre,unidad,descripcion FROM indicador",
    'medicion': """SELECT i.codigo,md.periodo,md.sede,md.valor,md.desagregacion,e.codigo,md.nota FROM medicion md JOIN indicador i ON i.id=md.indicador_id
                   LEFT JOIN evidencia e ON e.id=md.evidencia_id""",
    'indicador_nodo': """SELECT i.codigo,m.codigo,n.codigo,x.rol FROM indicador_nodo x JOIN indicador i ON i.id=x.indicador_id
                         JOIN nodo n ON n.id=x.nodo_id JOIN marco m ON m.id=n.marco_id""",
    'curso': "SELECT nombre,componente_cma,creditos,periodo,categoria_abet,confianza,nota FROM curso",
    'curso_outcome': "SELECT c.nombre,n.codigo,co.nivel FROM curso_outcome co JOIN curso c ON c.id=co.curso_id JOIN nodo n ON n.id=co.nodo_id",
    'normativa': "SELECT tipo,numero,anio,organo FROM normativa",
    'normativa_mencion': """SELECT n.tipo,n.numero,n.anio,e.codigo FROM normativa_mencion x JOIN normativa n ON n.id=x.normativa_id
                            JOIN evidencia e ON e.id=x.evidencia_id""",
    'brecha': "SELECT n.codigo,b.titulo,b.descripcion,b.severidad,b.accion,b.responsable,b.estado FROM brecha b JOIN nodo n ON n.id=b.nodo_id",
    'v_cobertura_abet': "SELECT * FROM v_cobertura_abet",
    'v_creditos_abet': "SELECT * FROM v_creditos_abet",
    'v_inconsistencias': "SELECT * FROM v_inconsistencias",
}


def filas(db, sql):
    con = sqlite3.connect(db)
    try:
        return sorted(con.execute(sql).fetchall(), key=repr)
    finally:
        con.close()


def comparar(db_a, db_b):
    difs = {}
    for nombre, sql in CONSULTAS.items():
        a, b = filas(db_a, sql), filas(db_b, sql)
        solo_a = [r for r in a if r not in b]; solo_b = [r for r in b if r not in a]
        if solo_a or solo_b:
            difs[nombre] = (solo_a, solo_b)
    return difs


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    difs = comparar(sys.argv[1], sys.argv[2])
    for nombre in CONSULTAS:
        if nombre not in difs:
            print(f'= {nombre}')
            continue
        solo_a, solo_b = difs[nombre]
        print(f'≠ {nombre}: {len(solo_a)} solo en A, {len(solo_b)} solo en B')
        for r in solo_a[:5]: print('   A', repr(r)[:240])
        for r in solo_b[:5]: print('   B', repr(r)[:240])
