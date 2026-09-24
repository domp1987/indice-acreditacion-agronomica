"""Reproyección: las etiquetas extraídas (CNA, REA) generan etiquetas inferidas en el marco destino vía correspondencias.

Reglas (CLAUDE.md): el rol se traduce equivalente → principal, parcial → parcial, apoyo → apoyo; la etiqueta
nace 'inferida' y 'propuesta'. Las correspondencias descartadas no se usan. Es idempotente (INSERT OR IGNORE),
así que nunca sobrescribe una etiqueta que ya exista, incluidas las que el comité haya validado o descartado.
"""
import sqlite3
from pathlib import Path

ROL = {'equivalente': 'principal', 'parcial': 'parcial', 'apoyo': 'apoyo'}


def reproyectar(db, marco_destino='ABET-EAC'):
    db = Path(db)
    if not db.exists():
        raise SystemExit(f'No existe {db}. Ejecuta primero: indice cargar')
    con = sqlite3.connect(db)
    try:
        filas = con.execute("""
            SELECT en.evidencia_id, c.destino_id, c.tipo FROM evidencia_nodo en
            JOIN correspondencia c ON c.origen_id = en.nodo_id AND c.estado <> 'descartada'
            JOIN nodo d ON d.id = c.destino_id
            JOIN marco m ON m.id = d.marco_id AND m.codigo = ?
            WHERE en.origen = 'extraccion' AND en.estado <> 'descartada'""", (marco_destino,)).fetchall()
        antes = con.total_changes
        con.executemany("INSERT OR IGNORE INTO evidencia_nodo VALUES (?,?,?,'inferida','propuesta')",
                        [(eid, dest, ROL[t]) for eid, dest, t in filas])
        con.commit()
        nuevas = con.total_changes - antes
        print(f'Reproyección → {marco_destino}: {len(filas)} candidatas, {nuevas} etiquetas nuevas')
        return nuevas
    finally:
        con.close()
