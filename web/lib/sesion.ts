/**
 * Identificacion por correo. **No hay autenticacion.**
 *
 * El correo se guarda en una cookie por conveniencia: pedirlo en cada
 * calificacion rompe los <=2 clics de CA-M7.1. **La atribucion es
 * declarativa** y hay que decirlo al publicar H1 y H2: el dueno decidio no
 * adoptar el token (R-A2), asi que H-012 sigue abierto y quien conozca un
 * correo autorizado puede calificar por esa gerencia.
 *
 * Lo que F0.3 si cierra: **la cookie va firmada** (`lib/firma.ts`), asi que ya
 * no se falsifica editandola en el navegador, y **solo se emite para correos
 * que estan en `usuario` y activos**. Sin firma valida no hay identidad.
 *
 * La calificacion se atribuye a **gerencia** (CA-M7.2) y ademas se registra
 * **quien** la escribio en `calificacion.id_usuario`. No son dos ejes de
 * atribucion: el analisis de H1 y H2 va por gerencia; el autor esta para poder
 * auditar una calificacion discutida.
 */
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { gerenciaDelCorreo } from "./consultas";
import { destinoSeguro } from "./destino";
import { verificar } from "./firma";

export const COOKIE_CORREO = "correo";

export interface Identidad {
  /**
   * El id de fila de `usuario`. Hace falta para `seguimiento.id_usuario`.
   *
   * **Y aqui hay una asimetria deliberada que conviene no «corregir»:**
   * `seguimiento` atribuye a PERSONA y `calificacion` a GERENCIA. No es un
   * descuido. El seguimiento necesita saber quien cambio un estado —es una
   * decision operativa con consecuencias—; la calificacion no debe saberlo,
   * porque CA-M7.2 exige que sea independiente y que nadie vea la de otro.
   * Igualarlas por consistencia romperia una de las dos.
   */
  id: number;
  correo: string;
  id_gerencia: string;
  nombre: string;
  rol: string;
}

/**
 * Quien esta calificando, o `null` si nadie se ha identificado todavia.
 *
 * Dos filtros, y los dos tienen que pasar: la cookie **tiene que estar
 * firmada** por este servidor, y el correo **tiene que seguir en `usuario` y
 * activo**. Lo segundo importa tanto como lo primero: a quien se le retira el
 * acceso deja de tener identidad en su siguiente peticion, sin tocar su
 * navegador.
 */
export async function identidadActual(): Promise<Identidad | null> {
  const correo = verificar((await cookies()).get(COOKIE_CORREO)?.value);
  if (!correo) return null;
  const usuario = await gerenciaDelCorreo(correo);
  return usuario ? { correo, ...usuario } : null;
}

/** Solo el administrador ve el panel de metricas (CA-M9.14). */
export async function esAdministrador(): Promise<boolean> {
  const yo = await identidadActual();
  return yo?.rol === "administrador";
}

/**
 * La identidad, o se va a `/entrar`. **Toda pantalla salvo `/entrar` la llama.**
 *
 * Antes leer era abierto con el enlace y el correo se pedia al ir a calificar.
 * El dueno lo cambio el 2026-09-24: ahora se entra primero. **Mejora privacidad
 * e imagen, no la atribucion** — quien conozca un correo autorizado sigue
 * pudiendo usarlo, R-A2 y H-012 siguen abiertos, y hay que decirlo al publicar
 * H1 y H2. Esto no es autenticacion y no conviene que lo parezca.
 *
 * `destino` es la ruta que se pidio, para volver a ella despues de entrar. Se
 * pasa desde cada pagina porque un componente de servidor no puede leer la ruta
 * actual, y se sanea en `destino.ts`.
 *
 * **Que no se olvide en una pagina nueva** lo comprueba
 * `tests/test_puerta_de_entrada.py`, que recorre `web/app/**\/page.tsx`. Una
 * pantalla que se olvide de llamar aqui quedaria abierta sin que nadie lo note,
 * igual que `/priorizados` estuvo rota sin que ninguna comprobacion lo viera.
 */
export async function exigirIdentidad(destino: string): Promise<Identidad> {
  const yo = await identidadActual();
  if (yo) return yo;
  const a = destinoSeguro(destino);
  redirect(a === "/" ? "/entrar" : `/entrar?destino=${encodeURIComponent(a)}`);
}
