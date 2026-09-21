# CLAUDE.md — MVP Inteligencia Territorial (Pactia)

Guía de trabajo para agentes sobre este repositorio.
**Actualizado:** 2026-09-21 · F4 a la mitad, corridas 19-21

---

## 1. Qué es este proyecto

Un **experimento acotado, no un producto.** Es la *Fase -1* del PRD de
Inteligencia Territorial v1.2 de Pactia: 8 semanas, 3 ciclos quincenales, para
decidir go/no-go sobre la Fase 0.

Comprueba si una cadena multiagente puede extraer señal inmobiliaria accionable
de fuentes públicas colombianas. El pipeline va de un snapshot de datos
(SECOP II, feed de noticias, Bing, TerriData) a un informe del top 3 de
municipios que 7 gerencias califican de 1 a 5 durante 3 ciclos.

| Dato | Valor |
|---|---|
| Municipios | **18** — los que trae el snapshot, no los 25-30 que preveía el PRD §2.1 |
| Señales | 20.030, repartidas en 3 ciclos por la fecha de cada registro (D2) |
| LLM | Azure OpenAI, superficie v1 de Foundry, **Responses API** (no `chat.completions`) |
| Base | SQLAlchemy sobre SQLite en local, PostgreSQL en nube (D8) |

Las hipótesis que valida son H1–H5 ([PRD §1](docs/prd.md)). **H4 — trazabilidad
al 100% — es bloqueante**: si falla, la arquitectura no es auditable y no puede
ir a producción. No se resuelve con más ingeniería.

> **Sobre H3 y el conteo «2 de 3 fuentes».** El PRD §2.3 lista SECOP II, el feed
> de noticias y TerriData como las tres fuentes, y eso induce a error al leer
> H3. **TerriData no es una fuente comparable**: es contexto estructural
> —población, economía, vivienda—, no señal de coyuntura, y no podría producir
> insights aunque estuviera cargada. De las fuentes que **sí pueden originar
> insights**, las dos están evaluadas: SECOP desde el principio y RSS desde el
> 2026-09-21, con un 98% de supervivencia al validador. **H3 está más cerca de
> respondido de lo que el conteo 2/3 sugiere.**

Documentos de referencia, en orden de autoridad: [PRD](docs/prd.md) ·
[Addendum 01 — Fuente de datos](docs/addendum-01-fuente-de-datos.md) ·
[Addendum 02 — Stack](docs/addendum-02-stack.md) ·
[Arquitectura](docs/architecture.md) · [Pendientes](docs/pendientes.md)

El resultado acumulado se va escribiendo en
[docs/informe_resultados.md](docs/informe_resultados.md), organizado por H1–H5.
Es un **documento de trabajo**: cada cifra lleva de dónde salió, y lo que no se
ha medido está como sección vacía con la nota de qué falta. Al medir algo que
toque una hipótesis, actualízalo ahí además de en `pendientes.md`.

> El PRD principal v1.2 **no está en el repositorio** (pendiente 11.5). Varias
> referencias citadas en otros documentos vienen de ahí y no se pueden
> verificar. No inventes requisitos para cubrirlas.

---

## 2. Reglas de obligado cumplimiento

### 2.1 Datos — consecuencia de D8 (SQLite local / PostgreSQL nube)

1. **Todo acceso a datos pasa por SQLAlchemy.** Nunca SQL crudo de un motor.
2. **El esquema se gobierna con Alembic** desde la primera migración.
3. **Las columnas JSON usan el tipo `JSON` portátil.** Nunca operadores JSONB de
   PostgreSQL (`->>`, `@>`, `jsonb_path_query`): no existen en SQLite y rompen
   el entorno local.

### 2.2 Bloqueante — CA-M6.3

**Ninguna cifra de un informe o infografía puede provenir del LLM.** Todas se
componen desde el almacén de datos. El LLM redacta; los números los pone el
código. Esta regla no admite excepción ni atajo.

### 2.3 Corolarios que sostienen H4

