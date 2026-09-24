"""Prueba de aceptación de la tarea 1: el flujo completo corre desde una carpeta limpia con un solo comando.

Requiere los PDF (ruta de indice.toml) y poppler; si faltan, las pruebas se omiten.
Las pruebas del modelo de datos (tarea 4) irán en archivos aparte.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

from indice.cli import main
from indice.config import PROYECTO, cargar_rutas
from indice.extraer import _binario

sys.path.insert(0, str(Path(__file__).parent))
from comparar_bases import comparar  # noqa: E402

rutas = cargar_rutas()
LEGADO = PROYECTO / 'legado' / 'indice_acreditacion.sqlite'

pytestmark = pytest.mark.skipif(
    not rutas.pdf.exists() or not _binario('pdftotext', rutas.poppler),
    reason='faltan los PDF de factores o poppler (pdftotext)')


@pytest.fixture(scope='module')
def salida(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp('salida')
    assert main(['todo', '--salida', str(carpeta), '--motor', 'pdftotext']) == 0
    return carpeta


def test_genera_todos_los_productos(salida):
    for nombre in ['diapositivas.json', 'indice_acreditacion.sqlite', 'data.json', 'tablas_csv.zip', 'indice_acreditacion_abet.html']:
        assert (salida / nombre).stat().st_size > 0, nombre
    html = (salida / 'indice_acreditacion_abet.html').read_text(encoding='utf-8')
    assert '__DATA__' not in html


def test_conteos_del_prototipo(salida):
    con = sqlite3.connect(salida / 'indice_acreditacion.sqlite')
    n = lambda q: con.execute(q).fetchone()[0]
    assert n('SELECT COUNT(*) FROM evidencia') == 240
    assert n('SELECT COUNT(*) FROM evidencia_nodo') == 492
    assert n('SELECT COUNT(*) FROM nodo') == 89
    assert n('SELECT COUNT(*) FROM medicion') == 227   # 224 del prototipo + 3 de la corrección de F04-P006
    assert n('SELECT COUNT(*) FROM curso') == 54
    assert n('SELECT SUM(creditos) FROM curso') == 150
    con.close()


def test_data_json_completo(salida):
    d = json.loads((salida / 'data.json').read_text(encoding='utf-8'))
    assert len(d['abet']) == 24 and len(d['cna']) == 60 and len(d['evidencias']) == 240


def test_reproyectar_es_idempotente(salida):
    assert main(['reproyectar', '--salida', str(salida)]) == 0
    con = sqlite3.connect(salida / 'indice_acreditacion.sqlite')
    assert con.execute('SELECT COUNT(*) FROM evidencia_nodo').fetchone()[0] == 492
    con.close()


def test_graficas_y_tablas_pptx(salida):
    con = sqlite3.connect(salida / 'indice_acreditacion.sqlite')
    n = lambda q, *a: con.execute(q, a).fetchone()[0]
    assert n('SELECT COUNT(*) FROM grafica') == 79
    assert n('SELECT COUNT(*) FROM tabla_diapositiva') == 53
    # La serie de alcance de REA transcrita a mano coincide con los datos de la gráfica de F05-P027
    grafica = dict(((s, c), v) for s, c, v in con.execute("""
        SELECT d.serie, d.categoria, d.valor FROM grafica_dato d JOIN grafica g ON g.id=d.grafica_id
        JOIN evidencia e ON e.id=g.evidencia_id WHERE e.codigo='F05-P027'"""))
    manual = con.execute("""SELECT m.periodo, substr(i.codigo, 5), m.valor FROM medicion m JOIN indicador i ON i.id=m.indicador_id
                            WHERE i.codigo LIKE 'ALC_REA%'""").fetchall()
    assert len(manual) == 25 and all(grafica[(p, r)] == v for p, r, v in manual)
    con.close()


def test_inconsistencias_graduacion(salida):
    con = sqlite3.connect(salida / 'indice_acreditacion.sqlite')
    filas = con.execute('SELECT codigo, periodo FROM v_inconsistencias ORDER BY periodo').fetchall()
    # La diferencia real entre factores 4 y 6 sigue; la de la media NBC era un error de transcripción
    assert filas == [('GRAD_ACUM', 'S12'), ('GRAD_ACUM', 'S13'), ('GRAD_ACUM', 'S14')]
    con.close()


@pytest.mark.skipif(not LEGADO.exists(), reason='no está la base del prototipo en legado/')
def test_igual_al_prototipo(salida):
    difs = comparar(LEGADO, salida / 'indice_acreditacion.sqlite')
    # Diferencias esperadas: poppler 26.09 corta distinto las líneas de 3 diapositivas, y la graduación
    # acumulada del factor 4 se corrigió con la gráfica del PPTX. El resto debe ser idéntico.
    assert set(difs) <= {'evidencia', 'evidencia.texto', 'medicion', 'v_inconsistencias'}
    assert {r[0] for r in difs.get('evidencia.texto', ([], []))[1]} <= {'F05-P016', 'F07-P020', 'F11-P006'}
    assert {r[0] for r in difs.get('evidencia', ([], []))[1]} <= {'F07-P020'}
    solo_a, solo_b = difs.get('medicion', ([], []))
    assert {r[0] for r in solo_a + solo_b} <= {'GRAD_ACUM', 'GRAD_ACUM_NBC'}
    assert {r[5] for r in solo_a + solo_b} == {'F04-P006'}
