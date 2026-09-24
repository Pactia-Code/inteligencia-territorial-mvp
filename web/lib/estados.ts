/**
 * Los estados del tablero de seguimiento. **Constantes puras, sin servidor.**
 *
 * Este modulo existe por una razon concreta y vale la pena dejarla escrita,
 * porque el fallo que lo motivo no lo ve ni `tsc` ni un `curl`.
 *
 * `EXIGEN_NOTA` vivia en `lib/tablero.ts`, que importa `./db`, y `db.ts`
 * **lanza en el cuerpo del modulo** si falta `DATABASE_URL`. Al importarlo
 * desde `CambiarEstado.tsx` —que es `"use client"`— el empaquetador se llevaba
 * `tablero.ts`, `db.ts` y el driver de Neon entero **al navegador**, donde
 * `process.env.DATABASE_URL` no existe nunca: Next solo expone las
 * `NEXT_PUBLIC_*`. Resultado: el chunk reventaba al evaluarse, React subia el
 * error y `error.tsx` tapaba una pagina que el servidor habia compuesto bien.
 *
 * De ahi la regla: **lo que importe un componente de cliente no puede colgar,
 * ni de lejos, de un modulo que toque la base.** Una constante compartida entre
 * cliente y servidor vive aqui, no junto a las consultas.
 *
 * La guarda que lo impide de verdad es `scripts/verificar_bundle.mjs`, porque
 * esta nota no la lee el empaquetador.
 */

/**
 * El estado con el que un municipio entra al tablero (CA-M9.8).
 *
 * **Nadie se da de alta a mano**: el tablero es derivado, y `seguimiento` solo
 * guarda los cambios sobre este estado inicial.
 */
export const ESTADO_INICIAL = "priorizado";

/**
 * Los dos estados que **exigen nota** al pasar a ellos (CA-M9.9).
 *
 * Son los que cierran o comprometen: descartar apaga un municipio que el
 * sistema priorizo, y estructurar mueve recursos. Sin el porque, el historial
 * guarda que paso y no por que.
 *
 * La comprobacion que manda es la del servidor (`app/acciones.ts`): un
 * `required` de HTML se salta con cualquier cliente. Aqui el cliente solo la
 * usa para **avisar antes** de enviar.
 */
export const EXIGEN_NOTA: readonly string[] = ["descartado", "en_estructuracion"];
