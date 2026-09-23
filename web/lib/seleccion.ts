/**
 * Cómo se describe en pantalla qué insights se piden calificar. F1.5, H-015.
 *
 * **La pantalla describía un criterio que ya no se aplica.** Decía «los 2 de
 * mayor peso y 3 al azar», que además nunca existió del todo: venía de pedir
 * «las 2 de mayor peso en el score», y los insights **no entran en el score**
 * —se calcula desde `senal_cruda`, por eso es inmune a A6—. El criterio vigente
 * es por tipo (`M9-sel`): se priorizan los correlacionados y se completa con
 * contratación y prensa.
 *
 * **Se lee del payload, no se escribe a mano.** `composicion_pedida` registra
 * qué salió en cada municipio, y es lo que hay que enseñar: con la regla de
 * relleno, un municipio con pocos correlacionados recibe otra mezcla, y un
 * texto fijo mentiría precisamente ahí. Tampoco se repite aquí la cuota
 * nominal: vive en `informes/seleccion.py` y duplicarla sería una segunda
 * fuente de verdad que envejece en silencio.
 */

/** Cómo se nombra cada cuota en castellano, en singular y plural. */
const NOMBRES: Record<string, [string, string]> = {
  correlacionado: ["correlacionado", "correlacionados"],
  contratacion: ["de contratación", "de contratación"],
  prensa: ["de prensa", "de prensa"],
  // La cuota de relleno: lo que entró porque un tipo no alcanzaba. Se nombra
  // «para completar» y no «de relleno» porque lo segundo suena a descarte, y no
  // lo es — son insights del municipio como los demás.
  relleno: ["para completar", "para completar"],
  otro: ["de otra fuente", "de otras fuentes"],
};

/** Orden fijo: dos municipios no describen lo mismo en distinto orden. */
const ORDEN = ["correlacionado", "contratacion", "prensa", "relleno", "otro"];

/**
 * «3 correlacionados, 1 de contratación y 1 de prensa».
 *
 * Devuelve cadena vacía si no hay composición registrada —un informe anterior a
 * que el payload la trajera—, para que la pantalla pueda callar en vez de
 * inventarse una.
 */
export function describirComposicion(composicion: Record<string, number>): string {
  const partes = ORDEN.filter((clave) => (composicion?.[clave] ?? 0) > 0).map((clave) => {
    const n = composicion[clave];
    const [uno, varios] = NOMBRES[clave] ?? [clave, clave];
    return `${n} ${n === 1 ? uno : varios}`;
  });

  // Las claves que no conoce este mapa se muestran igual: preferible un nombre
  // feo a una cuenta que no cuadra con los insights que se ven debajo.
  for (const clave of Object.keys(composicion ?? {})) {
    if (!ORDEN.includes(clave) && composicion[clave] > 0) {
      partes.push(`${composicion[clave]} ${clave}`);
    }
  }

  if (partes.length === 0) return "";
  if (partes.length === 1) return partes[0];
  return partes.slice(0, -1).join(", ") + " y " + partes[partes.length - 1];
}
