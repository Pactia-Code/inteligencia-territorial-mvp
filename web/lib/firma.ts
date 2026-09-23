/**
 * Firma de la cookie de identificacion. F0.3, residual de H-012.
 *
 * **Esto no es autenticacion y no la sustituye.** El dueno decidio el
 * 2026-09-22 **no adoptar el token** (riesgo R-A2 aceptado): la identidad sigue
 * siendo un correo tecleado, asi que quien conozca un correo autorizado puede
 * calificar por esa gerencia. H-012 queda **abierto**.
 *
 * Lo que la firma si cierra es el escalon mas barato del ataque: **editar la
 * cookie a mano**. Antes bastaba con poner `correo=quien.sea@pactia.com` en el
 * navegador; ahora el valor tiene que venir acompanado de un HMAC que solo
 * puede calcular el servidor. Sin firma valida, no hay identidad.
 *
 * `COOKIE_SECRET` vive en `.env` (y en las variables del proyecto de Vercel).
 * **Si falta, no se emite ni se acepta ninguna identidad**: fallar cerrado es
 * lo correcto aqui — un despliegue sin secreto no debe degradarse a «cualquiera
 * es quien dice ser», que es justo lo que veniamos a quitar.
 */
import { createHmac, timingSafeEqual } from "node:crypto";

/** Separa el valor de su firma. No puede aparecer en un correo. */
const SEPARADOR = "|";

export class SinSecreto extends Error {
  constructor() {
    super(
      "falta COOKIE_SECRET: sin secreto no se puede firmar la identificacion. " +
        "Anadela al .env local o a las variables del proyecto.",
    );
  }
}

function secreto(): string | null {
  const valor = process.env.COOKIE_SECRET;
  return valor && valor.trim() ? valor : null;
}

export function haySecreto(): boolean {
  return secreto() !== null;
}

function hmac(valor: string, clave: string): string {
  return createHmac("sha256", clave).update(valor).digest("base64url");
}

/** `valor|firma`. Lanza si no hay secreto: no se emite identidad a ciegas. */
export function firmar(valor: string): string {
  const clave = secreto();
  if (clave === null) throw new SinSecreto();
  return `${valor}${SEPARADOR}${hmac(valor, clave)}`;
}

/**
 * El valor si la firma cuadra, `null` si no.
 *
 * Devuelve `null` —y no lanza— ante cualquier cosa rara: sin secreto, sin
 * separador, firma de otra longitud o firma que no cuadra. Una cookie invalida
 * es un visitante sin identidad, no un error de la pagina; leer el informe
 * sigue siendo abierto.
 */
export function verificar(cookie: string | undefined): string | null {
  const clave = secreto();
  if (clave === null || !cookie) return null;

  const corte = cookie.lastIndexOf(SEPARADOR);
  if (corte <= 0) return null;

  const valor = cookie.slice(0, corte);
  const firma = cookie.slice(corte + 1);
  const esperada = hmac(valor, clave);
  // Longitudes distintas rompen `timingSafeEqual`, asi que se comprueba antes.
  if (firma.length !== esperada.length) return null;
  if (!timingSafeEqual(Buffer.from(firma), Buffer.from(esperada))) return null;
  return valor;
}
