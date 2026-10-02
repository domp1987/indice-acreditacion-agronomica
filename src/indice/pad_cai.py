"""Lector complementario para los PAD de los Campos de Aprendizaje Institucional (CAI).

Los PAD de los CAI (Comunicación y lectura crítica, Lengua extranjera, Razonamiento lógico y cuantitativo, Ciencia,
tecnología e innovación, Cátedra Generación Siglo 21 y los nivelatorios) usan plantillas distintas a las de los cursos
disciplinares: la «V2 institucional», el «modelo nivelatorios CAI» (también en inglés) y la del CAI de RLC. El
analizador geométrico de pad.py los lee a medias; este módulo completa, a partir del texto con disposición
(pdftotext -layout), solo los campos que quedaron vacíos: código, nombre, créditos, semestre, prerrequisitos,
REA general, REA específicos y experiencias. Nunca reemplaza un dato que el analizador principal sí obtuvo.
"""
import re
import subprocess
from pathlib import Path

ORDINALES = {'primero': 1, 'primer': 1, 'first': 1, 'segundo': 2, 'second': 2, 'tercero': 3, 'tercer': 3, 'third': 3,
             'cuarto': 4, 'fourth': 4, 'quinto': 5, 'fifth': 5, 'sexto': 6, 'sixth': 6, 'septimo': 7, 'séptimo': 7,
             'seventh': 7, 'octavo': 8, 'eighth': 8, 'noveno': 9, 'ninth': 9}
ROMANOS = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9}
CORTE = r'(?:CONSECUTIVO|REA ESPEC|RA ESPEC|Espec[ií]fic|PARA EL LOGRO|PARA LOGRAR|DESCRIPCI[ÓO]N EXPERIENCIA|VIVE UNA EXPERIENCIA|Specific)'


def es_cai(texto):
    # solo el encabezado: los PAD disciplinares también mencionan los CAI en su texto
    t = texto[:1500].upper()
    return bool(re.search(r'CAMPO DE APRENDIZAJE INSTITUCIONAL|CAMPO INSTITUCIONAL|NIVELATORIOS CAI|INFORMACI[ÓO]N GENERAL DEL CAI|'
                          r'NOMBRE DEL CAI|LEARNING FIELD|INSTITUTIONAL LEARNING|CAI CODE|APRENDIZAJE \(CAI?\):|C[ÓO]DIGO DEL CAI?:', t))


