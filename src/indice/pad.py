"""Extracción de los Planes de Aprendizaje Digital (PAD) de cada CADI.

Los PAD son formularios generados desde HTML (iText/pdfHTML) sin estructura etiquetada, en dos plantillas:
- V1.9: filas "etiqueta | valor" con la etiqueta centrada verticalmente respecto a su valor, experiencias
  ("Vive una experiencia"), un problema ("Soluciona un problema") por etapas y actividades con lugares,
  tipo de actividad, instrumentos y recursos; bibliografía con ISBN.
- V2: encabezado en bloques, experiencias con descripción y una tabla ancha de actividades por columnas.

El análisis es geométrico sobre las palabras (pdftotext -tsv): se reconstruyen líneas, se parten en columnas,
se agrupan en celdas y cada celda de valor se asigna a la etiqueta (o actividad) cuya fila la contiene.
Se guarda además el texto completo de cada PAD para búsqueda.

El nombre del profesor líder no se extrae: es un dato personal (CLAUDE.md, privacidad).
"""
import csv
import io
import json
import re
import subprocess
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from indice.extraer import binario, ejecutar


# ---------- Geometría: palabras → líneas → segmentos → celdas ----------
@dataclass
class Seg:
    p: int
    x0: float
    y0: float
    x1: float
    y1: float
    t: str
    palabras: list = None   # palabras que lo forman (para volver a partirlo por columnas)

    @property
    def yc(self): return (self.y0 + self.y1) / 2

    @property
    def h(self): return self.y1 - self.y0


@dataclass
class Celda:
    lineas: list = field(default_factory=list)   # Seg ordenados por y

    @property
    def p(self): return self.lineas[0].p

    @property
    def x0(self): return min(s.x0 for s in self.lineas)

    @property
    def x1(self): return max(s.x1 for s in self.lineas)

    @property
    def y0(self): return self.lineas[0].y0

    @property
    def y1(self): return self.lineas[-1].y1

    @property
    def yc(self): return (self.y0 + self.y1) / 2

    @property
    def t(self): return '\n'.join(s.t for s in self.lineas)


