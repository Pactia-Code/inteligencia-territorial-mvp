# Auditoría técnica independiente — MVP Inteligencia Territorial (Pactia)

**Commit auditado:** `96e10e0` · rama `audit/2026-09-22` (HEAD de trabajo `fc46469`,
que solo añade `docs/audit-baseline.md` y `.claude/commands/auditoria.md`; el
código es idéntico al SHA auditado — verificado con `git diff --stat 96e10e0 HEAD`).
**Fecha del Preflight:** 2026-09-22.
**Estado del informe:** Fase 0 (Preflight) completa. Ninguna área auditada todavía.
No hay hallazgos numerados; la numeración `H-001…` empieza con el área 1.

Restricciones bajo las que se escribe: solo se modifica este archivo; ninguna
sentencia de escritura contra ninguna base; ningún ciclo ni llamada a LLM
ejecutados; ninguna interacción con el servidor de desarrollo que escriba datos.

---

## 0. Preflight

### 0.0 Condiciones de la sesión y asunciones declaradas

Los argumentos del comando dejaron dos campos sin rellenar. Se procede con las
asunciones siguientes, que el dueño puede corregir antes del área 1:

| Campo | Asunción adoptada | Por qué |
|---|---|---|
| Base usada durante la auditoría | **SQLite local `data/territorial.db`** para toda lectura que no exija Neon; **Neon solo con `SELECT` e inspección de esquema**, para comparar las dos bases | Es la opción sin ningún riesgo de escritura sobre la nube. La cadena de `.env` tiene permisos de escritura (`show transaction_read_only` devolvió `off`), así que la contención es por disciplina, no por permiso |
| Fuente de verdad de los resultados | **Neon** para el estado vigente del experimento (informe publicado, usuarios, futuras calificaciones); **las cifras de `docs/informe_resultados.md` se produjeron antes de la migración**, sobre SQLite | Las dos bases tienen **datos de pipeline idénticos** (§0.7), así que ninguna cifra de pipeline puede diferir por la base. Solo `informe` y `usuario` viven únicamente en Neon |

Criterios acordados con el dueño que **no están en el PRD** y que este informe aplica:

- **Conjunto bloqueante definido por la auditoría:** CA-M3.1–CA-M3.4, CA-M6.3,
  CA-M7.2, CA-M8.1, CA-M9.16. Es un criterio de auditoría, no una designación
  del PRD, que solo marca H4 como bloqueante.
- **Infografía** (CA-M6.2, CA-M9.4): no especificada y no retirada → se reporta
  lo que hace el código y el hueco va como Brecha documental.
- **Criterios con desviación registrada** se evalúan contra el registro
  (`docs/pendientes.md`), y luego se comprueba si la desviación retira un control
  del que depende otro criterio.

### 0.1 Mapa del repositorio

**Lenguajes:** Python 3.12 (pipeline, `src/territorial/`, `scripts/`, `alembic/`,
`tests/`) y TypeScript/React (aplicativo web, `web/`). Configuración en `.env`
(pydantic-settings) y `config/*.json`.

| Directorio | Archivos | Líneas | Qué es |
|---|---|---|---|
| `src/territorial/` (raíz) | 3 | 704 | `config.py` (Config pydantic), `ciclo.py` (orquestación determinista M2→M3→M4→M5), `__init__.py` |
| `src/territorial/agentes/` | 6 | 1.204 | `cliente.py` (OpenAI SDK contra Foundry v1), `clasificador.py` (M2), `correlacionador.py` (M4), `linaje.py` (D7 prompts), `persistencia.py` (corridas, insights, descartes, trazas) |
| `src/territorial/agentes/prompts/` | 6 | 582 | `clasificador_v1..v4.md`, `correlacionador_v1..v2.md` |
| `src/territorial/reglas/` | 7 | 687 | `validador.py` (M3, R1–R7), `prefiltro.py`, `cobertura.py`, `normalizacion.py`, `contexto.py` (bandas), `cifras.py` (fuga de cifras) |
| `src/territorial/scoring/` | 6 | 1.352 | `factores.py` (F1–F6), `pesos.py`, `ranking.py`, `agregacion.py` (ORM→entradas), `persistencia.py` (corridas append-only) |
| `src/territorial/informes/` | 4 | 755 | `composicion.py` (payload M6), `publicacion.py`, `seleccion.py` (qué se pide calificar) |
| `src/territorial/ingesta/` | 4 | 560 | `snapshot.py` (M1 sobre snapshot), `nomenclator.py`, `contexto.py` (TerriData) |
| `src/territorial/almacen/` | 4 | 984 | `modelos.py` (18 tablas), `sesion.py`, `blob.py` |
| `src/territorial/utiles/` | 2 | 76 | `divipola.py` |
| `alembic/` + `versions/` | 14 | 1.347 | 11 migraciones lineales, `949a8ff9e15d` → `b37b4fd6e183` |
| `scripts/` | 19 | 3.084 | Puntos de entrada (ver abajo) |
| `tests/` | 14 | 3.920 | 272 pruebas, todas sobre `sqlite://` en memoria |
| `web/app/` | 10 | 1.628 | Next.js 15 App Router: `layout.tsx`, `page.tsx`, `acciones.ts` (Server Actions), `Nav.tsx`, `ciclo/[id]/` (3), `priorizados/` (2), `globals.css` |
| `web/lib/` | 7 | 643 | `db.ts`, `consultas.ts`, `escrituras.ts`, `sesion.ts`, `tablero.ts`, `tipos.ts`, `contrato.generado.ts` |
| `docs/` | 9 | ~3.800 | PRD, dos addenda, arquitectura, design system, pendientes, informe de resultados, línea base de auditoría |

**Directorios que el diseño prevé y no existen:** `src/territorial/grafo/`
(LangGraph), `src/territorial/observabilidad/` (Langfuse), `web/app/historico/`,
`web/app/metricas/`.

**Puntos de entrada y cómo se corre un ciclo (modelo de ejecución D9 del
Addendum 02: manual, sin cron):**

| Paso | Comando | Gasta tokens | Escribe |
|---|---|---|---|
| Ingesta del snapshot (M1) | `scripts/cargar_snapshot.py` → `ingesta/snapshot.cargar()` (aplica migraciones, `snapshot.py:156`) | No | `dataset_version`, `ciclo`, `municipio`, `senal_cruda` |
| Nomenclátor y contexto | `scripts/cargar_divipola.py`, `scripts/cargar_contexto.py` | No | `entidad_divipola`, `contexto_municipal` |
| Usuarios autorizados | `scripts/cargar_usuarios.py` (CSV `data/usuarios.csv`, ignorado por git) | No | `usuario` |
| **Ciclo M2→M3→M4→M5** | `scripts/correr_ciclo.py --ciclo N [--municipio D]... [--lote n] [--seco]` → `ciclo.procesar_ciclo()` (`ciclo.py:473-576`) | **Sí** | `corrida_agentes`, `prompt_version`, `insight`, `descarte`, `traza_agente`, y al final `corrida_scoring` + `score_municipio` |
| Solo scoring (M5) | `scripts/calcular_scores.py [--ciclo N] [--seco]` | No | `corrida_scoring`, `score_municipio` |
| **Publicar informe (M6)** | **No existe script.** `informes/publicacion.publicar(sesion, id_corrida_scoring, id_corrida_agentes)` (`publicacion.py:128-178`) solo es invocable desde Python | No | `informe` |
| Aplicativo (M9) | `web/`: `npm run dev` / `next build`; lee `DATABASE_URL` | No | `calificacion`, `seguimiento` (vía Server Actions) |
| Calibración y medición | `comparar_prompts.py`, `comparar_correlacionador.py [--persistir]`, `comparar_pasadas.py`, `dos_pasadas.py`, `probar_clasificador.py`, `probar_correlacionador.py`, `medir_prefiltro.py`, `estimar_costo.py`, `generar_hojas_revision.py` | Algunos sí | `--persistir` inserta corridas de agentes **sin Clasificador** (ver `publicacion.py:66-86`) |
| Migraciones | `alembic upgrade head` (CLI, `alembic/env.py`) o `sesion.aplicar_migraciones()`; ambos pasan por `exigir_directa()` | No | DDL |
| Contrato TS | `scripts/generar_contrato_ts.py [--check]` → `web/lib/contrato.generado.ts` | No | archivo |

**Confirmación municipio a municipio:** `procesar_ciclo` hace `commit()` tras cada
municipio (`ciclo.py:539-542`) y `rollback()` + re-adjunta la corrida si uno falla
(`ciclo.py:543-555`). Ese commit es el único «checkpoint» existente; el propio
módulo declara que LangGraph «**no está cableado**» (`ciclo.py:17-21`).

### 0.2 Qué se pudo ejecutar

Todo lo siguiente se ejecutó en esta sesión. **La auditoría no es estática**: hay
comprobaciones ejecutadas de entorno, esquema, tests, tipos y rutas HTTP. **Lo que
no se ejecutó**: ningún ciclo, ninguna llamada al LLM, ninguna escritura.

