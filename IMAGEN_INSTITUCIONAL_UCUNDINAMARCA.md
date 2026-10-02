# Imagen institucional — Universidad de Cundinamarca

Guía reutilizable para aplicar la identidad visual de la UCundinamarca en portales web,
tableros, documentos (Word/PDF) y piezas digitales.

- **Fuente oficial:** *Manual de Imagen Institucional ECOM002 V18*, Oficina Asesora de
  Comunicaciones (`Manuales/ECOM002_V18.pdf`). Si este documento y el manual no coinciden,
  manda el manual.
- **Implementación de referencia:** Observatorio de Investigación
  (`observatorio_django/static/css/observatorio.css`, `static/js/tableros.js`,
  `documentacion/manuales/base.py`).
- **Recursos oficiales (texturas, fondos):**
  https://www.ucundinamarca.edu.co/documents/comunicaciones/2026/RECURSOS-MANUAL.zip

---

## 1. Identificadores (logo y escudo)

| Elemento | Cuándo se usa |
|---|---|
| **Imagotipo** (logo: sol + nombre) | **Obligatorio** en toda comunicación, publicación o promoción interna y externa. |
| Imagotipo **horizontal** | Diseños digitales y web (en digital, en su versión monocromática). |
| Imagotipo **vertical** | Piezas con poco espacio para el logo; prendas de vestir. |
| **Escudo** (isotipo) | Solo en la bandera, placas conmemorativas y elementos simbólicos; esquina superior derecha de videos horizontales. |

**Reglas:**

- **Área de seguridad:** como mínimo ¼ de la altura del escudo alrededor del identificador.
- **Tamaño mínimo del escudo:** 20 mm.
- **Proporciones:** el escudo guarda la relación 2x × 3x (x = diámetro del círculo central). Nunca se distorsiona ni se reordenan sus elementos.
- **Versiones:** policromía (a color), línea en positivo y línea en negativo (blanco).
- **Policromía solo sobre blanco.** Sobre fondos de color, fotos o texturas, usar la versión monocromática (blanca sobre verde oscuro).
- **Piezas digitales (redes):** el logo va **arriba** (izquierda, centro o derecha), solo, sin identificadores secundarios al lado. Ancho: **220 px en un lienzo de 1080 px**.
- **Identificadores secundarios** (dependencias, eventos, observatorios): siempre **abajo**, más pequeños que el logo de la Universidad, en versión horizontal y con versión monocromática. Si no tienen logo propio, se escribe el nombre en **Century Gothic Italic** (máx. 3 líneas).
- **Cobranding:** todos los logos juntos en la parte inferior, a la misma altura que el de la UCundinamarca y con este en **primer lugar**. Si son más de 4, se ponen en dos filas.
- **Usos incorrectos:** fondos de tono parecido al logo, invadir el área de seguridad, modificar los elementos internos, cambiar proporciones o posición, logo a color sobre fondos que no sean blancos, o sobre fotos o texturas de contraste irregular.

### Elementos obligatorios en piezas gráficas

```
[Imagotipo arriba a la izquierda]
...
www.ucundinamarca.edu.co   Vigilada MinEducación
```

- Toda pieza publicitaria o institucional lleva el imagotipo, el texto `www.ucundinamarca.edu.co` y, a continuación, **Vigilada MinEducación**.
- En carruseles de redes, estos elementos solo van en la primera pieza (portada).
- En video, el imagotipo va al inicio o al final durante **≥ 2 s**, con una altura de ¼ de la pantalla.

---

## 2. Paleta de color

### 2.1 Principal (identidad y acciones principales)

| Nombre (token) | Pantone | HEX | RGB | CMYK |
|---|---|---|---|---|
| Verde institucional `--verde` | 3536 C | `#007B3E` | 0 123 62 | 100 3 85 10 |
| Verde oscuro `--verde-oscuro` | 3537 C | `#00482B` | 0 72 43 | 100 14 99 65 |
| Amarillo `--amarillo` | 107 C | `#FBE122` | 251 225 34 | 5 6 89 0 |
| Dorado `--dorado` | 110 C | `#DAAA00` | 218 170 0 | 2 22 100 8 |

