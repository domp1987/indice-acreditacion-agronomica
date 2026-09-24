"""Semillas: las del repositorio son válidas y el validador rechaza errores comunes con mensajes legibles."""
import shutil

import pytest

from indice.config import cargar_rutas
from indice.semillas import ErrorSemilla, leer_todas

SEMILLAS = cargar_rutas().semillas


@pytest.fixture
def semillas():
    return leer_todas(SEMILLAS)


@pytest.fixture
def copia(tmp_path):
    destino = tmp_path / 'semillas'
    shutil.copytree(SEMILLAS, destino)
    return destino


def test_semillas_del_repositorio(semillas):
    nodos = semillas['nodos']
    assert sum(n['tipo'] == 'factor' for n in nodos if n['marco'] == 'CNA') == 12
    assert sum(n['tipo'] == 'caracteristica' for n in nodos if n['marco'] == 'CNA') == 48
    assert sum(c['creditos'] for c in semillas['cursos']) == 150
    # Ningún nodo ABET queda sin padre salvo los criterios
    assert all(n['padre'] or n['tipo'] == 'criterio' for n in nodos if n['marco'] == 'ABET-EAC')


def test_rechaza_nodo_desconocido(copia):
    ruta = copia / 'correspondencias.csv'
    ruta.write_text(ruta.read_text(encoding='utf-8') + 'CNA,C99,ABET-EAC,C1,apoyo,\n', encoding='utf-8')
    with pytest.raises(ErrorSemilla, match='nodo desconocido CNA/C99'):
        leer_todas(copia)


def test_rechaza_correspondencia_dentro_del_mismo_marco(copia):
    ruta = copia / 'correspondencias.csv'
    ruta.write_text(ruta.read_text(encoding='utf-8') + 'CNA,C01,CNA,C02,apoyo,\n', encoding='utf-8')
    with pytest.raises(ErrorSemilla, match='mismo marco'):
        leer_todas(copia)


def test_rechaza_valor_no_numerico(copia):
    ruta = copia / 'mediciones.csv'
    ruta.write_text(ruta.read_text(encoding='utf-8') + 'RET,2026-1,Programa,noventa,,,\n', encoding='utf-8')
    with pytest.raises(ErrorSemilla, match='"valor" debe ser numérico'):
        leer_todas(copia)


def test_rechaza_encabezado_cambiado(copia):
    ruta = copia / 'cursos.csv'
    ruta.write_text(ruta.read_text(encoding='utf-8').replace('categoria_abet', 'categoria', 1), encoding='utf-8')
    with pytest.raises(ErrorSemilla, match='encabezado'):
        leer_todas(copia)
