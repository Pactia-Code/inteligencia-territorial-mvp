# Design System — Inteligencia Territorial (MVP)

**Ámbito.** Este sistema describe **una sola superficie**: el aplicativo web (M9), que las siete gerencias abren con un enlace para leer el informe del ciclo y calificar.

No hay correo de alerta ni canal de notificación (decisión del 2026-09-21, pendiente 11.4/3). No hay consola de Analítica: M9 tiene tres vistas más un panel de métricas para el administrador (CA-M9.3). La versión anterior de este documento describía cuatro superficies y daba por vigentes el umbral de fatiga, la revisión humana previa, el umbral de score, la clasificación Admiralty y el seguimiento de fuentes degradadas — todos ellos fuera del alcance del MVP (§2.2 del PRD). Se retiraron.

**Principio rector.** El lector es un gerente decidiendo en dos minutos. Toda decisión se resuelve a favor de la densidad de información y en contra del adorno. Si un elemento no aporta un dato, una fuente o una acción, no va.

---

## 0. Estado de la identidad de marca

Pactia no tiene un manual de marca unificado. Lo confirmado proviene de la plantilla Word corporativa real (`theme1.xml` y `styles.xml`). Este documento distingue tres niveles y **no los mezcla**:

| Nivel | Qué es | Cómo se marca |
|---|---|---|
| **Confirmado** | Extraído de la plantilla real de Pactia | Sin anotación |
| **Derivado** | Variación tonal del navy confirmado | `[derivado]` |
| **Provisional** | No existe en la marca Pactia. Propuesta técnica sujeta a reemplazo | `[provisional]` |

Lo marcado como provisional **no es identidad de Pactia**. Se reemplaza en cuanto exista brandbook. Ver §7.

> **Conflicto resuelto.** La especificación de interfaz previa (`especificacion_ui_inteligencia_territorial.md`) propone terracota como acento primario y tres familias tipográficas (serif, palo seco, monoespaciada). **Este documento la supersede en ambas cosas**: el navy está confirmado contra la plantilla real y las tres familias no existen en la identidad de Pactia. La especificación de UI sigue siendo válida como referencia de *estructura* de pantallas, no de color ni de tipografía.

---

## 1. Tokens

### 1.1 Color — base de marca

| Token | Hex | Uso |
|---|---|---|
| `color-navy-700` | `#0F4761` | **Confirmado.** Color primario: títulos, acciones primarias, insignia de posición, elementos de marca |
| `color-navy-100` | `#DEEAF0` | **Confirmado.** Fondo de fila alterna, fondos de bloque destacado |

### 1.2 Color — escala tonal del navy `[derivado]`

| Token | Hex | Uso |
|---|---|---|
| `color-navy-900` | `#0A3145` | Texto sobre navy-100, encabezados de primer nivel |
| `color-navy-500` | `#2C6B87` | Enlaces, elementos interactivos secundarios |
| `color-navy-300` | `#7FA9BC` | Bordes de elemento seleccionado, borde izquierdo de cita textual |
| `color-navy-050` | `#F1F7FA` | Superficie secundaria, recuadro de cita textual |

### 1.3 Color — neutrales `[provisional]`

| Token | Hex | Uso |
|---|---|---|
| `color-ink` | `#1A1D1F` | Texto de cuerpo |
| `color-ink-muted` | `#5B6670` | Metadatos, fuente y fecha, línea de fuentes |
| `color-ink-faint` | `#8A9199` | Texto deshabilitado, marcadores de posición |
| `color-border` | `#DDE2E5` | Bordes de tarjeta, separadores, líneas de tabla |
| `color-surface-alt` | `#F5F6F7` | Fondo de página |
| `color-surface` | `#FFFFFF` | Fondo de contenido |

### 1.4 Color — semántica de estado `[provisional]`

**Ninguno pertenece a la marca Pactia.** Se proponen por necesidad funcional y se reemplazan cuando exista paleta oficial.

| Token | Texto | Fondo | Significado en el MVP |
|---|---|---|---|
| `color-state-critical` | `#A4262C` | `#FBEAEA` | Error |
| `color-state-warning` | `#7A5400` | `#FDF4DC` | **Marca de contenido no validado** (CA-M6.5, CA-M9.17), correo no autorizado |
| `color-state-positive` | `#0E5C38` | `#E4F0EA` | Calificación registrada, estado guardado |
| `color-state-neutral` | `#5B6670` | `#EEF0F1` | Sin respuesta, pendiente, estado inicial |

