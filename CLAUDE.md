# Índice de acreditación CNA → ABET · Ingeniería Agronómica (UCundinamarca)

Documento de contexto para Claude Code. Colócalo en la raíz del repositorio como `CLAUDE.md`.

## Contexto

El programa de Ingeniería Agronómica de la Universidad de Cundinamarca (sede Fusagasugá y ampliación de lugar de desarrollo Facatativá) tiene su autoevaluación de alta calidad ante el CNA (Colombia) en 12 presentaciones, una por factor. El objetivo es proyectar el programa hacia la acreditación internacional ABET (Engineering Accreditation Commission, EAC).

Este proyecto indexa toda la evidencia CNA en una base relacional donde los factores son una dimensión más, no la estructura. La unidad básica es la **evidencia** (hoy, cada diapositiva). Cada evidencia se etiqueta con nodos de uno o varios marcos (CNA, ABET, REA del programa), y una tabla de **correspondencias** entre marcos permite reproyectarla automáticamente hacia ABET o cualquier marco futuro.

Idioma del proyecto: español (código, comentarios, datos e interfaz). Los textos de los criterios ABET están parafraseados en español y no deben copiarse literalmente del documento oficial.

## Estado actual (paquete `indice`, tarea 1 terminada)

- Base generada en `salida/indice_acreditacion.sqlite`:
  - 240 evidencias con 492 etiquetas (245 extraídas + 247 inferidas).
  - 3 marcos: CNA con 60 nodos, ABET-EAC con 24 nodos, REA-IA con 5 nodos.
  - 224 mediciones, 54 cursos (150 créditos), 35 normas y 14 brechas.
- `src/indice/schema.sql`: 13 tablas y 3 vistas.
- `src/indice/extraer.py`: extrae el texto por página con `pdftotext` (respaldo: pypdf, que altera el texto) y detecta el encabezado "Característica N.". Escribe `salida/diapositivas.json`.
- `src/indice/cargar.py`: borra y recrea la base; carga marcos, nodos, correspondencias, evidencias, normativa (por regex), indicadores, cursos y brechas. Los datos manuales siguen escritos aquí (tarea 2).
- `src/indice/reproyectar.py`: etiquetas extraídas → etiquetas ABET inferidas vía correspondencias. Idempotente.
- `src/indice/exportar.py`: `data.json` y `csv/` + `tablas_csv.zip` (UTF-8 con BOM).
- `src/indice/tablero.py` y `plantillas/template.html`: tablero autocontenido; inyecta `data.json` en `__DATA__`, JavaScript puro, sin dependencias.
- `indice.toml`: rutas (`pdf`, `salida`, `poppler` opcional). Hoy `pdf` apunta a `OneDrive_1_9-23-2026/`.
- `legado/`: scripts del prototipo y su base (no versionada) para comparar. `tests/comparar_bases.py` compara dos bases por claves naturales.

Flujo: `pip install -e .[dev]` y luego `indice todo` (o `extraer`, `cargar`, `reproyectar`, `exportar`, `tablero`). Pruebas: `pytest`.

Requisitos: Python 3.11 o superior (usa `tomllib`) y poppler (`pdftotext`, `pdfinfo`). En este equipo: poppler portable 26.09 en `%LOCALAPPDATA%\Programs\poppler\...\Library\bin`, MinGit en `%LOCALAPPDATA%\Programs\MinGit\cmd` (ambos en el PATH de usuario) y el intérprete es `py -3.14`; ojo: `python` en el PATH es el de Inkscape.

Diferencia conocida con la base del prototipo: poppler 26.09 corta distinto las líneas en F05-P016, F07-P020 y F11-P006; por eso el `fuente` de F07-P020 pasó de "Dirección" a "Dirección de". El resto es idéntico. `evidencia.archivo` guarda ahora el nombre real del PDF ("Factor 1. PEP e Identidad Institucional.pdf").

## Modelo de datos