| # | Comando | Resultado |
|---|---|---|
| 1 | `git rev-parse HEAD`, `git branch --show-current`, `git diff --stat 96e10e0 HEAD` | `fc46469` en `audit/2026-09-22`; diferencia con el SHA auditado: solo 2 archivos de `docs/` y `.claude/` |
| 2 | `python --version` (venv `%LOCALAPPDATA%\venvs\territorial`) | Python 3.12.14, pip 25.0.1 |
| 3 | `pip list --format=freeze \| wc -l`; `pip check` | 84 paquetes; «No broken requirements found». **No se instaló nada**: ya estaba todo |
| 4 | `pip show territorial` | Instalado **editable** desde `C:\dev\SeguimientoTerritorial` |
| 5 | Versiones clave | sqlalchemy 2.0.54 · alembic 1.20.0 · psycopg 3.3.5 · openai 3.14.1 · langfuse 4.15.4 · langgraph 1.2.11 · pytest 9.1.1 |
| 6 | `node --version`, `npm --version`, `npm ls --depth=0` en `web/` | Node 22.11.0, npm 10.9.0; next 15.5.25, react 19.3.0, typescript 5.9.3, `@neondatabase/serverless` presente; lockfile presente |
| 7 | `alembic current` con `DATABASE_URL=sqlite:///data/territorial.db` | `b37b4fd6e183 (head)` |
| 8 | `alembic current` contra Neon (cadena de `.env`, host directo) | `b37b4fd6e183 (head)` |
| 9 | `alembic check` (SQLite) | «No new upgrade operations detected» — esquema y modelos concuerdan |
| 10 | `alembic history` | 11 revisiones, cadena lineal sin ramas (ver §0.1) |
| 11 | `SELECT count(*)` por tabla en ambas bases + `SELECT` de `informe`, `corrida_scoring`, `corrida_agentes`, `usuario`, `alembic_version` | Ver §0.7 |
| 12 | `SELECT version()`, `show transaction_read_only` en Neon | PostgreSQL 18.6 (aarch64); `transaction_read_only = off` → la cadena **puede escribir** |
| 13 | `scripts/generar_contrato_ts.py --check` | «al día», exit 0 |
| 14 | `ruff check .` | **7 errores** (4 corregibles automáticamente); al menos uno en `scripts/probar_clasificador.py:103` (variable no usada). Inventario completo en el área 10 |
| 15 | `npx tsc --noEmit` en `web/` | exit 0, sin errores de tipos |
| 16 | `pytest --collect-only -q` | 272 tests en 13 archivos |
| 17 | `grep create_engine\|sqlite:// tests/` | Todas las fixtures usan `create_engine("sqlite://")` (memoria); `test_conexion.py` usa una URL de Neon **ficticia**. Ningún test toca `data/territorial.db` ni Neon |
| 18 | `pytest -q -p no:cacheprovider` | **272 passed in 6.61s** |
| 19 | `curl -s -o /dev/null -w %{http_code}` contra el dev server (puerto 3000, ya levantado por el dueño) | `/`→200 · `/ciclo/3`→200 · `/ciclo/2`→404 · `/priorizados`→200 · **`/historico`→404 · `/metricas`→404** |
| 20 | `git log --all -S'npg_'`; `git grep -I 'npg_' <cada commit>`; `git log --all -- .env` | 0 commits con el prefijo de la contraseña de Neon en 66 revisiones; `.env` nunca rastreado. `neon.tech` aparece solo como host de ejemplo o documentación en 4 commits |
| 21 | `grep` de nombres de variables en `.env` y `.env.example` (nunca valores) | 21 y 20 variables; solo difiere el alias antiguo `URL_BASE_DATOS`. Sin `.env` en `web/` |
| 22 | `Config()` en Python: `modo_almacen`, existencia de `RUTA_BLOB_LOCAL` | `local`; el directorio existe con 6 entradas |
| 23 | `grep -rn contexto_no_verificado src/ scripts/` (fuera de `modelos.py`) | **Cero asignaciones**: la columna que D1 exige marcar nunca se escribe |
| 24 | `grep` de escrituras a `ciclo.n_senales/n_insights/n_validados/n_rechazados/costo_tokens/duracion_seg` | **Nadie las escribe** |
| 25 | `grep` de `hash_output=`, `id_prompt=`, `id_dataset=` en la construcción de trazas | Solo el parámetro de `guardar_traza`; **ningún llamador pasa `hash_output`, `id_prompt` ni `id_dataset`** |
| 26 | `grep -- '->>\|@>\|jsonb\|json_extract' src/ scripts/ web/` | Ninguno fuera del comentario de `modelos.py:4` |
| 27 | `grep -i 'smtp\|sendmail\|nodemailer\|resend\|sendgrid\|send_email'` | Ninguno: no hay código que envíe correo |
| 28 | `grep 'TODO\|FIXME\|XXX\|HACK'` en `src/ web/ scripts/ alembic/ tests/` | **0** |
| 29 | `grep -i infografia src/ web/ scripts/` (fuera del modelo) | Ninguna referencia: solo la columna `informe.infografias` |
| 30 | `grep 'Seguimiento(\|Calificacion(\|\.delete(\|DELETE\|UPDATE ' src/ scripts/` | Python no escribe `seguimiento` ni `calificacion`; el único `delete()` es `scripts/copiar_base.py:138` (vaciar destino con `--vaciar`) |

### 0.3 Cobertura de inspección

Solo lo listado como **leído completo** puede citarse como evidencia en las áreas
sin volver a abrirlo.

**Leídos completos (con `cat -n`, líneas citables):**
`src/territorial/config.py` · `ciclo.py` · `almacen/modelos.py` · `almacen/sesion.py` ·
`almacen/blob.py` · `agentes/cliente.py` · `agentes/clasificador.py` ·
`agentes/correlacionador.py` · `agentes/linaje.py` · `agentes/persistencia.py` ·
`reglas/validador.py` · `reglas/cifras.py` · `reglas/prefiltro.py` · `reglas/cobertura.py` ·
`reglas/normalizacion.py` · `reglas/contexto.py` · `scoring/factores.py` · `scoring/pesos.py` ·
`scoring/ranking.py` · `scoring/persistencia.py` · `scoring/agregacion.py` ·
`informes/__init__.py` · `informes/composicion.py` · `informes/publicacion.py` ·
`informes/seleccion.py` · `ingesta/snapshot.py` · `ingesta/contexto.py` ·
`ingesta/nomenclator.py` · `utiles/divipola.py` · `alembic/env.py` ·
`scripts/correr_ciclo.py` · `scripts/calcular_scores.py` · `tests/conftest.py` ·
`config/pesos.json` · `config/tarifas.json` · `pyproject.toml` ·
`web/app/layout.tsx` · `web/app/page.tsx` · `web/app/Nav.tsx` · `web/app/acciones.ts` ·
`web/app/globals.css` · `web/app/ciclo/[id]/page.tsx` · `web/app/ciclo/[id]/Panel.tsx` ·
`web/app/ciclo/[id]/Identificarse.tsx` · `web/app/priorizados/page.tsx` ·
`web/app/priorizados/CambiarEstado.tsx` · `web/lib/db.ts` · `web/lib/sesion.ts` ·
`web/lib/consultas.ts` · `web/lib/escrituras.ts` · `web/lib/tipos.ts` ·
`web/lib/tablero.ts` · `web/lib/contrato.generado.ts` · `web/next.config.ts` ·
`web/package.json` · `docs/prd.md` · `docs/audit-baseline.md` · `CLAUDE.md`.
*Añadidos al cerrar el área 4:* las 11 migraciones `alembic/versions/*.py` ·
`alembic.ini` · `scripts/cargar_usuarios.py`.

**Leídos parcialmente:** `docs/addendum-01-fuente-de-datos.md` (§3 D1–D4, §5, §6,
§7, anexo) · `docs/addendum-02-stack.md` (D5 cabecera, D9, pendientes, anexo) ·
`docs/design-system.md` (§2–§4) · `docs/pendientes.md` (todas las filas, truncadas
a 900 caracteres) · `docs/architecture.md` (§0, §6.2, §11) · `docs/informe_resultados.md`
(solo encabezados; es el objeto del área 8) · `README.md` (solo encabezados) ·
`tests/test_conexion.py` (líneas con URL) · `tests/*.py` (solo `grep` de fixtures).

**No abiertos:** `alembic/script.py.mako` ·
`src/territorial/agentes/prompts/*.md` (6) · `scripts/` restantes (16: `cargar_snapshot`,
`cargar_divipola`, `cargar_contexto`, `comparar_*`, `copiar_base`, `dos_pasadas`,
`estimar_costo`, `generar_contrato_ts` —solo ejecutado—, `generar_hojas_revision`,
`medir_prefiltro`, `probar_*`, `verificar_*`) · `tests/test_*.py` (13, solo ejecutados) · `web/tsconfig.json` ·
`web/package-lock.json` · `.gitignore` · `.env.example` (solo nombres) ·
`docs/territorial_data_cruda_v3.json` · `data/*`.

### 0.4 Stack implementado vs. Addendum 02

