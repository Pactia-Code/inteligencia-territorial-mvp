/**
 * Guarda de empaquetado: la base de datos no puede viajar al navegador.
 *
 * **Por que hace falta una guarda y no basta con tener cuidado.** Bastaba una
 * linea —`import { EXIGEN_NOTA } from "@/lib/tablero"` en un componente
 * `"use client"`— para que el empaquetador arrastrase `lib/db.ts` y el driver
 * de Neon entero a `.next/static`. Alli `process.env.DATABASE_URL` no existe
 * nunca (Next solo expone las `NEXT_PUBLIC_*`), asi que el modulo lanzaba al
 * evaluarse y tumbaba `/priorizados` en cualquier navegador.
 *
 * Lo peligroso es lo que **no** avisa:
 *
 *   · `tsc --noEmit` pasa: los tipos son correctos.
 *   · `next build` pasa: compilar el modulo para el cliente es legal.
 *   · `curl` devuelve **200 con el HTML correcto**: el servidor renderiza bien
 *     y curl no ejecuta JavaScript.
 *
 * Tres comprobaciones en verde y la pagina rota. Por eso esto mira el
 * resultado del build en vez de fiarse del codigo fuente.
 *
 * Uso:
 *   node scripts/verificar_bundle.mjs            # tras `next build`
 *   node scripts/verificar_bundle.mjs --probar   # se comprueba a si misma
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const ESTATICO = join(process.cwd(), ".next", "static");

/**
 * Lo que no puede aparecer en nada que se sirva al navegador.
 *
 * Son huellas del **modulo**, no del valor: la credencial nunca estuvo en el
 * bundle —Next no inlinea `DATABASE_URL`— y el fallo no era una fuga, era un
 * `throw`. Aun asi se buscan tambien un par de formas del valor, porque si
 * alguien llegara a inlinear la cadena el sintoma seria mudo y mucho peor.
 */
const PROHIBIDO = [
  { patron: "Falta DATABASE_URL", que: "el throw de lib/db.ts" },
  { patron: "@neondatabase/serverless", que: "el driver de Neon" },
  { patron: "neon.tech", que: "un host de Neon (posible credencial)" },
  { patron: "postgresql://", que: "una cadena de conexion" },
  { patron: "npg_", que: "una credencial de Neon" },
];

function archivos(dir) {
  const salida = [];
  for (const entrada of readdirSync(dir)) {
    const ruta = join(dir, entrada);
    if (statSync(ruta).isDirectory()) salida.push(...archivos(ruta));
    else salida.push(ruta);
  }
  return salida;
}

function revisar(textos) {
  const hallazgos = [];
  for (const [nombre, contenido] of textos) {
    for (const { patron, que } of PROHIBIDO) {
      if (contenido.includes(patron)) hallazgos.push({ nombre, patron, que });
    }
  }
  return hallazgos;
}

// `--probar`: se prueba la guarda contra un caso que sabemos malo y otro
// bueno. Una guarda que nunca ha fallado no ha demostrado que detecte nada.
if (process.argv.includes("--probar")) {
  const malo = revisar([
    ["falso.js", 'let n=e.env.DATABASE_URL;if(!n)throw Error("Falta DATABASE_URL. En Vercel...")'],
  ]);
  const bueno = revisar([["falso.js", 'let c=["descartado","en_estructuracion"];']]);
  const ok = malo.length === 1 && bueno.length === 0;
  console.log(ok
    ? "guarda probada: detecta el caso malo y deja pasar el bueno"
    : `guarda ROTA: malo=${malo.length} (esperado 1), bueno=${bueno.length} (esperado 0)`);
  process.exit(ok ? 0 : 1);
}

let rutas;
try {
  rutas = archivos(ESTATICO).filter((r) => r.endsWith(".js"));
} catch {
  console.error(`no existe ${ESTATICO}: corre \`next build\` antes.`);
  process.exit(2);
}

if (!rutas.length) {
  console.error("no hay ningun .js en .next/static: el build no dejo nada que revisar.");
  process.exit(2);
}

const hallazgos = revisar(rutas.map((r) => [r, readFileSync(r, "utf8")]));

if (hallazgos.length) {
  console.error("\nLA BASE DE DATOS VIAJA AL NAVEGADOR. El build no es publicable.\n");
  for (const h of hallazgos) {
    console.error(`  ${h.nombre}`);
    console.error(`      contiene ${h.que}  («${h.patron}»)`);
  }
  console.error(
    "\nCausa habitual: un componente `\"use client\"` importa algo de un modulo\n" +
      "que —directa o indirectamente— importa `lib/db.ts`. Saca esa constante o\n" +
      "ese tipo a un modulo sin dependencias de servidor, como `lib/estados.ts`.\n",
  );
  process.exit(1);
}

console.log(`bundle limpio: ${rutas.length} archivos de .next/static revisados, ` +
  "ninguno trae la base de datos.");
