"""PAD de los Campos de Aprendizaje Institucional (CAI): Word convertido a PDF y lector complementario."""
import json

import pytest

from indice.compartir import anonimizar_texto
from indice.config import cargar_rutas

rutas = cargar_rutas()
pytestmark = pytest.mark.skipif(not rutas.pads_json.exists(), reason='falta salida/pads.json')


@pytest.fixture(scope='module')
def cai():
    pads = json.loads(rutas.pads_json.read_text(encoding='utf-8'))
    return {p['codigo']: p for p in pads if p.get('tipo_campo') == 'CAI'}


def test_cai_leidos(cai):
    assert len(cai) == 16   # los 16 PAD de PADs CAI
    assert sum(1 for p in cai.values() if p['archivo'].endswith('.docx')) == 7
    rlc = cai['CAI1002020201']
    assert rlc['nombre'].startswith('RAZONAMIENTO') and rlc['semestre'] == 2 and len(rlc['rea']) == 3 and len(rlc['experiencias']) == 3
    assert cai['CAI1002020305']['nombre'] == 'Producción de textos académicos y profesionales' and cai['CAI1002020305']['semestre'] == 3
    # ningún nombre de experiencia es un rótulo de la plantilla
    assert not [e['nombre'] for p in cai.values() for e in p['experiencias'] if e['nombre'].startswith(('Experiencia/', 'Description', 'Semestr'))]


def test_disciplinares_no_son_cai(cai):
    assert not [c for c in cai if c.startswith(('CAD', 'CFC'))]


def test_lideres_ocultos_en_la_version_para_compartir():
    t = 'Nombre profesor                    Prerrequisitos (si\n                ANA MARIA PEREZ GOMEZ     x\n Líder CAI   Juan Pérez'
    r = anonimizar_texto(t)
    assert 'ANA MARIA' not in r and 'Juan Pérez' not in r and 'Prerrequisitos' in r
