"""Recursos digitales del proyecto Jardín Vivo RA (realidad aumentada de plantas medicinales, UCundinamarca).

Inventario técnico, solo con la biblioteca estándar:
- modelos 3D .glb (Modelos/ y AR_models/): lee el bloque JSON del GLB → vértices, triángulos, mallas, materiales,
  texturas, compresión Draco, herramienta que lo generó y dimensiones de la caja envolvente;
- fotografías 360 (Imagenes360/): dimensiones del JPEG, si es equirectangular (2:1), cámara y fecha del EXIF
  (no se leen coordenadas GPS);
- videos 360 .mp4: duración y resolución de la cabecera MP4.
Resultado en salida/recursos_ra.json, con caché por archivo. Cada colección es una evidencia 'RA-…' con su tabla,
nivel 'principal' (son recursos vigentes del programa) y proceso 'acreditacion'.
"""
import json
import re
import struct
from pathlib import Path

EXT_IMG = ('.jpg', '.jpeg')


def leer_glb(ruta):
    with open(ruta, 'rb') as f:
        cab = f.read(12)
        if cab[:4] != b'glTF': return None
        largo, tipo = struct.unpack('<I4s', f.read(8))
        g = json.loads(f.read(largo)) if tipo == b'JSON' else {}
    acc = g.get('accessors', [])
    vert = tri = 0
    minimo, maximo = [float('inf')] * 3, [float('-inf')] * 3
    for m in g.get('meshes', []):
        for p in m.get('primitives', []):
            pos = p.get('attributes', {}).get('POSITION')
            if pos is not None and pos < len(acc):
                a = acc[pos]
                vert += a.get('count', 0)
                if a.get('min') and a.get('max'):
                    minimo = [min(x, y) for x, y in zip(minimo, a['min'])]
                    maximo = [max(x, y) for x, y in zip(maximo, a['max'])]
            idx = p.get('indices')
            if idx is not None and idx < len(acc): tri += acc[idx].get('count', 0) // 3
            elif pos is not None and pos < len(acc): tri += acc[pos].get('count', 0) // 3
    dims = [round(b - a, 3) for a, b in zip(minimo, maximo)] if minimo[0] != float('inf') else None
    return dict(vertices=vert, triangulos=tri, mallas=len(g.get('meshes', [])), materiales=len(g.get('materials', [])),
                texturas=len(g.get('textures', [])), draco='KHR_draco_mesh_compression' in g.get('extensionsUsed', []),
                generador=(g.get('asset', {}).get('generator') or '')[:60], dimensiones=dims)


def _exif(datos):
    """Make, Model y DateTimeOriginal de un bloque EXIF (TIFF). Sin GPS."""
    if datos[:6] != b'Exif\x00\x00': return {}
    t = datos[6:]
    orden = '<' if t[:2] == b'II' else '>'
    leer16 = lambda o: struct.unpack(orden + 'H', t[o:o + 2])[0]
    leer32 = lambda o: struct.unpack(orden + 'I', t[o:o + 4])[0]
    out = {}

    def ifd(o):
        sub = None
        for i in range(leer16(o)):
            e = o + 2 + i * 12
            etq, tipo, n = leer16(e), leer16(e + 2), leer32(e + 4)
            if tipo == 2:   # ASCII
                off = e + 8 if n <= 4 else leer32(e + 8)
                v = t[off:off + n].split(b'\x00')[0].decode('latin-1').strip()
                if etq == 0x010F: out['marca'] = v
                elif etq == 0x0110: out['modelo'] = v
                elif etq in (0x9003, 0x0132) and 'fecha' not in out: out['fecha'] = v
            elif etq == 0x8769: sub = leer32(e + 8)
        return sub
    try:
        sub = ifd(leer32(4))
        if sub: ifd(sub)
    except (struct.error, IndexError):
        pass
    return out


def leer_jpeg(ruta):
    """Ancho, alto y EXIF básico recorriendo los marcadores del JPEG."""
    info = {}
    with open(ruta, 'rb') as f:
        if f.read(2) != b'\xff\xd8': return None
        while True:
            m = f.read(2)
            if len(m) < 2 or m[0] != 0xFF: break
            if m[1] in (0xD8, 0x01) or 0xD0 <= m[1] <= 0xD7: continue
            largo = struct.unpack('>H', f.read(2))[0]
            if m[1] == 0xE1 and 'fecha' not in info:
                info.update(_exif(f.read(largo - 2))); continue
            if m[1] in (0xC0, 0xC1, 0xC2):
                alto, ancho = struct.unpack('>xHH', f.read(5))
                info.update(ancho=ancho, alto=alto); break
            f.seek(largo - 2, 1)
    if 'ancho' in info:
        info['equirectangular'] = abs(info['ancho'] / info['alto'] - 2) < 0.02
    return info


