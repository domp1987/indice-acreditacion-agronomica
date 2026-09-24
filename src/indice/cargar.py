"""Carga incremental de la base desde lo extraído de las presentaciones y las semillas (datos/semillas/*.csv).

- Marcos, nodos, correspondencias y evidencias se actualizan por clave natural y conservan su id.
- Las decisiones del comité (validado_por no nulo, u origen 'manual') nunca se modifican ni se borran.
- Las evidencias que ya no están en las fuentes quedan 'obsoleta'.
- Normativa, indicadores, mediciones, cursos, brechas, gráficas y tablas se reconstruyen: su fuente de verdad
  son las semillas y las presentaciones.
La reproyección CNA → ABET (etiquetas inferidas) vive en reproyectar.py.
"""
import json
import re
import sqlite3
from pathlib import Path

from indice.config import ESQUEMA
from indice.ocr import texto_nuevo
from indice.semillas import leer_todas


class Nodos:
    """Ids de los nodos por (marco, código), para no consultar la base en cada inserción."""

    def __init__(self, cur):
        self.ids = {(m, c): i for i, m, c in cur.execute("SELECT n.id, m.codigo, n.codigo FROM nodo n JOIN marco m ON m.id=n.marco_id")}
        self.caracteristicas = {c for (m, c), _ in self.ids.items() if m == 'CNA' and re.fullmatch(r'C\d\d', c)}

    def __call__(self, marco, codigo):
        return self.ids[(marco, codigo)]


# ---------- Marcos, nodos y correspondencias ----------
AHORA = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"


def sincronizar_marcos(cur, semillas, avisos):
    """Upsert de marcos, nodos y correspondencias por clave natural. Respeta las decisiones del comité."""
    for m in semillas['marcos']:
        cur.execute("""INSERT INTO marco(id,codigo,nombre,version,descripcion) VALUES (:id,:codigo,:nombre,:version,:descripcion)
                       ON CONFLICT(codigo) DO UPDATE SET nombre=excluded.nombre, version=excluded.version, descripcion=excluded.descripcion""", m)
    marco_id = dict(cur.execute('SELECT codigo, id FROM marco'))
    for n in semillas['nodos']:
        cur.execute(f"""INSERT INTO nodo(marco_id,codigo,nombre,descripcion,tipo,orden,creado_en,actualizado_en)
                        VALUES (?,?,?,?,?,?,{AHORA},{AHORA})
                        ON CONFLICT(marco_id,codigo) DO UPDATE SET nombre=excluded.nombre, descripcion=excluded.descripcion,
                          tipo=excluded.tipo, orden=excluded.orden, actualizado_en={AHORA}
                        WHERE nombre IS NOT excluded.nombre OR descripcion IS NOT excluded.descripcion
                          OR tipo IS NOT excluded.tipo OR orden IS NOT excluded.orden""",
                    (marco_id[n['marco']], n['codigo'], n['nombre'], n['descripcion'], n['tipo'], n['orden']))
    ids = {(m, c): i for i, m, c in cur.execute('SELECT n.id, m.codigo, n.codigo FROM nodo n JOIN marco m ON m.id=n.marco_id')}
    for n in semillas['nodos']:
        padre = ids[(n['marco'], n['padre'])] if n['padre'] else None
        cur.execute(f'UPDATE nodo SET padre_id=?, actualizado_en={AHORA} WHERE id=? AND padre_id IS NOT ?', (padre, ids[(n['marco'], n['codigo'])], padre))
    sobrantes = set(ids) - {(n['marco'], n['codigo']) for n in semillas['nodos']}
    if sobrantes:
        avisos.append(f'nodos que ya no están en las semillas (se conservan): {", ".join(sorted("/".join(k) for k in sobrantes))}')

    deseadas = {(ids[(c['marco_origen'], c['origen'])], ids[(c['marco_destino'], c['destino'])]): (c['tipo'], c['nota'])
                for c in semillas['correspondencias']}
    existentes = {(o, d): (i, t, nota, vp) for i, o, d, t, nota, vp in
                  cur.execute('SELECT id, origen_id, destino_id, tipo, nota, validado_por FROM correspondencia')}
    for clave, (tipo, nota) in deseadas.items():
        if clave not in existentes:
            cur.execute(f'INSERT INTO correspondencia(origen_id,destino_id,tipo,nota,creado_en,actualizado_en) VALUES (?,?,?,?,{AHORA},{AHORA})',
                        (*clave, tipo, nota))
            continue
        i, t0, nota0, validado_por = existentes[clave]
        if (t0, nota0) == (tipo, nota): continue
        if validado_por:
            avisos.append(f'correspondencia {i}: las semillas cambian el tipo a "{tipo}", pero el comité ya decidió ({validado_por}); se conserva')
        else:
            cur.execute(f'UPDATE correspondencia SET tipo=?, nota=?, actualizado_en={AHORA} WHERE id=?', (tipo, nota, i))
    for clave, (i, *_, validado_por) in existentes.items():
        if clave in deseadas: continue
        if validado_por:
            avisos.append(f'correspondencia {i} ya no está en las semillas, pero el comité la decidió ({validado_por}); se conserva')
        else:
            cur.execute('DELETE FROM correspondencia WHERE id=?', (i,))   # sus etiquetas inferidas las retira reproyectar