**Regla dura:** el color **nunca** porta información por sí solo. Todo estado lleva etiqueta de texto además de color.

### 1.5 Tipografía

**Fuente:** Aptos. Confirmada como la fuente de la plantilla corporativa de Pactia, locale español.

**Pila:**
```css
font-family: Aptos, "Segoe UI", system-ui, -apple-system, sans-serif;
```

Aptos no está disponible como fuente web y no se incrusta: en máquinas sin Microsoft 365 la pila cae a Segoe UI o a la del sistema. Es aceptable y deliberado — la alternativa sería introducir una fuente que no es de Pactia.

**No existe fuente serif ni monoespaciada en la identidad de Pactia.** No se introduce ninguna. Los datos numéricos —scores, fechas, cifras de contratación, DIVIPOLA— se distinguen del texto redactado con recursos de la propia Aptos:

```css
font-variant-numeric: tabular-nums;
font-feature-settings: "tnum" 1;
```

| Token | Tamaño / Peso | Uso |
|---|---|---|
| `type-display` | 28 / 600 | Nombre de municipio al desplegar su detalle |
| `type-h1` | 22 / 600 | Título del informe del ciclo |
| `type-h2` | 17 / 600 | Encabezado de sección |
| `type-h3` | 14 / 600 | Nombre de municipio en la lista, nombre de fuente |
| `type-body` | 15 / 400 | Cuerpo, resúmenes, implicaciones |
| `type-data` | 15 / 600 tabular | Valores numéricos dentro del cuerpo |
| `type-data-lg` | 32 / 600 tabular | Score destacado |
| `type-meta` | 12 / 400 | Fuente, fecha, DIVIPOLA, identificadores |
| `type-label` | 11 / 600 mayúsculas, +0.06em | Etiquetas de estado y categoría |

Altura de línea: 1.5 para cuerpo, 1.25 para títulos y datos.

### 1.6 Espaciado `[provisional]`

Escala de base 4.

| Token | px | Uso |
|---|---|---|
| `space-1` | 4 | Separación dato ↔ su fuente |
| `space-2` | 8 | Interior de etiquetas de estado |
| `space-3` | 12 | Entre líneas de dato dentro de un bloque |
| `space-4` | 16 | Interior de tarjeta, entre campos |
| `space-6` | 24 | Entre bloques de una sección |
| `space-8` | 32 | Entre secciones |
| `space-12` | 48 | Margen superior de superficie |

**Radio:** 4px en tarjetas y etiquetas, 2px en controles. **Sombras:** ninguna; la separación se resuelve con borde de 1px en `color-border`. **Ancho de línea:** máximo 72 caracteres en texto redactado; las tablas pueden ocupar el ancho completo.

---

## 2. Vista de ciclo — la pantalla que decide el MVP

Es donde se miden H1 y H2. Todo lo demás es secundario.

### 2.1 Encabezado

Título, rango de fechas del ciclo, y número de municipios mostrados. **No hay criterio de corte que declarar**: el umbral de información está apagado y el tope es fijo en 10 (decisión P1 del 2026-09-21). Lo que sustituye al criterio de corte es la línea de fuentes de cada municipio (§2.3).

**Marca de contenido no validado** (CA-M6.5, CA-M9.17): etiqueta en `color-state-warning`, **en el encabezado y no en el pie**, con el texto «MVP — contenido no validado por Analítica». Visible sin dominar: etiqueta de una línea con `type-label`, no banner de ancho completo.

### 2.2 Lista de municipios

Diez filas, ordenadas por score descendente. El orden es fijo y no reordenable.

| Zona | Contenido | Token |
|---|---|---|
| Posición | Número sobre fondo navy-700, texto blanco | `type-data` |
| Municipio | Nombre + departamento + DIVIPOLA | `type-h3` + `type-meta` |
| Score | Valor de 0 a 1, cuatro decimales | `type-data` tabular |
| **Línea de fuentes** | Ver §2.3 | `type-meta`, ink-muted |
| Justificación | Dos o tres líneas: qué convergió y por qué importa | `type-body` |
| Sugerencia de acción | Qué se recomienda hacer, en imperativo. Fondo navy-100 | `type-body` |

Filas alternas en `color-navy-100`, siguiendo el patrón zebra de la plantilla corporativa.

> El score es un valor de **0 a 1, ordinal dentro de su corrida** — no una nota sobre 100 y no comparable entre ciclos (normalización min-max por cohorte). No se presente como porcentaje ni como calificación. La versión del modelo de scoring acompaña al informe, porque dos ciclos con versiones distintas no son comparables.

