"""Interfaz web local para que el comité valide correspondencias y etiquetas (tarea 5).

Solo biblioteca estándar (http.server + sqlite3). Escucha en 127.0.0.1: no es accesible desde otros equipos.
Cada decisión queda en la tabla 'decision' (ver decisiones.py). Uso: indice validar [--puerto 8765] [--abrir]
"""
import html
import json
import re
import sqlite3
import threading
import urllib.parse
import webbrowser
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from indice.decisiones import ROLES, DecisionInvalida, agregar_etiqueta, decidir_correspondencia, decidir_etiqueta
from indice.reproyectar import reproyectar

NIVELES = {'principal': 'base ABET (CNA, PAD, DM 2019)', 'complementaria': 'complementaria (anexos)',
           'escenario': 'escenario solo renovación (DM 2025)'}
POR_PAGINA = 50
e = html.escape

CSS = """
:root{--fondo:#f7f7f5;--panel:#fff;--texto:#1f2328;--suave:#59636e;--borde:#d8dee4;--acento:#1a7f5a;--acento-t:#fff;
--prop:#9a6700;--val:#1a7f5a;--desc:#b42318;--marca:#fff8c5}
@media (prefers-color-scheme:dark){:root{--fondo:#0f1215;--panel:#171b20;--texto:#e6edf3;--suave:#9aa5b1;--borde:#2d333b;
--acento:#3fb68b;--acento-t:#0f1215;--prop:#d4a72c;--val:#3fb68b;--desc:#f47067;--marca:#3b3218}}
*{box-sizing:border-box}body{margin:0;background:var(--fondo);color:var(--texto);font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
header{background:var(--panel);border-bottom:1px solid var(--borde);padding:10px 16px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}
header b{font-size:16px}nav a{margin-right:14px;color:var(--texto);text-decoration:none}nav a:hover{text-decoration:underline}
main{max-width:1200px;margin:0 auto;padding:16px}h1{font-size:20px;margin:6px 0 14px}h2{font-size:16px;margin:18px 0 8px}
.panel{background:var(--panel);border:1px solid var(--borde);border-radius:8px;padding:12px;margin-bottom:14px;overflow-x:auto}
table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--borde);vertical-align:top}
th{font-size:13px;color:var(--suave);font-weight:600}td.num{text-align:right;font-variant-numeric:tabular-nums}
.chip{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;border:1px solid currentColor}
.propuesta{color:var(--prop)}.validada{color:var(--val)}.descartada{color:var(--desc)}
.suave{color:var(--suave);font-size:13px}.fragmento{color:var(--suave);font-size:13px;max-width:520px}
form.filtros{display:flex;gap:8px;flex-wrap:wrap;align-items:end}label{font-size:13px;color:var(--suave);display:flex;flex-direction:column;gap:2px}
input,select,textarea,button{font:inherit;color:var(--texto);background:var(--panel);border:1px solid var(--borde);border-radius:6px;padding:5px 8px}
button{cursor:pointer}button.principal{background:var(--acento);color:var(--acento-t);border-color:var(--acento)}
button.peligro{color:var(--desc);border-color:var(--desc)}.barra{position:sticky;bottom:0;background:var(--panel);border-top:1px solid var(--borde);
padding:10px;display:flex;gap:8px;flex-wrap:wrap;align-items:end;margin-top:10px}.aviso{background:var(--marca);border:1px solid var(--borde);
padding:8px 12px;border-radius:6px;margin-bottom:12px}.error{border-color:var(--desc);color:var(--desc)}
pre{white-space:pre-wrap;font:13px/1.4 ui-monospace,Consolas,monospace;max-height:420px;overflow:auto}
a{color:var(--acento)}mark{background:var(--marca);color:inherit}details summary{cursor:pointer}.paginas a,.paginas b{margin-right:8px}
@media (max-width:700px){main{padding:10px}th:nth-child(n+5),td:nth-child(n+5){display:none}}
"""


def _qs(params, **cambios):
    p = {k: v for k, v in params.items() if v not in (None, '')}
    p.update({k: v for k, v in cambios.items()})
    return '?' + urllib.parse.urlencode({k: v for k, v in p.items() if v not in (None, '')})


def _chip(estado):
    return f'<span class="chip {e(estado or "")}">{e(estado or "—")}</span>'


class Pagina:
    """Construye el HTML de cada página a partir de la base."""

    def __init__(self, con, params, validador, mensaje=None, error=None):
        self.con, self.p, self.validador, self.mensaje, self.error = con, params, validador, mensaje, error

    def q(self, sql, *a):
        return self.con.execute(sql, a).fetchall()

    def marco(self, titulo, cuerpo):
        aviso = ''
        if self.mensaje: aviso = f'<div class="aviso">{e(self.mensaje)}</div>'
        if self.error: aviso = f'<div class="aviso error">{e(self.error)}</div>'
        return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titulo)} · Validación ABET</title><style>{CSS}</style></head><body>
<header><b>Validación del comité</b><nav><a href="/">Resumen</a><a href="/correspondencias">Correspondencias</a>
<a href="/etiquetas">Etiquetas</a><a href="/evidencias">Evidencias</a><a href="/cursos">Cursos</a><a href="/auditoria">Auditoría</a></nav>
<span class="suave">Validador: {e(self.validador) if self.validador else '<i>sin definir</i>'}</span></header>
<main>{aviso}<h1>{e(titulo)}</h1>{cuerpo}</main></body></html>"""

    def barra(self, objeto, volver):
        return f"""<div class="barra"><input type="hidden" name="objeto" value="{objeto}"><input type="hidden" name="volver" value="{e(volver)}">
