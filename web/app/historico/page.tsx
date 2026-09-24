/**
 * VISTA 3 — Historico de informes publicados (CA-M9.7). **Sin construir.**
 *
 * Es la subfase F4.3 del plan (H-014, 1 d) y vive en el bloque P3: las
 * capacidades del PRD que el MVP no llego a construir. Hasta entonces esto
 * evita el 404, que durante la ronda se lee como una averia.
 */
import { Proximamente } from "../Proximamente";

export default function Historico() {
  return (
    <Proximamente
      titulo="Histórico"
      que="Aquí se podrán consultar los informes de ciclos anteriores, con el
           que se publicó en cada uno y las calificaciones que recibió."
    />
  );
}
