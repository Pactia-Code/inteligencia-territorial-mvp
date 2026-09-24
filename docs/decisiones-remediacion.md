# Decisiones del dueño para la remediación F0

**Fecha:** 2026-09-22
**Referencia:** `docs/auditoria.md` (rama `audit/2026-09-22`, commit `c6f660b`),
sección 7 «Plan de remediación», fase F0 «Prerrequisitos de distribución», y
sección 9 «Preguntas abiertas». La auditoría describe el commit `96e10e0`; la
remediación parte de ese mismo commit en la rama `remediacion/f0`.

## Decisiones

- **Token de F0.3 (H-012): ADOPTADO.** Enlace personal por usuario con token
  aleatorio, entrega única por canal interno. El riesgo condicional R-A2 **no se
  activa**.
- **P-2:** congelar la lista de gerencias en el **payload del informe** (opción
  que asume el plan en F0.1).
- **P-4:** se **retira formalmente la infografía** del MVP; queda para Fase 0.
- **P-5:** **abierta**; no bloquea F0. Analítica aportará la tarifa real de
  `gpt-5.4-mini` para F0b.2.
- **P-6: CERRADA el 2026-09-22. No se consulta a jurídica y el dueño acepta el
  riesgo.** La combinación es **H-048 + R-A1**: datos personales de 19.640
  registros de SECOP (`proveedor`, `rep_legal`) y, tras la carga, los de los
  calificadores, en una base gestionada externa **cuya credencial de escritura
  se sabe expuesta y no se rotará**. La auditoría no emitió juicio legal y
  sigue sin emitirlo; lo que cambia es que **ya no queda como pregunta
  pendiente**: es un riesgo aceptado por escrito, con nombre y fecha. **Deja de
  condicionar la carga de usuarios**, que ahora solo depende de la confirmación
  del dueño para ejecutarla.
- **P-1:** **cerrada** (v1 publicado; corrección de `CLAUDE.md` en F0.5).

## Decisiones del 2026-09-22 sobre calificadores y secuencia (segunda tanda)

Registradas tras cerrar F0.1. Amplían, no sustituyen, las de arriba.

- **a) El conjunto de calificadores no se cierra a las 7 gerencias del PRD.**
  Podrá incluir **gerencias adicionales** —por ejemplo Analítica, que no es una
  de las 7—. **Es una desviación del PRD** (§1 «7 gerencias», CA-M9.1) y se
  registra como tal. Qué usuarios califican **se decide antes de la
  republicación definitiva de F0.6**, porque la lista se congela al publicar.
- **b) Cómo se reporta.** **H2 se reporta siempre sobre las 7 gerencias del
  PRD**; los calificadores adicionales, **por separado**. **H1 se reporta con y
  sin ellos.** De ahí la marca `prd` / `adicional` de F0.1b: sin ella, las dos
  cifras no se pueden separar después.
- **c) Usuarios del dueño: dos, distintos.** Uno con rol `administrador` y otro
  con rol `gerencia` de **Analítica (adicional)**, con **correos distintos**
  (variante con `+`). Motivo, que es el que hay que conservar: **el operador del
  pipeline también califica**, así que hay conflicto de interés en H1 y sus
  calificaciones tienen que poder separarse de las demás.
- **d) Semilla de usuarios.** La lista real vive en un **archivo ignorado por
  git** y `scripts/cargar_usuarios.py` la lee de ahí. **Los tokens nunca se
  escriben** en ese archivo, ni en la base en claro, ni en logs: se generan en
  la carga y **se muestran una sola vez**. La carga de usuarios reales **no
  forma parte de F0** y no se hace sin confirmación del dueño. *(La condición de
  P-6 sobre esta carga quedó levantada el 2026-09-22: ver la decisión de arriba.
  Y los tokens quedaron sin efecto en la tercera tanda, que no los adopta.)*
- **e) F0.4 ampliada.** Las Server Actions de calificación y comentario solo
  aceptan a un usuario con rol `gerencia` **cuya `id_gerencia` esté en la lista
  congelada del payload**. Un administrador, o una gerencia dada de alta
  después de publicar, **recibe error y no escribe**.
