# Tablero Javelin — MVP Inteligencia Territorial

> **Congelado el 2026-10-01 por decisión del dueño. No se modifica ningún
> criterio después de esta fecha.**

Generado el 2026-10-01 con [`docs/prompts/javelin.md`](prompts/javelin.md),
aplicando sus reglas del proyecto. Entradas: [`docs/prd.md`](prd.md) (último
cambio en `a813a3c`, que es el commit al que se refieren los números de línea),
los dos addenda y las desviaciones de
[`docs/decisiones-remediacion.md`](decisiones-remediacion.md).

**Este documento solo fija criterios. No evalúa ninguna hipótesis con los datos
actuales**, aunque los haya: la columna «Datos del MVP» dice si existen, no qué
dicen. La evaluación se hace el 9 y el 10 con
[`docs/prompts/evaluacion-piloto.md`](prompts/evaluacion-piloto.md), contra este
tablero ya congelado.

## El tablero

| # | Dimensión | Hipótesis crítica | Supuesto clave | Experimento | Métrica | Criterio de éxito | Origen | Datos del MVP | Sección del PRD |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Deseabilidad** | El pipeline agéntico produce insights que las gerencias consideran relevantes | Que una gerencia distingue un insight útil de uno que no lo es al leerlo en el informe | Piloto del MVP | Distribución de calificaciones 1-5 | ≥30% de insights con promedio ≥4 **[EST]** | PRD H1 | **Sí** — calificaciones de la ronda principal (exportadas) y de la extendida (abierta) | §1, línea 46 |
| 2 | **Deseabilidad** | Las 7 gerencias califican de forma sostenida | Que calificar es lo bastante útil y barato como para hacerlo sin que nadie insista. **Desviaciones registradas**: el núcleo son **5 gerencias «prd»**, no 7; y la condición fue **invitación personal y calificación autónoma**, no notificación por correo | Piloto del MVP | Tasa de respuesta por gerencia por ciclo | ≥50% promedio en ciclo 3 **[EST]** | PRD H2 | **Sí** — tasa por gerencia de las dos rondas, con su condición | §1, línea 47 |
| 3 | **Viabilidad** | El costo por ciclo es viable a escala nacional | Que el costo por municipio se mantiene al pasar de 18 a 1.103 municipios | Piloto del MVP | Tokens y costo por ciclo, extrapolado a 1.103 municipios | Extrapolación documentada | PRD H5 | **Sí** — tokens de las 266 trazas de agente; tarifa condicional (P-5) | §1, línea 50 |
| 4 | **Viabilidad** | El Área de Analítica puede operar el sistema con la capacidad que tiene | Que un ciclo corre casi solo y pide poca intervención humana, como exige la restricción de origen del PRD | **Concierge**: quien opere un ciclo anota cada intervención —qué hizo y cuántos minutos— durante 2 ciclos | Horas-persona de intervención por ciclo | **≤ 8 horas-persona por ciclo** *(umbral del dueño)* | **Añadida** — experimento hacia adelante | **No** — las horas no se registraron durante el piloto | §0, línea 34 · §6, línea 395 |
| 5 | **Viabilidad** | Los municipios priorizados producen acción, no solo lectura | Que una gerencia mueve el estado de un municipio en el tablero de seguimiento cuando le interesa | **Observación**: durante un ciclo se mira el tablero **sin pedir a las gerencias que muevan estados**. **Después del ciclo**, una entrevista de 10 minutos para entender por qué actuaron o no | % de municipios del top 3 que salen de `priorizado` en un ciclo, y cuántos llegan a `en_estructuracion` | **≥ 1 de los 3 municipios del top 3 sale de `priorizado` por ciclo** *(umbral del dueño)* | **Añadida** — experimento hacia adelante | **No** — `seguimiento` tiene 0 cambios de estado | §6, líneas 396 y 398 · CA-M9.9, línea 357 |
| 6 | **Factibilidad** | Las fuentes públicas con API contienen señal accionable | Que lo que el Clasificador extrae de SECOP y del feed de noticias se sostiene con citas que existen en la fuente | Piloto del MVP | % de insights que sobreviven al validador | ≥60% **[EST]** | PRD H3 | **Sí** — estado de validación de cada insight, por corrida | §1, línea 48 |
| 7 | **Factibilidad** | La cadena multiagente preserva la trazabilidad | Que de cada insight publicado se puede volver a la señal de origen sin pasar por el modelo | Piloto del MVP | % de insights con evidencia completa hasta fuente | 100% (bloqueante) | PRD H4 | **Sí** — traza extremo a extremo del informe publicado | §1, línea 49 |

**Siete hipótesis: cinco del PRD y dos añadidas.** Deseabilidad y factibilidad
tienen dos cada una con solo las del PRD; **viabilidad se quedaba con una, H5**,
y por eso lleva las dos añadidas.

## Cómo se mide cada una, fijado antes de ver los datos

**Ningún umbral cambia.** Lo que sigue fija **sobre qué se calcula** cada cifra
donde el PRD no lo dice, para que el 9 no haya margen de elegir la medida que
mejor quede. **Cada definición sale de una decisión ya registrada**; ninguna es
nueva.