Se usa de forma **predominante** en documentos oficiales, señalética, presentaciones y sitios web institucionales.

### 2.2 Secundaria (apoyo visual, diferenciación de módulos, campañas)

| Nombre (token) | Pantone | HEX | RGB | CMYK |
|---|---|---|---|---|
| Verde lima `--verde-lima` | 3561 C | `#79C000` | 121 192 0 | 50 0 98 0 |
| Verde claro `--verde-claro` | 367 C | `#91C256` | 145 194 86 | 51 0 80 0 |
| Teal `--teal` | 7716 C | `#00A99D` | 0 169 157 * | 81 16 51 2 |
| Naranja `--naranja` | 144 C | `#F7931E` | 247 147 30 | 0 50 91 0 |
| Gris institucional `--gris-inst` | 425 C | `#4D4D4D` | 77 77 77 | 62 52 50 48 |

\* El manual escribe RGB 0 152 140 para el teal, pero eso no corresponde a `#00A99D`. En web se usa el HEX.

Los colores secundarios **complementan**, no compiten con los principales. Sirven para las fan pages de unidades regionales y facultades, campañas, folletos y banners. El manual (pág. 39) asigna además un color secundario por **sede, seccional o extensión** para sus campañas propias.

### 2.3 Degradados oficiales

| Degradado | Colores |
|---|---|
| Verde vital | `#79C000` → `#007B3E` *(barras y botones del portal)* |
| Verde profundo | `#00482B` → `#007B3E` → `#79C000` *(banners y héroes)* |
| Verde agua | `#79C000` → `#00A99D` / `#007B3E` → `#00A99D` |
| Sol | `#FBE122` → `#DAAA00` |
| Cálido | `#00482B` → `#DAAA00` → `#F7931E` |

### 2.4 Grises y estados (sistema de diseño web)

| Rol | Token | HEX |
|---|---|---|
| Texto principal / barras | `--negro` | `#111111` |
| Texto secundario | `--gris-texto` | `#4D4D4D` |
| Fondo alterno | `--gris-fondo` | `#F5F6F5` |
| Éxito | `--exito` | `#007B3E` |
| Error | `--error` | `#B00020` |
| Advertencia | `--advertencia` | `#DAAA00` |
| Información | `--info` | `#00A99D` |

### 2.5 Contraste (WCAG 2.1 AA: 4.5:1 en texto normal, 3:1 en texto grande e iconos)

| Color | Sobre blanco | Sobre `#111111` | Uso de texto recomendado |
|---|---|---|---|
| `#00482B` verde oscuro | **10.7** ✅ | 1.8 ❌ | Títulos y texto sobre fondo claro |
| `#007B3E` verde | **5.4** ✅ | 3.5 ⚠️ | Enlaces y botones con texto blanco |
| `#4D4D4D` gris | **8.5** ✅ | 2.2 ❌ | Texto secundario |
| `#00A99D` teal | 2.9 ❌ | **6.4** ✅ | Solo fondos o iconos grandes; texto oscuro encima |
| `#DAAA00` dorado | 2.2 ❌ | **8.8** ✅ | Franjas con texto **negro** encima |
| `#FBE122` amarillo | 1.3 ❌ | **14.3** ✅ | Fondos de aviso con texto negro |
| `#79C000` lima | 2.3 ❌ | **8.4** ✅ | Decoración, foco y hover; nunca texto sobre blanco |
| `#F7931E` naranja | 2.3 ❌ | **8.2** ✅ | Acentos; texto oscuro encima |

> En la práctica: **sobre blanco, el texto va en verde oscuro, verde o gris. Sobre amarillo,
> dorado, lima o naranja, el texto va en negro. Sobre verde o verde oscuro, el texto va en blanco.**

---

## 3. Tipografía

