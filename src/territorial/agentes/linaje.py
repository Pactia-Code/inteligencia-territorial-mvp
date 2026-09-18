"""Linaje de prompts (Addendum 02, D7).

`insight.version_prompt` guardaba la etiqueta —"v4"— y nada más. Una etiqueta
no ancla nada: si alguien edita `clasificador_v4.md` sin renombrarlo, todos los
insights anteriores siguen diciendo v4 y **no hay forma de saber que el prompt
cambió entre una pasada y otra**. Con dos pasadas del mismo ciclo eso es fatal
para A6: la diferencia entre ellas podría venir del prompt y no del modelo.

Esto archiva el texto del prompt en el almacén de objetos, lo ancla por hash y
deja a cada insight apuntando a esa fila. Es el equivalente de
`version_scoring` en el scoring: etiqueta más huella.

**Editar un prompt sin cambiar su versión es un error, no un aviso.** El hash lo
detecta y `registrar_prompt` falla. Si se dejara pasar, la fila diría v4 para
dos contenidos distintos y el linaje mentiría en silencio — que es peor que no
tenerlo.
"""

from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from territorial.almacen.blob import Almacen, obtener_almacen
from territorial.almacen.modelos import VersionPrompt
from territorial.config import Config


class PromptDivergente(RuntimeError):
    """El contenido de un prompt cambió sin que cambiara su versión."""


def ruta_blob(agente: str, version: str) -> str:
    return f"prompts/{agente}_{version}.md"


def registrar_prompt(
    sesion_bd: Session,
    agente: str,
    version: str,
    texto: str,
    almacen: Almacen | None = None,
    config: Config | None = None,
) -> VersionPrompt:
    """Archiva el prompt y devuelve su fila de linaje.

    Es idempotente: si ya está registrado con el mismo contenido, devuelve la
    fila existente sin reescribir nada. Si el contenido difiere, falla.
    """
    huella = hashlib.sha256(texto.encode("utf-8")).hexdigest()

    fila = sesion_bd.scalars(
        select(VersionPrompt).where(
            VersionPrompt.agente == agente, VersionPrompt.version == version
        )
    ).one_or_none()

    if fila is not None:
        if fila.hash_sha256 != huella:
            raise PromptDivergente(
                f"El prompt {agente} {version} ya está registrado con otro contenido "
                f"(hash {fila.hash_sha256[:8]}, ahora {huella[:8]}). Editar un prompt "
                f"sin cambiar su versión rompe el linaje: crea {agente}_<nueva>.md "
                "en vez de modificar el existente."
            )
        return fila

    alm = almacen or obtener_almacen(config)
    uri = alm.escribir_texto(ruta_blob(agente, version), texto)

    fila = VersionPrompt(
        agente=agente, version=version, uri_blob=uri, hash_sha256=huella
    )
    sesion_bd.add(fila)
    sesion_bd.flush()
    return fila