- **f) F0.6 cambiada.** Se **prepara y verifica en un branch de Neon** con
  usuarios de prueba. La **republicación definitiva en la base principal ocurre
  después** de cargar los usuarios reales y **desactivar los de prueba**, y
  **la ejecuta el dueño** con el comando que se le deje preparado.

## Decisiones del 2026-09-22 sobre identidad y gerencias reales (tercera tanda)

**Esta tanda sustituye lo decidido antes sobre el token, el enlace personal y el
archivo de semilla de usuarios.** Donde contradiga a las dos anteriores, manda
esta.

- **1) No se adopta el token. La identificación es por correo tecleado.** Se
  activa **R-A2**: **H-012 queda abierto como riesgo aceptado por el dueño**, no
  cerrado. Quien conozca un correo autorizado puede calificar por esa gerencia, y
  el `id_usuario` registrado sería el del suplantado. F0.3 pasa a reducir el
  residual sin eliminarlo: **firma la cookie** para que no se pueda forjar
  editándola, **restringe la identificación a correos registrados y activos** y
  **deja rastro** de cada identificación y de quién escribió cada calificación.
  Al publicar H1 y H2 hay que decir que la atribución es **declarativa**.
- **2) El núcleo del experimento son 5 gerencias, no 7.** Es una **desviación del
  PRD**, que habla de 7 (§1, CA-M9.1).
  - `prd`: `general`, `juridica`, `rotacion_portafolio`, `producto_logistica`,
    `producto_hoteles_oficinas`.
  - **Financiera no participa**, y **Oficinas y Hotelería son una sola gerencia**.
  - `adicional`: `administrativa`, `analitica`.
- **3) Reporte.** H2 se reporta sobre las gerencias **`prd`**; las **adicionales,
  aparte**. H1 se reporta **con y sin** ellas.
- **4) Los dos usuarios del dueño.** Wilmar Sánchez tiene
  `wsanchez@pactia.com` (calificador de `analitica`) y
  `wsanchez+admin@pactia.com` (**administrador**). Son dos filas distintas
  porque **el operador del pipeline también califica** y sus calificaciones
  tienen que poder separarse al analizar H1.
- **5) `config/usuarios.csv` y `config/gerencias.json` se versionan en git**, por
  indicación del dueño de que no contienen datos sensibles. Cambia lo decidido
  en la tanda anterior (archivo ignorado): **ya no hay archivo ignorado ni
  tokens que ocultar**, porque no hay tokens.

### Consecuencias registradas de esta tanda

- **Una tabla más que la app escribe: `identificacion`** (quién se identificó,
  cuándo, con qué navegador y desde qué IP si el despliegue la da). CA-M9.16
  enumera `calificacion` y `seguimiento`; esto es **dato de sesión**, que el
  criterio de la auditoría admite, y **nace en Alembic** como todo lo demás. Se
  registra aquí para que la ampliación de la superficie de escritura sea
  explícita y no un descubrimiento posterior.
- **`calificacion.id_usuario`** queda **anulable**. La escribe siempre la app;
  se deja anulable para no obligar a fabricar un usuario en cada prueba o carga
  de Python. La garantía que importa —que toda calificación hecha desde la web
  lleva autor— vive en el camino de escritura, no en el esquema.
- **El rol de «solo lectura» no existe** y **no se ha creado**. El modelo admite
  `gerencia` y `administrador` (`ck_rol`). Una fila del CSV con
  `puede_calificar=no` y `es_administrador=no` **se rechaza con un mensaje que
  pide decidirlo**. Hoy ninguna fila está en ese caso. **Leer no requiere estar
  en `usuario`**, así que un usuario de solo lectura no necesita fila; si se
  quiere igualmente por registro, hay que ampliar `ck_rol` con una migración.
- **Guarda prevista para F0.6** (no implementada aún; se implementa en esa
  subfase): `publicar()` se negará si **no hay ninguna gerencia `prd`** entre las
  autorizadas, o si **alguna gerencia `prd` no tiene al menos un usuario activo
  con rol `gerencia`**. **Sin números fijos en el código**: el conjunto sale de
  `config/gerencias.json` y de `usuario`, no de un «5» ni de un «7» escritos a
  mano.

