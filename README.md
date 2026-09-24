# Índice de acreditación CNA → ABET (Ingeniería Agronómica)

Indexa la evidencia de la autoevaluación CNA en una base SQLite y la reproyecta hacia ABET-EAC. El contexto completo y el plan de trabajo están en [CLAUDE.md](CLAUDE.md).

## Requisitos
- Python 3.11 o superior.
- poppler (`pdftotext`, `pdfinfo`) en el PATH, o su carpeta en `indice.toml` (`poppler = ...`) o en la variable `INDICE_POPPLER`. En Windows sirve la versión portable de <https://github.com/oschwartz10612/poppler-windows>.
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
indice cargar
indice reproyectar
indice exportar
indice tablero
```

Productos en `salida/`: `diapositivas.json`, `indice_acreditacion.sqlite`, `data.json`, `csv/` y `tablas_csv.zip` (UTF-8 con BOM, para Excel o Power BI) e `indice_acreditacion_abet.html` (tablero autocontenido).

## Pruebas
```
pytest
```
`tests/test_flujo.py` corre el flujo completo en una carpeta temporal y lo compara con la base del prototipo (`legado/indice_acreditacion.sqlite`, no versionada) mediante `tests/comparar_bases.py`.

## Estructura
```
indice.toml            configuración de rutas
src/indice/            extraer, cargar, reproyectar, exportar, tablero, cli; schema.sql
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
