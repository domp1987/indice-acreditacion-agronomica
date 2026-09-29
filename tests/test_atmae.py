"""Marco ATMAE 2027: estándares, estructura curricular (3.1), reproyección y recursos de Jardín Vivo RA."""
import sqlite3

import pytest

from indice.config import cargar_rutas
from indice.recursos_ra import leer_glb, leer_jpeg

rutas = cargar_rutas()
pytestmark = pytest.mark.skipif(not rutas.db.exists(), reason='falta la base (ejecuta indice todo)')


@pytest.fixture(scope='module')
def con():
    c = sqlite3.connect(rutas.db)
    yield c
    c.close()


def test_estandares(con):
    n = lambda q: con.execute(q).fetchone()[0]
    assert n("SELECT COUNT(*) FROM nodo x JOIN marco m ON m.id=x.marco_id WHERE m.codigo='ATMAE-2027' AND x.tipo='criterio'") == 12
    # sin evidencia: comité asesor (reglamento, lista, actas) y seguridad; cada uno con brecha abierta
    sin = {c for (c,) in con.execute('SELECT codigo FROM v_cobertura_atmae WHERE principales+parciales+apoyo=0 AND tipo=\'subcriterio\'')}
    assert {'A6.3', 'A10.1', 'A10.3', 'A10.4'} <= sin
    assert n("SELECT COUNT(*) FROM brecha b JOIN nodo x ON x.id=b.nodo_id JOIN marco m ON m.id=x.marco_id WHERE m.codigo='ATMAE-2027'") >= 10


def test_estructura_curricular(con):
    areas = {a: (cr, mi, ma) for a, cr, _, mi, ma in con.execute('SELECT * FROM v_creditos_atmae')}
    assert sum(cr for cr, _, _ in areas.values()) == 150
    assert all(cr >= mi for cr, mi, _ in areas.values())            # se cumplen todos los mínimos
    assert areas['gestion_tecnica'][0] > 60 and areas['ciencias'][0] > 18   # exceden el máximo: requieren justificación
    assert con.execute("SELECT SUM(creditos) FROM curso WHERE categoria_atmae='gestion'").fetchone()[0] <= 24


def test_reproyeccion_no_usa_el_escenario(con):
    n = lambda q: con.execute(q).fetchone()[0]
    atmae = "JOIN nodo x ON x.id=en.nodo_id JOIN marco m ON m.id=x.marco_id AND m.codigo='ATMAE-2027'"
    assert n(f"SELECT COUNT(*) FROM evidencia_nodo en {atmae} JOIN evidencia e ON e.id=en.evidencia_id WHERE e.nivel='escenario'") == 0
    assert n(f"SELECT COUNT(*) FROM evidencia_nodo en {atmae} JOIN evidencia e ON e.id=en.evidencia_id WHERE e.nivel='complementaria' AND en.rol<>'apoyo'") == 0
    assert n(f"SELECT COUNT(*) FROM evidencia_nodo en {atmae} WHERE en.estado='validada'") == 0


def test_recursos_ra(con):
    ra = {c: t for c, t in con.execute("SELECT codigo, texto FROM evidencia WHERE codigo LIKE 'RA-%'")}
    if not ra: pytest.skip('sin recursos de Jardín Vivo RA')
    assert set(ra) == {'RA-MODELOS', 'RA-MODELOS-AR', 'RA-360'}
    tags = {x for (x,) in con.execute("""SELECT x.codigo FROM evidencia_nodo en JOIN evidencia e ON e.id=en.evidencia_id
        JOIN nodo x ON x.id=en.nodo_id WHERE e.codigo='RA-360'""")}
    assert {'C21', 'A3.3', 'A6.1', 'A7.2'} <= tags   # laboratorio virtual, equipos y recursos


def test_lectores_binarios(tmp_path):
    import json, struct
    js = json.dumps({'asset': {'generator': 'prueba'}, 'accessors': [{'count': 3, 'min': [0, 0, 0], 'max': [1, 2, 0]}, {'count': 3}],
                     'meshes': [{'primitives': [{'attributes': {'POSITION': 0}, 'indices': 1}]}]}).encode()
    js += b' ' * (-len(js) % 4)
    glb = tmp_path / 'm.glb'
    glb.write_bytes(b'glTF' + struct.pack('<II', 2, 12 + 8 + len(js)) + struct.pack('<I4s', len(js), b'JSON') + js)
    g = leer_glb(glb)
    assert g['vertices'] == 3 and g['triangulos'] == 1 and g['generador'] == 'prueba' and g['dimensiones'] == [1, 2, 0]
    jpg = tmp_path / 'f.jpg'
    jpg.write_bytes(b'\xff\xd8' + b'\xff\xc0' + struct.pack('>HBHH', 11, 8, 3008, 6016) + b'\x03\x01\x11\x00' + b'\xff\xd9')
    assert leer_jpeg(jpg) == {'ancho': 6016, 'alto': 3008, 'equirectangular': True}
