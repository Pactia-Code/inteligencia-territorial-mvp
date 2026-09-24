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
> agregada sobre sesiones mixtas no dice nada de H2. Ver
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
| 2026-09-23 | Sandra Patricia Herrera Sanchez · sherrera@pactia.com | rotacion_portafolio | prd | **no** | **2 de 15, sesión incompleta.** Empezó por su cuenta |
| 2026-09-23 | Wilmar Stiven Sanchez Muñoz · wsanchez@pactia.com | analitica | adicional | — (prueba de humo) | **6 de 15.** Operador del pipeline. Calificaciones **reales**, emitidas al verificar el despliegue: cuentan para el análisis |
| | Andres Bejarano Palacios · abejarano@pactia.com | general | prd | | |
| | Rodrigo Adolfo Cuentas Rodriguez · rcuentas@pactia.com | juridica | prd | | |
| | Lina Maria Navarro Villa · lnavarro@pactia.com | producto_hoteles_oficinas | prd | | |
| | Edwin Gómez Villalobos · egomez@pactia.com | producto_logistica | prd | | |

Las 5 gerencias `prd` son el núcleo del experimento; `analitica` y
`administrativa` se reportan aparte (F0.1b).

### Dónde estamos al 2026-09-24

**23 de 105 calificaciones pedidas** (15 × 7), y **0 de las 5 gerencias `prd`
han terminado**, a cinco días del corte. La única completa es `administrativa`,
que es adicional.

Dos cosas que conviene ver ahora y no al analizar:

- **Ninguna de las sesiones registradas fue acompañada.** El plan preveía lo
  contrario, así que lo que la ronda está midiendo hasta ahora es **la condición
  que H2 sí mide**. Los 15 de 15 de `administrativa` son el dato más
  interesante que hay, aunque sea de una gerencia adicional.
- **Sandra Herrera se quedó en 2 de 15.** Una sesión que empieza y no termina es
  distinto de no empezar, y al reportar hay que distinguirlas: la primera dice
  algo sobre el esfuerzo que pide calificar, la segunda no dice nada todavía.

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

| Fecha | Qué se cambió | Por qué impedía calificar | A quién afectó |
|---|---|---|---|
| — | *nada todavía: las cuatro están autorizadas pero sin hacer* | | |

## Corte

**Martes 29 al final del día**: exportación de `calificacion` a CSV **fuera del
repositorio**. Esa foto es la que se analiza.

**La app no cierra el ciclo sola**: nada en el código impide calificar después
del martes, así que el corte lo define la exportación y no el sistema. Si
alguien califica el miércoles, la calificación existirá en la base pero no
estará en la foto — y la diferencia hay que declararla al reportar.