<label>Validador<input name="validador" required value="{e(self.validador or '')}" placeholder="Nombre de quien decide"></label>
<label style="flex:1;min-width:200px">Comentario (opcional)<input name="comentario" placeholder="Motivo de la decisión"></label>
<button class="principal" name="accion" value="validar">Validar seleccionadas</button>
<button class="peligro" name="accion" value="descartar">Descartar seleccionadas</button>
<button name="accion" value="reabrir">Reabrir</button></div>
<script>document.querySelectorAll('input[data-todas]').forEach(c=>c.addEventListener('change',()=>
document.querySelectorAll('input[name=item]').forEach(x=>x.checked=c.checked)))</script>"""

    def paginacion(self, total, ruta):
        pag = int(self.p.get('pagina') or 1)
        n = max(1, -(-total // POR_PAGINA))
        if n == 1: return ''
        enlaces = [f'<b>{i}</b>' if i == pag else f'<a href="{ruta}{_qs(self.p, pagina=i)}">{i}</a>' for i in range(1, n + 1)]
        return f'<p class="paginas">Páginas: {"".join(enlaces)}</p>'

    # ---------- Páginas ----------
    def resumen(self):
        n = lambda s: self.q(s)[0][0]
        pend_c = n("SELECT COUNT(*) FROM correspondencia WHERE estado='propuesta'")
        pend_e = n("SELECT COUNT(*) FROM evidencia_nodo WHERE estado='propuesta'")
        sin = n("""SELECT COUNT(*) FROM evidencia e WHERE e.estado_revision<>'obsoleta' AND NOT EXISTS (SELECT 1 FROM evidencia_nodo en
                   JOIN nodo x ON x.id=en.nodo_id JOIN marco m ON m.id=x.marco_id AND m.codigo='ABET-EAC' WHERE en.evidencia_id=e.id AND en.estado<>'descartada')""")
        dec = n('SELECT COUNT(*) FROM decision')
        filas = ''.join(f"""<tr><td><a href="/etiquetas{_qs({}, nodo=c)}">{e(c)}</a></td><td>{e(nom)}</td><td class="num">{v}</td>
<td class="num">{pr}</td><td class="num">{d}</td><td class="num">{m}</td></tr>"""
                        for c, nom, _, v, pr, d, m in self.q('SELECT * FROM v_validacion_abet'))
        cuerpo = f"""<div class="panel"><p><b>{pend_c}</b> correspondencias y <b>{pend_e}</b> etiquetas esperan decisión ·
<b>{sin}</b> evidencias sin ninguna etiqueta ABET · <b>{dec}</b> decisiones registradas.</p>
<p class="suave">Sugerencia de orden: 1) decidir las correspondencias (definen qué se infiere); 2) revisar las etiquetas inferidas por criterio;
3) etiquetar a mano las evidencias sin etiqueta (sesión de inicio y PAD).</p></div>
<div class="panel"><h2>Estado por criterio ABET</h2><table><tr><th>Nodo</th><th>Nombre</th><th>Validadas por el comité</th><th>Propuestas</th>
<th>Descartadas</th><th>Manuales</th></tr>{filas}</table></div>"""
        return self.marco('Resumen', cuerpo)

    def correspondencias(self):
        estado = self.p.get('estado', 'propuesta')
        destino = self.p.get('destino', '')
        filas = self.q(f"""SELECT c.id, mo.codigo, o.codigo, o.nombre, d.codigo, d.nombre, c.tipo, c.estado, c.nota, c.validado_por,
                (SELECT COUNT(*) FROM evidencia_nodo en WHERE en.nodo_id=c.origen_id AND en.origen='extraccion') AS evidencias
            FROM correspondencia c JOIN nodo o ON o.id=c.origen_id JOIN marco mo ON mo.id=o.marco_id JOIN nodo d ON d.id=c.destino_id
            WHERE (?='' OR c.estado=?) AND (?='' OR d.codigo=?) ORDER BY d.orden, mo.codigo, o.codigo""", estado, estado, destino, destino)
        destinos = self.q("SELECT n.codigo FROM nodo n JOIN marco m ON m.id=n.marco_id AND m.codigo='ABET-EAC' ORDER BY n.orden")
        opciones = ''.join(f'<option {"selected" if d == destino else ""}>{e(d)}</option>' for (d,) in destinos)
        estados = ''.join(f'<option value="{x}" {"selected" if x == estado else ""}>{x or "todos"}</option>' for x in ('propuesta', 'validada', 'descartada', ''))
        tr = ''.join(f"""<tr><td><input type="checkbox" name="item" value="c:{i}"></td><td>{e(mo)}/{e(o)}<div class="suave">{e(onom)}</div></td>
<td>→ <a href="/etiquetas{_qs({}, nodo=d)}">{e(d)}</a><div class="suave">{e(dnom)}</div></td><td>{e(t)}</td><td>{_chip(est)}
<div class="suave">{e(vp or '')}</div></td><td class="num">{n}</td><td class="fragmento">{e(nota or '')}</td></tr>"""
                     for i, mo, o, onom, d, dnom, t, est, nota, vp, n in filas)
        cuerpo = f"""<form class="filtros panel" method="get"><label>Estado<select name="estado">{estados}</select></label>
