"""Pruebas de la persistencia de insights y trazas (B6).

Corren contra una SQLite en memoria levantada con `create_all`, que aquí sí es
legítimo: es una base efímera de prueba, no un esquema gobernado. Que coincida
con las migraciones lo garantiza `alembic check`, no estas pruebas.

Lo que más importa aquí es `ids_insight_origen`. Es CA-M4.4 fuera de memoria:
un consolidado que no sabe de qué insights salió rompe el linaje en cuanto el
proceso termina, y H4 es bloqueante.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from territorial.agentes.correlacionador import (
    InsightCorrelacionado,
    ResultadoCorrelacion,
)
from territorial.agentes.persistencia import (
    ORIGEN_CLASIFICADOR,
    ORIGEN_CORRELACIONADOR,
    guardar_correlaciones,
    guardar_insights,
    guardar_traza,
)
from territorial.almacen.modelos import (
    Base,
    Ciclo,
    Insight,
    Municipio,
    SenalCruda,
    TrazaAgente,
)
from territorial.ciclo import _en_lotes

DIVIPOLA = "05147"
CICLO = 1


@pytest.fixture
def bd():
    """Base en memoria con el esquema de los modelos."""
    motor = create_engine("sqlite://")
    Base.metadata.create_all(motor)
    with Session(motor) as s:
        s.add(Municipio(divipola=DIVIPOLA, nombre="Carepa", departamento="Antioquia"))
        s.add(Ciclo(id=CICLO, fecha_desde=date(2025, 9, 1), fecha_hasta=date(2025, 10, 22)))
        s.commit()
        yield s


def insight_dict(categoria: str, senales: list[int], estado: str = "validado") -> dict:
    return {
        "categoria": categoria,
        "resumen": f"resumen de {categoria}",
        "implicacion_inmobiliaria": "implicación",
        "evidencia": [
            {
                "id_senal": s,
                "cita_textual": f"cita {s}",
                "url": f"https://ejemplo.gov.co/{s}",
                "fecha": "2025-09-15",
                "fuente": "SECOP II",
            }
            for s in senales
        ],
        "ids_senal": senales,
        "estado_validacion": estado,
        "motivo_rechazo": None if estado == "validado" else "sin url",
    }


# --------------------------------------------------------------------------
# Insights del Clasificador
# --------------------------------------------------------------------------


def test_se_guardan_los_insights_con_su_origen(bd):
    guardar_insights(
        bd, [insight_dict("obra_vial", [1])], CICLO, DIVIPOLA, "v4"
    )
    bd.commit()

    fila = bd.scalars(select(Insight)).one()
    assert fila.origen == ORIGEN_CLASIFICADOR
    assert fila.version_prompt == "v4"
    assert fila.ids_senal == [1]


def test_los_rechazados_tambien_se_guardan(bd):
    """Su proporción es la tasa de alucinación medida (CA-M3.3), de la que
    depende H4. Guardar solo lo válido dejaría el numerador sin denominador."""
    guardar_insights(
        bd,
        [
            insight_dict("obra_vial", [1], estado="validado"),
            insight_dict("vivienda", [2], estado="rechazado"),
        ],
        CICLO,
        DIVIPOLA,
        "v4",
    )
    bd.commit()

    estados = sorted(f.estado_validacion for f in bd.scalars(select(Insight)).all())
    assert estados == ["rechazado", "validado"]
    rechazado = bd.scalars(
        select(Insight).where(Insight.estado_validacion == "rechazado")
    ).one()
    assert rechazado.motivo_rechazo == "sin url"


def test_reescribir_un_municipio_no_acumula_corridas(bd):
    """El Clasificador no es reproducible (A6): sin esto, dos corridas dejarían
    insights superpuestos de ambas y nadie sabría cuál es el bueno."""
    guardar_insights(bd, [insight_dict("obra_vial", [1])], CICLO, DIVIPOLA, "v4")
    bd.commit()
    guardar_insights(
        bd,
        [insight_dict("vivienda", [2]), insight_dict("equipamiento", [3])],
        CICLO,
        DIVIPOLA,
        "v4",
    )
    bd.commit()

    filas = bd.scalars(select(Insight)).all()
    assert len(filas) == 2
    assert sorted(f.categoria for f in filas) == ["equipamiento", "vivienda"]


def test_reescribir_un_municipio_no_toca_a_los_demas(bd):
    bd.add(Municipio(divipola="08001", nombre="Barranquilla", departamento="Atlántico"))
    bd.commit()

    guardar_insights(bd, [insight_dict("obra_vial", [1])], CICLO, DIVIPOLA, "v4")
    guardar_insights(bd, [insight_dict("vivienda", [9])], CICLO, "08001", "v4")
    bd.commit()

    guardar_insights(bd, [insight_dict("equipamiento", [2])], CICLO, DIVIPOLA, "v4")
    bd.commit()

    otros = bd.scalars(select(Insight).where(Insight.divipola == "08001")).all()
    assert len(otros) == 1


def test_las_filas_salen_con_id_asignado(bd):
    """El Correlacionador necesita los ids reales, no los del lote."""
    filas = guardar_insights(
        bd, [insight_dict("obra_vial", [1]), insight_dict("vivienda", [2])],
        CICLO, DIVIPOLA, "v4",
    )
    assert all(f.id is not None for f in filas)


# --------------------------------------------------------------------------
# Consolidados del Correlacionador — CA-M4.4 en la base
# --------------------------------------------------------------------------


def correlacion(ids_temporales: list[int]) -> ResultadoCorrelacion:
    return ResultadoCorrelacion(
        correlacionados=[
            InsightCorrelacionado(
                ids_insight=ids_temporales,
                categorias=["obra_vial", "servicios_publicos"],
                por_que_convergen="comparten el corredor de la calle 45",
                resumen="se habilita suelo al norte",
                implicacion_inmobiliaria="licenciable antes de que suba el precio",
                confianza="alta",
                evidencia=[{"id_senal": 1, "cita_textual": "a"}],
                ids_senal=[1, 2],
            )
        ],
        version_prompt="v1",
    )


def test_el_consolidado_guarda_de_que_insights_salio(bd):
    """CA-M4.4 fuera de memoria. Sin esto el linaje muere con el proceso."""
    filas = guardar_insights(
        bd, [insight_dict("obra_vial", [1]), insight_dict("servicios_publicos", [2])],
        CICLO, DIVIPOLA, "v4",
    )
    mapa = {1: filas[0].id, 2: filas[1].id}

    guardar_correlaciones(bd, correlacion([1, 2]), CICLO, DIVIPOLA, mapa)
    bd.commit()

    cons = bd.scalars(
        select(Insight).where(Insight.origen == ORIGEN_CORRELACIONADOR)
    ).one()
    assert cons.ids_insight_origen == sorted([filas[0].id, filas[1].id])
    assert cons.confianza == "alta"
    assert "corredor" in cons.por_que_convergen


def test_los_ids_de_origen_son_los_de_la_base_no_los_del_lote(bd):
    """El agente numera 1, 2, 3...; la base asigna otros. Guardar los del lote
    dejaría punteros que no significan nada fuera del proceso."""
    filas = guardar_insights(
        bd, [insight_dict("obra_vial", [1]), insight_dict("servicios_publicos", [2])],
        CICLO, DIVIPOLA, "v4",
    )
    mapa = {1: filas[0].id, 2: filas[1].id}
    guardar_correlaciones(bd, correlacion([1, 2]), CICLO, DIVIPOLA, mapa)
    bd.commit()

    cons = bd.scalars(
        select(Insight).where(Insight.origen == ORIGEN_CORRELACIONADOR)
    ).one()
    # Se puede navegar del consolidado a sus orígenes reales.
    origenes = bd.scalars(
        select(Insight).where(Insight.id.in_(cons.ids_insight_origen))
    ).all()
    assert len(origenes) == 2
    assert all(o.origen == ORIGEN_CLASIFICADOR for o in origenes)


def test_el_consolidado_nace_validado(bd):
    """Su evidencia viene de insights que ya pasaron M3 y la copió el código."""
    filas = guardar_insights(
        bd, [insight_dict("obra_vial", [1]), insight_dict("servicios_publicos", [2])],
        CICLO, DIVIPOLA, "v4",
    )
    guardar_correlaciones(
        bd, correlacion([1, 2]), CICLO, DIVIPOLA, {1: filas[0].id, 2: filas[1].id}
    )
    bd.commit()

    cons = bd.scalars(
        select(Insight).where(Insight.origen == ORIGEN_CORRELACIONADOR)
    ).one()
    assert cons.estado_validacion == "validado"


def test_guardar_correlaciones_no_borra_los_insights_del_clasificador(bd):
    filas = guardar_insights(
        bd, [insight_dict("obra_vial", [1]), insight_dict("servicios_publicos", [2])],
        CICLO, DIVIPOLA, "v4",
    )
    guardar_correlaciones(
        bd, correlacion([1, 2]), CICLO, DIVIPOLA, {1: filas[0].id, 2: filas[1].id}
    )
    bd.commit()

    del_clasificador = bd.scalars(
        select(Insight).where(Insight.origen == ORIGEN_CLASIFICADOR)
    ).all()
    assert len(del_clasificador) == 2


# --------------------------------------------------------------------------
# Trazas — CA-M8.2
# --------------------------------------------------------------------------


def test_la_traza_registra_tokens_y_duracion(bd):
    guardar_traza(
        bd, id_ciclo=CICLO, agente="clasificador", modelo="gpt-5.4-mini",
        tokens_entrada=4749, tokens_salida=2157, duracion_ms=8200,
        hash_input="abc",
    )
    bd.commit()

    t = bd.scalars(select(TrazaAgente)).one()
    assert (t.tokens_entrada, t.tokens_salida) == (4749, 2157)
    assert t.modelo == "gpt-5.4-mini"
    assert t.hash_input == "abc"


def test_las_trazas_se_acumulan_no_se_reemplazan(bd):
    """Es un registro histórico: perder la corrida anterior haría imposible
    auditar qué pasó, y CA-M8.2 existe justamente para eso."""
    for _ in range(3):
        guardar_traza(
            bd, id_ciclo=CICLO, agente="clasificador", modelo="gpt-5.4-mini",
            tokens_entrada=100, tokens_salida=50, duracion_ms=1000,
        )
    bd.commit()
    assert bd.query(TrazaAgente).count() == 3


# --------------------------------------------------------------------------
# Troceo por lotes (B5)
# --------------------------------------------------------------------------


def senal_falsa(id_: int, objeto: str) -> SenalCruda:
    return SenalCruda(
        id=id_,
        id_ciclo=CICLO,
        divipola=DIVIPOLA,
        fuente="SECOP II",
        contenido=objeto,
        hash_dedup=f"h{id_}",
        datos={"objeto": objeto},
    )


def test_el_troceo_no_pierde_ni_duplica_señales():
    """Antes se mandaba `pasan[:limite]` y el resto se descartaba en silencio:
    de las 897 señales de Barranquilla se clasificaban 25."""
    senales = [senal_falsa(i, f"objeto {i}") for i in range(97)]
    lotes = _en_lotes(senales, 25)

    assert len(lotes) == 4
    ids = [s.id for lote in lotes for s in lote]
    assert sorted(ids) == list(range(97))


def test_los_objetos_identicos_caen_en_el_mismo_lote():
    """El Clasificador agrupa por frente de intervención. Si dos contratos del
    mismo frente caen en lotes distintos salen dos insights: es A4 empeorado."""
    senales = (
        [senal_falsa(i, "RECONSTRUCCION DE VIAS URBANAS") for i in range(5)]
        + [senal_falsa(100 + i, "SUMINISTRO DE PAPELERIA") for i in range(5)]
    )
    # Se barajan para que el orden de entrada no sea el que agrupa.
    revueltas = [senales[i] for i in (0, 5, 1, 6, 2, 7, 3, 8, 4, 9)]
    lotes = _en_lotes(revueltas, 5)

    for lote in lotes:
        objetos = {(s.datos or {})["objeto"] for s in lote}
        assert len(objetos) == 1, "un lote mezcló frentes que podían ir juntos"


def test_el_troceo_ignora_mayusculas_y_acentos_al_agrupar():
    senales = [
        senal_falsa(1, "RECONSTRUCCIÓN DE VÍAS"),
        senal_falsa(2, "suministro de papelería"),
        senal_falsa(3, "reconstruccion de vias"),
    ]
    lotes = _en_lotes(senales, 2)
    primero = {s.id for s in lotes[0]}
    assert primero == {1, 3}


def test_un_lote_vacio_no_produce_lotes():
    assert _en_lotes([], 25) == []