- El validador (M3) es **código, nunca LLM**. Si un modelo decidiera qué
  evidencia es suficiente, el experimento perdería su ancla: un agente elocuente
  parece funcionar aunque invente. **Su tasa de rechazo es la tasa de
  alucinación medida** (CA-M3.3).
- **Bing nunca es evidencia** (Addendum 01, D1). Es contexto cualitativo: llega
  sin fecha y sin URL. El validador lo rechaza por la regla R2.
- Los prompts van **versionados** y se archivan en el almacén (D7). El linaje se
  registra; no se edita un prompt en sitio.

---

## 3. Separación de capas

La frontera entre capas es lo que sostiene H4:
**lo determinista nunca depende de un LLM, y lo agéntico nunca decide qué es
evidencia suficiente** (PRD §3.1).

```
src/territorial/
│
├── CAPA 1 — DETERMINISTA (código, nunca LLM)
│   ├── ingesta/     Carga, particionado por ciclo, deduplicación
│   ├── reglas/      validador.py · prefiltro.py · cobertura.py · normalizacion.py
│   └── scoring/     M5 — F1–F6, pesos, ranking del top 3, persistencia
│
├── CAPA 2 — AGENTES (LLM)
│   ├── agentes/     fuentes · clasificador · correlacionador · sintetizador
│   ├── agentes/prompts/   Versionados (D7)
│   └── grafo/       EstadoCiclo y flujo LangGraph            [aún sin código]
│
├── CAPA 3 — SUPERFICIE
│   ├── web/         Django                                   [aún sin código]
│   ├── informes/    Jinja2 e infografías                     [aún sin código]
│   └── notificacion/  Correo con enlace profundo             [aún sin código]
│
└── TRANSVERSAL
    ├── almacen/     blob.py · modelos.py · sesion.py
    ├── observabilidad/  Langfuse, trazas de ciclo            [aún sin código]
    ├── utiles/      divipola.py
    └── config.py
```

Al añadir código, respeta la capa. Una regla de negocio no vive en un prompt, y
una llamada a LLM no vive en `reglas/`.

---

## 4. Estado real por módulo

Diagnóstico verificado sobre el árbol de trabajo el 2026-09-18. Las 139 pruebas
de `tests/` pasan.

**Nada se sobrescribe.** Insights, descartes y scores cuelgan de una *corrida*
—`corrida_agentes` y `corrida_scoring`— y cada ejecución inserta una nueva. Dos
pasadas del mismo ciclo conviven, que es lo que A6 necesita para medirse y lo
que impide que un reproceso borre lo que las gerencias calificaron.

### Dos resultados que no conviene enterrar

**La fuente sin filtrar rinde mejor que la filtrada.** RSS entra al Clasificador
**sin prefiltro** y convierte el **46%** de sus señales en insight; SECOP, que
pasa por el diccionario de obra, convierte el **40%**. El prefiltro existe para
ahorrar coste, y resulta que lo que deja pasar convierte *peor* que lo que nunca
se filtró. No prueba que haya que quitarlo —SECOP son 19.640 señales y RSS 336—
pero sí que su calibración no está seleccionando mejor señal, y refuerza A2
desde un ángulo distinto al de las subcadenas rotas.

Y cierra la duda que quedaba sobre el formato: de los 136 descartes de RSS,
**128 son `sin_implicacion_inmobiliaria`**. El Clasificador no se atraganta con
los titulares — les aplica la prueba de sustancia del prompt v4, que es lo que
tiene que hacer.

**Los 15 insights que cruzan RSS con SECOP son la primera evidencia de que la
correlación multiagente produce algo que ninguna fuente sola produce.** Es
CA-M4.1 literal —cruzar señales de categorías distintas sobre el mismo
municipio— y con una sola fuente era **literalmente imposible**: M4 no
funcionaba mal, no tenía nada que cruzar. Si algo lleva a la semana 8, es esto.

