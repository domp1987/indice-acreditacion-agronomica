# Índice de acreditación CNA → ABET (Ingeniería Agronómica)

Indexa la evidencia de la autoevaluación CNA en una base SQLite y la reproyecta hacia ABET-EAC. El contexto completo y el plan de trabajo están en [CLAUDE.md](CLAUDE.md).

## Requisitos
- Python 3.11 o superior.
- Opcional: PowerPoint (para presentaciones sin PDF) y el OCR de Windows con español instalado, o tesseract con `spa`.
- poppler (`pdftotext`, `pdfinfo`, `pdftoppm`) en el PATH, o su carpeta en `indice.toml` (`poppler = ...`) o en la variable `INDICE_POPPLER`. En Windows sirve la versión portable de <https://github.com/oschwartz10612/poppler-windows>.
- Si no hay poppler, se puede usar `--motor pypdf` (`pip install -e .[pypdf]`), pero el texto sale distinto y la base cambia.

## Instalación
```
pip install -e .[dev]
```

## Uso
La carpeta de PDF y la de salida se configuran en `indice.toml`; `--pdf` y `--salida` las sobrescriben.

```
indice todo                 # flujo completo
indice extraer --pdf datos/pdf
indice ocr                  # solo el OCR (con caché)
indice cargar               # incremental: conserva las decisiones del comité (--reconstruir la crea de nuevo)
indice reproyectar
indice exportar
indice tablero
```

`extraer` recorre la carpeta de presentaciones (con subcarpetas) y obtiene:
- el texto de cada página del PDF (si una presentación solo tiene PPTX, se convierte con PowerPoint);
- los datos de las gráficas y las celdas de las tablas de los PPTX (el PDF solo conserva la imagen de la gráfica);
- el texto dentro de imágenes, con el OCR de Windows (o tesseract). La primera vez tarda unos 10 minutos; después usa la caché. `--sin-ocr` lo omite y `indice ocr --rehacer-ocr` lo repite.

Productos en `salida/`: `diapositivas.json`, `pptx.json`, `ocr.json`, `pdf_convertidos/`, `indice_acreditacion.sqlite`, `data.json`, `csv/` y `tablas_csv.zip` (UTF-8 con BOM, para Excel o Power BI) e `indice_acreditacion_abet.html` (tablero autocontenido).

## Pruebas
```
pytest
```
`tests/test_flujo.py` corre el flujo completo en una carpeta temporal y lo compara con la base del prototipo (`legado/indice_acreditacion.sqlite`, no versionada) mediante `tests/comparar_bases.py`.

## Estructura
```
indice.toml            configuración de rutas
src/indice/            fuentes, extraer, pptx, ocr, cargar, reproyectar, exportar, tablero, cli; schema.sql; *.ps1
plantillas/            template.html del tablero
datos/semillas/        datos manuales (tarea 2, pendiente)
tests/
legado/                scripts del prototipo original, solo como referencia
salida/                productos generados (no se versiona)
```

## Consultas útiles
- Cobertura por criterio: `SELECT * FROM v_cobertura_abet;`
- Créditos por categoría: `SELECT * FROM v_creditos_abet;`
- Cifras contradictorias: `SELECT * FROM v_inconsistencias;`
