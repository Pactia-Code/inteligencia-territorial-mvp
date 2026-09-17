"""Guarda en la base lo que producen los agentes (B6).

Hasta ahora M2 y M4 solo corrían en scripts de prueba y su salida se perdía al
terminar el proceso. Sin esto no hay ciclo completo: M4 no tiene entrada
estable, M7 no tiene qué calificar y F6 del scoring nunca tendrá datos.

Dos decisiones:

**Se guardan también los insights rechazados por el validador.** Podría
parecer basura, pero su proporción *es* la tasa de alucinación medida
(CA-M3.3), y de ella depende H4. Si solo se guardara lo válido, el numerador
existiría y el denominador no.

**Reescribir un municipio borra lo suyo antes de insertar.** El Clasificador no
es reproducible —el mismo lote da 3 insights una vez y 6 otra, pendiente A6—,
así que no hay clave natural con la que hacer un upsert honesto. Se borra y se
reinserta el par (ciclo, municipio, origen), que deja la base en un estado
consistente en vez de acumular corridas superpuestas.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from territorial.agentes.correlacionador import ResultadoCorrelacion
from territorial.almacen.modelos import Insight, TrazaAgente

ORIGEN_CLASIFICADOR = "clasificador"
ORIGEN_CORRELACIONADOR = "correlacionador"


def _borrar_previos(sesion_bd: Session, id_ciclo: int, divipola: str, origen: str) -> int:
    existentes = sesion_bd.scalars(
        select(Insight.id).where(
            Insight.id_ciclo == id_ciclo,
            Insight.divipola == divipola,
            Insight.origen == origen,
        )
    ).all()
    if not existentes:
        return 0
    sesion_bd.execute(delete(Insight).where(Insight.id.in_(existentes)))
    return len(existentes)


def guardar_insights(
    sesion_bd: Session,
    insights: list[dict],
    id_ciclo: int,
    divipola: str,
    version_prompt: str,
) -> list[Insight]:
    """Persiste la salida del Clasificador ya validada por M3.

    Cada dict trae lo del Clasificador más `estado_validacion` y
    `motivo_rechazo`, que los pone el validador. Devuelve las filas con su id
    asignado, que es lo que el Correlacionador necesita para referenciarlas.
    """
    _borrar_previos(sesion_bd, id_ciclo, divipola, ORIGEN_CLASIFICADOR)

    filas: list[Insight] = []
    for ins in insights:
        fila = Insight(
            id_ciclo=id_ciclo,
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
    id_ciclo: int,
    divipola: str,
    mapa_ids: dict[int, int],
) -> list[Insight]:
    """Persiste los consolidados de M4.

    `mapa_ids` traduce el id temporal que vio el agente al id real de la base.
    Sin esa traducción, `ids_insight_origen` apuntaría a números de lote que no
    significan nada fuera del proceso, y CA-M4.4 quedaría en nada.
    """
    _borrar_previos(sesion_bd, id_ciclo, divipola, ORIGEN_CORRELACIONADOR)

    filas: list[Insight] = []
    for c in resultado.correlacionados:
        origenes = sorted(mapa_ids[i] for i in c.ids_insight if i in mapa_ids)
        fila = Insight(
            id_ciclo=id_ciclo,
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
