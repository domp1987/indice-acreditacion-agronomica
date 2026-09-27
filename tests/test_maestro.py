"""Documentos maestros (RRC 2025 para la resignificación, 2019 para la acreditación): secciones como evidencias,
plan de estudios propuesto y REA del programa."""
import json
import sqlite3

import pytest

from indice.config import cargar_rutas
from indice.maestro import plan_2025, rea_por_cadi, transicion_2025

rutas = cargar_rutas()
DM25, DM19 = rutas.salida / 'maestro_DM25.json', rutas.salida / 'maestro_DM19.json'
pytestmark = pytest.mark.skipif(not DM25.exists(), reason='falta salida/maestro_DM25.json (ejecuta indice maestro)')


@pytest.fixture(scope='module')
def datos():
    return json.loads(DM25.read_text(encoding='utf-8'))


def test_secciones_con_pagina(datos):
    secciones = {s['codigo']: s for s in datos['secciones']}
    assert len(secciones) >= 120
    assert secciones['DM25-4.6']['pagina'] == 140 and 'Resultados de Aprendizaje' in secciones['DM25-4.6']['titulo']
    assert sum(len(s['tablas']) for s in datos['secciones']) == 81
    # La portada (por error, de Robótica y Automatización) es una imagen: no aporta texto
    assert not any('Robótica' in p for s in datos['secciones'] for p in s['parrafos'])


def test_plan_2025(datos):
    plan = plan_2025(datos)
    assert sum(x['creditos'] for x in plan) == 150
    assert sum(x['creditos'] for x in plan if x['tipo'] == 'institucional') == 27
    por_periodo = {p: sum(x['creditos'] for x in plan if x['periodo'] == p) for p in range(1, 10)}
    assert por_periodo == {1: 17, 2: 17, 3: 18, 4: 18, 5: 18, 6: 18, 7: 18, 8: 17, 9: 9}
    nombres = {x['nombre'] for x in plan}
    assert {'Matemática Agrícola I', 'Matemática Agrícola II', 'Bioestadística', 'Hidráulica'} <= nombres


def test_transicion_y_rea(datos):
    t = transicion_2025(datos)
    assert len(t) == 34
    mat = [x for x in t if x['curso_vigente'] == 'Matemática Aplicada']
    assert [x['curso_propuesto'] for x in mat] == ['Matemáticas Agrícolas I', 'Matemáticas Agrícolas II']
    rea = rea_por_cadi(datos)
    assert len({x['codigo_cadi'] for x in rea}) == 38


@pytest.mark.skipif(not DM19.exists(), reason='falta salida/maestro_DM19.json')
def test_maestro_2019():
    d = json.loads(DM19.read_text(encoding='utf-8'))
    assert d['proceso'] == 'acreditacion' and len(d['secciones']) >= 110
    secciones = {s['codigo']: s for s in d['secciones']}
    # sus 5 REA específicos son los del marco REA-IA de las semillas
    rea = [p for p in secciones['DM19-3.2.2']['parrafos'] if p.lstrip('• ').startswith(('Aplicar', 'Desempeñarse', 'Identificar', 'Liderar'))]
    assert len(rea) == 5
    # el plan 2020 (Tabla 12) suma 150 créditos, como la tabla curso
    filas = [f for t in secciones['DM19-3.3.2']['tablas'] for f in t['filas']]
    total = next(f for f in filas if f[0].startswith('Total, Número Créditos'))
    assert total[3] == '150'


