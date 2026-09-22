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
*Añadidos al cerrar el área 3:* `scripts/comparar_correlacionador.py` ·
`scripts/medir_prefiltro.py` · `scripts/probar_correlacionador.py` ·
`tests/test_reglas.py` · `tests/test_cifras.py` · `tests/test_compuertas.py` ·
`tests/test_scoring.py`.
*Añadidos al cerrar el área 2:* los 6 prompts `src/territorial/agentes/prompts/*.md`
· `scripts/probar_clasificador.py` · `scripts/comparar_prompts.py` ·
`scripts/dos_pasadas.py` · `scripts/comparar_pasadas.py`.
*Añadidos al cerrar el área 8:* `scripts/estimar_costo.py` ·
`scripts/generar_hojas_revision.py`. *Área 7:* sin archivos nuevos.
*Añadidos en la sesión 2 (áreas 1, 6, 10):* `scripts/cargar_snapshot.py` ·
`scripts/cargar_divipola.py` · `scripts/cargar_contexto.py` · `docs/design-system.md`
(completo) · los 9 archivos de tests restantes (`test_conexion`, `test_contrato`,
`test_seleccion`, `test_nomenclator`, `test_contexto`, `test_correlacionador`,
`test_corridas`, `test_informes`, `test_persistencia`). **Quedan sin abrir solo**
`alembic/script.py.mako`, `web/tsconfig.json`, `web/package-lock.json` y
`.gitignore` (consultado vía `git check-ignore`).

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
7. **Etiqueta «Bloquea distribución»** (añadida tras revisar el área 5,
   independiente de la severidad): marca lo que **debe resolverse antes de enviar
   el informe a las 7 gerencias o de cargar sus usuarios**, porque después el daño
   a los datos no es reparable. Se aplica a **H-005, H-009, H-012, H-013 y a la
   pregunta P-1**, y a lo que las áreas siguientes encuentren con la misma
   propiedad. En el cierre, el plan de remediación empieza por una fase **F0
   «Prerrequisitos de distribución»** con exactamente esos puntos.
8. **Etiqueta «Bloquea decisión go/no-go»** (añadida tras revisar el área 8a,
   independiente de la severidad y de la anterior): marca lo que impide usar
   `docs/informe_resultados.md` ante la compuerta de la semana 8 mientras siga
   abierto. Se aplica a **H-027, H-028 y H-030**. En el cierre, el plan incluye
   una fase **F0b «Prerrequisitos de la decisión»** con esos puntos.

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

**H-005 · Alto · Riesgo · Confianza Media · Área 4 · CA-M7.3, H2 · 🔒 BLOQUEA DISTRIBUCIÓN — resolver antes de cargar los 7 usuarios reales (decisión del dueño, §4.9 y §0.11.7)**
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

**H-006 · Alto (reevaluado en §4.8; originalmente Medio) · Riesgo · Confianza Alta · Área 4 · CA-M8.2, CA-M8.3, H5, PRD §4.2 (`traza_agente.output_hash`)**
*El linaje de ejecución no es atribuible ni completo: `traza_agente` no enlaza con
la corrida y deja vacíos `hash_output`, `id_prompt` e `id_dataset`.* (El linaje de
**datos** cumple; ver §4.8.) SELECT sobre 266 trazas: `hash_output` NULL 266, `id_prompt` NULL
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

### 4.7 Ampliación (2026-09-22): la traza sobre los 241 insights del informe 5

A petición del dueño, la verificación de §4.3 se ejecutó —solo con `SELECT`—
sobre **todos** los insights del informe publicado: 241 insights en 10
municipios, 933 evidencias. Por cada insight se comprobó: existe en la base con
`id_corrida = 10`, el municipio y `estado_validacion = validado` del payload;
`ids_senal` y `evidencia` del payload son idénticos a la fila; si es consolidado,
sus `ids_insight_origen` existen, son del Clasificador, están validados y la unión
de sus `ids_senal` es exactamente la del consolidado; cada evidencia apunta a una
señal existente del mismo municipio y ciclo, con `url` y `fecha` iguales a la fila
y **cita localizable** en el contenido ingerido; cada señal es **byte a byte** el
registro del snapshot anclado por hash; y el `score`/`ranking` del municipio en
la corrida 24 coincide con el payload.

| Puesto | Municipio | Insights | Sin fallo | Citas loc./tot. | Snapshot | Score = payload |
|---|---|---|---|---|---|---|
| 1 | Ibagué 73001 | 8 | 8 | 46/46 | 8/8 | sí |
| 2 | Armenia 63001 | 8 | 8 | 11/11 | 8/8 | sí |
| 3 | Funza 25286 | 49 | 49 | 183/183 | 49/49 | sí |
| 4 | Barranquilla 08001 | 12 | 12 | 41/41 | 12/12 | sí |
| 5 | Buenaventura 76109 | 38 | 38 | 192/192 | 38/38 | sí |
| 6 | Facatativá 25269 | 30 | 30 | 151/151 | 30/30 | sí |
| 7 | Turbo 05837 | 21 | 21 | 72/72 | 21/21 | sí |
| 8 | Mosquera 25473 | 11 | 11 | 42/42 | 11/11 | sí |
| 9 | Dosquebradas 66170 | 20 | 20 | 84/84 | 20/20 | sí |
| 10 | La Dorada 17380 | 44 | 44 | 111/111 | 44/44 | sí |
| **Total** | | **241** | **241** | **933/933** | **241/241** | **10/10** |

**Fallos: ninguno.** Los 23 consolidados (tipo C) superan los 7 saltos; los 218
directos (tipo D) superan los 6. La tabla insight a insight está en el Anexo A.

**CA-M8.1 pasa de «Cumple» a «Cumple, verificado sobre el 100 % del informe
publicado»** para la cadena `señal → insight → validación → correlación → score →
informe`. Los saltos a `calificacion` y `seguimiento` siguen verificados solo por
estructura (0 filas).

### 4.8 Reevaluación de H-006 (a petición del dueño)

Se separan dos linajes que el hallazgo original mezclaba:

- **Linaje de datos** (qué señal produjo qué insight, qué corrida produjo qué
  score, qué corridas congela el informe): **Cumple**, verificado en §4.7 sobre
  241/241 insights.
- **Linaje de ejecución** (qué llamada al modelo, con qué tokens, produjo cada
  corrida): **Parcial**, y es lo que H-006 describe.

Evidencia adicional ejecutada (`SELECT`):

| Fuente | Ciclo 3 | Lectura |
|---|---|---|
| `corrida_agentes.tokens_entrada/salida` | corrida 9: 13.339 / 6.140 · corrida 10: 541.852 / 249.767 · corridas 11 y 12: **0 / 0** | El total **por corrida** existe para 9 y 10 (`ciclo.py:557-560`); las corridas de comparación 11 y 12 **no registraron su gasto en ninguna tabla** |
| `traza_agente` por agente | clasificador 507.513 / 152.474 · correlacionador 47.678 / 103.433 (suma 555.191 / 255.907) | La suma **coincide exactamente** con corridas 9 + 10 → las trazas cubren 9 y 10 y **ninguna** de 11 y 12 |
| Atribución por corrida y agente | 3 trazas anteriores a la apertura de la corrida 10; el resto se solapa | El desglose **por agente de la corrida publicada** no es determinable con certeza: exige restar la corrida 9, cuyo reparto por agente no está registrado |
| Ciclo 2 | `corrida_agentes` suma 0 / 0 (migrada); `traza_agente` 64.414 / 17.292 | Las dos fuentes de costo **se contradicen** para el ciclo 2 |

Consecuencia para H5: el costo **por ciclo** derivado de `traza_agente` es
incompleto (omite el control v1-vs-v1, que es gasto real del experimento y la
base de A11), el costo **por agente y corrida** no es atribuible cuando dos
corridas comparten ciclo y hora, y las dos tablas que registran gasto discrepan en
el ciclo 2. Eso compromete la medición de H5 tal como la define el PRD §1 («tokens
y costo por ciclo») y CA-M8.3 («desglosado por agente»).

**H-006 sube de Medio a Alto**, categoría Riesgo, confianza Alta (ejecutado). El
texto del hallazgo en §4.4 queda enmendado por esta sección; el linaje de datos
no está en cuestión.

### 4.9 Enmienda a H-005

**H-005 debe resolverse antes de cargar los 7 usuarios reales** en `usuario`, por
decisión del dueño: mientras la lista de gerencias autorizadas por ciclo no quede
congelada, la carga de los usuarios reales sobre un ciclo ya publicado altera el
denominador de H2 de ese ciclo. Prioridad: **previa a distribución**.

### Anexo A — Traza insight a insight del informe 5

Tipo `C` = consolidado del Correlacionador (7 saltos), `D` = directo del
Clasificador (6 saltos). «Citas» = evidencias cuya cita se localiza en la señal
ingerida / evidencias totales. «Score» = el score y el ranking del municipio en la
corrida 24 coinciden con el payload.

| Insight | Muni | Tipo | Saltos | Citas loc./tot. | Score | Fallos |
|---|---|---|---|---|---|---|
| 1087 | 73001 | D | 6/6 | 7/7 | sí | — |
| 1088 | 73001 | D | 6/6 | 1/1 | sí | — |
| 1089 | 73001 | D | 6/6 | 5/5 | sí | — |
| 1090 | 73001 | D | 6/6 | 2/2 | sí | — |
| 1091 | 73001 | D | 6/6 | 2/2 | sí | — |
| 1092 | 73001 | C | 7/7 | 12/12 | sí | — |
| 1093 | 73001 | C | 7/7 | 8/8 | sí | — |
| 1094 | 73001 | C | 7/7 | 9/9 | sí | — |
| 1047 | 63001 | D | 6/6 | 1/1 | sí | — |
| 1048 | 63001 | D | 6/6 | 1/1 | sí | — |
| 1049 | 63001 | D | 6/6 | 1/1 | sí | — |
| 1050 | 63001 | D | 6/6 | 1/1 | sí | — |
| 1051 | 63001 | D | 6/6 | 1/1 | sí | — |
| 1052 | 63001 | D | 6/6 | 1/1 | sí | — |
| 1053 | 63001 | D | 6/6 | 1/1 | sí | — |
| 1054 | 63001 | C | 7/7 | 4/4 | sí | — |
| 969 | 25286 | D | 6/6 | 4/4 | sí | — |
| 967 | 25286 | D | 6/6 | 3/3 | sí | — |
| 968 | 25286 | D | 6/6 | 1/1 | sí | — |
| 970 | 25286 | D | 6/6 | 2/2 | sí | — |
| 971 | 25286 | D | 6/6 | 1/1 | sí | — |
| 972 | 25286 | D | 6/6 | 6/6 | sí | — |
| 973 | 25286 | D | 6/6 | 8/8 | sí | — |
| 974 | 25286 | D | 6/6 | 3/3 | sí | — |
| 975 | 25286 | D | 6/6 | 4/4 | sí | — |
| 976 | 25286 | D | 6/6 | 2/2 | sí | — |
| 977 | 25286 | D | 6/6 | 1/1 | sí | — |
| 978 | 25286 | D | 6/6 | 2/2 | sí | — |
| 979 | 25286 | D | 6/6 | 8/8 | sí | — |
| 980 | 25286 | D | 6/6 | 1/1 | sí | — |
| 981 | 25286 | D | 6/6 | 1/1 | sí | — |
| 982 | 25286 | D | 6/6 | 3/3 | sí | — |
| 1003 | 25286 | D | 6/6 | 4/4 | sí | — |
| 983 | 25286 | D | 6/6 | 3/3 | sí | — |
| 984 | 25286 | D | 6/6 | 1/1 | sí | — |
| 985 | 25286 | D | 6/6 | 1/1 | sí | — |
| 986 | 25286 | D | 6/6 | 3/3 | sí | — |
| 987 | 25286 | D | 6/6 | 5/5 | sí | — |
| 988 | 25286 | D | 6/6 | 2/2 | sí | — |
| 989 | 25286 | D | 6/6 | 4/4 | sí | — |
| 990 | 25286 | D | 6/6 | 2/2 | sí | — |
| 992 | 25286 | D | 6/6 | 3/3 | sí | — |
| 993 | 25286 | D | 6/6 | 4/4 | sí | — |
| 994 | 25286 | D | 6/6 | 4/4 | sí | — |
| 995 | 25286 | D | 6/6 | 22/22 | sí | — |
| 996 | 25286 | D | 6/6 | 4/4 | sí | — |
| 997 | 25286 | D | 6/6 | 4/4 | sí | — |
| 998 | 25286 | D | 6/6 | 3/3 | sí | — |
| 999 | 25286 | D | 6/6 | 5/5 | sí | — |
| 1000 | 25286 | D | 6/6 | 6/6 | sí | — |
| 1001 | 25286 | D | 6/6 | 2/2 | sí | — |
| 1002 | 25286 | D | 6/6 | 2/2 | sí | — |
| 1005 | 25286 | D | 6/6 | 8/8 | sí | — |
| 1006 | 25286 | D | 6/6 | 1/1 | sí | — |
| 1007 | 25286 | D | 6/6 | 3/3 | sí | — |
| 1008 | 25286 | D | 6/6 | 1/1 | sí | — |
| 1009 | 25286 | D | 6/6 | 3/3 | sí | — |
| 1010 | 25286 | D | 6/6 | 2/2 | sí | — |
| 1011 | 25286 | D | 6/6 | 3/3 | sí | — |
| 1012 | 25286 | D | 6/6 | 1/1 | sí | — |
| 1013 | 25286 | D | 6/6 | 2/2 | sí | — |
| 1014 | 25286 | D | 6/6 | 1/1 | sí | — |
| 1015 | 25286 | C | 7/7 | 6/6 | sí | — |
| 1016 | 25286 | C | 7/7 | 12/12 | sí | — |
| 1017 | 25286 | C | 7/7 | 6/6 | sí | — |
| 834 | 08001 | D | 6/6 | 11/11 | sí | — |
| 827 | 08001 | D | 6/6 | 3/3 | sí | — |
| 828 | 08001 | D | 6/6 | 1/1 | sí | — |
| 829 | 08001 | D | 6/6 | 5/5 | sí | — |
| 830 | 08001 | D | 6/6 | 2/2 | sí | — |
| 831 | 08001 | D | 6/6 | 1/1 | sí | — |
| 832 | 08001 | D | 6/6 | 5/5 | sí | — |
| 833 | 08001 | D | 6/6 | 1/1 | sí | — |
| 835 | 08001 | D | 6/6 | 2/2 | sí | — |
| 836 | 08001 | D | 6/6 | 1/1 | sí | — |
| 837 | 08001 | C | 7/7 | 7/7 | sí | — |
| 838 | 08001 | C | 7/7 | 2/2 | sí | — |
| 1097 | 76109 | D | 6/6 | 1/1 | sí | — |
| 1098 | 76109 | D | 6/6 | 1/1 | sí | — |
| 1113 | 76109 | D | 6/6 | 15/15 | sí | — |
| 1114 | 76109 | D | 6/6 | 9/9 | sí | — |
| 1095 | 76109 | D | 6/6 | 4/4 | sí | — |
| 1096 | 76109 | D | 6/6 | 2/2 | sí | — |
| 1099 | 76109 | D | 6/6 | 3/3 | sí | — |
| 1100 | 76109 | D | 6/6 | 1/1 | sí | — |
| 1101 | 76109 | D | 6/6 | 1/1 | sí | — |
| 1102 | 76109 | D | 6/6 | 1/1 | sí | — |
| 1103 | 76109 | D | 6/6 | 1/1 | sí | — |
| 1104 | 76109 | D | 6/6 | 2/2 | sí | — |
| 1105 | 76109 | D | 6/6 | 1/1 | sí | — |
| 1106 | 76109 | D | 6/6 | 2/2 | sí | — |
| 1107 | 76109 | D | 6/6 | 4/4 | sí | — |
| 1108 | 76109 | D | 6/6 | 1/1 | sí | — |
| 1109 | 76109 | D | 6/6 | 14/14 | sí | — |
| 1110 | 76109 | D | 6/6 | 2/2 | sí | — |
| 1111 | 76109 | D | 6/6 | 5/5 | sí | — |
| 1112 | 76109 | D | 6/6 | 5/5 | sí | — |
| 1115 | 76109 | D | 6/6 | 1/1 | sí | — |
| 1116 | 76109 | D | 6/6 | 7/7 | sí | — |
| 1117 | 76109 | D | 6/6 | 16/16 | sí | — |
| 1118 | 76109 | D | 6/6 | 2/2 | sí | — |
| 1119 | 76109 | D | 6/6 | 3/3 | sí | — |
| 1120 | 76109 | D | 6/6 | 2/2 | sí | — |
| 1121 | 76109 | D | 6/6 | 5/5 | sí | — |
| 1122 | 76109 | D | 6/6 | 28/28 | sí | — |
| 1123 | 76109 | D | 6/6 | 9/9 | sí | — |
| 1124 | 76109 | D | 6/6 | 5/5 | sí | — |
| 1125 | 76109 | D | 6/6 | 14/14 | sí | — |
| 1126 | 76109 | D | 6/6 | 4/4 | sí | — |
| 1127 | 76109 | D | 6/6 | 3/3 | sí | — |
| 1128 | 76109 | D | 6/6 | 1/1 | sí | — |
| 1129 | 76109 | D | 6/6 | 2/2 | sí | — |
| 1130 | 76109 | C | 7/7 | 5/5 | sí | — |
| 1131 | 76109 | C | 7/7 | 6/6 | sí | — |
| 1132 | 76109 | C | 7/7 | 4/4 | sí | — |
| 936 | 25269 | D | 6/6 | 2/2 | sí | — |
| 937 | 25269 | D | 6/6 | 4/4 | sí | — |
| 938 | 25269 | D | 6/6 | 6/6 | sí | — |
| 939 | 25269 | D | 6/6 | 2/2 | sí | — |
| 940 | 25269 | D | 6/6 | 1/1 | sí | — |
| 941 | 25269 | D | 6/6 | 3/3 | sí | — |
| 942 | 25269 | D | 6/6 | 1/1 | sí | — |
| 943 | 25269 | D | 6/6 | 2/2 | sí | — |
| 944 | 25269 | D | 6/6 | 3/3 | sí | — |
| 946 | 25269 | D | 6/6 | 2/2 | sí | — |
| 947 | 25269 | D | 6/6 | 6/6 | sí | — |
| 948 | 25269 | D | 6/6 | 22/22 | sí | — |
| 949 | 25269 | D | 6/6 | 4/4 | sí | — |
| 950 | 25269 | D | 6/6 | 8/8 | sí | — |
| 951 | 25269 | D | 6/6 | 8/8 | sí | — |
| 952 | 25269 | D | 6/6 | 4/4 | sí | — |
| 953 | 25269 | D | 6/6 | 4/4 | sí | — |
| 954 | 25269 | D | 6/6 | 11/11 | sí | — |
| 955 | 25269 | D | 6/6 | 2/2 | sí | — |
| 956 | 25269 | D | 6/6 | 4/4 | sí | — |
| 957 | 25269 | D | 6/6 | 2/2 | sí | — |
| 958 | 25269 | D | 6/6 | 1/1 | sí | — |
| 959 | 25269 | D | 6/6 | 3/3 | sí | — |
| 960 | 25269 | D | 6/6 | 4/4 | sí | — |
| 961 | 25269 | D | 6/6 | 3/3 | sí | — |
| 962 | 25269 | D | 6/6 | 1/1 | sí | — |
| 963 | 25269 | D | 6/6 | 2/2 | sí | — |
| 964 | 25269 | C | 7/7 | 10/10 | sí | — |
| 965 | 25269 | C | 7/7 | 15/15 | sí | — |
| 966 | 25269 | C | 7/7 | 11/11 | sí | — |
| 806 | 05837 | D | 6/6 | 7/7 | sí | — |
| 807 | 05837 | D | 6/6 | 4/4 | sí | — |
| 808 | 05837 | D | 6/6 | 4/4 | sí | — |
| 818 | 05837 | D | 6/6 | 10/10 | sí | — |
| 809 | 05837 | D | 6/6 | 3/3 | sí | — |
| 810 | 05837 | D | 6/6 | 2/2 | sí | — |
| 811 | 05837 | D | 6/6 | 1/1 | sí | — |
| 812 | 05837 | D | 6/6 | 1/1 | sí | — |
| 813 | 05837 | D | 6/6 | 1/1 | sí | — |
| 814 | 05837 | D | 6/6 | 2/2 | sí | — |
| 815 | 05837 | D | 6/6 | 1/1 | sí | — |
| 816 | 05837 | D | 6/6 | 4/4 | sí | — |
| 817 | 05837 | D | 6/6 | 1/1 | sí | — |
| 819 | 05837 | D | 6/6 | 2/2 | sí | — |
| 820 | 05837 | D | 6/6 | 3/3 | sí | — |
| 821 | 05837 | D | 6/6 | 3/3 | sí | — |
| 822 | 05837 | D | 6/6 | 2/2 | sí | — |
| 823 | 05837 | D | 6/6 | 3/3 | sí | — |
| 824 | 05837 | D | 6/6 | 1/1 | sí | — |
| 825 | 05837 | C | 7/7 | 11/11 | sí | — |
| 826 | 05837 | C | 7/7 | 6/6 | sí | — |
| 1044 | 25473 | D | 6/6 | 6/6 | sí | — |
| 1045 | 25473 | D | 6/6 | 13/13 | sí | — |
| 1036 | 25473 | D | 6/6 | 1/1 | sí | — |
| 1037 | 25473 | D | 6/6 | 1/1 | sí | — |
| 1038 | 25473 | D | 6/6 | 1/1 | sí | — |
| 1039 | 25473 | D | 6/6 | 3/3 | sí | — |
| 1040 | 25473 | D | 6/6 | 6/6 | sí | — |
| 1041 | 25473 | D | 6/6 | 2/2 | sí | — |
| 1042 | 25473 | D | 6/6 | 1/1 | sí | — |
| 1043 | 25473 | D | 6/6 | 1/1 | sí | — |
| 1046 | 25473 | C | 7/7 | 7/7 | sí | — |
| 1067 | 66170 | D | 6/6 | 2/2 | sí | — |
| 1068 | 66170 | D | 6/6 | 1/1 | sí | — |
| 1069 | 66170 | D | 6/6 | 2/2 | sí | — |
| 1070 | 66170 | D | 6/6 | 2/2 | sí | — |
| 1071 | 66170 | D | 6/6 | 20/20 | sí | — |
| 1072 | 66170 | D | 6/6 | 2/2 | sí | — |
| 1073 | 66170 | D | 6/6 | 2/2 | sí | — |
| 1074 | 66170 | D | 6/6 | 4/4 | sí | — |
| 1075 | 66170 | D | 6/6 | 7/7 | sí | — |
| 1076 | 66170 | D | 6/6 | 2/2 | sí | — |
| 1077 | 66170 | D | 6/6 | 2/2 | sí | — |
| 1078 | 66170 | D | 6/6 | 17/17 | sí | — |
| 1079 | 66170 | D | 6/6 | 2/2 | sí | — |
| 1080 | 66170 | D | 6/6 | 2/2 | sí | — |
| 1081 | 66170 | D | 6/6 | 1/1 | sí | — |
| 1082 | 66170 | D | 6/6 | 2/2 | sí | — |
| 1083 | 66170 | D | 6/6 | 1/1 | sí | — |
| 1084 | 66170 | C | 7/7 | 4/4 | sí | — |
| 1085 | 66170 | C | 7/7 | 6/6 | sí | — |
| 1086 | 66170 | C | 7/7 | 3/3 | sí | — |
| 892 | 17380 | D | 6/6 | 5/5 | sí | — |
| 893 | 17380 | D | 6/6 | 2/2 | sí | — |
| 894 | 17380 | D | 6/6 | 1/1 | sí | — |
| 895 | 17380 | D | 6/6 | 3/3 | sí | — |
| 896 | 17380 | D | 6/6 | 2/2 | sí | — |
| 897 | 17380 | D | 6/6 | 1/1 | sí | — |
| 898 | 17380 | D | 6/6 | 2/2 | sí | — |
| 899 | 17380 | D | 6/6 | 1/1 | sí | — |
| 900 | 17380 | D | 6/6 | 2/2 | sí | — |
| 901 | 17380 | D | 6/6 | 2/2 | sí | — |
| 902 | 17380 | D | 6/6 | 1/1 | sí | — |
| 903 | 17380 | D | 6/6 | 1/1 | sí | — |
| 904 | 17380 | D | 6/6 | 8/8 | sí | — |
| 905 | 17380 | D | 6/6 | 1/1 | sí | — |
| 906 | 17380 | D | 6/6 | 2/2 | sí | — |
| 907 | 17380 | D | 6/6 | 3/3 | sí | — |
| 908 | 17380 | D | 6/6 | 2/2 | sí | — |
| 909 | 17380 | D | 6/6 | 6/6 | sí | — |
| 910 | 17380 | D | 6/6 | 2/2 | sí | — |
| 911 | 17380 | D | 6/6 | 1/1 | sí | — |
| 912 | 17380 | D | 6/6 | 2/2 | sí | — |
| 913 | 17380 | D | 6/6 | 2/2 | sí | — |
| 914 | 17380 | D | 6/6 | 2/2 | sí | — |
| 915 | 17380 | D | 6/6 | 2/2 | sí | — |
| 916 | 17380 | D | 6/6 | 1/1 | sí | — |
| 917 | 17380 | D | 6/6 | 1/1 | sí | — |
| 918 | 17380 | D | 6/6 | 1/1 | sí | — |
| 919 | 17380 | D | 6/6 | 2/2 | sí | — |
| 920 | 17380 | D | 6/6 | 1/1 | sí | — |
| 921 | 17380 | D | 6/6 | 2/2 | sí | — |
| 922 | 17380 | D | 6/6 | 2/2 | sí | — |
| 923 | 17380 | D | 6/6 | 2/2 | sí | — |
| 924 | 17380 | D | 6/6 | 3/3 | sí | — |
| 925 | 17380 | D | 6/6 | 4/4 | sí | — |
| 926 | 17380 | D | 6/6 | 3/3 | sí | — |
| 927 | 17380 | D | 6/6 | 1/1 | sí | — |
| 928 | 17380 | D | 6/6 | 1/1 | sí | — |
| 929 | 17380 | D | 6/6 | 3/3 | sí | — |
| 930 | 17380 | D | 6/6 | 3/3 | sí | — |
| 931 | 17380 | D | 6/6 | 2/2 | sí | — |
| 932 | 17380 | D | 6/6 | 4/4 | sí | — |
| 933 | 17380 | D | 6/6 | 1/1 | sí | — |
| 934 | 17380 | C | 7/7 | 6/6 | sí | — |
| 935 | 17380 | C | 7/7 | 12/12 | sí | — |

