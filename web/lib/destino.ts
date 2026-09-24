/**
 * A donde se vuelve despues de entrar. **Funcion pura, para poder probarla.**
 *
 * `/entrar` recibe el destino en la URL, y ese parametro lo controla quien
 * escriba el enlace. Si se usara tal cual, un enlace como
 * `/entrar?destino=https://otro-sitio` convertiria la pantalla de entrada en un
 * trampolin: la persona ve el dominio correcto, teclea su correo y acaba en
 * otra parte. Es una redireccion abierta, y en una pantalla de entrada es justo
 * donde mas dano hace.
 *
 * Asi que **solo se aceptan rutas internas**, y ante cualquier duda se vuelve a
 * la raiz. No se intenta «arreglar» un destino raro: se descarta.
 */

/** A donde se va si el destino falta o no es de fiar. */
export const DESTINO_POR_DEFECTO = "/";

/**
 * Casos que hay que rechazar, y por que no basta con «empieza por /»:
 *
 * · `//evil.com` empieza por `/` y el navegador lo lee como protocolo relativo,
 *   es decir, otro dominio.
 * · `/\evil.com` hace lo mismo en varios navegadores, porque normalizan la
 *   barra invertida.
 * · `https://evil.com` no empieza por `/`, pero conviene que caiga por la regla
 *   general y no por descarte.
 * · `/entrar` volveria a la propia pantalla de entrada: bucle.
 */
export function destinoSeguro(valor: string | undefined | null): string {
  if (!valor) return DESTINO_POR_DEFECTO;

  const limpio = valor.trim();
  if (!limpio.startsWith("/")) return DESTINO_POR_DEFECTO;
  if (limpio.startsWith("//") || limpio.startsWith("/\\")) return DESTINO_POR_DEFECTO;
  // Control y espacios: un `\n` permite colar cabeceras en algunos servidores.
  if (/[\s\u0000-\u001f\u007f]/.test(limpio)) return DESTINO_POR_DEFECTO;
  if (limpio === "/entrar" || limpio.startsWith("/entrar?")) return DESTINO_POR_DEFECTO;

  return limpio;
}