# ---------- Evidencias desde las diapositivas ----------
_OMITIR_TITULO = re.compile(r'^(Caracter[ií]stica|Fuente|FACTOR|Factor \d|Ingenier[ií]a$|Agron[oó]mica$|Acreditaci[oó]n de Alta|Sede Fusa|ALD Faca|Universidad de|CUNDINAMARCA)', re.I)


def _titulo_de(s):
    lines = [l.strip() for l in s['texto'].split('\n') if l.strip()]
    name = (s['car_nombre'] or '').lower()
    for l in lines:
        if _OMITIR_TITULO.search(l) or len(l) < 14 or l.lower() in name or name.startswith(l.lower()): continue
        if re.fullmatch(r'[\d\s%.,$]+', l): continue
        return l[:110]
    return s['car_nombre'] or 'Diapositiva'


def _titulo_presentacion(s):
    """Presentaciones que no son de factor: 'SECCIÓN: primera línea informativa' (p. ej. '¿QUIÉNES SOMOS?: Misión Institucional')."""
    lineas = [l.strip() for l in s['texto'].split('\n') if l.strip()]
    utiles = [l for l in lineas if len(l) >= 4 and not _OMITIR_TITULO.search(l) and not re.fullmatch(r'[\d\s%.,$•|-]+', l)]
    if not utiles:
        return f"{s['nombre_fuente']}, diapositiva {s['pagina']}"
    seccion = utiles[0]
    resto = next((l for l in utiles[1:] if len(l) >= 12 and l.upper() != seccion.upper()), None)
    return (f'{seccion}: {resto}' if resto else seccion)[:110]


def _es_portada(t):
    if len(t) < 120 and ('Acreditación de Alta Calidad' in t or re.search(r'FACTOR\s*\d+\s*$', t.split('\n')[0] if t else '')):
        return True
    return bool(re.match(r'^\s*FACTOR\s*\d+\s*\n', t) and len(t) < 200)


def _tipo_y_titulo(s):
    t = s['texto']; up = t.upper()
    if not s['factor']:
        return 'diapositiva', _titulo_presentacion(s)
    if 'VALORACIÓN INTERPRETATIVA' in up or 'Valoración Interpretativa' in t:
        return 'valoracion', f'Valoración interpretativa del factor {s["factor"]}'
    if 'LOGROS E' in up and 'IMPACTO' in up:
        return 'logros', f'Logros e impacto del factor {s["factor"]}'
    if 'PLAN DE' in up and 'MEJORAMIENTO' in up and 'Avance' in t:
        return 'plan_mejora', f'Avance en el plan de mejoramiento, factor {s["factor"]}'
    sub = _titulo_de(s)
    good = sub and len(sub) >= 18 and sub[0].isupper() and not sub.rstrip().endswith((',', ' que', ' de', ' y')) and sub != s['car_nombre']
    if s['car_nombre']:
        return 'diapositiva', f"{s['car_nombre'].rstrip('.')}: {sub}" if good else s['car_nombre'].rstrip('.')
    return 'diapositiva', sub if good else f"Factor {s['factor']}, diapositiva {s['pagina']}"


