"""Reproyección: las etiquetas extraídas (CNA, REA) generan etiquetas inferidas en el marco destino vía correspondencias.

Reglas (CLAUDE.md): el rol se traduce equivalente → principal, parcial → parcial, apoyo → apoyo; la etiqueta
nace 'inferida' y 'propuesta'. No se usan correspondencias ni etiquetas descartadas, ni evidencias obsoletas.
Regla adicional: una diapositiva de avance del plan de mejoramiento (sin característica) apoya el Criterio 4.

Sincroniza: agrega las inferidas que faltan, corrige el rol de las que cambiaron y retira las que ya no se
deducen. Nunca toca decisiones del comité (validado_por no nulo) ni etiquetas de otro origen. Es idempotente.
"""
import sqlite3
from pathlib import Path

ROL = {'equivalente': 'principal', 'parcial': 'parcial', 'apoyo': 'apoyo'}
FUERZA = {'principal': 0, 'parcial': 1, 'apoyo': 2}
AHORA = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"


def etiquetas_deseadas(con, marco_destino):
    """{(evidencia_id, nodo_id): rol} que se deducen hoy. Si varias correspondencias llevan al mismo nodo, gana el rol más fuerte."""
    filas = con.execute("""
        SELECT en.evidencia_id, c.destino_id, c.tipo FROM evidencia_nodo en
        JOIN evidencia e ON e.id = en.evidencia_id AND e.estado_revision <> 'obsoleta'
        JOIN correspondencia c ON c.origen_id = en.nodo_id AND c.estado <> 'descartada'
        JOIN nodo d ON d.id = c.destino_id
        JOIN marco m ON m.id = d.marco_id AND m.codigo = ?
        WHERE en.origen = 'extraccion' AND en.estado <> 'descartada'""", (marco_destino,)).fetchall()
    deseadas = {}
    for eid, nid, tipo in filas:
        rol = ROL[tipo]
        if (eid, nid) not in deseadas or FUERZA[rol] < FUERZA[deseadas[(eid, nid)]]:
            deseadas[(eid, nid)] = rol
    if marco_destino == 'ABET-EAC':
        c4 = con.execute("SELECT n.id FROM nodo n JOIN marco m ON m.id=n.marco_id AND m.codigo='ABET-EAC' WHERE n.codigo='C4'").fetchone()
        planes = con.execute("""
            SELECT e.id FROM evidencia e
            JOIN evidencia_nodo en ON en.evidencia_id = e.id AND en.origen = 'extraccion'
            JOIN nodo n ON n.id = en.nodo_id AND n.tipo = 'factor'
            WHERE e.tipo = 'plan_mejora' AND e.estado_revision <> 'obsoleta'""").fetchall()
        for (eid,) in planes:
            if c4: deseadas.setdefault((eid, c4[0]), 'apoyo')
    return deseadas, len(filas) + (len(planes) if marco_destino == 'ABET-EAC' else 0)


def reproyectar(db, marco_destino='ABET-EAC'):
    db = Path(db)
    if not db.exists():
        raise SystemExit(f'No existe {db}. Ejecuta primero: indice cargar')
    con = sqlite3.connect(db)
    try:
        deseadas, candidatas = etiquetas_deseadas(con, marco_destino)
        existentes = {(e, n): (rol, vp) for e, n, rol, vp in con.execute("""
            SELECT en.evidencia_id, en.nodo_id, en.rol, en.validado_por FROM evidencia_nodo en
            JOIN nodo d ON d.id = en.nodo_id JOIN marco m ON m.id = d.marco_id AND m.codigo = ?
            WHERE en.origen = 'inferida'""", (marco_destino,))}
        humanas = sum(1 for _, vp in existentes.values() if vp)
        nuevas = [(e, n, rol) for (e, n), rol in deseadas.items() if (e, n) not in existentes]
        cambio_rol = [(rol, e, n) for (e, n), rol in deseadas.items()
                      if (e, n) in existentes and existentes[(e, n)][0] != rol and not existentes[(e, n)][1]]
        retirar = [(e, n) for (e, n), (_, vp) in existentes.items() if (e, n) not in deseadas and not vp]
        antes = con.total_changes
        # INSERT OR IGNORE: si en ese par ya hay una etiqueta de otro origen (extracción o manual), prevalece esa
        con.executemany(f"""INSERT OR IGNORE INTO evidencia_nodo(evidencia_id,nodo_id,rol,origen,estado,creado_en,actualizado_en)
                            VALUES (?,?,?,'inferida','propuesta',{AHORA},{AHORA})""", sorted(nuevas))
        insertadas = con.total_changes - antes
        con.executemany(f"UPDATE evidencia_nodo SET rol=?, actualizado_en={AHORA} WHERE evidencia_id=? AND nodo_id=? AND origen='inferida'", cambio_rol)
        con.executemany("DELETE FROM evidencia_nodo WHERE evidencia_id=? AND nodo_id=? AND origen='inferida' AND validado_por IS NULL", retirar)
        con.commit()
        print(f'Reproyección → {marco_destino}: {candidatas} candidatas; {insertadas} etiquetas nuevas, {len(cambio_rol)} con rol corregido, '
              f'{len(retirar)} retiradas; {humanas} decisiones del comité respetadas')
        return dict(nuevas=insertadas, rol=len(cambio_rol), retiradas=len(retirar), humanas=humanas)
    finally:
        con.close()
