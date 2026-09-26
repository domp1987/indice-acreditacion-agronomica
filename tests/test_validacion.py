"""Tarea 5: decisiones del comité con auditoría y su interfaz web local."""
import shutil
import sqlite3
import threading
import urllib.parse
import urllib.request

import pytest

from indice.cargar import cargar
from indice.config import cargar_rutas
from indice.decisiones import DecisionInvalida, agregar_etiqueta, decidir_correspondencia, decidir_etiqueta
from indice.validacion import servidor

rutas = cargar_rutas()
pytestmark = pytest.mark.skipif(not rutas.db.exists() or not rutas.diapositivas.exists(), reason='falta la base (ejecuta indice todo)')

NODO = "(SELECT n.id FROM nodo n JOIN marco m ON m.id=n.marco_id WHERE m.codigo=? AND n.codigo=?)"


@pytest.fixture
def db(tmp_path):
    destino = tmp_path / 'base.sqlite'
    shutil.copy2(rutas.db, destino)
    return destino


def uno(con, sql, *a):
    return con.execute(sql, a).fetchone()


def test_decidir_etiqueta_queda_auditada(db):
    con = sqlite3.connect(db)
    eid, nid = uno(con, "SELECT evidencia_id, nodo_id FROM evidencia_nodo WHERE origen='inferida' AND estado='propuesta' LIMIT 1")
    decidir_etiqueta(con, eid, nid, 'validar', 'Ana', 'coincide con el criterio')
    assert uno(con, 'SELECT estado, validado_por FROM evidencia_nodo WHERE evidencia_id=? AND nodo_id=?', eid, nid) == ('validada', 'Ana')
    d = uno(con, 'SELECT validador, objeto, accion, estado_anterior, estado_nuevo, comentario FROM decision ORDER BY id DESC')
    assert d == ('Ana', 'etiqueta', 'validar', 'propuesta', 'validada', 'coincide con el criterio')
    decidir_etiqueta(con, eid, nid, 'reabrir', 'Ana')
    assert uno(con, 'SELECT estado, validado_por FROM evidencia_nodo WHERE evidencia_id=? AND nodo_id=?', eid, nid) == ('propuesta', None)
    assert uno(con, 'SELECT COUNT(*) FROM decision')[0] == 2


def test_validador_obligatorio(db):
    con = sqlite3.connect(db)
    cid = uno(con, 'SELECT id FROM correspondencia LIMIT 1')[0]
    with pytest.raises(DecisionInvalida, match='quien valida'):
        decidir_correspondencia(con, cid, 'validar', '  ')
    with pytest.raises(DecisionInvalida, match='Acción'):
        decidir_correspondencia(con, cid, 'aprobar', 'Ana')
    assert uno(con, 'SELECT COUNT(*) FROM decision')[0] == 0


def test_etiqueta_manual_en_evidencia_sin_etiquetas(db):
    con = sqlite3.connect(db)
    eid = uno(con, "SELECT id FROM evidencia WHERE codigo='PAD-CAD602020207'")[0]
    nid = uno(con, f'SELECT {NODO}', 'ABET-EAC', 'SO2')[0]
    agregar_etiqueta(con, eid, nid, 'principal', 'Comité', 'diseño de sistemas de riego')
    assert uno(con, 'SELECT origen, rol, estado, validado_por FROM evidencia_nodo WHERE evidencia_id=? AND nodo_id=?', eid, nid) == (
        'manual', 'principal', 'validada', 'Comité')
    assert uno(con, 'SELECT referencia, accion FROM decision')[0] == 'PAD-CAD602020207 → ABET-EAC/SO2'


def test_interfaz_web_de_punta_a_punta(db, tmp_path):
    srv = servidor(db, 0)
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    base = f'http://127.0.0.1:{srv.server_address[1]}'
    try:
        # Las páginas cargan
        for ruta in ['/', '/correspondencias', '/etiquetas?nodo=C6', '/evidencias?sin=1', '/evidencia?codigo=F05-P027', '/auditoria',
                     '/cursos', '/cursos?q=riego', '/curso?pad=CAD602020207&q=riego', '/curso?pad=CAD602020937']:
            with urllib.request.urlopen(base + ruta) as r:
                html = r.read().decode('utf-8')
                assert r.status == 200 and 'Validación del comité' in html, ruta
        # La búsqueda en los PAD encuentra el curso por el contenido de sus actividades
        with urllib.request.urlopen(base + '/cursos?q=riego') as r:
            assert 'HIDRAULICA' in r.read().decode('utf-8')
        # El texto de las evidencias se escapa (no se inyecta HTML)
        with urllib.request.urlopen(base + '/evidencia?codigo=%3Cscript%3E') as r:
            assert '<script>' not in r.read().decode('utf-8').split('</style>')[1].split('<script>document')[0]
        # Descartar una correspondencia desde el formulario retira sus inferidas y queda auditado
        con = sqlite3.connect(db)
        cid = uno(con, f'SELECT id FROM correspondencia WHERE origen_id={NODO} AND destino_id={NODO}', 'CNA', 'C10', 'ABET-EAC', 'C6')[0]
        antes = uno(con, "SELECT COUNT(*) FROM evidencia_nodo WHERE origen='inferida'")[0]
        con.close()
        datos = urllib.parse.urlencode({'objeto': 'correspondencia', 'item': f'c:{cid}', 'accion': 'descartar',
                                        'validador': 'Comité', 'comentario': 'número de docentes no equivale a C6', 'volver': '/correspondencias'}).encode()
        pedido = urllib.request.Request(base + '/decidir', data=datos, headers={'Origin': base})
        with urllib.request.urlopen(pedido) as r:
            assert 'registrada' in r.read().decode('utf-8')
        con = sqlite3.connect(db)
        assert uno(con, 'SELECT estado, validado_por FROM correspondencia WHERE id=?', cid) == ('descartada', 'Comité')
        assert uno(con, "SELECT COUNT(*) FROM evidencia_nodo WHERE origen='inferida'")[0] < antes
        assert uno(con, "SELECT COUNT(*) FROM decision WHERE objeto='correspondencia'")[0] == 1
        con.close()
        # Un formulario enviado desde otro sitio se rechaza
        ajeno = urllib.request.Request(base + '/decidir', data=datos, headers={'Origin': 'https://sitio-ajeno.example'})
        with pytest.raises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(ajeno)
        assert err.value.code == 403
    finally:
        srv.shutdown(); srv.server_close()
    # La decisión y la auditoría sobreviven a una recarga completa
    cargar(db, rutas.diapositivas, rutas.semillas, rutas.pptx_json, rutas.ocr_json, pads_json=rutas.pads_json)
    con = sqlite3.connect(db)
    assert uno(con, 'SELECT estado FROM correspondencia WHERE id=?', cid)[0] == 'descartada'
    assert uno(con, 'SELECT COUNT(*) FROM decision')[0] == 1