Justificación y sugerencia las escribe el Sintetizador y **llegan vacías hasta que M6 lo construya**. La pantalla debe pintar el hueco explícitamente, no ocultarlo.

### 2.3 La línea de fuentes

Es el elemento que sustituye a la exclusión por umbral de información. Su existencia es la decisión P1, y su posición es la decisión M6-orden.

**Posición:** junto al nombre y al score, con el mismo peso visual. **Nunca al pie, nunca en un desplegable.** Si va al pie, el desglose deja de informar y pasa a justificar a posteriori: para cuando se lee, el lector ya interpretó el puesto 1 como prioridad del ciclo.

**Contenido:** nombres de fuente, nunca códigos de factor (decisión M6-src). El mapa:

| Factor | Se muestra como |
|---|---|
| F1, F2, F3 | contratación pública |
| F4 | licencias de construcción |
| F5 | prensa |
| F6 | calificaciones de las gerencias |

Cinco factores colapsan en tres fuentes más las gerencias. **Las ausencias se nombran**, unidas con «ni», porque lo que falta informa más que lo que hay:

```
 1. Ibagué         0.8560   licencias y prensa, sin contratación
 3. Funza          0.5951   contratación, licencias y prensa
 4. Barranquilla   0.5696   licencias y prensa, sin contratación
```

F6 queda fuera de la frase **mientras falte en todos los municipios**: una línea que dice lo mismo siempre enseña a ignorarla, y es precisamente la línea que debe leerse. Sigue apareciendo en el desglose factor a factor. Cuando existan calificaciones, su ausencia vuelve a ser informativa y se reincorpora.

### 2.4 Calificación (CA-M7.1, CA-M7.6)

```
┌──────────────────────────────────────────────────┐
│  ¿Qué tan relevante es para tu evaluación?       │
│                                                  │
│   [ 1 ]  [ 2 ]  [ 3 ]  [ 4 ]  [ 5 ]              │  ← clic 1
│   nada                    acción inmediata       │
└──────────────────────────────────────────────────┘
```

- **Cinco controles terminales, un solo nivel.** Cada uno registra en el clic donde se pulsa. Sin confirmación intermedia, sin botón de envío (CA-M7.6).
- **Clic 1 = registro.** El segundo clic del presupuesto queda para el comentario opcional, que se despliega *después* de registrar. La calificación queda guardada aunque se cierre sin comentar.
- Los extremos llevan su significado escrito debajo. Los intermedios no se etiquetan: obligan a una lectura relativa, que es lo que se quiere medir.
- **Estado tras calificar:** el valor elegido queda en navy-700 sólido y el resto en borde. La fila no desaparece — hay que poder verificar qué se respondió sin recordarlo. Junto a ella, confirmación en `color-state-positive`.
- **Independencia (CA-M7.2):** nunca se muestra la calificación de otra gerencia, ni un promedio, ni cuántas ya respondieron.

**Alcance pedido (M9-carga):** la calificación **pedida** es sobre los insights de los tres primeros municipios. Los otros siete son calificables de forma opcional y se cuentan aparte. La distinción tiene que ser visible en la pantalla: si el lector no sabe qué se le pide, la tasa de H2 no significa nada.

**Correo antes de calificar (M9-acceso):** se pide una vez y se recuerda en cookie; pedirlo en cada calificación rompe los ≤2 clics. Quien no esté en la lista precargada no califica, y el mensaje debe decir **«este correo no está en la lista» y a quién escribir** — nunca un error genérico. Una errata durante la ventana de calificación se lleva por delante una respuesta de H2, y con siete gerencias cada una pesa el 14%. Debe existir una forma visible de cambiar el correo sin borrar cookies.

**Leer no requiere correo.** El informe se abre con el enlace; el correo solo gobierna la escritura.

---

## 3. Detalle de municipio (despliegue, no ruta)

Se abre dentro de la vista de ciclo. Los insights y sus evidencias se piden al desplegar, no vienen en la carga inicial.

### 3.1 Anatomía de un dato (CA-M6.4, RN-12)

Tres partes obligatorias, siempre en este orden y siempre contiguas:

| Parte | Token | Regla |
|---|---|---|
| **Valor** | `type-data`, ink, tabular | Compuesto desde el almacén de datos. **Nunca generado por el modelo** |
| **Etiqueta** | `type-body`, ink | Qué mide. Lenguaje de negocio |
| **Procedencia** | `type-meta`, ink-muted | `Fuente · fecha de publicación original · enlace` |