<label>Destino ABET<select name="destino"><option value="">todos</option>{opciones}</select></label><button>Filtrar</button></form>
<form method="post" action="/decidir" class="panel"><p class="suave">Descartar una correspondencia retira las etiquetas que se infirieron
de ella (salvo las ya decididas). La columna "Evidencias" cuenta las diapositivas etiquetadas con el nodo de origen.</p>
<table><tr><th><input type="checkbox" data-todas></th><th>Origen</th><th>Destino</th><th>Tipo</th><th>Estado</th><th>Evidencias</th><th>Nota</th></tr>
{tr or '<tr><td colspan="7" class="suave">No hay correspondencias con este filtro.</td></tr>'}</table>{self.barra('correspondencia', '/correspondencias' + _qs(self.p))}</form>"""
        return self.marco(f'Correspondencias ({len(filas)})', cuerpo)

    def etiquetas(self):
        estado = self.p.get('estado', 'propuesta')
        nodo = self.p.get('nodo', '')
        origen = self.p.get('origen', '')
        texto = self.p.get('q', '')
        pag = int(self.p.get('pagina') or 1)
        donde = """FROM evidencia_nodo en JOIN evidencia ev ON ev.id=en.evidencia_id JOIN nodo n ON n.id=en.nodo_id
            JOIN marco m ON m.id=n.marco_id AND m.codigo='ABET-EAC'
            WHERE ev.estado_revision<>'obsoleta' AND (?='' OR en.estado=?) AND (?='' OR n.codigo=?) AND (?='' OR en.origen=?)
              AND (?='' OR ev.codigo LIKE ? OR ev.titulo LIKE ? OR ev.texto LIKE ?)"""
        like = f'%{texto}%'
        args = (estado, estado, nodo, nodo, origen, origen, texto, like, like, like)
        total = self.q('SELECT COUNT(*) ' + donde, *args)[0][0]
        filas = self.q(f"""SELECT en.evidencia_id, en.nodo_id, ev.codigo, ev.titulo, substr(replace(ev.texto, char(10), ' '), 1, 220), n.codigo,
                en.rol, en.origen, en.estado, en.validado_por,
                (SELECT group_concat(x.codigo, ', ') FROM evidencia_nodo y JOIN nodo x ON x.id=y.nodo_id JOIN marco mx ON mx.id=x.marco_id
                 WHERE y.evidencia_id=en.evidencia_id AND mx.codigo<>'ABET-EAC' AND y.origen='extraccion')
            {donde} ORDER BY n.orden, ev.codigo LIMIT ? OFFSET ?""", *args, POR_PAGINA, (pag - 1) * POR_PAGINA)
        nodos = self.q("SELECT n.codigo, n.nombre FROM nodo n JOIN marco m ON m.id=n.marco_id AND m.codigo='ABET-EAC' ORDER BY n.orden")
        opciones = ''.join(f'<option value="{e(c)}" {"selected" if c == nodo else ""}>{e(c)} · {e(nm[:40])}</option>' for c, nm in nodos)
        est = ''.join(f'<option value="{x}" {"selected" if x == estado else ""}>{x or "todos"}</option>' for x in ('propuesta', 'validada', 'descartada', ''))
        ori = ''.join(f'<option value="{x}" {"selected" if x == origen else ""}>{x or "todos"}</option>' for x in ('', 'inferida', 'manual', 'extraccion'))
        tr = ''.join(f"""<tr><td><input type="checkbox" name="item" value="e:{eid}:{nid}"></td>
<td><a href="/evidencia{_qs({}, codigo=cod)}">{e(cod)}</a><div class="suave">{e(via or '')}</div></td>
<td>{e(tit)}<div class="fragmento">{e(frag)}…</div></td><td>{e(nc)}</td><td>{e(rol)}</td><td>{e(ori_)}</td>
<td>{_chip(est_)}<div class="suave">{e(vp or '')}</div></td></tr>"""
                     for eid, nid, cod, tit, frag, nc, rol, ori_, est_, vp, via in filas)
        volver = '/etiquetas' + _qs(self.p)
        cuerpo = f"""<form class="filtros panel" method="get"><label>Nodo ABET<select name="nodo"><option value="">todos</option>{opciones}</select></label>
