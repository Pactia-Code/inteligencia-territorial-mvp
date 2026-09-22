"""Qué insights se pide calificar. Código determinista, nunca un modelo.

Es lo que hace medible H1, así que las garantías importan más que el criterio:

· **Lo elige código, no un LLM.** Si un modelo decidiera qué se califica, la
  muestra dependería de algo que ni siquiera es reproducible (A6, A11).
· **La aleatoriedad va con semilla derivada del ciclo**, elegida al publicar y
  **congelada en el payload**. Si cada gerencia recibiera insights distintos,
  CA-M6.6 se rompe —«formato idéntico para las 7, sin personalización»— y las
  calificaciones dejan de ser comparables entre sí.
· **Los cinco son siempre del municipio que se está viendo.**


La cuota: 3 correlacionados, 1 de contratación, 1 de prensa
------------------------------------------------------------
Se selecciona **por tipo y explícitamente**, decisión de Analítica del
2026-09-22. Los correlacionados son la prioridad porque son **lo que ninguna
fuente sola produce**: los 15 insights que cruzan RSS con SECOP fueron la
primera evidencia de que la correlación multiagente aporta algo.

*Antes se ordenaba por número de señales de respaldo. Aquel criterio nació de
pedir «las 2 de mayor peso en el score», que **no existe** —el score se calcula
desde `senal_cruda` y los insights no entran en él, por eso es inmune a A6—. El
proxy funcionaba, pero acababa seleccionando correlacionados sin decirlo. Ahora
se dice.*


La regla de relleno, y por qué hace falta
------------------------------------------
En el ciclo 3 hay **38 correlacionados sobre 364 insights repartidos en 18
municipios**: muchos no llegarán a 3 y algunos no tendrán ninguno. Sin relleno,
la muestra encogería justo en los municipios con menos convergencia, que son los
que más interesa mirar.

  1. Los correlacionados que haya, hasta 3.
  2. Después 1 de contratación y 1 de prensa.
  3. Si una categoría no existe en ese municipio, se completa con lo que haya.

**Siempre 5**, mientras el municipio tenga 5.


Y el payload registra qué composición salió
--------------------------------------------
`3+1+1`, `1+2+2` o la que toque, y el tipo de cada insight pedido. Al analizar
H1 hará falta saber si las calificaciones bajas venían de correlacionados o de
directos, y sin esto habría que reconstruirlo a mano.
"""

from __future__ import annotations

import random

PEDIDAS = 5

# Cuántos de cada tipo, en orden de prioridad. Lo que falte se rellena.
CUOTA: tuple[tuple[str, int], ...] = (
    ("correlacionado", 3),
    ("contratacion", 1),
    ("prensa", 1),
)

FUENTE_PRENSA = "RSS"
FUENTE_CONTRATACION = "SECOP II"
ORIGEN_CORRELACIONADOR = "correlacionador"


def _fuentes(insight: dict) -> set[str]:
    return {(e.get("fuente") or "") for e in (insight.get("evidencia") or [])}


def tipo_de(insight: dict) -> str:
    """A qué cuota pertenece. Un insight cae en **una sola**.

    El orden importa: un correlacionado cruza fuentes por definición, así que si
    se mirara la fuente primero contaría dos veces. Y la prensa va antes que la
    contratación porque es la minoritaria —336 señales frente a 19.640—: si
    empatara con SECOP, no saldría nunca.
    """
    if insight.get("origen") == ORIGEN_CORRELACIONADOR:
        return "correlacionado"
    fuentes = _fuentes(insight)
    if FUENTE_PRENSA in fuentes:
        return "prensa"
    if FUENTE_CONTRATACION in fuentes:
        return "contratacion"
    return "otro"


def pedir_calificacion(
    insights: list[dict],
    semilla: int,
    divipola: str,
    pedidas: int = PEDIDAS,
) -> tuple[list[int], dict[int, str], dict[str, int]]:
    """Devuelve (ids pedidos, tipo de cada uno, composición que salió).

    La semilla se combina con el DIVIPOLA para que dos municipios del mismo
    ciclo no saquen la misma posición de la lista, sin dejar de ser
    reproducible: misma semilla y mismo municipio, misma muestra siempre.
    """
    if not insights:
        return [], {}, {}

    rnd = random.Random(f"{semilla}|{divipola}")
    # Orden estable de partida: sin esto, el orden de lectura de la base
    # cambiaría la muestra y dejaría de ser reproducible entre procesos.
    por_tipo: dict[str, list[dict]] = {}
    for i in sorted(insights, key=lambda x: x["id"]):
        por_tipo.setdefault(tipo_de(i), []).append(i)
    for lista in por_tipo.values():
        rnd.shuffle(lista)

    elegidos: list[dict] = []
    tipos: dict[int, str] = {}

    def tomar(candidatos: list[dict], cuantos: int, etiqueta: str) -> None:
        # Se comprueba contra `tipos`, que crece: mirar una copia tomada al
        # entrar dejaría repetir dentro de la misma llamada.
        for i in candidatos:
            if cuantos <= 0 or len(elegidos) >= pedidas:
                return
            if i["id"] in tipos:
                continue
            elegidos.append(i)
            tipos[i["id"]] = etiqueta
            cuantos -= 1

    for etiqueta, cuantos in CUOTA:
        tomar(por_tipo.get(etiqueta, []), cuantos, etiqueta)

    # Relleno: lo que haya, en el mismo orden de prioridad de la cuota para que
    # sea determinista, y marcado como relleno para poder distinguirlo en H1.
    if len(elegidos) < pedidas:
        resto = [
            i
            for etiqueta, _ in CUOTA
            for i in por_tipo.get(etiqueta, [])
        ] + por_tipo.get("otro", [])
        tomar(resto, pedidas - len(elegidos), "relleno")

    composicion: dict[str, int] = {}
    for etiqueta in tipos.values():
        composicion[etiqueta] = composicion.get(etiqueta, 0) + 1

    return sorted(tipos), tipos, composicion
