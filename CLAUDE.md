# Índice de acreditación CNA → ABET · Ingeniería Agronómica (UCundinamarca)

Documento de contexto para Claude Code. Colócalo en la raíz del repositorio como `CLAUDE.md`.

## Contexto

El programa de Ingeniería Agronómica de la Universidad de Cundinamarca (sede Fusagasugá y ampliación de lugar de desarrollo Facatativá) tiene su autoevaluación de alta calidad ante el CNA (Colombia) en 12 presentaciones, una por factor. El objetivo es proyectar el programa hacia la acreditación internacional ABET (Engineering Accreditation Commission, EAC).

Este proyecto indexa toda la evidencia CNA en una base relacional donde los factores son una dimensión más, no la estructura. La unidad básica es la **evidencia** (hoy, cada diapositiva). Cada evidencia se etiqueta con nodos de uno o varios marcos (CNA, ABET, REA del programa), y una tabla de **correspondencias** entre marcos permite reproyectarla automáticamente hacia ABET o cualquier marco futuro.

Idioma del proyecto: español (código, comentarios, datos e interfaz). Los textos de los criterios ABET están parafraseados en español y no deben copiarse literalmente del documento oficial.

## Estado actual (paquete `indice`, tareas 1 a 5 terminadas)

- Fuentes (14 presentaciones, 329 páginas): los 12 factores (PDF + PPTX) y las 2 de la sesión de inicio (`Sesión de Inicio/2. Presentación Rectoría.pptx` y `4. Facultad de Ciencias Agropecuarias.pptx`, solo PPTX).
- Base generada en `salida/indice_acreditacion.sqlite`:
  - 345 evidencias: 240 de factores (`F..`), 52 de la sesión de inicio (`S..`, sede `Institución`, sin etiquetas CNA: las debe asignar el comité) y 53 PAD (`PAD-…`). 148 tienen `texto_ocr`.
  - PAD: 53 documentos, 153 REA específicos, 158 experiencias, 508 actividades y 773 referencias bibliográficas.
  - 492 etiquetas (245 extraídas + 247 inferidas).
  - 3 marcos: CNA con 60 nodos, ABET-EAC con 24 nodos, REA-IA con 5 nodos.
  - 31 indicadores y 299 mediciones, todas ligadas a la diapositiva de donde sale el valor; 54 cursos (150 créditos), 39 normas y 14 brechas.
  - Desde las tablas de valoración: ponderación de las 48 características (`CNA_POND`), valoración y % de cumplimiento de los 12 factores (`CNA_VAL_FACTOR`, `CNA_CUMPL_FACTOR`). En cada factor las ponderaciones suman 100 % y el promedio ponderado coincide con la valoración del factor.
  - 83 gráficas (1.310 puntos) y 63 tablas de los PPTX.