### El Correlacionador vuelve a v1 por defecto hasta que F2.3 valide v2

- **Decisión del 2026-09-22, antes de desplegar.** El valor por defecto era v2
  y lo publicado se compuso con v1 (F0.5), así que **el próximo ciclo habría
  estrenado un prompt sin comparación validada con linaje persistido** —eso es
  la subfase **F2.3**—. Se corrige el valor por defecto en vez de confiar en que
  nadie corra un ciclo antes de tiempo.
- **Valor por defecto en el código: `VERSION_PROMPT = v1`.** Esta línea es la
  que lee `tests/test_version_prompt.py`: si alguien cambia la constante sin
  actualizar este documento, o al revés, el suite falla.
- **v2 no se borra ni se degrada.** Sigue en
  `agentes/prompts/correlacionador_v2.md` y se elige **explícitamente**, pasando
  `version="v2"` a `correlacionar()` o a los scripts de comparación. Lo que
  cambia es qué corre cuando nadie elige.
- **Consecuencia que conviene saber:** `VERSIONES_CON_CONTEXTO` solo incluye v2,
  así que por defecto **el contexto estructural bandeado no viaja**, igual que
  en la corrida 10, que es la del informe publicado. Al validar v2 en F2.3,
  volverá a viajar.
- No afecta a lo ya publicado ni a la republicación de F0.6, que usan la corrida
  10.

### Se califica solo lo pedido; el resto del municipio es de consulta

- **Decisión del dueño del 2026-09-22**, al revisar F4.1. El bloque desplegable
  con el resto de los insights del municipio **no lleva controles de
  calificación**, y el texto de la pantalla lo dice así: es de consulta. El
  motivo es que **H1 y H2 tienen que comparar sobre la misma base**; si cada
  gerencia calificara un subconjunto distinto de los 49 insights de Funza, el
  «≥30% con promedio ≥4» mediría también qué eligió mirar cada quien.
- **Resuelto el 2026-09-22, y la regla vive en los dos sitios.** Quedaba la
  excepción de los **7 municipios de 10 que el informe no pide calificar**,
  donde la pantalla mostraba controles en sus primeros 5 insights —35 en total—
  sin que se hubiera pedido ninguno. Ya no:
  - **En pantalla**, `Panel.tsx` pasa `conCalificacion` solo cuando el municipio
    es calificable, así que los controles salen únicamente en los **15 insights
    pedidos** de los 3 municipios que sí se piden.
  - **En el servidor**, `lib/alcance.ts` exige además que el `id_insight` esté
    entre los `insights_pedidos` de un municipio calificable del payload
    publicado, con su propio motivo, `insight_no_pedido`, y su mensaje. **Ocultar
    el botón no impide el POST**, así que la regla no podía vivir solo en la
    vista.
  - **Comentar sigue exactamente la misma regla que calificar.** Hoy no
    difieren: las dos acciones pasan por la misma comprobación de alcance, y el
    comentario viaja en la misma fila de `calificacion`.

### Un informe sin lista congelada no admite calificaciones

- **Comportamiento conservador, aceptado por el dueño** (F0.4). Un informe
  publicado **antes** de F0.1 no lleva `calificacion.gerencias`, y el código lo
  trata como que **nadie estaba autorizado**: sin lista no hay forma de saber
  quién formaba el denominador de H2, y admitir calificaciones «por si acaso»
  las metería en una medición cuyo universo se desconoce.
- **Consecuencia directa: la republicación de F0.6 es obligatoria antes de abrir
  la ventana.** El informe 5, tal como está publicado hoy, no admitiría ni una
  calificación.

### Verificación en branch de Neon

- El dueño creará un branch y dejará su cadena **directa** en `.env` como
  `DATABASE_URL_NEON_BRANCH`. Sobre ese branch —y **nunca** sobre la base
  principal— se pueden aplicar migraciones y ejecutar la verificación completa
  de F0.4 por Next.js, con las Server Actions corriendo. Se usa también para
  F0.6. **Si al llegar a F0.6 la variable no existe, la ejecución se detiene y
  se avisa.**