**Prohibido** mover la procedencia a un pie, a una nota final, a un número de referencia o a un elemento que requiera interacción. La separación entre dato y fuente es exactamente `space-1`. Si un dato no tiene fuente y fecha, no se muestra: el validador determinista ya debió rechazarlo aguas arriba.

### 3.2 Contexto estructural (M6-ctx)

Sección propia, compuesta por código desde `contexto_municipal`. El correlacionador escribe bandas en su prosa («un municipio con déficit habitacional alto»); **los números los pinta la pantalla**, nunca el modelo.

```
CONTEXTO ESTRUCTURAL
  20,9 %    Hogares en déficit cuantitativo
            DANE · censo 2018
  78.412    Habitantes
            DANE · proyección 2026
```

**El año es obligatorio y no es decorativo.** Un informe de 2026 mostrando déficit del censo 2018 necesita que el «2018» se vea, o se leerá como dato de hoy. Es lo que separa contexto estructural de señal del ciclo.

### 3.3 Evidencia, tres niveles

**Nivel 1 — Procedencia.** Visible siempre, sin interacción. Fuente y fecha junto al dato.

**Nivel 2 — Cita textual.** Se despliega en el sitio. Recuadro en `color-navy-050` con borde izquierdo de 2px en navy-300, con el fragmento literal entre comillas. Debajo: fuente, fecha de publicación y enlace, que abre en pestaña nueva.

**Nivel 3 — Señal cruda y cadena de trazabilidad (CA-M9.5).** Expone el registro de origen y su trayecto: `señal → insight → validación → correlación → score`.

| Campo | Contenido |
|---|---|
| Identificador de señal | Identificador interno |
| Fuente y categoría | SECOP II, RSS |
| Fecha de captura | Cuándo la ingestó el sistema |
| Fecha de publicación | Cuándo la publicó la fuente |
| URL de origen | Enlace directo |
| Contenido capturado | Texto tal como se recibió, sin reescritura |
| Trayecto | Insight, validación, correlación y aporte al score |

Es el ancla de auditabilidad y está a dos interacciones de cualquier cifra, nunca más. **Si dentro del despliegue resulta incómodo por volumen, puede tener ruta propia**: CA-M9.3 habla de navegación principal, no de que nada más pueda tener URL.

### 3.4 Score explicable (CA-M5.5, CA-M9.6)

```
Score del ciclo                                     0.5951
Versión del modelo: v3+8d8a2954

FACTORES QUE LO EMPUJARON

  Contratación pública                    ▓▓▓▓▓▓▓▓   +0.31
  Prensa                                  ▓▓▓▓▓      +0.14
  Licencias de construcción               ▓▓▓        +0.09

SIN DATOS EN LA VENTANA

  Calificaciones de las gerencias          —          (aún no hay)
```

- **Los factores sin datos se muestran, no se omiten.** Es la misma decisión de la línea de fuentes: la ausencia informa.
- **Orden por magnitud absoluta de contribución**, no por categoría.
- **La barra es comparativa, no decorativa.** Longitud proporcional, mismo eje para todos los factores de un municipio, siempre con el valor numérico al lado.
- **La versión del modelo acompaña al score.** Dos corridas con versiones distintas no son comparables y el lector debe poder notarlo.
- **Nombres de fuente, no códigos** — también aquí.

---

## 4. Las otras dos vistas y el panel

Se construyen después de la vista de ciclo, en este orden (§7 del PRD fija el mismo orden de recorte si hay retraso).

### 4.1 Municipios priorizados (CA-M9.8 a CA-M9.12)

Tabla, densidad alta. Estados con etiqueta de texto además de color: `priorizado`, `en_revision`, `en_estructuracion`, `descartado`. Nota obligatoria al pasar a `descartado` o `en_estructuracion`. Cada cambio queda como historial, no sobrescribe.

### 4.2 Histórico (CA-M9.7)

Lista de ciclos con informe publicado. Nada se sobrescribe entre ciclos. Los ciclos cerrados se ven y no se editan (CA-M7.7): un ciclo es editable si no hay informe publicado de un ciclo posterior.

### 4.3 Métricas — solo administrador (CA-M9.13, CA-M9.14)

Cuatro métricas: tasa de respuesta por gerencia, distribución de calificaciones, tasa de rechazo del validador y costo por ciclo por agente. Más exportación a CSV.

**Sin respuesta se cuenta aparte de calificación baja** (CA-M7.3). Son fenómenos distintos: uno es una opinión, el otro una ausencia. Colapsarlos destruye la única señal sobre adopción.

