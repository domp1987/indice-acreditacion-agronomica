"""Sello SOFÍA (Fundación madri+d): semillas, proyección desde la autoevaluación institucional y lectura por estándar."""
import sqlite3

import pytest

from indice.config import cargar_rutas
from indice.semillas import leer_todas, validar

rutas = cargar_rutas()


def test_semillas_sofia():
    d = leer_todas(rutas.semillas)
    assert not validar(d)
    nodos = [n for n in d['nodos'] if n['marco'] == 'SOFIA']
    assert [n['codigo'] for n in nodos if not n['padre']] == [f'SF{i}' for i in range(1, 11)]   # 10 estándares
    assert len(nodos) == 41   # + 31 apartados del informe de autoevaluación
    cor = [c for c in d['correspondencias'] if c['marco_destino'] == 'SOFIA']
    # la fuente es la autoevaluación institucional; el programa solo llega al estándar 5 (muestra de títulos)
    assert {c['marco_origen'] for c in cor} == {'CNA-INST', 'CNA'}
    assert all(c['destino'].startswith('SF5.') for c in cor if c['marco_origen'] == 'CNA')
    assert all(c['tipo'] in ('parcial', 'apoyo') for c in cor)   # ninguna equivalencia directa entre modelos distintos


@pytest.mark.skipif(not rutas.db.exists(), reason='falta la base (ejecuta indice todo)')
def test_proyeccion_y_lectura():
    con = sqlite3.connect(rutas.db)
    n = lambda q: con.execute(q).fetchone()[0]
    base = """FROM evidencia_nodo en JOIN evidencia e ON e.id=en.evidencia_id JOIN nodo x ON x.id=en.nodo_id
              JOIN marco m ON m.id=x.marco_id AND m.codigo='SOFIA'"""
    # todo lo de SOFÍA es inferido y queda como propuesta para el comité
    assert n(f"SELECT COUNT(*) {base} WHERE en.origen<>'inferida' OR en.estado<>'propuesta'") == 0
    assert n(f"SELECT COUNT(*) {base} WHERE e.codigo LIKE 'IF%'") > 0
    # la evidencia del programa solo llega a Formación
    assert n(f"SELECT COUNT(*) {base} WHERE e.codigo NOT LIKE 'I%' AND x.codigo NOT LIKE 'SF5%'") == 0
    # el documento maestro RRC 2025 (escenario) no se proyecta
    assert n(f"SELECT COUNT(*) {base} WHERE e.nivel='escenario'") == 0
    v = {r[0]: r[1:] for r in con.execute('SELECT codigo, valoracion_inst, minima_inst, brechas_media_alta FROM v_valoracion_sofia')}
    assert len(v) == 10
    assert v['SF7'][1] == 3.6        # impacto cultural y artístico, lo más bajo
    assert v['SF8'][0] == 5.0        # sistema de aseguramiento de la calidad
    assert v['SF1'][2] >= 1          # requisito de egresados sin verificar
    con.close()