| # | Qué se fija | De dónde sale |
|---|---|---|
| 1 | **Sobre los 15 insights pedidos** del informe 8, no sobre los 241 que muestra | «Se califica solo lo pedido» — `CLAUDE.md` regla 5 · F0.4 · **decisión del dueño del 2026-10-01** |
| 1 | **El promedio de cada insight usa las calificaciones de las gerencias «prd»** | Decisión del dueño del 2026-10-01 |
| 1 | **Un insight cuenta solo si tiene al menos 2 calificaciones «prd».** Si no, se reporta como **«insuficiente»** y **queda fuera del cálculo**: ni en el numerador ni en el denominador. El porcentaje se calcula sobre los insights que sí cuentan, y se dice cuántos quedaron fuera | Decisión del dueño del 2026-10-01 |
| 1 | **Se reporta también la versión con adicionales**: **sobre los mismos insights** —los que tienen al menos 2 calificaciones «prd»—, con el promedio incluyendo además las de `administrativa` y `analitica`. Así las dos versiones comparan el mismo conjunto | Decisión del dueño del 2026-10-01 · F0.1b |
| 2 | **Tasa por gerencia = calificados ÷ 15 pedidos**, y el promedio es **sobre las 5 gerencias «prd»** | F0.1b · núcleo del experimento |
| 2 | **Se reporta con su condición** y no se compara directamente con el criterio, que suponía correo | Decisión del 2026-09-25, condición única de la ronda |
| 1, 2 | **Ronda principal y ronda extendida, por separado** | Decisión del 2026-10-01 |
| 6 | **Supervivencia = 1 − tasa de rechazo, sobre los insights del Clasificador**, con la **corrida 10** —la publicada— como referencia | F0b.3: es el denominador que reproduce la auditoría |
| 6 | **R8 no se evaluó en ninguna corrida**: la supervivencia es a R1–R7, fidelidad de cita, y va con la frase de H-029 | F0b.3 · `CLAUDE.md` §4 |
| 7 | **Sobre los insights del informe publicado**, el 8 | Traza extremo a extremo de la auditoría y de F0.6 |
| 3 | **Tasa diaria por 14, no los totales del snapshot**; tarifa `1.586 + 239·k` con **k = 1** y la advertencia impresa; **sin Sintetizador**, que no existe, y hay que decirlo | `CLAUDE.md` §7 · decisión P-5 del 2026-09-25 |

## Lo que H2 puede y no puede decir con una sola ronda

**La hipótesis dice «de forma sostenida» y el criterio se mide «en ciclo 3».**
Con una sola ronda sobre un solo ciclo, lo que se obtiene es una tasa puntual,
no una sostenida. El criterio del PRD queda como está; lo que conviene es no
leer en él más de lo que mide.

Y con 5 gerencias «prd», **H2 es necesariamente indicativa** por la regla
n < 10 de la evaluación.

## De dónde sale cada hipótesis añadida

**Las dos se derivan de algo que el PRD ya menciona.** Ninguna introduce un
supuesto nuevo.

**4 · Capacidad de Analítica.** De la **línea 34** (§0):

> «… descansa sobre supuestos no verificados: que un sistema agéntico puede
> extraer señal accionable de fuentes públicas colombianas, que las gerencias
> van a calificar de forma sostenida, **y que el Área de Analítica tiene
> capacidad para operarlo**.»

**Son tres supuestos, y H1–H5 solo cubren dos**: el primero es H3 y el segundo
es H2. **El tercero no tiene ninguna hipótesis en el PRD**, aunque el propio
documento lo pone entre las incertidumbres que el MVP existe para resolver. La
métrica para medirlo también está ya en el PRD, **línea 395** (§6): «Horas
reales de intervención humana → Capacidad requerida de Analítica — pendiente 1
del PRD». Y la restricción que da sentido al umbral está en la **línea 38**: el
MVP «debe correr de forma autónoma».

**5 · Acción sobre los priorizados.** De dos líneas de §6:

> **Línea 396**: «Municipios priorizados que generaron interés de
> estructuración — Primera señal sobre conversión municipio → proyecto —
> medida directamente con los estados del tablero de seguimiento (CA-M9.9)».
>
> **Línea 398**: «Municipios que cambian de estado vs. los que quedan en
> `priorizado` sin tocar — Señal sobre si el top 3 produce acción o solo
> lectura».

El mecanismo para medirlo es el tablero de seguimiento, **CA-M9.9, línea 357**.
Existe y está desplegado; lo que no hay es ningún cambio de estado registrado.

## Cómo pesa cada hipótesis en la compuerta

**El tablero no cambia la compuerta del PRD §9.** Las dos hipótesis añadidas
son experimentos hacia adelante y **no entran en la decisión del 13**:

- **GO**: H2 y H4 cumplidos, y al menos dos de H1/H3/H5 en rango aceptable.
- **GO CONDICIONADO**: H4 cumplido pero H2 bajo.
- **NO-GO**: H4 incumplido, o H1 y H3 ambos por debajo del criterio.

## Decidido por el dueño el 2026-10-01, al congelar

1. **Hipótesis 4**: el umbral es **≤ 8 horas-persona por ciclo**, un día de
   trabajo por quincena. El PRD no daba cifra; la fija el dueño.
2. **Hipótesis 5**: el umbral es **≥ 1 de los 3 municipios del top 3 fuera de
   `priorizado` por ciclo**. Y el experimento **observa sin intervenir**: no se
   pide a las gerencias que muevan estados, porque pedirlo mediría la
   obediencia y no el interés. La entrevista va **después** del ciclo.
3. **H1**: sobre los 15 insights pedidos, con el promedio de las gerencias
   «prd», contando solo los insights con **al menos 2 calificaciones «prd»**;
   el resto se reporta como **«insuficiente»** y queda fuera. Se reporta
   también con adicionales. Detalle en la tabla de definiciones.
4. **H2 se queda en deseabilidad.**
5. **El tablero se congela hoy**, cinco días antes de lo previsto y una semana
   antes del cierre de la ronda extendida.
