"""Extrae el texto por página de los PDF de factores CNA y detecta la característica de cada diapositiva."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PATRON_FACTOR = re.compile(r'Factor[ _](\d+)', re.I)
PATRON_CARACTERISTICA = re.compile(r'Caracter[ií]stica\s*(\d+)\.?\s*\n?\s*([^\n]+(?:\n[a-záéíóúñ][^\n]+)?)')


def _binario(nombre, carpeta):
    if carpeta:
        exe = Path(carpeta) / (nombre + ('.exe' if os.name == 'nt' else ''))
        if exe.exists(): return str(exe)
    return shutil.which(nombre)


def _ejecutar(args):
    # pdfinfo escribe algunas fechas en la codificación local de Windows aunque se pida UTF-8
    return subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', check=True).stdout


def _paginas_pdftotext(pdf, pdfinfo, pdftotext):
    n = int(re.search(r'Pages:\s+(\d+)', _ejecutar([pdfinfo, '-enc', 'UTF-8', str(pdf)])).group(1))
    for p in range(1, n + 1):
        yield p, _ejecutar([pdftotext, '-enc', 'UTF-8', '-f', str(p), '-l', str(p), str(pdf), '-'])


def _paginas_pypdf(pdf):
    from pypdf import PdfReader
    for p, pagina in enumerate(PdfReader(pdf).pages, 1):
        yield p, pagina.extract_text(extraction_mode='layout') or ''


def elegir_motor(motor, poppler=None):
    """Devuelve una función pdf -> (página, texto). 'auto' prefiere pdftotext, que es con el que se construyó la base."""
    if motor in ('auto', 'pdftotext'):
        pdfinfo, pdftotext = _binario('pdfinfo', poppler), _binario('pdftotext', poppler)
        if pdfinfo and pdftotext:
            return 'pdftotext', lambda pdf: _paginas_pdftotext(pdf, pdfinfo, pdftotext)
        if motor == 'pdftotext':
            raise SystemExit('No se encontró pdftotext/pdfinfo. Instala poppler o indica su carpeta en indice.toml (poppler) o en INDICE_POPPLER.')
    try:
        import pypdf  # noqa: F401
    except ImportError:
        raise SystemExit('No hay extractor disponible: instala poppler (recomendado) o pypdf.')
    if motor == 'auto':
        print('Aviso: no se encontró pdftotext; se usa pypdf. El texto difiere y la base no será comparable.', file=sys.stderr)
    return 'pypdf', _paginas_pypdf


def listar_pdf(carpeta):
    pdfs = [(int(m.group(1)), f) for f in Path(carpeta).glob('*.pdf') if (m := PATRON_FACTOR.match(f.name))]
    if not pdfs:
        raise SystemExit(f'No hay PDF de factores ("Factor N...pdf") en {carpeta}')
    return sorted(pdfs)


def extraer(carpeta_pdf, destino, motor='auto', poppler=None):
    nombre_motor, paginas = elegir_motor(motor, poppler)
    out = []
    for factor, pdf in listar_pdf(carpeta_pdf):
        for p, t in paginas(pdf):
            t = re.sub(r'www\.ucundinamarca\.edu\.co.*', '', t)
            m = PATRON_CARACTERISTICA.search(t)
            out.append(dict(factor=factor, archivo=pdf.name, pagina=p,
                            car=int(m.group(1)) if m else None,
                            car_nombre=re.sub(r'\s+', ' ', m.group(2)).strip() if m else None,
                            texto=re.sub(r'[ \t]+', ' ', re.sub(r'\n\s*\n+', '\n', t)).strip()))
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    print(f'Extracción ({nombre_motor}): {len(out)} páginas de {len({d["archivo"] for d in out})} PDF → {destino}')
    return out