**Visibilidad restringida.** Ninguna gerencia ve el avance de otra: violaría CA-M7.2 y contaminaría H2.

---

## 5. Estados

### 5.1 Cargando

Esqueleto con la forma del resultado esperado, en `color-surface-alt`, sin animación de barrido. Indicador circular solo para acciones de menos de dos segundos.

**Prohibido** mostrar cifras parciales o provisionales. Un score que cambia mientras carga destruye la confianza en todos los scores.

### 5.2 Error

| Elemento | Contenido |
|---|---|
| Título | Qué falló, en lenguaje llano |
| Explicación | Una línea. Qué significa para el usuario |
| Tranquilización | Qué **no** se perdió |
| Acción | Una sola, primaria |

`color-state-critical`, con etiqueta de texto además del color. Un error nunca reemplaza contenido ya entregado: se anota junto a él. **Caso crítico:** si falla el guardado de una calificación, decirlo en el sitio y no borrar la selección.

### 5.3 Vacío

| Vacío | Mensaje |
|---|---|
| Aún no hay informe publicado | «El primer ciclo se publica el [fecha]» |
| El ciclo no produjo municipios | «Ningún municipio del ciclo tiene señal suficiente. El monitoreo continúa» |
| Los filtros no devuelven resultados | Mensaje + acción para limpiar filtros |

---

## 6. Móvil (CA-M9.18)

Usable en navegador móvil para **leer y calificar**. No hay app nativa y no hace falta que el tablero ni las métricas sean cómodos en pantalla estrecha.

- **La fila de calificación no se apila.** Cinco controles en fila, área táctil mínima de 44px. Apilarlos convierte un clic en un desplazamiento y rompe CA-M7.1.
- **La línea de fuentes no se trunca ni se esconde tras un «ver más».** Si no cabe en una línea, envuelve. Es el elemento que M6-orden exige que se lea.
- La lista de municipios pasa de fila a tarjeta: posición y score arriba, nombre, línea de fuentes, justificación.
- El detalle se abre a pantalla completa con retorno visible, no como despliegue dentro de una lista larga.

---

## 7. Vacíos de marca

Lo siguiente **no está definido en la identidad de Pactia** y no se inventó:

| Elemento | Impacto |
|---|---|
| **Logo** (archivo, variantes, zona de seguridad) | Hoy se resuelve con el texto «Inteligencia Territorial» en navy-700. Se requiere el archivo |
| **Iconografía corporativa** | Estados y categorías se resuelven solo con texto y color. Funciona, cuesta densidad |
| **Paleta semántica oficial** | Los cuatro colores de §1.4 son provisionales. Son los únicos valores que no derivan de la marca real |
| **Tono de voz** | La redacción de resúmenes, implicaciones y sugerencias la produce un modelo. Sin tono definido no hay criterio de aceptación para esa redacción. **Es el vacío más costoso**, y muerde en cuanto se construya el Sintetizador |
| **Escala tipográfica corporativa** | La de §1.5 es una derivación funcional de Aptos, no un estándar confirmado |

**Qué se necesita:** brandbook de Pactia, archivo de logo con sus variantes, y guía de tono de voz. Mientras no existan, los tokens `[provisional]` son deuda, no identidad.

---

## Anexo — Qué se retiró de la versión anterior y por qué

| Se retiró | Razón |
|---|---|
| Superficie de alerta por correo | No hay canal de notificación en el MVP (pendiente 11.4/3, resuelto 2026-09-21) |
| Consola de Analítica (catálogo de fuentes, supresiones, cola de revisión) | M9 tiene tres vistas más métricas (CA-M9.3). La consola es Fase 0 |
| Clasificación Admiralty (fiabilidad A–F, credibilidad 1–6) | No existe en el MVP |
| Umbral de fatiga y supresiones (RN-02) | Fuera de alcance: con ~6 alertas por ciclo no hay fatiga que suprimir (§2.2 del PRD) |
| Revisión humana previa de infografía | Fuera de alcance, riesgo aceptado (§7 del PRD) |
| Umbral de score y «criterio de corte aplicado» | El umbral de información está apagado y el tope es fijo en 10 (decisión P1) |
| Estado de fuente degradada | El MVP no rastrea salud de fuentes |
| Puntaje «sobre 100» | El score es 0–1, ordinal dentro de su corrida, no comparable entre ciclos |
| Restricciones de canal de correo (640px, sin CSS moderno) | No hay correo que renderizar |
