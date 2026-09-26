"""CLI del índice: indice {extraer, ocr, cargar, reproyectar, exportar, tablero, todo}."""
import argparse
import sys

from indice import __version__
from indice.cargar import cargar
from indice.config import PLANTILLA, cargar_rutas
from indice.exportar import exportar
from indice.extraer import extraer
from indice.fuentes import convertir_faltantes, listar_fuentes
from indice.ocr import ocr
from indice.pad import extraer_pads
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
    con_pdf.add_argument('--pdf', help='carpeta de presentaciones (PDF y PPTX, con subcarpetas)')
    con_ocr = argparse.ArgumentParser(add_help=False)
    con_ocr.add_argument('--rehacer-ocr', action='store_true', help='repite el OCR aunque esté en caché')
    motor = argparse.ArgumentParser(add_help=False)
    motor.add_argument('--motor', choices=['auto', 'pdftotext', 'pypdf'], default='auto',
                       help='extractor de texto; auto prefiere pdftotext (poppler)')
    motor.add_argument('--sin-ocr', action='store_true', help='no hace OCR de las imágenes')
    con_carga = argparse.ArgumentParser(add_help=False)
    con_carga.add_argument('--reconstruir', action='store_true',
                           help='respalda la base actual y la crea de nuevo (se pierden las decisiones del comité que tenga)')

    p = argparse.ArgumentParser(prog='indice', description='Índice de acreditación CNA → ABET')
    p.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    sub = p.add_subparsers(dest='comando', required=True)
    sub.add_parser('extraer', parents=[comun, con_pdf, motor, con_ocr], help='texto de los PDF, gráficas y tablas de los PPTX, OCR de imágenes y PAD')
    sub.add_parser('ocr', parents=[comun, con_pdf, con_ocr], help='solo el OCR de las imágenes (con caché)')
    sub.add_parser('pads', parents=[comun], help='solo extrae los Planes de Aprendizaje Digital (PAD) a pads.json')
    sub.add_parser('cargar', parents=[comun, con_carga], help='actualiza la base SQLite (incremental) desde lo extraído y las semillas')
    sub.add_parser('reproyectar', parents=[comun], help='infiere etiquetas ABET desde CNA y REA vía correspondencias')
    sub.add_parser('exportar', parents=[comun], help='genera data.json y los CSV')
    sub.add_parser('tablero', parents=[comun], help='genera el tablero HTML autocontenido')
    sub.add_parser('todo', parents=[comun, con_pdf, motor, con_ocr, con_carga], help='ejecuta el flujo completo')
    args = p.parse_args(argv)

    r = cargar_rutas(pdf=getattr(args, 'pdf', None), salida=args.salida, config=args.config)
    r.salida.mkdir(parents=True, exist_ok=True)
    pasos = ['extraer', 'cargar', 'reproyectar', 'exportar', 'tablero'] if args.comando == 'todo' else [args.comando]
    fuentes = None
    for paso in pasos:
        if paso in ('extraer', 'ocr') and fuentes is None:
            fuentes = convertir_faltantes(listar_fuentes(r.pdf), r.pdf_convertidos)
        if paso == 'extraer':
            extraer(fuentes, r.diapositivas, args.motor, r.poppler)
            extraer_pptx(fuentes, r.pptx_json, r.diapositivas)
            if not args.sin_ocr: ocr(fuentes, r.ocr_json, r.poppler, args.rehacer_ocr)
            extraer_pads(r.pads, r.pads_json, r.poppler)
        elif paso == 'ocr': ocr(fuentes, r.ocr_json, r.poppler, args.rehacer_ocr)
        elif paso == 'pads': extraer_pads(r.pads, r.pads_json, r.poppler)
        elif paso == 'cargar': cargar(r.db, r.diapositivas, r.semillas, r.pptx_json, r.ocr_json, args.reconstruir, r.pads_json)
        elif paso == 'reproyectar': reproyectar(r.db)
        elif paso == 'exportar': exportar(r.db, r.data_json, r.csv, r.csv_zip)
        elif paso == 'tablero': tablero(r.data_json, PLANTILLA, r.tablero)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
