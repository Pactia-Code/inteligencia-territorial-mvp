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

# Separadores que varían entre la fuente y la cita sin cambiar el sentido.
# SECOP intercambia coma y punto y coma con frecuencia en el mismo objeto
# contractual. Solo se eliminan cuando van seguidos de espacio o fin de texto,
# para no tocar los que están dentro de un número: "1,000" conserva su coma.
_SEPARADORES = re.compile(r"[,;:]+(?=\s|$)")
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
    """Minúsculas, sin acentos, sin separadores sueltos, con espacios colapsados.

    Lo que se ignora no cambia el sentido ni delata invención: mayúsculas,
    tildes, comillas tipográficas y el separador elegido entre palabras.
    **Ninguna palabra se descarta**, y su orden se conserva intacto. Una cita
    inventada difiere en palabras, no en puntuación, así que sigue siendo
    detectada.
    """
    if not texto:
        return ""
    t = texto.translate(_EQUIVALENCIAS)
    # NFD separa la letra de su tilde; luego se descartan las marcas.
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = _SEPARADORES.sub("", t)
    return _ESPACIOS.sub(" ", t).strip().lower()


def contiene(fuente: str | None, cita: str | None) -> bool:
    """¿La cita aparece en el texto fuente, tras normalizar ambos?"""
    c = normalizar(cita)
    if not c:
        return False
    return c in normalizar(fuente)
