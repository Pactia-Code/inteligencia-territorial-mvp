# Ronda de calificación — ciclo 3, informe 8

**Plazo: martes 2026-09-29.** Registro de las sesiones 1 a 1 y de cualquier
cambio hecho durante el congelamiento.

El avance en vivo no se anota aquí: se consulta, que es más fiable que una
tabla escrita a mano.

```powershell
$py = "$env:LOCALAPPDATA\venvs\territorial\Scripts\python.exe"
& $py scripts\avance_calificacion.py            # por persona y por gerencia
& $py scripts\avance_calificacion.py --csv
```

> **La condición se registra por sesión, no de una vez para toda la ronda.** La
> ronda se **diseñó** como sesiones 1 a 1 acompañadas, pero **las tres sesiones
> registradas hasta el 2026-09-24 ocurrieron sin acompañamiento**, así que la
> columna «Acompañada» de la tabla es el dato que manda y no esta cabecera.
>
> **H2 del PRD mide calificación sostenida sin acompañamiento.** Al reportar hay
> que separar las dos condiciones en vez de etiquetar la ronda entera; una tasa
> agregada sobre sesiones mixtas no dice nada de H2.
>
> **Ninguna calificación se descarta por rápida.** El tiempo entre
> calificaciones de una misma persona se conserva como dato del análisis: dice
> algo sobre cómo se usa la herramienta, y descartarlo sería decidir de antemano
> qué cuenta como calificación legítima. Ver
> [plan-siguientes-pasos.md](plan-siguientes-pasos.md) y
> [decisiones-remediacion.md](decisiones-remediacion.md).

## Cómo se conduce la sesión

- **Cada persona teclea su propio correo y emite sus propias calificaciones.**
  `calificacion.id_usuario` registra quién tecleó; calificar por otro dejaría un
  registro falso.
- **Se explica la herramienta, no los insights.** Lo que H1 mide es si el
  insight le parece relevante a la gerencia, no si se entiende la pantalla.
- **No se comenta ante nadie la calificación de otro** (CA-M7.2). Basta con
  mencionar «fulano le puso 5» para que dejen de ser independientes.
- **Se piden 5 insights en cada uno de los 3 primeros municipios: 15 en total.**
  El resto del informe es opcional y se puede leer sin calificar.

## Sesiones

| Fecha | Persona | Gerencia | Tipo | Acompañada | Notas |
|---|---|---|---|---|---|
| 2026-09-23 | Juan Antonio Echeverri · jecheverri@pactia.com | administrativa | adicional | **no** | **15 de 15, completa.** Calificó por su cuenta |
| 2026-09-23 | Sandra Patricia Herrera Sanchez · sherrera@pactia.com | rotacion_portafolio | prd | **no** | **2 de 15, sesión incompleta.** Empezó por su cuenta, 15:47 |
| 2026-09-23 | Wilmar Stiven Sanchez Muñoz · wsanchez@pactia.com | analitica | adicional | — (prueba de humo) | **6 de 15.** Operador del pipeline. Calificaciones **reales**, emitidas al verificar el despliegue: cuentan para el análisis |
| 2026-09-24 | Sandra Patricia Herrera Sanchez · sherrera@pactia.com | rotacion_portafolio | prd | **no** | **Segunda sesión: las 13 que faltaban, 22:53 a 23:08. Queda en 15 de 15.** Volvió por su cuenta al día siguiente, y **ya con la pantalla de entrada desplegada** |
| 2026-09-25 | Rodrigo Adolfo Cuentas Rodriguez · rcuentas@pactia.com | juridica | prd | **no** | **15 de 15, completa**, 08:55 a 09:15 (19,5 min). **8 comentarios**, la sesión que más comentó de toda la ronda |
| 2026-09-25 | Lina Maria Navarro Villa · lnavarro@pactia.com | producto_hoteles_oficinas | prd | **no** | **15 de 15, completa**, 09:30 a 09:52 (21,7 min). 3 comentarios |
| | Andres Bejarano Palacios · abejarano@pactia.com | general | prd | | |
| | Edwin Gómez Villalobos · egomez@pactia.com | producto_logistica | prd | | |

Las 5 gerencias `prd` son el núcleo del experimento; `analitica` y
`administrativa` se reportan aparte (F0.1b).

> **Las horas son de Bogotá y las de la base son UTC.** Las 13 calificaciones
> de la segunda sesión de Herrera figuran en `calificacion.creado_en` con fecha
> **2026-09-25** —entre las 03:53 y las 04:08— porque Colombia va cinco horas
> por detrás. Son de la noche del 24 en local. Al contar sesiones por día hay
> que convertir, o la misma sesión sale partida en dos fechas.

### Dónde estamos al 2026-09-25, 10:00 de Bogotá

**66 de 105 calificaciones pedidas** (15 × 7), y **3 de las 5 gerencias `prd`
han terminado**: `juridica`, `producto_hoteles_oficinas` y
`rotacion_portafolio`. También está completa `administrativa`, que es adicional
y no cuenta para H2. Quedan sin empezar **`general` y `producto_logistica`**.

La mañana del 25 aportó **30 calificaciones en una hora**, en dos sesiones
seguidas: jurídica de 08:55 a 09:15 y hoteles y oficinas de 09:30 a 09:52.

