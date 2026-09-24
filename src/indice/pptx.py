"""Extrae de los PPTX lo que el PDF no conserva: datos de las gráficas nativas y celdas de las tablas.

Solo lee las partes XML (los PPTX pesan cientos de MB por las imágenes). Las diapositivas se recorren
en el orden de la presentación, que debe coincidir con las páginas del PDF; se verifica comparando textos.
"""
import json
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
      'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}
R_ID = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
PATRON_FACTOR = re.compile(r'Factor[ _](\d+)', re.I)


def _rels(z, parte):
    d, b = posixpath.split(parte)
    rp = posixpath.join(d, '_rels', b + '.rels')
    if rp not in z.namelist(): return {}
    return {r.get('Id'): posixpath.normpath(posixpath.join(d, r.get('Target')))
            for r in ET.fromstring(z.read(rp)).findall('rel:Relationship', NS)}


def _limpiar(t):
    return re.sub(r'\s+', ' ', (t or '').replace('​', '')).strip()


def _numero(v):
    try: return float(v)
    except (TypeError, ValueError): return None


def _puntos(el):
    """{idx: valor} de un caché de gráfica (c:strCache o c:numCache); los puntos pueden ser dispersos."""
    return {int(p.get('idx')): p.findtext('c:v', namespaces=NS) for p in el.findall('.//c:pt', NS)} if el is not None else {}


def _categorias(cat):
    if cat is None: return {}
    multi = cat.find('.//c:multiLvlStrCache', NS)
    if multi is None: return {i: _limpiar(v) for i, v in _puntos(cat).items()}
    # Categorías de varios niveles: el nivel externo solo marca el primer índice de cada grupo
    pc = multi.find('c:ptCount', NS)
    n = int(pc.get('val')) if pc is not None else 0
    niveles = []
    for lvl in multi.findall('c:lvl', NS):
        pts = _puntos(lvl); actual = None; lleno = {}
        for i in range(n):
            actual = pts.get(i, actual); lleno[i] = _limpiar(actual)
        niveles.append(lleno)
    return {i: ' / '.join(nv[i] for nv in reversed(niveles) if nv.get(i)) for i in range(n)}


def _grafica(z, parte):
    x = ET.fromstring(z.read(parte))
    area = x.find('.//c:plotArea', NS)
    series = []
    for s in x.findall('.//c:ser', NS):
        nombre = _limpiar(' '.join(v.text or '' for v in s.findall('c:tx//c:v', NS)) or ' '.join(t.text or '' for t in s.findall('c:tx//a:t', NS)))
        cats = _categorias(s.find('c:cat', NS)) or _categorias(s.find('c:xVal', NS))
        vals = _puntos(s.find('c:val', NS)) or _puntos(s.find('c:yVal', NS))
        puntos = [[cats.get(i, str(i)), _numero(v)] for i, v in sorted(vals.items()) if _numero(v) is not None]
        if puntos: series.append(dict(nombre=nombre, puntos=puntos))
    return dict(titulo=_limpiar(' '.join(t.text or '' for t in x.findall('.//c:title//a:t', NS))),
                tipo=','.join(sorted({el.tag.split('}')[1] for el in area if el.tag.endswith('Chart')})) if area is not None else '',
                parte=parte, series=series)


def _tabla(t):
    return [[_limpiar(' '.join(x.text or '' for x in c.findall('.//a:t', NS))) for c in fila.findall('a:tc', NS)] for fila in t.findall('a:tr', NS)]


def leer_pptx(ruta):
    """Lista de diapositivas en orden: {'diapositiva', 'oculta', 'texto', 'graficas', 'tablas'}."""
    with zipfile.ZipFile(ruta) as z:
        pr = _rels(z, 'ppt/presentation.xml')
        orden = [pr[s.get(R_ID)] for s in ET.fromstring(z.read('ppt/presentation.xml')).findall('.//p:sldId', NS)]
        out = []
        for i, parte in enumerate(orden, 1):
            sx = ET.fromstring(z.read(parte)); r = _rels(z, parte)
            graficas = [_grafica(z, r[g.get(R_ID)]) for g in sx.findall('.//c:chart', NS) if g.get(R_ID) in r]
            out.append(dict(diapositiva=i, oculta=sx.get('show') == '0',
                            texto=_limpiar(' '.join(t.text or '' for t in sx.findall('.//a:t', NS))),
                            graficas=[g for g in graficas if g['series']],
                            graficas_vacias=sum(1 for g in graficas if not g['series']),
                            tablas=[_tabla(t) for t in sx.findall('.//a:tbl', NS)]))
        return out


def _palabras(t):
    return set(re.findall(r'[a-záéíóúñü]{4,}', t.lower()))


def extraer_pptx(carpeta, destino, diapositivas_pdf=None):
    """Escribe pptx.json. Si se da el texto del PDF, verifica que cada diapositiva visible coincida con su página."""
    pdf = {}
    if diapositivas_pdf and Path(diapositivas_pdf).exists():
        pdf = {(s['factor'], s['pagina']): s['texto'] for s in json.loads(Path(diapositivas_pdf).read_text(encoding='utf-8'))}
    archivos = sorted((int(m.group(1)), f) for f in Path(carpeta).glob('*.pptx') if (m := PATRON_FACTOR.match(f.name)))
    if not archivos:
        print(f'Aviso: no hay PPTX de factores en {carpeta}; se omiten gráficas y tablas.')
        return []
    out = []; dudosas = []
    for factor, ruta in archivos:
        pagina = 0
        for d in leer_pptx(ruta):
            if d['oculta']: continue  # las ocultas no se exportan al PDF
            pagina += 1
            if (factor, pagina) in pdf:
                a, b = _palabras(d['texto']), _palabras(pdf[(factor, pagina)])
                if a and b and len(a & b) / len(a | b) < 0.3:
                    dudosas.append(f'F{factor:02d}-P{pagina:03d}')
            if d['graficas'] or d['tablas']:
                out.append(dict(factor=factor, archivo=ruta.name, pagina=pagina, graficas=d['graficas'], tablas=d['tablas'],
                                graficas_vacias=d['graficas_vacias']))
    destino = Path(destino)
    destino.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    ng = sum(len(d['graficas']) for d in out); nt = sum(len(d['tablas']) for d in out)
    print(f'Extracción PPTX: {ng} gráficas y {nt} tablas en {len(out)} diapositivas de {len(archivos)} archivos → {destino}')
    if dudosas:
        print(f'Aviso: {len(dudosas)} diapositivas no se parecen a su página del PDF (revisar orden): {", ".join(dudosas[:10])}')
    return out
