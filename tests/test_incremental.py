"""Tarea 3: la carga incremental conserva las decisiones del comité y los ids, y es idempotente.

Usa lo ya extraído en salida/ (diapositivas.json, pptx.json, ocr.json); si no existe, se omite.
"""
import json
import shutil
import sqlite3

import pytest

from indice.cargar import cargar
from indice.config import PROYECTO, cargar_rutas
from indice.reproyectar import reproyectar

rutas = cargar_rutas()
pytestmark = pytest.mark.skipif(not rutas.diapositivas.exists(), reason='falta salida/diapositivas.json (ejecuta indice extraer)')


def recargar(t, diapositivas=None, semillas=None):
    cambios = cargar(t / 'base.sqlite', diapositivas or rutas.diapositivas, semillas or rutas.semillas, rutas.pptx_json, rutas.ocr_json)
    return cambios, reproyectar(t / 'base.sqlite')


def uno(con, sql, *a):
    fila = con.execute(sql, a).fetchone()
    return fila[0] if fila and len(fila) == 1 else fila


NODO = "(SELECT n.id FROM nodo n JOIN marco m ON m.id=n.marco_id WHERE m.codigo=? AND n.codigo=?)"
EVID = "(SELECT id FROM evidencia WHERE codigo=?)"


@pytest.fixture
def base(tmp_path):
    recargar(tmp_path)
    return tmp_path


def decidir(con):
    """Simula al comité: descarta una correspondencia, valida una inferida, agrega una manual y revisa una evidencia."""
    con.execute(f"""UPDATE correspondencia SET estado='descartada', validado_por='comité', validado_en='2026-09-24'
                    WHERE origen_id={NODO} AND destino_id={NODO}""", ('CNA', 'C10', 'ABET-EAC', 'C6'))
    con.execute(f"""UPDATE evidencia_nodo SET estado='validada', validado_por='comité', validado_en='2026-09-24'
                    WHERE evidencia_id={EVID} AND nodo_id={NODO}""", ('F05-P027', 'ABET-EAC', 'C3'))
    con.execute(f"""INSERT INTO evidencia_nodo(evidencia_id,nodo_id,rol,origen,estado,validado_por,validado_en)
                    VALUES ({EVID},{NODO},'parcial','manual','validada','comité','2026-09-24')""", ('F05-P027', 'ABET-EAC', 'SO6'))
    con.execute("UPDATE evidencia SET estado_revision='revisada' WHERE codigo='F01-P002'")
    con.commit()


def test_segunda_carga_no_cambia_nada(base):
    con = sqlite3.connect(base / 'base.sqlite')
    antes = con.execute('SELECT id, codigo, actualizado_en FROM evidencia ORDER BY id').fetchall()
    con.close()
    cambios, rep = recargar(base)
    assert cambios == dict(nuevas=0, actualizadas=0, obsoletas=0, etiquetas_nuevas=0, etiquetas_retiradas=0)
    assert rep == dict(nuevas=0, rol=0, retiradas=0, humanas=0)
    con = sqlite3.connect(base / 'base.sqlite')
    assert con.execute('SELECT id, codigo, actualizado_en FROM evidencia ORDER BY id').fetchall() == antes


def test_conserva_decisiones_del_comite(base):
    con = sqlite3.connect(base / 'base.sqlite')
    ids_antes = dict(con.execute('SELECT codigo, id FROM evidencia'))
    inferidas_c10 = uno(con, f"""SELECT COUNT(*) FROM evidencia_nodo en JOIN evidencia_nodo x ON x.evidencia_id=en.evidencia_id
                               WHERE en.nodo_id={NODO} AND en.origen='inferida' AND x.nodo_id={NODO} AND x.origen='extraccion'""",
                        'ABET-EAC', 'C6', 'CNA', 'C10')
    assert inferidas_c10 > 0
    decidir(con)
    con.close()

    _, rep = recargar(base)
    assert rep['humanas'] == 1 and rep['retiradas'] >= inferidas_c10   # se retiran las que venían de la correspondencia descartada

    con = sqlite3.connect(base / 'base.sqlite')
    assert dict(con.execute('SELECT codigo, id FROM evidencia')) == ids_antes
    assert uno(con, f"SELECT estado, validado_por FROM correspondencia WHERE origen_id={NODO} AND destino_id={NODO}",
               'CNA', 'C10', 'ABET-EAC', 'C6') == ('descartada', 'comité')
    assert uno(con, f"SELECT estado, validado_por FROM evidencia_nodo WHERE evidencia_id={EVID} AND nodo_id={NODO}",
               'F05-P027', 'ABET-EAC', 'C3') == ('validada', 'comité')
    assert uno(con, f"SELECT origen, rol FROM evidencia_nodo WHERE evidencia_id={EVID} AND nodo_id={NODO}",
               'F05-P027', 'ABET-EAC', 'SO6') == ('manual', 'parcial')
    assert uno(con, "SELECT estado_revision FROM evidencia WHERE codigo='F01-P002'") == 'revisada'
    # Ya no queda ninguna inferida (sin decisión) que venga solo de C10 → C6
    assert uno(con, f"""SELECT COUNT(*) FROM evidencia_nodo en JOIN evidencia_nodo x ON x.evidencia_id=en.evidencia_id
                        WHERE en.nodo_id={NODO} AND en.origen='inferida' AND en.validado_por IS NULL
                          AND x.nodo_id={NODO} AND x.origen='extraccion'""", 'ABET-EAC', 'C6', 'CNA', 'C10') == 0


