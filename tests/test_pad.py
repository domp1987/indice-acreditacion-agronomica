"""Extracción de los Planes de Aprendizaje Digital (PAD) en sus dos plantillas y su carga en la base."""
import sqlite3

import pytest

from indice.config import cargar_rutas
from indice.extraer import binario
from indice.pad import leer_pad
from indice.semillas import leer_todas

rutas = cargar_rutas()
V19 = rutas.pads / 'PAD V1.9' / 'PAD CAD602020105 FISICA V1.9.pdf'
V2 = rutas.pads / 'PAD V1.9' / 'PAD CAD602020937 OPCION DE GRADO.pdf'
pytestmark = pytest.mark.skipif(not V19.exists() or not binario('pdftotext', rutas.poppler),
                                reason='faltan los PAD o poppler')


def test_plantilla_v19():
    p = leer_pad(V19)
    assert (p['plantilla'], p['codigo'], p['creditos'], p['semestre']) == ('V1.9', 'CAD602020105', 2, 1)
    assert [r['consecutivo'] for r in p['rea']] == [1, 2, 3]
    assert [e['tipo'] for e in p['experiencias']] == ['vive_experiencia', 'vive_experiencia', 'soluciona_problema']
    acts = [a for e in p['experiencias'] for a in e['actividades']]
    assert len(acts) == 10
    primera = acts[0]
    assert primera['semana_inicio'] == 'Semana 1' and primera['duracion'] == '2 semanas'
    assert primera['lugares'] == ['(F-305) - AULA DE CLASE'] and primera['instrumentos'] == ['Tarea']
    assert p['experiencias'][0]['dimensiones'] == ['Cultura', 'Institución', 'Aula', 'Naturaleza']
    assert [a['etapa'] for a in p['experiencias'][2]['actividades']] == [
        'Analicemos el problema', 'Planifiquemos en equipo', 'Solucionemos el problema', 'Evidenciemos soluciones']
    assert len(p['bibliografia']) >= 19 and len(p['recursos']) == 11
    assert 'RECURSOS CGCA' not in (p['acciones'].get('transformaciones') or '')   # la bibliografía no se cuela
    # Privacidad: el nombre del profesor líder no se extrae a ningún campo estructurado
    assert 'MÉNDEZ' not in str({k: v for k, v in p.items() if k != 'texto'})


def test_plantilla_v2():
    p = leer_pad(V2)
    assert (p['plantilla'], p['codigo'], p['creditos'], p['semestre']) == ('V2', 'CAD602020937', 1, 9)
    assert [e['nombre'] for e in p['experiencias']] == [
        '¡Labrando el terreno para la siembra!', 'A sembrar, cuidar y cosechar', '¡A cosechar y vender lo producido!']
    acts = [a for e in p['experiencias'] for a in e['actividades']]
    assert [a['semana_inicio'] for a in acts] == ['Semana 1', 'Semana 2', 'Semana 3', 'Semana 5', 'Semana 8', 'Semana 12', 'Semana 14']
    assert all(a.get('instrumentos') for a in acts)
    assert len(p['bibliografia']) == 10 and p['bibliografia'][0]['anio'] == 2016


def test_todos_los_pad_estan_relacionados():
    semillas = leer_todas(rutas.semillas)
    relacion = {x['pad'] for x in semillas['pad_curso']}
    if not rutas.pads_json.exists(): pytest.skip('falta salida/pads.json')
    import json
    pads = json.loads(rutas.pads_json.read_text(encoding='utf-8'))
    assert len(pads) == 69   # 53 disciplinares y de especialización + 16 de los CAI institucionales (7 en Word)
    assert {p['codigo'] for p in pads} <= relacion


@pytest.mark.skipif(not rutas.db.exists(), reason='falta la base')
def test_pad_en_la_base():
    con = sqlite3.connect(rutas.db)
    n = lambda q: con.execute(q).fetchone()[0]
    assert n('SELECT COUNT(*) FROM pad') == 69
    assert n("SELECT COUNT(*) FROM evidencia WHERE tipo='pad'") == 69
    assert n("SELECT COUNT(*) FROM v_pad_curso WHERE estado='créditos distintos'") == 0
    assert n("SELECT COUNT(DISTINCT curso) FROM v_pad_curso WHERE estado='ok'") == 50
    # el período lo da la ruta v4 para los 54 cursos, y el semestre de cada PAD del plan coincide con él
    assert n('SELECT COUNT(*) FROM curso WHERE periodo IS NOT NULL') == 54
    # solo difiere el PAD de Cátedra Generación Siglo 21 (sexto semestre; la ruta v4 lo ubica en el séptimo)
    assert [c for (c,) in con.execute('SELECT c.nombre FROM pad p JOIN curso c ON c.id=p.curso_id WHERE p.semestre <> c.periodo')] == ['Cátedra Generación Siglo 21']
    assert n('SELECT COUNT(*) FROM curso_prerrequisito') == 34
    # Con los PAD de los CAI solo quedan sin PAD cuatro cursos institucionales (de ellos solo llegó el nivelatorio)
    assert {c for (c,) in con.execute("SELECT curso FROM v_pad_curso WHERE estado='sin PAD'")} == {
        'Ciudadanía siglo 21', 'Emprendimiento e innovación I', 'Emprendimiento e innovación II', 'Lengua extranjera II'}
    con.close()


V2026 = rutas.pads / 'Hidraulica CAD602020207.pdf'


@pytest.mark.skipif(not V2026.exists(), reason='falta el PAD de Hidráulica')
def test_variante_2026_por_semanas():
    p = leer_pad(V2026)
    assert (p['codigo'], p['creditos'], p['semestre'], p['relacion_creditos']) == ('CAD602020207', 3, 2, '1-2')
    assert [r['peso'] for r in p['rea']] == [32.0, 36.0, 32.0]
    assert all(len(r['texto']) < 400 for r in p['rea'])   # la tabla de fases del MCA no se cuela en el REA
    assert [f['fase'].split('.')[0] for f in p['fases']] == [f'Fase {i}' for i in range(1, 10)]
    acts = [a for e in p['experiencias'] for a in e['actividades']]
    assert len(acts) == 8 and all(a.get('descripcion') for a in acts)
    primera = acts[0]
    assert primera['lugares'] == ['LABORATORIO', 'EN CUNDINAMARCA'] and primera['instrumentos'] == ['Tarea']
    assert primera['fase'] == 'FASE 4. PARTICIPACIÓN; FASE 5. COLABORACIÓN Y COCREACIÓN'
    assert '[Semana 2]' in primera['descripcion_instrumentos']        # lo evaluado en la segunda semana
    assert len(p['bibliografia']) >= 14 and p['bibliografia'][0]['url'].startswith('https://')