| Familia | Uso | Respaldo web |
|---|---|---|
| **Montserrat** | Texto de interfaz web y lectura en pantalla | `"Montserrat", "Century Gothic", "Segoe UI", Arial, sans-serif` |
| **Century Gothic** | Títulos, cifras destacadas, pie de página, identificadores secundarios (Italic) | `"Century Gothic", "Montserrat", sans-serif` |
| **Times New Roman** | Documentos formales e impresos tradicionales | `"Times New Roman", Georgia, serif` |

- Jerarquía: H1 / H2 / H3 → texto base → etiquetas y metadatos. Tamaños, pesos e interlineado iguales en todos los módulos.
- Web: el portal usa interlineado de 1.55 en el texto base, títulos de sección de 2rem y H1 del héroe de 2.6rem.
- Documentos Word (manuales del Observatorio): Calibri 11 pt, H1 16 pt `#00482B`, H2 13 pt `#007B3E`. Para documentos oficiales nuevos se prefiere Century Gothic o Montserrat si están instaladas.
- Montserrat se puede servir localmente (licencia OFL). Century Gothic es comercial: no la incluya en el repositorio; declárela solo como fuente de respaldo.

---

## 4. Lineamientos web obligatorios

1. **WCAG 2.1 nivel AA** (Resolución MinTIC 1519 de 2020): contraste ≥ 4.5:1 en texto y ≥ 3:1 frente a colores adyacentes.
2. **Estructura de toda web institucional:**
   - **Header:** barra de redes sociales (y radio) → barra principal con el imagotipo (que **siempre enlaza a** `https://www.ucundinamarca.edu.co`) y el menú → barra secundaria de servicios. No se modifica su color ni su forma.
   - **Body:** zona editable.
   - **Footer institucional:** desde las certificaciones hasta el régimen legal. Va siempre y no se modifica.
3. **Grilla:** unidad base de **8 px**; espaciados de 8, 16, 24, 32, 48 y 64; 12 columnas en escritorio, 8 en tablet y 4 en móvil.
4. **Banners web:** 1500 × 500 px, frase corta y un texto que diga a dónde lleva el clic (no solo «ver más»). Los botones del banner son totalmente redondeados, con texto corto en *cursiva*.
5. **Sin ventanas emergentes** (pop-ups prohibidos).
6. Idioma `es` (español latinoamericano): `<html lang="es">`.
7. **Texto alternativo** en todas las imágenes; evitar infografías que no puedan describirse.
8. Animaciones, videos y audio con **controles visibles** (pausar, reiniciar, avanzar). Respetar `prefers-reduced-motion`.
9. **Lenguaje claro** (programa del DNP): explicar las siglas y evitar tecnicismos.
10. **Documentos publicados en PDF legible** (texto, no escaneado).
11. Peso liviano: páginas e imágenes optimizadas para zonas con poca cobertura.
12. Iconografía de un único sistema, funcional y de tamaños estándar.

---

## 5. Fotografía e imagen

- Resolución mínima de **1920 × 1080** en digital y **300 dpi** en impreso. Nada borroso, pixelado ni mal expuesto.
- Mostrar **Cundinamarca**: paisajes, arquitectura y comunidad real. Evitar bancos de imágenes con entornos extranjeros.
- Preferir tomas naturales de estudiantes, docentes y administrativos, con diversidad.
- Contar con **derechos de uso** y con la **autorización de tratamiento de datos** de quienes aparecen.
- Retratos de funcionarios: plano corto y sin objetos delante del rostro.

### Medidas frecuentes

| Destino | Medida |
|---|---|
| Banner web | 1500 × 500 px |
| Post cuadrado (Instagram/Facebook) | 1080 × 1080 px |
| Historia / Reel / TikTok | 1080 × 1920 px |
| Post horizontal | 1920 × 1080 px |
| Portada de Facebook | 820 × 315 px |
| Cabecera de LinkedIn | 1128 × 191 px |
| Imagen de link de LinkedIn | 1200 × 628 px |
| Cabecera de YouTube | 2560 × 1440 px (zona segura 2560 × 423) |
| Miniatura de video | 1280 × 720 px (título ≤ 40 caracteres) |

