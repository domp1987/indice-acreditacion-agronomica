"""Pestaña «Acreditadoras»: cada marco del índice tiene su ficha y su estructura sale de la base."""
import json
import sqlite3

import pytest

from indice.config import cargar_rutas
from indice.exportar import datos_tablero

rutas = cargar_rutas()
CAMPOS = ['marco', 'nombre', 'agencia', 'alcance', 'solicita', 'base', 'estructura_resumen', 'resultado', 'vigencia',
          'contexto', 'proceso', 'considera', 'decision', 'situacion', 'pestana', 'fuentes']


def test_fichas_completas():
    lista = json.loads((rutas.semillas.parent / 'acreditadoras.json').read_text(encoding='utf-8'))['acreditadoras']
    assert [a['marco'] for a in lista] == ['CNA', 'CNA-INST', 'ABET-EAC', 'ATMAE-2027', 'ANECA-EURACE', 'SOFIA']
    for a in lista:
        assert all(a.get(c) for c in CAMPOS), a['marco']
        assert len(a['proceso']) >= 2 and len(a['considera']) >= 3


@pytest.mark.skipif(not rutas.db.exists(), reason='falta la base (ejecuta indice todo)')
def test_estructura_desde_la_base():
    con = sqlite3.connect(rutas.db); con.row_factory = sqlite3.Row
    d = datos_tablero(con)
    con.close()
    est = {a['marco']: a['estructura'] for a in d['acreditadoras']}
    assert len([n for n in est['SOFIA'] if not n['padre']]) == 10
    assert len([n for n in est['CNA-INST'] if n['tipo'] == 'caracteristica']) == 38
    assert all(est[m] for m in est)
