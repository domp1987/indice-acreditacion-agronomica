"""Matriz cursos × Student Outcomes: propuestas desde los PAD y respeto de las decisiones del comité."""
import csv
import shutil
import sqlite3

import pytest

from indice.config import cargar_rutas
from indice.outcomes import actualizar_semilla, leer_semilla, proponer

rutas = cargar_rutas()
pytestmark = pytest.mark.skipif(not rutas.db.exists(), reason='falta la base (ejecuta indice todo)')


def test_propuestas_con_justificacion():
    p = proponer(rutas.db)
    assert len(p) > 100
    assert {f['estado'] for f in p.values()} == {'propuesta'}   # nunca se valida desde código
    assert all(f['justificacion'] for f in p.values())
    # E solo en los períodos 7–9 y sostenida por un REA del PAD
    con = sqlite3.connect(rutas.db)
    periodo = dict(con.execute('SELECT nombre, periodo FROM curso'))
    assert all(periodo[f['curso']] >= 7 and 'REA' in f['justificacion'] for f in p.values() if f['nivel'] == 'E')
    # los cursos sin PAD solo reciben propuestas por el nombre, con puntaje 0
    sin_pad = {c for (c,) in con.execute('SELECT nombre FROM curso c WHERE NOT EXISTS (SELECT 1 FROM pad WHERE curso_id=c.id)')}
    assert all(f['origen'] == 'nombre' and f['puntaje'] == 0 for f in p.values() if f['curso'] in sin_pad)
    assert p[('Comunicación y lectura crítica I', 'SO3')]['nivel'] == 'I'


def test_conserva_decisiones_del_comite(tmp_path):
    semilla = tmp_path / 'curso_outcomes.csv'
    shutil.copy2(rutas.semillas / 'curso_outcomes.csv', semilla)
    filas = leer_semilla(semilla)
    # el comité valida una, descarta otra y agrega una manual
    filas[0].update(estado='validada', nivel='R', validado_por='comité')
    filas[1].update(estado='descartada', validado_por='comité')
    filas.append(dict(curso='Física', outcome='SO7', nivel='I', estado='propuesta', origen='manual', puntaje='',
                      justificacion='agregada por el comité', validado_por=''))
    with semilla.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]), lineterminator='\n'); w.writeheader(); w.writerows(filas)
    actualizar_semilla(rutas.db, semilla)
    nuevas = {(r['curso'], r['outcome']): r for r in leer_semilla(semilla)}
    assert nuevas[(filas[0]['curso'], filas[0]['outcome'])]['estado'] == 'validada'
    assert nuevas[(filas[0]['curso'], filas[0]['outcome'])]['nivel'] == 'R'
    assert nuevas[(filas[1]['curso'], filas[1]['outcome'])]['estado'] == 'descartada'
    assert nuevas[('Física', 'SO7')]['origen'] == 'manual'
    assert len(nuevas) == len(filas)


def test_matriz_en_la_base():
    con = sqlite3.connect(rutas.db)
    n = lambda q: con.execute(q).fetchone()[0]
    assert n('SELECT COUNT(*) FROM curso_outcome') == len(leer_semilla(rutas.semillas / 'curso_outcomes.csv'))
    assert n("SELECT COUNT(*) FROM curso_outcome WHERE estado='validada' AND validado_por IS NULL") == 0
    assert n("SELECT COUNT(DISTINCT n.codigo) FROM curso_outcome co JOIN nodo n ON n.id=co.nodo_id") == 7