---

## 6. Canales oficiales

| Canal | Enlace |
|---|---|
| Web | https://www.ucundinamarca.edu.co/ |
| Facebook | https://www.facebook.com/ucundinamarcaoficial/ |
| Instagram | https://www.instagram.com/ucundinamarcaoficial/ |
| X | https://x.com/UCundinamarca |
| YouTube | UCUNDINAMARCA TV |
| TikTok | https://www.tiktok.com/@ucundinamarca_oficial |
| LinkedIn | https://www.linkedin.com/school/ucundinamarcaoficial/ |
| Radio | https://stream.zeno.fm/whsrutbb8cstv |

---

## 7. Código listo para reutilizar

### 7.1 Tokens CSS

```css
:root {
  /* Principal — ECOM002 V18 */
  --verde: #007B3E;          /* PANTONE 3536 C */
  --verde-oscuro: #00482B;   /* PANTONE 3537 C */
  --amarillo: #FBE122;       /* PANTONE 107 C  */
  --dorado: #DAAA00;         /* PANTONE 110 C  */
  /* Secundaria */
  --verde-lima: #79C000;     /* PANTONE 3561 C */
  --verde-claro: #91C256;    /* PANTONE 367 C  */
  --teal: #00A99D;           /* PANTONE 7716 C */
  --naranja: #F7931E;        /* PANTONE 144 C  */
  --gris-inst: #4D4D4D;      /* PANTONE 425 C  */
  /* Grises y estados */
  --negro: #111111;
  --gris-texto: #4D4D4D;
  --gris-fondo: #F5F6F5;
  --blanco: #FFFFFF;
  --exito: #007B3E;
  --error: #B00020;
  --advertencia: #DAAA00;
  --info: #00A99D;
  /* Degradados */
  --grad-vital: linear-gradient(180deg, #79C000 0%, #007B3E 100%);
  --grad-heroe: linear-gradient(105deg, #00482B 0%, #007B3E 55%, #79C000 100%);
  /* Sistema */
  --esp: 8px;                /* unidad base de la grilla */
  --radio: 10px;
  --sombra: 0 2px 10px rgba(0, 0, 0, .08);
  --fuente-texto: "Montserrat", "Century Gothic", "Segoe UI", Arial, sans-serif;
  --fuente-titulos: "Century Gothic", "Montserrat", sans-serif;
}

body { font-family: var(--fuente-texto); color: var(--negro); background: var(--blanco); line-height: 1.55; }
h1, h2, h3 { font-family: var(--fuente-titulos); color: var(--verde-oscuro); }
a { color: var(--verde); }
a:hover { color: var(--verde-oscuro); }
:focus-visible { outline: 3px solid var(--verde-lima); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
```

### 7.2 Componentes base (patrón del Observatorio)

```css
/* Barra superior negra con redes y sesión */
.barra-superior { background: var(--negro); color: var(--blanco); height: 44px; font-size: .85rem; }
.barra-superior a:hover { color: var(--verde-lima); }

/* Encabezado blanco con franja degradada inferior de 12px */
.encabezado { background: var(--blanco); position: relative; padding-bottom: 12px; }
.encabezado::after { content: ""; position: absolute; inset: auto 0 0 0; height: 12px; background: var(--grad-vital); }
.navegacion a.activo { color: var(--verde-oscuro); font-weight: 700; border-bottom: 2px solid var(--verde-oscuro); }

/* Botones */
.btn { background: var(--verde); color: var(--blanco); padding: 12px 32px; border: 0; border-radius: 6px; font-weight: 700; }
.btn:hover { background: var(--verde-oscuro); }
.btn-secundario { background: var(--blanco); color: var(--verde); border: 1px solid var(--verde); border-radius: 6px; }
.btn-secundario:hover { background: var(--verde); color: var(--blanco); }
.btn-banner { border-radius: 999px; font-style: italic; }   /* botones de banner: redondeados y en cursiva */

/* Franja de cifras (dorado con texto negro) */
.franja-cifras { background: var(--dorado); color: #1B1B1B; }

/* Avisos */
.aviso       { background: #FDF8E6; border-left: 4px solid var(--dorado); }
.informacion { background: #EEF6FB; border-left: 4px solid #1F6FA0; }

/* Pie negro */
.pie { background: var(--negro); color: #D5D5D5; }
.pie h4 { font-family: var(--fuente-titulos); color: var(--blanco); font-weight: 400; }
.pie a:hover { color: var(--verde-lima); }

/* Tarjeta / KPI */
.tarjeta { background: var(--blanco); border-radius: var(--radio); box-shadow: var(--sombra); padding: calc(var(--esp) * 3); }
.kpi-valor { font-size: 1.6rem; font-weight: 800; color: var(--verde-oscuro); }
```

