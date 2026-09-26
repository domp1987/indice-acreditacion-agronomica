"""Decisiones del comité sobre correspondencias y etiquetas, con auditoría (tabla 'decision').

Una decisión marca la fila con validado_por/validado_en: desde ese momento ni 'cargar' ni 'reproyectar' la tocan.
'reabrir' devuelve la fila a 'propuesta' y borra validado_por, así el sistema vuelve a administrarla.
Todas las funciones reciben una conexión abierta y hacen commit; se usan desde la interfaz web y desde las pruebas.
"""
from datetime import datetime, timezone

ACCIONES = {'validar': 'validada', 'descartar': 'descartada', 'reabrir': 'propuesta'}
ROLES = ('principal', 'parcial', 'apoyo')


class DecisionInvalida(ValueError):
    pass


def _ahora():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _validar_entrada(accion, validador):
    if accion not in ACCIONES:
        raise DecisionInvalida(f'Acción desconocida: {accion}')
    validador = (validador or '').strip()
    if not validador:
        raise DecisionInvalida('Falta el nombre de quien valida')
    return validador


def _nodo(con, nodo_id):
    fila = con.execute('SELECT m.codigo, n.codigo FROM nodo n JOIN marco m ON m.id=n.marco_id WHERE n.id=?', (nodo_id,)).fetchone()
    if not fila: raise DecisionInvalida(f'Nodo inexistente: {nodo_id}')
    return '/'.join(fila)


def _auditar(con, **d):
    d.setdefault('fecha', _ahora())
    cols = ','.join(d)
    con.execute(f'INSERT INTO decision({cols}) VALUES ({",".join("?" * len(d))})', tuple(d.values()))


def decidir_correspondencia(con, corr_id, accion, validador, comentario=None):
    validador = _validar_entrada(accion, validador)
    fila = con.execute('SELECT origen_id, destino_id, estado, tipo FROM correspondencia WHERE id=?', (corr_id,)).fetchone()
    if not fila: raise DecisionInvalida(f'Correspondencia inexistente: {corr_id}')
    origen, destino, anterior, tipo = fila
    nuevo = ACCIONES[accion]
    ahora = _ahora()
    if accion == 'reabrir':
        con.execute('UPDATE correspondencia SET estado=?, validado_por=NULL, validado_en=NULL, actualizado_en=? WHERE id=?', (nuevo, ahora, corr_id))
    else:
        con.execute('UPDATE correspondencia SET estado=?, validado_por=?, validado_en=?, actualizado_en=? WHERE id=?',
                    (nuevo, validador, ahora, ahora, corr_id))
    _auditar(con, fecha=ahora, validador=validador, objeto='correspondencia', referencia=f'{_nodo(con, origen)} → {_nodo(con, destino)}',
             correspondencia_id=corr_id, accion=accion, estado_anterior=anterior, estado_nuevo=nuevo, rol=tipo,
             comentario=(comentario or '').strip() or None)
    con.commit()


def decidir_etiqueta(con, evidencia_id, nodo_id, accion, validador, comentario=None):
    validador = _validar_entrada(accion, validador)
    fila = con.execute('SELECT e.codigo, en.estado, en.rol, en.origen FROM evidencia_nodo en JOIN evidencia e ON e.id=en.evidencia_id '
                       'WHERE en.evidencia_id=? AND en.nodo_id=?', (evidencia_id, nodo_id)).fetchone()
    if not fila: raise DecisionInvalida(f'Etiqueta inexistente: {evidencia_id}/{nodo_id}')
    codigo, anterior, rol, origen = fila
    nuevo = ACCIONES[accion]
    if accion == 'reabrir' and origen == 'extraccion':
        nuevo = 'validada'   # las de extracción nacen validadas (vienen del encabezado de la diapositiva)
    ahora = _ahora()
    if accion == 'reabrir':
        con.execute('UPDATE evidencia_nodo SET estado=?, validado_por=NULL, validado_en=NULL, actualizado_en=? WHERE evidencia_id=? AND nodo_id=?',
                    (nuevo, ahora, evidencia_id, nodo_id))
    else:
        con.execute('UPDATE evidencia_nodo SET estado=?, validado_por=?, validado_en=?, actualizado_en=? WHERE evidencia_id=? AND nodo_id=?',
                    (nuevo, validador, ahora, ahora, evidencia_id, nodo_id))
    _auditar(con, fecha=ahora, validador=validador, objeto='etiqueta', referencia=f'{codigo} → {_nodo(con, nodo_id)}',
             evidencia_id=evidencia_id, nodo_id=nodo_id, accion=accion, estado_anterior=anterior, estado_nuevo=nuevo, rol=rol,
             comentario=(comentario or '').strip() or None)
    con.commit()


def agregar_etiqueta(con, evidencia_id, nodo_id, rol, validador, comentario=None):
    """Etiqueta manual del comité (nace validada). Si ya existe una etiqueta en ese par, se valida esa con el rol indicado."""
    validador = _validar_entrada('validar', validador)
    if rol not in ROLES: raise DecisionInvalida(f'Rol desconocido: {rol}')
    codigo = con.execute('SELECT codigo FROM evidencia WHERE id=?', (evidencia_id,)).fetchone()
    if not codigo: raise DecisionInvalida(f'Evidencia inexistente: {evidencia_id}')
    ahora = _ahora()
    previa = con.execute('SELECT estado FROM evidencia_nodo WHERE evidencia_id=? AND nodo_id=?', (evidencia_id, nodo_id)).fetchone()
    if previa:
        con.execute('UPDATE evidencia_nodo SET rol=?, estado=\'validada\', validado_por=?, validado_en=?, actualizado_en=? '
                    'WHERE evidencia_id=? AND nodo_id=?', (rol, validador, ahora, ahora, evidencia_id, nodo_id))
    else:
        con.execute('INSERT INTO evidencia_nodo(evidencia_id,nodo_id,rol,origen,estado,validado_por,validado_en,creado_en,actualizado_en) '
                    "VALUES (?,?,?,'manual','validada',?,?,?,?)", (evidencia_id, nodo_id, rol, validador, ahora, ahora, ahora))
    _auditar(con, fecha=ahora, validador=validador, objeto='etiqueta', referencia=f'{codigo[0]} → {_nodo(con, nodo_id)}',
             evidencia_id=evidencia_id, nodo_id=nodo_id, accion='agregar', estado_anterior=previa[0] if previa else None,
             estado_nuevo='validada', rol=rol, comentario=(comentario or '').strip() or None)
    con.commit()