_CAMPOS_EVIDENCIA = ['titulo', 'tipo', 'texto', 'texto_ocr', 'fuente', 'archivo', 'pagina', 'sede']


def sincronizar_evidencias(cur, nodos, slides, ocr=None):
    """Upsert de una evidencia por diapositiva (sin portadas) y de sus etiquetas CNA de extracción.

    Las evidencias conservan su id. Las que ya no aparecen quedan 'obsoleta' (no se borran: pueden tener
    decisiones del comité). Devuelve ({código: id} de las vigentes, resumen de cambios).
    ocr: {(fuente, página): [líneas]} del OCR; se guarda solo lo que no está ya en el texto del PDF.
    """
    ocr = ocr or {}
    ev_ids = {}
    nuevas = actualizadas = 0
    etiquetas = {}   # {evidencia_id: nodo_id} de origen extracción, deseadas
    for s in slides:
        t = s['texto']
        if _es_portada(t): continue
        tipo, titulo = _tipo_y_titulo(s)
        texto_ocr = texto_nuevo(ocr.get((s['fuente'], s['pagina']), []), t) or None
        if not s['factor'] and texto_ocr and ':' not in titulo:
            # Diapositiva cuyo contenido es una imagen: el título se completa con la primera línea legible del OCR
            extra = next((l for l in texto_ocr.split('\n') if len(l) >= 12), None)
            if extra: titulo = (extra if titulo.endswith(f'diapositiva {s["pagina"]}') else f'{titulo}: {extra}')[:110]
        fuentes = re.findall(r'Fuente[.:]\s*([^\n]{3,80})', t)
        codigo = f'{s["fuente"]}-P{s["pagina"]:03d}'
        valores = dict(codigo=codigo, titulo=titulo, tipo=tipo, texto=t, texto_ocr=texto_ocr,
                       fuente=fuentes[0].strip() if fuentes else None, archivo=s['archivo'], pagina=s['pagina'], sede=s['sede'])
        existe = cur.execute('SELECT id FROM evidencia WHERE codigo=?', (codigo,)).fetchone()
        cur.execute(f"""INSERT INTO evidencia(codigo,{','.join(_CAMPOS_EVIDENCIA)},creado_en,actualizado_en)
                        VALUES (:codigo,{','.join(':' + c for c in _CAMPOS_EVIDENCIA)},{AHORA},{AHORA})
                        ON CONFLICT(codigo) DO UPDATE SET {', '.join(f'{c}=excluded.{c}' for c in _CAMPOS_EVIDENCIA)},
                          estado_revision=CASE WHEN estado_revision='obsoleta' THEN 'sin_revisar' ELSE estado_revision END,
                          actualizado_en={AHORA}
                        WHERE estado_revision='obsoleta' OR {' OR '.join(f'{c} IS NOT excluded.{c}' for c in _CAMPOS_EVIDENCIA)}""",
                    valores)
        if not existe: nuevas += 1
        elif cur.rowcount: actualizadas += 1
        eid = ev_ids[codigo] = existe[0] if existe else cur.lastrowid
        # Etiquetado CNA extraído del encabezado de la diapositiva
        car = f'C{s["car"]:02d}' if s['car'] else None
        if car in nodos.caracteristicas: etiquetas[eid] = nodos('CNA', car)
        elif s['factor']: etiquetas[eid] = nodos('CNA', f'F{s["factor"]:02d}')

    # Evidencias que ya no están en las fuentes
    vigentes = set(ev_ids.values())
    obsoletas = [i for (i,) in cur.execute("SELECT id FROM evidencia WHERE estado_revision<>'obsoleta'").fetchall() if i not in vigentes]
    cur.executemany(f"UPDATE evidencia SET estado_revision='obsoleta', actualizado_en={AHORA} WHERE id=?", [(i,) for i in obsoletas])

    # Etiquetas de extracción: se agregan las nuevas y se retiran las que ya no salen del encabezado, salvo
    # decisiones del comité. Si ya existe una etiqueta (p. ej. manual) en ese par, prevalece la existente.
    existentes = set(cur.execute("SELECT evidencia_id, nodo_id FROM evidencia_nodo WHERE origen='extraccion'").fetchall())
    deseadas = set(etiquetas.items())
    cur.executemany(f"""INSERT OR IGNORE INTO evidencia_nodo(evidencia_id,nodo_id,rol,origen,estado,creado_en,actualizado_en)
                        VALUES (?,?,'principal','extraccion','validada',{AHORA},{AHORA})""", sorted(deseadas - existentes))
    retirar = sorted((e, n) for e, n in existentes - deseadas if e in vigentes)
    cur.executemany("DELETE FROM evidencia_nodo WHERE evidencia_id=? AND nodo_id=? AND origen='extraccion' AND validado_por IS NULL", retirar)
    return ev_ids, dict(nuevas=nuevas, actualizadas=actualizadas, obsoletas=len(obsoletas),
                        etiquetas_nuevas=len(deseadas - existentes), etiquetas_retiradas=len(retirar))