- **El branch `remediacion-f0` no es fuente de datos. Es desechable.** Lo que
  hay ahí salió de verificar, no de operar: entre otras cosas contiene una
  **calificación de prueba** —insight **1088**, gerencia **general**, valor 4—
  escrita al comprobar que la regla «se califica solo lo pedido» acepta lo
  pedido y rechaza lo demás. También lleva informes republicados, usuarios de
  prueba desactivados y filas de `identificacion` de los clientes HTTP de las
  comprobaciones. **La base principal no tiene nada de esto**, y H1 y H2 no se
  miden sobre el branch. Si alguna cifra se saca de ahí por descuido, estará
  contaminada con datos que nadie emitió.

### Nota para F0b.3 (tasa de rechazo)

- **La tasa de rechazo se persiste y se reporta desglosada por regla**, no como
  un único porcentaje: **R1–R7** son fidelidad de cita —evidencia que no se
  sostiene— y **R8** es cifra sin fuente en la prosa. Son dos fallos distintos
  del modelo y mezclarlos en un número impide saber cuál está pasando. CA-M3.3
  dice que la tasa de rechazo **es** la tasa de alucinación medida, así que el
  desglose es parte de la medida, no un adorno del informe.

### Incidente

- **2026-09-22 — `config/gerencias.json` y `config/usuarios.csv` desaparecieron
  del disco a media sesión, sin causa encontrada** (nada en `tests/`, `scripts/`
  ni `src/` escribe o borra bajo `config/`, y el suite deja los cuatro archivos
  intactos; hipótesis externa no confirmada, del tipo antivirus, DLP o
  sincronización, sobre archivos recién creados). Restaurados con los hashes que
  dio el dueño; mitigado porque **ahora están versionados** —se recuperan con
  `git checkout -- config/`— y por la guarda `config_intacta` de `e24ebe7`, que
  falla si una prueba los toca. **No se investiga más.**

## Orden de ejecución acordado

F0.1 → **F0.1b** → F0.3 (sin token, ver tercera tanda) → F0.2 → F0.4 (ampliada por la decisión e) → F0.7 →
F0.8 → F0.5 → F0.6 (solo preparación y verificación en branch).

## Secuencia de republicación en la base principal

**La ejecuta el dueño. No se ha ejecutado.** Va entera y en este orden; el paso
2 es el que faltaba en la primera versión de estas instrucciones: **la base
principal sigue en `b37b4fd6e183`** y sin migrar no existen `usuario.cargo`,
`calificacion.id_usuario`, `identificacion` ni `informe.origen`.

La cadena de la base principal es la **directa**, no la del pooler: por el
endpoint `-pooler` no se migra. Y lleva `connect_timeout`, o la conexión se
cuelga sin error por IPv6.

```powershell
$py = "$env:LOCALAPPDATA\venvs\territorial\Scripts\python.exe"
$env:DATABASE_URL = "<cadena DIRECTA de la base principal>&connect_timeout=5"

# 1. Respaldo, FUERA del repositorio, antes de tocar nada.
pg_dump "$env:DATABASE_URL" -Fc -f C:\respaldos\territorial-antes-de-f06.dump

# 2. Migraciones: de b37b4fd6e183 a d5932c3bdc03 (tres pendientes).
& $py -m alembic upgrade head

# 3. Confirmar que subió de verdad. El `upgrade` puede mentir; esto no.
& $py -m alembic current          # debe decir d5932c3bdc03
& $py -m alembic check            # «No new upgrade operations detected»

# 4. Usuarios: primero mirar, después escribir.
& $py scripts\cargar_usuarios.py --previsualizar
& $py scripts\cargar_usuarios.py --confirmar

# 5. Publicación: primero en seco, después de verdad.
& $py scripts\publicar_informe.py --ciclo 3 --scoring 24 --agentes 10 --seco
& $py scripts\publicar_informe.py --ciclo 3 --scoring 24 --agentes 10
```

**Verificación posterior**, y si alguna falla hay que parar antes de repartir
el enlace:

