# Addendum 01 — Fuente de datos del MVP

**Documento base:** [PRD — MVP Inteligencia Territorial v1.0](prd.md)
**Fecha:** 2026-09-11
**Estado:** Decisiones tomadas
**Alcance:** Sustituye la §2.3 (Fuentes del MVP) y modifica M1, M3 y M5 del PRD del MVP.

---

## 1. Cambio de origen

El MVP **no ejecuta ingesta viva contra APIs**. Parte de un snapshot único:

```
docs/territorial_data_cruda_v3.json    20,2 MB · 258.153 líneas
generado: 2026-09-11 11:25 · versión 3.0
```

Esto altera el módulo M1 del PRD: el Agente Fuentes deja de consultar APIs y pasa a
cargar y particionar un archivo. Los criterios CA-M1.1 a CA-M1.5 se reinterpretan en §5.

---

## 2. Qué contiene el snapshot

**18 municipios** (no 25-30 como preveía §2.1 del PRD), en 5 corredores:
Caribe Portuario · Corredor Férreo · Eje Cafetero · Occidente Bogotá · Urabá–Puerto Antioquia.

| Fuente | Volumen | Naturaleza | Campos por registro |
|---|---|---|---|
| **SECOP II** | 19.640 (9.412 contratos firmados + 10.228 procesos en curso) | Oficial, verificable por URL e id | `id`, `objeto`, `entidad`, `proveedor`, `rep_legal`, `valor`, `valor_pagado`, `estado`, `modalidad`, `fecha`, `proceso_origen`, `url` |
| **RSS** (Google News) | 336 territoriales de 785 brutas | Filtrada por LLM; solo titular y resumen | `titulo`, `fuente`, `fecha`, `resumen`, `link` |
| **ELIC** (DANE, licencias de construcción) | 1 agregado por municipio | Oficial, verificable | `area_real_m2`, `unidades`, `licencias`, `desglose_destino[]`, `variacion_area_real_pct` |
| **Bing** (Azure AI Foundry) | ~10 señales por municipio | **Generado por LLM, NO verificado** (`url: null`) | `texto_completo` |

Volumen SECOP por municipio — mayores: Manizales 2.264, Armenia 2.152, Barranquilla 2.013,
Pereira 1.810. Menores: Chigorodó 154, Carepa 248, Puerto Colombia 373.

### 2.1 Sustituciones respecto al PRD

| PRD §2.3 | Snapshot v3 | Efecto |
|---|---|---|
| SECOP II vía SODA API | SECOP II (mismo origen, ya extraído) | Sin cambio de fondo |
| Feed georreferenciado (GDELT o equivalente) | RSS de Google News | Equivalente funcional; ver riesgo R2 |
| TerriData / DANE (población, economía, vivienda) | **Ausente.** En su lugar, ELIC | **Afecta CA-M5.2** — ver §6 |
| — | **Bing** (cuarta fuente, no prevista) | Ver decisión D1 |

---

## 3. Decisiones tomadas

### D1 — Bing es contexto, nunca evidencia

Bing no origina insights. El Agente Clasificador no lo recibe. El Agente Correlacionador
puede leerlo como contexto cualitativo, pero **ningún insight puede sustentarse en Bing**
ni citarlo como evidencia.

**Por qué:** Bing declara `url: null` y `naturaleza: "generado por LLM, NO verificado"`; sus
citas son marcadores tipo `【4:3†source】` que no resuelven a ninguna fuente. Si Bing pudiera
originar insights, el validador (CA-M3.1) los rechazaría en masa y la tasa de rechazo
—que según CA-M3.3 **es la tasa de alucinación medida**— pasaría a medir la alucinación de
Bing en vez de la del pipeline, invalidando H4 como señal.

**Implicación para la trazabilidad:** todo insight correlacionado que haya usado contexto de
Bing debe marcarlo en su traza (`contexto_no_verificado: true`), sin que ese contexto cuente
como evidencia.

### D2 — Los 3 ciclos se simulan por partición temporal

Ventanas, con corte por el campo `fecha` de cada registro:

| Ciclo | Ventana | SECOP | RSS |
|---|---|---|---|
| 1 | 2025-09-01 → 2025-10-22 | 6.419 | 17 |
| 2 | 2025-10-22 → 2026-01-14 | 6.669 | 58 |
| 3 | 2026-01-14 → 2026-09-09 | 6.548 | 261 |

Criterio: **terciles por volumen SECOP**, no tercios de tiempo iguales.