<label>Estado<select name="estado">{est}</select></label><label>Origen<select name="origen">{ori}</select></label>
<label>Buscar<input name="q" value="{e(texto)}" placeholder="código, título o texto"></label><button>Filtrar</button></form>
<form method="post" action="/decidir" class="panel"><table><tr><th><input type="checkbox" data-todas></th><th>Evidencia (vía CNA)</th>
<th>Título y fragmento</th><th>Nodo</th><th>Rol</th><th>Origen</th><th>Estado</th></tr>
{tr or '<tr><td colspan="7" class="suave">No hay etiquetas con este filtro.</td></tr>'}</table>
{self.paginacion(total, '/etiquetas')}{self.barra('etiqueta', volver)}</form>"""
        return self.marco(f'Etiquetas ABET ({total})', cuerpo)

    def evidencias(self):
        texto = self.p.get('q', '')
        tipo = self.p.get('tipo', '')
        sin = self.p.get('sin', '')
        nivel = self.p.get('nivel', '')
        pag = int(self.p.get('pagina') or 1)
        like = f'%{texto}%'
        donde = """FROM evidencia ev WHERE ev.estado_revision<>'obsoleta' AND (?='' OR ev.tipo=?)
            AND (?='' OR ev.nivel=?)
            AND (?='' OR ev.codigo LIKE ? OR ev.titulo LIKE ? OR ev.texto LIKE ? OR ev.texto_ocr LIKE ?)
            AND (?='' OR NOT EXISTS (SELECT 1 FROM evidencia_nodo en JOIN nodo x ON x.id=en.nodo_id JOIN marco m ON m.id=x.marco_id
                 AND m.codigo='ABET-EAC' WHERE en.evidencia_id=ev.id AND en.estado<>'descartada'))"""
        args = (tipo, tipo, nivel, nivel, texto, like, like, like, like, sin)
        total = self.q('SELECT COUNT(*) ' + donde, *args)[0][0]
        filas = self.q(f"""SELECT ev.codigo, ev.titulo, ev.tipo, ev.nivel,
                (SELECT group_concat(x.codigo || CASE en.estado WHEN 'descartada' THEN '✗' ELSE '' END, ', ') FROM evidencia_nodo en
                 JOIN nodo x ON x.id=en.nodo_id WHERE en.evidencia_id=ev.id)
            {donde} ORDER BY ev.codigo LIMIT ? OFFSET ?""", *args, POR_PAGINA, (pag - 1) * POR_PAGINA)
        tipos = ''.join(f'<option {"selected" if t == tipo else ""}>{e(t)}</option>' for (t,) in self.q('SELECT DISTINCT tipo FROM evidencia ORDER BY 1'))
        niveles = ''.join(f'<option value="{v}" {"selected" if v == nivel else ""}>{n}</option>' for v, n in NIVELES.items())
        tr = ''.join(f"""<tr><td><a href="/evidencia{_qs({}, codigo=c)}">{e(c)}</a></td><td>{e(t)}</td><td>{e(tp)}</td><td>{e(sd or '')}</td>
<td class="suave">{e(tags or '—')}</td></tr>""" for c, t, tp, sd, tags in filas)
        cuerpo = f"""<form class="filtros panel" method="get"><label>Buscar<input name="q" value="{e(texto)}" placeholder="texto, OCR, código"></label>
<label>Tipo<select name="tipo"><option value="">todos</option>{tipos}</select></label>
<label>Fuente<select name="nivel"><option value="">todas</option>{niveles}</select></label>
<label>Filtro<select name="sin"><option value="">todas</option><option value="1" {"selected" if sin else ""}>sin etiqueta ABET</option></select></label>
<button>Filtrar</button></form><div class="panel"><table><tr><th>Código</th><th>Título</th><th>Tipo</th><th>Fuente</th><th>Etiquetas</th></tr>
{tr or '<tr><td colspan="5" class="suave">Sin resultados.</td></tr>'}</table>{self.paginacion(total, '/evidencias')}</div>"""
        return self.marco(f'Evidencias ({total})', cuerpo)

    def evidencia(self):
        codigo = self.p.get('codigo', '')
        fila = self.q('SELECT id, codigo, titulo, tipo, texto, texto_ocr, fuente, archivo, pagina, sede, estado_revision FROM evidencia WHERE codigo=?', codigo)
        if not fila: return self.marco('Evidencia no encontrada', f'<p>No existe la evidencia {e(codigo)}.</p>')
        eid, cod, tit, tipo, texto, ocr, fuente, archivo, pagina, sede, rev = fila[0]
        etiquetas = self.q("""SELECT en.nodo_id, m.codigo, n.codigo, n.nombre, en.rol, en.origen, en.estado, en.validado_por FROM evidencia_nodo en
                              JOIN nodo n ON n.id=en.nodo_id JOIN marco m ON m.id=n.marco_id WHERE en.evidencia_id=? ORDER BY m.id, n.orden""", eid)
        tr = ''.join(f"""<tr><td><input type="checkbox" name="item" value="e:{eid}:{nid}"></td><td>{e(m)}/{e(c)}</td><td>{e(nm)}</td><td>{e(rol)}</td>
<td>{e(o)}</td><td>{_chip(est)}<div class="suave">{e(vp or '')}</div></td></tr>""" for nid, m, c, nm, rol, o, est, vp in etiquetas)
        nodos = self.q("SELECT n.id, m.codigo, n.codigo, n.nombre FROM nodo n JOIN marco m ON m.id=n.marco_id ORDER BY m.id<>2, m.id, n.orden")
        opciones = ''.join(f'<option value="{i}">{e(m)}/{e(c)} · {e(nm[:60])}</option>' for i, m, c, nm in nodos)
        roles = ''.join(f'<option>{r}</option>' for r in ROLES)
        graficas = self.q("""SELECT g.titulo, d.serie, group_concat(d.categoria || '=' || d.valor, '; ') FROM grafica g JOIN grafica_dato d ON d.grafica_id=g.id
                             WHERE g.evidencia_id=? GROUP BY g.id, d.serie_orden ORDER BY g.orden, d.serie_orden""", eid)
        gtxt = ''.join(f'<li><b>{e(t or "Gráfica")}</b> · {e(s)}: <span class="suave">{e(v[:400])}</span></li>' for t, s, v in graficas)
        volver = '/evidencia' + _qs({}, codigo=cod)
        cuerpo = f"""<div class="panel"><p><b>{e(tit)}</b></p><p class="suave">{e(tipo)} · {e(archivo or '')}{f' · página {pagina}' if pagina else ''}
 · sede {e(sede or '')} · revisión: {e(rev)}{f' · fuente: {e(fuente)}' if fuente else ''}</p></div>
