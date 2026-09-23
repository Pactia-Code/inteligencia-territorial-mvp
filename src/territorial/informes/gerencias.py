"""El catálogo de gerencias que califican: cuáles son núcleo y cuáles añadidas.

F0.1b de la remediación, que amplía H-005. F0.1 congeló **quién** podía
calificar cuando se publicó cada informe; esto añade **de qué clase es cada
uno**, porque el conjunto de calificadores **no es el del PRD**.

**El núcleo son 5, no 7** (decisión del dueño del 2026-09-22, tercera tanda):
`general`, `juridica`, `rotacion_portafolio`, `producto_logistica` y
`producto_hoteles_oficinas`. Financiera no participa, y Oficinas y Hotelería son
una sola gerencia. `administrativa` y `analitica` califican como **adicionales**.
Es una **desviación del PRD**, que habla de 7 (§1, CA-M9.1), y está registrada en
`docs/decisiones-remediacion.md`.

**Por qué hace falta la marca y no basta con la lista.** H2 se reporta sobre las
`prd` y las adicionales **aparte**; H1, con y sin ellas. Sin la marca congelada
junto a la lista, esas cifras no se pueden separar después: habría que
reconstruir meses más tarde quién era quién, que es el problema que F0.1 vino a
resolver. Y hay un motivo concreto para poder separarlas: **el operador del
pipeline también califica**, así que sus calificaciones tienen conflicto de
interés en H1 y deben poder aislarse.

Por qué un archivo de configuración y no una columna en `usuario`
-----------------------------------------------------------------
· **Ser del núcleo es una propiedad del diseño del experimento, no de una
  persona.** Dos usuarios de la misma gerencia no pueden discrepar sobre la
  marca, y una columna por usuario permite justamente eso. El archivo lo hace
  imposible por construcción.
· **No necesita migración** ni regenerar el contrato de TypeScript.
· Es el mismo patrón que `config/pesos.json` (CA-M5.3): una palanca editable sin
  tocar código, versionada y revisable.
· El dueño indicó que **no contiene datos sensibles**, así que se versiona en
  git — al contrario que la evidencia del pipeline, que no viaja.

**Una gerencia que no esté declarada aquí sale `adicional`.** No es un descarte
silencioso: `scripts/cargar_usuarios.py` se niega a cargar un usuario cuya
`id_gerencia` no esté en este archivo, así que la única forma de que aparezca
una sin declarar es editando la base a mano. Ante eso, lo prudente es no
contarla como núcleo.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

from territorial.config import Config, obtener_config

TIPO_PRD = "prd"
TIPO_ADICIONAL = "adicional"
TIPOS = (TIPO_PRD, TIPO_ADICIONAL)


@dataclass(frozen=True)
class Gerencia:
    """Una gerencia del catálogo, con su nombre para mostrar y su clase."""

    id_gerencia: str
    nombre: str
    tipo: str


class GerenciasInvalidas(ValueError):
    """El archivo de gerencias no cumple el contrato. Mejor fallar que marcar mal."""


def _exigir(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise GerenciasInvalidas(mensaje)


def cargar(config: Config | None = None) -> dict[str, Gerencia]:
    """El catálogo de `config/gerencias.json`, indexado por `id_gerencia`.

    Formato:

        {"gerencias": [{"id_gerencia": "general", "nombre": "...", "tipo": "prd"}]}

    Las claves que empiezan por `_` se ignoran, que es como se dejan notas en un
    JSON sin comentarios. Si el archivo no existe, el catálogo está vacío.
    """
    cfg = config or obtener_config()
    ruta = cfg.ruta_absoluta(cfg.ruta_gerencias)
    if not ruta.exists():
        return {}

    try:
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise GerenciasInvalidas(f"{ruta} no es JSON válido: {e}") from e

    _exigir(
        isinstance(contenido, dict),
        f'{ruta}: se esperaba un objeto {{"gerencias": [...]}}',
    )
    desconocidas = sorted(
        k for k in contenido if k != "gerencias" and not k.startswith("_")
    )
    _exigir(
        not desconocidas,
        f"{ruta}: claves desconocidas {desconocidas}. Solo «gerencias» (y notas «_…»)",
    )

    crudas = contenido.get("gerencias", [])
    _exigir(isinstance(crudas, list), f'{ruta}: «gerencias» debe ser una lista')

    catalogo: dict[str, Gerencia] = {}
    for n, fila in enumerate(crudas, start=1):
        donde = f"{ruta}, gerencia {n}"
        _exigir(isinstance(fila, dict), f"{donde}: se esperaba un objeto")
        sobran = sorted(set(fila) - {"id_gerencia", "nombre", "tipo"})
        _exigir(not sobran, f"{donde}: campos desconocidos {sobran}")

        id_gerencia = str(fila.get("id_gerencia", "")).strip()
        nombre = str(fila.get("nombre", "")).strip()
        tipo = str(fila.get("tipo", "")).strip()
        _exigir(bool(id_gerencia), f"{donde}: falta «id_gerencia»")
        _exigir(bool(nombre), f"{donde} ({id_gerencia}): falta «nombre»")
        _exigir(
            tipo in TIPOS,
            f"{donde} ({id_gerencia}): «tipo» es «{tipo}» y debe ser {list(TIPOS)}",
        )
        _exigir(
            id_gerencia not in catalogo,
            f"{ruta}: id_gerencia repetida «{id_gerencia}»",
        )
        catalogo[id_gerencia] = Gerencia(id_gerencia, nombre, tipo)

    return catalogo


def clasificar(id_gerencia: str, catalogo: Mapping[str, Gerencia]) -> str:
    """`prd` o `adicional`. Lo que no está declarado no es núcleo.

    Solo dos valores, porque el reporte solo distingue dos cosas: H2 sobre las
    `prd` y las adicionales aparte.
    """
    gerencia = catalogo.get(id_gerencia)
    return gerencia.tipo if gerencia is not None else TIPO_ADICIONAL