*Fin del área 4.*

---

## Área 3 — Componentes deterministas (validador y scoring)

**Cerrada el 2026-09-22.** Archivos leídos completos para esta área, además de
los del Preflight: `scripts/comparar_correlacionador.py`, `scripts/medir_prefiltro.py`,
`scripts/probar_correlacionador.py`, `tests/test_reglas.py`, `tests/test_cifras.py`,
`tests/test_compuertas.py`, `tests/test_scoring.py`. Comprobaciones ejecutadas,
todas de solo lectura y sin LLM: re-ejecución del validador sobre los 326 insights
del Clasificador de la corrida 10; recomputación del scoring de los tres ciclos
contra las corridas 22, 23 y 24 (sesión cerrada con `rollback`); detección de
cifras en la prosa de los 241 insights publicados contra sus señales de origen;
`scripts/medir_prefiltro.py` (solo cuenta); `grep` de llamadas a modelo en las
capas deterministas.

### 3.1 Sondas — validador (M3)

| Sonda | Respuesta | Evidencia |
|---|---|---|
| ¿El validador llama a algún modelo? | **No** | `validador.py:21-27` importa `dataclasses`, `datetime`, `urllib.parse` y `reglas.normalizacion`; `normalizacion.py:12-15` importa `re` y `unicodedata`. `grep` de `cliente_compartido\|responses\.\|openai` en `reglas/`, `scoring/`, `informes/`, `ingesta/`, `almacen/`: ninguna coincidencia fuera de un comentario (`prefiltro.py:8`) |
| ¿Comprueba URL? | **Parcial** (decisión del dueño: Medio) | R3 exige el campo (`validador.py:97-100`); R4 exige esquema `http(s)` y `netloc` (`68-75`, `102-104`). No se resuelve. H-007 |
| ¿Comprueba fecha? | **Sí** | R3 exige el campo; R5 exige fecha ISO interpretable (`58-65`, `106-108`); además R7 compara `url` y `fecha` de la evidencia con la fila real solo de forma indirecta —la fecha la copia código, no el modelo (`clasificador.py:196-206`) |
| ¿Comprueba que la cita se localiza en el contenido de la fuente? | **Sí, en el contenido ingerido** (decisión del dueño: cumple; condición verificada en el área 4) | R6: `contiene(senal.contenido, cita)` tras normalizar mayúsculas, tildes, comillas y separadores sin descartar palabras (`normalizacion.py:36-60`); R7: la señal existe y es del mismo municipio y ciclo (`110-132`). El texto contra el que se compara es `texto_de(s)` —`objeto` para SECOP, «título. resumen» para RSS— (`ciclo.py:199-215, 369-380`). Nunca la red (`149-151`) |
| ¿Los rechazos se persisten con motivo? | **Sí** | `ciclo.py:383-391` escribe `estado_validacion` y `motivo_rechazo`; `persistencia.guardar_insights` los inserta igual que a los válidos (`88-124`). Corrida 10: 4 rechazados, los 4 con motivo `evidencia[i]: la cita no aparece en la señal N` (insights 945, 991, 1004, 1064); 27 rechazados en total |
| ¿Hay algún camino por el que un rechazado llegue a la correlación? | **No** | Producción: solo `estado_validacion == "validado"` entra en `para_correlacionar` (`ciclo.py:407-424`). Scripts: `comparar_correlacionador.py:197-201` filtra `validado` y `origen == clasificador`; `probar_correlacionador.py:100-115` valida en proceso y salta los rechazados. **Base:** 0 de los 170 consolidados tiene un origen rechazado (`SELECT`, 27 rechazados) |
| ¿El veredicto es reproducible? | **Sí** | Re-ejecutado `validar()` sobre los 326 insights del Clasificador de la corrida 10 con el índice de señales del ciclo 3 por municipio: **326/326** veredictos idénticos a los persistidos, 0 diferencias |
| ¿La tasa de rechazo se reporta como métrica primaria (CA-M3.3)? | **No** | No se persiste ni se muestra; `ResumenCiclo.__str__` (`ciclo.py:146-181`) imprime válidos, correlacionados y descartes pero no la tasa. Calculada aquí por `SELECT`: corrida 10 **4/326 = 1,2 %**; corrida 7: 7 rechazados de 344 filas; corrida 8: 15 de 365. H-010 |

Nota sobre el alcance de R7: el índice `vistas` en producción se construye **solo
con el lote enviado** (`ciclo.py:369-380`), y el Clasificador descarta antes toda
evidencia que referencie una señal no entregada (`clasificador.py:196-206`), así
que ningún rechazo puede deberse a citar una señal real no enviada. La tasa de
rechazo mide, por construcción, citas no localizables.

### 3.2 Sondas — scoring (M5)

| Sonda | Respuesta | Evidencia |
|---|---|---|
| ¿Los pesos están externalizados? | **Sí** | `config/pesos.json` (F1 0,364286 · F2 0,182143 · F4 0,15 · F5 0,303571 en el ciclo 1; F4 0,09 en los ciclos 2 y 3), cargado por `pesos.cargar` (`112-144`) con validación de suma = 1,0 ± 0,001 (`82-109`); persistidos verbatim en `corrida_scoring.pesos` y en la huella de `version_scoring` (`scoring/persistencia.py:47-58, 103-104`). Los tests se aíslan de este archivo (`tests/conftest.py:24-27`) |
| ¿El desglose por municipio se persiste? | **Sí** | `score_municipio.factores.aportes[]` con `codigo, crudo, normalizado, peso, aporte, sin_cobertura, hay_dato, motivo`, más `valores_crudos` en plano (`scoring/persistencia.py:109-134`). Verificado sobre Ibagué en el área 4 |
| ¿La selección es determinista ante empates? | **Sí** | `scores.sort(key=lambda s: (-s.score, s.divipola))` (`ranking.py:362-365`); probado en `test_el_orden_es_reproducible_ante_empate` (`tests/test_scoring.py:412-421`). En el ciclo 3 no hay empates (0 de 18) |
| ¿El tamaño de la selección sigue la desviación registrada (P1: 10, umbral 0)? | **Sí** | `Config.tope_top=10`, `umbral_informacion=0.0` (`config.py:90, 107`); `ResultadoCiclo.tope` se guarda en el resultado (`ranking.py:187, 392`); `componer` toma el tope del Config y lo registra en `calificacion.mostrados` (`composicion.py:294-297, 417`). Tests `344-366` |
| ¿El scoring es reproducible? | **Sí, exactamente** | Recomputado con `entradas_del_ciclo` + `cortes_por_fuente` + `puntuar_ciclo` sobre la base actual: ciclo 3 vs corrida 24 → **diferencia máxima 0,00e+00, 18/18 rankings iguales**, `version_scoring` recomputada `v3+8d8a2954` = persistida; ciclo 1 vs corrida 22 y ciclo 2 vs corrida 23: idénticos, versiones `v3+bbf2789c` y `v3+8d8a2954` coinciden. Confirma la afirmación de `CLAUDE.md` §1.1 de que el scoring es lo único reproducible del sistema |
| ¿Qué alimenta F1–F3? | El prefiltro | `agregacion.py:184-186` cuenta `n_obra` y `valor_obra` con `es_obra(objeto)`, que es coincidencia de subcadena sin límite de palabra (`prefiltro.py:53-58`). H-011 |

### 3.3 CA-M6.3 medido sobre el informe publicado

Las cifras **estructuradas** del payload —scores, rankings, aportes, cobertura,
fracción informada, tres tarjetas de contexto con fuente y año, fechas y URLs de
evidencia— las compone `informes/composicion.py`, que no llama a ningún modelo
(§3.1 y `composicion.py:1-32`). `justificacion` es `None` y `sugerencias` es `[]`
en los 10 municipios (el Sintetizador no existe).

La **prosa** de cada insight —`resumen` e `implicacion_inmobiliaria`— la escribió
el modelo y se publica tal cual. Medido con `reglas/cifras.py` (números de ≥3
dígitos) sobre los 241 insights y contra el texto completo de sus señales de origen
(`objeto` + `datos` para SECOP; título y resumen para RSS):

| Métrica | Valor |
|---|---|
| Insights con alguna cifra escrita por el modelo | **15 de 241** (14 del Clasificador, 1 del Correlacionador; 15 en `resumen`, 1 en `implicacion`) |
| Insights con cifras **no presentes** en sus señales de origen | **0 de 241** |

Es decir: todas las cifras que el modelo escribió en lo publicado son
transcripciones de la fuente; ninguna es inventada. Pero **ningún componente de
la cadena de producción lo comprueba**: `reglas/cifras.py` solo lo usa
`scripts/comparar_correlacionador.py:294-305`, y solo sobre la salida del
Correlacionador en una comparación de versiones. `ciclo.py` no llama a `cifras`
ni a `inventadas`. H-009.

### 3.4 Prefiltro (contexto de F1–F3; pendiente A2)

`scripts/medir_prefiltro.py` ejecutado (solo cuenta): sobre 19.640 señales SECOP
pasan 7.628 (**reducción 61,2 %**; 56,6 / 60,8 / 66,0 % por ciclo). Motivos:
obra 38,8 %, sin término territorial 32,9 %, ruido administrativo 28,3 %. La
fracción que pasa por municipio va de **15,0 % (Puerto Colombia) a 58,9 %
(Turbo)**. El diccionario compara por subcadena (`prefiltro.py:58`: `term in t`),
lo que `pendientes.md` A2 documenta con ejemplos («via» en «Viviana»,
«ampliación» de cobertura en contratos de enfermeras). Está registrado como
pendiente abierto, no como desviación autorizada.

### 3.5 Qué afirman las pruebas leídas

- `tests/test_reglas.py` (295 líneas): 20 casos del validador —cita inventada,
  señal inexistente, otro municipio, otro ciclo, Bing declarado y Bing
  encubierto, una evidencia mala tumba el insight—, normalización con separadores
  y cifras, prefiltro (4) y cobertura (6). Cubren R1–R7.
- `tests/test_scoring.py` (685 líneas): independencia del tamaño (F1, F2, y la
  prueba resumen `test_el_tamano_no_decide_el_ranking`), F3 sin tope inventado,
  piso de ELIC con `hay_dato`, F5 por ventana (A7), F6 media de medias,
  redistribución que conserva la suma, winsorizado de F4, empate reproducible,
  tope fijo y configurable, umbral apagado y reactivable, caso Armenia.
- `tests/test_cifras.py` (53): el falso positivo «calles 76 y 80», el mínimo de 3
  dígitos y las variantes de redondeo.
- `tests/test_compuertas.py` (78): el invariante «la compuerta no suspende a su
  línea base» sobre las constantes `PISO_RUIDO` del script. Prueba constantes, no
  una medición: si alguien edita `PISO_RUIDO` a mano, el test sigue pasando.

### 3.6 Hallazgos

**H-009 · Alto · Riesgo · Confianza Alta · Área 3 · CA-M6.3 (conjunto bloqueante), CLAUDE.md §2.2 · 🔒 BLOQUEA DISTRIBUCIÓN · quick win (§3.9)**
*La prosa publicada contiene cifras escritas por el modelo y ninguna compuerta
de producción lo comprueba.* 15 de los 241 insights del informe 5 llevan al menos
un número de tres o más dígitos en `resumen` o `implicacion_inmobiliaria`; **los
15 están en sus señales de origen** (0 inventadas). La única detección existente
vive en un script de comparación:

```
scripts/comparar_correlacionador.py:294-300
        # --- fuga de cifras, sobre la pasada B ---
        permitidas: set[str] = set()
        for i in insights:
            permitidas |= numeros(i.resumen) | numeros(i.implicacion_inmobiliaria or "")
            ...
        inventadas = numeros(texto_de(rb)) - permitidas
```

y `ciclo.py` no la invoca ni para el Clasificador ni para el Correlacionador.
*Escenario:* en una pasada futura el Clasificador escribe «beneficia a 3.480
hogares» —cifra real de `contexto_municipal`, que el propio proyecto ya vio
filtrarse en el control v1/v2 (`comparar_correlacionador.py:28-32`)— y el
informe la publica sin que nada la detecte; el conjunto bloqueante se rompe en
silencio. **Por qué no es Crítico (razón escrita, como exige el criterio A):**
el estado medido del informe publicado es limpio —241/241 sin cifras inventadas—
y todas las cifras estructuradas las compone código; lo que falta es el control
que impida que deje de ser así. **Por qué es Alto y no Medio:** una sola cifra
inventada publicada invalidaría la confianza en el informe entero (H4/CA-M6.3), y
el propio proyecto declara que «una cifra real escrita por el modelo sigue siendo
una cifra escrita por el modelo» (`reglas/contexto.py:3-6`), lectura bajo la cual
los 15 casos ya son una desviación. Queda en Preguntas abiertas (P-3) qué lectura
adopta el dueño.

**H-010 · Medio · Brecha · Confianza Alta · Área 3 · CA-M3.3**
*La tasa de rechazo del validador no se reporta ni se persiste como métrica.*
CA-M3.3 la declara «métrica primaria» y «tasa de alucinación medida». Ningún
módulo la calcula: `ResumenCiclo.__str__` (`ciclo.py:146-181`) imprime válidos,
correlacionados y descartes; `corrida_agentes` guarda `senales_procesadas` y
tokens pero no rechazados; `ciclo.n_rechazados` existe y vale 0 (H-003). Se
obtiene solo por `SELECT` sobre `insight.estado_validacion`: **corrida 10, 4/326
= 1,2 %**. *Escenario:* el informe de resultados y el panel de CA-M9.13 tienen que
reconstruirla a mano cada vez, y dos personas pueden reconstruirla con
denominadores distintos (¿326 del Clasificador o 364 con consolidados?).

**H-011 · Medio · Riesgo · Confianza Alta · Área 3 · Addendum 01 D4 (F1–F3), pendiente A2**
*El diccionario de obra decide F1, F2 y F3 por coincidencia de subcadena sin
límite de palabra.*

```
src/territorial/reglas/prefiltro.py:53-58
def es_obra(texto: str | None) -> bool:
    t = normalizar(texto)
    if not t:
        return False
    return any(term in t for term in TERMINOS_OBRA)
```

`agregacion.py:184-186` cuenta `n_obra` y `valor_obra` con esa función, así que
los tres factores de contratación —el 53,7 % del peso en los ciclos 2 y 3 y el
54,6 % en el 1, según `config/pesos.json`— heredan sus falsos positivos.
Medido: la fracción marcada como obra va del 15,0 % al 58,9 % según el municipio.
*Escenario:* un municipio con muchos contratos de «prestación de servicios… vía
ampliación de cobertura» puntúa alto en F1 sin obra real; el ranking se mueve
por el diccionario y no por el territorio. Está registrado como pendiente abierto
A2 con los mismos ejemplos, y el dueño ha pedido no tocarlo durante la auditoría;
se consigna porque condiciona la lectura del ranking publicado.

### 3.7 Estado de los CA del área

| CA | Estado | Base |
|---|---|---|
| CA-M3.1 | **Parcial (Medio)** — decisión del dueño | «Localizable»: cumple, 933/933 citas del informe; «accesible»: sintaxis (H-007) |
| CA-M3.2 | **Cumple** | Rechazados persistidos con motivo; 27 filas, 4 en la corrida publicada |
| CA-M3.3 | **Parcial** | La tasa existe por derivación (1,2 % en la corrida 10) pero no se reporta ni se persiste (H-010) |
| CA-M3.4 | **Cumple** | Filtro en `ciclo.py:407-424`; 0 de 170 consolidados con origen rechazado; scripts también filtran |
| CA-M5.1 | **Cumple** | Ranking completo, explicable factor a factor y reproducido con diferencia 0 en los tres ciclos |
| CA-M5.2 | **Desviación autorizada** (Addendum 01 D4/§6) | Features de SECOP y ELIC en lugar de TerriData; F6 íntegro, sin ejercitar (0 calificaciones) |
| CA-M5.3 | **Cumple** | `config/pesos.json` con validación; sin cambio de código |
| CA-M5.4 | **Desviación autorizada** (P1) | Tope fijo de 10, umbral 0; verificado en Config, resultado y payload |
| CA-M5.5 | **Cumple** | `factores_que_empujaron` y aportes persistidos por municipio y corrida |
| CA-M6.3 | **Parcial** | Cifras estructuradas: compuestas por código, 100 %. Prosa: 15 insights con cifras del modelo, 0 inventadas, sin compuerta en producción (H-009). Lectura definitiva pendiente de P-3 |
| CA-M6.4 (composición) | **Cumple** | Contexto con `fuente` y `anio` (`composicion.py:117-152`); evidencia con `url` y `fecha`. La presentación se juzga en las áreas 5 y 6 |

### 3.8 No verificable en esta área

- Comportamiento del validador ante evidencia de una fuente **viva** (URL que
  cambia o desaparece): fuera del modelo de snapshot; artefacto: conector real en
  Fase 0.
- F6 (calificaciones previas ponderadas por gerencia): implementado y probado con
  datos sintéticos (`test_scoring.py:159-168`), nunca ejercitado con datos reales
  (0 calificaciones).

### 3.9 Decisión del dueño sobre P-3 (2026-09-22) y notas para el área 8

**CA-M6.3 — rige la lectura «ninguna cifra sin fuente».** Una cifra en la prosa
del modelo es conforme **solo si** (a) aparece literal en las señales de origen del
insight **y** (b) existe una compuerta de producción en `ciclo.py` que lo
verifique. Hoy se cumple (a) —15/15 cifras del informe 5 están en su fuente— y
no (b). Por tanto **CA-M6.3 queda Parcial y H-009 se mantiene Alto**. **H-009 es
candidato a quick win:** cablear `reglas.cifras.inventadas` sobre `resumen` e
`implicacion_inmobiliaria` en `ciclo.py`, tras M3 y tras M4, con el texto de las
señales del insight como entrada permitida; el módulo ya existe y está probado
(`tests/test_cifras.py`). P-3 queda cerrada con esta decisión.

**Para el área 8 (registrado a petición del dueño):**

1. Bajo el modelo de snapshot, la **tasa de rechazo del validador mide fidelidad
   de cita contra lo ingerido, no alucinación respecto del mundo**: R6 comprueba
   que la cita esté en el texto que se le entregó al modelo, y nada comprueba que
   el texto ingerido sea verdadero ni que la URL siga resolviendo. El área 8 debe
   verificar cómo presenta `informe_resultados.md` esa tasa (CA-M3.3 la llama
   «tasa de alucinación medida») y si la distinción está declarada.
2. **H-011 bajo el criterio C(ii):** el diccionario de obra decide F1–F3, el 54 %
   del peso del score. El área 8 debe evaluar si ese peso impide atribuir una
   calificación baja al pipeline agéntico (M2/M4, lo que H1 quiere medir) frente
   al scoring determinista (qué municipio se muestra y en qué puesto), y qué dice
   `informe_resultados.md` sobre H1 al respecto.

*Fin del área 3.*

---

## Área 5 — Aplicación web (M7 y M9)

