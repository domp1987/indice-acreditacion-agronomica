"""Documentos maestros del programa como contexto e índice (uno por proceso, declarados en datos/semillas/documentos.csv).

- DM25: documento maestro RRC 2025 (renovación de registro calificado, Decreto 1330 de 2019) → proceso de resignificación.
- DM19: documento maestro de la resignificación MEN 2019 → sigue siendo la base del proceso de acreditación de alta calidad.

Los PDF salen de Word con estructura etiquetada: se lee el árbol lógico con 'pdfinfo -struct-text' (títulos H1–H3,
párrafos, listas y tablas celda por celda) y se arma una evidencia por sección ('DM25-4.6', 'DM19-3.2'…) con su página
de inicio y sus tablas. La lectura tarda un par de minutos: cada documento se guarda en caché (salida/maestro_<prefijo>.json)
y solo se repite si cambia el PDF.

Nota: la portada del documento de 2025 es, por error tipográfico, la de otro programa (Ingeniería en Robótica y
Automatización). Es solo una imagen sin texto, así que no entra al índice.
"""
import json
import re
import subprocess
from pathlib import Path

from indice.extraer import binario

def _nodos(struct_text):
    """Convierte la salida indentada de pdfinfo -struct-text en un árbol de dicts {tipo, textos, hijos}."""
    raiz = dict(tipo='Raiz', textos=[], hijos=[])
    pila = [(-1, raiz)]
    for linea in struct_text.splitlines():
        if not linea.strip(): continue
        sangria = len(linea) - len(linea.lstrip(' '))
        cont = linea.strip()
        if cont.startswith('"'):
            # texto del nodo en curso (el más reciente con menor sangría)
            texto = cont[1:-1] if cont.endswith('"') else cont[1:]
            while len(pila) > 1 and pila[-1][0] >= sangria: pila.pop()
            pila[-1][1]['textos'].append(texto)
            continue
        if cont.startswith('/'): continue   # atributos (/BBox, /Placement…)
        m = re.match(r'([A-Za-z][A-Za-z0-9]*)', cont)
        if not m: continue
        while len(pila) > 1 and pila[-1][0] >= sangria: pila.pop()
        nodo = dict(tipo=m.group(1), textos=[], hijos=[])
        pila[-1][1]['hijos'].append(nodo)
        pila.append((sangria, nodo))
    return raiz


def _texto(n):
    partes = list(n['textos']) + [_texto(h) for h in n['hijos']]
    return re.sub(r'\s+', ' ', ' '.join(p for p in partes if p)).strip()


def _tabla(n):
    filas = []

    def recorrer(x):
        if x['tipo'] == 'TR':
            filas.append([_texto(c) for c in x['hijos'] if c['tipo'] in ('TD', 'TH')])
        else:
            for h in x['hijos']: recorrer(h)
    recorrer(n)
    return [f for f in filas if any(f)]


def _bloques(raiz):
    """Secuencia de bloques en orden de lectura: ('H1'|'H2'|'H3', texto), ('P', texto), ('Caption', texto), ('Table', filas)."""
    out = []

    def recorrer(n):
        t = n['tipo']
        if t in ('H1', 'H2', 'H3', 'H4'):
            out.append((t, _texto(n))); return
        if t == 'Table':
            out.append(('Table', _tabla(n))); return
        if t == 'Caption':
            out.append(('Caption', _texto(n))); return
        if t in ('P', 'LI', 'Lbl', 'LBody') and not any(h['tipo'] in ('Table', 'H1', 'H2', 'H3') for h in n['hijos']):
            texto = _texto(n)
            if texto: out.append(('P', texto))
            return
        if t in ('TOC', 'TOCI', 'Figure', 'Artifact'): return   # tabla de contenido e imágenes (la portada)
        if n['textos'] and not n['hijos']:
            texto = ' '.join(n['textos']).strip()
            if texto: out.append(('P', texto))
        for h in n['hijos']: recorrer(h)
    recorrer(raiz)
    return out


def _normalizar(t):
    import unicodedata
    t = unicodedata.normalize('NFKD', t.lower()).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', ' ', t).strip()