def _palabras(pdf, pdftotext):
    tsv = subprocess.run([pdftotext, '-enc', 'UTF-8', '-tsv', str(pdf), '-'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace', check=True).stdout
    out = []
    for r in csv.DictReader(io.StringIO(tsv), delimiter='\t', quoting=csv.QUOTE_NONE):
        if r['level'] != '5' or not r['text'].strip(): continue
        x, y, w, h = (float(r[k]) for k in ('left', 'top', 'width', 'height'))
        out.append(Seg(int(r['page_num']), x, y, x + w, y + h, r['text']))
    return out


def _lineas(palabras):
    """Agrupa palabras por página y altura en líneas visuales (listas de palabras ordenadas por x)."""
    lineas = []
    for w in sorted(palabras, key=lambda w: (w.p, w.y0, w.x0)):
        if lineas and lineas[-1][0].p == w.p and abs(lineas[-1][0].y0 - w.y0) < 2.5:
            lineas[-1].append(w)
        else:
            lineas.append([w])
    return [sorted(l, key=lambda w: w.x0) for l in lineas]


def _columnas(lineas):
    """Inicios de columna del documento: x donde empiezan (tras un hueco grande) al menos 3 líneas."""
    conteo = {}
    for l in lineas:
        for i, w in enumerate(l):
            if i == 0 or w.x0 - l[i - 1].x1 > 8:
                k = round(w.x0)
                conteo[k] = conteo.get(k, 0) + 1
    return sorted(k for k, n in conteo.items() if n >= 3)


def _segmentos(lineas, columnas):
    """Parte cada línea donde hay un hueco grande, o uno moderado que cae justo en un inicio de columna."""
    segs = []
    for l in lineas:
        actual = [l[0]]
        for prev, w in zip(l, l[1:]):
            hueco = w.x0 - prev.x1
            en_columna = any(abs(w.x0 - c) <= 1.5 for c in columnas)
            if hueco > 8 or (hueco > 3.2 and en_columna):
                segs.append(actual); actual = [w]
            else:
                actual.append(w)
        segs.append(actual)
    return [Seg(s[0].p, s[0].x0, min(w.y0 for w in s), s[-1].x1, max(w.y1 for w in s), ' '.join(w.t for w in s), s) for s in segs]


FRASES_ETIQUETA = [['Descripción', 'de', 'la', 'actividad'], ['Descripción', 'de', 'la']]


def _separar_frases(segs):
    """Separa etiquetas que el PDF deja pegadas a otro texto en la misma línea ('PLATAFORMA EDUCATIVA Descripción de la
    actividad' → dos segmentos), usando las palabras del segmento."""
    out = []
    for s in segs:
        ws = s.palabras or []
        corte = None
        for frase in FRASES_ETIQUETA:
            for i in range(len(ws) - len(frase) + 1):
                if [w.t for w in ws[i:i + len(frase)]] == frase and (i > 0 or i + len(frase) < len(ws)):
                    corte = (i, i + len(frase)); break
            if corte: break
        if not corte:
            out.append(s); continue
        for a_, b_ in ((0, corte[0]), corte, (corte[1], len(ws))):
            parte = ws[a_:b_]
            if parte:
                out.append(Seg(s.p, parte[0].x0, min(w.y0 for w in parte), parte[-1].x1, max(w.y1 for w in parte), ' '.join(w.t for w in parte), parte))
    return out


def _celdas(segs, tolerancia_x=2.0):
    """Agrupa segmentos de la misma columna (mismo x0) y verticalmente contiguos en celdas de varias líneas."""
    celdas = []
    abiertas = {}   # (página, x0 redondeado) → celda en curso
    for s in sorted(segs, key=lambda s: (s.p, s.y0, s.x0)):
        clave = next((k for k in abiertas if k[0] == s.p and abs(k[1] - s.x0) <= tolerancia_x), None)
        if clave:
            c = abiertas[clave]
            if s.y0 - c.y1 <= 0.45 * s.h:
                c.lineas.append(s); continue
        c = Celda([s]); celdas.append(c)
        if clave: del abiertas[clave]
        abiertas[(s.p, s.x0)] = c
    return sorted(celdas, key=lambda c: (c.p, c.y0, c.x0))


# ---------- Utilidades de texto ----------
def normalizar(t):
    """Para comparar etiquetas: sin tildes, minúsculas, sin signos. La plantilla V2 pierde las letras con tilde
    ('Nmero de crditos'), así que las letras no ASCII se eliminan en ambos lados."""
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', t).strip()


def _sin_vocales_tildadas(t):
    """'Número de créditos' → 'nmero de crditos' (como lo escribe la plantilla V2)."""
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', '', ''.join(ch for ch in t.lower() if ord(ch) < 128))).strip()


def _limpio(t):
    t = (t or '').replace('¿ ', '• ').replace('​', '')
    return re.sub(r'[ \t]+', ' ', t).strip()


def _parrafo(celdas):
    """Texto de varias celdas unido como párrafo (las líneas de una celda son cortes visuales, no párrafos)."""
    return _limpio(' '.join(re.sub(r'\s*\n\s*', ' ', c.t) for c in celdas)) or None


_VINETA = re.compile(r'^(•|¿(?=\s))\s*')   # la viñeta a veces llega como '¿ ' (codificación del PDF)
_ETIQUETA_SUELTA = re.compile(r'^(Componentes|genéricos asociados|Componentes genéricos asociados)$')


def _lista(celdas, vinetas):
    """Elementos de una lista con viñetas: cada viñeta (suelta o al inicio de la línea) abre un elemento; las líneas
    sin viñeta continúan el anterior. Una línea puede traer varios elementos: 'Cultura • Institución'."""
    items = []
    for c in celdas:
        for s in c.lineas:
            t = s.t.strip()
            if t in ('•', '¿') or _ETIQUETA_SUELTA.match(t): continue
            nuevo = bool(_VINETA.match(t)) or any(v.p == s.p and abs(v.yc - s.yc) < 3 for v in vinetas) or not items
            partes = [x for x in re.split(r'\s+•\s+', _VINETA.sub('', t)) if x]
            if not partes: continue
            if nuevo: items.append(partes[0])
            else: items[-1] += ' ' + partes[0]
            items += partes[1:]
    items = [_limpio(re.sub(r'\s*(Componentes\s+)?genéricos asociados$', '', i)) for i in items]
    return [i for i in items if i and not _ETIQUETA_SUELTA.match(i)]


def _entero(t):
    m = re.search(r'\d+', t or '')
    return int(m.group()) if m else None


# ---------- Etiquetas ----------
ETIQUETAS_IZQ = {
    'dimensiones': 'dimensiones', 'rea especifico': 'rea', 'descripcion': 'descripcion',
    'competencia generica saber pro': 'competencia', 'trabajo estudiante': 'trabajo_estudiante',
    'trabajo gestor del conocimiento profesor': 'trabajo_profesor', 'trabajo profesor': 'trabajo_profesor',
    'lugares': 'lugares', 'instrumentos de recoleccion de datos': 'instrumentos', 'instrumentos de recoleccion': 'instrumentos',
    'recursos cgca': 'recursos_cgca', 'recursos externos y o propios': 'recursos_externos',
    'unidad regional': 'unidad_regional', 'lineas translocales': 'lineas_translocales',
    'postulados persona transhumana': 'postulados', 'mejoras': 'mejoras', 'transformaciones': 'transformaciones',
    'semana inicio': 'semana_inicio', 'descripcion de la fase': 'fase',
    # variante 2026 (actividades desglosadas por semana)
    'lugar': 'lugares', 'fase': 'fase', 'trabajo del creador de oportunidades estudiante': 'trabajo_estudiante',
    'descripcion de la fase 7 y 8': 'analisis_retroalimentacion',
}
# Etiquetas de la columna central (variante 2026): su valor es la celda a la derecha
ETIQUETAS_MEDIO = {'descripcion de la actividad': 'descripcion'}
# Marcadores dentro de una actividad (variante 2026)
MARCA_SEMANA = re.compile(r'^Trabajo en la semana (\d+)', re.I)
MARCA_RECURSOS = re.compile(r'^Fase \d+\.\s*Socializaci.*Recursos', re.I)
MARCA_RECOLECCION = re.compile(r'^Fase \d+\.\s*Recolecci', re.I)
TIPO_INSTRUMENTO = re.compile(r'^(Tarea|Taller|Foro|Cuestionario|Consulta|Encuesta|Wiki|Base de datos|Lecci[oó]n|Glosario|Portafolio|R[uú]brica|Otro)$', re.I)
SIN_ELEMENTOS = re.compile(r'^(No hay elementos registrados|Sin recursos registrados|No hay datos)$', re.I)
ETIQUETAS_DER = {
    'integrantes': 'integrantes', 'componentes genericos asociados': 'componentes', 'semana inicio': 'semana_inicio',
    'duracion': 'duracion', 'tipo actividad': 'tipo_actividad', 'descripcion de los instrumentos': 'descripcion_instrumentos',
    'descripcion instrumentos': 'descripcion_instrumentos', 'descripcion': 'descripcion_transformaciones',
}
ENCABEZADO = {
    'nombre del cad': 'nombre', 'codigo del cad': 'codigo', 'ubicacion semestral': 'semestre',
    'prerrequisitos si aplica': 'prerrequisitos', 'numero de creditos': 'creditos', 'nombre profesor lider': None,
    'facultad unidad misional': 'facultad', 'programa academico': 'programa',
    'nombre del gestor del conocimiento lider': None, 'relacion de creditos': 'relacion_creditos',
}
# Variantes sin letras tildadas (plantilla V2)
ENCABEZADO.update({_sin_vocales_tildadas(k.replace('codigo', 'código').replace('ubicacion', 'ubicación').replace('numero', 'número')
                                         .replace('creditos', 'créditos').replace('lider', 'líder').replace('academico', 'académico')): v
                   for k, v in list(ENCABEZADO.items())})


def _etiqueta(texto, tabla):
    n = normalizar(texto)
    if n in tabla: return tabla[n]
    s = _sin_vocales_tildadas(texto)
    return tabla.get(s)


# ---------- Documento ----------
def _texto_completo(pdf, pdftotext):
    return re.sub(r'\n{3,}', '\n\n', ejecutar([pdftotext, '-enc', 'UTF-8', '-layout', str(pdf), '-'])).strip()


def _encabezado(segs):
    """Pares etiqueta/valor del encabezado: el valor es el segmento a la derecha en la misma línea."""
    datos = {}
    primera = [s for s in segs if s.p == 1]
    for s in primera:
        clave = _etiqueta(s.t, ENCABEZADO)
        if not clave: continue
        derecha = sorted((v for v in primera if abs(v.yc - s.yc) < 3 and v.x0 > s.x1 + 5), key=lambda v: v.x0)
        if derecha and _etiqueta(derecha[0].t, ENCABEZADO) is None:
            datos[clave] = _limpio(derecha[0].t)
    return datos


def _bloque_bajo(celdas, titulo, hasta):
    """Celdas entre el título de sección y el siguiente título."""
    i = next((k for k, c in enumerate(celdas) if normalizar(c.t).startswith(titulo)), None)
    if i is None: return []
    out = []
    for c in celdas[i + 1:]:
        if any(normalizar(c.t).startswith(h) for h in hasta): break
        out.append(c)
    return out


def _rea_especificos(celdas):
    """Números de consecutivo y texto; cada línea de texto va al número más cercano en altura."""
    bloque = _bloque_bajo(celdas, 'rea especific', ['para el logro', 'vive una experiencia', 'soluciona un problema', 'fases del mca'])
    bloque = [c for c in bloque if not normalizar(c.t).startswith('fases del mca')]
    numeros, lineas, pesos = [], [], []
    for c in bloque:
        if normalizar(c.t) in ('consecutivo', 'nombre', 'consecutivo nombre', 'porcentaje'): continue
        for s in c.lineas:
            t = s.t.strip()
            if re.fullmatch(r'\d{1,2}', t): numeros.append(s)
            elif re.fullmatch(r'\d+([.,]\d+)?\s*%', t): pesos.append(s)   # variante 2026: peso del REA
            elif normalizar(t) not in ('nombre', 'consecutivo', 'porcentaje', 'total'): lineas.append(s)
    if not numeros:
        return [dict(consecutivo=1, texto=_limpio(' '.join(s.t for s in lineas)))] if lineas else []
    rea, peso = {}, {}
    for s in sorted(lineas, key=lambda s: (s.p, s.y0)):
        n = min(numeros, key=lambda k: (k.p != s.p, abs(k.yc - s.yc)))
        rea.setdefault(int(n.t), []).append(s.t)
    for s in pesos:
        n = min(numeros, key=lambda k: (k.p != s.p, abs(k.yc - s.yc)))
        if abs(n.yc - s.yc) < 8: peso[int(n.t)] = float(s.t.strip().rstrip('%').strip().replace(',', '.'))
    return [dict(consecutivo=k, texto=_limpio(' '.join(v)), peso=peso.get(k)) for k, v in sorted(rea.items())]


def _fases_mca(segs):
    """Tabla 'Fases del MCA' (variante 2026): fase y descripción de lo que ocurre en ella en este CADI."""
    enc = next((s for s in segs if normalizar(s.t) == 'fases del mca'), None)
    if not enc: return []
    fin = next(((s.p, s.y0) for s in sorted(segs, key=lambda s: (s.p, s.y0))
                if (s.p, s.y0) > (enc.p, enc.y1) and normalizar(s.t) in ('vive una experiencia', 'soluciona un problema')), (1e9, 0))
    cuerpo = [s for s in segs if (enc.p, enc.y1) < (s.p, s.y0) < fin and normalizar(s.t) not in ('fase', 'descripcion')]
    if not cuerpo or all(SIN_ELEMENTOS.match(s.t.strip()) for s in cuerpo): return []
    x_desc = min((s.x0 for s in cuerpo if len(s.t) > 60), default=250) - 5
    anclas = [s for s in cuerpo if s.x0 < x_desc and re.match(r'Fase \d+', s.t)]
    filas = [dict(_a=a, fase=[], descripcion=[]) for a in anclas]
    if not filas: return []
    for s in sorted(cuerpo, key=lambda s: (s.p, s.y0, s.x0)):
        f = min(filas, key=lambda f: (f['_a'].p != s.p, abs(f['_a'].yc - s.yc)))
        f['fase' if s.x0 < x_desc else 'descripcion'].append(s.t)
    return [dict(fase=_limpio(' '.join(f['fase'])), descripcion=_limpio(' '.join(f['descripcion'])) or None) for f in filas]


def _tabla(segs, encabezados, parar):
    """Tabla bajo una fila de encabezados {clave: Seg}. Los encabezados van centrados y los valores alineados a la
    izquierda, así que las columnas se toman de los x de inicio de los valores y se emparejan en orden con los
    encabezados. Devuelve [(Seg, clave)] del cuerpo, hasta la primera línea que cumpla 'parar' o el fin de página."""
    enc = sorted(encabezados.items(), key=lambda kv: kv[1].x0)
    p, y_enc = enc[0][1].p, max(s.y1 for _, s in enc)
    cuerpo = sorted((s for s in segs if s.p == p and s.y0 > y_enc + 1), key=lambda s: (s.y0, s.x0))
    fin = next((s.y0 for s in cuerpo if parar(s)), 1e9)
    cuerpo = [s for s in cuerpo if s.y0 < fin]
    grupos = []
    for x in sorted(s.x0 for s in cuerpo):
        if not grupos or x - grupos[-1][-1] > 20: grupos.append([x])
        else: grupos[-1].append(x)
    inicios = [g[0] for g in grupos]
    if len(inicios) == len(enc):
        mapa = {x: k for x, (k, _) in zip(inicios, enc)}
    else:   # columnas vacías o líneas envueltas: cada grupo va al encabezado cuyo centro está más cerca del centro del grupo
        centros = {}
        for s in cuerpo:
            g = max(x for x in inicios if x <= s.x0 + 0.5)
            centros.setdefault(g, []).append((s.x0 + s.x1) / 2)
        mapa = {x: min(enc, key=lambda kv: abs((kv[1].x0 + kv[1].x1) / 2 - sum(centros[x]) / len(centros[x])))[0] for x in inicios}

    def columna(s):
        return mapa[max(x for x in inicios if x <= s.x0 + 0.5)]
    return [(s, columna(s)) for s in cuerpo]


def _filas_por_ancla(pares, ancla):
    """Agrupa [(Seg, clave)] en filas: cada segmento de la columna 'ancla' abre una fila y el resto va a la fila
    de centro más cercano. Varias líneas de una misma columna se concatenan."""
    anclas = [s for s, k in pares if k == ancla]
    filas = [dict(_y=a.yc) for a in anclas]
    if not filas: return []
    for s, k in pares:
        f = min(filas, key=lambda f: abs(f['_y'] - s.yc))
        f[k] = _limpio(f.get(k, '') + ' ' + s.t)
    for f in filas: f.pop('_y')
    return filas


def _bibliografia(celdas, segs):
    """Bibliografía: encabezados Autor / Nombre o Título / Año / ISBN o Estandarizado (y Editorial en V2)."""
    out = []
    claves = {'autor': 'autor', 'nombre': 'titulo', 'titulo': 'titulo', 'ttulo': 'titulo', 'ano': 'anio', 'ao': 'anio',
              'isbn': 'isbn', 'estandarizado': 'identificador', 'editorial': 'editorial', 'e v': 'edicion', 'url': 'url'}
    for a in (s for s in segs if normalizar(s.t) == 'autor'):
        encabezados = {}
        for s in segs:
            if s.p != a.p or abs(s.yc - a.yc) > 12: continue
            n = normalizar(s.t)
            n = n.split()[-1] if n.split() and n.split()[-1] in claves else n
            if n in claves: encabezados[claves[n]] = s
        if 'titulo' not in encabezados or 'anio' not in encabezados: continue
        pares = _tabla(segs, encabezados, lambda s: normalizar(s.t).startswith(('recursos', 'bibliografia', 'nombre del recurso')))
        for f in _filas_por_ancla(pares, 'anio'):
            f['anio'] = _entero((f.get('anio') or '').replace(',', '').replace('.', '')) or None
            if f.get('url'): f['url'] = f['url'].replace(' ', '')   # las URL largas se parten en varias líneas
            if f.get('isbn') in ('-', ''): f['isbn'] = None
            if f.get('titulo'): out.append(f)
    return out


def _recursos_externos(celdas, segs):
    """Tabla final 'Recursos externos y/o propios': nombre, tipo de recurso educativo y área de conocimiento."""
    out = []
    for a in (s for s in segs if normalizar(s.t) == 'nombre del recurso'):
        fila = sorted((s for s in segs if s.p == a.p and abs(s.yc - a.yc) < 6), key=lambda s: s.x0)
        if len(fila) < 3: continue
        encabezados = dict(zip(['nombre', 'tipo', 'area'], fila[:3]))
        pares = _tabla(segs, encabezados, lambda s: normalizar(s.t).startswith(('bibliografia', 'autor', 'recursos cgca')))
        out += [f for f in _filas_por_ancla(pares, 'nombre') if f.get('nombre')]
    return out


# ---------- Filas etiqueta/valor (plantilla V1.9) ----------
TITULO = re.compile(r'^(Experiencia|Actividad|Nombre de la actividad|Etapa \d+|Problema)\s*:', re.I)
SECCIONES = ('vive una experiencia', 'soluciona un problema', 'acciones', 'bibliografia')


def _filas_v19(celdas, segs):
    """Recorre el documento y arma experiencias, etapas y actividades con sus campos."""
    vinetas = [s for s in segs if s.t.strip() in ('•', '¿') and s.x1 - s.x0 < 5]
    x_etiqueta = 37.5
    # Etiquetas izquierdas: líneas de la columna de etiquetas (x1 < 132), alineadas a la izquierda o centradas,
    # que pueden ocupar varias líneas ('Trabajo gestor del' + 'conocimiento' + '(profesor)')
    zona = sorted((s for s in segs if s.x1 < 132 and s.t.strip() not in ('•', '¿')), key=lambda s: (s.p, s.y0))
    grupos = []
    for s in zona:
        if grupos and grupos[-1][-1].p == s.p and s.y0 - grupos[-1][-1].y1 <= 1.3 * s.h: grupos[-1].append(s)
        else: grupos.append([s])
    etiquetas = []
    for g in grupos:
        i = 0
        while i < len(g):   # la etiqueta más larga que empiece en i
            for j in range(len(g), i, -1):
                clave = _etiqueta(' '.join(x.t for x in g[i:j]), ETIQUETAS_IZQ)
                if clave:
                    etiquetas.append((clave, Celda(g[i:j]))); i = j; break
            else:
                i += 1
    der = [(k, c) for c in celdas if c.x0 > x_etiqueta + 150 and (k := _etiqueta(c.t.replace('\n', ' '), ETIQUETAS_DER))]
    # Etiquetas de la columna central (variante 2026), centradas y en una o dos líneas
    corto = sorted((s for s in segs if 150 <= s.x0 and s.x1 <= 362 and len(s.t) < 30), key=lambda s: (s.p, s.y0, s.x0))
    medio, previo = [], None
    for s in corto:
        debajo = previo and previo.p == s.p and 0 <= s.y0 - previo.y1 <= 0.6 * s.h and abs((s.x0 + s.x1) - (previo.x0 + previo.x1)) < 80
        al_lado = previo and previo.p == s.p and abs(s.yc - previo.yc) < 2 and 0 <= s.x0 - previo.x1 < 8
        if debajo or al_lado:
            if (k := _etiqueta(previo.t + ' ' + s.t, ETIQUETAS_MEDIO)):
                medio.append((k, Celda([previo, s]))); previo = None; continue
        if (k := _etiqueta(s.t, ETIQUETAS_MEDIO)):
            medio.append((k, Celda([s]))); previo = None; continue
        previo = s
    # Títulos que abren registros, en orden, y marcadores internos de la actividad (variante 2026)
    titulos = [c for c in celdas if TITULO.match(c.t) or normalizar(c.t) in SECCIONES]
    marcas = [Celda([s]) for s in segs if MARCA_SEMANA.match(s.t) or MARCA_RECURSOS.match(s.t) or MARCA_RECOLECCION.match(s.t)]
    ids_marcas = {id(s) for m in marcas for s in m.lineas}
    etiq_celdas = {id(c) for _, c in der} | {id(c) for c in titulos} | {id(c) for c in celdas if any(id(x) in ids_marcas for x in c.lineas)}
    etiq_segs = {id(s) for _, c in medio for s in c.lineas}
    valores = [c for c in celdas if id(c) not in etiq_celdas and c.x1 >= 132 and c.x0 > x_etiqueta + 50
               and c.t.strip() not in ('•', '¿') and not any(id(s) in etiq_segs for s in c.lineas)]

    def pos(c): return (c.p, c.y0)
    # Lo que sigue a la bibliografía son tablas propias, no valores de la última etiqueta
    limite = min((pos(c) for c in titulos if normalizar(c.t) == 'bibliografia'), default=(1e9, 0))
    valores = [v for v in valores if pos(v) < limite]
    # Bloques de recursos y de recolección de datos: van desde su marcador hasta el siguiente título, marcador o etiqueta
    fronteras = sorted([pos(c) for c in titulos + marcas] + [pos(c) for _, c in etiquetas + der + medio] + [limite])
    bloques = {}
    for m in marcas:
        if MARCA_SEMANA.match(m.t): continue
        fin = next((f for f in fronteras if f > (m.p, m.y1 - 1)), limite)
        bloques[id(m)] = [s for s in segs if (m.p, m.y1 - 1) < pos(s) < fin and s.t.strip() not in ('•',)]
    en_bloque = {id(s) for ss in bloques.values() for s in ss}
    valores = [v for v in valores if not any(id(s) in en_bloque for s in v.lineas)]
    # Valores de las etiquetas centrales: la celda a su derecha que contiene su centro
    centrales = {}
    for k, m in medio:
        cerca = [v for v in valores if v.p == m.p and v.x0 > m.x1 + 3 and v.y0 - 4 <= m.yc <= v.y1 + 4]
        centrales[id(m)] = cerca
    usadas = {id(v) for vs in centrales.values() for v in vs}
    valores = [v for v in valores if id(v) not in usadas]

    # Asigna cada celda de valor a una etiqueta izquierda: la que tiene su centro dentro de la celda;
    # si ninguna (continuación tras un salto de página), la última etiqueta anterior.
    asignadas = {id(c): [] for _, c in etiquetas}
    for v in valores:
        if v.x0 > x_etiqueta + 250 and any(abs(v.yc - d.yc) < 30 and v.p == d.p and v.x0 > d.x1 for _, d in der):
            continue   # valor de una etiqueta derecha
        dentro = [c for _, c in etiquetas if c.p == v.p and v.y0 - 3 <= c.yc <= v.y1 + 3]
        if dentro:
            asignadas[id(min(dentro, key=lambda c: abs(c.yc - v.yc)))].append(v); continue
        previas = [c for _, c in etiquetas if pos(c) < pos(v)]
        if previas: asignadas[id(max(previas, key=pos))].append(v)
    # Valores de etiquetas derechas: celdas a su derecha en la misma franja
    derechos = {}
    for k, d in der:
        cerca = [v for v in valores if v.p == d.p and v.x0 > d.x1 + 3 and v.y0 - 6 <= d.yc <= v.y1 + 6]
        if cerca:
            x = min(v.x0 for v in cerca)
            derechos[id(d)] = [v for v in cerca if v.x0 < x + 150]

    # Recorre títulos y etiquetas en orden de lectura
    eventos = sorted([('titulo', c.t, c) for c in titulos] + [('izq', k, c) for k, c in etiquetas] + [('der', k, c) for k, c in der]
                     + [('medio', k, c) for k, c in medio] + [('marca', c.t, c) for c in marcas],
                     key=lambda e: (e[2].p, e[2].y0, e[2].x0))
    experiencias, acciones = [], {}
    seccion, exp, etapa, act, semana = None, None, None, None, None

    def acumular(destino, k, valor):
        """Una actividad desglosada por semanas repite campos: los textos se unen y las listas se extienden."""
        if not valor: return
        if k == 'lugares' and isinstance(valor, list):
            # en la variante 2026 la descripción de la semana a veces se cuela en la columna de lugares
            largos = [x for x in valor if len(x) > 70]
            valor = [x for x in valor if len(x) <= 70]
            if largos: acumular(destino, 'descripcion', ' '.join(largos))
            if not valor: return
        if k == 'instrumentos' and isinstance(valor, list):
            # a veces la celda trae la descripción del producto en lugar del tipo de instrumento
            largos = [x for x in valor if len(x) > 60]
            valor = [x for x in valor if len(x) <= 60]
            if largos: acumular(destino, 'descripcion_instrumentos', ' '.join(largos))
            if not valor: return
        if k == 'fase':
            previas =[x.strip() for x in re.split(r'[;,]', destino.get('fase') or '') if x.strip()]
            nuevas = re.findall(r'FASE \d+\.\s*[A-ZÁÉÍÓÚÑ]{2,}(?:\s+(?:Y|[A-ZÁÉÍÓÚÑ]{2,}))*', valor)
            destino[k] = '; '.join(previas + [x for x in nuevas if x not in previas]) or valor
            return
        if isinstance(valor, list):
            destino[k] = destino.get(k) or []
            destino[k] += [x for x in valor if x not in destino[k]]
        elif destino.get(k) and k not in ('semana_inicio', 'duracion'):
            destino[k] = f'{destino[k]} {valor}' if k != 'fase' else f'{destino[k]}; {valor}'
        else:
            destino[k] = valor

    for tipo, k, c in eventos:
        if tipo == 'marca':
            if act is None: continue
            if (m := MARCA_SEMANA.match(k)):
                semana = m.group(1); continue
            ss = sorted(bloques.get(id(c), []), key=lambda s: (s.p, s.y0, s.x0))
            ss = [s for s in ss if not SIN_ELEMENTOS.match(s.t.strip())]
            if MARCA_RECOLECCION.match(k):
                tipos = [s.t.strip() for s in ss if s.x1 < 132 and TIPO_INSTRUMENTO.match(s.t.strip())]
                acumular(act, 'instrumentos', tipos)
                texto = _limpio(' '.join(s.t for s in ss if not (s.x1 < 132 and s.t.strip() in tipos)))
                if texto: acumular(act, 'descripcion_instrumentos', f'[Semana {semana}] {texto}' if semana else texto)
            else:
                acumular(act, 'recursos_externos', _lista([Celda([s]) for s in ss], []))
            continue
        if tipo == 'medio':
            if act is not None:
                texto = _parrafo(sorted(centrales.get(id(c), []), key=pos))
                if texto: acumular(act, k, f'[Semana {semana}] {texto}' if semana else texto)
            continue
        if tipo == 'titulo':
            n = normalizar(k)
            if n in SECCIONES:
                if seccion != n and n in ('soluciona un problema', 'acciones', 'bibliografia'):
                    exp = act = None if n != 'soluciona un problema' else exp
                seccion = n; continue
            titulo = _limpio(re.sub(r'\s*\n\s*', ' ', k.split(':', 1)[1]))
            if k.lower().startswith('experiencia'):
                exp = dict(tipo='vive_experiencia', nombre=titulo, actividades=[]); experiencias.append(exp); etapa = act = None
            elif k.lower().startswith('problema'):
                exp = dict(tipo='soluciona_problema', nombre=titulo, problema=titulo, actividades=[]); experiencias.append(exp); etapa = act = None
            elif k.lower().startswith('etapa'):
                etapa = titulo; act = None
            elif k.lower().startswith(('actividad', 'nombre de la actividad')) and exp is not None:
                act = dict(nombre=titulo, etapa=etapa); exp['actividades'].append(act); semana = None
            continue
        destino = act if act is not None else exp
        if seccion == 'acciones' or k in ('postulados', 'mejoras', 'transformaciones', 'descripcion_transformaciones'):
            destino = acciones
        if destino is None: continue
        if tipo == 'izq':
            vals = asignadas.get(id(c), [])
            if k in ('dimensiones', 'lugares', 'instrumentos', 'recursos_cgca', 'recursos_externos', 'competencia', 'postulados', 'mejoras'):
                valor = _lista(vals, vinetas)
                if k == 'competencia':
                    destino.setdefault('competencias', []).extend(valor); continue
                acumular(destino, k, valor)
            else:
                texto = _parrafo(vals)
                if k == 'semana_inicio' and texto and (m := re.search(r'(Semana|Week)\s+\d+', texto)):
                    # variante con 'Semana inicio' a la izquierda: la celda puede arrastrar texto de otra columna
                    resto = _limpio(texto.replace(m.group(), '', 1))
                    texto = m.group()
                    if resto and not destino.get('trabajo_profesor'): destino['trabajo_profesor'] = resto
                if k == 'trabajo_estudiante' and texto and semana and act is not None and destino is act:
                    texto = f'[Semana {semana}] {texto}'
                acumular(destino, k, texto)
        else:
            vals = derechos.get(id(c), [])
            if k == 'componentes':
                destino.setdefault('componentes', []).extend(_lista(vals, vinetas))
            elif k == 'tipo_actividad':   # puede traer varias opciones con viñetas
                destino[k] = '; '.join(_lista(vals, vinetas)) or None
            else:
                destino[k] = _parrafo(vals)
    return experiencias, acciones


# ---------- Tabla de actividades (plantilla V2) ----------
def _experiencias_v2(celdas, segs):
    """Experiencias con su descripción y su tabla de actividades (plantilla V2)."""
    experiencias = []
    titulos = sorted((s for s in segs if re.match(r'Experiencia\s*:', s.t) and s.x0 < 300), key=lambda s: (s.p, s.y0))
    fin_doc = next(((s.p, s.y0) for s in sorted(segs, key=lambda s: (s.p, s.y0))
                    if normalizar(s.t) in ('autor', 'bibliografa o webgrafa', 'bibliografia o webgrafia')), (1e9, 0))
    # La cabecera de cada experiencia (Rea, Dimensiones, Semestre) empieza unas líneas por encima de su título centrado
    inicios = [(t.p, t.y0 - 32) for t in titulos]
    for i, t in enumerate(titulos):
        fin = inicios[i + 1] if i + 1 < len(titulos) else fin_doc
        cuerpo = [s for s in segs if (t.p, t.y0) <= (s.p, s.y0) < fin]
        cabecera = [s for s in segs if s.p == t.p and t.y0 - 32 <= s.y0 <= t.y1 + 40]
        # Título: 'Experiencia: …' (con los trozos de su misma línea) y sus líneas de continuación debajo
        excluir = re.compile(r'(Semestre|Periodo|Dimensiones|Descripci|DESCRIPCI|Rea)')
        izquierda = [s for s in cabecera if s.x0 < 300 and not excluir.match(s.t)]
        linea = sorted((s for s in izquierda if abs(s.yc - t.yc) < 3), key=lambda s: s.x0)
        partes = [' '.join(s.t for s in linea).split(':', 1)[1]]
        y = t.y1
        for s in sorted((s for s in cabecera if s.x0 < 300 and s.y0 > t.y1 - 1), key=lambda s: (s.y0, s.x0)):
            if excluir.match(s.t): continue
            if s.y0 - y > 6 or s.x1 > 320 or re.fullmatch(r'\d{1,2}', s.t.strip()): break
            partes.append(s.t); y = max(y, s.y1)
        exp = dict(tipo='vive_experiencia', nombre=re.sub(r'\s+Rea$', '', _limpio(' '.join(partes))), actividades=[])
        dims = next((s for s in cabecera if s.t.startswith('Dimensiones')), None)
        if dims:
            texto = [dims.t.split(':', 1)[1]] + [s.t for s in sorted(cabecera, key=lambda s: s.y0)
                                                 if dims.y0 < s.y0 < dims.y0 + 45 and dims.x0 - 30 <= s.x0 <= dims.x1 + 40
                                                 and not re.match(r'(Descripci|Semestre|Periodo|Rea\b)', s.t)]
            exp['dimensiones'] = [x.strip() for x in re.split(r'\s*-\s*', ' '.join(texto)) if x.strip()]
        encab_act = next((s for s in cuerpo if normalizar(s.t) == 'actividades'), None)
        antes = [s for s in cuerpo if encab_act is None or (s.p, s.y0) < (encab_act.p, encab_act.y0)]
        num = next((s for s in antes if re.fullmatch(r'\d{1,2}', s.t.strip()) and s.x0 < 60), None)
        if num:
            exp['rea'] = int(num.t)
            exp['descripcion'] = _limpio(' '.join(s.t for s in sorted(antes, key=lambda s: (s.p, s.y0, s.x0))
                                                  if s.x0 > 100 and (s.p, s.y0) > (num.p, num.y0 - 25)
                                                  and normalizar(s.t) not in ('rea', 'descripcion')
                                                  and not re.match(r'(Dimensiones|Semestre|Periodo|DESCRIPCI)', s.t)))
        if encab_act:
            exp['actividades'] = _tabla_actividades_v2([s for s in cuerpo if (s.p, s.y0) > (encab_act.p, encab_act.y0)])
        experiencias.append(exp)
    return experiencias


def _partir_por_x(segs, cortes):
    """Parte cada segmento en las fronteras de columna usando la posición de sus palabras."""
    out = []
    for s in segs:
        grupos = {}
        for w in (s.palabras or [s]):
            zona = sum(w.x0 >= c for c in cortes)
            grupos.setdefault(zona, []).append(w)
        for ws in grupos.values():
            out.append(Seg(s.p, ws[0].x0, min(w.y0 for w in ws), ws[-1].x1, max(w.y1 for w in ws), ' '.join(w.t for w in ws), ws))
    return out


def _tabla_actividades_v2(segs):
    """Tabla ancha de actividades: nombre | descripción | semana | duración | trabajo del profesor | trabajo del estudiante.
    Las columnas se ubican por las palabras 'Semana N' y 'N Semana(s)'; el resto por franjas."""
    palabras = [w for s in segs for w in (s.palabras or [s])]

    def moda(xs):
        xs = [round(x) for x in xs]
        return max(set(xs), key=lambda x: (sum(abs(y - x) <= 3 for y in xs), -x)) if xs else None
    # 'Semana N' aparece también dentro de las descripciones: la columna es la posición más frecuente de las
    # palabras 'Semana' seguidas de un número que ocupan solas su celda
    x_sem = moda([w.x0 for w in palabras if w.t == 'Semana'
                  and any(v.p == w.p and abs(v.yc - w.yc) < 2 and re.fullmatch(r'\d+', v.t) and 0 < v.x0 - w.x1 < 6 for v in palabras)
                  and not any(v.p == w.p and abs(v.yc - w.yc) < 2 and 0 < w.x0 - v.x1 < 6 for v in palabras)])
    x_dur = moda([v.x0 for w in palabras if w.t == 'Semana(s)' for v in palabras
                  if v.p == w.p and abs(v.yc - w.yc) < 2 and re.fullmatch(r'\d+', v.t) and 0 < w.x0 - v.x1 < 6])
    if x_sem is None and x_dur is None: return []
    x_sem = x_sem if x_sem is not None else x_dur - 45
    x_dur = x_dur if x_dur is not None else x_sem + 45
    # Columnas de la derecha: inicios de línea frecuentes a la derecha de la duración
    inicios = {}
    for s in segs:
        if s.x0 > x_dur + 40: inicios[round(s.x0 / 10)] = inicios.get(round(s.x0 / 10), 0) + 1
    der = sorted(k * 10 for k, n in inicios.items() if n >= 3)
    cols = []
    for x in der:
        if not cols or x - cols[-1] > 60: cols.append(x)
    x_est = cols[1] - 5 if len(cols) > 1 else 1e9
    # Frontera nombre | descripción: donde empiezan las líneas largas de descripción (suele ser x≈121, a veces antes)
    x_desc = moda([s.x0 for s in segs if 40 < s.x0 < x_sem - 50 and len(s.t) > 45])
    corte_nombre = min(110, x_desc - 3) if x_desc else 110
    cortes = [corte_nombre, x_sem - 4, x_dur - 4, x_dur + 40, x_est]
    zonas = {0: 'nombre', 1: 'descripcion', 2: 'semana_inicio', 3: 'duracion', 4: 'trabajo_profesor', 5: 'trabajo_estudiante'}
    # 'Herramientas de Recolección de Datos: …' ocupa varias columnas: se separa antes de partir por columnas
    herramientas = [s for s in segs if 'Herramientas de Recolecci' in s.t]
    continuaciones = {id(h_): [s for s in segs if s.p == h_.p and 0 < s.y0 - h_.y0 < 40 and abs(s.x0 - h_.x0) < 30 and s is not h_]
                      for h_ in herramientas}
    fuera = {id(h_) for h_ in herramientas} | {id(s) for cs in continuaciones.values() for s in cs}
    piezas = [s for s in _partir_por_x([s for s in segs if id(s) not in fuera], cortes) if s.t.strip()]
    zona = lambda s: zonas[sum(s.x0 >= c for c in cortes)]
    nombres = _celdas([s for s in piezas if zona(s) == 'nombre'])
    if not nombres: return []
    # Cada actividad tiene una sola duración 'N Semana(s)'. Si hay más celdas de nombre que duraciones, el nombre
    # está partido en varias líneas separadas ('UNA LUPA' / 'SOBRE EL' / 'MUNDO'): se unen alrededor de su duración.
    duraciones = [s for s in piezas if zona(s) == 'duracion' and re.search(r'\d+\s*Semana\(s\)', s.t)]
    if duraciones and len(nombres) > len(duraciones):
        grupos = {}
        for n in nombres:
            d = min(duraciones, key=lambda d: (d.p != n.p, abs(d.yc - n.yc)))
            grupos.setdefault(id(d), []).append(n)
        nombres = [Celda(sorted((s for n in g for s in n.lineas), key=lambda s: (s.p, s.y0))) for g in grupos.values()]
        nombres.sort(key=lambda c: (c.p, c.y0))
    acts = [dict(nombre=_limpio(n.t.replace('\n', ' ')), _c=n) for n in nombres]
    # 'Semana' y su número pueden venir en líneas separadas
    for s in [s for s in piezas if zona(s) == 'semana_inicio' and s.t.strip() == 'Semana']:
        num = next((v for v in piezas if zona(v) == 'semana_inicio' and v.p == s.p and 0 < v.y0 - s.y0 < 14
                    and re.fullmatch(r'\d+', v.t.strip())), None)
        if num: s.t = f'Semana {num.t.strip()}'

    def mas_cercana(s):
        misma = [a for a in acts if a['_c'].p == s.p]
        return min(misma or acts, key=lambda a: abs(a['_c'].yc - s.yc) if a['_c'].p == s.p else 1e9)

    def contenedora(c):
        dentro = [a for a in acts if a['_c'].p == c.p and c.y0 - 4 <= a['_c'].yc <= c.y1 + 4]
        if dentro: return dentro[0]
        previas = [a for a in acts if (a['_c'].p, a['_c'].y0) <= (c.p, c.y0)]
        return max(previas, key=lambda a: (a['_c'].p, a['_c'].y0)) if previas else acts[0]
    textos = {}
    for s in piezas:
        z = zona(s)
        patron = r'Semana \d+' if z == 'semana_inicio' else r'\d+\s*Semana\(s\)'
        if z in ('semana_inicio', 'duracion') and (m := re.search(patron, s.t)):
            a = mas_cercana(s)
            if not a.get(z): a[z] = m.group()
    for h_ in herramientas:
        a = contenedora(Celda([h_]))
        texto = h_.t.split('Herramientas de Recolecci', 1)[1].split(':', 1)[-1]
        texto = _limpio(texto + ' ' + ' '.join(s.t for s in continuaciones[id(h_)]))
        # 'V2' escribe '(Tarea): producto… (Foro): producto…': se separan los tipos de la descripción del producto
        tipos = re.findall(r'\(([^()]{2,40})\)\s*:', texto)
        for t in tipos or [texto]:
            if t not in a.setdefault('instrumentos', []): a['instrumentos'].append(t)
        if tipos:
            a['descripcion_instrumentos'] = _limpio(((a.get('descripcion_instrumentos') or '') + ' ' + texto))
    en_herr = set()
    for z in ('descripcion', 'trabajo_profesor', 'trabajo_estudiante'):
        for c in _celdas([s for s in piezas if zona(s) == z and id(s) not in en_herr and not s.t.startswith('Herramientas')]):
            textos.setdefault((id(contenedora(c)), z), []).append(c)
    for a in acts:
        for z in ('descripcion', 'trabajo_profesor', 'trabajo_estudiante'):
            cs = textos.get((id(a), z))
            if cs: a[z] = _parrafo(sorted(cs, key=lambda c: (c.p, c.y0)))
        if not a.get('semana_inicio') and (m := re.match(r'Semana (\d+)', a.get('descripcion') or '')):
            a['semana_inicio'] = m.group()   # algunas plantillas escriben la semana al inicio de la descripción
        a.pop('_c')
    return acts


# ---------- Documento completo ----------
def _codigo_de_archivo(nombre):
    m = re.search(r'(CAD\d{9,}(?:[A-Z]{0,2}-?[A-Z])?(?:-[A-Z])?)', nombre)
    return m.group(1) if m else None


def leer_pad(pdf, poppler=None):
    pdf = Path(pdf)
    pdftotext = binario('pdftotext', poppler)
    if not pdftotext:
        raise SystemExit('Se necesita pdftotext de poppler para leer los PAD.')
    palabras = _palabras(pdf, pdftotext)
    lineas = _lineas(palabras)
    segs = _separar_frases(_segmentos(lineas, _columnas(lineas)))
    celdas = _celdas(segs)
    primera = ' '.join(s.t for s in segs if s.p == 1 and s.y0 < 60)
    plantilla = 'V2' if re.search(r'DIGITAL V2\b', primera) else 'V1.9'
    enc = _encabezado(segs)
    codigo_archivo = _codigo_de_archivo(pdf.stem)
    codigo = codigo_archivo or (enc.get('codigo') if enc.get('codigo') and len(enc['codigo']) > 6 else None)
    ingles = bool(re.search(r'\bAGRICULTURAL\b|\bMICROBIOLOGY\b', pdf.stem, re.I))
    if not codigo:
        codigo = re.sub(r'[^A-Z0-9]+', '-', normalizar(pdf.stem.replace('PAD', '')).upper()).strip('-')
    if ingles: codigo += '-EN'
    justificacion = _bloque_bajo(celdas, 'justificacion', ['rea general'])
    rea_general = _bloque_bajo(celdas, 'rea general', ['rea especific'])
    if plantilla == 'V1.9':
        experiencias, acciones = _filas_v19(celdas, segs)
    else:
        experiencias, acciones = _experiencias_v2(celdas, segs), {}
    nombre = enc.get('nombre') or pdf.stem
    return dict(
        codigo=codigo, codigo_pdf=enc.get('codigo'), archivo=pdf.name, carpeta=pdf.parent.name, plantilla=plantilla,
        idioma='en' if ingles else 'es',
        nombre=_limpio(re.sub(r'\s*V\d+(\.\d+)?$', '', nombre)), programa=enc.get('programa'), facultad=enc.get('facultad'),
        semestre=_entero(enc.get('semestre')), creditos=_entero(enc.get('creditos')),
        prerrequisitos=None if normalizar(enc.get('prerrequisitos') or '') in ('', 'ninguno', 'no aplica') else enc.get('prerrequisitos'),
        justificacion=_parrafo([c for c in justificacion if not normalizar(c.t).startswith(('libertad', 'la libertad'))]),
        rea_general=_parrafo(rea_general), rea=_rea_especificos(celdas), fases=_fases_mca(segs),
        relacion_creditos=enc.get('relacion_creditos'),
        experiencias=experiencias, acciones=acciones,
        bibliografia=_bibliografia(celdas, segs), recursos=_recursos_externos(celdas, segs),
        paginas=max(s.p for s in segs), texto=_texto_completo(pdf, pdftotext))


def extraer_pads(carpeta, destino, poppler=None):
    """Lee todos los PAD (PDF, con subcarpetas) y escribe pads.json."""
    carpeta = Path(carpeta)
    if not carpeta.exists():
        print(f'Aviso: no existe la carpeta de PAD {carpeta}; se omiten.')
        return []
    pads = [leer_pad(f, poppler) for f in sorted(carpeta.rglob('*.pdf'))]
    repetidos = {p['codigo'] for p in pads if sum(q['codigo'] == p['codigo'] for q in pads) > 1}
    for p in pads:
        if p['codigo'] in repetidos:   # mismo código en dos archivos: se distingue por el nombre del archivo
            p['codigo'] += '-' + re.sub(r'[^A-Z0-9]+', '-', normalizar(Path(p['archivo']).stem).upper())[-12:].strip('-')
    Path(destino).write_text(json.dumps(pads, ensure_ascii=False), encoding='utf-8')
    act = sum(len(e['actividades']) for p in pads for e in p['experiencias'])
    print(f'PAD: {len(pads)} documentos, {sum(len(p["rea"]) for p in pads)} REA específicos, '
          f'{sum(len(p["experiencias"]) for p in pads)} experiencias, {act} actividades, '
          f'{sum(len(p["bibliografia"]) for p in pads)} referencias → {destino}')
    return pads