def leer_mp4(ruta):
    """Duración (s) y resolución de la primera pista de video, leyendo las cajas moov/mvhd/tkhd."""
    info = {}
    with open(ruta, 'rb') as f:
        datos = f.read(64 * 1024 * 1024) if Path(ruta).stat().st_size < 64 * 1024 * 1024 else None
        if datos is None or b'moov' not in datos:   # moov al final del archivo
            tam = Path(ruta).stat().st_size
            f.seek(max(0, tam - 8 * 1024 * 1024)); datos = f.read()
    i = datos.find(b'mvhd')
    if i > 0:
        v = datos[i + 4]
        escala, dur = (struct.unpack('>IQ', datos[i + 24:i + 36]) if v == 1 else struct.unpack('>II', datos[i + 16:i + 24]))
        if escala: info['duracion_s'] = round(dur / escala, 1)
    for m in re.finditer(b'tkhd', datos):
        v = datos[m.start() + 4]
        base = m.start() + 4 + (92 if v == 1 else 80)
        ancho, alto = struct.unpack('>II', datos[base:base + 8])
        if ancho >> 16 and alto >> 16:
            info.update(ancho=ancho >> 16, alto=alto >> 16); break
    return info


def evidencias_ra(datos):
    """Una evidencia por colección, con su tabla técnica y un texto que resume lo que muestra."""
    if not datos: return []
    fuente = 'Proyecto Jardín Vivo RA (UCundinamarca)'
    base = dict(texto_ocr=None, fuente=fuente, pagina=None, sede='Programa', proceso='acreditacion', nivel='principal')
    out = []
    m, ar = datos.get('modelos', []), datos.get('modelos_ar', [])
    if m:
        gen = sorted({x.get('generador') or 's. d.' for x in m})
        texto = (f'{len(m)} modelos 3D fuente de plantas medicinales (GLB), generados con {", ".join(gen)}: '
                 f'{", ".join(x["nombre"] for x in m)}. Promedio de {sum(x.get("vertices", 0) for x in m) // len(m):,} vértices y '
                 f'{sum(x["mb"] for x in m) / len(m):.0f} MB por modelo; {sum(1 for x in m if x.get("draco"))} con compresión Draco. '
                 'Son la versión de alta resolución: no aptos para realidad aumentada en celulares sin optimizar.')
        filas = [['Modelo', 'MB', 'Vértices', 'Triángulos', 'Texturas', 'Draco', 'Generador', 'Dimensiones (u)']] + [
            [x['nombre'], x['mb'], x.get('vertices'), x.get('triangulos'), x.get('texturas'), 'sí' if x.get('draco') else 'no',
             x.get('generador'), ' × '.join(str(d) for d in x.get('dimensiones') or [])] for x in m]
        out.append(dict(base, codigo='RA-MODELOS', titulo='Jardín Vivo RA · Modelos 3D fuente de plantas medicinales', tipo='recurso_digital',
                        texto=texto, archivo='Modelos/', _tablas=[dict(leyenda='Inventario técnico de los modelos 3D fuente', filas=filas)]))
    if ar:
        texto = (f'{len(ar)} modelos 3D optimizados para realidad aumentada web (MindAR + A-Frame, marcadores de imagen): '
                 f'{", ".join(x["nombre"] for x in ar)}. Promedio de {sum(x.get("vertices", 0) for x in ar) // len(ar):,} vértices y '
                 f'{sum(x["mb"] for x in ar) * 1000 / len(ar):.0f} KB por modelo, generados de forma procedimental.')
        filas = [['Modelo', 'KB', 'Vértices', 'Triángulos', 'Draco', 'Generador']] + [
            [x['nombre'], round(x['mb'] * 1000), x.get('vertices'), x.get('triangulos'), 'sí' if x.get('draco') else 'no', x.get('generador')] for x in ar]
        out.append(dict(base, codigo='RA-MODELOS-AR', titulo='Jardín Vivo RA · Modelos 3D para realidad aumentada', tipo='recurso_digital',
                        texto=texto, archivo='AR_models/', _tablas=[dict(leyenda='Modelos listos para la aplicación de realidad aumentada', filas=filas)]))
    im, vid = datos.get('imagenes360', []), datos.get('videos360', [])
    if im or vid:
        nombradas = [x['nombre'] for x in im if not x['nombre'].startswith(('AKASO', 'A360', 'WhatsApp', '1000'))]
        fechas = sorted({(x.get('fecha') or '')[:10].replace(':', '-') for x in im if x.get('fecha')})
        texto = (f'{len(im)} fotografías 360 ({sum(1 for x in im if x.get("equirectangular"))} equirectangulares, '
                 f'{sum(1 for x in im if x.get("ancho") == 12032)} de 12032 × 6016 px) y {len(vid)} videos 360 '
                 f'({sum(x.get("duracion_s", 0) for x in vid):.0f} s) de espacios de práctica del programa, tomadas entre '
                 f'{fechas[0] if fechas else "?"} y {fechas[-1] if fechas else "?"}. Escenas identificadas: {", ".join(nombradas)}. '
                 'Sirven para recorridos virtuales (laboratorio virtual de campo) del vivero, el jardín de plantas medicinales, '
                 'el beneficiadero, los cultivos de café, lulo y plátano y el mirador de Chinauta.')
        filas = [['Archivo', 'MB', 'Ancho', 'Alto', '360 (2:1)', 'Cámara', 'Fecha']] + [
            [x['nombre'], x['mb'], x.get('ancho'), x.get('alto'), 'sí' if x.get('equirectangular') else 'no', x.get('modelo'), x.get('fecha')]
            for x in im] + [[x['nombre'], x['mb'], x.get('ancho'), x.get('alto'), 'video', '', f'{x.get("duracion_s")} s'] for x in vid]
        out.append(dict(base, codigo='RA-360', titulo='Jardín Vivo RA · Fotografías y videos 360 de espacios de práctica', tipo='recurso_digital',
                        texto=texto, archivo='Imagenes360/', _tablas=[dict(leyenda='Inventario de fotografías y videos 360', filas=filas)]))
    return out