| Módulo | Estado | Detalle |
|---|---|---|
| **M1** Ingesta por API (Agente Fuentes) | ✅ Funciona | Carga los 18 municipios y las 20.030 señales; `data/territorial.db` poblada. Conectores vivos diferidos a Fase 0 |
| **Prefiltro** (apoya M2 y M5) | 🟡 Implementado, sin validar | Reduce 61,2%. El diccionario de obra produce entre 13% y 90% según el municipio — rango demasiado ancho para confiar en él (**pendiente A2**) |
| **M2** Clasificación | 🟡 Cumple CA-M2.1, no es reproducible | Prompt **v4**, lotes de 50, descartes registrados (CA-M2.5). **CA-M2.1 medido sobre el ciclo 1 completo: 95,2% y 94,9%** en dos pasadas (B2 cerrado). Pero **una de cada cinco señales cambia de destino entre pasadas idénticas** (**A6**): 19,5% aparecen en insight en una y no en la otra. No afecta al ranking —el score lee `senal_cruda`, no insights— pero sí a lo que las gerencias leen. Ver §8 y §9 |
| **M3** Validación determinista | ✅ Funciona | 7 reglas R1–R7. Tasa de rechazo 0,0% tras corregir el falso positivo de puntuación de SECOP. **Muestra pequeña: insuficiente para concluir sobre H4** |
| **M4** Correlación | 🟡 Funciona; CA-M4.3 sin ejercitar | Prompt v1, salida estructurada. CA-M4.1, CA-M4.2 y CA-M4.4 verificados contra el tenant. **La evidencia la une el código, no el modelo** (ver el encabezado de `agentes/correlacionador.py`). CA-M4.3 (bucle de aprendizaje) está implementado pero **no se puede probar**: no hay ni una calificación en la base |
| **M5** Scoring y priorización | ✅ Funciona con pesos provisionales | F1–F6 de D4, normalización por cohorte, winsorizado de F4, redistribución por cobertura, top 3 y desglose. Los 3 ciclos puntúan y persisten. Los **pesos definitivos** los decide Gerencia General (**pendiente A1/4**). Rigen los de `config/pesos.json`, que llevan **F4 a la mitad** por decisión de Analítica del 2026-09-21 — ver §7. Las corridas de antes y después conviven, distinguidas por `version_scoring` |
| **M6** Síntesis y distribución | ⬜ Sin código | Canal de notificación sin decidir (**pendiente 11.4/3**); §2.2 excluye Teams |
| **M7** Calificación | ⬜ Sin código | Depende del aplicativo web |
| **M8** Trazabilidad y observabilidad | 🟡 Parcial | Linaje de dataset, **de prompts por contenido** (D7) y trazas por agente (CA-M8.2). Falta Langfuse y el checkpointing de CA-M8.4: instalados pero **sin cablear**, no hay `grafo/` |
| **M9** Aplicativo web | ⬜ Sin código | Django **no está instalado** ni tiene versión fijada. Playwright está por verificar: descarga binarios sin firmar que la política de esta máquina bloquea |

### El nomenclátor DIVIPOLA: 1.135 entidades, y cuatro rarezas

`entidad_divipola` es una **tabla maestra de referencia**. Se carga con
`scripts/cargar_divipola.py`, es idempotente y **no amplía el universo del
MVP**: los 18 municipios siguen en `municipio` y las dos tablas no están
enlazadas a propósito. El MVP valida el mecanismo, no la cobertura (PRD §7).

Códigos como los de TerriData, para que un `join` futuro no traduzca nada:
nacional `01001`, departamento `dd000`, municipio `ddmmm`. Verificado contra el
propio TerriData: su primer indicador tiene exactamente estas 1.135 entidades.

Cuatro cosas que van a descuadrarle el conteo a alguien:

- **Son 1.102 municipios, no 1.103.** Falta San Andrés (88001); del
  departamento 88 solo está Providencia (88564).
- **Bogotá aparece solo como municipio** (11001). No existe `11000`, así que los
  departamentos son **32 y no 33**.
- **Las áreas no municipalizadas no están.**
- **63 nombres se repiten entre departamentos** y afectan a 144 municipios, el
  **13%**. Hay cuatro «La Unión» y cuatro «Buenavista». El par (departamento,
  municipio) es obligatorio; resolver por nombre suelto no es una opción.