1. **Lista congelada**: el payload del informe publicado trae **5 gerencias
   `prd`** —`general`, `juridica`, `producto_hoteles_oficinas`,
   `producto_logistica`, `rotacion_portafolio`— y **2 `adicional`**,
   `administrativa` y `analitica`. El propio script la imprime al publicar.
2. **`informe.origen`** con el commit, la invocación y la fecha.
3. **Traza del informe republicado: 241/241 insights, 933/933 citas y 10/10
   scores**, que son las cifras que la auditoría midió sobre el informe 5.
4. **El informe anterior queda archivado, no borrado**, y los dos usuarios de
   prueba quedan **inactivos**, tampoco borrados.

Lo verificado en el branch `remediacion-f0` fue exactamente esta secuencia, con
esos cuatro resultados.

## Reglas de ejecución

1. Una subfase por commit, sin arreglos oportunistas de otras.
2. Tests añadidos o actualizados; `pytest`, `tsc --noEmit` y
   `generar_contrato_ts.py --check` en verde antes de cada commit.
3. La verificación de cierre exacta del informe se ejecuta y su salida se pega en
   el mensaje de commit.
4. Migraciones y pruebas solo sobre SQLite local o una copia; ninguna migración a
   Neon sin preguntar. F0.4 y F0.6 se verifican en un branch de Neon.
5. Antes de F0.6 sobre la base principal: `pg_dump` de Neon fuera del repositorio
   y confirmación del dueño para republicar (corridas 24/10; cierre: traza
   241/241 repetida).
6. Sin usuarios reales ni tokens reales: solo el mecanismo y un usuario de prueba.

## Nota metodológica — la ronda se califica acompañada (2026-09-23)

La primera ronda de calificación se hace **1 a 1 con el dueño presente**: cada
gerente teclea su propio correo y emite sus propias calificaciones, pero en una
sesión acompañada y con plazo hasta el **martes 2026-09-29**.

**Eso condiciona lo que la tasa de respuesta puede demostrar.** **H2 del PRD
mide calificación sostenida y sin acompañamiento**, así que la tasa que salga de
esta ronda **se reporta como tasa en condición acompañada** y **no se compara
directamente con el criterio de éxito de H2**.

La asimetría importa al leer el resultado: una tasa alta aquí **no** demuestra
H2, porque se obtuvo en la condición más favorable que existe; una tasa baja sí
sería mala señal, por la misma razón.

Se registra en tres sitios para que no se pierda entre la medición y el informe:
aquí, en [plan-siguientes-pasos.md](plan-siguientes-pasos.md) y en la cabecera
de `scripts/avance_calificacion.py`, que es lo que se mira durante la ronda.

El registro de las sesiones —fecha, persona, gerencia y si fue acompañada— va en
[ronda-calificacion.md](ronda-calificacion.md).

## Tres ajustes a CLAUDE.md §2, decididos por el dueño (2026-09-23)

§2 de [CLAUDE.md](../CLAUDE.md) es normativa, así que sus reglas no se editan
por iniciativa de un agente. Al actualizar el documento aparecieron tres puntos
donde la regla chocaba con algo ya decidido o ya medido. **El dueño decidió los
tres y quedan aplicados:**

1. **§2.2 — fuera la mención a la infografía.** La regla decía «ninguna cifra de
   un informe **o infografía** puede provenir del LLM». La infografía se
   **retiró formalmente** del MVP en F0.8 (P-4), así que la regla nombraba un
   artefacto que ya no existe. **El fondo no cambia**: sigue siendo que ninguna
   cifra de un informe puede venir del LLM.
2. **§2.3 — qué mide de verdad la tasa de rechazo del validador.** Decía que
   **«es la tasa de alucinación medida»**, y eso afirma más de lo que el
   validador comprueba. Ahora dice que **mide la fidelidad de cita contra el
   contenido ingerido, no la veracidad respecto del mundo** (**H-029**). La
   distinción importa al publicar H4: una cita fiel a una fuente equivocada pasa
   las siete reglas.
