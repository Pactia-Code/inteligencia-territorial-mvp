/**
 * Comprobacion de los mensajes de fallo y de la seleccion (F0.7, H-045).
 *
 *     node --experimental-strip-types web/lib/mensajes.prueba.mts
 *
 * Lo lanza `tests/test_web_modulos_puros.py` con el resto del suite. Lo que se
 * protege aqui es que **ningun fallo sea mudo ni generico**: un motivo sin
 * texto, o siete motivos con el mismo texto, devolverian el problema que F0.7
 * vino a quitar.
 */
import {
  MOTIVOS_CALIFICACION,
  mensajeDeCalificacion,
  seleccionVisible,
} from "./mensajes.ts";

let fallos = 0;
function comprobar(etiqueta: string, condicion: boolean, detalle = "") {
  if (!condicion) fallos++;
  console.log(`${condicion ? "OK  " : "FALLA"}  ${etiqueta}${detalle ? " -> " + detalle : ""}`);
}

console.log("--- mensajes ---");
const textos = MOTIVOS_CALIFICACION.map(mensajeDeCalificacion);
comprobar("los 8 motivos tienen texto", textos.every((t) => t.trim().length > 20));
comprobar("ningun texto se repite", new Set(textos).size === textos.length,
  `${new Set(textos).size} distintos de ${textos.length}`);
comprobar("todos dicen que no se guardo", textos.every((t) => t.startsWith("No se guardó")));
comprobar("el fallo del driver conserva la seleccion en el texto",
  mensajeDeCalificacion("error_al_guardar").includes("selección sigue marcada"));
comprobar("el de gerencia dice a quien acudir",
  mensajeDeCalificacion("gerencia_no_congelada").includes("Escribe a quien"));
for (const m of MOTIVOS_CALIFICACION) {
  console.log(`      ${m}: ${mensajeDeCalificacion(m)}`);
}

console.log("--- seleccion visible ---");
comprobar("fallo del driver: se marca lo pulsado aunque no se guardara",
  seleccionVisible(undefined, { ok: false, valor: 4 }) === 4);
comprobar("exito: manda lo guardado",
  seleccionVisible(5, { ok: true, valor: 5 }) === 5);
comprobar("lo guardado manda sobre un intento fallido de cambiarlo",
  seleccionVisible(4, { ok: false, valor: 5 }) === 4);
comprobar("sin intento y sin guardado, nada marcado",
  seleccionVisible(undefined, null) === undefined);
comprobar("fallo sin valor (valor_invalido) no marca nada",
  seleccionVisible(undefined, { ok: false, valor: null }) === undefined);

process.exitCode = fallos ? 1 : 0;
console.log(fallos ? `\n${fallos} FALLAN` : "\ntodas pasan");
