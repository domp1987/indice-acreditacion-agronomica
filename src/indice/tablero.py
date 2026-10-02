"""Genera el tablero HTML autocontenido inyectando data.json en __DATA__ y ECharts (plantillas/vendor) en __ECHARTS__."""
import base64
from pathlib import Path


def tablero(data_json, plantilla, salida):
    data_json = Path(data_json)
    if not data_json.exists():
        raise SystemExit(f'No existe {data_json}. Ejecuta primero: indice exportar')
    # '</' se escapa para que ningún texto cierre el <script> antes de tiempo
    datos = data_json.read_text(encoding='utf-8').replace('</', '<\\/')
    html = Path(plantilla).read_text(encoding='utf-8').replace('__DATA__', datos)
    # ECharts 5.6.0 (Apache-2.0) para los radares; se incrusta para no depender de internet
    echarts = Path(plantilla).parent / 'vendor' / 'echarts.min.js'
    if '__ECHARTS__' in html:
        js = echarts.read_text(encoding='utf-8').replace('</script', '<\\/script') if echarts.exists() else ''
        html = html.replace('__ECHARTS__', js)
    # Imagotipo oficial de la Universidad (manual ECOM002), incrustado como data URI
    logo = Path(plantilla).parent / 'img' / 'imagotipo-ucundinamarca.jpg'
    if '__LOGO__' in html and logo.exists():
        html = html.replace('__LOGO__', 'data:image/jpeg;base64,' + base64.b64encode(logo.read_bytes()).decode())
    Path(salida).write_text(html, encoding='utf-8')
    print(f'Tablero: {salida}')