**Cerrada el 2026-09-22.** Todos los archivos de `web/app` y `web/lib` estaban
leídos completos desde el Preflight; no hay archivos nuevos. Comprobaciones
ejecutadas: `grep` de toda llamada a la base y de todo `cookies().set/delete` en
`web/`; `find` de *route handlers*; peticiones **GET** al servidor de desarrollo
—sin cookie, con cookie forjada de un usuario autorizado, de un no autorizado y
del administrador—, contando sobre el HTML renderizado sin el `<script>` del
payload RSC. **No se envió ninguna calificación, comentario ni cambio de
seguimiento.**

### 5.1 Superficie de escritura, enumerada

No existe ningún *route handler* (`find web/app -name route.ts` y `api/`: vacío)
ni ninguna importación del driver fuera de `web/lib/db.ts`. El único archivo
`"use server"` es `web/app/acciones.ts` (la mención en `tablero.ts:24` es un
comentario). Toda escritura pasa por estas cinco Server Actions:

| Server Action (`acciones.ts`) | Llama a | Sentencia | Tabla · columnas escritas | Verifica en servidor |
|---|---|---|---|---|
| `identificarse` (41-59) | `gerenciaDelCorreo` (lectura) | `cookies().set("correo", …)` (51-56) | **ninguna tabla**; cookie `correo` httpOnly, sameSite lax, 1 año, **sin firma** | Que el correo esté en `usuario` y `activo` |
| `cambiarCorreo` (62-65) | — | `cookies().delete` (63) | ninguna | — |
| `registrarCalificacion` (73-80) | `escrituras.calificar` (30-50) | `INSERT INTO calificacion … ON CONFLICT (id_insight, id_gerencia) DO UPDATE` (43-49) | `calificacion` · `id_insight`, `id_gerencia`, `valor`, `comentario`, `creado_en` | Identidad presente; `valor` entero 1–5 (`escrituras.ts:36-42`). **No** verifica ciclo abierto ni que el insight pertenezca a un informe publicado |
| `registrarComentario` (124-133) | `escrituras.comentar` (53-64) | `UPDATE calificacion SET comentario` (58-63) | `calificacion` · `comentario` | Identidad presente. Sin fila previa no escribe nada (0 filas afectadas) |
| `cambiarEstado` (93-121) | `escrituras.registrarSeguimiento` (70-78) | `INSERT INTO seguimiento` (73-77) | `seguimiento` · `divipola`, `id_ciclo_origen`, `estado`, `nota`, `id_usuario`, `fecha_cambio` | Identidad; `estado` en la unión generada; nota obligatoria en `descartado`/`en_estructuracion` (105-110). `divipola` e `id_ciclo` vienen de campos ocultos del cliente; solo las FK limitan |

Lecturas: 5 `SELECT` en `consultas.ts` (`informe`, `usuario`, `calificacion`
propia) y 3 en `tablero.ts` (`informe`, `seguimiento` + `usuario`). Ninguna
sentencia sobre `insight`, `senal_cruda`, `score_municipio`, `corrida_*`,
`usuario` (escritura) ni `informe` (escritura). **CA-M9.16 se cumple:** las
escrituras son exactamente `calificacion` y `seguimiento`, más la cookie.

### 5.2 Sondas

| Sonda | Respuesta | Evidencia |
|---|---|---|
| ¿Cómo se identifica quién califica? | Por el **valor en claro** de la cookie `correo`, resuelto en cada petición contra `usuario` (`sesion.ts:38-43`, `consultas.ts:69-81`). La gerencia es `usuario.id_gerencia` | GET con `Cookie: correo=prueba@territorial.local` **sin haber pasado por `identificarse`**: la página muestra «Calificando como **PRUEBA**» y 25 botones de calificación (5 insights × 5); con `correo=nadie@ejemplo.com`: sin identidad y formulario de identificación visible; con `correo=admin@territorial.local`: aparece «Métricas» en la barra |
| ¿Puede un usuario calificar a nombre de otra gerencia? | **Sí**, tecleando un correo autorizado ajeno o forjando la cookie. No hay secreto, firma ni verificación de posesión del correo | `acciones.ts:45-56`; demostrado por GET arriba (la identidad se acepta sin `identificarse`). Es lo que el registro `M9-acceso` y `sesion.ts:4-8` llaman «atribución declarativa» |
| ¿Puede calificar dos veces? | **No como dos filas**: el `ON CONFLICT` deja una por `(id_insight, id_gerencia)` (`escrituras.ts:46-49`, `modelos.py:429`). **Sí sobrescribir**: la segunda persona de la misma gerencia —o quien use su correo— reemplaza `valor` sin rastro (H-008: `creado_en` no cambia) | `escrituras.ts:43-49` |
| ¿Puede alguien leer calificaciones ajenas antes de emitir la suya (CA-M7.2)? | **Por la interfaz, no**: `calificacionesDeLaGerencia` filtra por la gerencia identificada (`consultas.ts:93-100`); la página no muestra promedios ni conteos de otras (GET: 0 menciones a «promedio»/«respondido»). **Con otra identidad, sí**: la misma cookie forjada muestra lo que esa gerencia calificó | Estático + GET |
| ¿CA-M7.7 (cierre de ciclo) se verifica en servidor? | **No.** Solo en la vista: `cicloEsEditable` decide `puedeCalificar` y si se pinta `Identificarse` (`ciclo/[id]/page.tsx:190, 271, 277`). `registrarCalificacion` y `registrarComentario` no lo consultan | `acciones.ts:73-80, 124-133` |
| ¿Se verifica que el insight pertenezca a un informe publicado? | **No.** `registrarCalificacion` toma `id_insight` del formulario y llama a `calificar` sin comprobar informe, ciclo ni `estado_validacion`; cualquier `insight.id` existente —incluidos los de las corridas 11/12 y los 27 rechazados— es aceptable para la FK | `acciones.ts:76-78`, `escrituras.ts:43-49` |
| Clics del informe a la calificación guardada (CA-M7.1) | Abrir el enlace → clic en el municipio (1) → **una vez** correo + «Continuar» → clic en la nota (1). Tras identificarse, **1 clic por calificación**, sin botón de enviar | `Panel.tsx:121-145` (form con 5 `submit`), `Identificarse.tsx:7-9` |
| Guardado instantáneo (CA-M7.6) | **Sí**: upsert en el clic, `revalidatePath` y marca «✓ Calificación registrada» sin ocultar la fila | `escrituras.ts:43-49`, `Panel.tsx:160-166` |
| Etiqueta MVP (desviación `M6-aviso`) en cada vista con contenido generado | **Solo en la vista de ciclo**: 1 `etiqueta-aviso` con «MVP» en el encabezado; el texto largo no se muestra («no validado»: 0). **En `/priorizados`: 0** (la única aparición de «MVP» es la `<meta name="description">` del layout) | GET sobre HTML sin `<script>`; `ciclo/[id]/page.tsx:235-237` |
| Vistas vs CA-M9.3 enmendado | **Dos de tres**: `/ciclo/[id]` y `/priorizados` existen; **`/historico` → 404 y `/metricas` → 404 también con identidad de administrador**, aunque `Nav.tsx:13-23` enlaza a ambas | GET; `git ls-files web/app` |
| `/ciclo/2` → 404 | **Comportamiento correcto**, no hallazgo: no hay informe publicado del ciclo 2 (`informeDelCiclo` → `notFound()`, `page.tsx:187-188`); el ciclo 2 nunca se corrió entero (área 4, §0.7). `/ciclo/1` igual; `/ciclo/abc` → 404 por `Number.isInteger` | GET |
| Texto de selección en `Panel.tsx:299-304` | **Obsoleto y renderizado**: «los **2 de mayor peso** y **3 al azar**, con al menos uno de prensa» aparece en Ibagué; la selección real es 3 correlacionados + 1 contratación + 1 prensa con relleno (`seleccion.py:56-60`) y el payload de Ibagué dice `{correlacionado: 3, contratacion: 1, prensa: 1}`, el de Armenia `{correlacionado: 1, prensa: 1, relleno: 3}` | GET: «de mayor peso» presente |
| ¿Cuántos insights y evidencias ve la gerencia? | **5 insights por municipio como máximo y 1 evidencia por insight.** Ibagué (8 en payload): 5 `<article>`, 5 «ver en la fuente». **Funza (49): 5 `<article>`**. Buenaventura (38, no pedido): 5 | GET; `Panel.tsx:69` (`evidencia[0]`), `Panel.tsx:312` (`pedidos` o `slice(0, 5)`) |
| Cadena de trazabilidad en interfaz (CA-M9.5) | **No existe** ruta ni componente; el insight muestra «señal N» como texto y un enlace a la URL de la fuente | `Panel.tsx:321-327, 85-95` |

### 5.3 Hallazgos

**H-012 · Alto · Riesgo · Confianza Alta · Área 5 · Criterio C(ii) sobre la desviación `3b`/`M9-acceso` → CA-M7.2, CA-M9.1, CA-M9.14, H1, H2 · 🔒 BLOQUEA DISTRIBUCIÓN**
*La identidad es una cookie en claro sin firma: cualquiera califica y lee a
nombre de cualquier gerencia autorizada.* (i) La desviación **está implementada
como se registró**: leer es abierto, calificar pide un correo de la lista
precargada, la app no da de alta a nadie. (ii) Pero la desviación retira el
control del que dependen CA-M7.2 («ninguna gerencia ve la de otra») y CA-M9.14
(tasa visible solo para el administrador), y la atribución de H1/H2 a gerencias:

```
web/app/acciones.ts:51-56
  (await cookies()).set(COOKIE_CORREO, correo, {
    httpOnly: true,
    sameSite: "lax",
    maxAge: DURACION_COOKIE,
    path: "/",
  });
web/lib/sesion.ts:38-42
  const correo = (await cookies()).get(COOKIE_CORREO)?.value;
  if (!correo) return null;
  const usuario = await gerenciaDelCorreo(correo);
```

*Demostrado con GET:* `Cookie: correo=prueba@territorial.local` sin pasar por
`identificarse` renderiza «Calificando como PRUEBA» con los 25 botones de
calificación activos; `correo=admin@territorial.local` muestra «Métricas».
*Escenario:* una persona con el listado de las 7 gerencias —que estará en el CSV
de `cargar_usuarios.py`— califica los 15 insights pedidos a nombre de las 7 en
diez minutos; H2 marca 100 % y H1 mide la opinión de una sola persona; nada lo
distingue de una respuesta real. `sesion.ts:4-8` lo reconoce («la atribución es
declarativa y hay que decirlo al publicar H2»). No es una Desviación no
registrada; es el riesgo residual de la registrada, y el registro no menciona que
la cookie se pueda forjar sin conocer siquiera el flujo de identificación.

**H-013 · Alto · Defecto · Confianza Alta · Área 5 · CA-M7.7, CA-M9.16 (alcance de la escritura) · 🔒 BLOQUEA DISTRIBUCIÓN**
*Las Server Actions no verifican en servidor el alcance de lo que escriben.*
`registrarCalificacion` y `registrarComentario` aceptan cualquier `id_insight`
existente, sin comprobar que el ciclo esté abierto ni que el insight pertenezca
al informe publicado; `cambiarEstado` acepta cualquier `divipola` e `id_ciclo`
que pasen las FK:

```
web/app/acciones.ts:73-80
export async function registrarCalificacion(datos: FormData): Promise<void> {
  const yo = await identidadActual();
  if (!yo) return;
  const idInsight = Number(datos.get("id_insight"));
  const valor = Number(datos.get("valor"));
  await calificar(idInsight, yo.id_gerencia, valor);
  revalidatePath("/ciclo/[id]", "page");
}
```

El cierre de ciclo vive solo en la vista (`ciclo/[id]/page.tsx:190, 277`).
*Escenario:* (a) publicado el informe del ciclo siguiente, una petición con el
formulario del ciclo cerrado —una pestaña abierta desde antes basta— sigue
escribiendo; (b) un `id_insight` de la corrida 11 o de un insight rechazado
recibe una calificación que `agregacion.py:203-213` (F6) y `ciclo.py:184-196`
(CA-M4.3) leerán como opinión de las gerencias. Corrompe la evidencia de H1 y el
insumo de F6 → Alto. Confianza Alta: no requiere ejecución, el código no tiene la
comprobación.

**H-014 · Medio · Brecha · Confianza Alta · Área 5 · CA-M9.3, CA-M9.7, CA-M9.13, CA-M9.14, CA-M9.15, CA-M7.5**
*Las vistas Histórico y Métricas no existen; la barra enlaza a ellas.*
`Nav.tsx:13-23` define `/historico` y, para el administrador, `/metricas`;
`web/app/` solo tiene `ciclo/[id]` y `priorizados`. GET: 404 en ambas, también
con identidad de administrador. Con ello no hay tasa de respuesta por gerencia
(CA-M7.5, CA-M9.13), ni distribución de calificaciones, ni tasa de rechazo, ni
costo por agente, ni exportación CSV (CA-M9.15), ni consulta de informes
anteriores (CA-M9.7). El PRD §7 permite recortar «métricas → filtros → histórico»
si la semana 5 va con retraso, pero **el recorte no está registrado** en
`pendientes.md` ni en `CLAUDE.md`, que dan M9 por «sin código» o «parcial» sin
nombrarlo. Medio porque ningún CA bloqueante depende de ello y las métricas se
pueden derivar por SQL; sube a Alto si la ventana de calificación se abre sin una
forma de reportar H2.

**H-015 · Medio · Defecto · Confianza Alta · Área 5 · Desviación registrada `M9-sel`, CA-M6.6**
*La pantalla describe un criterio de selección que ya no es el que se aplica.*

```
web/app/ciclo/[id]/Panel.tsx:299-304
            De los {m.insights.length} insights del municipio se piden estos{" "}
            {pedidos.length}: los <strong>2 de mayor peso</strong> y{" "}
            <strong>3 al azar</strong>, con al menos uno de prensa. Los elige
            código determinista con una semilla congelada, así que las siete
            gerencias reciben exactamente los mismos. El resto es opcional.
```

El criterio vigente es 3 correlacionados + 1 de contratación + 1 de prensa con
relleno (`seleccion.py:56-60`), y el payload lo registra (`composicion_pedida`:
Ibagué `{correlacionado: 3, contratacion: 1, prensa: 1}`, Armenia
`{correlacionado: 1, prensa: 1, relleno: 3}`). Renderizado en el servidor de
desarrollo. *Escenario:* una gerencia lee que califica «los de mayor peso» y
juzga los correlacionados como si fueran los que más pesan en el score, cuando el
score no lee insights; sesga la interpretación de H1.

**H-016 · Medio · Brecha · Confianza Alta · Área 5 · CA-M9.4, CA-M6.4 (presentación)**
*La interfaz muestra como máximo 5 insights por municipio y 1 evidencia por
insight.* El payload publica 241 insights con 933 evidencias; la pantalla pinta
`pedidos` en los tres primeros y `m.insights.slice(0, 5)` en el resto
(`Panel.tsx:312`), y de cada insight solo `i.evidencia[0]` (`Panel.tsx:68-70`).
Funza tiene 49 insights y 183 evidencias en el payload: se ven 5 y 5. El
consolidado 1092 tiene 12 evidencias (7 SECOP + 5 RSS): se ve 1. CA-M9.4 exige
«los insights que lo sustentan y la evidencia enlazada de cada uno», y M6-orden
sostiene que el cruce SECOP×RSS es «lo que ninguna fuente sola produce»: en
pantalla ese cruce no se ve. *Escenario:* una gerencia califica un consolidado
viendo una sola de sus doce citas.

**H-017 · Medio · Brecha · Confianza Alta · Área 5 · CA-M9.5**
*No hay cadena de trazabilidad en la interfaz.* La cadena existe en datos y se
reconstruyó al 100 % (área 4), pero CA-M9.5 la pide «expuesta en interfaz, no
solo en base de datos». La pantalla muestra «señal 4599, 4610, …» como texto
(`Panel.tsx:324-326`) y el enlace a la URL de la fuente; no hay ruta ni despliegue
para `señal → insight → validación → correlación → score`.

**H-018 · Medio · Brecha · Confianza Alta · Área 5 · CA-M9.11**
*La ficha del municipio priorizado no muestra insights acumulados ni
calificación promedio.* `priorizados/page.tsx:231-237` pinta ciclos y puestos
(«c3: puesto 1»); CA-M9.11 exige además «sus insights acumulados y su
calificación promedio». Con 0 calificaciones el promedio sería vacío hoy, pero el
código tampoco lo calcula ni lo consulta.

**H-019 · Bajo · Riesgo · Confianza Alta · Área 5 · CA-M9.17, desviación `M6-aviso`**
*La etiqueta MVP vive en una página, no en el layout.* Se pinta solo en
`ciclo/[id]/page.tsx:235-237`; `/priorizados` no la lleva (GET: 0
`etiqueta-aviso`). Esa vista no muestra prosa del modelo —nombres, scores y
estados—, por eso es Bajo; pero cualquier vista nueva nace sin la marca, y
CA-M9.17 dice «toda pantalla».

**H-020 · Medio · Brecha documental · Confianza Alta · Área 5 · CA-M6.2, CA-M9.4 — criterio B**
*La infografía no existe en el código y no está especificada ni retirada.*
`informe.infografias` es `[]` en los 4 informes (área 4); `web/` no tiene
imagen, gráfico ni componente con ese nombre; ningún documento del repositorio
define su contenido ni su formato; `pendientes.md` no la retira. Por el criterio
B se clasifica como Brecha documental y pasa a Preguntas abiertas (P-4).

### 5.4 Estado de los CA del área

| CA | Estado | Base |
|---|---|---|
| CA-M6.5 | **Desviación autorizada** (`M6-aviso`) | «MVP» en el encabezado de la vista de ciclo; texto largo en el payload. Ver H-019 |
| CA-M6.7 | **Parcial** | El informe publicado es permanente y visible en la app; sin correo (`11.4/3`, autorizada); **sin Histórico** para «consultable de forma permanente» más allá del ciclo vigente (H-014) |
| CA-M7.1 | **Cumple** | 1 clic por calificación tras identificarse una vez; identificación una sola vez por cookie de 1 año |
| CA-M7.2 | **Parcial** | Estructura: único `(id_insight, id_gerencia)` y lectura solo de lo propio. Independencia: no garantizable sin identidad (H-012) |
| CA-M7.3 | Parcial (área 4, H-005) | — |
| CA-M7.4 | **Cumple** | Comentario opcional tras calificar; `UPDATE` de la propia fila |
| CA-M7.5 | **No cumple** | Ninguna tasa se calcula ni se muestra (H-014) |
| CA-M7.6 | **Cumple** | Upsert en el clic; sin botón de enviar |
| CA-M7.7 | **Parcial** | Derivado correctamente (`cicloEsEditable`) pero aplicado solo en la vista (H-013) |
| CA-M9.1 | **Desviación autorizada** (`3b`/`M9-acceso`) con **Riesgo Alto** (H-012) | Identidad declarativa por correo precargado |
| CA-M9.2 | **Desviación autorizada** (`11.4/3`) | Sin correo; el enlace se comparte a mano y abre el informe sin paso previo |
| CA-M9.3 | **Parcial** | 2 de 3 vistas; enlaces a 404 (H-014) |
| CA-M9.4 | **Parcial** | Informe del top 10 con score, fuentes, contexto y evidencia; **5 insights y 1 evidencia por insight** (H-016); sin infografías (H-020) |
| CA-M9.5 | **No cumple** | H-017 |
| CA-M9.6 | **Desviación autorizada** (`M6-src`) · Cumple | Barras por fuente desde `aportes_por_fuente` (`Panel.tsx:251-288`); ausencias mostradas |
| CA-M9.7 | **No cumple** (vista) | Datos correctos (`informe` publicado/archivado); sin vista Histórico (H-014) |
| CA-M9.8 | **Cumple** | Tablero derivado de los informes publicados; sin alta manual (`tablero.ts:115-155`); GET: Ibagué, Armenia, Funza |
| CA-M9.9 | **Cumple** | Cuatro estados; nota obligatoria verificada **en servidor** (`acciones.ts:105-110`) |
| CA-M9.10 | Parcial (área 4, H-004) | Gerencia derivada en consulta |
| CA-M9.11 | **Parcial** | Ciclos y puestos sí; insights acumulados y promedio no (H-018) |
| CA-M9.12 | **Cumple** | Filtros estado/ciclo/departamento y orden score/fecha en la URL (`priorizados/page.tsx:85-96`) |
| CA-M9.13 · CA-M9.14 · CA-M9.15 | **No cumple** | Sin `/metricas` ni CSV (H-014). CA-M9.14 no se viola —nada expone la tasa— pero tampoco existe lo que debía proteger |
| CA-M9.16 | **Cumple** | Superficie enumerada en §5.1: `calificacion`, `seguimiento` y la cookie. El alcance de esas escrituras es H-013, no una escritura fuera de las permitidas |
| CA-M9.17 | **Desviación autorizada** (`M6-aviso`) con nota | Solo en la vista de ciclo (H-019) |
| CA-M9.18 | → Área 6 | — |

### 5.5 No verificable en esta área

- Que una Server Action forjada (POST con `id_insight` arbitrario o con el ciclo
  cerrado) escriba de verdad: **no se ejecutó ninguna escritura** por regla de
  esta auditoría; H-013 se sostiene en la lectura del código, que no contiene la
  comprobación. Artefacto: prueba de integración contra una rama de Neon.
- Comportamiento en Vercel con el endpoint *pooled* y `revalidatePath` bajo
  varias instancias: solo se observó el servidor de desarrollo.

*Fin del área 5.*

---

## Área 2 — Agentes y prompts (M2 y M4)

**Cerrada el 2026-09-22.** Archivos leídos completos para esta área, además de
los del Preflight: los 6 prompts (`clasificador_v1..v4.md`,
`correlacionador_v1..v2.md`), `scripts/probar_clasificador.py`,
`scripts/comparar_prompts.py`, `scripts/dos_pasadas.py`,
`scripts/comparar_pasadas.py`. Comprobaciones ejecutadas, sin LLM ni escrituras:
`git log -S` sobre la promoción de v2; `SELECT` sobre `prompt_version`, versiones
y linaje por corrida, descartes de la corrida 10, señales Bing y
`contexto_no_verificado`; contabilidad señal a señal de CA-M2.5.

### 2.1 Qué versión se carga en ejecución y cómo queda registrada

| Paso | Código | Verificado |
|---|---|---|
| Versión vigente | Constante `VERSION_PROMPT`: `"v4"` (`clasificador.py:35`), `"v2"` (`correlacionador.py:66`) | — |
| Carga | `instrucciones(version)` lee `prompts/<agente>_<version>.md` y lo cachea (`clasificador.py:113-118`, `correlacionador.py:203-208`) | Los 6 archivos existen |
| Linaje por contenido (D7) | `registrar_prompt` calcula SHA-256, archiva el texto en el blob y falla con `PromptDivergente` si la misma versión ya está registrada con otro hash (`linaje.py:39-78`); `procesar_ciclo` lo llama **antes** del bucle (`ciclo.py:515-527`) | `prompt_version` tiene **2 filas**: `clasificador v4` (id 1) y `correlacionador v1` (id 2); hash de tabla = blob = archivo en `src/` para v4, v1 **y v2** (área 4) |
| Registro por corrida | `corrida_agentes.version_clasificador/version_correlacionador/version_pipeline` (`persistencia.py:65-73`); `insight.version_prompt` (etiqueta) e `insight.id_prompt` (FK al linaje) (`88-124`, `127-166`) | Corrida 10: 326 insights v4 → `id_prompt 1`, 38 consolidados v1 → `id_prompt 2`, 0 NULL |

