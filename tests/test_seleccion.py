"""Pruebas de qué insights se pide calificar (M9-carga).

Es lo que hace medible H1, así que lo que hay que probar no es que elija cinco,
sino las **garantías** que sostienen la medición:

  · misma semilla y mismo municipio ⇒ misma muestra, siempre;
  · las siete gerencias reciben lo mismo (CA-M6.6);
  · la cuota 3+1+1 se respeta cuando se puede, y se rellena cuando no;
  · el payload registra qué composición salió.
"""

from __future__ import annotations

from territorial.informes.seleccion import PEDIDAS, pedir_calificacion, tipo_de


def correlacionado(id_: int) -> dict:
    return {
        "id": id_,
        "origen": "correlacionador",
        "evidencia": [{"fuente": "SECOP II"}, {"fuente": "RSS"}],
    }


def contratacion(id_: int) -> dict:
    return {"id": id_, "origen": "clasificador", "evidencia": [{"fuente": "SECOP II"}]}


def prensa(id_: int) -> dict:
    return {"id": id_, "origen": "clasificador", "evidencia": [{"fuente": "RSS"}]}


def municipio_completo() -> list[dict]:
    return (
        [correlacionado(i) for i in range(1, 9)]
        + [contratacion(i) for i in range(20, 40)]
        + [prensa(i) for i in range(50, 55)]
    )


# --------------------------------------------------------------------------
# A qué cuota pertenece cada insight
# --------------------------------------------------------------------------


def test_un_correlacionado_no_cuenta_como_su_fuente():
    """Cruza fuentes por definición: mirarlas primero lo contaría dos veces."""
    assert tipo_de(correlacionado(1)) == "correlacionado"


def test_la_prensa_gana_a_la_contratacion_en_el_mismo_insight():
    """336 señales de RSS frente a 19.640 de SECOP: si empatara, no saldría."""
    mixto = {"id": 1, "origen": "clasificador",
             "evidencia": [{"fuente": "SECOP II"}, {"fuente": "RSS"}]}
    assert tipo_de(mixto) == "prensa"


def test_un_insight_sin_fuente_conocida_es_otro():
    assert tipo_de({"id": 1, "origen": "clasificador", "evidencia": []}) == "otro"


# --------------------------------------------------------------------------
# La cuota 3 + 1 + 1
# --------------------------------------------------------------------------


def test_la_cuota_se_respeta_cuando_el_municipio_da_para_ella():
    _, _, composicion = pedir_calificacion(municipio_completo(), 3, "25286")
    assert composicion == {"correlacionado": 3, "contratacion": 1, "prensa": 1}


def test_los_correlacionados_son_la_prioridad():
    """Son lo que ninguna fuente sola produce."""
    ids, tipos, _ = pedir_calificacion(municipio_completo(), 3, "25286")
    assert sum(1 for t in tipos.values() if t == "correlacionado") == 3


def test_con_menos_de_tres_correlacionados_se_rellena():
    """En el ciclo 3 hay 38 correlacionados en 18 municipios: es lo normal."""
    insights = [correlacionado(1)] + [contratacion(i) for i in range(20, 30)]
    ids, tipos, composicion = pedir_calificacion(insights, 3, "25286")
    assert len(ids) == PEDIDAS
    assert composicion["correlacionado"] == 1
    assert composicion["relleno"] >= 1


def test_sin_correlacionados_sigue_pidiendo_cinco():
    insights = [contratacion(i) for i in range(20, 30)]
    ids, _, composicion = pedir_calificacion(insights, 3, "25286")
    assert len(ids) == PEDIDAS
    assert "correlacionado" not in composicion


def test_sin_prensa_se_completa_con_lo_que_haya():
    """Armenia no tiene contratación; otro municipio puede no tener prensa."""
    insights = [correlacionado(i) for i in range(1, 4)] + [
        contratacion(i) for i in range(20, 30)
    ]
    ids, _, composicion = pedir_calificacion(insights, 3, "25286")
    assert len(ids) == PEDIDAS
    assert "prensa" not in composicion


def test_siempre_cinco_mientras_los_haya():
    for n in (5, 8, 40):
        insights = [contratacion(i) for i in range(n)]
        assert len(pedir_calificacion(insights, 3, "25286")[0]) == PEDIDAS


def test_un_municipio_con_menos_de_cinco_los_pide_todos():
    insights = [correlacionado(1), contratacion(2), prensa(3)]
    ids, _, _ = pedir_calificacion(insights, 3, "25286")
    assert ids == [1, 2, 3]


def test_sin_insights_no_pide_nada():
    assert pedir_calificacion([], 3, "25286") == ([], {}, {})


def test_la_muestra_no_repite():
    ids, tipos, composicion = pedir_calificacion(municipio_completo(), 3, "25286")
    assert len(set(ids)) == len(ids) == sum(composicion.values()) == len(tipos)


# --------------------------------------------------------------------------
# Reproducibilidad: es lo que sostiene que H1 sea medible
# --------------------------------------------------------------------------


def test_misma_semilla_y_municipio_dan_siempre_la_misma_muestra():
    """Si variara, las calificaciones dejarían de ser comparables (CA-M6.6)."""
    insights = municipio_completo()
    primera = pedir_calificacion(insights, 3, "25286")
    for _ in range(5):
        assert pedir_calificacion(insights, 3, "25286") == primera


def test_el_orden_de_entrada_no_cambia_la_muestra():
    """Dos procesos pueden leer la base en otro orden y deben coincidir."""
    insights = municipio_completo()
    assert (
        pedir_calificacion(insights, 3, "25286")[0]
        == pedir_calificacion(list(reversed(insights)), 3, "25286")[0]
    )


def test_dos_municipios_del_mismo_ciclo_no_sacan_la_misma_muestra():
    insights = municipio_completo()
    assert (
        pedir_calificacion(insights, 3, "25286")[0]
        != pedir_calificacion(insights, 3, "73001")[0]
    )


def test_cada_pedido_dice_de_que_cuota_entro():
    """Sin esto, al analizar H1 habría que reconstruirlo a mano."""
    ids, tipos, _ = pedir_calificacion(municipio_completo(), 3, "25286")
    assert set(tipos) == set(ids)
    assert set(tipos.values()) <= {
        "correlacionado", "contratacion", "prensa", "relleno",
    }