@pytest.mark.skipif(not rutas.db.exists(), reason='falta la base')
def test_maestro_en_la_base():
    con = sqlite3.connect(rutas.db)
    n = lambda q: con.execute(q).fetchone()[0]
    assert n("SELECT COUNT(*) FROM evidencia WHERE tipo='documento_maestro' AND proceso='resignificacion'") >= 120
    assert n("SELECT COUNT(*) FROM evidencia WHERE tipo='documento_maestro' AND proceso='acreditacion'") == 107
    assert n("SELECT COUNT(*) FROM evidencia WHERE proceso IS NULL AND estado_revision != 'obsoleta'") == 0
    assert n("SELECT COUNT(*) FROM tabla_diapositiva t JOIN evidencia e ON e.id=t.evidencia_id WHERE e.codigo LIKE 'DM25-%' AND t.leyenda LIKE 'Tabla 23.%'") == 1
    assert n('SELECT COUNT(*) FROM v_plan_2025_inconsistencias') == 5
    assert n("SELECT COUNT(*) FROM nodo n JOIN marco m ON m.id=n.marco_id WHERE m.codigo='REA-IA-2025'") == 3
    # 'de acuerdo con el decreto 1330' no se toma como un Acuerdo
    assert n('SELECT COUNT(*) FROM normativa WHERE numero IN (1330, 1279)') == 0
    con.close()


@pytest.mark.skipif(not rutas.db.exists(), reason='falta la base')
def test_documentos_etiquetados_por_seccion():
    con = sqlite3.connect(rutas.db)
    n = lambda q: con.execute(q).fetchone()[0]
    # solo portadas y bibliografías quedan sin etiqueta CNA
    sin = {c for (c,) in con.execute("""SELECT codigo FROM evidencia e WHERE tipo IN ('documento_maestro','anexo')
        AND NOT EXISTS (SELECT 1 FROM evidencia_nodo WHERE evidencia_id=e.id)""")}
    assert sin == {'DM19-PORTADA', 'DM19-BIBLIOGRAFIA', 'DM25-PORTADA', 'DM25-REFERENCIAS-BIBLIOGRAFICAS'}
    # las etiquetas por sección nacen propuestas (las decide el comité) y la subsección hereda la de su padre
    assert n("""SELECT COUNT(*) FROM evidencia_nodo en JOIN evidencia e ON e.id=en.evidencia_id
        WHERE e.tipo IN ('documento_maestro','anexo') AND en.estado='validada'""") == 0
    tags = lambda c: {x for (x,) in con.execute("""SELECT n.codigo FROM evidencia_nodo en JOIN evidencia e ON e.id=en.evidencia_id
        JOIN nodo n ON n.id=en.nodo_id WHERE e.codigo=?""", (c,))}
    assert {'C23', 'C24'} <= tags('DM19-3.2.2') and 'C31' in tags('AX-46-34') and 'C11' in tags('DM25-8.4.2')
    # base ABET = presentaciones CNA, PAD y DM19; anexos complementarios (solo apoyo); DM25 escenario (sin ABET)
    assert n("SELECT COUNT(*) FROM evidencia WHERE nivel='principal'") == 452
    assert n("SELECT COUNT(*) FROM evidencia WHERE codigo LIKE 'DM19-%' AND nivel<>'principal'") == 0
    abet = lambda nivel, extra='': n(f"""SELECT COUNT(*) FROM evidencia_nodo en JOIN evidencia e ON e.id=en.evidencia_id
        JOIN nodo x ON x.id=en.nodo_id JOIN marco m ON m.id=x.marco_id AND m.codigo='ABET-EAC' WHERE e.nivel='{nivel}' {extra}""")
    assert abet('escenario') == 0 and abet('complementaria') > 0 and abet('complementaria', "AND en.rol<>'apoyo'") == 0
    # si todas las etiquetas de origen son 'apoyo', las inferidas también lo son
    assert n("""SELECT COUNT(*) FROM evidencia_nodo i JOIN evidencia e ON e.id=i.evidencia_id
        WHERE e.tipo='anexo' AND i.origen='inferida' AND i.rol<>'apoyo'
        AND NOT EXISTS (SELECT 1 FROM evidencia_nodo x WHERE x.evidencia_id=i.evidencia_id AND x.origen='extraccion' AND x.rol<>'apoyo')""") == 0
    con.close()
