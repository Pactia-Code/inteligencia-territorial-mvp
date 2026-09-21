"""Nomenclátor DIVIPOLA: del CSV a `entidad_divipola` (capa determinista).

**Tabla maestra, no ampliación del alcance.** El MVP sigue procesando 18
municipios; esto es la referencia contra la que resolver códigos y nombres
cuando haga falta. Ver el encabezado de `EntidadDivipola`.

**De 1.102 filas salen 1.135.** El CSV de origen solo trae municipios: los 32
departamentos se derivan agrupando por `codigo_departamento` y la fila nacional
se sintetiza. Los códigos siguen la convención de TerriData —nacional `01001`,
departamento `dd000`, municipio `ddmmm`—, y no es una elección arbitraria: el
primer indicador de TerriData tiene exactamente estas 1.135 entidades y las
mismas 1.102 municipales, así que un `join` futuro no necesita traducir nada.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from territorial.almacen.modelos import EntidadDivipola

CODIGO_NACIONAL = "01001"
NOMBRE_NACIONAL = "Colombia"
DEPTO_NACIONAL = "01"

COLUMNAS = ("codigo_divipola", "codigo_departamento", "departamento", "municipio")

# Bogotá existe como municipio (11001) y **no** como departamento. Derivar los
# departamentos sin esta excepción daría 33, y TerriData trae 32: el conteo
# dejaría de cuadrar con la fuente sin que nadie supiera por qué.
SIN_FILA_DEPARTAMENTAL = frozenset({"11"})

CAMPOS = ("codigo", "nombre", "codigo_departamento", "nombre_departamento", "tipo")


class NomenclatorInvalido(ValueError):
    """El origen no cumple el contrato. Mejor fallar que cargar a medias."""


@dataclass(frozen=True)
class ResultadoCarga:
    """Qué hizo la carga. Una segunda corrida debe dar nuevas=0, actualizadas=0."""

    nuevas: int
    actualizadas: int
    iguales: int
    sobrantes: list[str]

    @property
    def sin_cambios(self) -> bool:
        return self.nuevas == 0 and self.actualizadas == 0


def leer_csv(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        filas = list(csv.DictReader(f))
    if not filas:
        raise NomenclatorInvalido(f"{ruta}: el CSV no tiene filas")
    faltan = set(COLUMNAS) - set(filas[0])
    if faltan:
        raise NomenclatorInvalido(f"{ruta}: faltan columnas {sorted(faltan)}")
    return filas


def construir(filas: list[dict]) -> list[dict]:
    """Municipios del CSV + departamentos derivados + la fila nacional."""
    entidades: list[dict] = [
        {
            "codigo": CODIGO_NACIONAL,
            "nombre": NOMBRE_NACIONAL,
            "codigo_departamento": DEPTO_NACIONAL,
            "nombre_departamento": NOMBRE_NACIONAL,
            "tipo": "nacional",
        }
    ]

    nombres_depto: dict[str, str] = {}
    for f in filas:
        nombres_depto.setdefault(
            f["codigo_departamento"].strip(), f["departamento"].strip()
        )

    for cod in sorted(nombres_depto):
        if cod in SIN_FILA_DEPARTAMENTAL:
            continue
        entidades.append(
            {
                "codigo": f"{cod}000",
                "nombre": nombres_depto[cod],
                "codigo_departamento": cod,
                "nombre_departamento": nombres_depto[cod],
                "tipo": "departamento",
            }
        )

    for f in filas:
        cod_depto = f["codigo_departamento"].strip()
        codigo = f["codigo_divipola"].strip()
        if len(codigo) != 5 or not codigo.isdigit():
            raise NomenclatorInvalido(f"código no canónico en el origen: {codigo!r}")
        entidades.append(
            {
                "codigo": codigo,
                "nombre": f["municipio"].strip(),
                "codigo_departamento": cod_depto,
                "nombre_departamento": nombres_depto[cod_depto],
                "tipo": "municipio",
            }
        )

    cuenta = Counter(e["codigo"] for e in entidades)
    repetidos = sorted(c for c, n in cuenta.items() if n > 1)
    if repetidos:
        raise NomenclatorInvalido(f"códigos repetidos en el origen: {repetidos[:10]}")

    return entidades


def homonimos(entidades: list[dict]) -> dict[str, list[str]]:
    """Nombres de municipio que se repiten entre departamentos.

    Se calcula sobre lo que se va a cargar, en vez de citar la cifra del spike:
    así el 13% queda reverificable y no es un número de memoria.
    """
    por_nombre: dict[str, list[str]] = defaultdict(list)
    for e in entidades:
        if e["tipo"] == "municipio":
            por_nombre[e["nombre"]].append(e["codigo"])
    return {n: sorted(c) for n, c in por_nombre.items() if len(c) > 1}


def cargar(sesion_bd: Session, entidades: list[dict]) -> ResultadoCarga:
    """Inserta lo que falta, actualiza lo que cambió, no toca lo igual.

    Es idempotente de verdad, no «no revienta al repetirla»: la segunda corrida
    reporta cero y cero. Se hace comparando en Python en vez de con un `UPSERT`
    porque la misma sentencia tiene que servir a SQLite y a PostgreSQL (D8), y
    `ON CONFLICT` no se escribe igual en los dos.

    **No borra lo que sobra**, lo devuelve. Si el nomenclátor encoge, que
    alguien mire por qué antes de que un `DELETE` se lo lleve por delante.
    """
    existentes = {e.codigo: e for e in sesion_bd.scalars(select(EntidadDivipola)).all()}
    nuevas = actualizadas = iguales = 0

    for datos in entidades:
        actual = existentes.pop(datos["codigo"], None)
        if actual is None:
            sesion_bd.add(EntidadDivipola(**datos))
            nuevas += 1
            continue
        cambios = {c: datos[c] for c in CAMPOS if getattr(actual, c) != datos[c]}
        if cambios:
            for campo, valor in cambios.items():
                setattr(actual, campo, valor)
            actualizadas += 1
        else:
            iguales += 1

    sesion_bd.flush()
    return ResultadoCarga(nuevas, actualizadas, iguales, sorted(existentes))