| Tabla | Propósito |
|---|---|
| `marco` | Sistemas de acreditación o referencia: `CNA`, `ABET-EAC`, `REA-IA` |
| `nodo` | Jerarquía de cada marco (`padre_id`). Tipos: factor, caracteristica, criterio, subcriterio, outcome, rea |
| `correspondencia` | Nodo origen → nodo destino entre marcos. `tipo`: equivalente, parcial o apoyo. `estado`: propuesta, validada o descartada |
| `evidencia` | Unidad básica: código `Fxx-Pyyy`, título, tipo (diapositiva, valoracion, logros, plan_mejora), texto, fuente, archivo, página, sede, `url_sharepoint` |
| `evidencia_nodo` | Etiquetas. `rol`: principal, parcial o apoyo. `origen`: extraccion, inferida o manual. `estado` |
| `indicador`, `medicion`, `indicador_nodo` | Series por periodo, sede y `desagregacion` (por ejemplo `C01` para las valoraciones CNA) |
| `curso`, `curso_outcome` | Plan de estudios con `categoria_abet` y `confianza`; aporte I/R/E a cada Student Outcome (tabla aún vacía) |
| `normativa`, `normativa_mencion` | Acuerdos y resoluciones citados y en qué evidencias aparecen |
| `brecha` | Brechas por nodo ABET con severidad, acción, responsable y estado |

Vistas: `v_cobertura_abet`, `v_creditos_abet`, `v_inconsistencias` (misma medición, periodo, sede y desagregación con valores distintos).

Reglas de reproyección: una etiqueta CNA de tipo `extraccion` genera etiquetas ABET `inferida` y `propuesta`. El rol se traduce así: equivalente → principal, parcial → parcial, apoyo → apoyo. Solo cuenta para cobertura lo que no esté `descartada`. Nunca marques una etiqueta como `validada` desde código; eso lo decide el comité.

## Hallazgos del diagnóstico (no los pierdas)

- **Criterio 5.** Temas de ingeniería: 14 créditos frente a 45 exigidos. Matemáticas: 7 créditos (sin cálculo); física: 2. No hay experiencia de diseño obligatoria para todos. Es la brecha decisiva.
- **Criterio 6.** 1 docente de planta de 53. Casi nula formación en ingeniería en el área de ciencias de la ingeniería.
- **Criterios 2 y 3.** No existen PEOs. Los 5 REA no cubren SO2 (diseño), SO6 (experimentación) ni SO7 (aprendizaje autónomo).
- **Criterio 4.** El "% de alcance de REA" es una medición agregada; ABET pide evaluación directa por indicador de desempeño, con rúbricas y metas.
- **Criterio 7.** Disparidad entre sedes: 26 frente a 9 laboratorios.
- **Datos.** La graduación acumulada en S14 aparece como 44,3 % en el Factor 6 y como 34,33 % en el Factor 4. `v_inconsistencias` lo detecta.

## Deuda técnica conocida

1. ~~Rutas fijas~~ (resuelto en la tarea 1 con `indice.toml` y la CLI).
2. `cargar.py` borra y recrea la base en cada ejecución. Cualquier validación manual del comité se perdería.
3. Los indicadores, cursos, brechas, valoraciones CNA y correspondencias están escritos a mano dentro de `cargar.py`.
4. Los títulos de evidencias se derivan heurísticamente del texto de la diapositiva y algunos quedan pobres.
5. La normativa se detecta por regex; el órgano emisor puede estar mal y hay exclusiones manuales.
6. Las series de las gráficas de los PDF se transcribieron a mano. La del alcance de REA se leyó de la imagen de F05-P027: el orden de barras es 2025-2, 2025-1, 2024-2, 2024-1, 2023-2.
7. Solo hay la prueba de aceptación del flujo (`tests/test_flujo.py`); faltan las de la tarea 4.

## Tareas priorizadas

### 1. Estructura del repositorio y configuración — HECHA
Se implementó en la raíz (sin carpeta `acreditacion/`), con `argparse`, `indice.toml` para las rutas y `salida/` para los productos. Los PDF se leen desde la carpeta de OneDrive en lugar de copiarlos a `datos/pdf/`. Plan original:

Reorganiza el proyecto en paquete. Propuesta:

```
acreditacion/
  datos/pdf/              # PDF de entrada (no versionar)
  datos/semillas/         # CSV/YAML: marcos, nodos, correspondencias, cursos, brechas, indicadores manuales
  src/indice/             # extraer.py, cargar.py, reproyectar.py, exportar.py, tablero.py
  plantillas/template.html
  salida/                 # sqlite, csv, html (no versionar)
  tests/
```

Usa una CLI con `argparse` o `typer`: `indice extraer --pdf datos/pdf`, `indice cargar`, `indice reproyectar`, `indice exportar`, `indice tablero`.

**Criterio de aceptación:** el flujo completo corre desde una carpeta limpia con un solo comando.

### 2. Sacar los datos manuales a semillas
Mueve a `datos/semillas/` todo lo que hoy está escrito a mano en `cargar.py`: nodos CNA y ABET, correspondencias, REA, cursos, brechas, indicadores y valoraciones CNA.

