"""Detección de cifras en texto de agente (capa determinista, CA-M6.3).

Sostiene la comprobación de que **ninguna cifra de la salida de un agente puede
faltar en su entrada**. Da igual que el número sea correcto: si el modelo lo
escribió y no estaba en lo que recibió, se lo inventó, y una cifra real
inventada es más difícil de detectar que una falsa.

Está aquí y no en el script que la usa porque una comprobación en la que se
confía tiene que estar probada. La primera versión vivía en el script y tenía
un falso positivo que solo se vio corriéndola: capturaba `80.` —con el punto
final de la frase— en la salida y no capturaba `80 ` en la entrada, así que
«calles 76 y 80» se denunciaba como cifra inventada. **Las dos orillas tienen
que medirse con la misma vara**, o la comprobación acusa en falso y deja de
creerse.

**Límite conocido:** solo se miran números de **tres dígitos o más**. Un «2» o
un «15» aparecen en cualquier prosa —«dos frentes», «el 15% del área»— y
perseguirlos daría solo falsos positivos. La consecuencia es que un porcentaje
de dos dígitos escrito sin decimales podría colarse; por eso
`variantes_de_cifra` genera también la forma con un decimal, que sí tiene tres.
"""

from __future__ import annotations

import re

# Un número es una tira de dígitos que **empieza y acaba en dígito**, con
# puntos o comas dentro. Acabar en dígito es lo que impide tragarse el punto
# final de una frase, que era el falso positivo.
NUMERO = re.compile(r"\d[\d.,]*\d|\d")

# Por debajo de esto no se mira: ver el límite conocido del encabezado.
MINIMO_DIGITOS = 3


def normalizar(bruto: str) -> str:
    """Quita separadores de miles y decimales para poder comparar."""
    return bruto.replace(".", "").replace(",", "")


def cifras(texto: str) -> set[str]:
    """Los números de un texto, normalizados y sin los demasiado cortos."""
    salida: set[str] = set()
    for bruto in NUMERO.findall(texto or ""):
        limpio = normalizar(bruto)
        if len(limpio) >= MINIMO_DIGITOS:
            salida.add(limpio)
    return salida


def variantes_de_cifra(valor: float | int | None) -> set[str]:
    """Las formas en que un mismo dato puede aparecer escrito.

    Un déficit de 20,9 puede salir como «20,9», «20.9» o «21». Se generan las
    tres normalizadas para que la comprobación no dependa de cómo redondee el
    modelo.
    """
    if valor is None:
        return set()
    formas = {
        f"{valor:.0f}",
        f"{valor:.1f}",
        f"{valor:.2f}",
        str(valor),
    }
    return {normalizar(f) for f in formas if len(normalizar(f)) >= MINIMO_DIGITOS}


def inventadas(salida: str, entrada: str) -> set[str]:
    """Cifras que el agente escribió y no estaban en lo que recibió."""
    return cifras(salida) - cifras(entrada)