- `src/indice/schema.sql` (+ `esquema_pad.sql`, migración a v3): 23 tablas y 6 vistas.
- `src/indice/fuentes.py`: inventario de presentaciones y su código (`Factor N. …` → `FNN`; `N. …` → `SNN`). Las que solo tienen PPTX se convierten a PDF con PowerPoint (`pptx_a_pdf.ps1`, automatización COM) en `salida/pdf_convertidos/`, con caché.
- `src/indice/extraer.py`: extrae el texto por página con `pdftotext` (respaldo: pypdf, que altera el texto) y detecta el encabezado "Característica N.". Escribe `salida/diapositivas.json`.
- `src/indice/pptx.py`: lee los PPTX (solo sus XML) y extrae los datos nativos de las gráficas y las celdas de las tablas → `salida/pptx.json`. Verifica que cada diapositiva visible coincida con su página del PDF. Se cargan en `grafica`, `grafica_dato` (formato largo) y `tabla_diapositiva` (celdas en JSON). Los PPTX no tienen notas del orador y sus textos alternativos son casi todos automáticos, así que no se usan.
- `src/indice/ocr.py`: renderiza cada página (pdftoppm, 150 ppp) y aplica el OCR integrado de Windows en español (`ocr_windows.ps1`; tesseract si no es Windows). Caché cruda en `salida/ocr.json` (la primera vez tarda ~10 min; se repite solo si cambia el PDF, o con `--rehacer-ocr`). Al cargar, `texto_nuevo` guarda en `evidencia.texto_ocr` solo las líneas con palabras que no estén ya en el texto del PDF, sin encabezados institucionales ni ruido. `--sin-ocr` lo omite.
- `datos/semillas/*.csv` (versionadas): todo lo que no sale de las presentaciones — `marcos`, `nodos`, `correspondencias`, `indicadores`, `indicador_nodos`, `mediciones` (con el código de evidencia de donde sale cada valor), `cursos`, `brechas`, `normativa_manual` y `normativa_excluir`. UTF-8, celda vacía = NULL, el orden de filas es el de carga.
- `src/indice/pad.py`: extrae los **Planes de Aprendizaje Digital** (`PADs/`, 53 PDF: 44 de cursos del plan y 9 de dos especializaciones) → `salida/pads.json`. Plantillas generadas desde HTML sin estructura etiquetada: V1.9 (39, filas etiqueta/valor; incluye una variante en inglés con "Nombre de la actividad" y la **variante 2026**, con actividades desglosadas por semana —"Trabajo en la semana N"—, etiqueta central "Descripción de la actividad", bloques "Fase 2 … Recursos" y "Fase 6. Recolección de datos" con el producto evaluado, peso % de cada REA, tabla de fases del MCA y URL en la bibliografía) y V2 (14, tabla ancha de actividades). Análisis geométrico sobre palabras de `pdftotext -tsv`: líneas → segmentos partidos en inicios de columna → celdas → asignación a la etiqueta o actividad cuya fila las contiene. Extrae encabezado (código, semestre, créditos, prerrequisitos), justificación, REA general y específicos, experiencias (vive una experiencia / soluciona un problema por etapas), actividades (descripción, trabajo del estudiante y del profesor, semana, duración, lugares, tipo, instrumentos de recolección, recursos), competencias Saber Pro, bibliografía y recursos externos. **El nombre del profesor líder no se extrae** (dato personal). Tablas `pad`, `pad_rea`, `pad_experiencia`, `pad_actividad`, `pad_bibliografia`, `pad_recurso` (listas como JSON) y vistas `v_pad_curso`, `v_pad_lugar`, `v_pad_instrumento` (`esquema_pad.sql`, esquema v3). Cada PAD es además una evidencia `PAD-<código>` de tipo `pad` con su texto completo. `datos/semillas/pad_curso.csv` liga cada PAD con su curso (electivas: varias opciones por curso); al cargar se llena `curso.periodo` con el semestre del PAD.
- `src/indice/maestro.py`: documento maestro RRC 2025 (PDF de Word con estructura etiquetada). Lee el árbol lógico con `pdfinfo -struct-text` (≈2 min; caché en `salida/maestro.json`), arma una evidencia por sección (`DM-4.6`…, tipo `documento_maestro`, 126) con página y sus 81 tablas (`tabla_diapositiva.leyenda`), y lee la ruta 2025, la transición y los REA por CADI (esquema v6). `indice maestro`.
- `src/indice/semillas.py`: lee las semillas, convierte tipos y valida referencias (nodos, marcos, indicadores) antes de tocar la base, con errores legibles.
- `src/indice/cargar.py`: **carga incremental**. Marcos, nodos, correspondencias y evidencias se actualizan por clave natural (`evidencia.codigo`, `(marco, nodo.codigo)`, `(origen, destino)`) y conservan su id; las evidencias que desaparecen de las fuentes quedan `obsoleta` (se excluyen de cobertura y del tablero). Normativa, indicadores, mediciones, cursos, brechas, gráficas y tablas se reconstruyen en cada carga (su verdad son semillas y presentaciones: **las brechas se editan en `brechas.csv`, no en la base**). Esquema versionado en `meta.version_esquema` (hoy 6: `esquema_pad.sql`, `esquema_pad_v4.sql`, `esquema_v5_decision.sql` y `esquema_v6_maestro.sql`). Las migraciones se aplican instrucción por instrucción y un `ALTER TABLE … ADD COLUMN` repetido se salta. De v2 en adelante se migra en sitio con `MIGRACIONES` (solo agregan tablas: no se pierde nada); una base v1 se respalda como `*.respaldo-v1.sqlite` y se crea de nuevo; `--reconstruir` fuerza esto último.
- **Decisión del comité** = fila con `validado_por` no nulo (correspondencia o etiqueta, en estado validada o descartada) o etiqueta de origen `manual`. Ni `cargar` ni `reproyectar` la modifican o borran; si las semillas la contradicen, se conserva y se avisa. `creado_en`/`actualizado_en` (UTC) solo cambian cuando cambia el contenido.
- `src/indice/decisiones.py` y `src/indice/validacion.py` (tarea 5): **interfaz web local del comité**, `indice validar [--puerto 8765] [--abrir]`, solo biblioteca estándar (`http.server`), escucha en 127.0.0.1. Páginas: resumen por criterio ABET (`v_validacion_abet`), **cursos** (los 40 del plan con PAD, las especializaciones y los que no tienen PAD, con buscador en nombres, REA, actividades, lugares, instrumentos y bibliografía; ficha de cada PAD con REA y pesos, fases del MCA, experiencias y actividades semana a semana con su detalle, bibliografía con enlaces y recursos), correspondencias, etiquetas (filtros por nodo, estado, origen y texto), evidencias (filtro "sin etiqueta ABET"), ficha de evidencia (texto, OCR, datos de gráficas, etiquetas y alta de etiquetas manuales) y auditoría. Acciones validar / descartar / reabrir por fila o en lote, con validador obligatorio (recordado en una cookie) y comentario. Cada decisión fija `validado_por`/`validado_en` y queda en la tabla `decision` (esquema v5, nunca se reconstruye). Decidir una correspondencia ejecuta la reproyección. Los formularios enviados desde otro origen se rechazan (403). El servidor no reutiliza el puerto (`allow_reuse_address = False`): en Windows SO_REUSEADDR dejaba dos instancias escuchando en el mismo puerto y respondía la vieja.
- `src/indice/reproyectar.py`: sincroniza las etiquetas inferidas (agrega, corrige el rol, retira las que ya no se deducen) desde las etiquetas de extracción y las correspondencias no descartadas; incluye la regla "plan de mejoramiento → C4 apoyo". Si varias correspondencias llegan al mismo nodo gana el rol más fuerte. Idempotente.
- `src/indice/exportar.py`: `data.json` y `csv/` + `tablas_csv.zip` (UTF-8 con BOM).
- `src/indice/tablero.py` y `plantillas/template.html`: tablero autocontenido; inyecta `data.json` en `__DATA__`, JavaScript puro, sin dependencias.
- `indice.toml`: rutas (`pdf`, `salida`, `poppler` opcional). Hoy `pdf` apunta a `OneDrive_1_9-23-2026/`.
- `legado/`: scripts del prototipo y su base (no versionada) para comparar. `tests/comparar_bases.py` compara dos bases por claves naturales.

