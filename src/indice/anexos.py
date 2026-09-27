"""Anexos del documento maestro RRC 2025 (carpeta ANEXOS/, organizada por condición de calidad).

Cada archivo es una evidencia 'AX-<n>' (o 'AX-<n>-<k>' si el anexo es una carpeta con varios archivos), del proceso
de resignificación y de nivel 'complementaria': son anteriores a la base (PAD, presentaciones CNA, documento maestro 2019),
se consultan, pero hacia ABET solo aportan etiquetas de apoyo. Los PDF se indexan por su texto (pdftotext); los Excel se leen sin dependencias (un .xlsx es un zip
con XML) y cada hoja se guarda como tabla. Resultado en salida/anexos.json, con caché por archivo.

Se omiten:
- el Anexo 16 (Planes de Aprendizaje Digital): son idénticos a los de PADs/, que ya se indexan como 'PAD-…';
- el Anexo 21 (matriz de caracterización de población vulnerable): contiene datos personales sensibles de estudiantes;
- los archivos repetidos (mismo contenido que otro anexo, p. ej. 'convenio (1).pdf').
"""
import hashlib
import json
import re
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from indice.extraer import binario
from indice.ocr import elegir_motor, ocr_pdf

OMITIR = {16: 'idéntico a los PAD de PADs/ (se indexan como PAD-…)',
          21: 'datos personales sensibles de estudiantes (población vulnerable)'}
MAX_FILAS_HOJA = 2000
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}


def _numero_anexo(ruta, raiz):
    """Número de anexo y nombre, del propio archivo o de la carpeta 'Anexo N. …' que lo contiene."""
    for parte in ruta.relative_to(raiz).parts[::-1]:
        m = re.match(r'Anexo\s+(\d+)\.?\s*(.*)', Path(parte).stem if parte == ruta.name else parte, re.I)
        if m: return int(m.group(1)), m.group(2).strip()
    return None, ruta.stem


def _columna(ref):
    letras = re.match(r'[A-Z]+', ref).group()
    n = 0
    for ch in letras: n = n * 26 + ord(ch) - 64
    return n - 1


def leer_xlsx(ruta):
    """Hojas de un .xlsx como {nombre: [[celdas…], …]} usando solo la biblioteca estándar."""
    with zipfile.ZipFile(ruta) as z:
        compartidas = []
        if 'xl/sharedStrings.xml' in z.namelist():
            for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS):
                compartidas.append(''.join(t.text or '' for t in si.iter(f'{{{NS["m"]}}}t')))
        libro = ET.fromstring(z.read('xl/workbook.xml'))
        rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels')).findall('rel:Relationship', NS)}
        hojas = {}
        for h in libro.findall('m:sheets/m:sheet', NS):
            destino = rels[h.get(f'{{{NS["r"]}}}id')].lstrip('/')
            parte = destino if destino.startswith('xl/') else 'xl/' + destino
            filas = []
            for fila in ET.fromstring(z.read(parte)).iter(f'{{{NS["m"]}}}row'):
                valores = {}
                for c in fila.findall('m:c', NS):
                    v = c.find('m:v', NS)
                    if c.get('t') == 's' and v is not None: texto = compartidas[int(v.text)]
                    elif c.get('t') == 'inlineStr': texto = ''.join(t.text or '' for t in c.iter(f'{{{NS["m"]}}}t'))
                    else: texto = v.text if v is not None else ''
                    if texto not in (None, ''): valores[_columna(c.get('r'))] = str(texto).strip()
                if valores:
                    filas.append([valores.get(i, '') for i in range(max(valores) + 1)])
                if len(filas) >= MAX_FILAS_HOJA: break
            hojas[h.get('name')] = filas
        return hojas