def _paginas(pdf, pdftotext):
    texto = subprocess.run([pdftotext, '-enc', 'UTF-8', str(pdf), '-'], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', check=True).stdout
    return [_normalizar(p) for p in texto.split('\f')]


def _secciones(bloques, paginas, prefijo='DM'):
    """Una sección por título (H1–H3 no vacío). Código a partir de la numeración del título ('4.6' → 'DM25-4.6')."""
    secciones, actual, usados = [], None, set()
    buscar_desde = 0
    for tipo, valor in bloques:
        if tipo in ('H1', 'H2', 'H3', 'H4') and valor.strip(' .'):
            titulo = re.sub(r'\s+', ' ', valor).strip()
            m = re.match(r'^(\d+(?:\.\d+)*)\.?\s+(.*)', titulo)
            numero = m.group(1) if m else None
            base = f'{prefijo}-{numero}' if numero else f'{prefijo}-' + '-'.join(_normalizar(titulo).upper().split()[:4])
            codigo, k = base, 2
            while codigo in usados:
                codigo, k = f'{base}-{k}', k + 1
            usados.add(codigo)
            # página: primera página (desde la última sección) que contiene el título; se salta la tabla de contenido
            clave = _normalizar(m.group(2) if m else titulo)[:60]
            pagina = next((i + 1 for i in range(max(buscar_desde, 12), len(paginas)) if clave and clave in paginas[i]), None)
            if pagina: buscar_desde = pagina - 1
            actual = dict(codigo=codigo, numero=numero, titulo=titulo, nivel=int(tipo[1]), pagina=pagina, parrafos=[], tablas=[])
            secciones.append(actual)
            continue
        if actual is None:
            actual = dict(codigo=f'{prefijo}-PORTADA', numero=None, titulo='Portada y créditos', nivel=1, pagina=1, parrafos=[], tablas=[])
            secciones.append(actual); usados.add(actual['codigo'])
        if tipo == 'Table':
            leyenda = actual['parrafos'].pop() if actual['parrafos'] and actual['parrafos'][-1].startswith('Tabla ') else None
            actual['tablas'].append(dict(leyenda=leyenda, filas=valor))
        elif tipo == 'Caption':
            actual['parrafos'].append(valor)
        else:
            actual['parrafos'].append(valor)
    return secciones


def _firma(pdf):
    st = Path(pdf).stat()
    return f'{st.st_size}-{int(st.st_mtime)}'


def extraer_maestro(pdf, destino, poppler=None, prefijo='DM', proceso=None, titulo=None):
    """Lee un documento maestro (con caché) y escribe su JSON: {archivo, firma, prefijo, proceso, titulo_doc, secciones}."""
    destino = Path(destino)
    if not pdf:
        print('Aviso: no se encontró el documento maestro; se omite.')
        return None
    pdf = Path(pdf)
    if destino.exists():
        previo = json.loads(destino.read_text(encoding='utf-8'))
        if previo.get('firma') == _firma(pdf) and previo.get('archivo') == pdf.name and previo.get('prefijo') == prefijo:
            previo.update(proceso=proceso, titulo_doc=titulo or previo.get('titulo_doc'))
            print(f'{prefijo}: desde caché ({len(previo["secciones"])} secciones) → {destino.name}')
            return previo
    pdfinfo, pdftotext = binario('pdfinfo', poppler), binario('pdftotext', poppler)
    if not pdfinfo or not pdftotext:
        raise SystemExit('Se necesita poppler (pdfinfo, pdftotext) para leer el documento maestro.')
    print(f'Leyendo la estructura del documento maestro ({pdf.name}); tarda unos minutos la primera vez…')
    struct = subprocess.run([pdfinfo, '-enc', 'UTF-8', '-struct-text', str(pdf)], capture_output=True,
                            text=True, encoding='utf-8', errors='replace', check=True).stdout
    secciones = _secciones(_bloques(_nodos(struct)), _paginas(pdf, pdftotext), prefijo)
    datos = dict(archivo=pdf.name, firma=_firma(pdf), prefijo=prefijo, proceso=proceso, titulo_doc=titulo or pdf.stem, secciones=secciones)
    destino.write_text(json.dumps(datos, ensure_ascii=False), encoding='utf-8')
    print(f'{prefijo}: {len(secciones)} secciones, {sum(len(s["tablas"]) for s in secciones)} tablas → {destino.name}')
    return datos


# ---------- Tablas del plan de estudios propuesto (ruta 2025) ----------
ROMANOS = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10}


def _tabla_por_leyenda(datos, patron):
    for s in datos['secciones']:
        for t in s['tablas']:
            if t['leyenda'] and re.search(patron, t['leyenda'], re.I):
                return s['codigo'], t['filas']
    return None, []


def _num(t):
    m = re.search(r'\d+', t or '')
    return int(m.group()) if m else None


def plan_2025(datos):
    """Ruta de aprendizaje propuesta: período, campo, tipo, créditos y horas (Tabla 'Ruta de Aprendizaje … 2025'),
    con los créditos que da la tabla 'Distribución de los CADI' para contrastar."""
    seccion, filas = _tabla_por_leyenda(datos, r'Ruta de Aprendizaje del programa')
    _, distribucion = _tabla_por_leyenda(datos, r'Distribuci[oó]n de los CADI')
    cred_dist = {}
    for f in distribucion:
        if len(f) >= 2 and _num(f[1]) is not None: cred_dist.setdefault(_normalizar(f[0]), _num(f[1]))
    out, periodo = [], None
    for f in filas:
        if not f or not f[0]: continue
        if (m := re.match(r'Per[ií]odo\s+(\d+)', f[0], re.I)):
            periodo = int(m.group(1)); continue
        if f[0].lower().startswith(('total', 'denominaci')) or len(f) < 4 or periodo is None: continue
        c = f + [''] * (10 - len(f))
        institucional = c[0].upper().startswith('CAI') or c[8].strip().lower() == 'x'
        out.append(dict(orden=len(out) + 1, periodo=periodo, nombre=re.sub(r'\s+', ' ', c[0]).strip(),
                        tipo='institucional' if institucional else 'disciplinar', obligatorio=1 if c[1].strip().lower() == 'x' else 0,
                        creditos=_num(c[3]), horas_acompanamiento=_num(c[4]), horas_independiente=_num(c[5]), horas_total=_num(c[6]),
                        max_estudiantes=_num(c[9]), creditos_distribucion=cred_dist.get(_normalizar(c[0])), seccion=seccion))
    return out