Flujo: `pip install -e .[dev]` y luego `indice todo` (o `extraer`, `ocr`, `cargar`, `reproyectar`, `exportar`, `tablero`). Pruebas: `pytest` (reutilizan las cachés de conversión y OCR de `salida/`).

Requisitos: Python 3.11 o superior (usa `tomllib`) y poppler (`pdftotext`, `pdfinfo`, `pdftoppm`). `binario()` ignora el `pdftotext` de xpdf (el que trae Git para Windows en `/mingw64/bin`), que parte el texto distinto y cambiaba la base según el orden del PATH. Opcionales: PowerPoint (convertir PPTX sin PDF) y el OCR de Windows con el idioma es-ES (o tesseract con `spa`). En este equipo: poppler portable 26.09 en `%LOCALAPPDATA%\Programs\poppler\...\Library\bin`, MinGit en `%LOCALAPPDATA%\Programs\MinGit\cmd` (ambos en el PATH de usuario) y el intérprete es `py -3.14`; ojo: `python` en el PATH es el de Inkscape.

Diferencia conocida con la base del prototipo: poppler 26.09 corta distinto las líneas en F05-P016, F07-P020 y F11-P006; por eso el `fuente` de F07-P020 pasó de "Dirección" a "Dirección de". El resto es idéntico. `evidencia.archivo` guarda ahora el nombre real del PDF ("Factor 1. PEP e Identidad Institucional.pdf").

