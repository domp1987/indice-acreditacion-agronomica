"""Propuesta de aporte de cada curso a los Student Outcomes ABET (matriz I/R/E) a partir de los PAD.

No decide nada: escribe filas 'propuesta' en datos/semillas/curso_outcomes.csv, con el puntaje y la justificación
(qué REA, experiencias o actividades del PAD la sustentan). El comité edita esa semilla: cambia 'estado' a validada o
descartada, ajusta el nivel y firma en 'validado_por'. Al volver a proponer, las filas decididas (estado distinto de
propuesta u origen manual) se conservan tal cual y solo se recalculan las propuestas.

Indicios (texto normalizado, sin tildes):
- REA específicos del PAD pesan 3, experiencias 2 y actividades 1 (una vez por REA, experiencia o actividad);
- una experiencia 'soluciona un problema' suma 3 a SO1; las competencias Saber Pro de las experiencias suman 1
  (Comunicación Escrita → SO3; Competencias Ciudadanas → SO4).
Se propone el outcome si el puntaje llega a UMBRAL. Nivel según el período de la ruta: I (1–3), R (4–6) y E (7–9)
solo si algún REA lo sustenta (si no, R). Los cursos sin PAD (institucionales) reciben propuestas por su nombre,
con puntaje 0 y la justificación explícita.
"""
import csv
import re
import sqlite3
import unicodedata
from pathlib import Path

UMBRAL = 4
CAMPOS = ['curso', 'outcome', 'nivel', 'estado', 'origen', 'puntaje', 'justificacion', 'validado_por']

PATRONES = {
    'SO1': r'\bresolv|\bsolucion(ar|es)?\b|\bcalcul|\bmodel(o|os|ar|acion)\b|\bcuantific|\boptimiz',
    'SO2': r'\bdisen(ar|o|os|a|e)\b(?!\s+(de\s+)?experiment)|\bdimension(ar|amiento)|\bplan de manejo|\bpropuesta tecnica|\bprototipo',
    'SO3': r'\bexposicion|\bsustentacion|\bsocializ|\binforme|\bpresentacion oral|\bposter\b|\binfografia|\bpodcast|\bvideo\b|\bcomunic(ar|acion)',
    'SO4': r'\betic[ao]s?\b|\bresponsabilidad social|\bimpacto (social|ambiental)|\bnormativ|\bbienestar (animal|social)|\bderechos',
    'SO5': r'\bequipo|\bgrupal|\ben grupo|\bcolaborativ|\bparejas|\bcooperativ',
    'SO6': r'\bexperiment|\blaboratorio|\bmuestre|\banalisis de datos|\bestadistic|\bmedir\b|\bmedicion|\bhipotesis|\btratamientos\b',
    'SO7': r'\bautonom|\bindag|\brevision (bibliografica|documental)|\bconsulta\b|\bautoaprendizaje|\bbusqueda de informacion',
}
SABER_PRO = {'comunicacion escrita': 'SO3', 'competencias ciudadanas': 'SO4'}

# Cursos sin PAD: propuesta por el nombre (baja confianza, el comité decide)
POR_NOMBRE = [
    (r'^comunicacion y lectura critica', ['SO3']),
    (r'^lengua extranjera', ['SO3']),
    (r'^razonamiento logico', ['SO1']),
    (r'^ciudadania|^catedra generacion', ['SO4']),
    (r'^ciencia, tecnologia e innovacion', ['SO6', 'SO7']),
    (r'^emprendimiento e innovacion', ['SO5']),
]


def normalizar(t):
    return unicodedata.normalize('NFKD', (t or '').lower()).encode('ascii', 'ignore').decode()


def _nivel(periodo, con_rea):
    if periodo is None: return 'I'
    if periodo <= 3: return 'I'
    if periodo <= 6: return 'R'
    return 'E' if con_rea else 'R'


