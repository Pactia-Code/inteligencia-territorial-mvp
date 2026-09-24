/**
 * A donde se vuelve despues de entrar, y sobre todo a donde NO.
 *
 * El destino viaja en la URL de `/entrar`, asi que lo escribe quien mande el
 * enlace. Una redireccion abierta en una pantalla de entrada es de las peores:
 * la persona ve el dominio correcto, teclea su correo y acaba en otro sitio.
 *
 * Se lanza desde `tests/test_puerta_de_entrada.py`.
 */
import { destinoSeguro, DESTINO_POR_DEFECTO } from "./destino.ts";

let fallos = 0;

function comprueba(que: string, real: unknown, esperado: unknown) {
  const ok = real === esperado;
  if (!ok) {
    fallos++;
    console.error(`  FALLA  ${que}\n         esperado ${JSON.stringify(esperado)}, dio ${JSON.stringify(real)}`);
  }
}

// --- Rutas internas: se conservan enteras -------------------------------
comprueba("una ruta simple pasa", destinoSeguro("/priorizados"), "/priorizados");
comprueba(
  "con parametros, tambien",
  destinoSeguro("/ciclo/3?m=73001"),
  "/ciclo/3?m=73001",
);
comprueba(
  "los filtros del tablero sobreviven",
  destinoSeguro("/priorizados?estado=descartado&orden=fecha"),
  "/priorizados?estado=descartado&orden=fecha",
);

// --- Lo que hay que rechazar --------------------------------------------
for (const malo of [
  "//evil.com",          // protocolo relativo: es otro dominio
  "/\\evil.com",         // varios navegadores normalizan la barra invertida
  "https://evil.com",
  "http://evil.com",
  "evil.com",
  "javascript:alert(1)",
  "/priorizados\nSet-Cookie: x=1", // salto de linea
  "  /priorizados\u0000",
]) {
  comprueba(
    `se rechaza ${JSON.stringify(malo)}`,
    destinoSeguro(malo),
    DESTINO_POR_DEFECTO,
  );
}

// --- Vacios y bucles ------------------------------------------------------
comprueba("sin destino, a la raiz", destinoSeguro(undefined), DESTINO_POR_DEFECTO);
comprueba("cadena vacia, a la raiz", destinoSeguro(""), DESTINO_POR_DEFECTO);
comprueba("nulo, a la raiz", destinoSeguro(null), DESTINO_POR_DEFECTO);
comprueba(
  "volver a /entrar seria un bucle",
  destinoSeguro("/entrar"),
  DESTINO_POR_DEFECTO,
);
comprueba(
  "y con parametros, igual",
  destinoSeguro("/entrar?destino=%2Fentrar"),
  DESTINO_POR_DEFECTO,
);

if (fallos) {
  console.error(`\n${fallos} comprobacion(es) fallan en destino.ts`);
  process.exit(1);
}
console.log("destino.ts: todas pasan");