<form method="post" action="/decidir" class="panel"><h2>Etiquetas</h2><table><tr><th><input type="checkbox" data-todas></th><th>Nodo</th><th>Nombre</th>
<th>Rol</th><th>Origen</th><th>Estado</th></tr>{tr or '<tr><td colspan="6" class="suave">Sin etiquetas.</td></tr>'}</table>{self.barra('etiqueta', volver)}</form>
<form method="post" action="/agregar" class="panel"><h2>Agregar etiqueta manual</h2><input type="hidden" name="evidencia_id" value="{eid}">
<input type="hidden" name="volver" value="{e(volver)}"><div class="filtros"><label style="flex:1;min-width:260px">Nodo<select name="nodo_id">{opciones}</select></label>
<label>Rol<select name="rol">{roles}</select></label><label>Validador<input name="validador" required value="{e(self.validador or '')}"></label>
<label style="flex:1;min-width:180px">Comentario<input name="comentario"></label><button class="principal">Agregar</button></div></form>
{f'<div class="panel"><h2>Datos de gráficas</h2><ul>{gtxt}</ul></div>' if gtxt else ''}
<div class="panel"><h2>Texto</h2><pre>{e(texto or '')}</pre>{f'<h2>Texto en imágenes (OCR)</h2><pre>{e(ocr)}</pre>' if ocr else ''}</div>"""
        return self.marco(cod, cuerpo)

    # ---------- Cursos y PAD ----------
    def cursos(self):
        texto = self.p.get('q', '').strip()
        like = f'%{texto}%'
        # Un PAD coincide si el texto aparece en su nombre, código, REA, actividades o bibliografía
        coincide = """(?='' OR p.nombre LIKE ? OR p.codigo LIKE ? OR p.rea_general LIKE ?
            OR EXISTS (SELECT 1 FROM pad_rea r WHERE r.pad_id=p.id AND r.texto LIKE ?)
            OR EXISTS (SELECT 1 FROM pad_experiencia x JOIN pad_actividad a ON a.experiencia_id=x.id WHERE x.pad_id=p.id
                       AND (a.nombre LIKE ? OR a.descripcion LIKE ? OR a.trabajo_estudiante LIKE ? OR a.lugares LIKE ?
                            OR a.instrumentos LIKE ? OR a.descripcion_instrumentos LIKE ? OR x.nombre LIKE ? OR x.descripcion LIKE ?))
            OR EXISTS (SELECT 1 FROM pad_bibliografia b WHERE b.pad_id=p.id AND (b.titulo LIKE ? OR b.autor LIKE ?)))"""
        args = (texto, like, like, like, like, like, like, like, like, like, like, like, like, like, like)
        filas = self.q(f"""SELECT p.codigo, p.nombre, c.nombre, p.programa, p.semestre, p.creditos, c.creditos,
                (SELECT COUNT(*) FROM pad_rea r WHERE r.pad_id=p.id),
                (SELECT COUNT(*) FROM pad_experiencia x JOIN pad_actividad a ON a.experiencia_id=x.id WHERE x.pad_id=p.id),
                (SELECT COUNT(*) FROM pad_bibliografia b WHERE b.pad_id=p.id)
            FROM pad p LEFT JOIN curso c ON c.id=p.curso_id WHERE {coincide}
            ORDER BY c.id IS NULL, p.semestre, p.nombre""", *args)
        sin_pad = [] if texto else self.q("SELECT curso, creditos_plan FROM v_pad_curso WHERE estado='sin PAD' ORDER BY curso")
        # Ruta de formación 2020-2027 (plan-estudios-agronomica-v4): período, número, créditos y prerrequisitos
        ruta = [] if texto else self.q("""SELECT c.periodo, c.numero, c.nombre, c.creditos, c.categoria_abet,
                (SELECT group_concat(r.requisito, '; ') FROM curso_prerrequisito r WHERE r.curso_id=c.id),
                (SELECT MIN(p.codigo) FROM pad p WHERE p.curso_id=c.id)
            FROM curso c ORDER BY c.periodo, c.numero""")
        ruta_tr = ''.join(f"""<tr><td class="num">{per or ''}</td><td class="num">{num or ''}</td>
<td>{f'<a href="/curso{_qs({}, pad=pad)}">{e(nom)}</a>' if pad else e(nom)}</td><td class="num">{cr}</td><td>{e(cat)}</td>
<td class="suave">{e(req or '')}</td></tr>""" for per, num, nom, cr, cat, req, pad in ruta)

        def fila(cod, nom, curso, prog, sem, cr, cr_plan, nrea, nact, nbib):
            aviso = f' <span class="chip descartada" title="créditos del plan">plan {cr_plan}</span>' if cr_plan and cr != cr_plan else ''
            return f"""<tr><td class="num">{sem if sem is not None else ''}</td><td><a href="/curso{_qs({}, pad=cod, q=texto)}">{e(nom)}</a>
<div class="suave">{e(cod)}</div></td><td>{e(curso or '')}<div class="suave">{e('' if curso else (prog or '').title())}</div></td>
<td class="num">{cr if cr is not None else ''}{aviso}</td><td class="num">{nrea}</td><td class="num">{nact}</td><td class="num">{nbib}</td></tr>"""
        del_plan = ''.join(fila(*f) for f in filas if f[2])
        otros = ''.join(fila(*f) for f in filas if not f[2])
        cab = '<tr><th>Sem.</th><th>PAD</th><th>Curso del plan</th><th>Créditos</th><th>REA</th><th>Actividades</th><th>Bibliografía</th></tr>'
        cuerpo = f"""<form class="filtros panel" method="get"><label style="flex:1;min-width:260px">Buscar en los PAD
