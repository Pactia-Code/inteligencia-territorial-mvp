"""Prefiltro determinista de señal territorial (pendiente A2).

Separa contratación de obra e infraestructura del ruido administrativo antes
de que el LLM vea nada. Cumple dos funciones:

  1. Reduce el volumen que llega al Clasificador. Foundry no ofrece Batch API
     (Addendum 02, D6), así que cada registro ahorrado se nota en el costo.
  2. Alimenta los factores F1, F2 y F3 del scoring (Addendum 01, D4).

**Este diccionario está sin validar.** Es el pendiente A2: sobre el snapshot
produce entre 13% y 90% de obra según el municipio, y ese rango tan ancho
sugiere que hay que revisarlo antes de confiar en él.
"""

from __future__ import annotations

from territorial.reglas.normalizacion import normalizar

# Términos que marcan intervención física sobre el territorio.
# Se comparan sobre texto ya normalizado, así que van sin acentos.
TERMINOS_OBRA: tuple[str, ...] = (
    "obra",
    "infraestructura",
    "construccion",
    "via",
    "vial",
    "paviment",
    "acueducto",
    "alcantarillado",
    "urbaniz",
    "parque",
    "puente",
    "edific",
    "adecuacion",
    "mejoramiento",
    "ampliacion",
    "ordenamiento",
    "vivienda",
    "lote",
    "predio",
)

# Términos que marcan contratación administrativa sin huella territorial.
# Si aparecen y no hay término de obra, el registro se descarta antes.
TERMINOS_RUIDO: tuple[str, ...] = (
    "prestacion de servicios profesionales",
    "apoyo a la gestion",
    "servicios de apoyo",
)


def es_obra(texto: str | None) -> bool:
    """¿El objeto contractual describe intervención física sobre el territorio?"""
    t = normalizar(texto)
    if not t:
        return False
    return any(term in t for term in TERMINOS_OBRA)


def es_ruido_administrativo(texto: str | None) -> bool:
    """¿El objeto es contratación administrativa sin huella territorial?"""
    t = normalizar(texto)
    if not t:
        return False
    return any(term in t for term in TERMINOS_RUIDO)


def terminos_encontrados(texto: str | None) -> list[str]:
    """Qué términos dispararon la marca. Alimenta la traza de CA-M2.5."""
    t = normalizar(texto)
    if not t:
        return []
    return [term for term in TERMINOS_OBRA if term in t]


def clasificar(texto: str | None) -> tuple[bool, str]:
    """Decide si el registro pasa al Clasificador, y por qué.

    Devuelve (pasa, motivo). El motivo se registra en la traza: CA-M2.5 exige
    saber qué se descartó y por qué.
    """
    if not normalizar(texto):
        return False, "objeto vacio"

    encontrados = terminos_encontrados(texto)
    if encontrados:
        return True, f"obra: {', '.join(encontrados)}"

    if es_ruido_administrativo(texto):
        return False, "ruido administrativo"

    return False, "sin termino territorial"
