/**
 * Comprobacion de las reglas de alcance (F0.4, H-013). Se ejecuta con:
 *
 *     node --experimental-strip-types web/lib/alcance.prueba.mts
 *
 * **Por que no es un test normal:** el proyecto no tiene corredor de pruebas de
 * TypeScript, y montar uno para tres funciones puras seria mas infraestructura
 * que la que se prueba. `tests/test_alcance_web.py` lo lanza desde pytest, asi
 * que corre con el resto del suite y no se queda atras en silencio.
 *
 * Lo que se prueba aqui no es cosmetico: es **quien puede escribir**. Si estas
 * reglas se relajan, entran en H1 y en H2 filas que ninguna gerencia emitio.
 */
import { puedeCalificar, puedeMoverSeguimiento } from "./alcance.ts";

let fallos = 0;
function comprobar(etiqueta: string, real: unknown, esperado: unknown) {
  const ok = JSON.stringify(real) === JSON.stringify(esperado);
  if (!ok) fallos++;
  console.log(`${ok ? "OK  " : "FALLA"}  ${etiqueta} -> ${JSON.stringify(real)}`);
}

const CONGELADAS = [
  { id_gerencia: "general", tipo: "prd" as const },
  { id_gerencia: "juridica", tipo: "prd" as const },
  { id_gerencia: "analitica", tipo: "adicional" as const },
];
const GERENTE = { rol: "gerencia", id_gerencia: "general" };
const ADMIN = { rol: "administrador", id_gerencia: "analitica" };
const ADICIONAL = { rol: "gerencia", id_gerencia: "analitica" };
const NUEVA = { rol: "gerencia", id_gerencia: "dada_de_alta_despues" };

console.log("--- calificar ---");
comprobar("gerencia prd en la lista congelada", puedeCalificar(GERENTE, CONGELADAS, true), { ok: true });
comprobar("gerencia adicional en la lista", puedeCalificar(ADICIONAL, CONGELADAS, true), { ok: true });
comprobar("ADMINISTRADOR no califica", puedeCalificar(ADMIN, CONGELADAS, true),
  { ok: false, motivo: "rol_no_califica" });
comprobar("gerencia dada de alta DESPUES de publicar", puedeCalificar(NUEVA, CONGELADAS, true),
  { ok: false, motivo: "gerencia_no_congelada" });
comprobar("ciclo cerrado (CA-M7.7)", puedeCalificar(GERENTE, CONGELADAS, false),
  { ok: false, motivo: "ciclo_cerrado" });
comprobar("sin identificar", puedeCalificar(null, CONGELADAS, true),
  { ok: false, motivo: "sin_identificar" });
comprobar("informe sin lista congelada (anterior a F0.1)", puedeCalificar(GERENTE, undefined, true),
  { ok: false, motivo: "gerencia_no_congelada" });
comprobar("lista congelada vacia", puedeCalificar(GERENTE, [], true),
  { ok: false, motivo: "gerencia_no_congelada" });

console.log("--- seguimiento ---");
comprobar("municipio del informe", puedeMoverSeguimiento(GERENTE, ["05147", "73001"], "05147"), { ok: true });
comprobar("administrador tambien puede (CA-M9.9)", puedeMoverSeguimiento(ADMIN, ["05147"], "05147"), { ok: true });
comprobar("municipio que no esta en el informe", puedeMoverSeguimiento(GERENTE, ["05147"], "11001"),
  { ok: false, motivo: "fuera_de_alcance" });
comprobar("sin identificar", puedeMoverSeguimiento(null, ["05147"], "05147"),
  { ok: false, motivo: "sin_identificar" });

process.exitCode = fallos ? 1 : 0;
console.log(fallos ? `\n${fallos} FALLAN` : "\ntodas pasan");