<input name="q" value="{e(texto)}" placeholder="p. ej. riego, Python, rúbrica, laboratorio de suelos, diseño"></label><button>Buscar</button>
{'<a href="/cursos">Quitar búsqueda</a>' if texto else ''}</form>
<div class="panel"><h2>Cursos del plan con PAD ({sum(1 for f in filas if f[2])})</h2><table>{cab}{del_plan or '<tr><td colspan="7" class="suave">Sin coincidencias.</td></tr>'}</table></div>
{f'<div class="panel"><h2>Otros programas (especializaciones) ({sum(1 for f in filas if not f[2])})</h2><table>{cab}{otros}</table></div>' if otros else ''}
{f'<div class="panel"><h2>Cursos del plan sin PAD ({len(sin_pad)})</h2><p class="suave">' + ', '.join(f'{e(c)} ({cr} cr.)' for c, cr in sin_pad) + '</p></div>' if sin_pad else ''}
{f'''<div class="panel"><h2>Ruta de formación y aprendizaje 2020–2027 ({sum(r[3] for r in ruta)} créditos)</h2>
<p class="suave">Fuente: plan-estudios-agronomica-v4. Los diagnósticos y nivelatorios (0 créditos) solo aparecen como prerrequisitos.</p>
<table><tr><th>Per.</th><th>N.º</th><th>Curso</th><th>Créditos</th><th>Categoría ABET</th><th>Prerrequisitos</th></tr>{ruta_tr}</table></div>''' if ruta else ''}"""
        return self.marco('Cursos y PAD' + (f' · «{texto}»' if texto else ''), cuerpo)

    def curso(self):
        cod = self.p.get('pad', '')
        texto = self.p.get('q', '').strip()
        fila = self.q("""SELECT p.id, p.codigo, p.nombre, p.programa, p.plantilla, p.idioma, p.semestre, p.creditos, p.relacion_creditos,
                p.prerrequisitos, p.justificacion, p.rea_general, p.acciones, p.archivo, p.paginas, c.nombre, c.categoria_abet, c.confianza
            FROM pad p LEFT JOIN curso c ON c.id=p.curso_id WHERE p.codigo=?""", cod)
        if not fila: return self.marco('PAD no encontrado', f'<p>No existe el PAD {e(cod)}. <a href="/cursos">Ver cursos</a></p>')
        (pid, cod, nom, prog, plantilla, idioma, sem, cr, rel, prer, just, rea_g, acciones, archivo, pags,
         curso, cat, conf) = fila[0]
        lista = lambda v: ', '.join(e(x) for x in json.loads(v)) if v else ''

        def resaltar(t):
            t = e(t or '')
            if texto:
                t = re.sub(re.escape(e(texto)), lambda m: f'<mark>{m.group()}</mark>', t, flags=re.I)
            return t
        reas = self.q('SELECT consecutivo, texto, peso FROM pad_rea WHERE pad_id=? ORDER BY consecutivo', pid)
        rea_tr = ''.join(f'<tr><td class="num">{n}</td><td>{resaltar(t)}</td><td class="num">{f"{p:g} %" if p is not None else ""}</td></tr>' for n, t, p in reas)
        fases = self.q('SELECT fase, descripcion FROM pad_fase WHERE pad_id=? ORDER BY orden', pid)
        fases_html = ''.join(f'<tr><td>{e(f)}</td><td class="fragmento">{resaltar(d)}</td></tr>' for f, d in fases)
        bloques = []
        for xid, tipo, xnom, xrea, xdesc, dims, integ, comps, compo, unidad, lineas in self.q(
                """SELECT id, tipo, nombre, rea, descripcion, dimensiones, integrantes, competencias, componentes, unidad_regional, lineas_translocales
                   FROM pad_experiencia WHERE pad_id=? ORDER BY orden""", pid):
            acts = self.q("""SELECT orden, etapa, nombre, semana_inicio, duracion_semanas, lugares, tipo_actividad, instrumentos, descripcion,
                    trabajo_estudiante, trabajo_profesor, descripcion_instrumentos, analisis_retroalimentacion, fase, recursos_cgca, recursos_externos
                FROM pad_actividad WHERE experiencia_id=? ORDER BY orden""", xid)
            filas_act = ''
            for (o, etapa, anom, sem_i, dur, lug, tip, ins, desc, est, prof, dins, anal, fase, rcgca, rext) in acts:
                detalle = ''.join(f'<p><b>{titulo}.</b> {resaltar(v)}</p>' for titulo, v in [
                    ('Descripción', desc), ('Trabajo del estudiante', est), ('Trabajo del profesor', prof),
                    ('Producto evaluado', dins), ('Análisis y retroalimentación', anal), ('Fase del MCA', fase)] if v)
                recursos = ''.join(f'<p><b>{titulo}.</b> {lista(v)}</p>' for titulo, v in [('Recursos CGCA', rcgca), ('Recursos externos', rext)] if v)
                filas_act += f"""<tr><td class="num">{sem_i or ''}</td><td class="num">{dur or ''}</td><td><b>{resaltar(anom)}</b>
{f'<div class="suave">{e(etapa)}</div>' if etapa else ''}<details><summary class="suave">ver detalle</summary>{detalle}{recursos}</details></td>
<td>{lista(lug)}</td><td class="fragmento">{e(tip or '')}</td><td>{lista(ins)}</td></tr>"""
            titulo_x = 'Soluciona un problema' if tipo == 'soluciona_problema' else 'Vive una experiencia'
            meta = ' · '.join(x for x in [f'REA {e(xrea)}' if xrea and len(xrea) < 4 else '', f'Dimensiones: {lista(dims)}' if dims else '',
                                          f'Integrantes: {integ}' if integ else '', f'Saber Pro: {lista(comps)}' if comps else ''] if x)
            bloques.append(f"""<div class="panel"><h2>{titulo_x}: {resaltar(xnom)}</h2><p class="suave">{meta}</p>
{f'<p class="suave">REA: {resaltar(xrea)}</p>' if xrea and len(xrea) >= 4 else ''}{f'<details><summary class="suave">Descripción de la experiencia</summary><p>{resaltar(xdesc)}</p></details>' if xdesc else ''}
<table><tr><th>Semana</th><th>Sem.</th><th>Actividad</th><th>Lugares</th><th>Tipo</th><th>Instrumentos</th></tr>
{filas_act or '<tr><td colspan="6" class="suave">Sin actividades registradas.</td></tr>'}</table></div>""")
        bib = self.q('SELECT autor, titulo, anio, isbn, identificador, editorial, url FROM pad_bibliografia WHERE pad_id=? ORDER BY orden', pid)
        bib_tr = ''.join(f"""<tr><td>{resaltar(a)}</td><td>{f'<a href="{e(u)}" target="_blank" rel="noopener">{resaltar(t)}</a>' if u else resaltar(t)}</td>