**No existe fila `correlacionador v2` en `prompt_version`.** Ninguna corrida
registrada con linaje ha corrido el prompt que `CLAUDE.md` declara vigente.

**Por qué la corrida 10 (publicada) usó el Correlacionador v1 — cronología
ejecutada** (`git log --date=iso`, timestamps de la base en UTC):

| Momento (UTC) | Hecho |
|---|---|
| 2026-09-21 16:02:54 | Abre la corrida 10 (`corrida_agentes.fecha_corrida`), con `version_correlacionador = 'v1'` |
| 2026-09-21 21:15:38 | Commit `9afa300` **añade** `correlacionador_v2.md` («contexto municipal de TerriData, bandeado para el Correlacionador») |
| 2026-09-21 21:33:01 | Abren las corridas 11 y 12: control **v1 contra v1** (`comparar_correlacionador.py --a v1 --b v1 --persistir`), ambas `version_correlacionador = 'v1'` |
| 2026-09-21 22:33:54 | Commit `165097e` **promueve** v2 (`VERSION_PROMPT = "v2"`) |
| 2026-09-22 16:53:40 | Se publica el informe 5 sobre la corrida 10 |

La corrida 10 es **cinco horas anterior** a que existiera el archivo v2 y seis y
media a su promoción. Desde entonces **nadie ha vuelto a correr `procesar_ciclo`**:
la última corrida con Clasificador es la 10. El contraste v1/v2 que justificó la
promoción (40 convergencias, tipología 35, citado en `CLAUDE.md` y
`comparar_correlacionador.py:88-99`) **no está persistido**: las únicas corridas
del script son la 11 y la 12, y son v1/v1. Alimenta P-1 y el área 8 (H-023).

### 2.2 Restricciones declaradas en los prompts y qué las hace cumplir

| Restricción (prompt) | Dónde se declara | Lo hace cumplir el código | Evidencia |
|---|---|---|---|
| Cita textual exacta, «copia y pega» | `clasificador_v4.md:75-77` (v1–v3 igual) | **Sí** — validador R6 + R7 | `validador.py:134-136`; 933/933 en el informe (área 4) |
| Solo `id_senal` recibidos | `clasificador_v4.md:79`; `correlacionador_v2.md:37` | **Sí** — el Clasificador descarta evidencia con ids ajenos antes de validar; `ensamblar` rechaza grupos con ids no entregados | `clasificador.py:196-206`; `correlacionador.py:318-323` |
| «No inventes cifras» / «Ninguna cifra puede salir de ti» | `clasificador_v4.md:81`; `correlacionador_v2.md:63-64, 89-92` | **No en producción** — solo en el script de comparación | H-009 (área 3) |
| Un hecho, un insight; agrupar por frente | `clasificador_v4.md:7-16, 83-86` | **No** — nada fusiona ni detecta duplicados en `ciclo.py`; `comparar_prompts.py:60-74` lo mide solo en calibración | Pendiente A4; 235 descartes «duplicado» en la corrida 10 muestran que el modelo sí declara duplicados, pero nada verifica los que no declara |
| `cambio_fisico` obligatorio (prueba de sustancia) | `clasificador_v4.md:18-47` | **Solo el esquema** — Pydantic exige el campo (`clasificador.py:62-64`), pero **no se persiste**: `guardar_insights` no lo escribe y `insight` no tiene la columna | `persistencia.py:103-116`; `PRAGMA table_info(insight)` sin `cambio_fisico`. H-025 |
| Categoría de una lista cerrada de 7 | `clasificador_v4.md:59-71` | **Parcial** — fuera de la lista el código escribe `otro` y conserva el insight | `clasificador.py:209`; corrida 10: **23 de 326 (7,1 %) en `otro`**, que no pueden correlacionar (`correlacionador.py:85, 333-348`). H-026 |
| Toda señal en insight o en descarte | `clasificador_v4.md:107-108` | **Sí** — `sin_contabilizar` se registra con `declarado=False` | `clasificador.py:227-231`, `persistencia.py:236-248`. Corrida 10: 1.018 en insights ∪ 1.632 en descarte = **2.487 = `senales_procesadas`**; 98 no mencionadas (3,9 %) quedaron registradas; 163 señales aparecen en ambos lados (usadas y declaradas «duplicado») |
| Códigos de descarte cerrados (8) | `clasificador_v4.md:110-123` | **No** — `motivo` es texto libre sin validar | Corrida 10: **307 motivos distintos fuera de la lista** («duplicado de la señal 3613…», «arrendamiento de un lote…») |
| Prohibido «se observa», «sugiere», «podría» | `clasificador_v4.md:100` | **No en producción** — `comparar_prompts.py:38-41` lo mide en calibración | — |
| Sin restricción de tipología ni de idioma (CA-M2.3, CA-M2.4) | `clasificador_v4.md:88-91` | Solo prompt; no hay nada en código que restrinja, así que se cumple por ausencia | — |
| ≥ 2 categorías distintas, ≥ 2 insights, `otro` no cuenta | `correlacionador_v2.md:12-33` | **Sí** — `ensamblar` | `correlacionador.py:76-85, 325-348` |
| «No copies citas ni URLs»; el sistema une la evidencia | `correlacionador_v2.md:57-61` | **Sí, estructural** — el esquema de salida no tiene campo de evidencia; `_unir_evidencia` la compone | `correlacionador.py:125-137, 281-299` |
| `confianza` ∈ {alta, media, baja} | `correlacionador_v2.md:54-55` | **Sí** — fuera del conjunto cae a `baja` | `correlacionador.py:350-352` |
| Contexto Bing: orientativo, nunca evidencia, no cites | `correlacionador_v2.md:98-102`; D1 | **Sí para evidencia** (validador R2 sobre los orígenes; el consolidado no copia evidencia). **No para el marcado**: D1 exige `contexto_no_verificado: true` y nunca se escribe | H-021 |
| El contexto estructural explica, nunca crea (regla 1) | `correlacionador_v2.md:84-87` | **Solo en calibración** — compuerta 1 de `comparar_correlacionador.py:355-381` con piso de ruido; nada en producción | Diseño declarado en CLAUDE.md §2.4 |
| Usa la banda, nunca el número (regla 2) | `correlacionador_v2.md:89-92` | **Sí en la entrada** (`ContextoBandeado` sin cifras ni años, `contexto.py:84-119`); **no en la salida** en producción | H-009 |
| Calificaciones previas ajustan el criterio (CA-M4.3) | `correlacionador_v2.md:104-111` | **Sí, cableado** — consulta `ciclo.py:184-196`, resumen por categoría en el prompt `correlacionador.py:216-233, 269-271` | **Nunca ejercitado**: 0 calificaciones. La consulta lee `calificacion` de **todas** las corridas de ciclos previos, no solo de las publicadas, así que H-013 (calificar un insight ajeno al informe) contaminaría también este bucle |

### 2.3 Por qué `contexto_no_verificado` nunca se escribe

D1 (Addendum 01): «todo insight correlacionado que haya usado contexto de Bing
debe marcarlo en su traza (`contexto_no_verificado: true`)». El contexto Bing
**sí llega al prompt**: `ciclo.py:427-432` pasa `[s.contenido for s in crudas if
fuente == "Bing"]` y `_serializar` lo inserta recortado a 400 caracteres
(`correlacionador.py:262-267`). Hay una señal Bing por municipio y ciclo (18 por
ciclo, 1.600 caracteres de media), así que **todos los consolidados de todas las
corridas se produjeron con contexto Bing en la entrada**. Pero:

- `InsightCorrelacionado` no tiene el atributo (`correlacionador.py:148-171`);
- `guardar_correlaciones` no lo asigna (`persistencia.py:144-161`);
- `ResultadoCorrelacion` no registra si hubo contexto.

Resultado: `contexto_no_verificado = 0` en los 1.213 insights (`SELECT`), incluidos
los 170 consolidados. La columna existe desde `949a8ff9e15d:117` y nadie la
conecta. Es una omisión, no una decisión: ningún documento la retira.

### 2.4 Linaje ausente en las corridas 11 y 12

`comparar_correlacionador.py --persistir` crea sus corridas y guarda sus
consolidados **sin pasar por el linaje**:

```
scripts/comparar_correlacionador.py:226-233
        with sesion() as s:
            for etiqueta, version in (("A", args.a), ("B", args.b)):
                c = crear_corrida(
                    s, id_ciclo, sorted(filas_por_muni),
                    version_correlacionador=version,
                )
scripts/comparar_correlacionador.py:307-313
        if args.persistir:
            with sesion() as s:
                for etiqueta, r in (("A", ra), ("B", rb)):
                    guardar_correlaciones(
                        s, r, ids_corrida[etiqueta], d,
                        {i.id: i.id for i in insights},
                    )
```

No llama a `registrar_prompt`, no pasa `id_prompt`, no pasa `version_clasificador`
(queda `None`), y `tipo_corrida` sale «completa» porque cubre los 18 municipios.
`SELECT`: corridas 11 y 12 → 39 y 42 insights, **81/81 con `id_prompt NULL`**,
`version_prompt = 'v1'` solo como etiqueta. Las corridas 1, 2 y 4 también tienen
NULL (46 filas), pero son anteriores a `a6ac249fcec9` y la migración lo declara.
Consecuencias: (a) el piso de ruido de la compuerta (`PISO_RUIDO`) se midió sobre
corridas cuyo prompt no está anclado por hash —la etiqueta dice v1, pero D7 existe
justo porque la etiqueta no ancla—; (b) `ciclos_publicables` ya las excluye por
`_corrio_la_cadena` (`publicacion.py:66-86`), así que no pueden publicarse.

### 2.5 Hallazgos

**H-021 · Medio · Brecha · Confianza Alta · Área 2 · Addendum 01 D1 (implicación de trazabilidad), CA-M4.4**
*Ningún consolidado marca que usó contexto Bing, aunque todos lo recibieron.*
Evidencia en §2.3. *Escenario:* una gerencia lee una convergencia cuya
`por_que_convergen` se apoyó en el texto de Bing («generado por LLM, NO
verificado», D1) y nada en el dato lo distingue de una convergencia apoyada solo
en evidencia validada. El validador impide que Bing sea evidencia; no impide que
oriente la correlación, que es exactamente lo que D1 pidió marcar. Medio: no
rompe H4 (la evidencia sigue siendo verificable) pero incumple una implicación
explícita del addendum normativo.

**H-022 · Medio · Brecha · Confianza Alta · Área 2 · Addendum 02 D7, CA-M8.2**
*El script de comparación persiste corridas sin linaje de prompt.* Evidencia en
§2.4: 81 insights en las corridas 11 y 12 con `id_prompt NULL` y sin
`registrar_prompt`. *Escenario:* si `correlacionador_v1.md` se editara sin cambiar
la versión —el caso que D7 y `linaje.py:13-16` existen para detectar—, nada
delataría que el piso de ruido de la compuerta se midió con otro prompt. El
control v1-vs-v1 es la base de A11 y de la promoción de v2.

**H-023 · Medio · Brecha documental · Confianza Alta · Área 2 · CLAUDE.md §4 (M4 «v2 vigente»), pendiente A10, P-1**
*«v2 vigente» no tiene ninguna corrida registrada detrás.* `prompt_version` no
tiene fila v2; ninguna `corrida_agentes` tiene `version_correlacionador = 'v2'`;
las cifras que sostienen la promoción (40 convergencias frente al rango 39–42,
tipología 35 frente a 24) se produjeron en una ejecución de
`comparar_correlacionador.py` **sin `--persistir`** o no se conservaron. El
informe publicado es v1 (§2.1). *Escenario:* el área 8 no podrá reproducir la
evidencia de A10 desde la base, y `CLAUDE.md` describe como vigente un prompt que
las gerencias no van a leer. Se resuelve con P-1.

**H-024 · Bajo · Riesgo · Confianza Alta · Área 2 · CLAUDE.md §9 (documentado)**
*El Clasificador no pasa por `techo_de`.*

```
src/territorial/agentes/clasificador.py:165
            max_output_tokens=cfg.max_tokens_salida,
```

frente a `techo_de("correlacionador", cfg)` en `correlacionador.py:434`. Hoy los
dos techos valen 16.384 y no cambia nada; `CLAUDE.md` §9 lo declara como «detalle
menor pendiente». Se consigna para la matriz.

**H-025 · Bajo · Brecha · Confianza Alta · Área 2 · Prompt v3/v4 («prueba de sustancia»), CA-M2.5**
*`cambio_fisico` —la respuesta obligatoria que justifica cada insight— se exige
al modelo y se descarta al persistir.* El esquema lo requiere
(`clasificador.py:62-64`) y `clasificar_lote` lo conserva en el dict
(`clasificador.py:212`), pero `guardar_insights` no lo escribe y la tabla no tiene
la columna. *Escenario:* al diagnosticar A4 o revisar por qué un insight pasó la
prueba de sustancia, la respuesta del modelo ya no existe.

**H-026 · Bajo · Defecto · Confianza Alta · Área 2 · CA-M2.2**
*23 de los 326 insights del Clasificador en la corrida 10 (7,1 %) no tienen
categoría válida.* El prompt exige una de siete; el código sustituye por `otro`
(`clasificador.py:209`) en vez de rechazar o reintentar, y esos insights no pueden
entrar a una convergencia. CA-M2.2 exige «categoría» por insight; `otro` no es
una. Bajo porque la degradación está contenida (`CATEGORIA_DESCONOCIDA`), y
`CLAUDE.md` §9 ya registra que la calidad de categorización cae con lotes
grandes.

### 2.6 Estado de los CA del área

| CA | Estado | Base |
|---|---|---|
| CA-M2.1 | **Cumple (medido en el área 8)** | Reducción calculable desde `corrida_agentes.senales_procesadas` y `descarte`; la cifra reportada (95,2 %/94,9 %) se verifica en el área 8 |
| CA-M2.2 | **Parcial** | DIVIPOLA, resumen, implicación y evidencia siempre; categoría inválida en el 7,1 % (H-026) |
| CA-M2.3 · CA-M2.4 | **Cumple** | Declarados en el prompt (`clasificador_v4.md:88-91`); nada en código restringe idioma ni tipología |
| CA-M2.5 | **Cumple** | Contabilidad señal a señal cerrada: 2.487 = 2.487 en la corrida 10; los no mencionados quedan con `declarado=False`. Los códigos de descarte no se validan (texto libre) |
| CA-M4.1 | **Cumple** | Cruce de ≥ 2 categorías conocidas exigido por código; 38 consolidados en la corrida 10 |
| CA-M4.2 | **Cumple (v1); v2 sin ejercitar** | `implicacion_inmobiliaria` obligatoria en el esquema; el contexto bandeado que debía mejorarla (v2) no ha corrido en ninguna corrida registrada (H-023) |
| CA-M4.3 | **No verificable** | Cableado y probado con datos sintéticos (`test_correlacionador.py`, no abierto); 0 calificaciones. Riesgo de contaminación vía H-013 |
| CA-M4.4 | **Cumple** | Verificado 23/23 consolidados del informe (área 4) |
| CA-M8.2 (linaje de prompt) | **Parcial** | Completo en las corridas de `procesar_ciclo`; ausente en las del script de comparación (H-022) |

### 2.7 No verificable en esta área

- Reproducibilidad del Clasificador y del Correlacionador (A6 19,5 %, A11 14,1 %):
  exige volver a llamar al modelo; se verifica en el área 8 solo la
  reproducibilidad de las **cifras** desde las corridas persistidas (7/8 y 11/12).
- Efecto real del bloque de contexto bandeado sobre la salida: no existe corrida
  registrada de v2.

### 2.8 Decisión del dueño sobre P-1 (2026-09-22)

**Se mantiene publicado el informe 5 con el Correlacionador v1.** `CLAUDE.md`
debe corregirse para declarar **v1 como la versión publicada** y **v2 como
candidata**, pendiente de una comparación con linaje persistido
(`comparar_correlacionador.py --persistir` con `registrar_prompt`, hoy ausente:
H-022). La corrección de `CLAUDE.md` **no se hace en esta auditoría**: entra al
plan de remediación como subfase de F0. P-1 queda cerrada con esta decisión.

**H-022 y H-023 quedan sin la etiqueta «Bloquea distribución».** Condición
registrada: **si el dueño cambiara la decisión y republicara el ciclo 3 con v2,
ambos pasarían a «Bloquea distribución»**, porque entonces la corrida publicada
dependería de una comparación cuyo prompt no está anclado por hash (H-022) y de
una evidencia de promoción que no está persistida (H-023).

*Fin del área 2.*

---

## Área 8a — Integridad de la evidencia, primera mitad de `informe_resultados.md`

**Cerrada el 2026-09-22.** Cubre las líneas 1–317 del documento: «Cómo leer las
cifras», «0. Estado de las cinco hipótesis», H1, H2, H3 y H4. La segunda mitad
(H5, «Hallazgos no previstos» 1–8, Anexo CA-M2.1 y «Qué falta para poder
cerrar la compuerta», líneas 318–702) es el área 8b. El documento está fechado
**2026-09-21** y declara como última medición las corridas 11 y 12. Todas las
cifras se reprodujeron con `SELECT` sobre SQLite (datos de pipeline idénticos a
Neon, §0.7) en el commit `96e10e0`; ningún script del repositorio se ejecutó
para producirlas salvo la lógica de `comparar_pasadas.destino_por_senal`, que se
reimplementó en solo lectura.

### 8a.1 Medición de H-021 (encargo del dueño)

Sobre los 241 insights publicados se buscó, en `resumen`, `implicacion_inmobiliaria`
y `por_que_convergen`, cualquier **cifra** (≥3 dígitos) o **nombre propio**
(secuencia con mayúscula inicial que no abre oración, excluidos genéricos y el
nombre del municipio y del departamento) que apareciera en el texto Bing del
municipio en el ciclo 3 y **no** en el texto ni en los `datos` de sus señales de
origen.

| Búsqueda | Insights afectados |
|---|---|
| Cifras presentes en Bing y ausentes en las señales | **0 de 241** |
| Nombres propios presentes en Bing y ausentes en las señales | **0 de 241** |

Una primera pasada con una heurística más laxa marcó 56 insights, todos por
verbos al inicio de oración («Mejora», «Ordena», «Aumenta»): falsos positivos que
la pasada definitiva excluye. **Límite del método:** es una heurística léxica; no
detecta paráfrasis ni afirmaciones tomadas de Bing sin nombres ni cifras.

**Veredicto:** no hay evidencia medible de que el texto de Bing haya aportado
contenido identificable a lo publicado. **H-021 se mantiene en Medio y no
bloquea distribución.** Sigue siendo una brecha de trazabilidad —D1 exige el
marcado y el dato no permite saber qué convergencias se orientaron por Bing—,
pero no un contagio detectado.

### 8a.2 Cifras de la primera mitad: productor, pertinencia y reproducibilidad

«Productor» es el código o la consulta que produce la cifra en `96e10e0`;
«mide lo definido» pregunta si la cifra mide lo que la hipótesis o el criterio
citado definen; «reproducible» es el resultado de rehacerla hoy.

| Cifra en el documento | Productor | ¿Mide lo definido? | Reproducible en `96e10e0` |
|---|---|---|---|
| **§0** 18 municipios · 20.030 señales (19.640 / 336 / 54) · ventanas 51, 84, 239 días | `SELECT count(*)` sobre `municipio`, `senal_cruda`, `ciclo` | Sí (inventario) | **Sí**, exacto |
| §0 corridas de agentes **10** · corridas de scoring **21** · insights **1.132** · informes publicados **0** | `SELECT count(*)` | Inventario | **Desactualizado**: hoy 12, 24, 1.213 y 1 (Neon). El propio documento cita las corridas 11 y 12 como última medición y su tabla no las cuenta (H-031) |
| §0 descartes 5.731 · trazas 266 · calificaciones 0 | `SELECT count(*)` | Inventario | **Sí**, exacto |
| **H1** corridas 7 y 8: 344 y 365 insights; 1.140 y 1.160 evidencias | `SELECT count(*)`, suma de `len(evidencia)` por corrida | Sí (volumen por pasada) | **Sí**, exacto |
| H1 A6: **22,4 %** cambian de destino; **543 (19,5 %)** en insight en una pasada y no en otra | `scripts/comparar_pasadas.py --a 7 --b 8` (`destino_por_senal`, 44-65); reimplementado en solo lectura | Sí: mide reproducibilidad del Clasificador señal a señal, que es lo que A6 define | **Sí**: 625/2.786 = 22,4 %; 543/2.786 = 19,5 % |
| H1 «entre el **25 % y el 50 %** del contenido del informe del top 3 depende de qué pasada se publicó, según criterio laxo o estricto» | **Ninguno.** No hay script, consulta ni definición de «criterio laxo» y «estricto» en el repositorio; `pendientes.md` A6 repite la cifra sin método | No evaluable | **No reproducible** (H-030) |
| H1 A11: Correlacionador reproduce el **14,1 %** de sus convergencias | `comparar_correlacionador.py` (huellas por `frozenset` de ids, 157-165); reimplementado sobre `ids_insight_origen` de las corridas 11 y 12 | Sí | **Sí**: 10 idénticas de 71 distintas = 14,1 %; 85/322 = 26,4 % voltean |
| **H2** 10 mostrados, 3 pedidos; denominador = carga pedida | `Config.tope_top`, `composicion.py:259, 416-423` | Es la definición decidida (M9-carga), no una medición | Sí (configuración) |
| H2 «un 80 % en una gerencia podría ser una persona calificando por dos» | Ilustrativo, no medido | — | No aplica |
| **H3** supervivencia RSS **98 % y 100 %**, SECOP **99 %** `[pendientes B7, ciclo 3]` | Insights del Clasificador con evidencia de esa fuente: validados/total, por corrida | Sí para CA-M3.3 tal como el PRD la define (% que sobrevive al validador); **no mide alucinación respecto del mundo** (8a.3) | **Sí**: corrida 10 RSS 53/54 = 98,1 %, SECOP 269/272 = 98,9 %; corrida 9 RSS 5/5 = 100 %. El documento no dice de qué corridas salen los dos valores de RSS |
| H3 conversión RSS **46 %**, SECOP **40 %** | Señales de la fuente enviadas al Clasificador que acaban en insight validado / enviadas, corrida 10 | Sí (rendimiento del prefiltro, A2) | RSS **46,0 %** (120/261) exacto; SECOP **39,0 %** (869/2.226): el documento redondea a 40 |
| H3 **136** descartes RSS, **128** `sin_implicacion_inmobiliaria` | `descarte` ⋈ `senal_cruda` (fuente RSS), corrida 10 | Sí | 128 exacto; el total es **141 filas** (137 declaradas + 4 no mencionadas), no 136 |
| H3 **15 insights cruzan RSS con SECOP** | Consolidados de la corrida 10 con evidencia de ambas fuentes | Sí (CA-M4.1) | **Sí**: 15 de 38; ningún insight del Clasificador cruza fuentes |
| H3 corrida 10: **364 insights sobre 1.382 evidencias**; corrida 7: **1.140** | `SELECT` | Sí | **Sí**, exacto |
| H3 y H4 «la tasa de rechazo del validador es **0,0 %**» `[CLAUDE §4]` (dos veces: líneas 263 y 296) | Ninguno en el documento; `CLAUDE.md` §4 la afirma sin productor | Mide fidelidad de cita (8a.3) | **No**: corrida 9 0,0 % (10 insights), **corrida 10 1,2 %** (4/326), corrida 7 2,2 %, corrida 8 4,4 %. Las corridas 7, 8 y 10 ya existían cuando se escribió el documento (H-028) |
| **H4** «**266 trazas** con tokens de entrada, de salida, duración y **hashes de entrada y de salida**» `[BD]` | `SELECT` sobre `traza_agente` | Sí (CA-M8.2) | **No**: 266 trazas, `hash_input` en 215, **`hash_output` en 0** (H-027) |
| H4 descartes **5.455 declarados y 276 no declarados** | `SELECT sum(declarado)` | Sí (CA-M2.5) | **Sí**, exacto |
| H4 «Ninguna cifra del informe viene del LLM (CA-M6.3)» | Composición por código (área 3) | Parcial: verdadero para las cifras estructuradas; la prosa publicada lleva 15 cifras transcritas por el modelo sin compuerta (H-009, decisión P-3) | Parcial |
| H4 «Los prompts se anclan por hash; editar uno sin subir la versión levanta `PromptDivergente`» | `linaje.py:39-78` | Sí (D7) | **Sí** para las corridas de `procesar_ciclo`; **no** para las del script de comparación (H-022) |
| H4 «La evidencia la une el código, no el modelo» | `correlacionador.py:281-299` | Sí (CA-M4.4) | **Sí**, verificado 23/23 consolidados (área 4) |
| H4 «No hay informes publicados» | `SELECT count(*) FROM informe` | Estado | **Desactualizado**: informe 5 publicado el 2026-09-22 (posterior al documento) |
| Regla de decisión `[PRD §11]` | Cita | — | **Cita errónea**: la compuerta está en PRD **§9**; §11 no existe (H-032) |

