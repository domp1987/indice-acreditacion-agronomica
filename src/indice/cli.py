"""CLI del índice: indice {extraer, cargar, reproyectar, exportar, tablero, todo}."""
import argparse
import sys

from indice import __version__
from indice.config import PLANTILLA, cargar_rutas
from indice.cargar import cargar
from indice.exportar import exportar
from indice.extraer import extraer
from indice.pptx import extraer_pptx
from indice.reproyectar import reproyectar
from indice.tablero import tablero


def main(argv=None):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    comun = argparse.ArgumentParser(add_help=False)
    comun.add_argument('--salida', help='carpeta de productos (por defecto, la de indice.toml o salida/)')
    comun.add_argument('--config', help='archivo de configuración (por defecto, indice.toml del proyecto)')
    con_pdf = argparse.ArgumentParser(add_help=False)
    con_pdf.add_argument('--pdf', help='carpeta con los PDF "Factor N....pdf"')
    con_pdf.add_argument('--motor', choices=['auto', 'pdftotext', 'pypdf'], default='auto',
                         help='extractor de texto; auto prefiere pdftotext (poppler)')

    p = argparse.ArgumentParser(prog='indice', description='Índice de acreditación CNA → ABET')
    p.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    sub = p.add_subparsers(dest='comando', required=True)
    sub.add_parser('extraer', parents=[comun, con_pdf], help='extrae el texto de los PDF y las gráficas y tablas de los PPTX')
    sub.add_parser('cargar', parents=[comun], help='crea la base SQLite desde lo extraído y los datos manuales')
    sub.add_parser('reproyectar', parents=[comun], help='infiere etiquetas ABET desde CNA y REA vía correspondencias')
    sub.add_parser('exportar', parents=[comun], help='genera data.json y los CSV')
    sub.add_parser('tablero', parents=[comun], help='genera el tablero HTML autocontenido')
    sub.add_parser('todo', parents=[comun, con_pdf], help='ejecuta el flujo completo')
    args = p.parse_args(argv)

    r = cargar_rutas(pdf=getattr(args, 'pdf', None), salida=args.salida, config=args.config)
    r.salida.mkdir(parents=True, exist_ok=True)
    pasos = ['extraer', 'cargar', 'reproyectar', 'exportar', 'tablero'] if args.comando == 'todo' else [args.comando]
    for paso in pasos:
        if paso == 'extraer':
            extraer(r.pdf, r.diapositivas, args.motor, r.poppler)
            extraer_pptx(r.pptx, r.pptx_json, r.diapositivas)
        elif paso == 'cargar': cargar(r.db, r.diapositivas, r.pptx_json)
        elif paso == 'reproyectar': reproyectar(r.db)
        elif paso == 'exportar': exportar(r.db, r.data_json, r.csv, r.csv_zip)
        elif paso == 'tablero': tablero(r.data_json, PLANTILLA, r.tablero)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