**Por qué:** SECOP es el 98% del volumen crudo y por tanto determina la carga del Clasificador
(CA-M2.1, reducción ≥85%) y el costo en tokens por ciclo (H5, CA-M8.3). Con tercios de tiempo
iguales los ciclos quedan en 11.961 / 5.118 / 2.557 registros — una razón de 5:1 que haría
insignificante la extrapolación presupuestal a 1.103 municipios.

**Debilidad aceptada:** el ciclo 1 queda con 17 noticias RSS para 18 municipios. SECOP y RSS
tienen distribuciones temporales opuestas (SECOP se concentra 84% entre sep-2025 y ene-2026 por
el ciclo de contratación pública colombiana; RSS se concentra en abr–jul 2026) y no existe un
corte que equilibre ambas.

**Ventana extendida a 2026-09-09.** El archivo declara `ventana_temporal_general` hasta
2026-08-09, pero contiene 1.007 registros SECOP entre 2026-08-10 y 2026-09-09. Se incorporan:
son dato real y verificable, y alimentan el ciclo 3.

**Fuentes no particionables:** ELIC y Bing carecen de fechas por registro. ELIC es un agregado
"acumulado enero–junio" de 2026 contra 2025. Ambas son **contexto constante en los 3 ciclos**;
no varían entre ellos y no pueden aportar novedad temporal.

### D3 — La PII se conserva

Los campos `proveedor` y `rep_legal` de SECOP (nombres de personas naturales en 19.640
registros) se mantienen en ingesta y persistencia.

**Por qué:** el dato proviene de fuente pública y es verificable por URL e id.

**Nota:** el propio snapshot advierte que los datos de personas están incluidos de forma
intencional y deben tratarse "conforme a la normativa de datos aplicable". Origen público no
exime de las obligaciones de la Ley 1581 de 2012. Queda como decisión consciente, no como
omisión.

### D4 — El scoring se construye sin TerriData, solo con razones y tasas

**TerriData no se incorpora al MVP.** El motor de scoring se construye con los datos del
snapshot, usando exclusivamente **proporciones y tasas normalizadas por cobertura**, nunca
volúmenes absolutos.

#### Por qué no bastaba usar los datos "tal cual"

El análisis del snapshot reveló tres sesgos que un score ingenuo habría incorporado sin que
nadie los viera:

1. **El volumen absoluto de SECOP mide tamaño de ciudad, no oportunidad.** El top por volumen
   en el ciclo 1 es Barranquilla (1.408), Armenia (1.222), Cartagena (1.010), Pereira (785),
   Manizales (526) — todas capitales. Un score sobre volumen rankearía las mismas capitales en
   los 3 ciclos. **Normalizar por población era precisamente la función de TerriData en CA-M5.2.**
2. **La variación interanual de ELIC explota en bases pequeñas.** Chigorodó marca +430,63% sobre
   5.768 m² y Carepa +273,15% sobre 4.239 m². Una sola licencia mueve el indicador cientos de
   puntos. Sin control de base, ELIC aporta ruido, no señal.
3. **La cobertura de SECOP es desigual entre municipios** y perjudica a los seis de mayor
   volumen (ver R7). Un score sobre conteos los dejaría en cero por falta de datos, no por
   falta de actividad.

#### Diseño del score

Todos los factores son **independientes del tamaño del municipio** por construcción:

| # | Factor | Cálculo | Por qué no depende del tamaño |
|---|---|---|---|
| F1 | Intensidad de obra | `n_obra / n_total` SECOP del ciclo | Es una proporción |
| F2 | Ticket medio de obra | `valor_obra / n_obra`, escalado | Es un promedio, no una suma |
| F3 | Aceleración de obra | tasa diaria de obra del ciclo ÷ tasa diaria del **mismo municipio** en ciclos previos | Comparación intra-municipal, normalizada por días cubiertos |
| F4 | Dinámica de licencias | `variacion_area_real_pct` de ELIC, **winsorizada a p10–p90** y anulada si `area_real_m2 < 10.000` | El winsorizado y el piso de área neutralizan la base pequeña |
| F5 | Densidad mediática | `n_noticias / días cubiertos` del ciclo | Es una tasa |
| F6 | Calificaciones previas | media de calificaciones 1-5 de ciclos anteriores, ponderada por gerencia | Satisface CA-M5.2; entra desde el ciclo 2 |

`n_obra` se determina por coincidencia de palabras clave de obra e infraestructura sobre el
campo `objeto` de SECOP (obra, infraestructura, construcción, vía, vial, pavimentación,
acueducto, alcantarillado, urbanización, parque, puente, edificación, adecuación, mejoramiento,
ampliación, ordenamiento, vivienda, lote, predio), con acentos normalizados.