### 8a.3 Encargos del dueño sobre esta mitad

**La tasa de rechazo mide fidelidad de cita contra lo ingerido, no alucinación
respecto del mundo.** El documento no usa la palabra «alucinación» en esta
mitad; presenta la cifra como «supervivencia al validador» y, en H3, advierte
que «un rechazo del 0 % no distingue “el modelo no alucina” de “el validador no
aprieta”» (263-265). **No declara el alcance real del validador**: R6 comprueba
que la cita esté en el texto que se le entregó al modelo (`validador.py:134-136`,
`149-151`); nada comprueba que ese texto sea verdadero, que la URL resuelva ni
que el insight interprete bien la señal. Bajo el snapshot, la tasa es una medida
de **fidelidad de transcripción**, y CA-M3.3 la llama «tasa de alucinación
medida». Un lector del informe de resultados no puede saberlo desde el texto.
H-029.

**H-011 bajo el criterio C(ii) y la lectura de H1.** La sección H1 condiciona la
lectura del criterio solo por A6 (banda de error de qué se publica). No dice que
**qué municipios se muestran y en qué puesto** —y por tanto qué insights se piden
calificar— lo decide el scoring determinista, cuyos factores F1–F3 (el 54 % del
peso) dependen del diccionario de obra por subcadena (H-011). Una calificación
baja de una gerencia puede significar «el insight es malo» (M2/M4, lo que H1
quiere medir) o «este municipio no debía estar aquí» (M5), y el documento no
prepara esa distinción. La segunda mitad (8b, hallazgos 5 y 6) trata el scoring;
si tampoco la establece, H-033 se consolida allí.

**Qué afirma el documento sobre H1, H2 y CA-M4.3 sin calificaciones.** H1 y H2
están marcadas «⬜ Sin medir — cero calificaciones», coherente con el encuadre de
§0.11.2. **CA-M4.3 no aparece en ninguna línea de las 702 del documento**: el
bucle de aprendizaje que el PRD llama «el bucle de aprendizaje del MVP» no se
menciona ni como pendiente, aunque está cableado y sin ejercitar (área 2) y aunque
la interpretación de un tercer ciclo dependería de él. H-033.

**Evidencia no persistida de la promoción de v2:** vive en las líneas 485-504
(hallazgo 4 del documento) → área 8b.

### 8a.4 Hallazgos

**H-027 · Alto · Defecto · Confianza Alta · Área 8a · H4 (bloqueante), CA-M8.2 · ⛔ BLOQUEA DECISIÓN GO/NO-GO**
*El informe de resultados afirma en la sección de H4 que las 266 trazas llevan
«hashes de entrada y de salida» `[BD]`, y no es cierto.*

```
docs/informe_resultados.md:279-281
- **Trazas por agente** (CA-M8.2): **266 trazas** con tokens de entrada, de
  salida, duración y hashes de entrada y de salida. `[BD]`
```

`SELECT`: `hash_output` es NULL en 266/266; `hash_input` es NULL en 51/266 (todas
las del Correlacionador). Es una afirmación de evidencia a favor de la hipótesis
bloqueante, marcada como salida de la base, que la base contradice. Alto por la
regla del área: un resultado reportado que no se reproduce, en la sección que
decide el GO.

**H-028 · Alto · Defecto · Confianza Alta · Área 8a · H3, H4, CA-M3.3 · ⛔ BLOQUEA DECISIÓN GO/NO-GO**
*«La tasa de rechazo del validador es 0,0 %» se afirma dos veces y la base la
contradice.* Corrida 10: 4/326 = **1,2 %**; corrida 7: 7/320 = 2,2 %; corrida 8:
15/342 = 4,4 %; solo la corrida 9 (10 insights) da 0,0 %. Las corridas 7, 8 y 10
son anteriores al documento. La cifra se cita `[CLAUDE §4]` y `CLAUDE.md` §4 la
repite («Tasa de rechazo 0,0 % tras corregir el falso positivo»), también sin
productor. *Escenario:* el lector concluye que el validador «no aprieta» —el
propio documento lo plantea— cuando en realidad rechaza entre el 1 % y el 4 %
por citas no localizables, que es la señal que H4 necesita. Alto: cifra
reportada no reproducible en la sección de la hipótesis bloqueante. Corregir
también `CLAUDE.md` §4.

**H-029 · Medio · Brecha documental · Confianza Alta · Área 8a · CA-M3.3, H3, H4**
*El documento no declara que la tasa de rechazo mide fidelidad de cita contra
el contenido ingerido.* Evidencia en 8a.3. Sin esa frase, «≥60 % sobrevive al
validador» se lee como «≥60 % es verdadero», y no es lo que se midió. Medio: no
altera la cifra, altera lo que significa.

**H-030 · Alto · Brecha documental · Confianza Alta · Área 8a · H1, A6 · ⛔ BLOQUEA DECISIÓN GO/NO-GO**
*«Entre el 25 % y el 50 % del contenido del informe del top 3 depende de qué
pasada se publicó» no tiene productor.* No existe script, consulta ni definición
de «criterio laxo» y «criterio estricto» en el repositorio ni en `pendientes.md`
A6, que repite el rango. Alto por la regla acordada para el área («un número sin
código que lo produzca es Alto»); es además la cifra que el documento usa para
pedir «banda de error» en H1. Confianza Alta en que no hay productor; la cifra
puede ser correcta, pero no se puede saber.

**H-031 · Bajo · Brecha documental · Confianza Alta · Área 8a · §0 y estados**
*Inventario y estados desactualizados o internamente inconsistentes.* La tabla de
§0 cuenta 10 corridas de agentes, 21 de scoring, 1.132 insights y 0 informes
publicados; el mismo documento declara como última medición las corridas 11 y 12
(que suman 81 insights) y hoy hay 12, 24, 1.213 y 1. H1 y H2 dicen que «M7 y M9
no tienen código» y que «Django no está instalado», cuando la decisión de
Next.js es del 2026-09-21 y `web/` existe. Dos cifras con desviación menor: SECOP
convierte 39,0 % (el documento dice 40 %) y los descartes RSS son 141 filas / 137
declaradas (dice 136). Bajo: nada de esto mueve una hipótesis, pero el documento
se presenta como «cada cifra lleva su procedencia para que se pueda volver a
comprobar» y varias no pasan la comprobación literal.

**H-032 · Bajo · Brecha documental · Confianza Alta · Área 8a · PRD §9**
*La regla de decisión se cita como `[PRD §11]` dos veces (líneas 29 y 696); está
en PRD §9 y el PRD no tiene §11.*

**H-033 · Medio · Brecha documental · Confianza Alta · Área 8a · H1, CA-M4.3, H-011**
*La lectura de H1 omite dos condicionantes.* (a) Qué se califica lo decide el
scoring —tope 10, los 3 primeros pedidos— y el 54 % de ese score depende del
diccionario de obra (H-011): una calificación baja no distingue insight malo de
municipio mal seleccionado, y la sección solo advierte de A6. (b) **CA-M4.3 no se
menciona en el documento**: el bucle de aprendizaje está cableado y jamás
ejercitado, y la comparación entre ciclos que H1 supone lo daría por activo.
Consolidación pendiente de 8b (hallazgos 5 y 6 del documento).

### 8a.5 No verificable en esta mitad

- Las cifras de `[pendientes B7]` que el documento atribuye al «ciclo 3» sin
  corrida: se reprodujeron sobre la corrida 10 (y la 9 para el 100 % de RSS); si
  salieron de otra pasada no persistida, no hay forma de saberlo.
- Las «hojas de revisión del equipo —5 personas, 45 insights—» (H1): no hay
  artefacto en el repositorio; `scripts/generar_hojas_revision.py` existe y no se
  abrió (área 10).

*Fin del área 8a.*

---

## Área 8b — Integridad de la evidencia, segunda mitad de `informe_resultados.md`

**Cerrada el 2026-09-22.** Cubre las líneas 318–702: H5, «Hallazgos no
previstos» 1–8, Anexo CA-M2.1 y «Qué falta para poder cerrar la compuerta».
Archivos leídos completos para esta mitad: `scripts/estimar_costo.py`,
`scripts/generar_hojas_revision.py`. Ejecutado: `scripts/estimar_costo.py` (solo
lee `traza_agente` y `config/tarifas.json`) y `SELECT` sobre SQLite para cada
cifra.

### 8b.1 Cifras de la segunda mitad: productor, pertinencia y reproducibilidad

| Cifra en el documento | Productor | ¿Mide lo definido? | Reproducible en `96e10e0` |
|---|---|---|---|
| **H5** piloto **USD 39/año**, nacional **USD 2.160/año** `[pendientes B4]` | `scripts/estimar_costo.py` con `config/tarifas.json` | Sí para «extrapolación documentada» | **No**: hoy el script da **USD 1,15 por quincena de 18 → 29,9/año** y **USD 1.825/año nacional**. La estimación promedia los tokens del Correlacionador sobre **todas** las trazas acumuladas (`estimar_costo.py:175-176`), así que cambia cada vez que se corre algo; el documento no fija ni la fecha ni el corte de trazas (H-035) |
| H5 «el Correlacionador es el 89 % del gasto» | Derivado de la proyección | Sí | Hoy **86,9 %** (USD 1.586 de 1.825); el 89 % correspondía a otro estado de `traza_agente` |
| H5 «su salida de razonamiento sola es el 84 % del total» | **Ninguno**: `traza_agente` no tiene columna de tokens de razonamiento (`PRAGMA`); `ResultadoCorrelacion.tokens_razonamiento` existe en memoria y no se persiste | — | **No reproducible** desde la base (H-035) |
| H5 «Batch (−50 %) y bajarlo a mini (−71 %) se acumulan hasta −86 %» | Aritmética sobre tarifas | Hipotético | 1 − 0,5 × 0,29 = 0,855 ✓, con tarifas de `tarifas.json` |
| H5 consumo medido: Clasificador 215 llamadas, 1.759.734 / 459.192, 39,5 min; Correlacionador 51, 140.172 / 264.562, 48,6 min `[BD]` | `SELECT` sobre `traza_agente` | Sí | **Sí**, exacto (39,47 y 48,61 min) |
| H5 ciclo 1 dos veces: 170 llamadas, 1.276.657 / 441.861, 53,6 min; «~638K y ~221K por pasada, ~27 min» | `SELECT` por `id_ciclo=1` | Sí | **Sí**: 170, 1.276.657, 441.861, 53,59 min |
| H5 «7.628 tras el prefiltro; ~615 por quincena; factor 12» `[CLAUDE §8]` | `medir_prefiltro.py` (7.628 ✓, área 3); 615 = 7.628 / 374 × 14 × … | Sí | 7.628 exacto; **615 sin productor en el repo** (`estimar_costo.py:51` lo lleva como constante `SENALES_POR_QUINCENA_18 = 615`; 7.628/374×14 = 285,5, así que la constante no sale de esa fórmula) |
| Tokens por señal del Clasificador: **~282 / ~111** `[CLAUDE §8]` | Ninguno | — | **Tres cifras distintas en tres sitios**: `CLAUDE.md` §8 282/111; `estimar_costo.py:48-49` **240/92** (medido sobre Barranquilla ciclo 2, 284 señales); `corrida_agentes` da **225/78** (corridas 7 y 8) y **218/100** (corrida 10). El documento no elige ninguna, el script proyecta con 240/92 |
| **Hallazgo 1** volteo por municipio: Barranquilla **10 %**, Funza **87,5 %** `[pendientes A6]` | Lógica de `comparar_pasadas.py` por municipio | Sí | **Sí**: 90/897 = 10,0 %; 35/40 = 87,5 % |
| Hallazgo 1 descartes: `servicios_profesionales` **1.618**, `duplicado` **911**, `evento_capacitacion` **798** `[BD]` | `SELECT motivo, count(*)` | Sí | **No**: exacto 1.290 / 810 / 705; por prefijo 1.637 / 922 / 802. Ninguno de los dos métodos da las cifras del documento, y `descarte` no ha cambiado (5.731 filas) |
| **Hallazgo 2** (A11): 10 de 71 = 14,1 %; 85/322 = 26,4 %; **14 de 18** municipios; 39 y 42; tipología **23 y 24** | Corridas 11 y 12 | Sí | **Sí**, todo exacto (tipología recalculada con las palabras de `comparar_correlacionador.py:124-128`) |
| **Hallazgo 3** «0 % / 19,5 % / 26,4 % / 25–50 %» | Compuesto de A6, A11 y la cifra sin productor | — | 0 % ✓ (área 3: scoring reproducido con diferencia 0); 19,5 % ✓; 26,4 % ✓; **25–50 % no** (H-030) |
| **Hallazgo 4** tabla: v1 pasada 1 **42/20**, pasada 2 39/23, pasada 3 42/24; **v2 40/35** `[pendientes A10]` | `comparar_correlacionador.py`; constantes `PISO_RUIDO` (94-99) | Sí para la compuerta | **Parcial**: 39/23 y 42/24 son las corridas 11 y 12; **42/20 y 40/35 no tienen corrida** —la pasada A del contraste v1/v2 y la pasada v2 no se persistieron— y solo existen como constantes del script y como afirmación del documento (H-036) |
| Hallazgo 4 «calles 76 y 80», Carepa, corrida 12 | `tests/test_cifras.py:14-18` | Anecdótico | Sí, como caso de prueba |
| **Hallazgo 5** Apartadó F4 **−43,5 %** en los tres ciclos | `score_municipio.valores_crudos` | Sí | **Sí**: −43,5 en las corridas 22, 23 y 24; F4 idéntico en 18/18 |
| Hallazgo 5 top 3 antes/después, corridas 16/8/18 → 19/20/21 `[BD]` | `SELECT … ORDER BY ranking LIMIT 3` | Sí | Ciclos 1 y 2 **exactos** (Carepa/Barranquilla/Armenia → Barranquilla/Carepa/Pereira; Ibagué/Carepa/Buenaventura → Carepa/Ibagué/Buenaventura). **Ciclo 3 no**: las corridas 18 y 21 dan Ibagué/Armenia/Funza; el documento escribe «Funza, Buenaventura, Facatativá», que es el top 3 **con el umbral de información activo** (excluidos los cinco del hallazgo 7), sin decirlo |
| Hallazgo 5 «F1, F3 y F5 varían entre ciclos: 18, 15 y 18 de 18» | Comparación de `valores_crudos` | Sí | F1 18 ✓, F5 18 ✓; **F3: 18 de 18** entre los ciclos 2 y 3 (5 municipios sin F3 en alguno); el 15 no se reproduce con ningún criterio evidente |
| **Hallazgo 6** seis violaciones de «ausencia de SECOP» `[CLAUDE §7]` | Narrativa sobre A7, `_corte`, A8, A2, B7, P1 | Cualitativo | Las seis tienen correlato en código leído (áreas 3 y 4); no es una cifra |
| **Hallazgo 7** fracciones informadas **20,10 % o 77,80 %**, cinco municipios fuera, top 5 «apoyado en» `[pendientes P1]` | `score_municipio.factores.fraccion_informada`, corrida 24 | Sí | **Sí**: {0,201, 0,778}; los 5 son Ibagué, Armenia, Barranquilla, Pereira y Cartagena; el top 5 coincide con el payload publicado |
| **Hallazgo 8** atribución cruzada **0,64 %**; pares 31 / 20 / 10 / 8 `[pendientes A3]` | Ninguno declarado; reimplementado como «nombre de otro municipio del MVP en el objeto SECOP» | Sí como piso | **Aproximado**: 129/19.640 = **0,66 %**; Manizales→La Dorada **32**, Barranquilla→Puerto Colombia 20 ✓, Pereira→Dosquebradas 10 ✓, Apartadó→Chigorodó 8 ✓, más Buenaventura→«Mosquera» 11 que el documento omite (probable apellido). Método no declarado |
| **Anexo CA-M2.1**: 95,2 % · 94,9 % · 95,3 % `[pendientes B2]` | `ResumenCiclo.reduccion_global` = 1 − validados / señales del ciclo | Sí, tal como CA-M2.1 se reinterpretó (validados sobre crudas) | **Sí**, exacto: 313/6.454, 327/6.454, 322/6.831 |
| «Qué falta»: «Django sin instalar», «Canal sin decidir `[pendientes 11.4/3]`» | Estado | — | **Desactualizado**: Next.js decidido el 09-21; 11.4/3 cerrado |
| Hojas de revisión: 45 insights, 5 revisores, 30 estables + 15 volteados | `scripts/generar_hojas_revision.py:113-116` (defaults 30/15/5, corridas 7 vs 8, semilla 20260921) | Sí | El generador existe y es determinista; **las hojas no están en el repositorio** (`data/revision/`, ignorado) y no hay devolución |

### 8b.2 Encargos del dueño sobre esta mitad

**Evidencia no persistida de la promoción de v2.** Confirmado (tabla, hallazgo
4): de las cuatro filas que justifican la promoción, dos son las corridas 11 y 12
y dos —la pasada 1 de v1 (42/20) y **la única pasada de v2 (40/35)**— no existen
en la base. `PISO_RUIDO = {"convergencias": (42, 39, 42), "tipologia": (20, 23,
24)}` (`comparar_correlacionador.py:94-99`) codifica un valor no persistido, y
`tests/test_compuertas.py` prueba esas constantes, no una medición. H-036.

**Consolidación de H-033.** Los hallazgos 5, 6 y 7 tratan el scoring con detalle
—F4 constante, ausencia de SECOP, umbral apagado— pero **ninguno conecta con la
lectura de H1**: en ninguna línea se dice que lo que las gerencias califican lo
seleccionó el scoring y que el 54 % de ese score depende del diccionario de
obra. CA-M4.3 sigue sin aparecer. **H-033 se consolida en Medio** tal como se
redactó en 8a.

**H5 con la tarifa de `gpt-5.4-mini` sin verificar.** `config/tarifas.json`
lleva la advertencia en su propio texto («la cotización se pidió para gpt-5-mini.
Verificar que la tarifa aplique al despliegue que corre de verdad»). La tarifa
real **no está en el repositorio y no se busca fuera** (decisión del dueño). El
efecto se calcula como condicional sobre la proyección que el script produce hoy:

| Componente (año nacional, USD) | Con la tarifa aplicada (0,25 / 2,00) |
|---|---|
| Correlacionador (`gpt-5`, 1,25 / 10,00) | **1.586** (78,8 M entrada + 148,8 M salida) |
| Clasificador (`gpt-5.4-mini`, tarifa **sin verificar**) | **239** (235,2 M entrada + 90,1 M salida) |
| Total | **1.825** |

Si la tarifa real de `gpt-5.4-mini` es *k* veces la aplicada: total = 1.586 +
239 × *k*. Con *k* = 0,5 → 1.706; *k* = 2 → 2.064 (+13 %); *k* = 5 → 2.782
(+52 %); *k* = 10 → 3.977 (+118 %). **El total se duplica en *k* ≈ 7,6.** La
conclusión de H5 —«el costo no es la barrera»— no cambia con ningún *k* dentro
de un orden de magnitud, porque el Clasificador es el 13 % del gasto; **las
cifras publicadas sí cambian** con cualquier *k* ≠ 1, y ya no coinciden con el
script ni con *k* = 1. La tarifa real queda como **P-5**.

### 8b.3 Causa raíz (encargo del dueño): cifras citadas de documentos, no de consultas

El documento declara «cada cifra lleva su procedencia entre corchetes para que se
pueda volver a comprobar». Recuento de marcas en las 702 líneas: **14 `[BD]`**,
**36 `[pendientes]`**, **17 `[CLAUDE]`**, 6 `[PRD]`. Es decir, **53 de 67
procedencias no son la base sino otro documento**, y ninguna de las 14 `[BD]`
adjunta la consulta. El patrón se confirma en las dos mitades:

| Síntoma | Cifras afectadas |
|---|---|
| `[CLAUDE]` que a su vez no tiene productor | «tasa de rechazo 0,0 %» (H-028); «~282/~111 tokens por señal» (tres valores distintos en tres sitios) |
| `[BD]` falsa o no reproducible con ningún método | «hashes de entrada y de salida» (H-027); descartes 1.618 / 911 / 798 |
| `[pendientes]` sin método ni corrida | «25–50 % del contenido» (H-030); «F3 varía en 15 de 18»; «0,64 %» (aproximado, método no declarado); top 3 del ciclo 3 con filtro no declarado |
| Cifra atada a un estado mutable sin corte | USD 39 / 2.160 y 89 % (H-035): dependen de `traza_agente` acumulada |
| Cifra de una ejecución no persistida | 42/20 y 40/35 de la promoción de v2 (H-036); 615 señales por quincena; 84 % razonamiento |
| Inventario y estados no refrescados | 10 corridas, 21 de scoring, 1.132 insights, 0 informes, Django, canal sin decidir (H-031) |