def _texto_pdf(ruta, pdftotext, pdfinfo):
    texto = subprocess.run([pdftotext, '-enc', 'UTF-8', str(ruta), '-'], capture_output=True, text=True,
                           encoding='utf-8', errors='replace').stdout
    info = subprocess.run([pdfinfo, str(ruta)], capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
    m = re.search(r'Pages:\s+(\d+)', info)
    return re.sub(r'\n{3,}', '\n\n', texto.replace('\f', '\n')).strip(), int(m.group(1)) if m else None


def _firma(ruta):
    st = ruta.stat()
    return f'{st.st_size}-{int(st.st_mtime)}'


def extraer_anexos(carpeta, destino, poppler=None, con_ocr=True):
    """Indexa los anexos y escribe anexos.json: {archivos: [{codigo, numero, nombre, condicion, archivo, tipo, texto,
    paginas, tablas, estado}]}. Reutiliza lo ya leído de los archivos que no cambiaron. Los PDF escaneados pasan por OCR."""
    carpeta, destino = Path(carpeta), Path(destino)
    if not carpeta.exists():
        print(f'Aviso: no existe la carpeta de anexos {carpeta}; se omiten.')
        return None
    pdftotext, pdfinfo, pdftoppm = binario('pdftotext', poppler), binario('pdfinfo', poppler), binario('pdftoppm', poppler)
    motor = elegir_motor() if pdftoppm else None
    previo = {}
    if destino.exists():
        previo = {a['archivo']: a for a in json.loads(destino.read_text(encoding='utf-8'))['archivos']}
    archivos, vistos, por_anexo = [], {}, {}
    rutas = sorted(f for f in carpeta.rglob('*') if f.is_file() and f.suffix.lower() in ('.pdf', '.xlsx'))
    for ruta in rutas:
        numero, nombre = _numero_anexo(ruta, carpeta)
        rel = ruta.relative_to(carpeta).as_posix()
        condicion = ruta.relative_to(carpeta).parts[0]
        base = dict(numero=numero, nombre=nombre, condicion=condicion, archivo=rel, tipo=ruta.suffix.lower()[1:])
        if numero in OMITIR:
            archivos.append(dict(base, codigo=None, estado='omitido: ' + OMITIR[numero])); continue
        huella = hashlib.sha256(ruta.read_bytes()).hexdigest()
        if huella in vistos:
            archivos.append(dict(base, codigo=None, estado=f'omitido: repetido de {vistos[huella]}')); continue
        vistos[huella] = rel
        por_anexo.setdefault(numero, []).append(len(archivos))
        firma = _firma(ruta)
        falta_ocr = previo.get(rel, {}).get('escaneado') and not previo.get(rel, {}).get('ocr') and con_ocr and motor
        if rel in previo and previo[rel].get('firma') == firma and previo[rel].get('estado') == 'indexado' and not falta_ocr:
            archivos.append(dict(previo[rel], **base)); continue
        texto, paginas, tablas = '', None, []
        if base['tipo'] == 'pdf':
            texto, paginas = _texto_pdf(ruta, pdftotext, pdfinfo)
        else:
            for hoja, filas in leer_xlsx(ruta).items():
                tablas.append(dict(leyenda=f'Hoja «{hoja}»', filas=filas))
                texto += f'\n{hoja}\n' + '\n'.join(' | '.join(f) for f in filas[:400])
        poco_texto = base['tipo'] == 'pdf' and paginas and len(texto) < 150 * paginas
        if poco_texto and con_ocr and motor:
            # documento escaneado: el texto sale del OCR (caché por archivo en anexos.json)
            print(f'OCR del anexo escaneado {rel} ({paginas} páginas)…')
            lineas = ocr_pdf(ruta, motor, pdftoppm)
            texto = '\n'.join(' '.join(l) if isinstance(l, list) else l for p in sorted(lineas, key=int) for l in lineas[p])
        archivos.append(dict(base, firma=firma, texto=texto.strip(), paginas=paginas, tablas=tablas, estado='indexado',
                             escaneado=bool(poco_texto), ocr=bool(poco_texto and con_ocr and motor)))
    # Códigos: AX-12 si el anexo es un solo archivo; AX-46-01, AX-46-02… si es una carpeta
    for numero, indices in por_anexo.items():
        for k, i in enumerate(indices, 1):
            archivos[i]['codigo'] = f'AX-{numero:02d}' if len(indices) == 1 else f'AX-{numero:02d}-{k:02d}'
    destino.write_text(json.dumps(dict(archivos=archivos), ensure_ascii=False), encoding='utf-8')
    indexados = [a for a in archivos if a['estado'] == 'indexado']
    print(f'Anexos: {len(indexados)} archivos indexados de {len(por_anexo)} anexos, {len(archivos) - len(indexados)} omitidos, '
          f'{sum(1 for a in indexados if a.get("escaneado"))} con poco texto (posible escaneo) → {destino.name}')
    return dict(archivos=archivos)


def evidencias_anexos(datos):
    if not datos: return []
    out = []
    for a in datos['archivos']:
        if a['estado'] != 'indexado': continue
        titulo = f'Anexo {a["numero"]} · {a["nombre"]}' + (f' · {Path(a["archivo"]).stem}' if a['codigo'].count('-') == 2 else '')
        out.append(dict(codigo=a['codigo'], titulo=titulo[:110], tipo='anexo', texto=a['texto'] or None, texto_ocr=None,
                        fuente=f'Anexos RRC 2025 · {a["condicion"]}', archivo=a['archivo'], pagina=None, sede='Programa',
                        proceso='resignificacion', nivel='complementaria', _tablas=a['tablas']))
    return out
