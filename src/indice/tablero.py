"""Genera el tablero HTML autocontenido inyectando data.json en el marcador __DATA__ de la plantilla."""
from pathlib import Path


def tablero(data_json, plantilla, salida):
    data_json = Path(data_json)
    if not data_json.exists():
        raise SystemExit(f'No existe {data_json}. Ejecuta primero: indice exportar')
    # '</' se escapa para que ningún texto cierre el <script> antes de tiempo
    datos = data_json.read_text(encoding='utf-8').replace('</', '<\\/')
    html = Path(plantilla).read_text(encoding='utf-8').replace('__DATA__', datos)
    Path(salida).write_text(html, encoding='utf-8')
    print(f'Tablero: {salida}')
