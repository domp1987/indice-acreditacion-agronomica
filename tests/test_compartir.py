"""Versión para compartir: sin correos ni nombres de profesores; la versión completa no cambia."""
import hashlib
import json
import re
import zipfile

import pytest

from indice.cli import PLANTILLA
from indice.compartir import anonimizar_texto, compartir
from indice.config import cargar_rutas

rutas = cargar_rutas()
CORREO = re.compile(r'[\w.+-]+@[\w-]+(\.[\w-]+)+')


def test_anonimizar_texto():
    t = 'Nombre profesor líder      ANA PÉREZ GÓMEZ\nCréditos 3\nescribir a ana.perez@ucundinamarca.edu.co'
    r = anonimizar_texto(t)
    assert 'ANA PÉREZ' not in r and 'ana.perez' not in r
    assert 'Nombre profesor líder [omitido]' in r and 'Créditos 3' in r and '[correo omitido]' in r


@pytest.mark.skipif(not rutas.db.exists(), reason='falta la base (ejecuta indice todo)')
def test_version_para_compartir(tmp_path):
    huella = hashlib.sha256(rutas.db.read_bytes()).hexdigest()
    r = compartir(rutas.db, tmp_path, PLANTILLA, rutas.semillas)
    assert hashlib.sha256(rutas.db.read_bytes()).hexdigest() == huella   # la completa no se toca
    assert r['evidencias_omitidas'] >= 40
    html = (tmp_path / 'indice_acreditacion_abet.html').read_text(encoding='utf-8')
    with zipfile.ZipFile(tmp_path / 'tablas_csv.zip') as z:
        csvs = ''.join(z.read(n).decode('utf-8-sig') for n in z.namelist())
    for texto in (html, csvs):
        assert not CORREO.search(texto)
        assert not re.search(r'profesor l[ií]der\s+[A-ZÁÉÍÓÚÑ]{3,}', texto, re.I)
    d = json.loads((tmp_path / 'data.json').read_text(encoding='utf-8'))
    ev = {e['codigo']: e for e in d['evidencias']}
    assert ev['AX-36']['texto'].startswith('[Texto omitido')
    assert len(d['evidencias']) == 716 and d['matriz']   # nada más cambia: mismas evidencias, etiquetas y matriz
