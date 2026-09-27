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
indice pads                 # solo los Planes de Aprendizaje Digital (PADs/)
indice cargar               # incremental: conserva las decisiones del comité (--reconstruir la crea de nuevo)
indice reproyectar
indice exportar
indice tablero
indice maestro              # solo los documentos maestros declarados en datos/semillas/documentos.csv
indice anexos               # solo los anexos (ANEXOS/, con OCR de los escaneados)
indice outcomes             # propone la matriz cursos × Student Outcomes en datos/semillas/curso_outcomes.csv
indice compartir            # versión sin datos personales en salida/compartir/ (también la genera `indice todo`)
indice validar --abrir      # interfaz web local del comité (http://127.0.0.1:8765)
```

## Compartir y trabajar en equipo
Siempre hay dos versiones de los productos:

| Carpeta | Contenido | Para quién |
|---|---|---|
| `salida/` | **Versión completa**: todos los textos, tablas y nombres | quien mantiene el índice y el comité, dentro de la universidad |
| `salida/compartir/` | **Versión para compartir**: sin correos, sin el profesor líder de los PAD y sin los listados de personas de `datos/semillas/privacidad.csv` (sus textos y tablas se reemplazan por un aviso) | pares, directivos y cualquiera fuera del comité |

En cada carpeta, `indice_acreditacion_abet.html` es el tablero: un solo archivo que se abre con doble clic, sin instalar nada. `tablas_csv.zip` trae las 27 tablas para Excel o Power BI. El tablero compartido lo indica en su encabezado. Para omitir más evidencias en la versión compartida, agrega una fila a `privacidad.csv` (expresión regular sobre el código de la evidencia y el motivo).

Para que otras personas **trabajen** sobre el índice:
- **Sin instalar nada:** comparte `datos/semillas/` en una carpeta de OneDrive. El comité edita los CSV (sobre todo `curso_outcomes.csv`: `estado` validada o descartada y `validado_por`; también `brechas.csv`, `correspondencias.csv`, `documento_nodos.csv`) y quien mantiene el índice corre `indice todo` y vuelve a publicar los tableros. Si se editan en Excel, deben guardarse como «CSV UTF-8».
- **Con el código:** clona el repositorio privado, `pip install -e .[dev]`, copia las fuentes (presentaciones, `PADs/`, documentos maestros, `ANEXOS/`, `plan-estudios-agronomica-v4.pdf`) desde la carpeta institucional y corre `indice todo`. Las fuentes y `salida/` no se versionan: contienen datos institucionales y personales.

`extraer` recorre la carpeta de presentaciones (con subcarpetas) y obtiene:
- el texto de cada página del PDF (si una presentación solo tiene PPTX, se convierte con PowerPoint);
- los datos de las gráficas y las celdas de las tablas de los PPTX (el PDF solo conserva la imagen de la gráfica);
- los Planes de Aprendizaje Digital de la carpeta `PADs/` (REA, experiencias, actividades, bibliografía), ligados a cada curso por `datos/semillas/pad_curso.csv`;
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
src/indice/            fuentes, extraer, pptx, ocr, pad, semillas, cargar, reproyectar, exportar, tablero, cli; *.sql; *.ps1
plantillas/            template.html del tablero
datos/semillas/        datos que no salen de los documentos (CSV versionados)
PADs/                  Planes de Aprendizaje Digital en PDF (no se versionan)
tests/
legado/                scripts del prototipo original, solo como referencia
salida/                productos generados (no se versiona)
```

## Consultas útiles
- Cobertura por criterio: `SELECT * FROM v_cobertura_abet;`
- Créditos por categoría: `SELECT * FROM v_creditos_abet;`
- Cifras contradictorias: `SELECT * FROM v_inconsistencias;`