> **No midas la atribución cruzada (A3) buscando estos 1.102 nombres en texto
> libre.** Son dos fenómenos distintos: A3 es contratación departamental
> archivada en la capital y ejecutada fuera, no colisión de nombres. Con el 13%
> de nombres ambiguos, «La Unión», «Buenavista» o «El Carmen» aparecerían por
> razones ajenas al municipio y el número saldría inflado — pasaríamos de un
> piso inútil por bajo (0,64%) a un techo inútil por alto. Esa medición
> necesita diseño propio.

### Pendientes que frenan el avance

- **B2** — CA-M2.1 **medido una sola vez**: 94,6% sobre Barranquilla en el ciclo
  2, por encima del 85% exigido. El «falta descartar otro 61,4%» que decía antes
  este pendiente salía de lotes de 20-25 señales y **no se sostuvo** al procesar
  el volumen real. Sigue abierto porque un municipio-ciclo no es el ciclo: falta
  correr los 18 y medir el agregado.
- **A4** — tras cuatro versiones del prompt, el Clasificador sigue partiendo un
  mismo frente de obra en varios insights (cuatro de pavimentación en Carepa).
  Infla el conteo y degrada el informe.
- **A3** — atribución geográfica (R8). El 0,5% de las señales SECOP nombran un
  municipio distinto al que están archivadas, y entran municipios fuera del MVP
  (caso Frontino). Resolverlo exige un nomenclátor DIVIPOLA de los 1.103
  municipios, que el snapshot no trae.
- ~~**B4**~~ — cerrado el 2026-09-17. **H5 tiene base y el costo no es una
  barrera**: USD 39/año el piloto, USD 2.160/año los 1.103 municipios. Tarifas
  en `config/tarifas.json`, cálculo en `scripts/estimar_costo.py`. El 89% del
  gasto es el Correlacionador, y el 84% del total es solo su salida de
  razonamiento. **No cuenta el Sintetizador (M6), que también corre sobre
  gpt-5** y podría no ser menor.
- **A5** — de las dos decisiones de M5 que D4 no cubre, el **umbral de
  información** ya está resuelto: queda en **50%**, en el centro de una meseta y
  no en un filo. Sigue abierta la **escala común** de los factores: min-max por
  cohorte es ordinal dentro de su corrida y no comparable entre ciclos. Ver §7.

---

## 5. Problemas abiertos en el repositorio

1. **La tabla «Estado» del [README.md](README.md) está desactualizada.** Declara
   M2 y M3 como pendientes, cuando ambos están en el repo desde los commits
   `440fe58` y `6f0b098`. La tabla de §4 de este archivo es la fuente correcta
   mientras el README no se corrija.

*Cerrado 2026-09-17:* Alembic estaba instalado pero sin inicializar. Ya existe
`alembic/` con la migración de línea base `949a8ff9e15d`, la ingesta migra en
vez de llamar a `create_all` y la base de desarrollo quedó estampada en `head`.
Ver §6.1.

---

## 6. Entorno

El intérprete vive **fuera del repositorio**, porque la política corporativa
impide ejecutar binarios desde `Downloads`. `python` a secas resuelve al stub de
Microsoft Store y no sirve.

```powershell
$py = "$env:LOCALAPPDATA\venvs\territorial\Scripts\python.exe"
& $py scripts\cargar_snapshot.py                        # M1 ingesta
& $py scripts\correr_ciclo.py --ciclo 1 --municipio 05147   # M2→M3→M4, gasta tokens
& $py scripts\calcular_scores.py --ciclo 1              # M5, no gasta tokens
& $py scripts\verificar_llm.py                          # conexión al tenant
& $py -m pytest -q                                      # pruebas
```

`correr_ciclo.py` sin `--municipio` procesa los 18, que son 18 llamadas al
Clasificador más las del Correlacionador. **Prueba siempre primero con uno.**
`--seco` corre y revierte.

