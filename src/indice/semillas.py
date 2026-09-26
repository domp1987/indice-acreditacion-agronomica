"""Lectura y validación de las semillas (datos/semillas/*.csv): los datos que no salen de las presentaciones.

Cada CSV es UTF-8 con encabezado. Una celda vacía significa NULL, salvo 'desagregacion' (texto vacío) y
'estado' (toma el valor por defecto del esquema). El orden de las filas es el orden de carga.
"""
import csv
from pathlib import Path

ARCHIVOS = {
    'marcos': ['id', 'codigo', 'nombre', 'version', 'descripcion'],
    'nodos': ['marco', 'codigo', 'nombre', 'tipo', 'padre', 'orden', 'descripcion'],
    'correspondencias': ['marco_origen', 'origen', 'marco_destino', 'destino', 'tipo', 'nota'],
    'indicadores': ['codigo', 'nombre', 'unidad', 'descripcion'],
    'indicador_nodos': ['indicador', 'marco', 'nodo', 'rol'],
    'mediciones': ['indicador', 'periodo', 'sede', 'valor', 'desagregacion', 'evidencia', 'nota'],
    'cursos': ['nombre', 'componente_cma', 'creditos', 'periodo', 'categoria_abet', 'confianza', 'nota'],
    'brechas': ['marco', 'nodo', 'titulo', 'descripcion', 'severidad', 'accion', 'responsable', 'estado'],
    'normativa_manual': ['tipo', 'numero', 'anio', 'organo', 'texto_a_buscar'],
    'normativa_excluir': ['tipo', 'numero', 'anio'],
    'pad_curso': ['pad', 'curso', 'nota'],
}
# Columnas numéricas por archivo (el resto es texto; 'periodo' es número en cursos y texto en mediciones)
ENTEROS = {'marcos': {'id'}, 'nodos': {'orden'}, 'cursos': {'creditos', 'periodo'},
           'normativa_manual': {'numero', 'anio'}, 'normativa_excluir': {'numero', 'anio'}}
REALES = {'mediciones': {'valor'}}
TEXTO_VACIO = {'desagregacion'}   # columnas NOT NULL DEFAULT '' en el esquema


class ErrorSemilla(SystemExit):
    pass


def _convertir(nombre, n, col, v):
    if v == '':
        return '' if col in TEXTO_VACIO else None
    try:
        if col in ENTEROS.get(nombre, ()): return int(v)
        if col in REALES.get(nombre, ()): return float(v)
    except ValueError:
        raise ErrorSemilla(f'{nombre}.csv, fila {n}: "{col}" debe ser numérico y es "{v}"')
    return v


def leer(carpeta, nombre):
    """Filas del CSV como dicts con tipos convertidos. Verifica el encabezado."""
    ruta = Path(carpeta) / f'{nombre}.csv'
    if not ruta.exists():
        raise ErrorSemilla(f'Falta la semilla {ruta}')
    with open(ruta, newline='', encoding='utf-8-sig') as f:
        lector = csv.DictReader(f)
        if lector.fieldnames != ARCHIVOS[nombre]:
            raise ErrorSemilla(f'{ruta.name}: el encabezado debe ser {",".join(ARCHIVOS[nombre])}')
        return [{c: _convertir(nombre, n, c, v.strip()) for c, v in fila.items()} for n, fila in enumerate(lector, 2)]


def leer_todas(carpeta):
    datos = {nombre: leer(carpeta, nombre) for nombre in ARCHIVOS}
    validar(datos)
    return datos


def validar(d):
    """Revisa referencias entre semillas antes de tocar la base, para dar errores legibles."""
    errores = []
    marcos = {m['codigo'] for m in d['marcos']}
    nodos = set()
    for n in d['nodos']:
        if n['marco'] not in marcos: errores.append(f'nodos.csv: marco desconocido {n["marco"]} en {n["codigo"]}')
        if n['padre'] and (n['marco'], n['padre']) not in nodos:
            errores.append(f'nodos.csv: el padre {n["padre"]} de {n["codigo"]} debe aparecer antes en el mismo marco')
        if (n['marco'], n['codigo']) in nodos: errores.append(f'nodos.csv: nodo repetido {n["marco"]}/{n["codigo"]}')
        nodos.add((n['marco'], n['codigo']))
    for c in d['correspondencias']:
        for m, x in [(c['marco_origen'], c['origen']), (c['marco_destino'], c['destino'])]:
            if (m, x) not in nodos: errores.append(f'correspondencias.csv: nodo desconocido {m}/{x}')
        if c['marco_origen'] == c['marco_destino']:
            errores.append(f'correspondencias.csv: {c["origen"]}→{c["destino"]} une nodos del mismo marco')
    indicadores = {i['codigo'] for i in d['indicadores']}
    for x in d['indicador_nodos']:
        if x['indicador'] not in indicadores: errores.append(f'indicador_nodos.csv: indicador desconocido {x["indicador"]}')
        if (x['marco'], x['nodo']) not in nodos: errores.append(f'indicador_nodos.csv: nodo desconocido {x["marco"]}/{x["nodo"]}')
    for m in d['mediciones']:
        if m['indicador'] not in indicadores: errores.append(f'mediciones.csv: indicador desconocido {m["indicador"]}')
        if m['valor'] is None: errores.append(f'mediciones.csv: falta el valor de {m["indicador"]} {m["periodo"]}')
    cursos = {c['nombre'] for c in d['cursos']}
    for x in d['pad_curso']:
        if x['curso'] and x['curso'] not in cursos: errores.append(f'pad_curso.csv: curso desconocido "{x["curso"]}" para {x["pad"]}')
    for b in d['brechas']:
        if (b['marco'], b['nodo']) not in nodos: errores.append(f'brechas.csv: nodo desconocido {b["marco"]}/{b["nodo"]}')
    if errores:
        raise ErrorSemilla('Errores en las semillas:\n  ' + '\n  '.join(errores[:30]))