<td class="num">{an or ''}</td><td class="suave">{e(i or idf or '')}{f' · {e(ed)}' if ed else ''}</td></tr>""" for a, t, an, i, idf, ed, u in bib)
        recs = self.q('SELECT nombre, tipo, area FROM pad_recurso WHERE pad_id=? ORDER BY orden', pid)
        rec_tr = ''.join(f'<tr><td>{e(n)}</td><td>{e(t or "")}</td><td class="suave">{e(a or "")}</td></tr>' for n, t, a in recs)
        acc = json.loads(acciones) if acciones else {}
        cuerpo = f"""<p><a href="/cursos{_qs({}, q=texto)}">← Todos los cursos</a> · <a href="/evidencia{_qs({}, codigo='PAD-' + cod)}">Etiquetar este PAD / ver texto completo</a></p>
<div class="panel"><p><b>{e(cod)}</b> · {e((prog or '').title())} · plantilla {e(plantilla or '')}{' (inglés)' if idioma == 'en' else ''} · {pags} páginas · <span class="suave">{e(archivo)}</span></p>
<p>Semestre <b>{sem if sem is not None else '—'}</b> · <b>{cr}</b> créditos{f' (relación {e(rel)})' if rel else ''} · prerrequisitos: {e(prer or 'ninguno')}</p>
{f'<p>Curso del plan: <b>{e(curso)}</b> · categoría ABET actual: {e(cat)} (confianza {e(conf)})</p>' if curso else '<p class="suave">No está ligado a un curso del plan.</p>'}</div>
<div class="panel"><h2>Resultados de aprendizaje</h2><p><b>REA general.</b> {resaltar(rea_g)}</p>
<table><tr><th>N.º</th><th>REA específico</th><th>Peso</th></tr>{rea_tr}</table>
{f'<details><summary class="suave">Justificación</summary><p>{resaltar(just)}</p></details>' if just else ''}</div>
{f'<div class="panel"><h2>Fases del MCA</h2><table>{fases_html}</table></div>' if fases_html else ''}
{''.join(bloques)}
{f'<div class="panel"><h2>Acciones</h2>' + ''.join(f'<p><b>{e(k.replace("_", " ").capitalize())}.</b> {e(", ".join(v) if isinstance(v, list) else v)}</p>' for k, v in acc.items()) + '</div>' if acc else ''}
<div class="panel"><h2>Bibliografía ({len(bib)})</h2><table><tr><th>Autor</th><th>Título</th><th>Año</th><th>ISBN / editorial</th></tr>
{bib_tr or '<tr><td colspan="4" class="suave">El PAD no trae bibliografía en la tabla final.</td></tr>'}</table></div>
{f'<div class="panel"><details><summary><b>Recursos externos ({len(recs)})</b></summary><table><tr><th>Recurso</th><th>Tipo</th><th>Área</th></tr>{rec_tr}</table></details></div>' if recs else ''}"""
        return self.marco(nom, cuerpo)

    def auditoria(self):
        filas = self.q('SELECT fecha, validador, objeto, referencia, accion, estado_anterior, estado_nuevo, rol, comentario FROM decision ORDER BY id DESC LIMIT 500')
        tr = ''.join(f"""<tr><td class="suave">{e(f)}</td><td>{e(v)}</td><td>{e(o)}</td><td>{e(r)}</td><td>{e(a)}</td>
<td>{_chip(ea)} → {_chip(en)}</td><td>{e(rol or '')}</td><td class="fragmento">{e(c or '')}</td></tr>"""
                     for f, v, o, r, a, ea, en, rol, c in filas)
        cuerpo = f"""<div class="panel"><p class="suave">Últimas 500 decisiones. La tabla completa está en la base (tabla <code>decision</code>)
