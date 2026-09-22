/**
 * VISTA 2 — Municipios priorizados. Las consultas del tablero de seguimiento.
 *
 * **Nadie se da de alta a mano** (CA-M9.8): el tablero es *derivado*. Todo
 * municipio que entro al top 3 de un informe publicado aparece con estado
 * `priorizado`, y `seguimiento` solo guarda los **cambios** sobre ese estado
 * inicial. Asi no hay que escribir filas al publicar ni hay riesgo de
 * duplicarlas, y «no requiere alta manual» es una propiedad de la consulta y no
 * algo que alguien tenga que acordarse de disparar.
 *
 * **El estado vigente es la fila mas reciente** (CA-M9.10). La tabla es de
 * historial: cada cambio inserta, nunca sobrescribe, asi que la trayectoria
 * completa del municipio se reconstruye entera.
 */
import { sql } from "./db";
import type { Informe } from "./tipos";

export const ESTADO_INICIAL = "priorizado";

/**
 * Los dos estados que **exigen nota** al pasar a ellos (CA-M9.9).
 *
 * Vive aqui y no en `acciones.ts` por una razon del framework: un modulo
 * `"use server"` solo puede exportar funciones asincronas, asi que una
 * constante alli rompe la compilacion entera — y lo hace en tiempo de
 * ejecucion, no en `tsc`.
 *
 * Son los que cierran o comprometen: descartar apaga un municipio que el
 * sistema priorizo, y estructurar mueve recursos. Sin el porque, el historial
 * guarda que paso y no por que.
 */
export const EXIGEN_NOTA: readonly string[] = ["descartado", "en_estructuracion"];

export interface CambioDeEstado {
  id: number;
  estado: string;
  nota: string | null;
  fecha_cambio: string;
  /** Persona, no gerencia: ver la asimetria en `sesion.ts`. */
  usuario: string | null;
  gerencia: string | null;
}

export interface FilaTablero {
  divipola: string;
  nombre: string;
  departamento: string;
  /** Los ciclos en que entro al top 3. Señal persistente o puntual (CA-M9.11). */
  ciclos: number[];
  /** Posicion en cada uno de esos ciclos, para el mismo fin. */
  puestos: Record<number, number>;
  /** El del informe mas reciente en que aparecio. No comparable entre ciclos. */
  score: number;
  ciclo_del_score: number;
  estado: string;
  fecha_cambio: string | null;
  nota: string | null;
  usuario: string | null;
}

/** Los `contenido` de todos los informes publicados, del mas nuevo al mas viejo. */
async function informesPublicados(): Promise<Informe[]> {
  const filas = await sql`
    SELECT contenido
      FROM informe
     WHERE estado = 'publicado'
     ORDER BY id_ciclo DESC
  `;
  return filas.map((f) => f.contenido as Informe);
}

/**
 * El historial completo de un municipio, del cambio mas reciente al mas viejo.
 *
 * Lee `usuario` para poner nombre a quien cambio el estado. **La app nunca
 * escribe esa tabla** (M9-acceso).
 */
export async function historialDe(divipola: string): Promise<CambioDeEstado[]> {
  const filas = await sql`
    SELECT s.id, s.estado, s.nota, s.fecha_cambio, u.nombre AS usuario,
           u.id_gerencia AS gerencia
      FROM seguimiento s
      LEFT JOIN usuario u ON u.id = s.id_usuario
     WHERE s.divipola = ${divipola}
     ORDER BY s.fecha_cambio DESC, s.id DESC
  `;
  return filas as CambioDeEstado[];
}

/** El ultimo cambio de cada municipio. Es el estado vigente (CA-M9.10). */
async function ultimosCambios(): Promise<Map<string, CambioDeEstado>> {
  const filas = await sql`
    SELECT DISTINCT ON (s.divipola)
           s.divipola, s.id, s.estado, s.nota, s.fecha_cambio,
           u.nombre AS usuario, u.id_gerencia AS gerencia
      FROM seguimiento s
      LEFT JOIN usuario u ON u.id = s.id_usuario
     ORDER BY s.divipola, s.fecha_cambio DESC, s.id DESC
  `;
  const mapa = new Map<string, CambioDeEstado>();
  for (const f of filas as (CambioDeEstado & { divipola: string })[]) {
    mapa.set(f.divipola, f);
  }
  return mapa;
}

/**
 * El tablero entero.
 *
 * Se compone en TypeScript a partir del `contenido` de los informes en vez de
 * consultar dentro del JSON: los informes publicados son pocos —uno por ciclo—
 * y asi no hace falta ningun operador JSONB, que es lo que la regla 3 de D8
 * evita para que la capa de datos no se bifurque.
 */
export async function tablero(): Promise<FilaTablero[]> {
  const [informes, cambios] = await Promise.all([
    informesPublicados(),
    ultimosCambios(),
  ]);

  const filas = new Map<string, FilaTablero>();
  for (const informe of informes) {
    // CA-M9.8: los que entraron al top 3. Los demas del top 10 se muestran en
    // el informe pero no se siguen: el tablero es de lo priorizado.
    const top = informe.municipios.filter(
      (m) => m.puesto <= informe.calificacion.pedida_hasta_puesto,
    );
    for (const m of top) {
      const ya = filas.get(m.divipola);
      if (ya) {
        ya.ciclos.push(informe.ciclo);
        ya.puestos[informe.ciclo] = m.puesto;
        continue;
      }
      const cambio = cambios.get(m.divipola);
      filas.set(m.divipola, {
        divipola: m.divipola,
        nombre: m.nombre,
        departamento: m.departamento,
        ciclos: [informe.ciclo],
        puestos: { [informe.ciclo]: m.puesto },
        // Del informe mas reciente, porque los informes vienen ordenados.
        score: m.score,
        ciclo_del_score: informe.ciclo,
        estado: cambio?.estado ?? ESTADO_INICIAL,
        fecha_cambio: cambio?.fecha_cambio ?? null,
        nota: cambio?.nota ?? null,
        usuario: cambio?.usuario ?? null,
      });
    }
  }

  for (const f of filas.values()) f.ciclos.sort((a, b) => a - b);
  return [...filas.values()];
}
