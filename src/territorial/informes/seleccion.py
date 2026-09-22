"""Qué insights se pide calificar. Código determinista, nunca un modelo.

Es lo que hace medible H1, así que las garantías importan más que el criterio:

· **Lo elige código, no un LLM.** Si un modelo decidiera qué se califica, la
  muestra dependería de algo que ni siquiera es reproducible (A6, A11).
· **La aleatoriedad va con semilla derivada del ciclo**, elegida al publicar y
  **congelada en el payload**. Si cada gerencia recibiera insights distintos,
  CA-M6.6 se rompe —«formato idéntico para las 7, sin personalización»— y las
  calificaciones dejan de ser comparables entre sí.
· **Los cinco son siempre del municipio que se está viendo.** No tiene sentido
  entrar a Funza y que pida calificar insights de otro sitio.


Por qué 2 fijas y 3 aleatorias, y no 5 de un tipo
--------------------------------------------------
Las dos de más peso miden **lo que el sistema priorizó**; las tres aleatorias,
**lo que produce en general**. La mezcla da un diagnóstico que ninguna de las
dos da sola: si las gerencias califican alto las fijas y bajo las aleatorias,
**el scoring acierta y el pipeline produce ruido**. Con solo las de más peso
ese caso se vería como un éxito.


Qué significa «de mayor peso», y por qué es una interpretación
---------------------------------------------------------------
**Los insights no tienen peso en el score.** El score se calcula desde
`senal_cruda` —por eso es inmune a A6— y los insights no entran en él. No hay
un «peso del insight» que leer.

El proxy es **cuántas señales respalda cada insight**: es lo más cercano a
«cuánto de la señal del municipio explica este insight», es determinista y se
explica en una frase. Los consolidados del Correlacionador agrupan varias
señales, así que tienden a quedar arriba — que es coherente con «lo que el
sistema priorizó».

**Es una interpretación, no una lectura del dato.** Si Analítica prefiere otra
—los correlacionados primero, o los de la categoría del factor que más aporta—
se cambia aquí y solo aquí.
"""

from __future__ import annotations

import random

# Las que se piden por municipio, y cuántas de ellas son fijas.
PEDIDAS = 5
FIJAS = 2

FUENTE_PRENSA = "RSS"


def es_de_prensa(insight: dict) -> bool:
    """¿Alguna de sus evidencias viene de prensa?"""
    return any(
        (e.get("fuente") or "") == FUENTE_PRENSA for e in (insight.get("evidencia") or [])
    )


def _peso(insight: dict) -> tuple[int, int]:
    """Orden determinista: más señales primero, y el id desempata.

    Sin el desempate por id, dos insights con las mismas señales podrían salir
    en orden distinto entre procesos y la muestra dejaría de ser reproducible.
    """
    return (-len(insight.get("ids_senal") or []), insight["id"])


def pedir_calificacion(
    insights: list[dict],
    semilla: int,
    divipola: str,
    pedidas: int = PEDIDAS,
    fijas: int = FIJAS,
) -> list[int]:
    """Los ids de los insights que se pide calificar en ese municipio.

    La semilla se combina con el DIVIPOLA para que dos municipios del mismo
    ciclo no saquen la misma posición de la lista, sin dejar de ser
    reproducible: misma semilla y mismo municipio, misma muestra siempre.
    """
    if len(insights) <= pedidas:
        return sorted(i["id"] for i in insights)

    ordenados = sorted(insights, key=_peso)
    elegidos = ordenados[:fijas]
    resto = ordenados[fijas:]

    rnd = random.Random(f"{semilla}|{divipola}")
    elegidos += rnd.sample(resto, pedidas - fijas)

    # **Al menos una de prensa, si el municipio tiene.** Sin esto, un municipio
    # con 47 insights de contratación y 2 de prensa casi nunca mostraría prensa,
    # y H1 no diría nada sobre la fuente que mejor convierte (46% frente al 40%
    # de SECOP). Se sustituye la última aleatoria, no una fija.
    if not any(es_de_prensa(i) for i in elegidos):
        ya = {i["id"] for i in elegidos}
        prensa = next(
            (i for i in ordenados if es_de_prensa(i) and i["id"] not in ya), None
        )
        if prensa is not None:
            elegidos[-1] = prensa

    return sorted(i["id"] for i in elegidos)