Lo que sí se reproduce exactamente —A6, A11, CA-M2.1, consumo medido, F4,
fracción informada, cruces RSS×SECOP— tiene en común que sale de corridas
persistidas con un cálculo que el repositorio contiene. **La causa raíz no es un
error de transcripción: es que el documento se escribió a mano copiando cifras
de `pendientes.md` y `CLAUDE.md`, que a su vez las recibieron de sesiones de
trabajo, sin que ninguna cifra quede ligada a la consulta o al script que la
produce ni al estado de la base (commit + corridas) en que se produjo.** H-034.

### 8b.4 Hallazgos

**H-034 · Alto · Brecha documental (causa raíz) · Confianza Alta · Área 8 · «Cómo leer las cifras» del propio documento; H1–H5 · ⛔ BLOQUEA DECISIÓN GO/NO-GO**
*Ninguna cifra de `informe_resultados.md` está ligada a la consulta o script que
la produce ni al estado de la base en que se produjo.* Agrupa H-027, H-028,
H-030, H-031, H-035 y H-036, y las cifras «método-dependientes» de 8b.1
(descartes 1.618/911/798, F3 15/18, top 3 del ciclo 3, 0,64 %, 615/quincena,
282/111). *Escenario:* la compuerta de la semana 8 se decide con un documento en
el que dos afirmaciones de la sección bloqueante son falsas y una docena no se
puede rehacer; corregir cifra a cifra reproduce el problema en la próxima
actualización. **Propuesta para el plan (F0b):** no corregir cifras sueltas sino
**regenerar el documento** desde un script (`scripts/informe_resultados.py` o
equivalente) que emita cada cifra con (a) la consulta o función que la produce,
(b) el commit y (c) los ids de corrida sobre los que se calculó; lo que no tenga
productor sale del documento o se marca explícitamente como «afirmación sin
medición». Las 19 cifras que hoy se reproducen exactamente son la semilla de ese
script.

**H-035 · Alto · Brecha documental · Confianza Alta · Área 8b · H5, CA-M8.3, pendiente B4 · ⛔ BLOQUEA DECISIÓN GO/NO-GO**
*Las cifras de H5 no se reproducen y dependen de un estado mutable.*
`estimar_costo.py:175-176` promedia los tokens del Correlacionador sobre todas
las trazas acumuladas:

```
scripts/estimar_costo.py:175-176
    ent_muni = sum((f[3] or 0) for f in corr) / sum(f[2] for f in corr) if corr else 0
    sal_muni = sum((f[4] or 0) for f in corr) / sum(f[2] for f in corr) if corr else 0
```

El documento dice USD 39 y 2.160 (2026-09-17); el mismo script en `96e10e0` da
USD 29,9 y 1.825; el 89 % es hoy 86,9 %; el «84 % de razonamiento» no tiene
columna que lo sostenga; los tokens por señal valen 282/111, 240/92 o 218–225
según el sitio. A esto se suma la tarifa de `gpt-5.4-mini` sin verificar
(8b.2, P-5) y el Sintetizador sin contar, que el documento sí declara. *Escenario:*
H5 es una de las tres hipótesis que el GO puede contar; su cifra no se puede
defender ante la compuerta porque quien la rehaga obtendrá otra. La conclusión
cualitativa («no es la barrera») es robusta; las cifras, no.

**H-036 · Alto · Brecha documental · Confianza Alta · Área 8b · Hallazgo 4 del documento, pendiente A10, CLAUDE.md §2.4**
*La promoción de v2 se apoya en dos mediciones que no existen en la base.* De la
tabla 42/20 · 39/23 · 42/24 · **40/35**, solo 39/23 y 42/24 (corridas 11 y 12)
se reproducen; la pasada A del contraste v1/v2 y la pasada v2 no se persistieron
y viven como constantes en `comparar_correlacionador.py:94-99` y en el texto.
`tests/test_compuertas.py:36-67` prueba esas constantes. Alto por la regla del
área (número sin productor). No lleva la etiqueta go/no-go porque no alimenta
H1–H5; **pasaría a «Bloquea distribución» si el dueño republicara con v2**
(§2.8).

**Enmienda a H-031** (Bajo): se añaden como ocurrencias las filas «Django sin
instalar» y «Canal sin decidir» de «Qué falta», ya cerradas en `pendientes.md`.

### 8b.5 Estado de CA y hipótesis tocados por el área 8

| Elemento | Estado tras el área 8 |
|---|---|
| CA-M2.1 | **Cumple**: 95,2 / 94,9 / 95,3 % reproducidos exactamente |
| CA-M3.3 | **Parcial**: la tasa existe (1,2 % corrida 10) pero el documento publica 0,0 % (H-028) y no declara qué mide (H-029) |
| CA-M8.3 | **Parcial**: costo por agente agregable a nivel de ciclo desde `traza_agente`; no por corrida (H-006) ni con tokens de razonamiento |
| H1, H2 | **No medidas** (encuadre del dueño, §0.11.2); el documento lo dice correctamente |
| H3 | Criterio cumplido (98,8 %), con la salvedad de qué mide (H-029) |
| H4 | La cadena está verificada al 100 % (área 4), pero **la sección H4 del documento contiene una afirmación falsa (H-027) y una cifra errónea (H-028)** |
| H5 | Conclusión cualitativa robusta; cifras no reproducibles (H-035); tarifa sin verificar (P-5) |

### 8b.6 No verificable en esta mitad

- Las cifras de la promoción de v2 (42/20, 40/35): no hay corrida; artefacto
  necesario: volver a correr el contraste con `--persistir` y `registrar_prompt`.
- El 84 % de tokens de razonamiento: no hay columna; artefacto: persistir
  `tokens_razonamiento` en `traza_agente`.
- Las hojas de revisión y su devolución: fuera del repositorio.

*Fin del área 8b.*

---

## Área 7 — Ejecución y operación

**Cerrada el 2026-09-22.** Sin archivos nuevos: todo lo citado estaba leído
completo desde el Preflight (`ciclo.py`, `correr_ciclo.py`, `calcular_scores.py`,
`cliente.py`, `agentes/persistencia.py`, `informes/publicacion.py`,
`informes/composicion.py`, `linaje.py`). Ejecutado, sin escrituras: regeneración
del payload del informe 5 con `componer(sesion_sqlite, 24, 10)` en una sesión
cerrada con `rollback`, comparada con el `contenido` publicado y con los tres
archivados en Neon; lectura de los valores por defecto del SDK `openai` instalado;
`grep` de reintentos, timeouts y bloqueos; `git log` de la publicación. **No se
ejecutó ningún ciclo ni se escribió en ninguna base**, así que no hizo falta la
copia temporal que el dueño autorizó condicionalmente.

### 7.1 Sondas

