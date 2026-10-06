"""Autoevaluación institucional (modelo institucional del CNA): fuentes, etiquetado y valoraciones."""
import sqlite3

import pytest

from indice.config import cargar_rutas
from indice.fuentes import listar_fuentes

rutas = cargar_rutas()


@pytest.mark.skipif(not (rutas.pdf_institucional and rutas.pdf_institucional.exists()), reason='faltan las presentaciones institucionales')
def test_fuentes_institucionales():
    fuentes = listar_fuentes(rutas.pdf_institucional, 'institucional')
    codigos = [f.codigo for f in fuentes]
    assert codigos == ['IF01', 'IF02', 'IF03', 'IF04', 'IF05', 'IF06', 'IF07', 'IF09', 'IF10', 'IF11', 'IF12', 'IP01']   # sin factor 8
    assert all(f.sede == 'Institución' for f in fuentes)
    assert not [f for f in fuentes if 'HV' in f.nombre]   # las hojas de vida de los pares no se indexan


@pytest.mark.skipif(not rutas.db.exists(), reason='falta la base (ejecuta indice todo)')
def test_etiquetado_y_valoraciones():
    con = sqlite3.connect(rutas.db)
    n = lambda q: con.execute(q).fetchone()[0]
    assert n("SELECT COUNT(*) FROM nodo x JOIN marco m ON m.id=x.marco_id WHERE m.codigo='CNA-INST' AND x.tipo='caracteristica'") == 38
    # las diapositivas institucionales se etiquetan con el modelo institucional, nunca con el encabezado del programa
    assert n("""SELECT COUNT(*) FROM evidencia_nodo en JOIN evidencia e ON e.id=en.evidencia_id JOIN nodo x ON x.id=en.nodo_id
                JOIN marco m ON m.id=x.marco_id WHERE e.codigo LIKE 'I%' AND m.codigo='CNA' AND en.estado='validada'""") == 0
    assert n("""SELECT COUNT(*) FROM evidencia_nodo en JOIN evidencia e ON e.id=en.evidencia_id JOIN nodo x ON x.id=en.nodo_id
                JOIN marco m ON m.id=x.marco_id WHERE e.codigo LIKE 'IF10-%' AND m.codigo='CNA-INST' AND x.codigo='IC29'""") > 0
    # y respaldan al programa como propuesta (planta profesoral → número, dedicación y formación)
    assert n("""SELECT COUNT(*) FROM evidencia_nodo en JOIN evidencia e ON e.id=en.evidencia_id JOIN nodo x ON x.id=en.nodo_id
                JOIN marco m ON m.id=x.marco_id WHERE e.codigo LIKE 'IF10-%' AND m.codigo='CNA' AND x.codigo='C10' AND en.estado='propuesta'""") > 0
    val = dict(con.execute('SELECT codigo, valoracion FROM v_valoracion_cna_inst'))
    assert val['IC29'] == 4.8 and val['IC24'] == 3.6 and val['IC25'] is None   # factor 8 sin presentación
    assert n("SELECT COUNT(*) FROM v_cna_inst_programa WHERE inst='IC29' AND programa='C10'") == 1
    con.close()