### 7.3 Paleta para gráficos (ECharts, Chart.js, matplotlib)

Es una secuencia sobria derivada de la paleta: los verdes primero y el dorado como acento.

```js
const PALETA_UDEC = ['#00482B', '#2E6B4F', '#6E9C85', '#A9C7B8', '#D5E3DC',
                     '#DAAA00', '#E9C94A', '#8C7A1E', '#4D4D4D', '#007B3E'];
const ESCALA_VERDE = ['#F1F6F3', '#A9C7B8', '#2E6B4F', '#00482B'];   // mapas de calor
```

```python
PALETA_UDEC = ["#00482B", "#2E6B4F", "#6E9C85", "#A9C7B8", "#D5E3DC",
               "#DAAA00", "#E9C94A", "#8C7A1E", "#4D4D4D", "#007B3E"]
# matplotlib: plt.rcParams["axes.prop_cycle"] = plt.cycler(color=PALETA_UDEC)
```

### 7.4 Documentos Word / PDF (python-docx, reportlab)

```python
from docx.shared import RGBColor
VERDE_OSC = RGBColor(0x00, 0x48, 0x2B)   # títulos H1, encabezado de tablas
VERDE     = RGBColor(0x00, 0x7B, 0x3E)   # subtítulos H2
GRIS      = RGBColor(0x4D, 0x4D, 0x4D)   # encabezado y pie de página
# Tablas: fila de encabezado en #00482B con texto blanco; filas alternas en #F1F6F3
# Cajas: nota #EEF6FB con borde #1F6FA0; aviso #FDF8E6 con borde #DAAA00
```

Ejemplo completo: `documentacion/manuales/base.py` (portada con logo, encabezado, número de página, tablas, código y figuras).

### 7.5 Tema para Excel (openpyxl)

```python
from openpyxl.styles import Font, PatternFill
ENCABEZADO = PatternFill("solid", fgColor="00482B")
FUENTE_ENC = Font(bold=True, color="FFFFFF")
FILA_ALTERNA = PatternFill("solid", fgColor="F1F6F3")
```

---

## 8. Lista de verificación antes de publicar

- [ ] El imagotipo es el oficial, sin deformar, con su área de seguridad y enlazado a ucundinamarca.edu.co (en la web).
- [ ] Logo a color solo sobre blanco; sobre color va la versión blanca.
- [ ] Los identificadores secundarios van abajo y más pequeños que el logo de la Universidad.
- [ ] Incluye `www.ucundinamarca.edu.co` + **Vigilada MinEducación** (piezas gráficas).
- [ ] Usa la paleta principal de forma predominante; la secundaria solo como apoyo.
- [ ] Contraste AA comprobado (sección 2.5).
- [ ] Tipografía Montserrat / Century Gothic (o Times New Roman en impresos formales).
- [ ] Imágenes ≥ 1920 × 1080 (digital) / 300 dpi (impreso), con derechos y autorizaciones.
- [ ] Web: `lang="es"`, textos alternativos, sin pop-ups, controles en multimedia, PDF accesibles.
- [ ] Ante cualquier duda, consultar a la **Oficina Asesora de Comunicaciones**.