# ---------- Normativa ----------
_PATRON_NORMA = re.compile(r'(Acuerdo|Resoluci[oó]n)\b([^\n]{0,60}?)(?:N[o°º]\.?\s*|N\.\s*)?(\d{3,6})\s+(?:del?\s+)?(?:\d{1,2}\s+de\s+[a-zA-Z]+\s+(?:de\s+)?)?(\d{4})', re.I)


def cargar_normativa(cur, slides, ev_ids, semillas):
    """Normas citadas: las que reconoce el patrón (menos las excluidas) y las de normativa_manual.csv."""
    excluir = {(n['tipo'], n['numero'], n['anio']) for n in semillas['normativa_excluir']}
    texto = {f'{s["fuente"]}-P{s["pagina"]:03d}': s['texto'] for s in slides}
    for codigo, eid in ev_ids.items():
        t = re.sub(r'\s+', ' ', texto[codigo])
        for m in _PATRON_NORMA.finditer(t):
            tipo = 'Acuerdo' if m.group(1).lower().startswith('acu') else 'Resolución'
            num, anio = int(m.group(3)), int(m.group(4))
            if (tipo, num, anio) in excluir or anio < 1990 or anio > 2026: continue
            ctx = m.group(0)
            org = 'Consejo Superior' if re.search(r'Superior|C\.?\s?S\b|CSU|CS\b', ctx) else 'Consejo Académico' if re.search(r'Acad[eé]mico|C\.?\s?A\b', ctx) else 'Rectoría' if 'Rector' in ctx else None
            cur.execute("INSERT OR IGNORE INTO normativa(tipo,numero,anio,organo) VALUES (?,?,?,?)", (tipo, num, anio, org))
            if org: cur.execute("UPDATE normativa SET organo=COALESCE(organo,?) WHERE tipo=? AND numero=? AND anio=?", (org, tipo, num, anio))
            doc = cur.execute("SELECT id FROM normativa WHERE tipo=? AND numero=? AND anio=?", (tipo, num, anio)).fetchone()[0]
            cur.execute("INSERT OR IGNORE INTO normativa_mencion VALUES (?,?)", (doc, eid))
    for n in semillas['normativa_manual']:
        cur.execute("INSERT OR IGNORE INTO normativa(tipo,numero,anio,organo) VALUES (?,?,?,?)", (n['tipo'], n['numero'], n['anio'], n['organo']))
        doc = cur.execute("SELECT id FROM normativa WHERE tipo=? AND numero=? AND anio=?", (n['tipo'], n['numero'], n['anio'])).fetchone()[0]
        for codigo, eid in ev_ids.items():
            if n['texto_a_buscar'] in texto[codigo]:
                cur.execute("INSERT OR IGNORE INTO normativa_mencion VALUES (?,?)", (doc, eid))


