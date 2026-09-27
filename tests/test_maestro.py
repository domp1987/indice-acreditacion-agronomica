"""Documento maestro RRC 2025: secciones como evidencias, plan de estudios propuesto y REA del programa."""
import json
import sqlite3

import pytest

from indice.config import cargar_rutas
from indice.maestro import plan_2025, rea_por_cadi, transicion_2025

rutas = cargar_rutas()
pytestmark = pytest.mark.skipif(not rutas.maestro_json.exists(), reason='falta salida/maestro.json (ejecuta indice maestro)')


@pytest.fixture(scope='module')
def datos():
    return json.loads(rutas.maestro_json.read_text(encoding='utf-8'))


def test_secciones_con_pagina(datos):
    secciones = {s['codigo']: s for s in datos['secciones']}
    assert len(secciones) >= 120
    assert secciones['DM-4.6']['pagina'] == 140 and 'Resultados de Aprendizaje' in secciones['DM-4.6']['titulo']
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


@pytest.mark.skipif(not rutas.db.exists(), reason='falta la base')
def test_maestro_en_la_base():
    con = sqlite3.connect(rutas.db)
    n = lambda q: con.execute(q).fetchone()[0]
    assert n("SELECT COUNT(*) FROM evidencia WHERE tipo='documento_maestro'") >= 120
    assert n("SELECT COUNT(*) FROM tabla_diapositiva WHERE leyenda LIKE 'Tabla 23.%'") == 1
    assert n('SELECT COUNT(*) FROM v_plan_2025_inconsistencias') == 5
    assert n("SELECT COUNT(*) FROM nodo n JOIN marco m ON m.id=n.marco_id WHERE m.codigo='REA-IA-2025'") == 3
    # 'de acuerdo con el decreto 1330' no se toma como un Acuerdo
    assert n('SELECT COUNT(*) FROM normativa WHERE numero IN (1330, 1279)') == 0
    con.close()
