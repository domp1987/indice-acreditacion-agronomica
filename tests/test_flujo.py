"""Prueba de aceptación: el flujo completo corre desde una carpeta limpia con un solo comando.

Requiere las presentaciones (ruta de indice.toml) y poppler; si faltan, las pruebas se omiten.
Para no repetir la conversión con PowerPoint ni el OCR (minutos), se copian sus cachés de salida/ si existen;
sin ellas el flujo corre igual, solo que más lento.
Las pruebas del modelo de datos (tarea 4) irán en archivos aparte.
"""
import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

from indice.cli import main
from indice.config import PROYECTO, cargar_rutas
from indice.extraer import binario

sys.path.insert(0, str(Path(__file__).parent))
from comparar_bases import comparar  # noqa: E402

rutas = cargar_rutas()
LEGADO = PROYECTO / 'legado' / 'indice_acreditacion.sqlite'

pytestmark = pytest.mark.skipif(
    not rutas.pdf.exists() or not binario('pdftotext', rutas.poppler),
    reason='faltan las presentaciones o poppler (pdftotext)')


@pytest.fixture(scope='module')
def salida(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp('salida')
    if rutas.pdf_convertidos.exists():
        shutil.copytree(rutas.pdf_convertidos, carpeta / 'pdf_convertidos', copy_function=shutil.copy2)
    if rutas.ocr_json.exists():
        shutil.copy2(rutas.ocr_json, carpeta / 'ocr.json')
    assert main(['todo', '--salida', str(carpeta), '--motor', 'pdftotext']) == 0
    return carpeta


@pytest.fixture(scope='module')
def con(salida):
    c = sqlite3.connect(salida / 'indice_acreditacion.sqlite')
    yield c
    c.close()


def test_genera_todos_los_productos(salida):
    for nombre in ['diapositivas.json', 'pptx.json', 'indice_acreditacion.sqlite', 'data.json', 'tablas_csv.zip', 'indice_acreditacion_abet.html']:
        assert (salida / nombre).stat().st_size > 0, nombre
    html = (salida / 'indice_acreditacion_abet.html').read_text(encoding='utf-8')
    assert '__DATA__' not in html


def test_conteos(con):
    n = lambda q: con.execute(q).fetchone()[0]
    assert n("SELECT COUNT(*) FROM evidencia WHERE codigo LIKE 'F%'") == 240      # como el prototipo
    assert n("SELECT COUNT(*) FROM evidencia WHERE codigo LIKE 'S%'") == 52       # sesión de inicio (Rectoría y Facultad)
    assert n('SELECT COUNT(*) FROM evidencia_nodo') == 492
    assert n('SELECT COUNT(*) FROM nodo') == 89
    assert n('SELECT COUNT(*) FROM medicion') == 299   # 224 del prototipo + 3 (corrección F04-P006) + 72 (ponderaciones y factores CNA)
    assert n('SELECT COUNT(*) FROM curso') == 54
    assert n('SELECT SUM(creditos) FROM curso') == 150


def test_sesion_de_inicio(con):
    sedes = con.execute("SELECT DISTINCT sede FROM evidencia WHERE codigo LIKE 'S%'").fetchall()
    assert sedes == [('Institución',)]
    archivos = {a for (a,) in con.execute("SELECT DISTINCT archivo FROM evidencia WHERE codigo LIKE 'S%'")}
    assert archivos == {'2. Presentación Rectoría.pptx', '4. Facultad de Ciencias Agropecuarias.pptx'}


def test_data_json_completo(salida):
    d = json.loads((salida / 'data.json').read_text(encoding='utf-8'))
    assert len(d['abet']) == 24 and len(d['cna']) == 60 and len(d['evidencias']) == 292


def test_reproyectar_es_idempotente(salida, con):
    assert main(['reproyectar', '--salida', str(salida)]) == 0
    assert con.execute('SELECT COUNT(*) FROM evidencia_nodo').fetchone()[0] == 492


def test_graficas_y_tablas_pptx(con):
    n = lambda q: con.execute(q).fetchone()[0]
    por_fuente = lambda t, p: n(f"SELECT COUNT(*) FROM {t} x JOIN evidencia e ON e.id=x.evidencia_id WHERE e.codigo LIKE '{p}%'")
    assert por_fuente('grafica', 'F') == 79 and por_fuente('tabla_diapositiva', 'F') == 53
    assert por_fuente('grafica', 'S') == 4 and por_fuente('tabla_diapositiva', 'S') == 10
    # La serie de alcance de REA transcrita a mano coincide con los datos de la gráfica de F05-P027
    grafica = dict(((s, c), v) for s, c, v in con.execute("""
        SELECT d.serie, d.categoria, d.valor FROM grafica_dato d JOIN grafica g ON g.id=d.grafica_id
        JOIN evidencia e ON e.id=g.evidencia_id WHERE e.codigo='F05-P027'"""))
    manual = con.execute("""SELECT m.periodo, substr(i.codigo, 5), m.valor FROM medicion m JOIN indicador i ON i.id=m.indicador_id
                            WHERE i.codigo LIKE 'ALC_REA%'""").fetchall()
    assert len(manual) == 25 and all(grafica[(p, r)] == v for p, r, v in manual)


@pytest.mark.skipif(not rutas.ocr_json.exists(), reason='sin caché de OCR; el OCR completo tarda varios minutos')
def test_ocr_recupera_texto_de_imagenes(con):
    ocr = con.execute("SELECT texto_ocr FROM evidencia WHERE codigo='F03-P016'").fetchone()[0] or ''
    assert 'CIRCUITO DE' in ocr and 'INNOVACIÓN' in ocr   # infografía que el PDF no trae como texto
    assert con.execute('SELECT COUNT(*) FROM evidencia WHERE texto_ocr IS NOT NULL').fetchone()[0] > 100


def test_inconsistencias_graduacion(con):
    filas = con.execute('SELECT codigo, periodo FROM v_inconsistencias ORDER BY periodo').fetchall()
    # La diferencia real entre factores 4 y 6 sigue; la de la media NBC era un error de transcripción
    assert filas == [('GRAD_ACUM', 'S12'), ('GRAD_ACUM', 'S13'), ('GRAD_ACUM', 'S14')]


@pytest.mark.skipif(not LEGADO.exists(), reason='no está la base del prototipo en legado/')
def test_igual_al_prototipo(salida):
    difs = comparar(LEGADO, salida / 'indice_acreditacion.sqlite')
    es_sesion = lambda fila: any(isinstance(v, str) and v[:1] == 'S' and v[1:3].isdigit() and '-P' in v for v in fila)
    # Diferencias esperadas: poppler 26.09 corta distinto las líneas de 3 diapositivas; la graduación acumulada
    # del factor 4 se corrigió con la gráfica del PPTX; y se agregaron las presentaciones de la sesión de inicio
    # (evidencias S.., con su normativa). El resto debe ser idéntico.
    assert set(difs) <= {'evidencia', 'evidencia.texto', 'medicion', 'indicador', 'v_inconsistencias', 'normativa', 'normativa_mencion'}
    assert {r[0] for r in difs.get('evidencia.texto', ([], []))[1] if not es_sesion(r)} <= {'F05-P016', 'F07-P020', 'F11-P006'}
    assert {r[0] for r in difs.get('evidencia', ([], []))[1] if not es_sesion(r)} <= {'F07-P020'}
    # Mediciones: corrección de F04-P006, vínculos de evidencia que el prototipo no resolvía o resolvía mal
    # (retención y deserción, series de Facatativá, valoraciones CNA) e indicadores nuevos de las tablas de valoración
    solo_a, solo_b = difs.get('medicion', ([], []))
    corregidas = {'GRAD_ACUM', 'GRAD_ACUM_NBC', 'RET', 'DES', 'INSC', 'ADM', 'PRIM', 'CNA_VAL'}
    assert {r[0] for r in solo_a} <= corregidas
    assert {r[0] for r in solo_b} <= corregidas | {'CNA_POND', 'CNA_VAL_FACTOR', 'CNA_CUMPL_FACTOR'}
    assert all(r[0] != 'GRAD_ACUM' or r[5] == 'F04-P006' for r in solo_a + solo_b)
    assert set(difs.get('indicador', ([], []))[1]) <= {r for r in difs.get('indicador', ([], []))[1] if r[0].startswith('CNA_')}
    # Normativa: solo se agrega (nada del prototipo se pierde) y las menciones nuevas son de la sesión de inicio
    assert not difs.get('normativa', ([], []))[0]
    solo_a, solo_b = difs.get('normativa_mencion', ([], []))
    assert not solo_a and all(es_sesion(r) for r in solo_b)


def test_mediciones_ligadas_a_su_evidencia(con):
    # Toda medición cita la diapositiva de donde sale su valor
    sin = con.execute('SELECT DISTINCT i.codigo FROM medicion m JOIN indicador i ON i.id=m.indicador_id WHERE m.evidencia_id IS NULL').fetchall()
    assert sin == []
    # Las series de Facatativá están en F06-P016 y las de Fusagasugá en F06-P015
    filas = con.execute("""SELECT DISTINCT m.sede, e.codigo FROM medicion m JOIN indicador i ON i.id=m.indicador_id
                           JOIN evidencia e ON e.id=m.evidencia_id WHERE i.codigo IN ('INSC','ADM','PRIM')""").fetchall()
    assert sorted(filas) == [('Facatativá', 'F06-P016'), ('Fusagasugá', 'F06-P015')]


def test_ponderaciones_cna(con):
    # En cada factor las ponderaciones de sus características suman 100 %
    sumas = con.execute("""SELECT p.codigo, SUM(m.valor) FROM medicion m JOIN indicador i ON i.id=m.indicador_id AND i.codigo='CNA_POND'
                           JOIN nodo n ON n.codigo=m.desagregacion AND n.marco_id=1 JOIN nodo p ON p.id=n.padre_id GROUP BY p.codigo""").fetchall()
    assert len(sumas) == 12 and all(abs(s - 100) < 0.01 for _, s in sumas)
