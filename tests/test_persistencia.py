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
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from territorial.agentes.correlacionador import (
    InsightCorrelacionado,
    ResultadoCorrelacion,
)
from territorial.agentes.linaje import PromptDivergente, registrar_prompt
from territorial.agentes.persistencia import (
    ORIGEN_CLASIFICADOR,
    ORIGEN_CORRELACIONADOR,
    crear_corrida,
    guardar_correlaciones,
    guardar_descartes,
    guardar_insights,
    guardar_traza,
)
from territorial.almacen.modelos import (
    Base,
    Ciclo,
    CorridaAgentes,
    Descarte,
    Insight,
    Municipio,
    SenalCruda,
    TrazaAgente,
    VersionPrompt,
)
from territorial.ciclo import _en_lotes

DIVIPOLA = "05147"
CICLO = 1


@pytest.fixture
def bd():
    """Base en memoria con el esquema de los modelos.

    Con `foreign_keys=ON`: sin él, SQLite no aplica las claves foráneas y estas
    pruebas pasarían aunque un insight apuntara a una corrida inexistente, que
    es exactamente lo que hay que impedir.
    """
    motor = create_engine("sqlite://")

    @event.listens_for(motor, "connect")
    def _fk(conexion, _record):
        cur = conexion.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(motor)
    with Session(motor) as s:
        s.add(Municipio(divipola=DIVIPOLA, nombre="Carepa", departamento="Antioquia"))
        s.add(Ciclo(id=CICLO, fecha_desde=date(2025, 9, 1), fecha_hasta=date(2025, 10, 22)))
        s.commit()
        yield s


@pytest.fixture
def corrida(bd):
    """Una pasada de agentes abierta, de la que colgar los insights."""
    c = crear_corrida(bd, CICLO, [DIVIPOLA], "v4", "v1")
    bd.commit()
    return c


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


def test_se_guardan_los_insights_con_su_origen(bd, corrida):
    guardar_insights(
        bd, [insight_dict("obra_vial", [1])], corrida.id, DIVIPOLA, "v4"
    )
    bd.commit()

    fila = bd.scalars(select(Insight)).one()
    assert fila.origen == ORIGEN_CLASIFICADOR
    assert fila.version_prompt == "v4"
    assert fila.ids_senal == [1]


def test_los_rechazados_tambien_se_guardan(bd, corrida):
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


def test_dos_pasadas_del_mismo_municipio_conviven(bd, corrida):
    """La propiedad que este cambio existe para dar.

    Aquí vivía `_borrar_previos`, que borraba la pasada anterior. Sin esto, A6
    no se puede medir: no hay comparación cuando la segunda borra a la primera.
    """
    guardar_insights(bd, [insight_dict("obra_vial", [1])], corrida.id, DIVIPOLA, "v4")
    bd.commit()

    segunda = crear_corrida(bd, CICLO, [DIVIPOLA], "v4", "v1")
    guardar_insights(
        bd,
        [insight_dict("vivienda", [2]), insight_dict("equipamiento", [3])],
        segunda.id,
        DIVIPOLA,
        "v4",
    )
    bd.commit()

    assert bd.query(CorridaAgentes).count() == 2
    assert bd.query(Insight).count() == 3
    primera = bd.scalars(select(Insight).where(Insight.id_corrida == corrida.id)).all()
    assert [f.categoria for f in primera] == ["obra_vial"]


def test_un_insight_no_puede_colgar_de_una_corrida_inexistente(bd):
    """Con `foreign_keys=ON`; sin el PRAGMA esto pasaría en silencio."""
    from sqlalchemy.exc import IntegrityError

    bd.add(Insight(id_corrida=9999, divipola=DIVIPOLA, categoria="x", resumen="y"))
    with pytest.raises(IntegrityError):
        bd.commit()