def transicion_2025(datos):
    """Plan de transición ruta 2020 → 2026: curso vigente, curso propuesto y si se homologa (H) o requiere curso complementario."""
    _, filas = _tabla_por_leyenda(datos, r'Plan de transici[oó]n')
    out, vigente = [], (None, None, None)
    for f in filas:
        i = next((k for k in range(1, len(f)) if f[k].strip() in ROMANOS and k >= 3), None)   # semestre del plan propuesto
        if i is None: continue
        if f[0].strip():
            vigente = (f[0].strip(), ROMANOS.get(f[1].strip()), _num(f[2]))
        propuesto = f[i - 1].strip()
        if not propuesto: continue
        tipo = f[i + 2].strip() if len(f) > i + 2 else ''
        out.append(dict(orden=len(out) + 1, curso_vigente=vigente[0], semestre_vigente=vigente[1], creditos_vigente=vigente[2],
                        curso_propuesto=propuesto, semestre_propuesto=ROMANOS.get(f[i].strip()), creditos_propuesto=_num(f[i + 1]),
                        tipo=tipo or None))
    return out


def rea_por_cadi(datos):
    """Matriz de REA específicos por CADI del plan propuesto: perfil, código, créditos, campo, consecutivo y texto."""
    _, filas = _tabla_por_leyenda(datos, r'Matriz de relaci[oó]n de los resultados de aprendizaje espec')
    out, cadi = [], None
    for f in filas[1:]:
        c = f + [''] * (6 - len(f))
        if c[1].strip():
            cadi = dict(perfil=c[0].strip() or None, codigo_cadi=c[1].strip(), creditos=_num(c[2]), campo=re.sub(r'\s+', ' ', c[3]).strip())
        if cadi is None: continue
        texto = c[5].strip()
        if c[4].strip():
            out.append(dict(cadi, consecutivo=_num(c[4]), texto=None if texto.upper() == 'NA' else texto))
        elif texto and out and out[-1]['codigo_cadi'] == cadi['codigo_cadi']:
            out[-1]['texto'] = ((out[-1]['texto'] or '') + ' ' + texto).strip()   # continuación de la celda
    return out


def evidencias_maestro(datos):
    """Cada sección como evidencia (tipo 'documento_maestro'); sus tablas van aparte (tabla_diapositiva)."""
    if not datos: return []
    out = []
    for s in datos['secciones']:
        texto = '\n'.join(s['parrafos']).strip()
        for t in s['tablas']:   # las tablas también cuentan para la búsqueda
            texto += '\n' + (t['leyenda'] or 'Tabla') + '\n' + '\n'.join(' | '.join(f) for f in t['filas'])
        if not texto.strip() and not s['tablas']: continue
        out.append(dict(codigo=s['codigo'], titulo=f'{datos["titulo_doc"]} · {s["titulo"]}'[:110], tipo='documento_maestro',
                        texto=texto.strip(), texto_ocr=None, fuente=datos['titulo_doc'], archivo=datos['archivo'],
                        pagina=s['pagina'], sede='Programa', proceso=datos.get('proceso'), _tablas=s['tablas']))
    return out


def extraer_maestros(raiz, documentos, salida, poppler=None):
    """Lee los documentos maestros declarados en documentos.csv (patrón del nombre de archivo, prefijo, proceso).
    Cada uno se guarda en salida/maestro_<prefijo>.json. Devuelve la lista de documentos leídos."""
    leidos = []
    for d in documentos:
        pdf = next((f for f in sorted(Path(raiz).glob('*.pdf')) if d['patron'].lower() in f.name.lower()), None)
        if not pdf:
            print(f'Aviso: no se encontró el documento {d["prefijo"]} (patrón "{d["patron"]}"); se omite.')
            continue
        leidos.append(extraer_maestro(pdf, Path(salida) / f'maestro_{d["prefijo"]}.json', poppler, d['prefijo'], d['proceso'], d['titulo']))
    return leidos


def leer_maestros(salida):
    """Los documentos maestros ya extraídos (salida/maestro_*.json)."""
    return [json.loads(f.read_text(encoding='utf-8')) for f in sorted(Path(salida).glob('maestro_*.json'))]
