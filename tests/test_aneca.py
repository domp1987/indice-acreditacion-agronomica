"""Marco ANECA (sello EUR-ACE): criterios, áreas de resultados EUR-ACE y estructura frente a la Orden CIN/323/2009."""
import sqlite3

import pytest

from indice.config import cargar_rutas

rutas = cargar_rutas()
pytestmark = pytest.mark.skipif(not rutas.db.exists(), reason='falta la base (ejecuta indice todo)')


@pytest.fixture(scope='module')
def con():
    c = sqlite3.connect(rutas.db)
    yield c
    c.close()


def test_criterios_y_resultados(con):
    tipos = dict(con.execute("""SELECT x.tipo, COUNT(*) FROM nodo x JOIN marco m ON m.id=x.marco_id
                                WHERE m.codigo='ANECA-EURACE' GROUP BY x.tipo""").fetchall())
    assert tipos == {'criterio': 9, 'outcome': 8}
    # los criterios de gestión y recursos tienen evidencia CNA; el escenario DM25 no aporta
    cob = {c: p + a for c, _, _, _, p, a, _ in con.execute('SELECT * FROM v_cobertura_aneca')}
    assert all(cob[c] > 0 for c in ('E1', 'E3', 'E4', 'E5', 'E7', 'E9'))
    assert con.execute("""SELECT COUNT(*) FROM evidencia_nodo en JOIN evidencia e ON e.id=en.evidencia_id JOIN nodo x ON x.id=en.nodo_id
        JOIN marco m ON m.id=x.marco_id AND m.codigo='ANECA-EURACE' WHERE e.nivel='escenario' OR en.estado='validada'""").fetchone()[0] == 0


def test_estructura_frente_a_la_orden_cin(con):
    m = {mod: (cr, ects, mi) for mod, cr, ects, _, mi in con.execute('SELECT * FROM v_creditos_aneca')}
    assert sum(cr for cr, _, _ in m.values()) == 150 and sum(e for _, e, _ in m.values()) == 240   # 240 ECTS, como un grado español
    assert m['basico'][1] < 60 and m['tfg'][1] < 12            # brechas: formación básica y trabajo fin de grado
    assert m['comun_agricola'][1] >= 60 and m['tecnologia_especifica'][1] >= 48


def test_brechas(con):
    b = {c for (c,) in con.execute("""SELECT x.codigo FROM brecha b JOIN nodo x ON x.id=b.nodo_id JOIN marco m ON m.id=x.marco_id
                                      WHERE m.codigo='ANECA-EURACE'""")}
    assert {'E8', 'E8.1', 'E8.3', 'E4', 'E7'} <= b