Scripts de calibración: `medir_prefiltro.py`, `probar_clasificador.py`
(prefiltro → Clasificador → Validador en miniatura) y `comparar_prompts.py`,
que mide dos versiones de prompt sobre el mismo lote.

### 6.1 Migraciones (regla 2 de D8)

```powershell
& $py -m alembic current                              # en qué revisión está
& $py -m alembic upgrade head                         # aplicar pendientes
& $py -m alembic revision --autogenerate -m "motivo"  # tras tocar modelos.py
& $py -m alembic check                                # ¿el esquema y los modelos concuerdan?
```

Cuatro cosas que ahorran un rato:

- **`aplicar_migraciones()` en `almacen/sesion.py` es el camino desde código.**
  La ingesta lo llama; ya no existe `crear_esquema`. `create_all` quedó
  prohibido porque crea lo que falta y calla ante lo que cambió.
- **La URL no está en `alembic.ini`.** Sale de `Config.url_base_datos` vía
  `env.py`. No la escribas en el `.ini` o local y nube se separarán sin aviso.
- **`render_as_batch=True` está activo**, y es obligatorio: SQLite no sabe
  eliminar una columna ni cambiarle el tipo con un `ALTER TABLE` normal.
- **`--autogenerate` compara contra la base a la que apuntes.** Si esa base ya
  tiene las tablas, la migración sale vacía. Genera contra una base limpia:
  `URL_BASE_DATOS="sqlite:///$env:TEMP\vacia.db"`.

Corre `alembic check` antes de abrir una PR que toque `modelos.py`: falla si el
modelo y las migraciones se desincronizaron.

### El `upgrade` no prueba nada. `alembic check` sí

**Corre `alembic check` después de cada `upgrade`.** No es redundante: es la
verificación real.

El 2026-09-18 una migración imprimió `Running upgrade ... -> a6ac249fcec9` y
**falló a continuación**, dejando la base en la revisión anterior. La causa fue
un `create_foreign_key(None, ...)` que autogenerate rinde sin nombre y que en
modo batch revienta; el error salió por stderr y un `grep` del comando se lo
comió. El log decía que había subido y no había subido.

`alembic check` compara el esquema real contra los modelos, así que contradice
al `upgrade` cuando el `upgrade` miente. Fue lo único que lo detectó.

Y **nombra siempre las claves foráneas** en las migraciones. Autogenerate las
deja sin nombre y avisa en un `UserWarning` fácil de pasar por alto; en SQLite,
donde todo pasa por modo batch, sin nombre no funcionan.


**Ni la ingesta ni la capa determinista necesitan la clave** — solo los agentes.
`.env` nunca se sube a git; `.env.example` sí.

### Notas del tenant, verificadas por llamada real

- Cliente `OpenAI` con `base_url`, **no** `AzureOpenAI`. `api_version` no aplica
  en esta superficie.
- Despliegues asignados: clasificador `gpt-5.4-mini`, correlacionador `gpt-5`,
  sintetizador `gpt-5`. El criterio salió de una medición de tokens, no de una
  preferencia.
- Un `max_output_tokens` bajo **corta a los modelos de razonamiento antes de que
  emitan texto, y la llamada vuelve vacía sin error.** El techo está en **16384**
  para todos los agentes (`max_tokens_salida` y `max_tokens_salida_razonamiento`
  en `config.py`). Empezó en 4096 y hubo que subirlo dos veces: ver §9.

---

## 7. Dos decisiones de M5 que no vienen de D4

Están implementadas, documentadas en el código y son configurables, pero
**nadie las ha aprobado**. Si tocas el scoring, léelas antes.

**La escala común de los factores.** D4 fija cómo se calcula cada factor y
cuánto pesa, pero no en qué escala se suman, y sin eso los pesos no significan
nada: F1 vive en [0, 1], F4 va de -65% a +900% y F2 son miles de millones de
pesos. Se normaliza **min-max dentro de la cohorte del ciclo**. El costo: los
scores **no son comparables entre ciclos**, solo dentro de uno. Para el top 3
por ciclo da igual; para una serie temporal del score, habría que rehacerlo.

