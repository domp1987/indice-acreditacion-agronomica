"""Versión para compartir: el mismo tablero y los mismos CSV, sin datos personales.

La versión completa (salida/) no se toca. Se trabaja sobre una copia de la base en salida/compartir/ y se aplica:
- correos electrónicos → '[correo omitido]' en textos y celdas de tablas;
- en los PAD, la línea del profesor líder → '[omitido]';
- evidencias listadas en datos/semillas/privacidad.csv (listados de profesores, actas, evaluación docente…): su texto
  se reemplaza por un aviso, se quitan sus tablas y, en los anexos de varios archivos, el nombre del archivo del título;
- tablas de documentos maestros y anexos cuyo encabezado es de personas (columna "nombre" junto a profesor, docente,
  investigador, estudiante o egresado) se quitan;
- la tabla de decisiones y los campos validado_por conservan quién decidió (son actos del comité).
Los autores de la bibliografía y los directivos que firman documentos institucionales se conservan (rol público).
Después se usan el mismo exportador y la misma plantilla que la versión completa.
"""
import json
import re
import shutil
import sqlite3
from pathlib import Path

from indice.exportar import exportar
from indice.semillas import leer
from indice.tablero import tablero

CORREO = re.compile(r'[\w.+-]+@[\w-]+(\.[\w-]+)+')
LIDER = re.compile(r'((?:nombre\s+(?:del\s+)?)?(?:profesor|docente)(?:a)?\s+l[ií]der:?)[^\n]*', re.I)
PERSONAS = re.compile(r'profesor|docente|investigador|estudiante|egresad|graduad|integrante', re.I)
AVISO = '[Texto omitido en la versión para compartir: {motivo}. Está en la versión completa del índice.]'


def anonimizar_texto(t):
    if not t: return t
    return LIDER.sub(r'\1 [omitido]', CORREO.sub('[correo omitido]', t))


def _tabla_de_personas(filas):
    cab = ' '.join(str(c) for f in filas[:2] for c in f).lower()
    return 'nombre' in cab and bool(PERSONAS.search(cab))


def anonimizar_base(db, semillas):
    """Aplica las omisiones sobre una copia de la base. Devuelve un resumen."""
    con = sqlite3.connect(db)
    reglas = [(re.compile(r['patron']), r['motivo']) for r in leer(semillas, 'privacidad')]
    omitidas = tablas = 0
    for eid, cod, titulo, texto, ocr in con.execute('SELECT id, codigo, titulo, texto, texto_ocr FROM evidencia').fetchall():
        motivo = next((m for p, m in reglas if p.search(cod)), None)
        if motivo:
            if re.match(r'^AX-\d+-\d+$', cod):   # el nombre del archivo puede llevar el de la persona
                titulo = f'{titulo.split(" · ")[0]} · {titulo.split(" · ")[1]} · archivo {cod.rsplit("-", 1)[1]}'
            con.execute('UPDATE evidencia SET titulo=?, texto=?, texto_ocr=NULL, archivo=NULL WHERE id=?',
                        (titulo, AVISO.format(motivo=motivo), eid))
            tablas += con.execute('DELETE FROM tabla_diapositiva WHERE evidencia_id=?', (eid,)).rowcount
            omitidas += 1
        else:
            con.execute('UPDATE evidencia SET texto=?, texto_ocr=? WHERE id=?', (anonimizar_texto(texto), anonimizar_texto(ocr), eid))
    for tid, celdas, tipo in con.execute("""SELECT t.id, t.celdas, e.tipo FROM tabla_diapositiva t JOIN evidencia e ON e.id=t.evidencia_id""").fetchall():
        filas = json.loads(celdas)
        if tipo in ('documento_maestro', 'anexo') and _tabla_de_personas(filas):
            con.execute('DELETE FROM tabla_diapositiva WHERE id=?', (tid,)); tablas += 1
        else:
            limpias = [[anonimizar_texto(c) if isinstance(c, str) else c for c in f] for f in filas]
            if limpias != filas: con.execute('UPDATE tabla_diapositiva SET celdas=? WHERE id=?', (json.dumps(limpias, ensure_ascii=False), tid))
    for campo in ('justificacion', 'acciones'):
        for pid, v in con.execute(f'SELECT id, {campo} FROM pad').fetchall():
            if v and anonimizar_texto(v) != v: con.execute(f'UPDATE pad SET {campo}=? WHERE id=?', (anonimizar_texto(v), pid))
    con.commit()
    con.close()
    return dict(evidencias_omitidas=omitidas, tablas_quitadas=tablas)


def publicar(compartida, docs):
    """Copia a docs/ (GitHub Pages) el tablero y los CSV de la versión para compartir. Nunca la versión completa."""
    compartida, docs = Path(compartida), Path(docs)
    html = compartida / 'indice_acreditacion_abet.html'
    if not html.exists() or '"version":"compartir"' not in html.read_text(encoding='utf-8'):
        raise SystemExit(f'No está la versión para compartir en {compartida}. Ejecuta primero: indice compartir')
    docs.mkdir(parents=True, exist_ok=True)
    shutil.copy2(html, docs / 'index.html')
    shutil.copy2(compartida / 'tablas_csv.zip', docs / 'tablas_csv.zip')
    (docs / '.nojekyll').write_text('', encoding='utf-8')   # GitHub Pages sirve los archivos tal cual
    print(f'Publicación: {docs / "index.html"} y tablas_csv.zip (versión para compartir). Súbelos con git commit y git push.')


def compartir(db, destino, plantilla, semillas):
    """Genera en `destino` la base, data.json, CSV y tablero sin datos personales."""
    db, destino = Path(db), Path(destino)
    if not db.exists():
        raise SystemExit(f'No existe {db}. Ejecuta primero: indice cargar')
    destino.mkdir(parents=True, exist_ok=True)
    copia = destino / 'indice_acreditacion_compartir.sqlite'
    shutil.copy2(db, copia)
    r = anonimizar_base(copia, semillas)
    exportar(copia, destino / 'data.json', destino / 'csv', destino / 'tablas_csv.zip')
    datos = json.loads((destino / 'data.json').read_text(encoding='utf-8'))
    datos['version'] = 'compartir'   # el tablero lo anuncia en el encabezado
    (destino / 'data.json').write_text(json.dumps(datos, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    tablero(destino / 'data.json', plantilla, destino / 'indice_acreditacion_abet.html')
    print(f'Versión para compartir: {r["evidencias_omitidas"]} evidencias con texto omitido, {r["tablas_quitadas"]} tablas de '
          f'personas quitadas, correos y profesores líderes omitidos → {destino}')
    return r