## Contexto del programa (documento maestro RRC 2025)

Fuente: `DOCUMENTO MAESTRO RRC ING AGRONOMICA 2025.pdf` (374 p., renovación de registro calificado, Decreto 1330 de 2019), indexado por `maestro.py`. **La portada es, por error tipográfico, la de otro programa (Ingeniería en Robótica y Automatización, 2024)**: no usarla como referencia.

- **Identidad.** Ingeniería Agronómica, título Ingeniero Agrónomo, profesional universitario, presencial; Fusagasugá y extensión Facatativá; Facultad de Ciencias Agropecuarias. Creado por Acuerdo 0014 del Consejo Superior (7 sep. 1993). 9 períodos, 150 créditos, admisión semestral de 40 estudiantes. Campo detallado: producción agrícola y ganadera.
- **Misión y visión.** Formar ingenieros agrónomos ciudadanos, emprendedores e innovadores en sistemas de producción agrícola sostenible y socioecológicos (MEDIT). Visión 2034: alta calidad, desarrollo sostenible, seguridad y soberanía alimentaria.
- **Propósitos de formación** (lo más cercano a PEOs para el Criterio 2, aunque no están formulados como logros a 3–5 años del egreso): profesionales éticos que planifican, ejecutan, evalúan y gestionan sistemas de producción agrícola sostenibles; investigación e innovación tecnológica; emprendimiento en agronegocios y agroturismo ecológico.
- **Perfiles.** Profesional: diseñar, gestionar y transformar sistemas productivos agrícolas con tecnologías emergentes. Ocupacional: diseña sistemas sostenibles; aplica técnicas y tecnologías en proyectos productivos; evalúa impacto social, económico y ambiental. Perfiles de egreso P1–P3 ligados a los REA.
- **Resultados de aprendizaje del programa (2025): 3 REA**, cargados como marco `REA-IA-2025` (el marco `REA-IA` conserva los 5 REA de 2019; los indicadores `ALC_REA1–5` miden esos cinco): REA 1 *Diseñar* sistemas productivos agrícolas sostenibles…; REA 2 *Aplicar* tecnología agronómica con criterios éticos y de responsabilidad social…; REA 3 *Formular* alternativas tecnológicas con criterios científicos… Correspondencias propuestas hacia SO (pendientes del comité): REA1→SO2 parcial y SO1 apoyo; REA2→SO4 parcial; REA3→SO1 parcial y SO6 apoyo. Con la ruta 2025 existe por primera vez un REA de programa sobre diseño (parcial para SO2: no explicita proceso de diseño de ingeniería).
- **Ruta de aprendizaje 2025 (propuesta).** Tabla `plan_2025` (70 filas, 150 créditos: 123 disciplinares y 27 institucionales; 17–18 créditos por período y 9 en el noveno). Cambios frente a la ruta 2020 (`transicion_2025`, 34 filas: 24 homologaciones y 7 con curso complementario): Matemática aplicada → Matemática Agrícola I y II; Modelos estadísticos → Bioestadística + Diseño de experimentos y modelación; Hidráulica, riegos y drenajes → Hidráulica + Riegos y drenajes; Topografía → Topografía y SIG; Geología y pedología → Suelos I; nuevos: Gestión integral de proyectos sostenibles, Producción e innovación agrícola, Innovación en poscosecha y logística. Profundización en dos líneas (Agronegocios; Agroecología y desarrollo ecoturístico, 10 créditos, VI–IX), que se articulan con las especializaciones de la Facultad (sus PAD están en `PADs/`). REA por CADI en `plan_2025_rea` (38 CADI). La base `curso` sigue siendo la **ruta 2020 vigente** (la de la autoevaluación CNA).
- **Inconsistencias internas del documento** (`v_plan_2025_inconsistencias`, se avisan al cargar): Ecología y recursos naturales 3 créditos con 96 h; Diseño de experimentos 3 créditos en la ruta y 2 en la distribución de CADI; Profundización IIA, IVA y IVB con horas que no corresponden a sus créditos (IVB: 480 h para 4 créditos).
- **Opciones de grado** (Acuerdo 012 de 2024): monografía o artículo, ruta de emprendimiento, título de especialización, pasantía, obra de creación. Sigue sin haber una experiencia de diseño obligatoria para todos (C5d).
- **Profesores y espacios.** Tablas de profesores por sede (8.1.1) y de laboratorios con número de equipos (9.3.3, Tabla 71) disponibles en `tabla_diapositiva` (leyenda 'Tabla 47', 'Tabla 48', 'Tabla 71'). Contienen nombres de profesores: la base es local y no se versiona.

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
- **Criterio 5 (PAD).** 40 de los 54 cursos tienen PAD; solo faltan los 14 institucionales. Los PAD de Matemática aplicada (CFC1002020201) y Modelos estadísticos aplicados (CFC1002020302) son cursos de **formación común** con Zootecnia (el PDF figura en ese programa), adaptados al contexto agropecuario (sistemas agroambientales, agrícolas y pecuarios); el de Hidráulica, riegos y drenajes es propio del programa. Los créditos de todos los PAD coinciden con el plan. Créditos por semestre (cursos con PAD): 16, 12, 13, 14, 16, 12, 13, 16, 11. Estos tres PAD usan la variante 2026 y declaran el peso de cada REA (Hidráulica 32/36/32 %, Matemática 40/30/30 %, Modelos 30/20/50 %).
- **Datos.** La graduación acumulada del programa difiere entre factores en los tres semestres: Factor 6 = 32,9 / 39,4 / 44,3 % y Factor 4 = 18,71 / 27,45 / 34,33 % (S12 / S13 / S14). La media nacional NBC coincide en ambos (25,1 / 28,1 / 31,1 %). `v_inconsistencias` lo detecta. El prototipo tomaba 27,45 % como media NBC en S14; la gráfica del PPTX muestra que es el programa en S13 (corregido).

