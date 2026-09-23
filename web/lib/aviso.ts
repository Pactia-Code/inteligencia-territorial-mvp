/**
 * La marca de que esto es un MVP. F5.3, hallazgo H-019.
 *
 * **Vivía en una sola página** —la vista de ciclo— así que `/priorizados` no la
 * llevaba y **cualquier vista nueva nacía sin ella**. CA-M9.17 dice «toda
 * pantalla», y una marca que depende de que alguien se acuerde de ponerla no es
 * una marca. Ahora la pinta el layout, que envuelve a todas.
 *
 * **El texto es una desviación registrada, no un descuido.** CA-M6.5 y CA-M9.17
 * piden «MVP — contenido no validado por Analítica»; se muestra solo «MVP» por
 * decisión de producto del 2026-09-22 (pendiente `M6-aviso`). La consecuencia
 * está escrita allí y conviene no perderla: «MVP» dice que es una versión
 * temprana, y «no validado por Analítica» decía que **nadie revisó el
 * contenido**, que es lo que el lector necesita para calibrar lo que lee. El
 * texto completo sigue en el payload de cada informe (`informe.aviso`), así que
 * la divergencia entre lo pedido y lo mostrado queda registrada en el dato.
 *
 * **Esta constante repite `AVISO_CORTO` de `informes/composicion.py`**, y es la
 * única duplicación que quedó: el layout no compone informes, así que no tiene
 * payload del que leerla. Si se cambia el texto, hay que cambiarlo en los dos
 * sitios — y el de Python es el que manda, porque es el que queda escrito en
 * cada informe publicado.
 */
export const AVISO_CORTO = "MVP";
