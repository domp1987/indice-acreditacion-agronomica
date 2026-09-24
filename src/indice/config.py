"""Rutas del proyecto: se leen de indice.toml y se pueden sobrescribir desde la CLI."""
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

PAQUETE = Path(__file__).resolve().parent
PROYECTO = PAQUETE.parents[1]
ESQUEMA = PAQUETE / 'schema.sql'
PLANTILLA = PROYECTO / 'plantillas' / 'template.html'


@dataclass
class Rutas:
    pdf: Path
    salida: Path
    poppler: Path | None = None

    @property
    def pptx_json(self): return self.salida / 'pptx.json'

    @property
    def ocr_json(self): return self.salida / 'ocr.json'

    @property
    def pdf_convertidos(self): return self.salida / 'pdf_convertidos'

    @property
    def db(self): return self.salida / 'indice_acreditacion.sqlite'

    @property
    def diapositivas(self): return self.salida / 'diapositivas.json'

    @property
    def data_json(self): return self.salida / 'data.json'

    @property
    def csv(self): return self.salida / 'csv'

    @property
    def csv_zip(self): return self.salida / 'tablas_csv.zip'

    @property
    def tablero(self): return self.salida / 'indice_acreditacion_abet.html'


def cargar_rutas(pdf=None, salida=None, config=None):
    """Combina, en este orden de prioridad: argumentos de la CLI, indice.toml y valores por defecto."""
    config = Path(config) if config else PROYECTO / 'indice.toml'
    cfg = {}
    if config.exists():
        with open(config, 'rb') as f:
            cfg = tomllib.load(f).get('rutas', {})
    base = config.parent

    def ruta(cli, clave, defecto):
        if cli: return Path(cli).resolve()
        valor = cfg.get(clave, defecto)
        if valor is None: return None
        v = Path(valor)
        return v if v.is_absolute() else (base / v).resolve()

    poppler = os.environ.get('INDICE_POPPLER') or None
    return Rutas(pdf=ruta(pdf, 'pdf', 'datos/pdf'),
                 salida=ruta(salida, 'salida', 'salida'),
                 poppler=Path(poppler) if poppler else ruta(None, 'poppler', None))