def _firma(ruta):
    st = ruta.stat()
    return f'{st.st_size}-{int(st.st_mtime)}'


def inventariar(raiz, destino):
    """Escribe recursos_ra.json: {modelos: [...], modelos_ar: [...], imagenes360: [...], videos360: [...]}."""
    raiz, destino = Path(raiz), Path(destino)
    if not raiz.exists():
        print(f'Aviso: no existe la carpeta del proyecto de RA {raiz}; se omite.')
        return None
    previo = {}
    if destino.exists():
        for lista in json.loads(destino.read_text(encoding='utf-8')).values():
            for x in lista: previo[x['archivo']] = x
    out = dict(modelos=[], modelos_ar=[], imagenes360=[], videos360=[])

    def agregar(clave, ruta, lector):
        rel = ruta.relative_to(raiz).as_posix()
        firma = _firma(ruta)
        if rel in previo and previo[rel].get('firma') == firma:
            out[clave].append(previo[rel]); return
        datos = lector(ruta) or {}
        out[clave].append(dict(archivo=rel, nombre=ruta.stem, firma=firma, mb=round(ruta.stat().st_size / 1e6, 2), **datos))

    for ruta in sorted((raiz / 'Modelos').glob('*.glb')): agregar('modelos', ruta, leer_glb)
    for ruta in sorted((raiz / 'AR_models').glob('*.glb')): agregar('modelos_ar', ruta, leer_glb)
    for ruta in sorted((raiz / 'Imagenes360').iterdir()):
        if ruta.suffix.lower() in EXT_IMG: agregar('imagenes360', ruta, leer_jpeg)
        elif ruta.suffix.lower() == '.mp4': agregar('videos360', ruta, leer_mp4)
    destino.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    eq = sum(1 for x in out['imagenes360'] if x.get('equirectangular'))
    print(f'Recursos RA: {len(out["modelos"])} modelos fuente, {len(out["modelos_ar"])} modelos AR, '
          f'{len(out["imagenes360"])} imágenes ({eq} equirectangulares 360), {len(out["videos360"])} videos → {destino.name}')
    return out
