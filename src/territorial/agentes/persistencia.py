"""Guarda en la base lo que producen los agentes (B6, CA-M8.2).

**Nada se sobrescribe.** Cada pasada de la cadena inserta una `CorridaAgentes`
y los insights cuelgan de ella. Aquí vivía `_borrar_previos`, que borraba los
insights de la pasada anterior por `(ciclo, municipio, origen)`: dos pasadas del
mismo ciclo no podían compararse, y desde que M7 exista habría borrado los
insights que las gerencias calificaron. **Esa función ya no existe**, no está
desactivada: un `DELETE` dormido vuelve.

`tipo_corrida` se decide **aquí** y no en el llamador, igual que en el scoring:
el invariante vive donde vive el dato, así que cualquier punto de entrada futuro
queda protegido sin tener que acordarse.

**Se guardan también los insights rechazados por el validador.** Su proporción
*es* la tasa de alucinación medida (CA-M3.3), y de ella depende H4. Si solo se
guardara lo válido, el numerador existiría y el denominador no.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from territorial.agentes.correlacionador import ResultadoCorrelacion
from territorial.almacen.modelos import (
    CorridaAgentes,
    Descarte,
    Insight,
    Municipio,
    TrazaAgente,
)

log = logging.getLogger(__name__)

ORIGEN_CLASIFICADOR = "clasificador"
ORIGEN_CORRELACIONADOR = "correlacionador"

# Qué cadena corre. Se sube a mano cuando cambia **qué señales entran** al
# agente, aunque el prompt no se mueva.
#
#   p1  solo SECOP II, con prefiltro.
#   p2  SECOP II + RSS sin filtro, en lotes separados.
VERSION_PIPELINE = "p2"


def crear_corrida(
    sesion_bd: Session,
    id_ciclo: int,
    cohorte: list[str],
    version_clasificador: str | None = None,
    version_correlacionador: str | None = None,
) -> CorridaAgentes:
    """Abre una pasada. Se crea **antes** del bucle: los insights la necesitan.

    `cohorte` son los municipios que se van a procesar, no los que acabaron
    bien. Un municipio que falle sigue perteneciendo a la pasada — excluirlo
    haría que la corrida pareciera más completa de lo que fue.
    """
    objetivo = sorted(d for (d,) in sesion_bd.execute(select(Municipio.divipola)).all())
    cohorte = sorted(set(cohorte))
    completa = set(cohorte) >= set(objetivo)

    corrida = CorridaAgentes(
        id_ciclo=id_ciclo,
        tipo_corrida="completa" if completa else "parcial",
        municipios_objetivo=objetivo,
        municipios_en_cohorte=cohorte,
        version_clasificador=version_clasificador,
        version_correlacionador=version_correlacionador,
        version_pipeline=VERSION_PIPELINE,
    )
    sesion_bd.add(corrida)
    sesion_bd.flush()

    if not completa:
        faltan = sorted(set(objetivo) - set(cohorte))
        log.warning(
            "Corrida de agentes %s del ciclo %s es PARCIAL: %d de %d municipios. "
            "Quedan fuera %d: %s. Los insights de esos municipios siguen "
            "colgando de su pasada anterior, no de esta.",
            corrida.id, id_ciclo, len(cohorte), len(objetivo), len(faltan), faltan,
        )
    return corrida


def guardar_insights(
    sesion_bd: Session,
    insights: list[dict],
    id_corrida: int,
    divipola: str,
    version_prompt: str,
    id_prompt: int | None = None,
) -> list[Insight]:
    """Persiste la salida del Clasificador ya validada por M3.

    Devuelve las filas con su id asignado, que es lo que el Correlacionador
    necesita para referenciarlas.
    """
    filas: list[Insight] = []
    for ins in insights:
        fila = Insight(
            id_corrida=id_corrida,
            divipola=divipola,
            categoria=ins.get("categoria", "otro"),
            resumen=ins.get("resumen", ""),
            implicacion_inmobiliaria=ins.get("implicacion_inmobiliaria"),
            evidencia=ins.get("evidencia", []),
            ids_senal=ins.get("ids_senal", []),
            estado_validacion=ins.get("estado_validacion", "pendiente"),
            motivo_rechazo=ins.get("motivo_rechazo"),
            origen=ORIGEN_CLASIFICADOR,
            version_prompt=version_prompt,
            id_prompt=id_prompt,
        )
        sesion_bd.add(fila)
        filas.append(fila)

    # Se fuerza el INSERT ahora para que las filas tengan id: el Correlacionador
    # guarda en `ids_insight_origen` los ids reales de la base, no los de la
    # numeración temporal del lote.
    sesion_bd.flush()
    return filas


def guardar_correlaciones(
    sesion_bd: Session,
    resultado: ResultadoCorrelacion,
    id_corrida: int,
    divipola: str,
    mapa_ids: dict[int, int],
    id_prompt: int | None = None,
) -> list[Insight]:
    """Persiste los consolidados de M4.

    `mapa_ids` traduce el id temporal que vio el agente al id real de la base.
    Sin esa traducción, `ids_insight_origen` apuntaría a números de lote que no
    significan nada fuera del proceso, y CA-M4.4 quedaría en nada.
    """
    filas: list[Insight] = []
    for c in resultado.correlacionados:
        origenes = sorted(mapa_ids[i] for i in c.ids_insight if i in mapa_ids)
        fila = Insight(
            id_corrida=id_corrida,
            divipola=divipola,
            categoria="+".join(c.categorias)[:60],
            resumen=c.resumen,
            implicacion_inmobiliaria=c.implicacion_inmobiliaria,
            evidencia=c.evidencia,
            ids_senal=c.ids_senal,
            # Nace validado: su evidencia es la de insights que ya pasaron M3,
            # y el código la copió sin que el modelo la tocara.
            estado_validacion="validado",
            origen=ORIGEN_CORRELACIONADOR,
            version_prompt=resultado.version_prompt,
            id_prompt=id_prompt,
            ids_insight_origen=origenes,
            por_que_convergen=c.por_que_convergen,
            confianza=c.confianza,
        )
        sesion_bd.add(fila)
        filas.append(fila)

    sesion_bd.flush()
    return filas


def guardar_traza(
    sesion_bd: Session,
    id_ciclo: int,
    agente: str,
    modelo: str | None,
    tokens_entrada: int,
    tokens_salida: int,
    duracion_ms: int,
    tokens_cache_lectura: int = 0,
    hash_input: str | None = None,
    hash_output: str | None = None,
) -> TrazaAgente:
    """Una fila por corrida de agente. CA-M8.2 y CA-M8.3.

    No se borra nada aquí: la traza es un registro histórico, y perder la
    corrida anterior al recalcular haría imposible auditar qué pasó.
    """
    traza = TrazaAgente(
        id_ciclo=id_ciclo,
        agente=agente,
        modelo=modelo,
        tokens_entrada=tokens_entrada,
        tokens_salida=tokens_salida,
        tokens_cache_lectura=tokens_cache_lectura,
        duracion_ms=duracion_ms,
        hash_input=hash_input,
        hash_output=hash_output,
    )
    sesion_bd.add(traza)
    return traza


def guardar_descartes(
    sesion_bd: Session,
    descartes: list[dict],
    sin_contabilizar: list[int],
    id_corrida: int,
) -> int:
    """Registra qué se descartó y por qué. Es CA-M2.5.

    `descartes` son los que el modelo declaró, con su motivo.
    `sin_contabilizar` son las señales que no aparecieron ni en un insight ni
    en un descarte: se guardan igual, marcadas `declarado=False`. Una señal que
    desaparece sin motivo es peor que una descartada con uno malo, y dejarla
    fuera del registro sería no cumplir el criterio.

    Sin esto, la tasa de reducción de CA-M2.1 no es auditable: queda el
    numerador y se pierde el denominador.
    """
    vistas: set[int] = set()
    filas = 0

    for d in descartes:
        id_senal = d.get("id_senal")
        if id_senal is None or id_senal in vistas:
            continue
        vistas.add(id_senal)
        sesion_bd.add(
            Descarte(
                id_corrida=id_corrida,
                id_senal=id_senal,
                motivo=(d.get("motivo") or "").strip() or "sin motivo declarado",
                declarado=True,
            )
        )
        filas += 1

    for id_senal in sin_contabilizar:
        if id_senal in vistas:
            continue
        vistas.add(id_senal)
        sesion_bd.add(
            Descarte(
                id_corrida=id_corrida,
                id_senal=id_senal,
                motivo="el modelo no la mencionó ni en insights ni en descartes",
                declarado=False,
            )
        )
        filas += 1

    sesion_bd.flush()
    return filas
