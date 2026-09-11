"""Normalización de códigos DIVIPOLA (Addendum 02, D7).

El snapshot trae los códigos sin ceros a la izquierda: Antioquia llega como
depto=5 y Atlántico como depto=8, cuando el estándar DANE es 05 y 08. El código
canónico son 5 caracteres: 2 de departamento + 3 de municipio.

Sin esta normalización, cualquier unión futura con TerriData o con fuentes
oficiales falla en silencio.
"""

from __future__ import annotations

import re

PATRON_CANONICO = re.compile(r"^\d{5}$")


class DivipolaInvalido(ValueError):
    """El valor recibido no puede normalizarse a un DIVIPOLA de 5 dígitos."""


def normalizar(depto: int | str, muni: int | str) -> str:
    """Combina departamento y municipio en un DIVIPOLA canónico de 5 dígitos.

    >>> normalizar(25, 286)
    '25286'
    >>> normalizar(5, 45)
    '05045'
    >>> normalizar("8", "1")
    '08001'
    """
    try:
        d = int(str(depto).strip())
        m = int(str(muni).strip())
    except (TypeError, ValueError) as exc:
        raise DivipolaInvalido(f"depto={depto!r} muni={muni!r} no son numéricos") from exc

    if not (1 <= d <= 99):
        raise DivipolaInvalido(f"departamento fuera de rango: {d}")
    if not (0 <= m <= 999):
        raise DivipolaInvalido(f"municipio fuera de rango: {m}")

    return f"{d:02d}{m:03d}"


def desde_codigo(codigo: str) -> str:
    """Normaliza un código en formato 'DD-MMM' o ya canónico.

    >>> desde_codigo("5-045")
    '05045'
    >>> desde_codigo("25286")
    '25286'
    """
    valor = str(codigo).strip()
    if PATRON_CANONICO.match(valor):
        return valor
    if "-" not in valor:
        raise DivipolaInvalido(f"formato no reconocido: {codigo!r}")
    depto, _, muni = valor.partition("-")
    return normalizar(depto, muni)


def desde_bloque(cod_divipola: dict) -> str:
    """Normaliza el bloque `cod_divipola` tal como viene en el snapshot.

    Prefiere los campos numéricos `depto`/`muni`; si faltan, cae a `codigo`.
    """
    depto = cod_divipola.get("depto")
    muni = cod_divipola.get("muni")
    if depto is not None and muni is not None:
        return normalizar(depto, muni)

    codigo = cod_divipola.get("codigo")
    if codigo is None:
        raise DivipolaInvalido(f"bloque sin depto/muni ni codigo: {cod_divipola!r}")
    return desde_codigo(codigo)
