# Índice de acreditación CNA → ABET (Ingeniería Agronómica)

## Archivos
- `indice_acreditacion.sqlite`: base completa (abrir con DB Browser for SQLite, DBeaver o Python).
- `schema.sql`: estructura de tablas y vistas.
- `tablas_csv.zip`: una tabla por CSV (UTF-8 con BOM) para Excel o Power BI.
- `extract.py`, `build_db.py`, `export.py`: scripts que reconstruyen todo desde los PDF.

## Cómo reconstruir
1. Poner los PDF de los factores en una carpeta y ajustar la ruta en `extract.py`.
2. `python3 extract.py && python3 build_db.py && python3 export.py`
Requiere `pdftotext`/`pdfinfo` (poppler) y Python 3.

## Tareas del comité
- Validar las correspondencias (`correspondencia.estado`: propuesta → validada o descartada).
- Revisar las etiquetas inferidas (`evidencia_nodo.origen = 'inferida'`).
- Completar `evidencia.url_sharepoint` con el enlace de cada archivo.
- Validar `curso.categoria_abet` con los PAD y llenar `curso_outcome` (I/R/E por Student Outcome).
- Actualizar `brecha.estado` y responsables.

## Consultas útiles
- Cobertura por criterio: `SELECT * FROM v_cobertura_abet;`
- Créditos por categoría: `SELECT * FROM v_creditos_abet;`
- Cifras contradictorias: `SELECT * FROM v_inconsistencias;`