| Componente | Addendum 02 | Implementado (evidencia) | Estado |
|---|---|---|---|
| Orquestación | D5: LangGraph + checkpointer | Bucle explícito en `ciclo.py`; LangGraph instalado (1.2.11) y **sin uso** en `src/` (`grep` #25 del §0.2 y `ciclo.py:17-21`). Checkpoint = commit por municipio | **Divergente**, declarado en el código |
| Observabilidad | D5: Langfuse Cloud instrumentado por nodo | Tabla propia `traza_agente` escrita por `agentes/persistencia.guardar_traza` (`persistencia.py:169-198`); columna `id_traza_langfuse` nunca poblada; claves Langfuse en `Config` (`config.py:52-54`) sin consumidor | **Divergente** |
| LLM | D6: `OpenAI` con `base_url` a Foundry v1, Responses API; despliegues por agente | `cliente.py:73-76` (cliente), `responses.parse` en `clasificador.py:160` y `correlacionador.py:425`; despliegues `gpt-5.4-mini` / `gpt-5` / `gpt-5` (`config.py:33-35`); techos 16384 (`config.py:39,49`) | Conforme |
| Semi-estructurado | D7: Blob (local: sistema de archivos) | `blob.py` con `AlmacenLocal`/`AlmacenAzure`; `MODO_ALMACEN=local`; prompts y snapshot archivados por hash (`linaje.py`, `snapshot.py:152-154`) | Conforme (modo local) |
| Estructurado | D8: SQLite local → PostgreSQL nube | `DATABASE_URL` (`config.py:64-67`); `normalizar_url` reescribe a psycopg 3 (`sesion.py:42-44`); Neon PostgreSQL 18.6 alcanzable | Conforme |
| Esquema | D8 regla 2: Alembic | 11 migraciones, `alembic check` limpio, `render_as_batch=True` (`env.py:65,83`); guardas `exigir_directa` en ambos caminos (`sesion.py:133`, `env.py:48`) | Conforme |
| Scheduler | D9: ejecución manual en el MVP | Sin `.github/workflows`, sin cron; `correr_ciclo.py` | Conforme con D9 (el PRD §4.3 pedía cron; D9 lo difiere) |
| App web | D5 original: Django+HTMX; **revisado 2026-09-21: Next.js en Vercel** (anexo D5, `M9-fw`) | `web/` Next.js 15.5 con driver HTTP `@neondatabase/serverless` (`db.ts:13-23`); lectura directa de Neon; escrituras vía Server Actions | Conforme con la revisión |
| Dependencias | — | `pyproject.toml` sin lockfile; `psycopg` solo en el extra `azure` aunque es imprescindible para Neon; `web/package-lock.json` sí existe | Nota para el área 10 |

### 0.5 Mapa `grupo de CA → ubicación en código`

| CA | Ubicación | Nota de Preflight |
|---|---|---|
| CA-M1.1 | `ingesta/snapshot.py:143-219` (`cargar`), `_senales_del_municipio` 75-140; ventanas en `config.py:109-119` | Reinterpretado por Add. 01 §5: carga 4 fuentes del snapshot |
| CA-M1.2 | `snapshot.py:89-101` (SECOP: `url`, `fecha`), `110-121` (RSS: `link`, `fecha`); columnas `senal_cruda.url`, `fecha_publicacion` (`modelos.py:226-228`) | Bing sin URL ni fecha por diseño (D1) |
| CA-M1.3 | `snapshot.py:99,119,136` (`hash_dedup`), dedup en memoria `183-209`; **restricción en base** `uq_senal_ciclo_hash` (`modelos.py:235-237`) | Unicidad por (ciclo, hash), no global — pendiente 11.2 |
| CA-M1.4 | **No encontrado** como aislamiento por fuente (no hay fuentes vivas). El análogo por municipio/lote está en `ciclo.py:346-362, 530-555` | Add. 01 §5: «sin validar» |
| CA-M1.5 | `Resumen` de ingesta (`snapshot.py:29-51`, por fuente y ciclo); en el ciclo, `log.info` (`ciclo.py:295-302`) y `corrida_agentes.senales_procesadas` | La ingesta no persiste su resumen en tabla |
| CA-M2.1 | `ResumenMunicipio.reduccion` / `ResumenCiclo.reduccion_global` (`ciclo.py:109-114, 140-144`); denominador auditable vía `descarte` | Solo impreso; no persistido como métrica |
| CA-M2.2 | `clasificador.py:53-79` (esquema), `196-219` (evidencia con url/fecha/fuente); `insight` (`modelos.py:307-367`) | — |
| CA-M2.3 / CA-M2.4 | Prompt `prompts/clasificador_v4.md` (**no abierto**) | Área 2 |
| CA-M2.5 | `clasificador.py:221-231` (`descartes`, `sin_contabilizar`); `persistencia.guardar_descartes` (`201-251`); tabla `descarte` (`modelos.py:370-397`) | — |
| CA-M3.1 | `reglas/validador.py:78-138` (R2–R7), `normalizacion.contiene` (`55-60`) | «Accesible» = bien formada (R4); «localizable» = contra el contenido **ingerido**, nunca la red (`validador.py:149-151`) |
| CA-M3.2 | `ciclo.py:383-391` (`estado_validacion`, `motivo_rechazo`), `persistencia.guardar_insights` (`88-124`) | Rechazados se persisten |
| CA-M3.3 | `ciclo.py:392-393` (conteo en resumen); no hay métrica persistida ni panel | Área 3 y 8 |
| CA-M3.4 | `ciclo.py:407-424` (solo `validado` entra a `para_correlacionar`) | — |
| CA-M4.1 | `correlacionador.py:302-379` (`ensamblar`: ≥2 categorías conocidas, ≥2 insights) | — |
| CA-M4.2 | Esquema `Convergencia.implicacion_inmobiliaria` (`correlacionador.py:133-135`); contexto bandeado `reglas/contexto.py` + `VERSIONES_CON_CONTEXTO` (`correlacionador.py:72`) | — |
| CA-M4.3 | Consulta `ciclo.py:184-196`; entra al prompt en `correlacionador.py:216-233, 269-271` | **Nunca ejercitado**: `calificacion` tiene 0 filas en ambas bases |
| CA-M4.4 | `_unir_evidencia` + `senales_perdidas` (`correlacionador.py:281-299, 372-377`); guarda en `ciclo.py:458-462`; `ids_insight_origen` (`persistencia.py:158`) | — |
| CA-M5.1 | `scoring/ranking.py:311-393`; `ScoreMunicipio.explicar` (`148-169`) | — |
| CA-M5.2 | `factores.py:153-259` (F1–F6, sin TerriData); F6 `241-259`; calificaciones vía `agregacion.py:203-213` | Modificado por D4 |
| CA-M5.3 | `pesos.py:112-144` (`config/pesos.json`), persistidos verbatim en `corrida_scoring.pesos` (`scoring/persistencia.py:104`) | — |
| CA-M5.4 | `ranking.py:74, 189-199`; `config.py:90` (`tope_top=10`) | Desviación `P1` |
| CA-M5.5 | `Aporte`/`factores_que_empujaron` (`ranking.py:77-146`); persistido en `score_municipio.factores` y `valores_crudos` (`scoring/persistencia.py:116-127`) | — |
| CA-M6.1 | `composicion.py:377-378` (`justificacion: None`, `sugerencias: []`) | Sintetizador **no existe** |
| CA-M6.2 | **No encontrado**: solo la columna `informe.infografias` (`modelos.py:649`), nunca poblada | Criterio B |
| CA-M6.3 | `informes/composicion.py` sin llamada a modelo; `reglas/cifras.py` (detección de fugas en `comparar_correlacionador.py`, no abierto) | — |
| CA-M6.4 | `composicion.py:117-152` (`CampoContexto` con fuente y año); evidencia con `url`/`fecha` | — |
| CA-M6.5 | `composicion.py:55, 69` (`AVISO_MVP`, `AVISO_CORTO`); pintado en `ciclo/[id]/page.tsx:235-237` | Desviación `M6-aviso`: solo «MVP» |
| CA-M6.6 | Semilla congelada `composicion.py:316-319, 420-422`; `seleccion.py:104` | — |
| CA-M6.7 | `publicacion.py:128-178`; `informe.estado` + índice único parcial (`modelos.py:660-666`) | **Sin punto de entrada**; sin correo (`11.4/3`) |
| CA-M7.1 | `Panel.tsx:100-204` (`Calificar`: form con 5 botones submit) | Clics: 1 tras identificarse |
| CA-M7.2 | `UniqueConstraint(id_insight, id_gerencia)` (`modelos.py:429`); `consultas.calificacionesDeLaGerencia` solo lo propio (`89-110`) | Bajo la desviación sin auth: criterio C |
| CA-M7.3 | **No encontrado** como estado explícito `sin_respuesta`; es ausencia de fila. Contador «N de M calificados» en `ciclo/[id]/page.tsx:144-146` | Área 4/5 |
| CA-M7.4 | `Panel.tsx:167-199`; `escrituras.comentar` (`53-64`); `acciones.registrarComentario` (`124-133`) | — |
| CA-M7.5 | **No encontrado**: no hay cálculo ni vista de tasa de respuesta | Depende de `/metricas` (404) |
| CA-M7.6 | `escrituras.calificar` upsert `ON CONFLICT` (`43-49`); `acciones.registrarCalificacion` (`73-80`) | — |
| CA-M7.7 | `consultas.cicloEsEditable` (`45-54`) usado en `ciclo/[id]/page.tsx:190, 277` | **Solo en la vista**: `acciones.registrarCalificacion:73-80` no lo comprueba en servidor |
| CA-M9.1 / CA-M9.2 | `acciones.identificarse` (`41-59`), cookie `correo` (`sesion.ts:38-43`), `consultas.gerenciaDelCorreo` (`69-81`) | Desviación `3b`/`M9-acceso` |
| CA-M9.3 | `Nav.tsx:13-23`; rutas existentes: `web/app/ciclo/[id]`, `web/app/priorizados` | **`/historico` y `/metricas` → 404** (ejecutado, §0.2 #19) |
| CA-M9.4 | `ciclo/[id]/page.tsx` + `Panel.tsx`; insights desde `informe.contenido` | `Panel.tsx:69` pinta **solo `evidencia[0]`**; `Panel.tsx:312` pinta **solo 5 insights** en los no pedidos; sin infografías |
| CA-M9.5 | **No encontrado**: no hay ruta ni componente de cadena de trazabilidad; `Panel.tsx:324-326` muestra «señal N» sin enlace | Área 5 |
| CA-M9.6 | `Panel.tsx:251-288` (barras por fuente desde `aportes_por_fuente`) | Desviación `M6-src` |
| CA-M9.7 | `consultas.ciclosPublicados` (`27-37`); `informe` archivado/publicado | **Sin vista Histórico** (404) |
| CA-M9.8 | `tablero.ts:115-155` (derivado de informes publicados, sin alta manual) | — |
| CA-M9.9 | `acciones.cambiarEstado` (`93-121`), `EXIGEN_NOTA` (`tablero.ts:32`), `CambiarEstado.tsx` | Comprobación en servidor: `acciones.ts:108-110` |
| CA-M9.10 | `escrituras.registrarSeguimiento` INSERT (`70-78`); `tablero.historialDe` (`78-88`) | Registra usuario (persona), no gerencia directa; gerencia por JOIN a `usuario` |
| CA-M9.11 | `priorizados/page.tsx:231-237` (ciclos y puestos) | Sin insights acumulados ni calificación promedio |
| CA-M9.12 | `priorizados/page.tsx:85-96` | — |
| CA-M9.13 / CA-M9.14 / CA-M9.15 | **No encontrado**: `Nav.tsx:21-23` enlaza `/metricas` solo a admin, pero la ruta no existe (404); sin CSV | — |
| CA-M9.16 | Escrituras: `escrituras.ts` (3 funciones) + cookie (`acciones.ts:51-56, 63`); lecturas en `consultas.ts`, `tablero.ts` | Área 5 enumera todos los caminos |
| CA-M9.17 | `ciclo/[id]/page.tsx:235-237` (solo en la vista de ciclo) | `/priorizados` no lleva marca |
| CA-M9.18 | `globals.css`; sin media queries | Área 6 |
| CA-M8.1 | Enlaces: `insight.ids_senal`/`evidencia[].id_senal` → `senal_cruda`; `insight.ids_insight_origen`; `insight.id_corrida` → `corrida_agentes.id_ciclo`; `score_municipio.id_corrida`; `informe.id_corrida` + `id_corrida_agentes`; `calificacion.id_insight` | Traza extremo a extremo en el área 4 |
| CA-M8.2 | `traza_agente` (`modelos.py:687-705`) vía `guardar_traza`: input (hash solo clasificador), **sin `hash_output`**, tokens, duración; **sin `id_corrida`** | Langfuse no cableado |
| CA-M8.3 | Agregable por `traza_agente.id_ciclo` + `agente` + `modelo`; tarifas `config/tarifas.json`; `scripts/estimar_costo.py` (no abierto) | Mezcla pasadas del mismo ciclo |
| CA-M8.4 | **No encontrado**: sin checkpointer; reanudar = commit por municipio + volver a lanzar (crea otra corrida) | — |

### 0.6 Desviaciones registradas en `pendientes.md` → dónde viven en código

| Registro | Qué decide | Código | Observación |
|---|---|---|---|
| `P1` | Tope 10, umbral de información en 0 | `config.py:90, 107`; `ranking.py:74, 189-199, 340`; `composicion.py:294-297` | Conforme al registro |
| `M6-aviso` | Etiqueta «MVP» sola; texto largo en payload | `composicion.py:55, 69, 393-394`; `ciclo/[id]/page.tsx:235-237` | Conforme; `/priorizados` sin etiqueta |
| `M6-src` | Nombres de fuente, no códigos | `composicion.py:73-88, 155-224`; `Panel.tsx:251-288`; `page.tsx:40-55` | Conforme |
| `M6-orden` | Línea de fuentes junto al nombre y score | `ciclo/[id]/page.tsx:40-55, 112-114` | Conforme |
| `M6-ctx` | Tres tarjetas TerriData con año | `composicion.py:117-152`; `Panel.tsx:33-66` | Conforme |
| `M9-carga` | Se piden 5 insights en los 3 primeros | `composicion.py:259, 338-343, 379, 416-423` | Conforme |
| `M9-sel` | 3 correlacionados + 1 contratación + 1 prensa, relleno | `seleccion.py:56-60, 89-145` | **El texto de pantalla no coincide**: `Panel.tsx:299-304` dice «los 2 de mayor peso y 3 al azar», criterio que `M9-sel` descartó |
| `M9-fw` | Next.js en Vercel, lee Neon | `web/`, `db.ts` | Conforme |
| `M9-acceso` | Identificación por correo, lista precargada, sin alta | `acciones.ts:41-59`; `consultas.ts:69-81`; `scripts/cargar_usuarios.py` (no abierto) | Conforme en lo leído |
| `A9` | Canónica = la del informe publicado; dos corridas congeladas | `modelos.py:603-684`; `publicacion.py:119-125, 161-177` | Conforme |
| `A10` | Correlacionador v2 con contexto bandeado | `correlacionador.py:66, 72, 256-260`; `reglas/contexto.py` | Conforme |
| `A8` | `hay_dato` vs `disponible` | `factores.py:96-145, 209-215`; `ranking.py:248-250` | Conforme |
| `A7` | F5 dividido por ventana | `factores.py:219-238` | Conforme |
| `B7` | RSS sin prefiltro, lotes propios | `ciclo.py:268-310` | Conforme |
| `A1/4` | F4 a la mitad | `config/pesos.json` (F4 0.15 / 0.09 / 0.09) | Conforme; suma por ciclo = 1,0 (validado por `pesos._validar`) |
| `A5` | Crudos persistidos para escala futura | `score_municipio.valores_crudos` (`scoring/persistencia.py:125-127`) | Conforme |
| `11.4/3` | Sin canal de notificación | Sin código de correo (§0.2 #27) | Conforme |
| `3b` | Sin autenticación | `sesion.ts:1-13` | Conforme; riesgo a evaluar (criterio C) |
| `11.2` | Dedup por ciclo | `uq_senal_ciclo_hash` | Conforme al registro |
| `B4` | Tarifas en JSON | `config/tarifas.json`; **advertencia interna**: cotización de `gpt-5-mini` aplicada a `gpt-5.4-mini` | Área 8 (H5) |
| `A3`, `A2`, `A4`, `A6`, `A11`, `MARCA-tono`, `DS-anexo`, `11.x` | Sin código asociado o fuera de alcance | — | Se citan solo donde condicionen un criterio |

### 0.7 Estado de las dos bases (solo `SELECT`)

Ambas en `b37b4fd6e183 (head)`, 18 tablas. Conteos idénticos en **16 de 18**:
`senal_cruda` 20.030 · `insight` 1.213 · `descarte` 5.731 · `traza_agente` 266 ·
`score_municipio` 432 · `corrida_scoring` 24 · `corrida_agentes` 12 ·
`prompt_version` 2 · `dataset_version` 1 · `municipio` 18 · `ciclo` 3 ·
`entidad_divipola` 1.135 · `contexto_municipal` 1.102 · `calificacion` 0 ·
`seguimiento` 0 · `alembic_version` 1.

| Tabla | SQLite | Neon | Lectura |
|---|---|---|---|
| `informe` | 0 | 4 (ids 2–4 `archivado`, **5 `publicado`**, todos del ciclo 3, corridas 24/10) | La publicación existe **solo en Neon** |
| `usuario` | 0 | 2 (una gerencia distinta: usuarios de prueba) | Lista de autorizados **solo en Neon** |

Consecuencias para las áreas:

- **Área 8:** toda cifra de pipeline en `informe_resultados.md` puede reproducirse
  contra cualquiera de las dos bases; ninguna puede diferir por la base elegida.
- **Ciclo 2 no es publicable**: su única `corrida_agentes` es la 2 y el ciclo 3
  concentra las corridas 9–12; `publicacion.py:89-116` lo detecta.
- Las corridas 11 y 12 del ciclo 3 son de comparación (sin Clasificador), según
  `publicacion.py:66-86`. El informe publicado usa la 10.
- `version_scoring` muestra tres generaciones conviviendo (`v1+migrado`, `v1+…`,
  `v2+…`, `v3+…`), con dos huellas de pesos distintas para los ciclos 2/3
  (`c5acf85d` → `8d8a2954`) y dos para el ciclo 1 (`fc2358e0` → `bbf2789c`).

### 0.8 Pistas del setup, verificadas

| Pista | Verificación | Resultado |
|---|---|---|
| Dos bases en la misma revisión con 18 tablas | §0.2 #7, #8, #11 | **Confirmado**; difieren solo `informe` y `usuario` |
| 8 tablas sin correlato en el PRD | `modelos.py` completo | **Confirmado**: `corrida_agentes`, `corrida_scoring`, `score_municipio`, `descarte`, `prompt_version`, `dataset_version`, `entidad_divipola`, `contexto_municipal`. Además, `municipio` **no** tiene `features_scoring/score_ciclo/ranking_ciclo` (PRD §4.2): se movieron a `score_municipio`; `informe` no tiene `ruta_html` sino `contenido` JSON |
| Langfuse y LangGraph sin uso | §0.2 #25 y `grep` de `langfuse\|langgraph` en `src/` | **Confirmado**: solo `config.py:52-54`, la columna `id_traza_langfuse` y dos comentarios en `ciclo.py` |
| Sin punto de entrada para publicar | `ls scripts/`, `grep publicar(` | **Confirmado**: `publicar()` solo en `informes/publicacion.py`; el informe 5 se publicó con código ad hoc |
| Sin cron; ciclo vía `correr_ciclo.py` | §0.1 | **Confirmado**, coherente con D9 |
| Python sin lockfile | `ls` | **Confirmado**: solo `pyproject.toml`; `web/` sí tiene `package-lock.json` |

### 0.9 Riesgo aceptado por el dueño — credencial de Neon (registro preliminar; formal en el área 10)

- **Hecho:** la contraseña de Neon en `.env` fue expuesta en un chat y **no se
  rotará**, por decisión del dueño.
- **Historial de git (ejecutado, §0.2 #20):** el prefijo `npg_` **no aparece en
  ningún blob de las 66 revisiones** ni `.env` fue rastreado nunca. `neon.tech`
  aparece solo como host de ejemplo (`test_conexion.py:24` usa un endpoint
  ficticio) o en documentación. La exposición es **externa al repositorio**.
- **Permisos de la credencial:** lectura y escritura (`transaction_read_only = off`,
  §0.2 #12); el rol no está restringido.
- **Evidencia del experimento que depende de su integridad:** todo lo que **solo
  existe en Neon** (§0.7): el informe 5 publicado —que fija la corrida canónica
  del ciclo 3 (`A9`)—, la tabla `usuario` —denominador de H2— y **todas las
  futuras `calificacion` y `seguimiento`**, que son la evidencia primaria de H1 y
  H2 y de las métricas 1, 3, 4, 8 y 10 del PRD §6. Los datos de pipeline tienen
  copia íntegra en SQLite local, así que su integridad no depende de Neon; las
  calificaciones **no tendrán copia** salvo que se establezca una.
- Se registra como **Riesgo aceptado**, no como hallazgo a remediar.

### 0.10 Plan de áreas, tamaño estimado e hipótesis a verificar

Tamaño en términos de archivos a leer/releer y comprobaciones. Una sesión por área
salvo que el dueño agrupe. Las «hipótesis» son pistas del Preflight que **aún no
son hallazgos**: cada una se confirma o descarta con evidencia en su área.

| Área | Alcance | Tamaño | Hipótesis a verificar |
|---|---|---|---|
| 1 Ingesta | `ingesta/*` (leídos), `scripts/cargar_*.py` (3, no abiertos), `snapshot` JSON | **Pequeño** | Dedup por constraint (sí) pero por ciclo; CA-M1.4 sin fuentes vivas; resumen de ingesta no persistido (CA-M1.5); `ciclo.n_senales…` nunca escritos |
| 2 Agentes y prompts | `agentes/*` (leídos), 6 prompts (no abiertos), `scripts/comparar_*`, `probar_*` | **Medio** | Prompt vigente = `VERSION_PROMPT` + hash en `prompt_version`; CA-M4.3 real pero nunca ejercitado (0 calificaciones); `contexto_no_verificado` nunca marcado (D1); Clasificador usa `cfg.max_tokens_salida` en vez de `techo_de`; restricción «sin cifras» del prompt v2 sin guarda en la cadena de producción (solo en el script de comparación) |
| 3 Componentes deterministas | `reglas/*`, `scoring/*` (leídos), `tests/test_reglas.py`, `test_scoring.py` | **Medio** | CA-M3.1 «accesible» = sintaxis, «localizable» = contra lo ingerido, no la fuente (bloqueante: decidir Cumple/Parcial); desempate determinista (sí, `ranking.py:365`); tasa de rechazo no persistida como métrica; prefiltro A2 alimenta F1–F3 |
| 4 Contrato de estado y datos + **traza extremo a extremo** | `modelos.py`, 11 migraciones (no abiertas), consultas `SELECT` sobre un insight real del informe 5 | **Grande** | `EstadoCiclo` del PRD no existe como objeto (es la suma de tablas); `seguimiento` sin caminos UPDATE/DELETE en código; `sin_respuesta` implícito; `traza_agente` sin `id_corrida` ni `hash_output` → salto traza↔corrida por tiempo; `informe` sin `ruta_html`; `@validates` no protege de SQL crudo (declarado) |
| 5 Aplicación web | `web/app`, `web/lib` (leídos), rutas GET | **Medio** | `/historico` y `/metricas` 404 (CA-M9.3, 9.7, 9.13–9.15, 7.5); CA-M7.7 solo en UI, no en `registrarCalificacion`; `registrarCalificacion` no comprueba que el insight pertenezca a un informe publicado; solo `evidencia[0]` y 5 insights en no pedidos (CA-M9.4); sin cadena de trazabilidad (CA-M9.5); texto «2 de mayor peso» obsoleto (`M9-sel`); `/priorizados` sin marca MVP (CA-M9.17); atribución declarativa por cookie (criterio C: CA-M7.2, CA-M9.14, H2); `idCiclo`/`divipola` del seguimiento vienen del cliente |
| 6 Conformidad de interfaz | `globals.css`, componentes, `design-system.md` §1–§6 (releer §1, §5, §6) | **Pequeño** | Tokens y tipografía cargados; sin media queries (§6 móvil); estados vacío/error/carga parciales; DS §2.2 pide «sugerencia de acción» y justificación (vacías hasta el Sintetizador) |
| 7 Ejecución y operación | `correr_ciclo.py`, `calcular_scores.py`, `ciclo.py`, `cliente.py`, `estimar_costo.py` (no abierto), `traza_agente` | **Medio** | Sin checkpointer (CA-M8.4); reanudar = nueva corrida; trazas sin `hash_output`/`id_prompt`/`id_dataset`; correlacionador sin `hash_input`; costo por agente agregable pero mezcla pasadas; sin script de publicación; secretos solo en `.env` (nombres verificados) |
| 8 Integridad de la evidencia | `docs/informe_resultados.md` (702 líneas, 69 cifras con %, 8 menciones a corridas), `comparar_pasadas.py`, `dos_pasadas.py`, `estimar_costo.py`, `medir_prefiltro.py`, consultas `SELECT` | **Grande** — la más costosa | Cifras de A6/A11 (19,5 %, 14,1 %), CA-M2.1 (95,2 %/94,9 %), H3 (98 %), H5 (USD 39 / 2.160 con tarifa de `gpt-5-mini` aplicada a `gpt-5.4-mini`), F4 constante, fracción informada 20,10 %/77,80 %: localizar el código o consulta que produce cada una y si es reproducible en `96e10e0` |
| 9 Reglas de `CLAUDE.md` §2 | Reglas 2.1 (1, 2, 3), 2.2, 2.3 (3 corolarios), 2.4 | **Pequeño** | Regla 1: la web emite SQL crudo (lecturas + 3 escrituras) amparado en la precisión del 2026-09-21 y el contrato generado; regla 3: sin JSONB (verificado); 2.4: piso de ruido en `comparar_correlacionador.py` + `test_compuertas.py` |
| 10 Transversal | historial git, dependencias, `tests/*` (13, no abiertos), `ruff`, PII en logs | **Medio** | Riesgo aceptado de la credencial (§0.9); `ruff` 7 errores; sin lockfile Python; `psycopg` en extra opcional; PII de SECOP en `senal_cruda.datos` (D3) y posiblemente en `log.info`; qué afirman de verdad las 272 pruebas; 0 TODO/FIXME |

**Orden sugerido:** 4 (traza extremo a extremo; alimenta el conjunto bloqueante
CA-M8.1) → 3 → 5 → 2 → 8 → 7 → 1 → 9 → 10 → 6. Si el dueño prefiere ir por
severidad potencial, 4, 3 y 5 concentran el conjunto bloqueante.

### 0.11 Decisiones del dueño tras revisar el Preflight (2026-09-22)

Se aplican en todas las áreas y en el cierre:

1. **Asunciones de §0.0 confirmadas** tal como están escritas.
2. **Encuadre: auditoría previa a distribución.** Con 0 calificaciones y 2
   usuarios de prueba, **H1 y H2 se reportan como «no medidas»**, nunca como
   cumplidas o incumplidas. La primera línea del resumen ejecutivo lo dirá.
3. **CA-M3.1 (conjunto bloqueante), decisión del dueño:**
   - «Localizable contra el contenido ingerido» **cumple** bajo el modelo de
     snapshot del Addendum 01, **siempre que** el contenido ingerido sea
     inmutable y esté ligado a su URL y a un hash. La condición se verifica en el
     área 4; si no se cumple, es **Crítico**.
   - «Accesible» verificado solo por sintaxis: **Parcial, severidad Medio.**
4. **Cobertura:** en cada área se leen completos los archivos no abiertos que le
   correspondan antes de concluir (área 4: las 11 migraciones; área 2: los 6
   prompts; área 10: los 13 archivos de tests; scripts donde apliquen), y la tabla
   de §0.3 se actualiza al cerrar cada área.
5. **Área 8:** además de la reproducibilidad, verificar qué afirma
   `informe_resultados.md` sobre H1, H2 y CA-M4.3 dado que no existen
   calificaciones. Si no cabe en una sesión, se divide en 8a y 8b por secciones.
6. **Operación:** al cerrar cada área, commit de `docs/auditoria.md` en
   `audit/2026-09-22` con «docs(audit): área N».

---

*Fin de la Fase 0.*

---

## Área 4 — Contrato de estado y datos, con la traza extremo a extremo

**Cerrada el 2026-09-22.** Archivos leídos completos para esta área, además de
los del Preflight: las 11 migraciones de `alembic/versions/`, `alembic.ini`,
`scripts/cargar_usuarios.py`. Comprobaciones ejecutadas: solo `SELECT` e
inspección de esquema sobre SQLite (y una lectura del `informe` publicado en
Neon); cálculo de SHA-256 sobre el snapshot y los prompts archivados; comparación
de 12 señales contra el snapshot archivado.

### 4.1 Sondas

| Sonda | Respuesta | Evidencia |
|---|---|---|
| ¿El esquema coincide con el modelo de datos del PRD §4.2 tal como lo enmiendan los addenda? | **Parcial** | Ver la tabla 4.2. Las 9 entidades existen; 4 columnas del PRD no (`municipio.features_scoring/score_ciclo/ranking_ciclo` → movidas a `score_municipio`; `seguimiento.responsable` → **ausente**; `informe.ruta_html` → sustituida por `contenido` JSON en `b37b4fd6e183`); 8 tablas añadidas sin correlato en el PRD |
| ¿`seguimiento` es append-only en la práctica (sin caminos UPDATE/DELETE)? | **Sí** | Web: solo `INSERT` (`web/lib/escrituras.ts:70-78`); Python: ningún `Seguimiento(` fuera del modelo (§0.2 #30); ningún `.delete()` salvo `scripts/copiar_base.py:138` (vaciar destino con `--vaciar`, no es camino de app). Filas: 0 en ambas bases |
| ¿`sin_respuesta` se distingue de una calificación baja? | **Parcial** | No existe como estado ni fila: `calificacion` tiene `ck_valor_1_5` (`modelos.py:430`), así que una fila siempre es una opinión 1–5, y la ausencia es la no-respuesta. Es distinguible **por derivación**, pero nada la registra ni la calcula (H-005) |
| ¿Las migraciones están ordenadas? | **Sí** | `alembic history`: 11 revisiones lineales, cada `down_revision` apunta a la anterior; `downgrade()` definido en las 11; FKs en modo batch nombradas (`fk_score_corrida`, `fk_informe_corrida`, `fk_insight_corrida`, `fk_insight_prompt`, `fk_informe_corrida_agentes`); `alembic check` sin diferencias (§0.2 #9). Nota: `41d077a78426` y `cb034d1c967b` migran datos con `sa.text(...)` (SQLAlchemy Core, no SQL de motor) y `b37b4fd6e183:49` añade `contenido NOT NULL` sin default, válido solo porque la tabla estaba vacía (declarado en su docstring) |
| ¿El contrato `EstadoCiclo` del PRD §4.1 existe? | **No** | No hay clase, esquema ni grafo con ese nombre ni con esos campos; el estado de un ciclo es la suma de tablas más los `dataclass` locales `ResumenMunicipio`/`ResumenCiclo` (`ciclo.py:91-181`), que son un resumen de impresión, no el estado. `municipios_objetivo` es un `select(Municipio)` (`ciclo.py:498-501`), no un campo del estado (H-002) |
| **Condición del dueño para CA-M3.1:** ¿el contenido ingerido es inmutable y está ligado a su URL y a un hash? | **Sí, con una salvedad** | (a) **URL:** `senal_cruda.url` no nula en las 19.640 de SECOP y las 336 de RSS; nula en las 54 de Bing por diseño (D1). (b) **Hash:** `dataset_version.hash_sha256 = 2bf78050…fa90` **coincide** con el SHA-256 recalculado del blob archivado y con el de `docs/territorial_data_cruda_v3.json`; los tres prompts archivados coinciden con su fuente. Las 12 señales trazadas son **byte a byte idénticas** (`contenido`, `url` y `datos`) al registro del snapshot anclado. (c) **Inmutabilidad:** ningún camino de código escribe sobre `senal_cruda` tras la ingesta (§0.2 #30 y grep de asignaciones); no hay protección en base. **Salvedad:** el hash por señal (`hash_dedup`) cubre la identidad —`sha256(fuente|divipola|id_externo)`, `snapshot.py:99,119`—, no el contenido, y `uri_blob` está NULL en las 20.030 filas: una alteración de `contenido` solo se detectaría re-derivando desde el snapshot archivado (H-001). **Veredicto: la condición se cumple; no es Crítico** |

### 4.2 Esquema real vs. PRD §4.2 (enmendado por D7, D8 y A9)

| Entidad PRD | Estado | Diferencias (evidencia) |
|---|---|---|
| `señal_cruda` | Cumple, ampliada | `id_fuente` → `fuente` texto; `fecha_captura` → `capturado_en`; `municipio_inferido` → `divipola` FK; añade `datos` JSON, `uri_blob` (nunca poblado), `id_externo`, `id_ciclo`. Único `(id_ciclo, hash_dedup)` (`modelos.py:235-237`; migración `949a8ff9e15d:180`) |
| `insight` | Cumple, ampliada | `id_ciclo` retirado a favor de `id_corrida` (`cb034d1c967b:145-164`); añade `origen`, `version_prompt`, `id_prompt`, `ids_insight_origen`, `por_que_convergen`, `confianza`, `contexto_no_verificado` (nunca `True`, §0.2 #23). `evidencia[]` con `{url, fecha, cita_textual, fuente, id_senal}` |
| `calificacion` | Cumple | `fecha` → `creado_en`; **único `(id_insight, id_gerencia)`** que el PRD presuponía y no escribía (`modelos.py:429`); `ck_valor_1_5` |
| `municipio` | Parcial | Sin `features_scoring`, `score_ciclo`, `ranking_ciclo`: viven en `score_municipio` por corrida (`41d077a78426`). Añade `elic`, `corredores` |
| `ciclo` | **Defecto** | Todas las columnas existen; `n_senales`, `n_insights`, `n_validados`, `n_rechazados`, `costo_tokens` valen **0** y `duracion_seg` **NULL** en los 3 ciclos (SELECT), y nadie las escribe (§0.2 #24). H-003 |
| `traza_agente` | Parcial | Todas las columnas existen; `hash_output` NULL en 266/266, `id_prompt` e `id_dataset` NULL en 266/266, `hash_input` NULL en las 51 del correlacionador; **sin `id_corrida`**. H-006 |
| `usuario` | Cumple | Idéntica al PRD; `correo` único; `ck_rol` |
| `seguimiento` | **Parcial** | Falta `responsable`; la gerencia del cambio no se persiste (H-004). `id_usuario` nullable |
| `informe` | Cumple, enmendada (A9) | `ruta_html` eliminada y `contenido` JSON añadido; `id_corrida` + `id_corrida_agentes` congeladas por `@validates` (`modelos.py:669-684`); índice único parcial `uq_informe_publicado_por_ciclo` **verificado en el esquema real** (inspección). `infografias` siempre `[]` |
| Añadidas | — | `corrida_scoring`, `corrida_agentes`, `score_municipio`, `descarte`, `prompt_version`, `dataset_version`, `entidad_divipola`, `contexto_municipal`: todas nacen en migraciones con FKs y CHECKs; ninguna contradice el PRD, que no las prohíbe (baseline §10, hueco 19) |

Restricciones verificadas por inspección del esquema real (no solo del modelo):
`uq_senal_ciclo_hash`, `uq_calificacion_insight_gerencia`, `uq_descarte_corrida_senal`,
`uq_score_corrida_municipio`, `uq_prompt_agente_version`, `dataset_version.hash_sha256`
único, `usuario.correo` único, `uq_informe_publicado_por_ciclo` (índice único parcial).

### 4.3 Traza extremo a extremo — elemento real del informe publicado

**Elemento:** insight **1092** (consolidado del Correlacionador, `tipo_pedido =
correlacionado`), municipio **Ibagué 73001**, puesto 1 del informe **5**
(publicado 2026-09-22 16:53 UTC, ciclo 3, corridas scoring **24** / agentes **10**).
Elegido como el primer insight pedido de origen `correlacionador` del primer
municipio calificable. Cada salto se ejecutó con `SELECT`.

| # | Salto | Dónde se guarda el vínculo | Cómo se consulta de vuelta | Resultado |
|---|---|---|---|---|
| 1 | informe → insight | `informe.contenido.municipios[].insights[].id` y `informe.id_corrida_agentes` (`composicion.py:324-336`, `publicacion.py:169-175`) | `SELECT … FROM insight WHERE id=1092` | Existe; `id_corrida=10`, `divipola=73001`, `estado=validado`, `id_prompt=2`, `version_prompt=v1`, 12 evidencias, `ids_senal` idénticos a los del payload |
| 2 | insight → corrida de agentes | `insight.id_corrida` FK `fk_insight_corrida` | `SELECT … FROM corrida_agentes WHERE id=10` | `(10, ciclo 3, completa, clasificador v4, correlacionador v1, pipeline p2)` |
| 3 | correlación → insights de origen | `insight.ids_insight_origen = [1087, 1089]` (`persistencia.py:158`) | `SELECT` por cada id | 1087 (`ordenamiento`, 7 señales) y 1089 (`obra_vial`, 5 señales), ambos `validado`, `id_prompt=1` (v4) |
| 4 | validación | `insight.estado_validacion`, `motivo_rechazo` en la misma fila (`ciclo.py:383-391`) | misma fila | `validado`, motivo `None` en los tres |
| 5 | insight → señal | `insight.evidencia[].id_senal`, `insight.ids_senal` | `SELECT … FROM senal_cruda WHERE id=…` para las 12 | Las 12 existen, son de `73001` y del ciclo 3; **las 12 citas se localizan en la señal ingerida** (`normalizacion.contiene`), y `url` y `fecha` de la evidencia coinciden con la fila. La unión de `ids_senal` de 1087 y 1089 es exactamente `ids_senal` de 1092 (CA-M4.4) |
| 6 | señal → fuente archivada | `ciclo.id_dataset` → `dataset_version.hash_sha256`; blob `raw/territorial_data_cruda_v3.json` | Recalcular SHA-256; buscar por `id_externo` (SECOP) y `link` (RSS) en el snapshot | Hash **idéntico** en blob, en `docs/` y en la tabla; las 12 señales son **byte a byte** el registro del snapshot (`contenido`, `url`, `datos`) |
| 7 | insight → score | **No hay vínculo por fila**: el score lee `senal_cruda`, no insights (`agregacion.py:176-188`); el vínculo es (`divipola`, ciclo) a través de las dos corridas que el informe congela | `SELECT … FROM score_municipio WHERE id_corrida=24 AND divipola='73001'` | `score 0.855951651592403` **igual al payload**, `ranking 1 == puesto 1`, `3/239 días`, `sin_cobertura`; aportes persistidos F4 0,4478 + F5 0,4081, F1/F2/F3/F6 sin cobertura; `fraccion_informada 0,200976` igual al payload; `corrida_scoring 24 = v3+8d8a2954` con pesos verbatim |
| 8 | insight → calificación | `calificacion.id_insight` FK + único `(id_insight, id_gerencia)`; consulta `consultas.calificacionesDeLaGerencia` (`web/lib/consultas.ts:93-100`) une `calificacion → insight → corrida_agentes.id_ciclo` | `SELECT count(*) FROM calificacion WHERE id_insight=1092` | **0 filas** (0 en toda la tabla, ambas bases). Vínculo verificado **por estructura**, no por dato |
| 9 | municipio → seguimiento | `seguimiento.divipola` + `id_ciclo_origen`; el tablero deriva los priorizados de `informe.contenido` (`tablero.ts:115-155`) | `SELECT count(*) FROM seguimiento` | **0 filas**. Derivación verificada: el top 3 del informe 5 (73001, 63001, 25286) es lo que el tablero listaría como `priorizado` |
| 10 | agente → traza | `traza_agente(id_ciclo, agente, tokens, duracion)` **sin `id_corrida`** | `SELECT … WHERE id_ciclo=3 GROUP BY agente` | 71 trazas del clasificador (16:01:02–16:32:49) y 18 del correlacionador; las corridas **9** (16:00:41) y **10** (16:02:54) del mismo ciclo se **solapan en el tiempo**, así que no se puede decir con certeza qué trazas son de la corrida publicada; las corridas 11 y 12 (21:33) **no tienen ninguna traza** |

**Veredicto CA-M8.1:** la cadena `señal → insight → validación → correlación →
score → informe` es **reconstruible desde datos persistidos y se reconstruyó** sobre
un elemento real, hasta el snapshot anclado por hash. Los saltos a `calificacion`
y `seguimiento` están definidos por FK y por consulta, pero **no pueden
ejercitarse con datos** hasta la ventana de calificación: quedan como *verificados
por estructura*. El salto `agente → traza` (CA-M8.2, no CA-M8.1) **no** es
reconstruible con certeza cuando hay dos corridas del mismo ciclo (H-006).

Dos notas para otras áreas que salen de la traza:

- El informe publicado se compone sobre la corrida 10, que corrió el
  **Correlacionador v1** (`version_correlacionador='v1'`, `id_prompt=2`), no el v2
  que `CLAUDE.md` declara vigente desde el 2026-09-21. No es un defecto de datos
  —la corrida es anterior a la promoción—, pero **lo que las gerencias leerán es
  salida de v1**. Área 2 y área 8.
- Las corridas 1, 2, 4, 11 y 12 tienen todos sus insights con `id_prompt NULL`
  (127 filas). Las tres primeras son anteriores a `a6ac249fcec9` (declarado en la
  migración); **11 y 12 son las corridas de comparación** y no registraron linaje
  de prompt (D7). Área 2.

### 4.4 Hallazgos

**H-001 · Medio · Riesgo · Confianza Alta · Área 4 · CA-M3.1 (condición del dueño), D7**
*El contenido ingerido está anclado por hash a nivel de dataset, no de señal.*
`hash_dedup` es `sha256(fuente|divipola|id_externo)` y no cubre `contenido`:

```
src/territorial/ingesta/snapshot.py:99
    "hash_dedup": _hash("SECOP II", divipola, reg.get("id")),
src/territorial/ingesta/snapshot.py:119
    "hash_dedup": _hash("RSS", divipola, noticia.get("link")),
```

`senal_cruda.uri_blob` está NULL en las 20.030 filas (SELECT). La inmutabilidad
la garantiza la ausencia de código que escriba sobre `senal_cruda` (§0.2 #30) y el
snapshot archivado con `dataset_version.hash_sha256` verificado (§4.1). *Escenario:*
una fila de `senal_cruda.contenido` modificada por SQL directo con la credencial de
Neon —que tiene escritura— no dispararía ninguna comprobación; la cita seguiría
«localizándose» en un contenido alterado, y solo una re-derivación desde el
snapshot lo detectaría. *Por qué no es Crítico:* la condición del dueño se cumple
—contenido reproducible byte a byte desde un raw anclado por hash y ligado a su
URL—; lo que falta es detección por fila. Ocurrencias: `snapshot.py:99, 119, 136`;
`modelos.py:229-231`.

**H-002 · Medio · Brecha · Confianza Alta · Área 4 · PRD §4.1, §3.2**
*El contrato de estado `EstadoCiclo` no existe.* El PRD lo declara «el activo más
importante del MVP» y el punto de inserción del orquestador. No hay clase, esquema
ni grafo: el estado de un ciclo es la suma de tablas, y `municipios_objetivo` es una
consulta:

```
src/territorial/ciclo.py:498-501
    consulta = select(Municipio).order_by(Municipio.divipola)
    if solo:
        consulta = consulta.where(Municipio.divipola.in_(solo))
    municipios = sesion_bd.scalars(consulta).all()
```

`ciclo.py:8-11` lo reconoce: «Cuando se cablee LangGraph (`grafo/`, CA-M8.4) este
módulo es lo que se convierte en el grafo». *Escenario:* la Fase 0 quiere insertar
el orquestador «sin cambios en los agentes aguas abajo» (PRD §4.1) y no hay contrato
contra el que verificarlo. No afecta a H1–H5; afecta a la promesa de escalabilidad
de §3.2.

**H-003 · Medio · Defecto · Confianza Alta · Área 4 · PRD §4.2 (`ciclo`)**
*Los contadores de `ciclo` existen, son NOT NULL y nadie los escribe.* SELECT:

```
(1, '2025-09-01', '2025-10-22', 1, 0, 0, 0, 0, 0.0, None)
(2, '2025-10-22', '2026-01-14', 1, 0, 0, 0, 0, 0.0, None)
(3, '2026-01-14', '2026-09-10', 1, 0, 0, 0, 0, 0.0, None)
```

con 6.419 / 6.669 / 6.548 señales SECOP por ciclo según el Addendum 01 D2. Ningún
módulo asigna `n_senales`, `n_insights`, `n_validados`, `n_rechazados`,
`costo_tokens` ni `duracion_seg` (§0.2 #24). *Escenario:* cualquier consulta externa
o panel que lea `ciclo` reporta cero señales y cero costo para los tres ciclos; es
dato persistido falso, no ausente. Los valores reales existen en `corrida_agentes`
y `traza_agente`, pero el PRD los ubica en `ciclo`.

**H-004 · Medio · Brecha · Confianza Alta · Área 4 · PRD §4.2 (`seguimiento.responsable`), CA-M9.10**
*`seguimiento` no persiste la gerencia del cambio ni tiene `responsable`.*
`modelos.py:582-600` define `divipola, id_ciclo_origen, estado, nota, id_usuario,
fecha_cambio`; la gerencia se deriva en consulta:

```
web/lib/tablero.ts:80-83
    SELECT s.id, s.estado, s.nota, s.fecha_cambio, u.nombre AS usuario,
           u.id_gerencia AS gerencia
      FROM seguimiento s
      LEFT JOIN usuario u ON u.id = s.id_usuario
```

CA-M9.10 exige «registra usuario, gerencia, fecha y nota». *Escenario:*
`scripts/cargar_usuarios.py:116-120` actualiza `usuario.id_gerencia` in situ; un
usuario que cambie de gerencia entre ciclos reescribe retroactivamente la gerencia
de todo su historial de seguimiento. `id_usuario` es además nullable.

**H-005 · Alto · Riesgo · Confianza Media · Área 4 · CA-M7.3, H2**
*`sin_respuesta` no se registra y su denominador no está congelado por ciclo.* La
no-respuesta es la ausencia de fila en `calificacion` (correcto para distinguirla de
una nota baja: `ck_valor_1_5`), pero el denominador —qué gerencias estaban
autorizadas cuando se publicó cada informe— vive solo en el estado **actual** de
`usuario`:

```
web/lib/consultas.ts:72-77
    SELECT id, id_gerencia, nombre, rol
      FROM usuario
     WHERE lower(correo) = lower(${correo})
       AND activo
```

y `cargar_usuarios.py:116-120` modifica filas in situ (`activo`, `id_gerencia`,
`rol`). `informe.contenido` congela los insights pedidos y la semilla
(`composicion.py:416-423`) pero **no la lista de gerencias**. *Escenario:* se
sustituyen los 2 usuarios de prueba por los 7 reales tras publicar el ciclo 3, o
una gerencia se desactiva en el ciclo 2: la tasa de respuesta del ciclo 3 se
recalcula con otro denominador y H2 deja de ser reproducible. Alto porque
compromete la medición de H2. Confianza Media: estático, y H2 aún no se ha medido.
Ocurrencia relacionada: ningún código calcula la tasa (CA-M7.5, área 5).

**H-006 · Medio · Brecha · Confianza Alta · Área 4 · CA-M8.2, PRD §4.2 (`traza_agente.output_hash`)**
*`traza_agente` no enlaza con la corrida y deja vacíos `hash_output`, `id_prompt`
e `id_dataset`.* SELECT sobre 266 trazas: `hash_output` NULL 266, `id_prompt` NULL
266, `id_dataset` NULL 266, `hash_input` NULL en las 51 del correlacionador aunque
`hash_entrada` existe (`correlacionador.py:470-473`) y no se llama:

```
src/territorial/ciclo.py:443-452
        guardar_traza(
            sesion_bd,
            id_ciclo=id_ciclo,
            agente="correlacionador",
            modelo=despliegue_de("correlacionador", cfg),
            tokens_entrada=corr.tokens_entrada,
            tokens_salida=corr.tokens_salida,
            tokens_cache_lectura=corr.tokens_cache_lectura,
            duracion_ms=corr.duracion_ms,
        )
```

*Escenario verificado:* en el ciclo 3 las corridas 9 y 10 se solapan en el tiempo
(9 abre 16:00:41, 10 abre 16:02:54, trazas del clasificador de 16:01:02 a 16:32:49):
no se puede atribuir con certeza qué trazas —y qué tokens— son de la corrida
publicada. Las corridas 11 y 12 no tienen traza alguna, así que su costo no está en
la tabla. Afecta a CA-M8.3 por corrida y a la reproducibilidad del costo de H5 por
pasada (área 8); no rompe CA-M8.1, que no incluye la traza.

**H-007 · Medio · Brecha · Confianza Alta · Área 4 · CA-M3.1 («accesible») — decisión del dueño**
*«URL accesible» se verifica solo por sintaxis.*

```
src/territorial/reglas/validador.py:68-75
def _url_valida(valor) -> bool:
    ...
    return p.scheme.lower() in ESQUEMAS_VALIDOS and bool(p.netloc)
```

y `validador.py:149-151`: «El validador nunca consulta la red». Bajo el modelo de
snapshot (Addendum 01) la URL no se resuelve en ningún punto de la cadena. **Por
decisión del dueño (§0.11.3): Parcial, severidad Medio.** La otra mitad del criterio
—«cita localizable»— **cumple**, verificada la condición de inmutabilidad y anclaje
(§4.1) y ejercitada sobre 12 evidencias reales (§4.3).

**H-008 · Bajo · Riesgo · Confianza Alta · Área 4 · PRD §6 (métrica «tiempo hasta la primera calificación»)**
*Una calificación corregida no queda fechada.* El upsert conserva `creado_en` y no
hay `actualizado_en`:

```
web/lib/escrituras.ts:46-48
    ON CONFLICT (id_insight, id_gerencia)
      DO UPDATE SET valor = EXCLUDED.valor,
                    comentario = COALESCE(EXCLUDED.comentario, calificacion.comentario)
```

*Escenario:* una gerencia califica 2 el día 1 y corrige a 5 el día 10; la fila dice
5 con fecha del día 1. La métrica de §6 sobrevive (mide la primera); se pierde la
trayectoria de la opinión, que RN-03 y el análisis de acuerdo entre gerencias
podrían necesitar.

### 4.5 Estado de los CA del área

| CA | Estado | Base |
|---|---|---|
| CA-M1.3 | **Desviación autorizada** (11.2) | Dedup por restricción real `uq_senal_ciclo_hash`, alcance por ciclo |
| CA-M2.5 | **Cumple** | Tabla `descarte` con `motivo` y `declarado`; 5.731 filas; FK a señal y corrida |
| CA-M3.1 | **Parcial (Medio)** — decisión del dueño | «Localizable»: Cumple (condición verificada, 12/12 citas); «accesible»: solo sintaxis (H-007) |
| CA-M3.2 | **Cumple** | Rechazados persistidos con motivo: 4 en la corrida 10, 27 en el total |
| CA-M4.4 | **Cumple** | Unión de `ids_senal` verificada en el consolidado 1092; `ids_insight_origen` persistido |
| CA-M5.3 | **Cumple** | Pesos externos en `config/pesos.json` y persistidos verbatim en `corrida_scoring.pesos` |
| CA-M5.5 | **Cumple** | `score_municipio.factores.aportes` y `valores_crudos` por municipio y corrida |
| CA-M7.2 | **Cumple (estructura)** | Único `(id_insight, id_gerencia)` en el esquema real; la independencia bajo la desviación sin autenticación se juzga en el área 5 |
| CA-M7.3 | **Parcial** | Derivable por ausencia de fila; no registrado; denominador no congelado (H-005) |
| CA-M8.1 | **Cumple** | Cadena reconstruida sobre un elemento real hasta el snapshot anclado; calificación y seguimiento verificados por estructura, sin datos |
| CA-M8.2 | **Parcial** | Tokens y duración por agente; sin `hash_output`, sin `id_corrida`, `hash_input` solo en el clasificador (H-006) |
| CA-M9.10 | **Parcial** | Usuario, fecha y nota persistidos; gerencia derivada en consulta (H-004) |
| CA-M9.16 (nivel de esquema) | **Cumple (provisional)** | Las únicas escrituras de la app son `calificacion` y `seguimiento`; la enumeración completa de caminos es del área 5 |

### 4.6 No verificable en esta área

- Saltos `insight → calificacion` y `municipio → seguimiento` con datos reales:
  0 filas. Artefacto necesario: al menos una calificación y un cambio de estado
  registrados desde la app durante la ventana.
- Comportamiento del índice único parcial en PostgreSQL bajo concurrencia (dos
  `publicar()` simultáneos): no se ejecuta nada que escriba. Artefacto: prueba de
  integración contra una rama de Neon.

*Fin del área 4.*