y se exporta en <code>tablas_csv.zip</code>.</p><table><tr><th>Fecha (UTC)</th><th>Validador</th><th>Objeto</th><th>Referencia</th><th>Acción</th>
<th>Estado</th><th>Rol</th><th>Comentario</th></tr>{tr or '<tr><td colspan="8" class="suave">Aún no hay decisiones.</td></tr>'}</table></div>"""
        return self.marco('Auditoría', cuerpo)


def crear_manejador(db):
    db = str(db)

    class Manejador(BaseHTTPRequestHandler):
        server_version = 'ValidacionABET/1.0'

        def log_message(self, formato, *args):   # silencioso: la terminal queda para los avisos
            pass

        def _validador(self):
            c = cookies.SimpleCookie(self.headers.get('Cookie', ''))
            return urllib.parse.unquote(c['validador'].value) if 'validador' in c else ''

        def _responder(self, cuerpo, estado=200, extra=None):
            datos = cuerpo.encode('utf-8')
            self.send_response(estado)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(datos)))
            self.send_header('Cache-Control', 'no-store')
            for k, v in (extra or {}).items(): self.send_header(k, v)
            self.end_headers()
            self.wfile.write(datos)

        def _redirigir(self, destino, validador=None):
            self.send_response(303)
            self.send_header('Location', destino)
            if validador:
                self.send_header('Set-Cookie', f'validador={urllib.parse.quote(validador)}; Path=/; Max-Age=31536000; SameSite=Strict')
            self.end_headers()

        def do_GET(self):
            url = urllib.parse.urlsplit(self.path)
            params = {k: v[-1] for k, v in urllib.parse.parse_qs(url.query).items()}
            rutas = {'/': 'resumen', '/correspondencias': 'correspondencias', '/etiquetas': 'etiquetas',
                     '/evidencias': 'evidencias', '/evidencia': 'evidencia', '/auditoria': 'auditoria',
                     '/cursos': 'cursos', '/curso': 'curso'}
            if url.path not in rutas:
                return self._responder('<p>No encontrado</p>', 404)
            con = sqlite3.connect(db)
            try:
                pagina = Pagina(con, params, self._validador(), params.pop('ok', None), params.pop('error', None))
                self._responder(getattr(pagina, rutas[url.path])())
            finally:
                con.close()

        def do_POST(self):
            # Solo se aceptan formularios de esta misma interfaz (protección básica contra CSRF)
            origen = self.headers.get('Origin') or self.headers.get('Referer') or ''
            host = urllib.parse.urlsplit(origen).netloc
            if origen and host != self.headers.get('Host'):
                return self._responder('<p>Origen no permitido</p>', 403)
            largo = int(self.headers.get('Content-Length') or 0)
            form = urllib.parse.parse_qs(self.rfile.read(largo).decode('utf-8'))
            uno = lambda k: (form.get(k) or [''])[-1]
            volver = uno('volver') or '/'
            if not volver.startswith('/'): volver = '/'
            validador = uno('validador').strip()
            con = sqlite3.connect(db)
            con.execute('PRAGMA foreign_keys = ON')
            try:
                if self.path == '/decidir':
                    items, accion, comentario = form.get('item', []), uno('accion'), uno('comentario')
                    if not items: raise DecisionInvalida('No seleccionaste ninguna fila')
                    hubo_corr = False
                    for it in items:
                        partes = it.split(':')
                        if partes[0] == 'c':
                            decidir_correspondencia(con, int(partes[1]), accion, validador, comentario); hubo_corr = True
                        elif partes[0] == 'e':
                            decidir_etiqueta(con, int(partes[1]), int(partes[2]), accion, validador, comentario)
                    con.close()
                    if hubo_corr: reproyectar(db)   # sincroniza las inferidas con la nueva decisión
                    mensaje = f'{len(items)} decisión(es) registrada(s): {accion}'
                elif self.path == '/agregar':
                    agregar_etiqueta(con, int(uno('evidencia_id')), int(uno('nodo_id')), uno('rol'), validador, uno('comentario'))
                    mensaje = 'Etiqueta manual agregada'
                else:
                    return self._responder('<p>No encontrado</p>', 404)
                sep = '&' if '?' in volver else '?'
                self._redirigir(f'{volver}{sep}ok={urllib.parse.quote(mensaje)}', validador)
            except (DecisionInvalida, ValueError) as ex:
                sep = '&' if '?' in volver else '?'
                self._redirigir(f'{volver}{sep}error={urllib.parse.quote(str(ex))}', validador or None)
            finally:
                try: con.close()
                except sqlite3.ProgrammingError: pass

    return Manejador


def servidor(db, puerto=8765):
    """Crea el servidor sin arrancarlo (útil para pruebas: puerto 0 elige uno libre)."""
    db = Path(db)
    if not db.exists():
        raise SystemExit(f'No existe {db}. Ejecuta primero: indice todo')
    con = sqlite3.connect(db)
    tiene = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='decision'").fetchone()[0]
    con.close()
    if not tiene:
        raise SystemExit('La base no tiene la tabla de auditoría. Ejecuta primero: indice cargar (la migra al esquema actual)')
    try:
        return _Servidor(('127.0.0.1', puerto), crear_manejador(db))
    except OSError:
        raise SystemExit(f'El puerto {puerto} ya está en uso (¿otra interfaz abierta?). Ciérrala o usa --puerto con otro número.')


class _Servidor(ThreadingHTTPServer):
    # En Windows, SO_REUSEADDR deja que dos servidores escuchen en el mismo puerto y responda el viejo sin aviso
    allow_reuse_address = False
    daemon_threads = True


def validar(db, puerto=8765, abrir=False):
    srv = servidor(db, puerto)
    url = f'http://127.0.0.1:{srv.server_address[1]}/'
    print(f'Interfaz de validación en {url}  (Ctrl+C para terminar)')
    if abrir: threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\nInterfaz detenida.')
    finally:
        srv.server_close()