**Normalización por cobertura — la pieza que neutraliza el truncamiento.** Todo factor basado en
SECOP se calcula sobre **días de cobertura real del municipio dentro del ciclo**, no sobre la
duración nominal de la ventana. Si un municipio cubre menos del **30%** de los días del ciclo,
sus factores SECOP (F1, F2, F3) se marcan `sin_cobertura` y **su peso se redistribuye
proporcionalmente entre los factores restantes**. Nunca se puntúa como cero: ausencia de dato no
es ausencia de actividad.

**Pesos por defecto (provisionales).** Pendiente 4 del PRD asigna esta decisión a Gerencia
General. Conforme a CA-M5.3 son configurables sin cambio de código. Propuesta inicial:

| Ciclo | F1 | F2 | F3 | F4 | F5 | F6 |
|---|---|---|---|---|---|---|
| 1 | 30% | 15% | — | 30% | 25% | — |
| 2 y 3 | 22% | 10% | 20% | 18% | 10% | 20% |

En el ciclo 1 no existen ciclos previos: F3 y F6 no aplican y su peso se redistribuye.

#### Qué se sacrifica

**CA-M5.2 queda modificado.** Donde decía *"features objetivas (TerriData/DANE) + calificaciones
previas"*, el MVP ejecuta *"features objetivas de composición y tasa derivadas de SECOP y ELIC +
calificaciones previas"*. La cláusula de calificaciones (F6) se cumple íntegra; la de features
objetivas se cumple con otro insumo.

CA-M5.1, CA-M5.3, CA-M5.4 y CA-M5.5 se cumplen sin cambios: el score es explicable factor por
factor, los pesos son configurables, se selecciona top 3 fijo y cada municipio del top 3 puede
listar qué factores lo empujaron.

**Por qué no se trae TerriData:** los seis factores son insensibles al tamaño por construcción,
de modo que la normalización poblacional deja de ser necesaria para que el ranking sea justo.
Sumar una fuente nueva añade alcance a un cronograma que §7 del PRD ya declara tensionado (8
semanas, 1 desarrollador, más el aplicativo web). **TerriData queda como requisito de Fase 0**,
no del MVP.

---

## 4. Riesgos nuevos

| # | Riesgo | Severidad | Tratamiento |
|---|---|---|---|
| R1 | El ciclo 1 tiene 17 noticias RSS para 18 municipios | Medio | Aceptado. SECOP carga la señal del ciclo 1; el desequilibrio se documenta al interpretar H1 |
| R2 | Los enlaces RSS son redirecciones de `news.google.com/rss/articles/...`, no la fuente original, y solo hay titular y resumen sin cuerpo | Medio | La cita textual exigida por CA-M3.1 solo puede ser el titular. Se acepta como cita válida para origen RSS; se documenta la limitación |
| R3 | ELIC y Bing son constantes en los 3 ciclos | Medio | Estructural, no corregible con este snapshot. Ningún insight puede derivar su novedad de ELIC o Bing |
| R4 | Sin TerriData no hay features estructurales para el scoring | Medio | Ver §6 |
| R5 | El snapshot es estático: no se valida la ingesta viva (CA-M1.1 a CA-M1.5) | Alto — aceptado | El MVP valida clasificación, validación, correlación y scoring. **No concluir de este MVP que la ingesta automatizada funciona** |
| R6 | 18 municipios en vez de 25-30 | Bajo | El PRD ya acepta que el MVP valida el mecanismo, no la cobertura (§7) |
| R7 | **La extracción SECOP está truncada en los 6 municipios de mayor volumen** | **Alto — mitigado** | Ver §4.1. Mitigado por la normalización de cobertura de D4 |
| R8 | **Atribución geográfica poco fiable**: hay señales archivadas bajo un municipio cuyo texto habla de otro | **Medio — no resuelto** | Ver §4.2 |

### 4.2 R8 — atribución geográfica

Medido sobre los 19.640 registros SECOP: **95 señales (0,5%)** nombran en su texto un municipio
distinto de aquel bajo el que están archivadas, sin mencionar el propio. Los casos frecuentes son
municipios vecinos — Manizales con La Dorada (30), Pereira con Dosquebradas (8), Apartadó con
Chigorodó (8) — lo que apunta a entidades contratantes de alcance regional.

**El 0,5% es un piso, no el total.** Solo cuenta menciones a los otros 17 municipios del MVP. Una
señal atribuida a un municipio que ni siquiera está en la lista no se detecta con este método. Se
encontró al menos un caso real: tres contratos sobre **Frontino** (Antioquia, fuera del MVP)
archivados bajo Apartadó, que produjeron un insight geográficamente equivocado.

