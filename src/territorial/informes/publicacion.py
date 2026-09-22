"""Publica el informe de un ciclo. Un solo publicado a la vez, y congelado.

Publicar es un **acto deliberado** y tiene tres efectos que van juntos o no van:

  1. Se compone el contenido desde el almacén (`composicion.componer`).
  2. Se archiva el informe que estuviera publicado de ese ciclo.
  3. Entra el nuevo, con **las dos corridas congeladas**.

Los tres en la misma transacción. Si se separaran, habría un instante con dos
informes publicados del mismo ciclo o con ninguno, y «la última publicada» —que
es como se define la corrida canónica— dejaría de tener respuesta justo cuando
alguien la necesita.

**Esto es lo que resuelve A9, y sin flag.** La corrida canónica de un ciclo es
la que referencia su informe publicado. No hay `es_canonica` que mantener
sincronizado ni que pueda acabar en dos filas a la vez.

No se pregunta si archivar: la regla es que solo puede haber uno vigente, y un
índice único parcial lo garantiza en la base. Preguntar abriría la puerta al
estado que no debe existir.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from territorial.almacen.modelos import CorridaAgentes, CorridaScoring, Informe
from territorial.config import Config
from territorial.informes.composicion import componer


class PublicacionInvalida(ValueError):
    """No se publica. Mejor no publicar que publicar algo que no se sostiene."""


def _exigir_completa(corrida: CorridaScoring | CorridaAgentes, que: str) -> None:
    """Una corrida parcial no se publica.

    `scoring/persistencia.py` ya lo dice al insertarla: «ninguna vista de
    gerencia debe leer esta corrida». Una parcial recalculó unos municipios y
    los demás arrastran datos de otra, así que su ranking mezcla dos momentos.
    """
    if corrida.tipo_corrida != "completa":
        raise PublicacionInvalida(
            f"la corrida de {que} {corrida.id} es «{corrida.tipo_corrida}», no "
            "completa. Recalcula el ciclo entero antes de publicar: un informe "
            "sobre una corrida parcial mezcla municipios de dos momentos."
        )


def informe_vigente(sesion_bd: Session, id_ciclo: int) -> Informe | None:
    """El informe publicado del ciclo, si lo hay. Define la corrida canónica."""
    return sesion_bd.scalars(
        select(Informe).where(
            Informe.id_ciclo == id_ciclo, Informe.estado == "publicado"
        )
    ).one_or_none()


def publicar(
    sesion_bd: Session,
    id_corrida_scoring: int,
    id_corrida_agentes: int,
    config: Config | None = None,
    tope_calificable: int = 3,
) -> Informe:
    """Compone, archiva el anterior y publica. Devuelve el informe nuevo."""
    contenido = componer(
        sesion_bd, id_corrida_scoring, id_corrida_agentes,
        config=config, tope_calificable=tope_calificable,
    )
    id_ciclo = contenido["ciclo"]

    _exigir_completa(sesion_bd.get(CorridaScoring, id_corrida_scoring), "scoring")
    _exigir_completa(sesion_bd.get(CorridaAgentes, id_corrida_agentes), "agentes")

    if not contenido["municipios"]:
        raise PublicacionInvalida(
            f"la corrida de scoring {id_corrida_scoring} no deja ningún municipio "
            "que mostrar. Un informe vacío no es un informe."
        )

    anterior = informe_vigente(sesion_bd, id_ciclo)
    if anterior is not None:
        anterior.estado = "archivado"
        # **El flush va aquí y no al final.** El índice único parcial solo
        # admite un `publicado` por ciclo: si el nuevo se insertara antes de que
        # el viejo quede archivado, la base lo rechazaría.
        sesion_bd.flush()

    informe = Informe(
        id_ciclo=id_ciclo,
        id_corrida=id_corrida_scoring,
        id_corrida_agentes=id_corrida_agentes,
        contenido=contenido,
        estado="publicado",
    )
    sesion_bd.add(informe)
    sesion_bd.flush()
    return informe
