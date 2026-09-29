"""Lectura y validación de las semillas (datos/semillas/*.csv): los datos que no salen de las presentaciones.

Cada CSV es UTF-8 con encabezado. Una celda vacía significa NULL, salvo 'desagregacion' (texto vacío) y
'estado' (toma el valor por defecto del esquema). El orden de las filas es el orden de carga.
"""
import csv
import re
from pathlib import Path

ARCHIVOS = {
    'marcos': ['id', 'codigo', 'nombre', 'version', 'descripcion'],
    'nodos': ['marco', 'codigo', 'nombre', 'tipo', 'padre', 'orden', 'descripcion'],
    'correspondencias': ['marco_origen', 'origen', 'marco_destino', 'destino', 'tipo', 'nota'],
    'indicadores': ['codigo', 'nombre', 'unidad', 'descripcion'],
    'indicador_nodos': ['indicador', 'marco', 'nodo', 'rol'],
    'mediciones': ['indicador', 'periodo', 'sede', 'valor', 'desagregacion', 'evidencia', 'nota'],
    'cursos': ['nombre', 'numero', 'componente_cma', 'creditos', 'periodo', 'categoria_abet', 'categoria_atmae', 'confianza', 'nota'],
    'prerrequisitos': ['curso', 'requisito'],
    'curso_outcomes': ['curso', 'outcome', 'nivel', 'estado', 'origen', 'puntaje', 'justificacion', 'validado_por'],
    'brechas': ['marco', 'nodo', 'titulo', 'descripcion', 'severidad', 'accion', 'responsable', 'estado'],
    'normativa_manual': ['tipo', 'numero', 'anio', 'organo', 'texto_a_buscar'],
    'normativa_excluir': ['tipo', 'numero', 'anio'],
    'pad_curso': ['pad', 'curso', 'nota'],
    'documentos': ['patron', 'prefijo', 'proceso', 'nivel', 'titulo'],
    'documento_nodos': ['patron', 'nodo', 'rol', 'nota'],
    'privacidad': ['patron', 'motivo'],
}
# Columnas numéricas por archivo (el resto es texto; 'periodo' es número en cursos y texto en mediciones)
ENTEROS = {'marcos': {'id'}, 'nodos': {'orden'}, 'cursos': {'numero', 'creditos', 'periodo'}, 'curso_outcomes': {'puntaje'},
           'normativa_manual': {'numero', 'anio'}, 'normativa_excluir': {'numero', 'anio'}}
REALES = {'mediciones': {'valor'}}
TEXTO_VACIO = {'desagregacion'}
NIVELES = ('principal', 'complementaria', 'escenario')   # peso de una fuente para ABET (esquema v8)   # columnas NOT NULL DEFAULT '' en el esquema


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
    for x in d['prerrequisitos']:
        if x['curso'] not in cursos: errores.append(f'prerrequisitos.csv: curso desconocido "{x["curso"]}"')
        if x['requisito'] not in cursos and not x['requisito'].startswith('Diagnóstico y nivelatorio'):
            errores.append(f'prerrequisitos.csv: requisito desconocido "{x["requisito"]}" de {x["curso"]}')
    vistos = set()
    for x in d['curso_outcomes']:
        clave = (x['curso'], x['outcome'])
        if x['curso'] not in cursos: errores.append(f'curso_outcomes.csv: curso desconocido "{x["curso"]}"')
        if ('ABET-EAC', x['outcome']) not in nodos or not x['outcome'].startswith('SO'):
            errores.append(f'curso_outcomes.csv: Student Outcome desconocido {x["outcome"]}')
        if x['nivel'] not in ('I', 'R', 'E'): errores.append(f'curso_outcomes.csv: nivel "{x["nivel"]}" en {clave} (usa I, R o E)')
        if x['estado'] not in ('propuesta', 'validada', 'descartada'): errores.append(f'curso_outcomes.csv: estado "{x["estado"]}" en {clave}')
        if x['estado'] == 'validada' and not x['validado_por']:
            errores.append(f'curso_outcomes.csv: {clave} está validada sin validado_por')
        if clave in vistos: errores.append(f'curso_outcomes.csv: fila repetida {clave}')
        vistos.add(clave)
    for c in d['cursos']:
        if c['categoria_atmae'] not in ('educacion_general', 'matematicas', 'ciencias_fisicas', 'ciencias_vida', 'gestion', 'tecnica', 'electivas'):
            errores.append(f'cursos.csv: categoria_atmae "{c["categoria_atmae"]}" en {c["nombre"]}')
    numeros = [c['numero'] for c in d['cursos'] if c['numero'] is not None]
    if len(numeros) != len(set(numeros)): errores.append('cursos.csv: número de la ruta repetido')
    for x in d['documentos']:
        if x['proceso'] not in ('acreditacion', 'resignificacion', 'ambos'):
            errores.append(f"documentos.csv: proceso desconocido '{x['proceso']}' ({x['prefijo']})")
        if x['nivel'] not in NIVELES:
            errores.append(f"documentos.csv: nivel desconocido '{x['nivel']}' ({x['prefijo']})")
    for x in d['privacidad']:
        try: re.compile(x['patron'])
        except re.error as err: errores.append(f"privacidad.csv: patrón inválido '{x['patron']}' ({err})")
        if not x['motivo']: errores.append(f"privacidad.csv: falta el motivo de '{x['patron']}'")
    for x in d['documento_nodos']:
        try: re.compile(x['patron'])
        except re.error as err: errores.append(f"documento_nodos.csv: patrón inválido '{x['patron']}' ({err})")
        if ('CNA', x['nodo']) not in nodos: errores.append(f"documento_nodos.csv: nodo CNA desconocido {x['nodo']}")
        if x['rol'] not in ('principal', 'parcial', 'apoyo'): errores.append(f"documento_nodos.csv: rol desconocido '{x['rol']}'")
    for b in d['brechas']:
        if (b['marco'], b['nodo']) not in nodos: errores.append(f'brechas.csv: nodo desconocido {b["marco"]}/{b["nodo"]}')
    if errores:
        raise ErrorSemilla('Errores en las semillas:\n  ' + '\n  '.join(errores[:30]))