**El umbral de información del 50%** (`Config.umbral_informacion`). D4 manda
redistribuir el peso de los factores sin cobertura para no castigar al
municipio truncado. Sobre el snapshot aparece el efecto contrario: en el ciclo
3, Armenia tiene **0 de 239 días cubiertos**, conserva solo F4, ese factor pasa
a valer el 100% del score y Armenia sale **primera con un 1,0000 perfecto**.
Ibagué igual, con 3 días. La redistribución acaba premiando al que no tiene
datos, y encima con ELIC, que es constante en los 3 ciclos (D2/R3) y por tanto
no aporta señal del ciclo.

La guarda registra qué fracción del peso nominal tenía datos y, por debajo del
umbral, el municipio **queda fuera del top 3 pero no fuera del ranking**: no se
le pone cero, que es lo que D4 prohíbe. Con el umbral en `0.0` vuelve el
comportamiento literal de D4, y hay una prueba que lo verifica.

**La fracción informada mide dato, no puntuación** (decisión 2 de Analítica,
2026-09-21). `ValorFactor` separa `disponible` —¿el factor puntúa?— de
`hay_dato` —¿existe el dato subyacente?—. Coinciden salvo en un caso: el piso
de área de ELIC, donde el dato existe pero el porcentaje no es fiable sobre una
base tan pequeña. Antes eso descontaba dos veces: del score, que es correcto, y
de la fracción informada, que no. El piso sigue sin puntuar y sin entrar en la
escala de la cohorte; lo único que cambia es que cuenta como informado y el
crudo se conserva para el informe.

### Los pesos que corren no son los de `pesos.py`

`config/pesos.json` **está en el repositorio** y manda sobre
`PESOS_POR_DEFECTO`. Lleva **F4 a la mitad** —15% en el ciclo 1, 9% en los
otros dos, con lo liberado repartido en proporción— aprobado por Analítica el
2026-09-21.

F4 es **idéntico en los tres ciclos para los 18 municipios**: Apartadó marca
−43,5% en el 1, en el 2 y en el 3. No es un factor lento, es una constante por
municipio, y con el 18% del peso desplazaba a todos de forma fija sin que nadie
pudiera subir ni bajar por él. A la mitad y no a cero porque con F4 en cero F5
pasa a dominar el ciclo 3 con el 37% —donde SECOP está truncado— y Barranquilla
sale primera con un 1,0000 sacado de un solo factor: la patología se mudaba, no
se arreglaba.

Las pruebas **no** leen ese archivo: `tests/conftest.py` las fija a los pesos de
D4. Si no, cada recalibración de Gerencia rompería el suite por algo que no es
un defecto.

### La trampa que ya ha aparecido seis veces

**Ausencia de SECOP no es ausencia de actividad.** Está escrito en D4 y aun así
el sistema lo ha violado seis veces, siempre igual: SECOP es la fuente más rica,
así que todo acaba calculándose desde ella, y el municipio que no contrata
obra queda indistinguible del que no existe.

1. **F5** dividía por días cubiertos, que salían solo de fechas de SECOP.
   Barranquilla con 47 noticias se quedaba sin densidad mediática (A7).
2. **El corte de cohorte** propagaba el NULL al conjunto si a un municipio le
   faltaba SECOP, dejando el ciclo 3 sin fecha de auditoría (`_corte`).
3. **El piso de área de ELIC** se descontaba de la fracción informada, como si
   una base pequeña fuera un dato ausente (A8).
4. **El prefiltro** marca como obra los contratos de servicios profesionales
   que hablan de obra sin serlo, y no ve nada que no tenga forma de objeto
   contractual (A2).
5. **RSS no llegaba al Clasificador**: una de las tres barreras era el
   diccionario de obra, calibrado sobre objetos de SECOP (B7).
