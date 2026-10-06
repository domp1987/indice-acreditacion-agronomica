"""Inventario de presentaciones fuente y su código de evidencia.

- "Factor N. ....pdf/.pptx"            → fuente FNN (evidencias FNN-Pppp)
- "N. ....pptx" (p. ej. Sesión de inicio) → fuente SNN (evidencias SNN-Pppp)
- Presentaciones institucionales (autoevaluación de la Universidad, modelo institucional del CNA):
  "Factor N. ..." → IFNN; las demás (p. ej. Presentación Rectoría) → IPNN. Su "Característica N." es la del modelo
  institucional (38 características), no la del programa. Se omiten las hojas de vida (datos personales).

Si una presentación no tiene PDF, se convierte con PowerPoint (solo Windows) a salida/pdf_convertidos/.
"""
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from indice.config import PAQUETE

PATRON_FACTOR = re.compile(r'Factor[ _](\d+)', re.I)
PATRON_SESION = re.compile(r'(\d+)\.\s*(.+)')
EXCLUIR = re.compile(r'\bHV\b|hoja[s]? de vida', re.I)   # hojas de vida de pares u otras personas


@dataclass
class Fuente:
    codigo: str                 # F05, S02
    nombre: str                 # "Factor 5. Aspectos...", "Presentación Rectoría"
    factor: int | None          # número de factor CNA; None para presentaciones que no son de factor
    pdf: Path | None
    pptx: Path | None
    ambito: str = 'programa'    # 'programa' o 'institucional'

    @property
    def archivo(self):
        """Nombre del archivo original (el PDF si existe; si no, el PPTX)."""
        return (self.pdf if self.pdf and self.pdf.parent.name != 'pdf_convertidos' else self.pptx or self.pdf).name

    @property
    def sede(self):
        return 'Programa' if self.factor and self.ambito == 'programa' else 'Institución'


def listar_fuentes(carpeta, ambito='programa'):
    """Recorre la carpeta (y subcarpetas) y agrupa PDF y PPTX con el mismo nombre."""
    grupos, otras = {}, {}
    for f in sorted(Path(carpeta).rglob('*')):
        if f.suffix.lower() not in ('.pdf', '.pptx') or f.name.startswith('~$') or EXCLUIR.search(f.name): continue
        if ambito == 'institucional':
            if m := PATRON_FACTOR.match(f.name):
                codigo, factor, nombre = f'IF{int(m.group(1)):02d}', int(m.group(1)), re.sub(r'\s*\(OK\)\s*$', '', f.stem)
            else:
                codigo = otras.setdefault(f.stem, f'IP{len(otras) + 1:02d}')
                factor, nombre = None, f.stem
        elif m := PATRON_FACTOR.match(f.name):
            codigo, factor, nombre = f'F{int(m.group(1)):02d}', int(m.group(1)), f.stem
        elif m := PATRON_SESION.match(f.name):
            codigo, factor, nombre = f'S{int(m.group(1)):02d}', None, Path(m.group(2)).stem
        else:
            continue
        g = grupos.setdefault(codigo, Fuente(codigo, nombre, factor, None, None, ambito))
        setattr(g, f.suffix.lower()[1:], f)
    if not grupos:
        raise SystemExit(f'No hay presentaciones ("Factor N...", "N. ...") en {carpeta}')
    return sorted(grupos.values(), key=lambda g: ('FSI'.index(g.codigo[0]), g.codigo))


def convertir_faltantes(fuentes, carpeta_salida):
    """Exporta a PDF (con PowerPoint) las presentaciones que solo tienen PPTX. Reutiliza conversiones previas."""
    carpeta_salida = Path(carpeta_salida)
    for f in fuentes:
        if f.pdf or not f.pptx: continue
        destino = carpeta_salida / (f.pptx.stem + '.pdf')
        if not destino.exists() or destino.stat().st_mtime < f.pptx.stat().st_mtime:
            if os.name != 'nt' or not shutil.which('powershell'):
                print(f'Aviso: {f.pptx.name} no tiene PDF y no hay PowerPoint para convertirlo; se omite su texto.')
                continue
            carpeta_salida.mkdir(parents=True, exist_ok=True)
            print(f'Convirtiendo con PowerPoint: {f.pptx.name}')
            r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(PAQUETE / 'pptx_a_pdf.ps1'),
                                '-Pptx', str(f.pptx), '-Pdf', str(destino)], capture_output=True, text=True, encoding='utf-8', errors='replace')
            if r.returncode != 0 or not destino.exists():
                print(f'Aviso: no se pudo convertir {f.pptx.name}: {r.stderr.strip()[:300]}')
                continue
        f.pdf = destino
    return fuentes
