/**
 * Comprobación de la descripción de la muestra pedida (F1.5, H-015).
 *
 *     node --experimental-strip-types web/lib/seleccion.prueba.mts
 *
 * Lo lanza `tests/test_web_modulos_puros.py`. Lo que se protege es que el texto
 * **siga la composición real** y no una cuota escrita a mano: con la regla de
 * relleno cada municipio recibe su propia mezcla.
 */
import { describirComposicion } from "./seleccion.ts";

let fallos = 0;
function comprobar(etiqueta: string, real: string, esperado: string) {
  const ok = real === esperado;
  if (!ok) fallos++;
  console.log(`${ok ? "OK  " : "FALLA"}  ${etiqueta} -> «${real}»`);
}

comprobar("cuota completa 3+1+1",
  describirComposicion({ correlacionado: 3, contratacion: 1, prensa: 1 }),
  "3 correlacionados, 1 de contratación y 1 de prensa");

comprobar("con relleno: pocos correlacionados",
  describirComposicion({ correlacionado: 1, contratacion: 2, prensa: 2 }),
  "1 correlacionado, 2 de contratación y 2 de prensa");

comprobar("sin correlacionados, que es el caso que el texto viejo escondía",
  describirComposicion({ contratacion: 4, prensa: 1 }),
  "4 de contratación y 1 de prensa");

comprobar("un solo tipo", describirComposicion({ prensa: 5 }), "5 de prensa");

// El caso real de Armenia en el ciclo 3: solo 1 correlacionado y 1 de prensa,
// y el resto entra por la regla de relleno. Es justo el municipio donde el
// texto viejo mentía más.
comprobar("cuota de relleno, con su nombre y al final",
  describirComposicion({ correlacionado: 1, prensa: 1, relleno: 3 }),
  "1 correlacionado, 1 de prensa y 3 para completar");

comprobar("orden fijo aunque el objeto venga al revés",
  describirComposicion({ prensa: 1, correlacionado: 3, contratacion: 1 }),
  "3 correlacionados, 1 de contratación y 1 de prensa");

comprobar("los ceros no se nombran",
  describirComposicion({ correlacionado: 0, contratacion: 5 }),
  "5 de contratación");

comprobar("un informe sin composición registrada calla",
  describirComposicion({}), "");

comprobar("una cuota desconocida se muestra igual, no se traga",
  describirComposicion({ prensa: 1, inventada: 2 }),
  "1 de prensa y 2 inventada");

process.exitCode = fallos ? 1 : 0;
console.log(fallos ? `\n${fallos} FALLAN` : "\ntodas pasan");