## Documentos pendientes de conseguir

- **PAD de Modelos estadísticos aplicados adaptado al contexto agrícola.** Existe, pero no se tiene; el PDF actual (`PADs/Modelos CFC1002020302.pdf`) es la versión con ejemplos pecuarios. Trae el mismo código (CFC1002020302): cuando llegue, reemplazar el PDF, correr `indice todo` y quitar de `pad_curso.csv` la nota sobre la versión pecuaria.

## Deuda técnica conocida

1. ~~Rutas fijas~~ (resuelto en la tarea 1 con `indice.toml` y la CLI).
2. ~~La carga borraba la base~~ (resuelto en la tarea 3: carga incremental). Pendiente: si el comité corrige títulos o textos de evidencias en la base, la siguiente carga los sobrescribe; hace falta un campo propio (p. ej. `titulo_revisado`) o hacerlo en semillas.
3. ~~Datos escritos a mano en el código~~ (resuelto en la tarea 2: `datos/semillas/`).
4. Los títulos de evidencias se derivan heurísticamente del texto de la diapositiva y algunos quedan pobres (sobre todo en la sesión de inicio, donde se usan la sección y la primera línea útil o del OCR).
4b. El `texto_ocr` tiene algo de ruido de fotos y logos; sirve para búsqueda, no como cita textual.
5. La normativa se detecta por regex; el órgano emisor puede estar mal y hay exclusiones manuales. Se descarta "de acuerdo con/a/al…" (falsos positivos como el Decreto 1330 leído como Acuerdo).
6. Vínculos corregidos respecto al prototipo: retención y deserción no tenían evidencia (la búsqueda usaba un espacio que no existe) → F06-P004; las series de Facatativá de inscritos, admitidos y primer curso apuntaban a F06-P015 (Fusagasugá) → F06-P016. Las series de los indicadores se transcribieron a mano. Ya se pueden contrastar con `grafica_dato`: la de alcance de REA (F05-P027), retención y deserción, graduados, inscritos, admitidos y primer curso coinciden; las 48 valoraciones CNA coinciden con las tablas de valoración de cada factor. En la tarea 2, los indicadores deben apuntar a la serie de la gráfica en vez de repetir los números.
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

### 2. Sacar los datos manuales a semillas — HECHA
Semillas en CSV (sin dependencias; YAML habría requerido PyYAML). La base generada es idéntica a la anterior, incluso en los ids internos. Plan original:

Mueve a `datos/semillas/` todo lo que hoy está escrito a mano en `cargar.py`: nodos CNA y ABET, correspondencias, REA, cursos, brechas, indicadores y valoraciones CNA.