# ---------- Indicadores, cursos y brechas (semillas) ----------
def cargar_indicadores(cur, nodos, ev_ids, semillas):
    """Devuelve los códigos de evidencia citados en mediciones.csv que no existen en la base."""
    ind = {}
    for i in semillas['indicadores']:
        cur.execute("INSERT INTO indicador(codigo,nombre,unidad,descripcion) VALUES (:codigo,:nombre,:unidad,:descripcion)", i)
        ind[i['codigo']] = cur.lastrowid
    for x in semillas['indicador_nodos']:
        cur.execute("INSERT INTO indicador_nodo VALUES (?,?,?)", (ind[x['indicador']], nodos(x['marco'], x['nodo']), x['rol']))
    faltantes = set()
    for m in semillas['mediciones']:
        if m['evidencia'] and m['evidencia'] not in ev_ids: faltantes.add(m['evidencia'])
        cur.execute("INSERT INTO medicion(indicador_id,periodo,sede,valor,desagregacion,evidencia_id,nota) VALUES (?,?,?,?,?,?,?)",
                    (ind[m['indicador']], m['periodo'], m['sede'] or 'Programa', m['valor'], m['desagregacion'], ev_ids.get(m['evidencia']), m['nota']))
    return faltantes


def cargar_cursos_y_brechas(cur, nodos, semillas):
    cur.executemany("INSERT INTO curso(nombre,componente_cma,creditos,periodo,categoria_abet,confianza,nota) "
                    "VALUES (:nombre,:componente_cma,:creditos,:periodo,:categoria_abet,:confianza,:nota)", semillas['cursos'])
    for b in semillas['brechas']:
        cur.execute("INSERT INTO brecha(nodo_id,titulo,descripcion,severidad,accion,responsable,estado) VALUES (?,?,?,?,?,?,?)",
                    (nodos(b['marco'], b['nodo']), b['titulo'], b['descripcion'], b['severidad'], b['accion'], b['responsable'], b['estado'] or 'abierta'))


# ---------- Gráficas y tablas de los PPTX ----------
def cargar_pptx(cur, pptx, ev_ids):
    """Liga gráficas y tablas a la evidencia de su diapositiva. Devuelve las diapositivas sin evidencia."""
    huerfanas = []
    for d in pptx:
        codigo = f'{d["fuente"]}-P{d["pagina"]:03d}'
        eid = ev_ids.get(codigo)
        if eid is None:
            huerfanas.append(codigo); continue
        for orden, g in enumerate(d['graficas'], 1):
            cur.execute("INSERT INTO grafica(evidencia_id,orden,titulo,tipo) VALUES (?,?,?,?)", (eid, orden, g['titulo'] or None, g['tipo']))
            gid = cur.lastrowid
            cur.executemany("INSERT INTO grafica_dato VALUES (?,?,?,?,?,?)",
                            [(gid, so, s['nombre'], po, cat, v) for so, s in enumerate(g['series'], 1) for po, (cat, v) in enumerate(s['puntos'], 1)])
        for orden, t in enumerate(d['tablas'], 1):
            cur.execute("INSERT INTO tabla_diapositiva(evidencia_id,orden,filas,columnas,celdas) VALUES (?,?,?,?,?)",
                        (eid, orden, len(t), max((len(f) for f in t), default=0), json.dumps(t, ensure_ascii=False)))
    return huerfanas


def _leer_ocr(ocr_json):
    if not ocr_json or not Path(ocr_json).exists(): return {}
    cache = json.loads(Path(ocr_json).read_text(encoding='utf-8'))
    return {(fuente, int(p)): lineas for fuente, c in cache.items() for p, lineas in c['paginas'].items()}


VERSION_ESQUEMA = 2
# Tablas que son copia directa de semillas o del PPTX: se vacían y se vuelven a llenar en cada carga
# (hijas antes que padres). Su fuente de verdad son los CSV y las presentaciones, no la base.
DERIVADAS = ['grafica_dato', 'grafica', 'tabla_diapositiva', 'normativa_mencion', 'normativa',
             'medicion', 'indicador_nodo', 'indicador', 'curso_outcome', 'curso', 'brecha']


def version_esquema(con):
    try:
        return int(con.execute("SELECT valor FROM meta WHERE clave='version_esquema'").fetchone()[0])
    except sqlite3.OperationalError:
        return 1   # bases anteriores a la carga incremental (sin tabla meta)