def test_las_filas_salen_con_id_asignado(bd, corrida):
    """El Correlacionador necesita los ids reales, no los del lote."""
    filas = guardar_insights(
        bd, [insight_dict("obra_vial", [1]), insight_dict("vivienda", [2])],
        corrida.id, DIVIPOLA, "v4",
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


def test_el_consolidado_guarda_de_que_insights_salio(bd, corrida):
    """CA-M4.4 fuera de memoria. Sin esto el linaje muere con el proceso."""
    filas = guardar_insights(
        bd, [insight_dict("obra_vial", [1]), insight_dict("servicios_publicos", [2])],
        corrida.id, DIVIPOLA, "v4",
    )
    mapa = {1: filas[0].id, 2: filas[1].id}

    guardar_correlaciones(bd, correlacion([1, 2]), corrida.id, DIVIPOLA, mapa)
    bd.commit()

    cons = bd.scalars(
        select(Insight).where(Insight.origen == ORIGEN_CORRELACIONADOR)
    ).one()
    assert cons.ids_insight_origen == sorted([filas[0].id, filas[1].id])
    assert cons.confianza == "alta"
    assert "corredor" in cons.por_que_convergen


def test_los_ids_de_origen_son_los_de_la_base_no_los_del_lote(bd, corrida):
    """El agente numera 1, 2, 3...; la base asigna otros. Guardar los del lote
    dejaría punteros que no significan nada fuera del proceso."""
    filas = guardar_insights(
        bd, [insight_dict("obra_vial", [1]), insight_dict("servicios_publicos", [2])],
        corrida.id, DIVIPOLA, "v4",
    )
    mapa = {1: filas[0].id, 2: filas[1].id}
    guardar_correlaciones(bd, correlacion([1, 2]), corrida.id, DIVIPOLA, mapa)
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


def test_el_consolidado_nace_validado(bd, corrida):
    """Su evidencia viene de insights que ya pasaron M3 y la copió el código."""
    filas = guardar_insights(
        bd, [insight_dict("obra_vial", [1]), insight_dict("servicios_publicos", [2])],
        corrida.id, DIVIPOLA, "v4",
    )
    guardar_correlaciones(
        bd, correlacion([1, 2]), corrida.id, DIVIPOLA, {1: filas[0].id, 2: filas[1].id}
    )
    bd.commit()

    cons = bd.scalars(
        select(Insight).where(Insight.origen == ORIGEN_CORRELACIONADOR)
    ).one()
    assert cons.estado_validacion == "validado"


def test_guardar_correlaciones_no_borra_los_insights_del_clasificador(bd, corrida):
    filas = guardar_insights(
        bd, [insight_dict("obra_vial", [1]), insight_dict("servicios_publicos", [2])],
        corrida.id, DIVIPOLA, "v4",
    )
    guardar_correlaciones(
        bd, correlacion([1, 2]), corrida.id, DIVIPOLA, {1: filas[0].id, 2: filas[1].id}
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


# --------------------------------------------------------------------------
# CA-M2.5 — qué se descartó y por qué
# --------------------------------------------------------------------------


def senal_en_bd(bd, id_: int) -> SenalCruda:
    s = SenalCruda(
        id=id_, id_ciclo=CICLO, divipola=DIVIPOLA, fuente="SECOP II",
        contenido="x", hash_dedup=f"h{id_}", datos={"objeto": "x"},
    )
    bd.add(s)
    bd.flush()
    return s


def test_los_descartes_declarados_se_guardan_con_su_motivo(bd, corrida):
    for i in (1, 2):
        senal_en_bd(bd, i)
    n = guardar_descartes(
        bd,
        [{"id_senal": 1, "motivo": "suministro"}, {"id_senal": 2, "motivo": "personal"}],
        [],
        corrida.id,
    )
    bd.commit()

    assert n == 2
    filas = {d.id_senal: d for d in bd.scalars(select(Descarte)).all()}
    assert filas[1].motivo == "suministro"
    assert all(d.declarado for d in filas.values())


def test_las_senales_sin_contabilizar_tambien_se_registran(bd, corrida):
    """Una señal que desaparece sin motivo es peor que una descartada con uno
    malo. Dejarla fuera del registro sería no cumplir CA-M2.5."""
    for i in (1, 2):
        senal_en_bd(bd, i)
    guardar_descartes(bd, [{"id_senal": 1, "motivo": "suministro"}], [2], corrida.id)
    bd.commit()

    perdida = bd.scalars(select(Descarte).where(Descarte.id_senal == 2)).one()
    assert not perdida.declarado
    assert "no la mencionó" in perdida.motivo


def test_una_senal_no_se_registra_dos_veces_en_la_misma_pasada(bd, corrida):
    senal_en_bd(bd, 1)
    n = guardar_descartes(
        bd,
        [{"id_senal": 1, "motivo": "suministro"}, {"id_senal": 1, "motivo": "otro"}],
        [1],
        corrida.id,
    )
    bd.commit()
    assert n == 1
    assert bd.query(Descarte).count() == 1


def test_dos_pasadas_pueden_descartar_la_misma_senal(bd, corrida):
    """Comparar qué descartó cada pasada es parte de medir A6."""
    senal_en_bd(bd, 1)
    guardar_descartes(bd, [{"id_senal": 1, "motivo": "suministro"}], [], corrida.id)
    otra = crear_corrida(bd, CICLO, [DIVIPOLA], "v4", "v1")
    guardar_descartes(bd, [{"id_senal": 1, "motivo": "estudio"}], [], otra.id)
    bd.commit()

    motivos = sorted(d.motivo for d in bd.scalars(select(Descarte)).all())
    assert motivos == ["estudio", "suministro"]


def test_un_motivo_vacio_no_deja_el_registro_mudo(bd, corrida):
    senal_en_bd(bd, 1)
    guardar_descartes(bd, [{"id_senal": 1, "motivo": "  "}], [], corrida.id)
    bd.commit()
    assert bd.scalars(select(Descarte)).one().motivo == "sin motivo declarado"


# --------------------------------------------------------------------------
# D7 — linaje de prompts por contenido
# --------------------------------------------------------------------------


class AlmacenFalso:
    """Almacén en memoria, para no escribir en disco durante las pruebas."""

    def __init__(self):
        self.objetos: dict[str, str] = {}

    def escribir_texto(self, ruta: str, texto: str) -> str:
        self.objetos[ruta] = texto
        return f"mem://{ruta}"


def test_registrar_un_prompt_lo_archiva_y_lo_ancla_por_hash(bd):
    alm = AlmacenFalso()
    fila = registrar_prompt(bd, "clasificador", "v4", "contenido del prompt", almacen=alm)
    bd.commit()

    assert fila.agente == "clasificador"
    assert len(fila.hash_sha256) == 64
    assert fila.uri_blob == "mem://prompts/clasificador_v4.md"
    assert alm.objetos["prompts/clasificador_v4.md"] == "contenido del prompt"


def test_registrar_dos_veces_el_mismo_prompt_no_duplica(bd):
    alm = AlmacenFalso()
    a = registrar_prompt(bd, "clasificador", "v4", "mismo texto", almacen=alm)
    b = registrar_prompt(bd, "clasificador", "v4", "mismo texto", almacen=alm)
    bd.commit()
    assert a.id == b.id
    assert bd.query(VersionPrompt).count() == 1


def test_editar_un_prompt_sin_cambiar_su_version_falla(bd):
    """El punto entero del hash.

    Si se dejara pasar, la fila diría v4 para dos contenidos distintos y el
    linaje mentiría en silencio — peor que no tenerlo.
    """
    alm = AlmacenFalso()
    registrar_prompt(bd, "clasificador", "v4", "texto original", almacen=alm)
    bd.commit()

    with pytest.raises(PromptDivergente, match="otro contenido"):
        registrar_prompt(bd, "clasificador", "v4", "texto EDITADO", almacen=alm)


def test_un_insight_apunta_al_prompt_bajo_el_que_nacio(bd, corrida):
    alm = AlmacenFalso()
    prompt = registrar_prompt(bd, "clasificador", "v4", "contenido", almacen=alm)
    filas = guardar_insights(
        bd, [insight_dict("obra_vial", [1])], corrida.id, DIVIPOLA, "v4",
        id_prompt=prompt.id,
    )
    bd.commit()

    assert filas[0].id_prompt == prompt.id
    # Y se puede navegar del insight al contenido exacto que lo produjo.
    registrada = bd.get(VersionPrompt, filas[0].id_prompt)
    assert alm.objetos[registrada.uri_blob.removeprefix("mem://")] == "contenido"
