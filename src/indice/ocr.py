"""OCR del texto que está dentro de imágenes (infografías, capturas, portadas de libros).

Renderiza cada página del PDF y la pasa por el OCR integrado de Windows, o por tesseract si está en el PATH.
El resultado crudo se guarda en caché (salida/ocr.json) y solo se repite si cambia el PDF. El filtrado contra
el texto del PDF se hace al cargar (texto_nuevo), para poder ajustar las reglas sin repetir el OCR.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path

from indice.config import PAQUETE
from indice.extraer import binario

RESOLUCION = 150   # ppp: suficiente para el OCR y rápido (una diapositiva ≈ 2000 × 1125 px)
_REPETIDO = re.compile(r'universidad de|cundinamarca|vigilada|mineducaci|www\.|\.edu\.co|acreditaci[oó]n de alta', re.I)


def elegir_motor():
    if os.name == 'nt' and shutil.which('powershell'): return 'windows'
    if shutil.which('tesseract'): return 'tesseract'
    return None


def _ocr_windows(carpeta, idioma='es-ES'):
    salida = Path(carpeta) / '_ocr.json'
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(PAQUETE / 'ocr_windows.ps1'),
                        '-Carpeta', str(carpeta), '-Salida', str(salida), '-Idioma', idioma],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:500])
    datos = json.loads(salida.read_text(encoding='utf-8-sig'))
    # ConvertTo-Json de Windows PowerShell puede entregar una sola línea como texto y no como lista
    return {k: [v] if isinstance(v, str) else list(v or []) for k, v in datos.items()}


def _ocr_tesseract(carpeta):
    out = {}
    for png in sorted(Path(carpeta).glob('*.png')):
        r = subprocess.run(['tesseract', str(png), '-', '-l', 'spa'], capture_output=True, text=True, encoding='utf-8', errors='replace')
        out[png.name] = [l for l in r.stdout.splitlines() if l.strip()]
    return out


def _firma(pdf):
    st = Path(pdf).stat()
    return f'{st.st_size}-{int(st.st_mtime)}'


def ocr_pdf(pdf, motor, pdftoppm):
    """OCR de todas las páginas de un PDF: {'1': [líneas], '2': […], …}."""
    with tempfile.TemporaryDirectory(prefix='indice_ocr_') as tmp:
        subprocess.run([pdftoppm, '-png', '-r', str(RESOLUCION), str(pdf), str(Path(tmp) / 'p')], check=True, capture_output=True)
        lineas = _ocr_windows(tmp) if motor == 'windows' else _ocr_tesseract(tmp)
    return {str(int(re.search(r'-(\d+)\.png$', k).group(1))): v for k, v in lineas.items()}


def ocr(fuentes, destino, poppler=None, rehacer=False):
    """Actualiza la caché de OCR {fuente: {firma, motor, paginas: {n: [líneas]}}} para cada fuente con PDF."""
    motor = elegir_motor()
    pdftoppm = binario('pdftoppm', poppler)
    if not motor or not pdftoppm:
        print('Aviso: no hay motor de OCR (Windows o tesseract) o falta pdftoppm; se omite el OCR.')
        return None
    destino = Path(destino)
    cache = json.loads(destino.read_text(encoding='utf-8')) if destino.exists() and not rehacer else {}
    hechas = 0
    for f in fuentes:
        if not f.pdf: continue
        if cache.get(f.codigo, {}).get('firma') == _firma(f.pdf): continue
        paginas = ocr_pdf(f.pdf, motor, pdftoppm)
        cache[f.codigo] = dict(firma=_firma(f.pdf), motor=motor, paginas=paginas)
        hechas += 1
        print(f'OCR ({motor}) {f.codigo}: {len(paginas)} páginas')
        destino.write_text(json.dumps(cache, ensure_ascii=False), encoding='utf-8')   # guarda el avance
    total = sum(len(c['paginas']) for c in cache.values())
    print(f'OCR: {hechas} presentaciones procesadas, {len(cache) - hechas} desde caché, {total} páginas → {destino}')
    return cache


def _normalizar(t):
    return unicodedata.normalize('NFKD', t.lower()).encode('ascii', 'ignore').decode()


def _palabras(t):
    return re.findall(r'[a-z]{4,}', _normalizar(t))


def texto_nuevo(lineas, texto_pdf):
    """Líneas del OCR que aportan algo que no está en el texto del PDF, sin encabezados repetidos ni ruido."""
    conocidas = set(_palabras(texto_pdf))
    out = []
    for l in lineas:
        l = re.sub(r'\s+', ' ', l).strip()
        if len(l) < 6 or _REPETIDO.search(l): continue
        letras = sum(ch.isalpha() for ch in l)
        if letras / max(1, len(l.replace(' ', ''))) < 0.6: continue   # ruido de fotos: símbolos y cifras sueltas
        palabras = _palabras(l)
        if not palabras or all(p in conocidas for p in palabras): continue
        out.append(l)
    return '\n'.join(out)
