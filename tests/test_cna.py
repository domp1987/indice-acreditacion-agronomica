"""Análisis CNA de alta calidad: valoraciones de la autoevaluación, grado inferido y riesgo de sobrevaloración."""
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


def test_valoraciones_y_grado(con):
    filas = con.execute('SELECT codigo, valoracion, grado FROM v_valoracion_cna').fetchall()
    assert len(filas) == 48 and all(v is not None for _, v, _ in filas)
    # la escala inferida coincide con la de los informes del programa
    assert all((g == 'Se cumple plenamente') == (v >= 4.5) for _, v, g in filas)
    assert min(v for _, v, _ in filas) == 3.7 and dict((c, v) for c, v, _ in filas)['C09'] == 3.7


def test_riesgo_de_sobrevaloracion(con):
    riesgo = dict(con.execute('SELECT codigo, riesgo_sobrevaloracion FROM v_valoracion_cna'))
    assert riesgo['C10'] == 'alto'          # profesorado: 4,5 en la autoevaluación, brechas altas en ABET, ATMAE y ANECA
    assert riesgo['C09'] == 'bajo'          # valoración baja: no hay sobrevaloración que advertir
    # solo cuentan brechas del nodo de destino por correspondencias equivalentes o parciales
    assert riesgo['C33'] == 'bajo'


def test_brechas_cna(con):
    b = {c for (c,) in con.execute("""SELECT x.codigo FROM brecha b JOIN nodo x ON x.id=b.nodo_id JOIN marco m ON m.id=x.marco_id
                                      WHERE m.codigo='CNA'""")}
    assert {'C10', 'C23', 'C27', 'F01'} <= b