6. **La fracción informada** es casi toda peso derivado de SECOP. Al bajar F4,
   los cinco municipios truncados del ciclo 3 pasan de 28% a **20%** informados
   — Barranquilla entre ellos, con 12 insights de prensa que pasaron el
   validador. El sistema sabe cosas de Barranquilla y su propia métrica dice
   que no sabe nada (P1).

Antes de escribir cualquier cosa que divida, filtre o cuente, pregúntate qué
pasa con el municipio que tiene noticias y no tiene contratos.

## 8. Carga inicial y operación no son lo mismo

El snapshot cubre **374 días** y sus tres ciclos duran **51, 84 y 239 días**. No
son quincenales, pese a que el PRD los llame así: D2 los partió por terciles de
volumen SECOP. **El ciclo 3 son 17 quincenas.**

| | Señales tras el prefiltro |
|---|---|
| Carga inicial (el snapshot, un año) | **7.628** |
| Una quincena en operación | **~615** |

La tasa real agregada es de 43,9 señales al día en los 18 municipios. En régimen
normal **13 de los 18 no llegan a 20 señales por quincena**; solo Barranquilla
(204), Armenia (92), Pereira (61), Cartagena (50) e Ibagué (48) pasan de 40.

Dos consecuencias, y la segunda es la que importa:

- Dimensionar el troceo con las cifras del snapshot sobredimensiona el sistema
  por un factor de 12.
- **H5 no se puede extrapolar con los totales del snapshot.** Multiplicar el
  costo de un ciclo del MVP por 1.103 municipios sobreestima el régimen
  permanente en un orden de magnitud. Para el pendiente B4 hay que usar la tasa
  diaria por 14, no los totales. Medido: el Clasificador gasta ~282 tokens de
  entrada y ~111 de salida por señal.

## 9. Tres cosas que cortan una llamada sin avisar

**El techo de tokens puede depender del agente, aunque hoy no difiera.**
`cliente.techo_de()` devuelve `max_tokens_salida_razonamiento` para los agentes
de `AGENTES_QUE_RAZONAN` (Correlacionador y Sintetizador) y `max_tokens_salida`
para el resto. **Ambos valen 16384 hoy**, así que la función no cambia nada: se
conserva como el punto donde separarlos si vuelven a divergir. Si añades un
agente sobre un modelo de razonamiento, mételo en ese conjunto.

Con el techo en 4096 el Correlacionador se cortó en seco en Barranquilla —6
insights sobre 5 categorías— y **la llamada volvió vacía y sin error**, que es
la forma más difícil de diagnosticar.

*Detalle menor pendiente:* el Clasificador llama a `cfg.max_tokens_salida`
directamente en vez de a `techo_de("clasificador")`. Hoy da el mismo número, así
que no cambia nada; si algún día los valores divergen, ese es el sitio que se
queda atrás.

**El Clasificador se truncaba, y fallaba distinto** (pendiente B5, cerrado). Su
techo era de texto, no de razonamiento: a ~111 tokens de salida por señal, 40
señales daban 4.243 y el corte estaba en 4.096, así que el JSON llegaba cortado
a media cadena. Ahora el techo es 16.384 y `Config.senales_por_lote` trocea de
50 en 50. **No subas el lote por velocidad**: con 100 señales cabe de sobra pero
4 de 7 insights salieron sin categorizar. El límite práctico es la calidad, no
los tokens, y se degrada en silencio — el JSON sigue siendo válido.

**El Clasificador no es reproducible entre corridas.** El mismo lote de 20
señales de Carepa dio 3 insights una vez y 6 otra. Importa para H4 y para
cualquier medición de prompts: `comparar_prompts.py` mide una muestra de uno.

## 10. Al cambiar el prompt de un agente

No lo afines a ojo. Crea una versión nueva en `agentes/prompts/`, córrela contra
la anterior sobre el mismo lote con `comparar_prompts.py` y reporta las métricas
(reducción, tasa de rechazo, señales sin contabilizar, insights duplicados,
tokens). Las versiones que resultan peores **se conservan como registro**: v3
está en el repo porque documenta una hipótesis que resultó incorrecta.