def abrir_base(db, reconstruir=False):
    """Abre la base; la crea si no existe. Una base de esquema anterior (o con --reconstruir) se respalda y se crea de nuevo."""
    db = Path(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    if db.exists():
        con = sqlite3.connect(db)
        v = version_esquema(con)
        con.close()
        if reconstruir or v < VERSION_ESQUEMA:
            respaldo = db.with_name(f'{db.stem}.respaldo-v{v}.sqlite')
            db.replace(respaldo)
            motivo = 'se pidió reconstruir' if reconstruir else f'su esquema es v{v} (actual v{VERSION_ESQUEMA})'
            print(f'La base se crea de nuevo porque {motivo}; la anterior queda en {respaldo.name}')
        elif v > VERSION_ESQUEMA:
            raise SystemExit(f'{db} tiene un esquema más nuevo (v{v}) que este programa (v{VERSION_ESQUEMA}). Actualiza el paquete.')
    nueva = not db.exists()
    con = sqlite3.connect(db)
    con.execute('PRAGMA foreign_keys = ON')
    if nueva:
        con.executescript(ESQUEMA.read_text(encoding='utf-8'))
    return con


def cargar(db, diapositivas, semillas_dir, pptx_json=None, ocr_json=None, reconstruir=False):
    """Carga incremental: actualiza la base sin perder las decisiones del comité (ver schema.sql)."""
    diapositivas = Path(diapositivas)
    if not diapositivas.exists():
        raise SystemExit(f'No existe {diapositivas}. Ejecuta primero: indice extraer')
    slides = json.loads(diapositivas.read_text(encoding='utf-8'))
    if slides and 'fuente' not in slides[0]:
        raise SystemExit(f'{diapositivas} es de una versión anterior. Ejecuta de nuevo: indice extraer')
    semillas = leer_todas(semillas_dir)   # valida antes de tocar la base
    con = abrir_base(db, reconstruir)
    avisos = []
    try:
        cur = con.cursor()
        sincronizar_marcos(cur, semillas, avisos)
        nodos = Nodos(cur)
        ev_ids, cambios = sincronizar_evidencias(cur, nodos, slides, _leer_ocr(ocr_json))
        for t in DERIVADAS:
            cur.execute(f'DELETE FROM {t}')
        cargar_normativa(cur, slides, ev_ids, semillas)
        faltantes = cargar_indicadores(cur, nodos, ev_ids, semillas)
        if faltantes:
            avisos.append(f'mediciones.csv cita evidencias que no existen (quedan sin vínculo): {", ".join(sorted(faltantes))}')
        cargar_cursos_y_brechas(cur, nodos, semillas)
        if pptx_json and Path(pptx_json).exists():
            huerfanas = cargar_pptx(cur, json.loads(Path(pptx_json).read_text(encoding='utf-8')), ev_ids)
            if huerfanas:
                avisos.append(f'gráficas o tablas en diapositivas sin evidencia (portadas): {", ".join(huerfanas)}')
        con.commit()
        for a in avisos: print(f'Aviso: {a}')
        n = lambda q: cur.execute(q).fetchone()[0]
        vigentes = n("SELECT COUNT(*) FROM evidencia WHERE estado_revision<>'obsoleta'")
        print(f'Carga: {vigentes} evidencias vigentes '
              f'({cambios["nuevas"]} nuevas, {cambios["actualizadas"]} actualizadas, {cambios["obsoletas"]} pasan a obsoletas; '
              f'{n("SELECT COUNT(*) FROM evidencia WHERE texto_ocr IS NOT NULL")} con texto OCR), '
              f'{n("SELECT COUNT(*) FROM evidencia_nodo")} etiquetas (extracción: +{cambios["etiquetas_nuevas"]} −{cambios["etiquetas_retiradas"]}), '
              f'{n("SELECT COUNT(*) FROM nodo")} nodos, {n("SELECT COUNT(*) FROM medicion")} mediciones, '
              f'{n("SELECT COUNT(*) FROM curso")} cursos ({n("SELECT SUM(creditos) FROM curso")} créditos), '
              f'{n("SELECT COUNT(*) FROM grafica")} gráficas ({n("SELECT COUNT(*) FROM grafica_dato")} puntos), '
              f'{n("SELECT COUNT(*) FROM tabla_diapositiva")} tablas → {db}')
        return cambios
    finally:
        con.close()