def proponer(db):
    """Filas propuestas {(curso, outcome): fila} calculadas desde los PAD de la base."""
    con = sqlite3.connect(db)
    patrones = {so: re.compile(p) for so, p in PATRONES.items()}
    propuestas = {}
    cursos = con.execute('SELECT id, nombre, periodo FROM curso ORDER BY periodo, numero').fetchall()
    for cid, curso, periodo in cursos:
        pads = con.execute('SELECT id, codigo FROM pad WHERE curso_id=?', (cid,)).fetchall()
        if not pads:
            for patron, sos in POR_NOMBRE:
                if re.search(patron, normalizar(curso)):
                    for so in sos:
                        propuestas[(curso, so)] = dict(curso=curso, outcome=so, nivel=_nivel(periodo, False), estado='propuesta',
                                                       origen='nombre', puntaje=0,
                                                       justificacion='Curso institucional sin PAD: propuesta por el nombre del curso')
            continue
        puntaje = {so: 0 for so in PATRONES}
        motivos = {so: [] for so in PATRONES}
        con_rea = {so: False for so in PATRONES}
        for pid, codigo in pads:
            for n, texto in con.execute('SELECT consecutivo, texto FROM pad_rea WHERE pad_id=?', (pid,)):
                t = normalizar(texto)
                for so, p in patrones.items():
                    m = p.search(t)
                    if m:
                        puntaje[so] += 3; con_rea[so] = True
                        motivos[so].append(f'{codigo} REA {n}: «{m.group().strip()}»')
            for tipo, nombre, desc, comps in con.execute('SELECT tipo, nombre, descripcion, competencias FROM pad_experiencia WHERE pad_id=?', (pid,)):
                t = normalizar(f'{nombre} {desc}')
                if tipo == 'soluciona_problema':
                    puntaje['SO1'] += 3; motivos['SO1'].append(f'{codigo} soluciona un problema: {(nombre or "")[:60]}')
                for so, p in patrones.items():
                    m = p.search(t)
                    if m:
                        puntaje[so] += 2; motivos[so].append(f'{codigo} experiencia: «{m.group().strip()}»')
                for comp, so in SABER_PRO.items():
                    if comp in normalizar(comps):
                        puntaje[so] += 1
            for (texto,) in con.execute("""SELECT coalesce(a.nombre,'')||' '||coalesce(a.descripcion,'')||' '||coalesce(a.trabajo_estudiante,'')||' '||
                        coalesce(a.descripcion_instrumentos,'')||' '||coalesce(a.tipo_actividad,'')||' '||coalesce(a.instrumentos,'')
                    FROM pad_actividad a JOIN pad_experiencia x ON x.id=a.experiencia_id WHERE x.pad_id=?""", (pid,)):
                t = normalizar(texto)
                for so, p in patrones.items():
                    if p.search(t): puntaje[so] += 1
        for so in PATRONES:
            if puntaje[so] < UMBRAL: continue
            actividades = puntaje[so] - 3 * sum('REA' in m for m in motivos[so])
            resumen = '; '.join(dict.fromkeys(motivos[so]))[:400] or f'{actividades} indicios en actividades o competencias'
            propuestas[(curso, so)] = dict(curso=curso, outcome=so, nivel=_nivel(periodo, con_rea[so]), estado='propuesta',
                                           origen='pad', puntaje=puntaje[so], justificacion=resumen)
    con.close()
    return propuestas


def leer_semilla(ruta):
    ruta = Path(ruta)
    if not ruta.exists(): return []
    with ruta.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def actualizar_semilla(db, ruta):
    """Recalcula las propuestas y reescribe la semilla conservando las filas decididas por el comité."""
    previas = leer_semilla(ruta)
    decididas = {(r['curso'], r['outcome']): r for r in previas if r['estado'] != 'propuesta' or r['origen'] == 'manual'}
    nuevas = proponer(db)
    filas = list(decididas.values()) + [f for k, f in nuevas.items() if k not in decididas]
    orden = {c: i for i, (c,) in enumerate(sqlite3.connect(db).execute('SELECT nombre FROM curso ORDER BY periodo, numero'))}
    filas.sort(key=lambda r: (orden.get(r['curso'], 999), r['outcome']))
    with Path(ruta).open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, lineterminator='\n')
        w.writeheader()
        for r in filas: w.writerow({c: r.get(c, '') for c in CAMPOS})
    retiradas = sum(1 for r in previas if r['estado'] == 'propuesta' and r['origen'] != 'manual' and (r['curso'], r['outcome']) not in nuevas)
    print(f'Outcomes: {len(nuevas)} propuestas calculadas, {len(decididas)} decisiones del comité conservadas, '
          f'{retiradas} propuestas retiradas → {Path(ruta).name}')
    return filas