def _layout(pdf, pdftotext):
    r = subprocess.run([pdftotext, '-enc', 'UTF-8', '-layout', str(pdf), '-'], capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.stdout.replace('\f', '\n')


def _limpio(t):
    return re.sub(r'\s+', ' ', t or '').strip(' .:*-_')


def _semestre(t):
    m = re.search(r'(?:Ubicaci[oó]n\s+Semestral|Semester\s+Location|Semestre|Semester)\s*:?\s*([^\n]{0,30})', t, re.I)
    if not m: return None
    v = m.group(1).strip().lower()
    n = re.match(r'_*(\d)', v)
    if n: return int(n.group(1))
    for palabra in re.findall(r'[a-záéíóú]+', v):
        if palabra in ORDINALES: return ORDINALES[palabra]
        if palabra in ROMANOS: return ROMANOS[palabra]
    return None


def _creditos(t):
    m = re.search(r'(?:N[uú]mero\s+de\s+cr[eé]ditos|Cr[eé]ditos|Cr[eé]dits|Credits)\s*:?\s*\n?\s*(?:[^\d\n]{0,40}\n\s*)?_*(\d)\b', t, re.I)
    return int(m.group(1)) if m else None


def _rea_general(t):
    m = re.search(r'(?:REA GENERAL\s*\*?|General Learning Outcome|RESULTADOS DE APRENDIZAJE \(RA\)\s*\n\s*General)\s*\n(.{20,1500}?)\n\s*' + CORTE, t, re.S | re.I)
    if not m: return None
    lineas = [l.strip() for l in m.group(1).splitlines() if l.strip() and not re.match(r'^(Estructura|General)$', l.strip(), re.I)]
    return _limpio(' '.join(lineas)) or None


def _rea_especificos(t):
    m = re.search(r'(?:CONSECUTIVO\s+REA ESPEC[IÍ]FICO|REA ESPEC[IÍ]FICOS?)\s*\n(.{20,4000}?)\n\s*(?:PARA EL LOGRO|PARA LOGRAR|DESCRIPCI)', t, re.S | re.I)
    if not m: return []
    rea, actual = [], None
    for linea in m.group(1).splitlines():
        n = re.match(r'^\s*(\d)\s+(.*)$', linea)
        if n:
            if actual: rea.append(actual)
            actual = dict(consecutivo=int(n.group(1)), texto=n.group(2).strip(), peso=None)
        elif linea.strip():
            if actual is None: actual = dict(consecutivo=1, texto='', peso=None)
            actual['texto'] = (actual['texto'] + ' ' + linea.strip()).strip()
    if actual: rea.append(actual)
    for r in rea: r['texto'] = _limpio(r['texto'])
    return [r for r in rea if len(r['texto']) > 20]


def _experiencias(t):
    nombres = []
    for m in re.finditer(r'(?<!DESCRIPCIÓN )(?<!DESCRIPCION )(?<!Descripción )Experiencia(?:/Problema/Comportamiento)?\s*:[ \t]?([^\n]*?)(?=\s{2,}|$)[^\n]*\n(\s*[^\n]*)', t, re.M | re.I):
        nombre = _limpio(m.group(1)) or _limpio(re.split(r'\s{3,}', m.group(2).strip())[0])
        if nombre and not re.match(r'^(Semestre|Descripci)', nombre, re.I): nombres.append(nombre)
    for m in re.finditer(r'Nombre de la\s+([^\n]+)\n\s*Experiencia', t, re.I):
        nombres.append(_limpio(m.group(1)))
    for m in re.finditer(r'(?:Name of the|Experience name)\s*:?\s+([^\n]+)', t, re.I):
        nombres.append(_limpio(m.group(1)))
    vistos, out = set(), []
    for n in nombres:
        if re.match(r'^(Experiencia/|Experience$|Description|Descripci|Semestre|Actividad)', n or '', re.I): continue
        if n and n.lower() not in vistos and len(n) > 3:
            vistos.add(n.lower())
            out.append(dict(tipo='vive_experiencia', nombre=n[:200], dimensiones=[], rea=None, descripcion=None, competencias=[], actividades=[]))
    return out


def complementar(pad, pdf, pdftotext):
    """Completa en `pad` (dict de leer_pad) los campos vacíos de un PAD CAI. Devuelve True si el PAD es CAI."""
    if re.match(r'^(CAD|CFC)\d', pad.get('codigo') or ''): return False   # cursos disciplinares y comunes
    t = _layout(pdf, pdftotext)
    if not es_cai(t): return False
    pad['tipo_campo'] = 'CAI'
    m = re.search(r'C[óo]digo del CAI\s+(CAI\d{6,})|\b(CAI\d{8,})\b', t, re.I)
    if m and not pad.get('codigo_pdf'):
        pad['codigo_pdf'] = m.group(1) or m.group(2)
        pad['codigo'] = pad['codigo_pdf']
    m = (re.search(r'Nombre del CAI\s+([^\n]+?)(?:\s{2,}|\n)', t, re.I)
         or re.search(r'Campo de[ \t]*\n?[ \t]*(\S[^\n]*?)\s*\n\s*Aprendizaje \(CAI?\):', t, re.I)   # nombre entre «Campo de» y «Aprendizaje (CA):»
         or re.search(r'(?:Campo de\s*\n?\s*Aprendizaje \(CAI?\):|Learning Field|Institutional Learning)\s+([^\n]+?)(?:\s{2,}|\n)', t, re.I))
    if m and re.search(r'^PAD|^\d\.|_|V\d', pad.get('nombre') or 'PAD'):
        pad['nombre'] = _limpio(m.group(1))
    if pad.get('semestre') is None: pad['semestre'] = _semestre(t)
    if pad.get('creditos') is None: pad['creditos'] = _creditos(t)
    if not pad.get('prerrequisitos'):
        m = re.search(r'Prerre?quisit(?:os|es)\s*\(?s?i?\s*[^\n]{0,30}?\)?\s{2,}([^\n]+)', t, re.I)
        if m: pad['prerrequisitos'] = _limpio(m.group(1))
    if not pad.get('rea_general'): pad['rea_general'] = _rea_general(t)
    if not pad.get('rea'): pad['rea'] = _rea_especificos(t)
    if not pad.get('experiencias'): pad['experiencias'] = _experiencias(t)
    return True