**Criterio de aceptación:** la base generada es idéntica a la actual (mismos conteos y mismas vistas).

Datos que ya están en las tablas del PPTX y aún no en la base: la ponderación (%) de cada característica y la valoración y el grado de cumplimiento de cada factor (tablas de 7 columnas en las diapositivas de valoración). Sirven como semilla verificable en lugar de valores escritos a mano.

### 3. Carga incremental que preserve la validación humana — HECHA
Pruebas en `tests/test_incremental.py`: idempotencia, decisiones del comité que sobreviven a una recarga, diapositiva retirada y restaurada, cambio en semillas frente a una decisión y migración desde la base del prototipo. Plan original:

Reemplaza el borrado y recreado por un *upsert* con claves naturales: `evidencia.codigo`, `(marco, nodo.codigo)` y `(origen, destino)`. Las etiquetas y correspondencias en estado `validada` o `descartada` no se tocan al recargar. Agrega columnas `creado_en`, `actualizado_en` y `validado_por` donde aplique.

### 4. Pruebas (pytest) — CUBIERTA
Todos los puntos están cubiertos en `tests/` (semillas: 48 características, 12 factores, 150 créditos, correspondencias entre marcos distintos, nodos ABET con padre; flujo: `v_inconsistencias`; incremental: idempotencia de la reproyección). 24 pruebas. Lista original:
Como mínimo, verificar:
- 48 características y 12 factores CNA;
- la suma de créditos de `curso` es 150;
- `v_inconsistencias` detecta el caso de graduación acumulada;
- toda correspondencia une nodos de marcos distintos;
- ningún nodo ABET queda sin padre salvo los criterios;
- la reproyección es idempotente.

### 5. Flujo de validación del comité — HECHA (opción b con biblioteca estándar, sin FastAPI)
Ver `validacion.py`. Plan original:
Crea una interfaz mínima para revisar propuestas: aceptar o descartar correspondencias y etiquetas inferidas, con comentario y validador. Hay dos opciones:
- **(a)** CLI interactiva;
- **(b)** aplicación web local con FastAPI y SQLite, sin dependencias de front-end pesadas.

Empieza por (b) si es viable. Cada decisión debe quedar auditada.

### 6. Enlaces a SharePoint
Pobla `evidencia.url_sharepoint`. Las presentaciones originales están en la carpeta de OneDrive institucional `DAYA/01. ACREDITACIÓN/PROCESOS DE ACREDITACIÓN 2026/VISITAS/3. Ingeniería Agronómica, Fusagasugá ALD Facatativá/Presentaciones-Ing. Agronómica, Fusagasugá ALD Facatativá`.

Primera versión: un CSV de mapeo `archivo → URL base`, construyendo `URL#page=N` cuando aplique. Una integración con Microsoft Graph queda como tarea opcional y requiere credenciales que deben pedirse al usuario; nunca las guardes en el repositorio.

### 7. Currículo y Student Outcomes — EN CURSO
Hecho: ingesta de los PAD (contenidos, actividades, REA, semanas; los PAD no traen horas) y columna de periodo del plan. Pendiente: reclasificar `curso.categoria_abet`, llenar `curso_outcome` (I/R/E) y la matriz en el tablero. Plan original:
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

- Código de evidencia: `F{factor:02d}-P{pagina:03d}` para factores y `S{n:02d}-P{pagina:03d}` para otras presentaciones ("N. Nombre.pptx", p. ej. sesión de inicio). Nodos CNA: `F01`… y `C01`…`C48`. Nodos ABET: `C1`…`C8`, `SO1`…`SO7`, `C5a`…`C5d`, `C8a`…`C8d`, `PC`.
- Sedes: `Fusagasugá`, `Facatativá`, `Programa` (agregado) o `Institución` (datos de toda la universidad o la facultad, de la sesión de inicio).
- Nunca inventes datos. Si un valor no está en los PDF o en las semillas, déjalo vacío y regístralo como pendiente.
- Respeta la privacidad: los PDF contienen datos agregados de estudiantes y docentes. No agregues datos personales identificables al repositorio.
- Mensajes de commit en español, en imperativo y breves.