def test_diapositiva_retirada_queda_obsoleta_y_vuelve(base, tmp_path):
    slides = json.loads(rutas.diapositivas.read_text(encoding='utf-8'))
    sin_una = [s for s in slides if (s['fuente'], s['pagina']) != ('F05', 27)]
    parcial = tmp_path / 'diapositivas_parcial.json'
    parcial.write_text(json.dumps(sin_una, ensure_ascii=False), encoding='utf-8')

    cambios, _ = recargar(base, diapositivas=parcial)
    assert cambios['obsoletas'] == 1
    con = sqlite3.connect(base / 'base.sqlite')
    assert uno(con, "SELECT estado_revision FROM evidencia WHERE codigo='F05-P027'") == 'obsoleta'
    assert uno(con, f"SELECT COUNT(*) FROM evidencia_nodo WHERE evidencia_id={EVID} AND origen='inferida'", 'F05-P027') == 0
    con.close()

    cambios, _ = recargar(base)
    assert cambios['actualizadas'] == 1 and cambios['obsoletas'] == 0
    con = sqlite3.connect(base / 'base.sqlite')
    assert uno(con, "SELECT estado_revision FROM evidencia WHERE codigo='F05-P027'") == 'sin_revisar'
    assert uno(con, f"SELECT COUNT(*) FROM evidencia_nodo WHERE evidencia_id={EVID} AND origen='inferida'", 'F05-P027') > 0


def test_cambio_en_semillas_respeta_la_decision(base, tmp_path):
    con = sqlite3.connect(base / 'base.sqlite')
    decidir(con)
    con.close()
    semillas = tmp_path / 'semillas'
    shutil.copytree(rutas.semillas, semillas)
    ruta = semillas / 'correspondencias.csv'
    texto = ruta.read_text(encoding='utf-8')
    assert 'CNA,C10,ABET-EAC,C6,equivalente,' in texto and 'CNA,C04,ABET-EAC,C1,equivalente,' in texto
    texto = texto.replace('CNA,C10,ABET-EAC,C6,equivalente,', 'CNA,C10,ABET-EAC,C6,parcial,')   # decidida por el comité
    texto = texto.replace('CNA,C04,ABET-EAC,C1,equivalente,', 'CNA,C04,ABET-EAC,C1,parcial,')   # sin decisión
    ruta.write_text(texto, encoding='utf-8')

    recargar(base, semillas=semillas)
    con = sqlite3.connect(base / 'base.sqlite')
    tipo = lambda o, d: uno(con, f"SELECT tipo FROM correspondencia WHERE origen_id={NODO} AND destino_id={NODO}", 'CNA', o, 'ABET-EAC', d)
    assert tipo('C10', 'C6') == 'equivalente'   # se conserva lo que decidió el comité
    assert tipo('C04', 'C1') == 'parcial'       # se actualiza
    # y las inferidas de C04 → C1 pasan de principal a parcial (cada evidencia tiene una sola etiqueta de extracción)
    roles = con.execute(f"""SELECT DISTINCT en.rol FROM evidencia_nodo en JOIN evidencia_nodo x ON x.evidencia_id=en.evidencia_id
                            WHERE en.nodo_id={NODO} AND en.origen='inferida' AND x.nodo_id={NODO} AND x.origen='extraccion'""",
                        ('ABET-EAC', 'C1', 'CNA', 'C04')).fetchall()
    assert roles == [('parcial',)]


def test_migra_base_de_esquema_anterior(tmp_path):
    legado = PROYECTO / 'legado' / 'indice_acreditacion.sqlite'
    if not legado.exists(): pytest.skip('no está la base del prototipo')
    shutil.copy2(legado, tmp_path / 'base.sqlite')
    recargar(tmp_path)
    assert (tmp_path / 'base.respaldo-v1.sqlite').exists()
    con = sqlite3.connect(tmp_path / 'base.sqlite')
    assert uno(con, "SELECT valor FROM meta WHERE clave='version_esquema'") == '2'
    assert uno(con, 'SELECT COUNT(*) FROM evidencia_nodo') == 492