**Criterio de aceptación:** la base generada es idéntica a la actual (mismos conteos y mismas vistas).

### 3. Carga incremental que preserve la validación humana
Reemplaza el borrado y recreado por un *upsert* con claves naturales: `evidencia.codigo`, `(marco, nodo.codigo)` y `(origen, destino)`. Las etiquetas y correspondencias en estado `validada` o `descartada` no se tocan al recargar. Agrega columnas `creado_en`, `actualizado_en` y `validado_por` donde aplique.

### 4. Pruebas (pytest)
Como mínimo, verificar:
- 48 características y 12 factores CNA;
- la suma de créditos de `curso` es 150;
- `v_inconsistencias` detecta el caso de graduación acumulada;
- toda correspondencia une nodos de marcos distintos;
- ningún nodo ABET queda sin padre salvo los criterios;
- la reproyección es idempotente.

### 5. Flujo de validación del comité
Crea una interfaz mínima para revisar propuestas: aceptar o descartar correspondencias y etiquetas inferidas, con comentario y validador. Hay dos opciones:
- **(a)** CLI interactiva;
- **(b)** aplicación web local con FastAPI y SQLite, sin dependencias de front-end pesadas.

Empieza por (b) si es viable. Cada decisión debe quedar auditada.

### 6. Enlaces a SharePoint
Pobla `evidencia.url_sharepoint`. Las presentaciones originales están en la carpeta de OneDrive institucional `DAYA/01. ACREDITACIÓN/PROCESOS DE ACREDITACIÓN 2026/VISITAS/3. Ingeniería Agronómica, Fusagasugá ALD Facatativá/Presentaciones-Ing. Agronómica, Fusagasugá ALD Facatativá`.

Primera versión: un CSV de mapeo `archivo → URL base`, construyendo `URL#page=N` cuando aplique. Una integración con Microsoft Graph queda como tarea opcional y requiere credenciales que deben pedirse al usuario; nunca las guardes en el repositorio.

### 7. Currículo y Student Outcomes
Agrega la ingesta de los Planes de Aprendizaje Digital (PAD) de cada CADI cuando estén disponibles: contenidos, horas y resultados de aprendizaje. Con ellos:
- reclasifica `curso.categoria_abet` y sube la confianza;
- llena `curso_outcome` (I/R/E);
- agrega al tablero la matriz de cursos por Student Outcome;
- agrega columnas de periodo al plan (hoy `curso.periodo` está vacío).

### 8. Evaluación directa de Student Outcomes (Criterio 4)
Diseña tablas para indicadores de desempeño por SO, rúbricas, metas y resultados por curso, periodo y sede. Agrega también el registro de acciones de mejora ("cierre del ciclo") ligadas a brechas. Esto alimentará el Criterio 4 con datos reales.

### 9. Tablero
Mantén `template.html` autocontenido (JavaScript puro, sin fetch). Mejoras:
- filtro por sede;
- vista por factor CNA (proyección inversa);
- estado de validación visible en cada cuadro de cobertura;
- exportación de la tabla filtrada a CSV;
- conservar el modo claro y oscuro y la accesibilidad por teclado.

### 10. Esqueleto del Self-Study Report
Crea un generador que produzca, por criterio ABET, un borrador en Markdown con:
- qué pide el criterio (texto parafraseado);
- las evidencias validadas y sus fuentes;
- los indicadores con su serie;
- las brechas abiertas.

Debe generarse en español; más adelante se agregará una versión en inglés.

### 11. Opcional
- Migrar a PostgreSQL cuando haya varios usuarios validando.
- Agregar otros marcos (por ejemplo, un segundo acreditador) sin cambiar el esquema; solo semillas nuevas.

## Convenciones

- Código de evidencia: `F{factor:02d}-P{pagina:03d}`. Nodos CNA: `F01`… y `C01`…`C48`. Nodos ABET: `C1`…`C8`, `SO1`…`SO7`, `C5a`…`C5d`, `C8a`…`C8d`, `PC`.
- Sedes: `Fusagasugá`, `Facatativá` o `Programa` (agregado).
- Nunca inventes datos. Si un valor no está en los PDF o en las semillas, déjalo vacío y regístralo como pendiente.
- Respeta la privacidad: los PDF contienen datos agregados de estudiantes y docentes. No agregues datos personales identificables al repositorio.
- Mensajes de commit en español, en imperativo y breves.