3. **§2.3 — el linaje de prompts: la regla se mantiene sin cambios.** Los
   prompts van versionados y su linaje se registra (D7). Lo que falla no es la
   norma sino el cumplimiento: **el Correlacionador v2 se promovió sin fila en
   `prompt_version`** (**H-036**). Se añade una nota al corolario diciéndolo, y
   **lo cierra F2.3**. Mientras tanto el valor por defecto es v1, que sí tiene
   linaje y es lo publicado.

El §10 de CLAUDE.md, que los listaba como pendientes, queda **cerrado** con esta
decisión.

## Decisiones del dueño del 2026-09-24

### 1. Se descarta el SSO con Microsoft

No se integra inicio de sesión corporativo. Queda fuera del MVP y no se
replantea durante la ronda.

### 2. Pantalla de entrada solo con correo, sin clave

Se añade una pantalla de entrada que pide el correo antes de dejar pasar. Hoy
**el informe se lee sin identificarse**, y eso es lo que cambia.

**Mejora privacidad e imagen. No mejora la atribución, y conviene no
confundirlo:** sin clave, quien conozca un correo autorizado puede seguir
entrando y calificando por esa gerencia. **R-A2 y H-012 siguen abiertos** como
riesgo aceptado, exactamente igual que antes, y hay que declararlo al publicar
H1 y H2. Una pantalla de entrada *parece* autenticación, que es justo el motivo
por el que esto queda escrito.

Va en **P0.5** del [plan](plan-siguientes-pasos.md), estimada en 0,75 d.

### 3. Excepción al congelamiento de la ronda

El congelamiento sigue vigente para el informe: no se republica ni se cambia
nada que altere lo que ven los calificadores. **Se permiten las correcciones que
no cambian el informe ni cómo se califica**, que son cuatro:

1. el fallo de `/priorizados`,
2. el fallo del botón «cambiar estado» —que resultó ser **el mismo fallo**, ver
   P0.5 del plan—,
3. las páginas «Próximamente» de las rutas de navegación sin construir,
4. la pantalla de entrada.

**Cada una en su rama, revisada y fusionada por el dueño**, y anotada en
[ronda-calificacion.md](ronda-calificacion.md). Nada de esto toca el payload,
los insights pedidos ni las reglas de alcance de F0.4.

### 4. Los logos oficiales de Pactia

El dueño entregó los logos oficiales en `web/public/marca/`:

| Archivo | Para qué | Verificado |
|---|---|---|
| `pactia-logo.png` | Versión principal, azul y gris, para la pantalla de entrada sobre fondo claro | PNG RGBA, **874 × 282 px**, 8 bits, 26.941 bytes |
| `pactia-logo-blanco.png` | Versión en negativo, para la barra superior si es oscura | PNG con paleta y `tRNS`, **356 × 90 px**, 4.081 bytes |

**Son los oficiales y no se recolorean, recortan ni deforman.** Se usan en la
fase 3; hasta entonces están en el repositorio sin referenciar.

Tres cosas que salieron de la verificación:

- **`pactia-logo.png` no tiene transparencia.** Declara canal alfa pero está
  **100% opaco**: el 80% de sus píxeles son blanco puro, así que sobre cualquier
  fondo que no sea blanco se verá un rectángulo blanco. **No se corrige por
  iniciativa propia** — queda anotado para que el dueño decida.
- **`pactia-logo-blanco.png` sí la tiene**, y bien: 64,8% transparente, 8%
  semitransparente en los bordes y blanco puro como único color visible. Es una
  versión en negativo correcta.
- **El azul del logo choca con el primario del Design System.** El logo usa
  **`#1D2559`** y el token `color-navy-700` es **`#0F4761`**, marcado
  «Confirmado» y derivado de la plantilla Word corporativa. No es un matiz: uno
  tira a violeta (tono ≈232°) y el otro a cian (≈199°). Puestos juntos —logo
  arriba, títulos y botones en navy— se leerá como un error de color. **Son dos
  fuentes de marca que no concuerdan y lo tiene que resolver el dueño**, no el
  código.
- El gris del logo es **`#808080`**, un neutro puro, frente a los neutros del
  Design System, que son fríos (`#5B6670`, `#8A9199`). Choca menos y **importa
  menos**: esos neutros están marcados `[provisional]` y no son identidad de
  Pactia, mientras que el gris del logo sí.