| Sonda | Respuesta | Evidencia |
|---|---|---|
| ¿Cómo se dispara un ciclo? | Manual, como fija D9: `scripts/correr_ciclo.py --ciclo N [--municipio D]… [--lote n] [--seco]` → `procesar_ciclo`. Sin cron ni workflow | `correr_ciclo.py:42-58`; §0.1 |
| ¿El informe 5 se puede regenerar desde `96e10e0`? | **Parcial.** `componer(24, 10)` sobre SQLite reproduce las 10 filas de municipios, los scores, las fuentes, el contexto, los `insights_pedidos`, los `tipo_pedido` y la raíz del payload **idénticos**; difiere en **5 de 10 municipios solo en el orden de la lista `insights`**, porque la consulta no ordena (`composicion.py:299-306`, `select(Insight)` sin `order_by`) y Neon y SQLite devuelven las filas en orden distinto (Funza: Neon `969, 967, 968…`, SQLite `967, 968, 969…`). El contenido ordenado por id es idéntico. **`publicar()` no tiene punto de entrada**: el informe no guarda el commit ni el comando que lo compuso; el rastro son cuatro filas —informes 2, 3, 4 y 5— publicadas el 2026-09-22 a las 14:32, 16:17, 16:45 y 16:53 UTC, con payloads de 16, 17, 18 y 18 claves por municipio (aparecen `semilla`, `composicion_pedida`, `tipo_pedido`, `aviso_corto`), y dos commits del código (`dbba66a` 12:58 UTC, `c9af35d` 15:00 UTC). El informe 2 se publicó **antes** de que existiera la guarda `_corrio_la_cadena` | Ejecutado; H-040 |
| CA-M8.4: ¿un ciclo que falla a mitad se reanuda sin reprocesar, o se duplica? | **Se duplica.** No hay reanudación: cada invocación llama a `crear_corrida` (`ciclo.py:507-513`) y procesa toda la cohorte. El commit por municipio (`ciclo.py:539-542`) **conserva lo pagado**, pero relanzar abre otra corrida y vuelve a llamar al modelo para los 18 municipios. Peor: la corrida interrumpida queda `tipo_corrida = completa` —`municipios_en_cohorte` es la lista **a procesar**, no la procesada (`persistencia.py:61-73`)— con `senales_procesadas` y tokens en 0 (se escriben al final, `ciclo.py:557-560`), y **`publicar()` la aceptaría** (`_exigir_completa` solo mira `tipo_corrida`; `_corrio_la_cadena` solo exige un insight del Clasificador) | H-037 |
| ¿Se persiste qué municipios fallaron? | **No.** `ResumenMunicipio.error` solo se imprime (`correr_ciclo.py:85-86`); un lote fallido se anota en el resumen y se sigue (`ciclo.py:346-362`); un error del Correlacionador deja el municipio con insights de M2 persistidos y sin M4, y `return resumen` antes de `guardar_correlaciones` (`ciclo.py:454-462`); la corrida no lo registra | H-037 |
| ¿`--seco` no escribe? | **Falso.** `procesar_ciclo` hace `commit()` tras cada municipio y tras el scoring (`ciclo.py:542, 555, 560, 569`); el `s.rollback()` de `correr_ciclo.py:63-64` llega cuando ya no queda nada por revertir. `CLAUDE.md` §6 dice «`--seco` corre y revierte» y el docstring «no escribe en la base». `calcular_scores.py --seco` sí es seco (`102-105`: no llama a `guardar`) | H-038 |
| ¿Qué impidió que las corridas 9 y 10 se solaparan? | **Nada.** No hay bloqueo, estado «en curso» ni comprobación de corridas abiertas (`grep` sin resultados). La 9 (`--municipio`, 50 señales) abrió a las 16:00:41 UTC y la 10 (los 18) a las 16:02:54, con la 9 aún escribiendo trazas. Dos `correr_ciclo.py` a la vez producen dos corridas válidas, trazas entremezcladas sin `id_corrida` (H-006) y, sobre SQLite, contienden por el único escritor: el `database is locked` que salte se traga como error de municipio y el ciclo sigue | H-039 |
| Idempotencia | Ninguna operación de agentes es idempotente por diseño: cada ejecución inserta. Es lo que A6 necesita y lo que el registro de corridas hace seguro; el precio es H-037/H-039. `registrar_prompt` sí es idempotente (`linaje.py:54-68`) y la ingesta también (`snapshot.py:160-209`) | — |
| Configuración del LLM | Despliegues por agente en `Config` (`config.py:33-35`) vía `despliegue_de` (`cliente.py:85-95`); techo 16.384 para los tres (`config.py:39, 49`, `techo_de` 105-110; el Clasificador no pasa por `techo_de`, H-024); cliente `OpenAI(api_key, base_url)` **sin `timeout` ni `max_retries`** (`cliente.py:73-76`) → rigen los del SDK 3.14.1: **2 reintentos, `connect` 5 s, `read` 600 s**; salida estructurada con `responses.parse` y `text_format` Pydantic | Ejecutado (`openai.DEFAULT_MAX_RETRIES`, `DEFAULT_TIMEOUT`) |
| ¿Qué pasa ante un error del proveedor a mitad de ciclo? | El SDK reintenta 2 veces; luego `clasificar_lote`/`correlacionar` capturan **cualquier** excepción y devuelven `error` (`clasificador.py:167-172`, `correlacionador.py:436-442`). El lote o el municipio se pierde, se imprime, la corrida sigue y termina `completa`. Una caída del proveedor de 20 minutos produce una corrida publicable con municipios vacíos y sin marca | H-037, H-041 |
| Trazas (CA-M8.2) y costo por agente (CA-M8.3) | Consolidado en H-006 (linaje de ejecución no atribuible por corrida; `hash_output`, `id_prompt`, `id_dataset` vacíos; corridas 11/12 sin traza) y H-035 (H5 depende de trazas acumuladas; tokens de razonamiento no persistidos). Sin hallazgo nuevo | Áreas 4 y 8 |
| Secretos | Solo en `.env` (21 nombres, §0.2 #21), nunca en código ni historial (0 patrones en `src/ scripts/ web/ alembic/`; §0.2 #20). Riesgo aceptado de la credencial de Neon en §0.9 | — |

### 7.2 Hallazgos

**H-037 · Alto · Defecto · Confianza Alta · Área 7 · CA-M8.4, CA-M6.7, CA-M1.4 (análogo), H1**
*Una corrida interrumpida, con lotes fallidos o con municipios sin correlación
queda marcada «completa», no registra qué falló y es publicable.* `tipo_corrida`
se decide antes de procesar:

```
src/territorial/agentes/persistencia.py:61-67
    objetivo = sorted(d for (d,) in sesion_bd.execute(select(Municipio.divipola)).all())
    cohorte = sorted(set(cohorte))
    completa = set(cohorte) >= set(objetivo)

    corrida = CorridaAgentes(
        id_ciclo=id_ciclo,
        tipo_corrida="completa" if completa else "parcial",
```

y los errores por municipio solo se imprimen (`correr_ciclo.py:85-86`). No hay
reanudación: `procesar_ciclo` siempre abre una corrida nueva y recorre los 18
(`ciclo.py:507-513, 530-537`). *Escenario:* el proceso muere en el municipio 12,
o el proveedor cae y seis lotes devuelven error: la corrida existe, dice
«completa», `senales_procesadas = 0`, y `ciclos_publicables()` la propone; el
informe publicado mostraría municipios con 0 insights «apoyados en» un score que
sí se calculó. Relanzar para completar cuesta los 18 municipios otra vez y deja
dos corridas «completas» del mismo ciclo sin nada que diga cuál está entera. El
commit por municipio que `CLAUDE.md` §4 y `ciclo.py:17-21` presentan como
checkpoint protege el gasto ya hecho, **no** cumple CA-M8.4 («se puede reanudar
desde el último checkpoint sin reprocesar»). Alto: puede publicar un ciclo
incompleto como evidencia de H1.

**H-038 · Medio · Defecto · Confianza Alta · Área 7 · `CLAUDE.md` §6, `correr_ciclo.py` docstring**
*`correr_ciclo.py --seco` escribe en la base y gasta tokens.*

```
scripts/correr_ciclo.py:57-64
    with sesion(cfg) as s:
        resumen = procesar_ciclo(s, args.ciclo, args.lote, args.municipio, cfg)
        ...
        if args.seco:
            s.rollback()
```

pero `procesar_ciclo` confirma por municipio (`ciclo.py:542`), tras el fallo
(`555`), al cerrar la corrida (`560`) y tras el scoring (`569`): cuando llega el
`rollback` todo está confirmado. `CLAUDE.md` §6 afirma «`--seco` corre y
revierte». *Escenario:* una prueba «en seco» inserta una corrida de agentes y
una de scoring reales, con trazas, y esa corrida entra en `ciclos_publicables`.
Medio: el diseño append-only impide que dañe lo anterior, pero contradice la
documentación operativa y suma corridas indistinguibles (H-006).

**H-039 · Medio · Riesgo · Confianza Alta · Área 7 · CA-M8.2, D9**
*Nada impide dos ejecuciones simultáneas ni registra que una está en curso.* No
hay bloqueo de archivo, fila de estado ni comprobación de corridas abiertas
(`grep` de `lock|en_curso|abierta|fecha_fin`: ninguna). Las corridas 9 y 10 se
solaparon el 2026-09-21 (16:00:41 y 16:02:54 UTC) y sus trazas son
indistinguibles (H-006). Sobre SQLite, dos escritores contienden por el bloqueo
único y el error se absorbe como fallo de municipio (`ciclo.py:543-555`); sobre
Neon no hay contención pero sí dos corridas «completas» del mismo ciclo con
minutos de diferencia. Riesgo adicional en la primera ejecución de una versión
nueva de prompt: dos procesos pueden intentar `registrar_prompt` sin ver la fila
del otro (`linaje.py:54-58`, se confirma solo con el primer municipio) y el
segundo revienta en `uq_prompt_agente_version`.

**H-040 · Medio · Riesgo · Confianza Alta · Área 7 · CA-M6.7, CA-M9.4, H4 (reproducibilidad del informe)**
*El informe publicado no es regenerable byte a byte ni registra el código que
lo compuso.* (a) `componer` lee los insights sin orden:

```
src/territorial/informes/composicion.py:299-306
    insights_por_muni: dict[str, list[Insight]] = {}
    for ins in sesion_bd.scalars(
        select(Insight).where(
            Insight.id_corrida == id_corrida_agentes,
            Insight.estado_validacion == "validado",
        )
    ).all():
        insights_por_muni.setdefault(ins.divipola, []).append(ins)
```

Regenerado sobre SQLite, 5 de 10 municipios difieren solo en el orden de
`insights`; y ese orden **decide qué ve la gerencia**: `Panel.tsx:312` pinta
`m.insights.slice(0, 5)` en los municipios no pedidos (Buenaventura en Neon:
1097, 1098, 1113, 1114, 1095; en SQLite: 1095–1099). (b) `informe` no guarda el
commit ni la invocación; hubo **cuatro publicaciones en un día** con payloads de
esquema distinto y la única forma de saber qué código produjo cada una es cruzar
`fecha_publicacion` con `git log`. El informe 2 (14:32 UTC) es anterior al commit
que añadió la guarda `_corrio_la_cadena` (15:00 UTC). *Escenario:* en la semana 8
alguien quiere demostrar que el informe 5 sale del código: obtiene otro orden y
no puede probar qué versión de `componer` corrió. Medio: el contenido es
idéntico; lo no reproducible es el orden y la procedencia.

**H-041 · Bajo · Riesgo · Confianza Alta · Área 7 · D6, CA-M1.4 (análogo)**
*Reintentos y timeouts del LLM no están fijados ni documentados; rigen los del
SDK.* `OpenAI(api_key=…, base_url=…)` (`cliente.py:73-76`) sin `timeout` ni
`max_retries`; el SDK 3.14.1 aplica 2 reintentos y `read=600 s`. Con lotes de 50
señales y razonamiento en gpt-5, un cuelgue del proveedor puede retener un lote
hasta 30 minutos antes de fallar «en silencio» hacia H-037. Bajo: los valores
son razonables; el problema es que nadie los eligió ni los escribió.

### 7.3 Estado de los CA del área

| CA | Estado | Base |
|---|---|---|
| CA-M1.4 (análogo por lote/municipio) | **Parcial** | El ciclo no aborta (`ciclo.py:346-362, 543-555`) pero el fallo no queda registrado (H-037); la versión por fuente sigue sin validar (Addendum 01 §5) |
| CA-M6.7 (publicación) | **Parcial** | Publica y archiva en una transacción con índice único; **sin punto de entrada, sin rastro del código** (H-040); sin correo (autorizada) |
| CA-M8.2 | **Parcial** | H-006 (consolidado) |
| CA-M8.3 | **Parcial** | H-006 y H-035 (consolidados); agregable por ciclo y agente, no por corrida ni con razonamiento |
| CA-M8.4 | **No cumple** | Sin checkpointer ni reanudación; relanzar duplica (H-037) |
| D9 (ejecución manual) | **Cumple** | Sin cron; punto de entrada único e intercambiable |
| Secretos | **Cumple** | Solo en `.env`; ninguno en código ni historial |

### 7.4 No verificable en esta área

- Comportamiento real ante caída del proveedor y ante `database is locked`:
  exigiría ejecutar un ciclo; se infiere del código. Artefacto: prueba con un
  cliente simulado que falle en el lote 3 de 6.
- Qué código exacto publicó los informes 2–4: no está registrado; solo la
  cronología. Artefacto: guardar `commit` e invocación en `informe`.

### 7.5 Anexo (sesión 2, encargo del dueño): ¿la corrida 10 está completa por datos?

El estado `completa` no vale como prueba (H-037). Se verificó con `SELECT`, sin
usar `tipo_corrida`:

| Comprobación | Resultado |
|---|---|
| Municipios en `municipios_objetivo` y en `municipios_en_cohorte` | 18 y 18, idénticos |
| Municipios con salida persistida | **18 de 18** con insights del Clasificador (mínimo Cartagena: 1 insight, 2 señales enviadas) |
| Señales enviadas, recomputadas con el prefiltro sobre SECOP del ciclo 3 + todo RSS | **2.487**, igual a `senales_procesadas` |
| Contabilidad por municipio (en insight ∪ en descarte = enviadas) | **18 de 18 cuadran**; ninguna señal enviada sin destino → ningún lote fallido ni vacío (un lote fallido dejaría sus señales fuera de ambos lados, `ciclo.py:346-351`) |
| Lotes esperados (`ceil(secop/50) + ceil(rss/50)` por municipio) | **69** para la corrida 10; la corrida 9 (Puerto Colombia: 40 SECOP + 10 RSS) suma 2 → **71 = trazas del Clasificador del ciclo 3** |
| Llamadas al Correlacionador esperadas (≥ 2 insights validados y ≥ 2 categorías conocidas) | **17** municipios (Cartagena no, con 1 insight); más 1 de la corrida 9 → **18 = trazas del Correlacionador del ciclo 3** |
| Tokens | `traza_agente` del ciclo 3 menos corrida 9 = **541.852 / 249.767 = `corrida_agentes.tokens`** de la 10, exacto |
| Trazas del Clasificador con salida mínima | 3 trazas con 36–58 tokens de salida (ids 188, 191, 224): lotes que devolvieron casi solo descartes; sus señales están contabilizadas, así que no son fallos |

**Veredicto: la corrida 10 está completa por datos** —18/18 municipios,
2.487/2.487 señales contabilizadas, 69 lotes y 17 llamadas a M4 coincidentes con
las trazas, tokens exactos—. **No se añade ningún hallazgo ni etiqueta.** H-037
sigue vigente como riesgo estructural: esta verificación tuvo que hacerse a mano
porque el sistema no la registra.

*Fin del área 7.*

---

## Área 1 — Ingesta (M1 sobre el snapshot)

**Cerrada en la sesión 2.** Archivos leídos completos para esta área, además de
los del Preflight: `scripts/cargar_snapshot.py`, `scripts/cargar_divipola.py`,
`scripts/cargar_contexto.py` (`ingesta/snapshot.py`, `nomenclator.py` y
`contexto.py` estaban leídos). Ejecutado, sin escrituras: recuento del snapshot
archivado (`data/blob/raw/territorial_data_cruda_v3.json`, hash verificado en el
área 4) contra `senal_cruda`, y `git check-ignore` sobre `data/`.

### 1.1 Sondas

| Sonda | Respuesta | Evidencia |
|---|---|---|
| ¿Aislamiento de fallos por fuente? | **No aplica / No verificable** | No hay fuentes vivas (Addendum 01 §1, D9). La ingesta lee un JSON y tolera que a un municipio le falte una fuente (`(muni.get("secop") or {})`, `snapshot.py:83, 104, 124`), pero **es una sola transacción**: `cargar` abre `with sesion(cfg)` (`159`) y cualquier excepción —un `DivipolaInvalido` en `desde_bloque`, `186`— revierte todo. Es todo-o-nada, no aislamiento. CA-M1.4 queda «sin validar», como declara el Addendum 01 §5 |
| ¿URL y fecha de publicación original persistidas? | **Sí** | SECOP: `url` y `fecha` del registro (`snapshot.py:93-96`); RSS: `link` y `fecha` (`115-117`); ambas con 0 NULL en 19.640 y 336 filas (§0.2, área 4). El registro completo viaja en `datos` (D3). Bing sin URL ni fecha por diseño (D1). `capturado_en` es la hora de **carga** (`modelos.py:233`), no la fecha de captura del snapshot (`raw.generado`), que no se persiste por fila |
| ¿La deduplicación se apoya en contenido estable y la impone una restricción? | **Restricción sí; contenido no** | `uq_senal_ciclo_hash` real en el esquema (área 4) más el conjunto `vistos` en memoria (`snapshot.py:183-209`). El hash es de **identidad** —`sha256(fuente\|divipola\|id_externo)` para SECOP, del `link` para RSS, del ciclo para Bing (`99, 119, 136`)—, no del contenido (H-001). Alcance por ciclo (desviación 11.2). **Sobre el snapshot real no se ejercita**: 0 duplicados por `(municipio, id)` en SECOP y 0 por `(municipio, link)` en RSS |
| ¿La ingesta es sin pérdida respecto del snapshot? | **Sí, exacta** | Snapshot: 19.640 registros SECOP (0 fuera de la ventana extendida, 0 sin fecha), 336 noticias (0 fuera), 18 textos Bing → base: 19.640 / 336 / 54 (= 18 × 3 ciclos). La ventana declarada por el archivo (hasta 2026-08-09) se extendió a 2026-09-09 (D2) y absorbe los 1.007 registros posteriores |
| ¿Qué registra la traza por fuente (CA-M1.5)? | **Solo en pantalla** | `Resumen` (`snapshot.py:29-51`) imprime señales por ciclo y por fuente, fuera de ventana y duplicadas; `cargar_snapshot.py:37-38` lo muestra y no lo guarda. Persistido: `dataset_version` (hash, URI, `n_registros = 18`, que son **municipios**, no registros) y `ciclo.id_dataset`. `ciclo.n_senales` vale 0 (H-003) |
| Nomenclátor y contexto (tablas maestras) | **Idempotentes y desacoplados** | `nomenclator.cargar` compara en Python y reporta sobrantes sin borrar (`137-166`); `cargar_contexto.cargar` igual (`70-89`); ambos scripts llaman a `aplicar_migraciones()` antes de escribir (regla 2 de D8). Sin FK a `municipio` a propósito (`modelos.py:101-107`). **Sus insumos no están en el repositorio**: `data/divipola_terridata_1102.csv`, `data/TerriData.txt.zip` (3,31 GB) y `data/contexto_municipal.csv` están ignorados por git (`git check-ignore`) |
| Texto que se persiste vs. texto que ve el modelo | Distintos para RSS | `senal_cruda.contenido` guarda solo el **título** (`snapshot.py:116`); el Clasificador y el validador reciben «título. resumen» vía `texto_de` (`ciclo.py:199-215`), coherentes entre sí. El nivel 3 de evidencia del Design System («contenido capturado, tal como se recibió») mostraría el título y no el resumen |

### 1.2 Hallazgos

**H-042 · Bajo · Brecha · Confianza Alta · Área 1 · CA-M1.5, PRD §4.2 (`dataset_version`)**
*La traza de ingesta por fuente no se persiste y `dataset_version.n_registros`
no cuenta registros.* El resumen con «cuántos registros aportó cada fuente por
ciclo» —lo que CA-M1.5 exige y lo que el Addendum 01 §5 reinterpreta— se imprime
y se pierde:

```
scripts/cargar_snapshot.py:36-38
    inicio = time.perf_counter()
    resumen = cargar(cfg)
    print(resumen)
```

`dataset_version.n_registros = len(datos.get("municipios", []))` (`snapshot.py:166`)
guarda **18** bajo un nombre que sugiere señales. Los conteos se pueden rehacer
desde `senal_cruda`, por eso es Bajo; pero «fuera de ventana» y «duplicadas» no
se pueden rehacer sin el snapshot, y hoy valen 0 y 0 solo porque esta auditoría
lo recontó.

**H-043 · Bajo · Riesgo · Confianza Alta · Área 1 · D7 (linaje de dataset), reproducibilidad**
*`entidad_divipola` y `contexto_municipal` no son regenerables desde el
repositorio.* Sus fuentes viven en `data/` (ignorado): el CSV del nomenclátor, el
zip de TerriData y el CSV exportado. A diferencia del snapshot, **ninguno está
archivado en el blob ni anclado por hash** en `dataset_version`: la tabla
`contexto_municipal` (1.102 filas) alimenta las bandas del Correlacionador v2 y
las tres tarjetas del informe, y nada en la base dice de qué archivo salió. Bajo
porque el contenido es público y las cargas son idempotentes; sube si alguien
rehace el contexto desde otro corte de TerriData.

### 1.3 Estado de los CA del área

| CA | Estado | Base |
|---|---|---|
| CA-M1.1 | **Desviación autorizada** (Addendum 01 §5) · Cumple como reinterpretado | Carga las 4 fuentes del snapshot y particiona por ventana sin intervención manual; 19.640 / 336 / 54 exactos |
| CA-M1.2 | **Cumple** | URL y fecha original en 100 % de SECOP y RSS; Bing excluido por D1 |
| CA-M1.3 | **Desviación autorizada** (11.2) | Restricción única real por (ciclo, hash de identidad); no ejercitada por el snapshot; ver H-001 sobre contenido |
| CA-M1.4 | **No verificable** | Sin fuentes vivas; la ingesta es atómica, no aislada por fuente |
| CA-M1.5 | **Parcial** | Conteos por fuente solo en stdout (H-042); linaje de dataset por hash sí (D7) |

### 1.4 No verificable en esta área

- Comportamiento con una fuente caída o un registro malformado en producción:
  exige ingesta viva (Fase 0). Artefacto: conector real con una fuente simulada
  que falle.

*Fin del área 1.*

---

## Área 9 — Reglas de `CLAUDE.md` §2

**Cerrada en la sesión 2.** Sin archivos nuevos: cada regla se juzga con
evidencia ya citada en las áreas 2, 3, 4, 5 y 7. `CLAUDE.md` §2 es normativo
para el código (jerarquía de línea base, nivel 4); donde la regla fue precisada
el 2026-09-21 (§2.1, regla 1) se evalúa la versión precisada.

### 9.1 Un estado por regla

| Regla | Estado | Evidencia y matiz |
|---|---|---|
| **§2.1 regla 1** — Todo acceso a datos pasa por SQLAlchemy; la precisión del 2026-09-21 la restringe a **escrituras y esquema**, y admite que la app web lea Neon directamente si (a) sus escrituras se verifican contra `modelos.py` y (b) no genera migraciones | **Cumple, con dos notas** | Python: ORM/Core en todo `src/` y `scripts/`; las migraciones `41d077a78426` y `cb034d1c967b` usan `sa.text()`, que es SQLAlchemy Core, no SQL de motor. Web: 8 `SELECT` y 3 escrituras en SQL crudo vía `@neondatabase/serverless` (área 5, §5.1); la condición (a) se cumple por **forma** —`contrato.generado.ts` desde `modelos.py`, `tests/test_contrato.py` falla si divergen (ejecutado: «al día»)— pero **no por alcance**: el contrato garantiza columnas y tipos, no que el insight calificado pertenezca a un informe publicado ni que el ciclo esté abierto (H-013). La condición (b) se cumple: `web/` no tiene ORM ni migraciones. **Nota 2:** `Informe._congelar_corrida` reconoce que un `UPDATE` crudo lo saltaría (`modelos.py:673-676`); la web no toca `informe` |
| **§2.1 regla 2** — El esquema se gobierna con Alembic desde la primera migración | **Cumple** | 11 migraciones lineales, `alembic check` sin diferencias en SQLite y ambas bases en `head` (§0.2 #7-#10); `create_all` solo en fixtures de pruebas (`tests/*`), que la propia regla admite (`test_persistencia.py:3-5`); `aplicar_migraciones()` en la ingesta y en los tres scripts de carga; `exigir_directa` en los dos caminos (`sesion.py:133`, `env.py:48`); FKs nombradas en modo batch. Sin migraciones desde `web/` |
| **§2.1 regla 3** — Columnas JSON con el tipo `JSON` portátil; nunca operadores JSONB | **Cumple** | Todas las columnas semiestructuradas son `sa.JSON` (`modelos.py`, migraciones); `grep` de `->>`, `@>`, `jsonb`, `json_extract` en `src/`, `scripts/`, `web/`: ninguno fuera del comentario de `modelos.py:4` (§0.2 #26). `tablero.ts` compone en TypeScript el `contenido` entero en vez de consultar dentro del JSON (`tablero.ts:107-113`) |
| **§2.2** — Ninguna cifra de un informe proviene del LLM (CA-M6.3) | **Parcial** — decisión del dueño (P-3) | Cifras estructuradas 100 % por código (`informes/composicion.py`, sin llamada a modelo); prosa del modelo con 15 cifras transcritas de la fuente y **sin compuerta en `ciclo.py`** (H-009, Alto, quick win, 🔒). La regla dice «no admite excepción ni atajo» y hoy la sostiene la disciplina del prompt, no el código |
| **§2.3 corolario 1** — El validador es código, nunca LLM; su tasa de rechazo es la tasa de alucinación medida | **Cumple (código) · Parcial (métrica)** | `validador.py` sin importación ni llamada a modelo (área 3); veredicto reproducido 326/326. La **tasa** no se persiste ni reporta (H-010) y el documento de resultados publica 0,0 % cuando la base da 1,2 % (H-028); bajo snapshot mide fidelidad de cita, no alucinación (H-029) |
| **§2.3 corolario 2** — Bing nunca es evidencia (D1); el validador lo rechaza por R2 | **Cumple, con la implicación de D1 pendiente** | R2 y R7 rechazan Bing como origen y como señal (`validador.py:92-95, 121-122`); ningún insight de las 1.213 filas tiene evidencia Bing (área 4: 933/933 evidencias del informe son SECOP o RSS). Bing sí llega al prompt del Correlacionador como contexto, según D1 permite, pero el marcado `contexto_no_verificado` que D1 exige nunca se escribe (H-021) |
| **§2.3 corolario 3** — Los prompts van versionados y se archivan en el almacén (D7); el linaje se registra, no se edita en sitio | **Cumple en `procesar_ciclo` · Parcial en scripts** | `registrar_prompt` ancla por hash y falla ante edición sin cambio de versión (`linaje.py:39-78`; probado en `test_persistencia.py:487-498`); hashes de tabla = blob = `src/` para v4, v1 y v2 (área 4). Las corridas de `comparar_correlacionador.py --persistir` no registran linaje (H-022) y v2 «vigente» no tiene fila (H-023) |
| **§2.4** — Toda compuerta sobre la salida de un agente necesita su piso de ruido medido; criterio sobre el agregado, umbral = rango observado, sin piso se niega a juzgar; lo mismo para una detección | **Parcial** | El diseño cumple las tres reglas (`comparar_correlacionador.py:92-119, 355-381`) y el invariante «no suspende a su línea base» está probado (`tests/test_compuertas.py:36-44`). Pero el **piso codificado** mezcla dos pasadas persistidas (39/23, 42/24) con una no persistida (42/20), y `test_compuertas.py` prueba las constantes, no una medición (H-036). La detección de cifras «con la misma vara» existe y está probada (`reglas/cifras.py`, `test_cifras.py`), pero solo se usa en calibración (H-009) |

### 9.2 Hallazgos

Ningún hallazgo nuevo: los desvíos de las reglas §2.2, §2.3 y §2.4 ya están
registrados en H-009, H-010, H-021, H-022, H-023, H-028, H-029 y H-036, y el
matiz de la regla 1 en H-013. Se anota para la matriz que **las tres reglas de
§2.1 se cumplen**, que **§2.2 es Parcial por decisión del dueño** y que **§2.3 y
§2.4 se cumplen en el camino principal y fallan en los caminos de calibración**
(scripts), que es donde el proyecto midió lo que después declaró vigente.

*Fin del área 9.*

---

## Área 6 — Conformidad de interfaz con `docs/design-system.md`

**Cerrada en la sesión 2.** Archivos leídos completos para esta área:
`docs/design-system.md` entero (§0–§7 y anexo; §2–§4 ya leídos en el Preflight);
los componentes de `web/app` y `web/app/globals.css` estaban leídos. Ejecutado:
`find` de archivos de estado de Next, `grep` de `@media`, sombras y valores
literales. **El servidor de desarrollo ya no estaba levantado** en esta sesión
(la tarea de fondo terminó) y no se relanzó —arrancar servicios exige preguntar—,
así que las comprobaciones de render son las del área 5 (GET) más lectura de
código. El Design System es normativo en color y tipografía; su §4 solo esboza
las vistas secundarias (desvíos allí: como mucho Bajo, según la jerarquía).

### 6.1 Tokens y tipografía (§1)

| Bloque del DS | Implementación (`web/app/globals.css`) | Estado |
|---|---|---|
| §1.1 navy-700 `#0F4761`, navy-100 `#DEEAF0` (confirmados) | `--color-navy-700: #0f4761`, `--color-navy-100: #deeaf0` (14-15) | **Idéntico** |
| §1.2 escala derivada 900/500/300/050 | `#0a3145`, `#2c6b87`, `#7fa9bc`, `#f1f7fa` (18-21) | **Idéntico** |
| §1.3 neutrales `[provisional]` (6) | ink `#1a1d1f`, muted `#5b6670`, faint `#8a9199`, border `#dde2e5`, surface-alt `#f5f6f7`, surface `#ffffff` (24-29) | **Idéntico**; el CSS repite la marca `[provisional]` en comentario (4-6) |
| §1.4 semántica de estado `[provisional]` (4 pares) | critical `#a4262c/#fbeaea`, warning `#7a5400/#fdf4dc`, positive `#0e5c38/#e4f0ea`, neutral `#5b6670/#eef0f1` (32-39) | **Idéntico** en valores; el DS los llama `color-state-*` y el CSS `--color-*` (solo nomenclatura) |
| §1.5 Aptos, pila, sin serif ni monoespaciada, `tabular-nums` | `--fuente: Aptos, "Segoe UI", system-ui, -apple-system, sans-serif` (56); `.t-data` con `font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1` (117-123); ninguna otra familia | **Idéntico** |
| §1.5 escala: display 28/600 · h1 22 · h2 17 · h3 14 · body 15/400 · data 15/600 · data-lg 32 · meta 12/400 · label 11/600 mayúsculas +0.06em; interlínea 1.5 cuerpo, 1.25 títulos y datos | `.t-display` 28/600/1.25, `.t-h1` 22, `.t-h2` 17, `.t-h3` 14, `.t-body` 15/400, `.t-meta` 12 ink-muted, `.t-label` 11/600 uppercase 0.06em, `.t-data` 15, `.t-data-lg` 32; `body` line-height 1.5 (78-129) | **Idéntico** |
| §1.6 espaciado base 4 (1/2/3/4/6/8/12), radio 4 tarjetas y 2 controles, sin sombras, 72 caracteres en prosa | `--space-1..12` = 4/8/12/16/24/32/48 (42-48); `--radio-tarjeta: 4px`, `--radio-control: 2px` (50-51); `grep box-shadow`: 0; `.prosa { max-width: 72ch }` (165-167) | **Idéntico** |
| Regla dura §1.4: el color nunca porta información solo | `.etiqueta*` siempre envuelve texto (139-157); estados del tablero con `ETIQUETA[estado]` junto a `CLASE[estado]` (`priorizados/page.tsx:16-29, 238-240`) | **Cumple** |

Valores literales fuera de tokens en componentes (`grep`): `#fff` ×10 para
texto sobre navy (el DS no define un token de «texto sobre primario»; existe
`color-surface #FFFFFF`), `fontSize: 14` en la línea de fuentes (igual al tamaño
de `type-h3`, decisión M6-orden), y anchos de maquetación (28, 44, 236, 640,
1200 px) que el DS no regula. Ninguno contradice un token.

### 6.2 Estructura de la vista de ciclo (§2) y del detalle (§3)

| Elemento del DS | Implementación | Estado |
|---|---|---|
| §2.1 encabezado: título, rango de fechas, número de municipios; marca en `color-state-warning` con `type-label`, en el encabezado y no en el pie | `ciclo/[id]/page.tsx:218-238`: `t-h1`, fechas, «N municipios mostrados», `etiqueta etiqueta-aviso t-label` en el encabezado | **Cumple**; el texto es «MVP» (desviación `M6-aviso`; H-019 para `/priorizados`) |
| §2.2 lista: posición sobre navy-700 con `type-data`; nombre `type-h3` + depto + DIVIPOLA `type-meta`; score 0–1 con 4 decimales `type-data`; línea de fuentes; justificación `type-body`; **sugerencia de acción** sobre navy-100; filas alternas navy-100; orden fijo | Posición (`91-105`), nombre y meta (`108-111`), score `toFixed(4)` (`123`), línea de fuentes (`112-114`), justificación condicional (`115-119`), zebra navy-100 (`82-86`), orden del payload | **Parcial**: la zona **«sugerencia de acción» no existe** en la vista y el hueco no se pinta; el aviso `faltaProsa` (`240-246`) nombra solo la justificación (H-046) |
| §2.2 nota: score ordinal 0–1, nunca porcentaje; versión del modelo junto al informe | `Panel.tsx:241-245` «Score del ciclo (0 – 1)» y `modelo {version_scoring}` | **Cumple** |
| §2.3 línea de fuentes: junto al nombre y al score, «mismo peso visual», nombres de fuente, ausencias con «ni», F6 fuera mientras falte en todos | `LineaDeFuentes` 14 px ink con la ausencia en negrita (`40-55`); frase de `composicion.resumir_fuentes` | **Cumple §2.3**; contradice la tabla de §2.2, que le asigna `type-meta` ink-muted (H-047) |
| §2.4 calificación: 5 controles terminales, clic 1 = registro, extremos etiquetados, valor elegido en navy-700 sólido, confirmación positiva, sin promedio ni conteo ajeno, correo una vez, mensaje «no está en la lista» con a quién escribir, forma visible de cambiar el correo, leer sin correo | `Panel.tsx:100-204` (5 `submit`, `minWidth/minHeight 44`, «nada»/«acción inmediata», navy-700 al elegido, `etiqueta-positiva`); `Identificarse.tsx:72-81`; `layout.tsx:43-63` «cambiar correo»; lectura abierta | **Cumple**. El mensaje remite a «quien te compartió el enlace», no a un contacto nombrado (aceptable con el DS) |
| §2.4 alcance pedido visible (M9-carga) | Pastilla «se pide» + contador solo en los 3 primeros; «Ver detalle» en los demás (`page.tsx:130-169`) | **Cumple** |
| §3 despliegue lateral, no ruta; insights al desplegar | `?m=` en la URL, `aside` sticky (`268-294`); el servidor serializa solo el municipio abierto | **Cumple** |
| §3.1 anatomía del dato: valor `type-data` tabular → etiqueta `type-body` → procedencia `type-meta`, contiguos, separación `space-1`, nunca en pie ni tras interacción | `Panel.tsx:44-62`: `t-data-lg`, `t-body`, `t-meta` con `fuente anio`, `marginTop: var(--space-1)` | **Cumple** |
| §3.2 contexto estructural con año obligatorio | `Contexto` (`33-66`); tres tarjetas con `fuente` y `anio` del payload | **Cumple** |
| §3.3 evidencia en tres niveles: procedencia siempre; cita en recuadro navy-050 con borde 2 px navy-300 «que se despliega»; nivel 3 señal cruda y cadena | Nivel 1 y 2 en `Evidencia` (`68-98`): recuadro `navy-050`, `borderLeft: 2px solid navy-300`, cita entre comillas, fuente · fecha · enlace en pestaña nueva; **solo `evidencia[0]`** y siempre desplegada; **nivel 3 ausente** | **Parcial** — H-016 y H-017 (área 5) |
| §3.4 score explicable: barras comparativas con valor al lado, orden por magnitud, sin datos mostrados, versión, nombres de fuente | `Panel.tsx:251-288` sobre `aportes_por_fuente` (ordenado en `composicion.agrupar_por_fuente`), «(aún no hay)» para sin datos | **Cumple** |
| §4.1 tablero: densidad alta, estados con texto + color, nota obligatoria, historial | `priorizados/page.tsx` y `CambiarEstado.tsx` | **Cumple** el esbozo |
| §4.2 Histórico · §4.3 Métricas | No existen (H-014) | — (ya registrado; en §4 el DS solo esboza) |

### 6.3 Estados (§5) y móvil (§6)

| Elemento del DS | Implementación | Estado |
|---|---|---|
| §5.1 cargando: esqueleto con la forma del resultado, sin cifras provisionales | Sin `loading.tsx` en `web/app` (`find`: ninguno); las páginas son RSC con `force-dynamic` y bloquean hasta tener datos, así que no hay cifras provisionales, pero tampoco esqueleto | **Parcial** (Bajo) |
| §5.2 error: título, explicación, qué no se perdió, una acción; **si falla el guardado de una calificación, decirlo en el sitio y no borrar la selección** | Sin `error.tsx` ni `global-error.tsx`; `registrarCalificacion` no devuelve estado (`acciones.ts:73-80`, `Promise<void>`) y `Calificar` no tiene rama de error (`Panel.tsx:100-204`); una excepción del driver sube al límite de error por defecto de Next | **No cumple** (H-045) |
| §5.3 vacío: «El primer ciclo se publica el [fecha]»; filtros sin resultado con acción | Raíz: «Aún no hay ningún informe publicado.» sin fecha (`page.tsx:15`); filtros: mensaje + «Quitar los filtros» (`priorizados/page.tsx:176-184`); `/ciclo/N` sin informe → 404 por defecto de Next, sin `not-found.tsx` | **Parcial** (Bajo, en H-046) |
| §6 móvil: fila de calificación no se apila, 44 px; línea de fuentes envuelve; **lista pasa de fila a tarjeta**; **detalle a pantalla completa con retorno** | `@media`: **0** en todo `web/app`. Rejilla fija de dos columnas `minmax(0, 1fr) minmax(0, 1fr)` (`page.tsx:251`) y `aside` sticky en cualquier ancho; controles 44 px en `flex` sin `wrap` (cumple); línea de fuentes `span` inline (envuelve, cumple) | **Parcial** — H-044 |

### 6.4 Hallazgos

**H-044 · Medio · Brecha · Confianza Alta · Área 6 · CA-M9.18, Design System §6**
*La interfaz no tiene ninguna adaptación a pantalla estrecha.* `grep '@media'
web/app` devuelve 0. La vista de ciclo fija dos columnas:

```
web/app/ciclo/[id]/page.tsx:248-254
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)",
          gap: "var(--space-6)",
          alignItems: "start",
        }}
      >
```

En un teléfono, lista y detalle comparten el ancho a la mitad cada una y el
`aside` sigue `sticky`; el DS §6 pide que la lista pase a tarjeta y el detalle a
pantalla completa con retorno. Lo que sí se cumple: la fila de calificación no
se apila (44 px, `flex`) y la línea de fuentes envuelve. *Escenario:* una gerencia
abre el enlace en el móvil —el caso que CA-M9.18 protege— y califica sobre
columnas de media pantalla; H2 puede perder respuestas por incomodidad que el
sistema no distinguirá de desinterés. Confianza Alta en el código; no se pudo
renderizar a 375 px porque el servidor no estaba levantado.

**H-045 · Medio · Brecha · Confianza Alta · Área 6 · Design System §5.2, CA-M7.6**
*Un fallo al guardar una calificación no se muestra en el sitio ni conserva la
selección.* `registrarCalificacion` y `registrarComentario` devuelven
`Promise<void>` (`acciones.ts:73, 124`); `Calificar` no usa `useActionState` ni
tiene rama de error (`Panel.tsx:100-204`); no hay `error.tsx` en `web/app`. Si
`calificar` lanza —`CalificacionInvalida`, fallo de red con Neon, `database
is locked`—, Next muestra su página de error genérica y la fila desaparece con
ella. El DS §5.2 lo señala como «caso crítico». *Escenario:* durante la ventana
una gerencia pulsa 4, la petición falla, ve un error genérico, y no sabe si su
calificación quedó; con siete gerencias cada respuesta pesa el 14 % de H2.
`CambiarEstado` sí tiene manejo de resultado (`useActionState`, `ResultadoSeguimiento`),
así que el patrón existe en el propio código.

**H-046 · Bajo · Brecha · Confianza Alta · Área 6 · Design System §2.2, §5.1, §5.3**
*Tres huecos menores frente al DS.* (a) La zona «sugerencia de acción» de §2.2
no se renderiza: `grep sugerencias web/app` no devuelve nada, y el aviso de prosa
pendiente (`page.tsx:240-246`) solo nombra la justificación, así que el hueco de
las sugerencias **no se pinta explícitamente** como el DS exige. (b) El vacío de
la raíz no lleva fecha del primer ciclo (`page.tsx:15`). (c) Sin `loading.tsx`
ni `not-found.tsx`: el esqueleto de §5.1 no existe y `/ciclo/1` cae en el 404 por
defecto de Next. Bajo: nada de esto afecta a una medición.

**H-047 · Bajo · Brecha documental · Confianza Alta · Área 6 · Design System §2.2 vs §2.3**
*El Design System se contradice sobre la línea de fuentes.* La tabla de §2.2 le
asigna `type-meta, ink-muted` (12 px gris); §2.3 exige «junto al nombre y al
score, con el mismo peso visual» y `pendientes.md` M6-orden dice que «pintada en
gris pequeño se leía como una nota técnica». La implementación sigue §2.3 (14 px
en tinta plena, ausencia en negrita, `page.tsx:40-55`). Por la regla de
conflicto, el documento posterior y más específico prevalece (§2.3 y M6-orden),
pero la tabla de §2.2 debería corregirse para que el DS no describa dos cosas.

### 6.5 Estado de los CA del área

| CA / regla | Estado | Base |
|---|---|---|
| CA-M9.18 | **Parcial** | Lectura y calificación funcionan en cualquier ancho sin romperse (controles 44 px, sin apilar), pero sin la adaptación que el DS §6 define (H-044) |
| CA-M6.5 (presentación) | **Desviación autorizada** (`M6-aviso`) | Encabezado, `type-label`, `color-state-warning`: conforme al DS §2.1 salvo el texto |
| CA-M9.6 (presentación) | **Cumple** | §3.4 íntegro |
| CA-M6.4 (presentación) | **Cumple** | §3.1 y §3.2 íntegros en las tarjetas de contexto y en la evidencia mostrada |
| DS §1 tokens y tipografía | **Cumple** | 100 % de valores idénticos |
| DS §5 estados | **Parcial** | H-045, H-046 |

*Fin del área 6.*

---

## Área 10 — Transversal

**Cerrada en la sesión 2.** Archivos leídos completos para esta área: los 13
archivos de `tests/` (los 9 que faltaban se leyeron aquí: `test_conexion.py`,
`test_contrato.py`, `test_seleccion.py`, `test_nomenclator.py`, `test_contexto.py`,
`test_correlacionador.py`, `test_corridas.py`, `test_informes.py`,
`test_persistencia.py`). Ejecutado: `ruff check --output-format concise`,
`pytest --collect-only` por archivo, `grep` de módulos de `src/` referenciados
por tests, versión declarada vs instalada de las 14 dependencias, `npm audit
--omit=dev`, `git check-ignore` sobre `data/`, `grep` de PII en logs y de
símbolos sin uso. Con esta área **todos los archivos de código del repositorio
están leídos completos** salvo `alembic/script.py.mako`, `web/tsconfig.json`,
`web/package-lock.json` y `.gitignore` (solo consultado con `git check-ignore`).

### 10.1 Secretos

| Sonda | Resultado |
|---|---|
| Secretos en código | `grep` de patrones (`sk-`, `npg_`, `AKIA`, `password =`) en `src/ scripts/ web/ alembic/`: **0** (área 7) |
| Secretos en historial | `npg_` en 0 de 66 revisiones; `.env` nunca rastreado (§0.2 #20) |
| Configuración | 21 variables en `.env`, 20 en `.env.example`; ninguna en `web/` (§0.2 #21) |
| `data/` (usuarios, nomenclátor, TerriData, base, blob) | **Ignorado por git** en los seis casos; 0 archivos rastreados bajo `data/` |

**R-A1 · Riesgo aceptado por el dueño (no es hallazgo a remediar) · credencial
de Neon.** La contraseña de la cadena `DATABASE_URL` fue expuesta en un chat y
**no se rotará**. Hechos verificados: no está en el repositorio ni en su
historial; el rol tiene **escritura** (`transaction_read_only = off`); la
exposición es externa. **Evidencia del experimento que depende de su
integridad:** todo lo que solo existe en Neon (§0.7) —el informe 5 publicado, que
fija la corrida canónica del ciclo 3 (A9); la tabla `usuario`, denominador de H2;
y todas las futuras `calificacion` y `seguimiento`, evidencia primaria de H1 y
H2 y de cinco de las diez métricas del PRD §6—. Los datos de pipeline tienen
copia íntegra en SQLite local; las calificaciones no tendrán copia salvo que se
establezca. Con H-012 (identidad forjable) y H-013 (acciones sin alcance), la
credencial es el tercer camino de escritura sin control sobre la evidencia de H1
y H2.

### 10.2 Datos personales

| Sonda | Resultado |
|---|---|
| Dónde vive la PII de SECOP (D3: `proveedor`, `rep_legal`) | En `senal_cruda.datos` de las 19.640 filas SECOP, **en SQLite y en Neon** (copia íntegra, §0.7); el snapshot lleva su propia `nota_pii` |
| ¿Llega al informe publicado? | Indirectamente: `informe.contenido` copia `evidencia[].cita_textual`, tomada del campo `objeto`, no de `proveedor`; no se detectó nombre de persona en las 933 citas de forma sistemática (no se buscó) |
| ¿Se loguea? | `src/`: ningún `log.*` ni `print` con `contenido`, `datos`, `proveedor` o `rep_legal` (`grep`); los scripts de calibración imprimen citas y resúmenes por stdout (`comparar_prompts.py:205-211`, `probar_clasificador.py:105-122`), no `datos` |

**H-048 · Medio · Riesgo · Confianza Alta · Área 10 · Addendum 01 D3, snapshot `nota_pii`**
*La PII de SECOP se replicó a una base gestionada en la nube sin política de
tratamiento ni retención.* D3 conserva `proveedor` y `rep_legal` «como decisión
consciente» y cita la Ley 1581 de 2012; desde el 2026-09-21 esas 19.640 filas
están también en Neon (host `aws.neon.tech`), accesibles con la credencial de
R-A1, y ningún documento del repositorio define quién es responsable del
tratamiento, cuánto tiempo se conservan ni si la transferencia a un proveedor
externo está cubierta. *Escenario:* la Fase 0 hereda el dato y la exposición sin
que nadie haya decidido nada sobre ellos. No es un juicio legal —la auditoría no
lo hace—; es la constatación de que D3 decidió conservar y no decidió tratar.

### 10.3 Dependencias

| Sonda | Resultado |
|---|---|
| Fijación (Python) | `pyproject.toml` con **rangos abiertos y sin lockfile** (§0.4). Saltos de versión mayor ya ocurridos entre lo declarado y lo instalado: `openai >=1.50` → **3.14.1**; `langgraph >=0.2` → **1.2.11**; `langfuse >=2.55` → **4.15.4**; `langgraph-checkpoint-sqlite >=2.0` → **3.1.1**; `ruff >=0.8` → 0.16.8 |
| `psycopg` | Declarado solo en el extra `azure` (`pyproject.toml:35`) aunque D8 hace de PostgreSQL la base de nube y `sesion.normalizar_url` lo presupone (`sesion.py:31-34`); un `pip install .` sin extras no puede conectar a Neon |
| Fijación (web) | `package-lock.json` presente; `next ^15.1.3` resuelto a 15.5.25 |
| Vulnerabilidades (web) | `npm audit --omit=dev`: **1 high, 1 moderate**, ambas por `postcss <= 8.5.22` transitiva de `next`; la corrección propuesta es `next@16.3.6` (cambio mayor) |
| Vulnerabilidades (Python) | No se ejecutó auditoría (no hay herramienta instalada; no se instala nada) — **No verificable** |

**H-049 · Medio · Riesgo · Confianza Alta · Área 10 · Addendum 02 D5/D8, reproducibilidad del entorno**
*El entorno Python no es reproducible y arrastra saltos de versión mayor en los
SDK que llaman al modelo.* Sin lockfile, un `pip install -e .` hoy y otro dentro
de un mes pueden instalar versiones mayores distintas de `openai`, `langfuse` y
`langgraph`; ya ha pasado (1.50 → 3.14 en `openai`, cuyos valores por defecto de
reintentos y timeout rigen la cadena, H-041). `psycopg` queda fuera de las
dependencias base aunque Neon lo exige. En `web/`, `next` 15.5 arrastra un
`postcss` con dos avisos que solo cierra un salto a `next` 16. *Escenario:* rehacer
las mediciones de la semana 8 en una máquina nueva instala otro SDK y otra
librería de trazas; si el comportamiento cambia, no habrá forma de separar
«cambió el modelo» de «cambió el cliente». Medio: no bloquea, degrada
reproducibilidad y mantenimiento.

### 10.4 Qué afirman las pruebas (272, todas en verde)

| Archivo | Tests | Qué afirma de verdad |
|---|---|---|
| `test_reglas.py` | 35 | Normalización (separadores, cifras, orden de palabras), validador R1–R7 con Bing declarado y encubierto, una evidencia mala tumba el insight, prefiltro (4), cobertura y redistribución (6) |
| `test_scoring.py` | 44 | F1–F6 uno a uno, independencia del tamaño, piso de ELIC con `hay_dato`, winsorizado, normalización de cohorte, pesos desde archivo y validación, ranking, empate reproducible, tope configurable, umbral apagado y reactivable, caso Armenia |
| `test_informes.py` | 39 | Frase de fuentes, contexto con fuente y año, composición (validados, pedidos, hueco de prosa, tope), publicación (dos corridas congeladas, inmutables, archivado, índice único, parcial y sin cadena rechazadas), aportes por fuente, semilla y trayecto |
| `test_persistencia.py` | 29 | Insights con origen, rechazados guardados, dos pasadas conviven, FK activa, `ids_insight_origen` reales, troceo por lotes, descartes declarados y no declarados, linaje de prompt por hash con `PromptDivergente`, `texto_de` para RSS y SECOP, `VERSION_PIPELINE` |
| `test_corridas.py` | 23 | Scoring append-only, `tipo_corrida` calculado y reverificable, corte de cohorte mínimo y con faltantes, versión y pesos verbatim, informe no reapuntable, `procesar_ciclo` encadena scoring (con dobles), fallo del scoring no pierde tokens, `corte_por_fuente`, `valores_crudos` |
| `test_contexto.py` | 23 | Formato numérico de TerriData, extracción con las cinco trampas, derivación per cápita y por predio, clases fijas, cuartiles, **ni un dígito en el prompt**, `VERSIONES_CON_CONTEXTO`, tres reglas en v2 |
| `test_correlacionador.py` | 19 | `ensamblar`: cruce de categorías, `otro`, ids no entregados, unión de evidencia sin pérdida, dedup por cita, confianza normalizada; `_resumen_calificaciones` |
| `test_nomenclator.py` | 16 | Construcción (Bogotá, San Andrés, códigos TerriData), homónimos, carga idempotente sin borrado, CSV con BOM |
| `test_seleccion.py` | 16 | Cuota 3+1+1, relleno, siempre 5, misma semilla ⇒ misma muestra, orden de entrada irrelevante |
| `test_conexion.py` | 8 | Reescritura de URL a psycopg 3, SQLite absoluta, `-pooler` rechazado en los dos caminos (uno de ellos por `grep` del texto de `env.py`) |
| `test_contrato.py` | 7 | Contrato TS al día, solo dos tablas, unión de tipos, rango 1–5, determinista |
| `test_cifras.py` | 7 | Falso positivo «76 y 80», mínimo de 3 dígitos, variantes de redondeo |
| `test_compuertas.py` | 6 | Invariante «no suspende a su línea base» sobre las **constantes** `PISO_RUIDO` (H-036); 40 ≤ 42 y 35 > 24 como aserciones fijas |

Todos corren sobre SQLite en memoria con `create_all` (legítimo en pruebas,
declarado en `test_persistencia.py:3-5`) y aislados de `config/pesos.json`
(`conftest.py`). Lo que **ningún test toca**, verificado por `grep` de importación
o monkeypatch:

| Sin prueba | Qué es | Por qué importa |
|---|---|---|
| `ingesta/snapshot.py` | **Toda M1**: `_senales_del_municipio`, `_ciclo_de`, `_hash`, `cargar` | La partición por ciclo (D2) y el `hash_dedup` (H-001) no tienen ni un caso |
| `scoring/agregacion.py` | `entradas_del_ciclo`, `cortes_por_fuente`: el único código de M5 que lee la base | Un error aquí cambia F1–F6 con los 44 tests de `factores`/`ranking` en verde; el área 3 lo verificó por recomputación, no la suite |
| `ciclo.procesar_municipio` | El encadenado M2 → M3 → M4 por municipio, los lotes fallidos, el error del Correlacionador | Es donde viven H-037 y H-038; `procesar_ciclo` solo se prueba con dobles y `solo=["00000"]` |
| `agentes/clasificador.clasificar_lote`, `agentes/correlacionador.correlacionar`, `agentes/cliente` | Las llamadas al modelo y sus ramas de error (`salida is None`, excepción → `error`) | Sin un cliente simulado, el comportamiento ante el proveedor caído solo se conoce por lectura (H-037, H-041) |
| `almacen/blob.py`, `utiles/divipola.py` | Almacén de objetos y normalización DIVIPOLA | `desde_bloque` decide la clave de todas las señales |
| `web/` completo | 0 archivos de prueba; sin framework de pruebas en `package.json` | CA-M7.x y CA-M9.x solo se verifican por GET y lectura (área 5) |

**H-050 · Medio · Brecha · Confianza Alta · Área 10 · CLAUDE.md §4 («las pruebas pasan» como garantía), H4**
*La suite no cubre la ingesta, la agregación del scoring, el encadenado por
municipio ni la aplicación web.* Los 272 tests pasan y son buenos donde llegan
—prueban propiedades, no aritmética—, pero dejan sin un solo caso los cuatro
puntos donde el código toca el mundo: leer el snapshot (`snapshot.py`), leer la
base para puntuar (`agregacion.py`), orquestar los agentes con sus fallos
(`procesar_municipio`) y todo `web/`. `test_compuertas.py` prueba constantes.
*Escenario:* un cambio en `_ciclo_de` o en `entradas_del_ciclo` mueve el ranking
publicado con la suite en verde; el área 3 tuvo que recomputar el scoring a mano
para afirmar que reproduce la corrida 24. Medio: no invalida lo medido —esta
auditoría lo reprodujo—, pero la garantía «las 272 pruebas pasan» no cubre lo que
más importa reproducir.

### 10.5 Código muerto, deuda y estilo

| Ítem | Evidencia |
|---|---|
| Símbolos definidos y sin uso | `AlmacenAzure` (`blob.py:89-116`, 0 usos, extra `azure` sin instalar), `pesos.escribir_plantilla` (`157-166`), `divipola.desde_codigo` (solo lo llama `desde_bloque`), `correlacionador.hash_entrada` (`470-473`, nunca llamado: H-006) |
| Columnas nunca pobladas | `senal_cruda.uri_blob` (20.030 NULL), `traza_agente.hash_output`, `id_prompt`, `id_dataset`, `id_traza_langfuse` (266 NULL), `insight.contexto_no_verificado` (1.213 en `False`, H-021), `informe.infografias` (4 × `[]`), `ciclo.n_*` (H-003), `tokens_razonamiento` calculado y no persistido (H-035) |
| Docstrings que describen un sistema anterior | `probar_correlacionador.py:5` («todavía no hay insights persistidos: M2 corre pero no guarda»); `clasificador.py:13-14` («debe descartar otro 61,4 %», cifra que B2 desmintió); `correr_ciclo.py:17` y `CLAUDE.md` §6 sobre `--seco` (H-038) |
| Scripts de calibración que no miden lo que corre | `probar_clasificador.py:57-62` y `comparar_prompts.py:124-128` envían `c.contenido` (título para RSS) mientras producción envía `texto_de` (título + resumen, `ciclo.py:199-215`) y prefiltran RSS, que producción no filtra (`ciclo.py:268-307`). Sus medidas de reducción y rechazo no son las del pipeline |
| `ruff check` | 7 avisos: 3 `I001` (orden de imports en las migraciones `14122d0ee975`, `aef93e016610`, `b37b4fd6e183`), `E501` y `B007` en `comparar_prompts.py`, `F541` en `medir_prefiltro.py`, `B007` en `probar_clasificador.py`. Ninguno en `src/` |
| TODO / FIXME / XXX / HACK | **0** (§0.2 #28) |

**H-051 · Bajo · Brecha · Confianza Alta · Área 10 · Deuda**
*Código muerto, columnas vacías y scripts de calibración desalineados con
producción.* Ocurrencias en la tabla de 10.5. Lo único con efecto potencial en
una medición es la desalineación de `probar_clasificador.py` y
`comparar_prompts.py` con `texto_de` y con el no-filtrado de RSS: cualquier
comparación de prompts hecha con ellos mide un pipeline distinto del que corre
(`VERSION_PIPELINE = "p2"`). Bajo porque los datos publicados salen de
`procesar_ciclo`, no de estos scripts.

### 10.6 Estado tras el área

| Elemento | Estado |
|---|---|
| Secretos en código e historial | **Cumple** |
| Credencial de Neon | **Riesgo aceptado R-A1** (dueño) |
| PII | **Riesgo Medio** (H-048); D3 registrada como decisión |
| Dependencias | **Riesgo Medio** (H-049) |
| Cobertura de pruebas | **Parcial** (H-050) |
| Deuda y estilo | **Bajo** (H-051); 0 TODO |

*Fin del área 10.*

---

## Preguntas abiertas (acumuladas; se consolidan en la sección 9 al cierre)

| # | Pregunta | Decide | Prioridad | Origen |
|---|---|---|---|---|
| P-5 | **Tarifa real de `gpt-5.4-mini` en el tenant de Pactia** (`config/tarifas.json` aplica la de `gpt-5-mini` y lo advierte). No está en el repositorio y no se buscó fuera. Sin ella, las cifras de H5 son condicionales (8b.2): total nacional = 1.586 + 239 × *k*. ¿Cuál es *k*? | Dueño / Analítica | Previa a la decisión go/no-go | Área 8b, H-035 |
| P-4 | **Infografía por municipio (CA-M6.2, CA-M9.4):** no existe en el código ni está especificada ni retirada. ¿Se **implementa**, se **especifica** (contenido, formato y cómo se compone sin cifras del modelo) o se **retira formalmente** del alcance del MVP con registro en `pendientes.md`? | Dueño | Previa a distribución | Área 5, H-020 |
| P-3 | **¿Qué lectura de CA-M6.3 rige?** (a) La literal del PRD: ninguna cifra *generada* sin fuente → los 15 insights con cifras transcritas cumplen y H-009 es un Riesgo por falta de compuerta. (b) La del propio proyecto (`reglas/contexto.py:3-6`): ninguna cifra *escrita* por el modelo → los 15 son una desviación no registrada y H-009 sube a Crítico. Decide también si la compuerta de `reglas/cifras.py` debe cablearse en `ciclo.py` antes de distribuir | Dueño | **Previa a distribución** | Área 3, H-009 |
| P-1 | **El informe 5 se compuso con el Correlacionador v1** (corrida 10, `version_correlacionador='v1'`, `id_prompt=2`) mientras `CLAUDE.md` declara vigente v2 desde el 2026-09-21. ¿Se republica el ciclo 3 con una corrida v2 —lo que exige volver a correr M4 y gastar tokens— o se corrige `CLAUDE.md` para que diga que lo publicado es v1? | Dueño | **🔒 Bloquea distribución** | Área 4, §4.3 |
| P-2 | **H-005 debe resolverse antes de cargar los 7 usuarios reales.** ¿Cómo se congela la lista de gerencias autorizadas por ciclo —en el payload del informe, en una tabla propia o en Alembic— para que el denominador de H2 no dependa del estado actual de `usuario`? | Dueño | **Previa a distribución** | Área 4, H-005 y §4.9 |
