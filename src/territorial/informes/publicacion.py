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

from territorial.almacen.modelos import (
    CorridaAgentes,
    CorridaScoring,
    Informe,
    Insight,
)
from territorial.config import Config
from territorial.informes.composicion import componer


class PublicacionInvalida(ValueError):
    """No se publica. Mejor no publicar que publicar algo que no se sostiene."""


def _exigir_completa(corrida: CorridaScoring | CorridaAgentes, que: str) -> None:
    """Una corrida parcial no se publica.

    `scoring/persistencia.py` ya lo dice al insertarla: «ninguna vista de
    gerencia debe leer esta corrida». Una parcial recalculó unos municipios y
    los demás arrastran datos de otra, así que su ranking mezcla dos momentos.

    **El mensaje dice cuán parcial**, y no es cosmético: una corrida con 17 de
    18 municipios y otra con 1 de 18 son las dos «parcial», y lo que hay que
    hacer con cada una es distinto. Hoy el ciclo 2 solo tiene una corrida de
    agentes, con **1 de 18**: no se corrió nunca entero.
    """
    if corrida.tipo_corrida == "completa":
        return
    hechos = len(corrida.municipios_en_cohorte or [])
    total = len(corrida.municipios_objetivo or [])
    raise PublicacionInvalida(
        f"la corrida de {que} {corrida.id} es «{corrida.tipo_corrida}»: "
        f"{hechos} de {total} municipios. Recalcula el ciclo entero antes de "
        "publicar — un informe sobre una corrida parcial mezcla municipios de "
        "dos momentos, y los que falten arrastran datos de otra corrida."
    )


def _corrio_la_cadena(sesion_bd: Session, id_corrida: int) -> bool:
    """¿Esa corrida de agentes pasó por el Clasificador, o solo por M4?

    **`tipo_corrida` dice cuántos municipios se cubrieron, no qué pasos se
    corrieron**, y esa diferencia tiene una trampa concreta: las corridas 11 y
    12 del ciclo 3 están marcadas «completa» —cubren los 18— y contienen **cero
    insights del Clasificador**. Las creó `comparar_correlacionador.py
    --persistir`, que solo guarda correlaciones.

    Publicar una de esas daría un informe con las convergencias y **sin los
    insights individuales**, que son el grueso de lo que la gerencia lee. Nada
    lo habría advertido: el tipo de corrida es correcto, solo que no significa
    lo que parece.
    """
    return bool(
        sesion_bd.scalar(
            select(Insight.id)
            .where(Insight.id_corrida == id_corrida, Insight.origen == "clasificador")
            .limit(1)
        )
    )


def ciclos_publicables(sesion_bd: Session) -> dict[int, dict]:
    """Qué ciclos se pueden publicar hoy, y qué le falta a cada uno.

    Existe para poder preguntar **antes** de intentarlo. El caso que la motiva
    es real y no estaba escrito en ninguna parte: el **ciclo 2 nunca se corrió
    entero**, así que no es publicable por mucho que tenga scoring completo.
    Sin esto, la única forma de enterarse era intentar publicar y leer el error.
    """
    ciclos: dict[int, dict] = {}
    for modelo, clave in ((CorridaScoring, "scoring"), (CorridaAgentes, "agentes")):
        for corrida in sesion_bd.scalars(select(modelo)).all():
            caja = ciclos.setdefault(
                corrida.id_ciclo, {"scoring": None, "agentes": None}
            )
            if corrida.tipo_corrida != "completa":
                continue
            # Una corrida de agentes que no paso por el Clasificador no sirve
            # aunque cubra los 18 municipios. Ver `_corrio_la_cadena`.
            if clave == "agentes" and not _corrio_la_cadena(sesion_bd, corrida.id):
                continue
            # La más reciente que valga, de cada tipo.
            if caja[clave] is None or corrida.id > caja[clave]:
                caja[clave] = corrida.id

    for caja in ciclos.values():
        caja["publicable"] = caja["scoring"] is not None and caja["agentes"] is not None
        caja["falta"] = [k for k in ("scoring", "agentes") if caja[k] is None]
    return dict(sorted(ciclos.items()))


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
    if not _corrio_la_cadena(sesion_bd, id_corrida_agentes):
        raise PublicacionInvalida(
            f"la corrida de agentes {id_corrida_agentes} no tiene ni un insight "
            "del Clasificador: cubre los municipios pero **no corrió la cadena "
            "entera**. Suele ser una corrida de comparación persistida con "
            "`comparar_correlacionador.py --persistir`, que solo guarda "
            "correlaciones. Publicarla daría un informe con las convergencias y "
            "sin los insights individuales. Usa `ciclos_publicables()` para ver "
            "cuál sirve."
        )

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
