"""Genera el tablero HTML autocontenido a partir de data.json y template.html."""
import sys
salida = sys.argv[1] if len(sys.argv) > 1 else 'indice_acreditacion_abet.html'
datos = open('data.json', encoding='utf-8').read().replace('</', '<\\/')
html = open('template.html', encoding='utf-8').read().replace('__DATA__', datos)
open(salida, 'w', encoding='utf-8').write(html)
print(f'Tablero generado: {salida}')