Cuatro cosas que conviene ver ahora y no al analizar:

- **Ninguna de las sesiones registradas fue acompañada.** El plan preveía lo
  contrario, así que **lo que la ronda está midiendo es la condición que H2 sí
  mide**. Con 3 de 5 gerencias `prd` completas sin acompañamiento, eso ha dejado
  de ser una anécdota y pasa a ser el resultado principal.
- **Herrera terminó en dos sesiones, no en una.** Se quedó en 2 de 15 el día 23
  y volvió el 24 a completar las 13 restantes. Eso cambia lo que se puede decir
  de la primera: **abandonar no fue definitivo**, y al reportar conviene contar
  sesiones y no solo personas.
- **Completar lleva unos 20 minutos.** Las cuatro sesiones completas van de 13,4
  a 21,7 minutos para 15 insights. Es un dato de esfuerzo que H2 necesita y que
  no se deduce del conteo.
- **Los comentarios se concentran.** Hay 13 en total y **11 son de las dos
  sesiones del 25** (jurídica 8, hoteles 3). Al analizar H1 conviene mirar si
  eso es la persona, el momento o los insights que les tocaron, y no darlo por
  «unas gerencias se implican más».

## Congelamiento

Hasta el corte del martes **no se republica el informe** ni se cambia nada que
altere lo que ven los calificadores: ni el payload, ni los textos, ni la
selección pedida. Un informe republicado cambiaría los insights pedidos y las
calificaciones ya emitidas dejarían de ser comparables.

**Solo se corrige un error que impida calificar**, y se anota aquí.

> **Excepción autorizada por el dueño el 2026-09-24.** Se permiten cuatro
> correcciones que **no cambian el informe ni cómo se califica**: el fallo de
> `/priorizados` —que arrastraba el del botón «cambiar estado», es el mismo—,
> las páginas «Próximamente» de las rutas sin construir y la pantalla de
> entrada. **Cada una en su rama, revisada y fusionada por el dueño.** Ver
> P0.5 del [plan](plan-siguientes-pasos.md) y
> [decisiones-remediacion.md](decisiones-remediacion.md).

### Excepciones aplicadas

Las tres, el **2026-09-24**. **Ninguna cambió el informe ni cómo se califica**:
ni el payload, ni los insights pedidos, ni las reglas de alcance. Las
calificaciones ya emitidas siguen siendo comparables con las que vengan.

| Fecha | Qué se cambió | Por qué | A quién afectó | Cómo llegó |
|---|---|---|---|---|
| 2026-09-24 | **`/priorizados` y «cambiar estado»** dejan de caerse en el navegador | Un componente de cliente arrastraba el driver de base al navegador y la página reventaba al hidratar. **Impedía usar el tablero entero** | A cualquiera que abriera Priorizados. La vista de ciclo, donde se califica, **no estaba afectada** | **PR #2**, merge `100f7b1` |
| 2026-09-24 | **«Próximamente»** en `/historico` y `/metricas` | Las dos entradas del menú daban 404, que durante la ronda se lee como que el sistema está roto | A quien pulsara esas entradas | **PR #2** |
| 2026-09-24 | **Pantalla de entrada** con correo y logo | Decisión del dueño: privacidad e imagen. Antes el informe se leía con solo tener el enlace | **A todos**, y es la que más se nota: ahora hay que entrar antes de ver nada | **PR #3**, merge `45ec4d2` |

> **La tercera cambia lo que se encuentra quien aún no ha entrado.** No altera el
> informe ni la calificación, pero **sí lo que se ve al abrir el enlace**.
>
> **Y ya hay una medición de eso**: Herrera completó sus 13 calificaciones
> restantes el 24 por la noche, **con la pantalla de entrada ya desplegada** y
> sin acompañamiento. La puerta no le impidió calificar.

## Corte

**Martes 2026-09-29 a las 23:59, hora de Bogotá (UTC−5).** En la base, que
guarda en UTC, eso es **2026-09-30 a las 04:59**.

La exportación de `calificacion` a CSV va **fuera del repositorio**, **se
ejecuta después de esa hora** y filtra por:

```sql
WHERE creado_en <= '2026-09-30 04:59:59+00'
```

Esa foto es la que se analiza.

> **Por qué se escribe el instante en los dos husos.** Las calificaciones de la
> segunda sesión de Herrera figuran en la base con fecha **25** siendo de la
> noche del **24** en Bogotá. Un corte definido solo como «el martes» se
> aplicaría mal por cinco horas, y se llevaría por delante justo las
> calificaciones de última hora, que son las que más probable es que lleguen.
>
> Nota sobre el predicado: `<= '04:59:59+00'` deja fuera la fracción de segundo
> entre `04:59:59.000001` y `04:59:59.999999`. Si se quiere el mismo límite sin
> ese hueco, el equivalente exacto es `< '2026-09-30 05:00:00+00'`. Queda a
> decisión del dueño; el filtro oficial es el de arriba.

**La app no cierra el ciclo sola**: nada en el código impide calificar después
del martes, así que el corte lo define la exportación y no el sistema. Si
alguien califica el miércoles, la calificación existirá en la base pero no
estará en la foto — y la diferencia hay que declararla al reportar.
