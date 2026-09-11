"""Normalización de texto para comparar citas contra la fuente.

El validador tiene que decidir si una cita textual aparece de verdad en la
señal de origen. Esa comparación no puede ser byte a byte: el LLM reescribe
espacios, cambia mayúsculas y a veces pierde acentos. Pero tampoco puede ser
laxa, o dejaría pasar citas inventadas.

El equilibrio: se ignoran mayúsculas, acentos y espacios redundantes. No se
ignora ninguna palabra.
"""

from __future__ import annotations

import re
import unicodedata

_ESPACIOS = re.compile(r"\s+")
# Comillas y guiones que varían entre la fuente y lo que devuelve el modelo.
_EQUIVALENCIAS = str.maketrans(
    {
        "‘": "'", "’": "'", "‚": "'", "‛": "'",
        "“": '"', "”": '"', "„": '"', "«": '"', "»": '"',
        "‐": "-", "‑": "-", "‒": "-", "–": "-",
        "—": "-", "―": "-", "−": "-",
        " ": " ",
    }
)


def normalizar(texto: str | None) -> str:
    """Minúsculas, sin acentos, con espacios colapsados."""
    if not texto:
        return ""
    t = texto.translate(_EQUIVALENCIAS)
    # NFD separa la letra de su tilde; luego se descartan las marcas.
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return _ESPACIOS.sub(" ", t).strip().lower()


def contiene(fuente: str | None, cita: str | None) -> bool:
    """¿La cita aparece en el texto fuente, tras normalizar ambos?"""
    c = normalizar(cita)
    if not c:
        return False
    return c in normalizar(fuente)