**Por qué importa:** el Clasificador es fiel a la fuente, así que reproduce el municipio que dice
el texto. Un insight mal ubicado llega al informe del top 3 y lo leen las 7 gerencias a la vez.
Afecta la credibilidad, no solo la precisión.

**Sin resolver.** Detectarlo en general exige un nomenclátor DIVIPOLA completo de los 1.103
municipios, que no está en el snapshot. Queda como pendiente A3.

### 4.1 R7 en detalle — truncamiento de la extracción SECOP

Seis municipios tienen `fecha` máxima muy anterior al cierre del snapshot, y son exactamente los
seis de mayor volumen. El patrón indica que la extracción alcanzó un tope por municipio y dejó de
recolectar:

| Municipio | Registros | Fecha máxima | Meses sin cubrir |
|---|---|---|---|
| Barranquilla | 2.013 | 2025-11-21 | ~9,5 |
| Cartagena de Indias | 1.504 | 2025-12-29 | ~8,3 |
| Armenia | 2.152 | 2026-01-09 | ~8,0 |
| Pereira | 1.810 | 2026-01-15 | ~7,8 |
| Ibagué | 1.178 | 2026-01-16 | ~7,8 |
| Manizales | 2.264 | 2026-07-24 | ~1,5 |

Los otros doce municipios llegan hasta 2026-09-04 o posterior.

**Consecuencia si no se tratara:** Barranquilla, Cartagena, Armenia, Pereira e Ibagué quedarían
con cero registros SECOP en el ciclo 3 y un score cercano a cero — no por ausencia de actividad,
sino por ausencia de datos. El sesgo sería sistemático contra las ciudades grandes e invisible en
el informe.

**Opción descartada:** restringir el análisis a la cobertura común a los 18 municipios
(2025-09-01 → 2025-11-21, 81 días) conservaría solo el **53% de SECOP y el 12,5% de RSS** (42
noticias de 336). Inviable.

**Tratamiento adoptado:** la normalización por días de cobertura y el umbral `sin_cobertura` del
30% definidos en D4. Cada municipio se evalúa sobre el periodo que realmente tiene datos, y la
falta de cobertura se declara en la traza en vez de puntuarse como cero.

**Para Fase 0:** re-extraer SECOP con paginación completa. El tope de extracción debe tratarse
como defecto de ingesta, no como característica del dato.

---

## 5. Reinterpretación de criterios de aceptación

**M1 — Ingesta.** CA-M1.1 pasa a: *carga las 4 fuentes del snapshot y particiona por ventana
del ciclo sin intervención manual*. CA-M1.2 se mantiene sin cambios (URL y fecha de origen se
conservan). CA-M1.3 (dedup por hash) se mantiene: el `id` de SECOP y el `link` de RSS son la
clave. CA-M1.4 (tolerancia a fuente caída) queda **sin validar** — no hay fuente que se caiga.
CA-M1.5 se mantiene: se registra cuántos registros aportó cada fuente por ciclo.

**M3 — Validación.** CA-M3.1 se mantiene íntegro. Origen SECOP: `url` + `fecha` + cita del
campo `objeto`. Origen RSS: `link` + `fecha` + cita del `titulo` (ver R2). Origen ELIC:
`fuente_url` + periodo + cifra del desglose. Origen Bing: **no puede producir insights** (D1).

---

## 6. Scoring sin TerriData — resuelto

Resuelto en **D4**: el score se construye sin TerriData, con seis factores de composición y tasa
insensibles al tamaño del municipio, normalizados por días de cobertura real. CA-M5.2 queda
modificado; CA-M5.1, CA-M5.3, CA-M5.4 y CA-M5.5 se cumplen sin cambios.

TerriData pasa a ser requisito de Fase 0.

---

## 7. Pendientes abiertos

| # | Pendiente | Bloquea | Responsable |
|---|---|---|---|
| A1 | **Pesos definitivos del score** (D4 propone valores provisionales) | Calibración de M5 | Gerencia General — pendiente 4 del PRD |
| A2 | Validación del diccionario de palabras clave de obra sobre el campo `objeto` de SECOP | Precisión de F1, F2 y F3 | Área de Analítica |

---

## Anexo — Decisiones en una línea

- **D1** · Bing es contexto cualitativo, nunca evidencia. No origina insights.
- **D2** · Tres ciclos por terciles de volumen SECOP: cortes en 2025-10-22 y 2026-01-14, ventana extendida a 2026-09-09. ELIC y Bing son constantes en los tres.
- **D3** · La PII de SECOP se conserva.
- **D4** · Score sin TerriData: seis factores de composición y tasa, normalizados por cobertura real.
