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
import { gerenciaDelCorreo } from "./consultas";
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
