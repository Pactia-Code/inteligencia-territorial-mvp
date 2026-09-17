"""Pruebas de M4 — Correlacionador (PRD §5, CA-M4.1 a CA-M4.4).

El agente llama a un LLM, pero **lo que decide si una correlación es admisible
es código**, y eso es lo que se prueba aquí: sin red, sin tokens y de forma
exacta.

La pieza crítica es CA-M4.4. Es requisito de H4, que es bloqueante, y por eso
el modelo no copia evidencia: declara qué converge y `ensamblar()` une la
evidencia por él. Si esa unión pierde una señal, el linaje se rompe sin que se
note en el texto del insight, que se seguiría viendo perfecto.
"""

from __future__ import annotations

from territorial.agentes.correlacionador import (
    MIN_CATEGORIAS,
    CalificacionPrevia,
    Convergencia,
    InsightValidado,
    _resumen_calificaciones,
    ensamblar,
)


def evidencia(id_senal: int, cita: str = "texto de la fuente") -> dict:
    return {
        "id_senal": id_senal,
        "cita_textual": cita,
        "url": f"https://ejemplo.gov.co/{id_senal}",
        "fecha": "2025-09-15",
        "fuente": "SECOP II",
    }


def insight(id_: int, categoria: str, senales: list[int]) -> InsightValidado:
    return InsightValidado(
        id=id_,
        categoria=categoria,
        resumen=f"insight {id_}",
        implicacion_inmobiliaria="implicación",
        evidencia=[evidencia(s) for s in senales],
        ids_senal=list(senales),
    )


def convergencia(ids: list[int], confianza: str = "alta") -> Convergencia:
    return Convergencia(
        ids_insight=ids,
        por_que_convergen="comparten el corredor de la calle 45",
        resumen="se está habilitando suelo al norte",
        implicacion_inmobiliaria="el suelo queda licenciable antes de que suba el precio",
        confianza=confianza,
    )


# --------------------------------------------------------------------------
# CA-M4.1 — cruce de categorías distintas
# --------------------------------------------------------------------------


def test_convergencia_entre_categorias_distintas_se_acepta():
    insights = [insight(1, "obra_vial", [10]), insight(2, "servicios_publicos", [20])]
    r = ensamblar([convergencia([1, 2])], insights)

    assert len(r.correlacionados) == 1
    assert r.correlacionados[0].categorias == ["obra_vial", "servicios_publicos"]
    assert not r.rechazados


def test_dos_insights_de_la_misma_categoria_no_son_una_correlacion():
    """Agrupar dos frentes de obra vial es trabajo del Clasificador (A4)."""
    insights = [insight(1, "obra_vial", [10]), insight(2, "obra_vial", [20])]
    r = ensamblar([convergencia([1, 2])], insights)

    assert not r.correlacionados
    assert len(r.rechazados) == 1
    assert "consolidación" in r.rechazados[0].motivo
    # Y los insights siguen vivos, sueltos.
    assert r.sueltos == [1, 2]


def test_un_grupo_de_uno_se_rechaza():
    insights = [insight(1, "obra_vial", [10]), insight(2, "vivienda", [20])]
    r = ensamblar([convergencia([1])], insights)

    assert not r.correlacionados
    assert "no es una convergencia" in r.rechazados[0].motivo


def test_referencia_a_un_insight_no_entregado_se_rechaza():
    """El modelo no puede correlacionar algo que no vio."""
    insights = [insight(1, "obra_vial", [10]), insight(2, "vivienda", [20])]
    r = ensamblar([convergencia([1, 2, 99])], insights)

    assert not r.correlacionados
    assert "no entregados" in r.rechazados[0].motivo
    assert "99" in r.rechazados[0].motivo


def test_umbral_de_categorias_es_dos():
    assert MIN_CATEGORIAS == 2


def test_otro_no_cuenta_como_categoria_para_el_cruce():
    """`otro` es un fallo de categorización del Clasificador, no una categoría.

    Si contara, bastaría con que el Clasificador fallara al etiquetar para que
    cualquier par de insights pareciera una convergencia.
    """
    insights = [insight(1, "servicios_publicos", [10]), insight(2, "otro", [20])]
    r = ensamblar([convergencia([1, 2])], insights)

    assert not r.correlacionados
    assert "fallo de categorización" in r.rechazados[0].motivo
    assert r.sueltos == [1, 2]


def test_dos_conocidas_mas_otro_si_se_acepta():
    """`otro` no bloquea: solo no cuenta para llegar al mínimo."""
    insights = [
        insight(1, "obra_vial", [10]),
        insight(2, "vivienda", [20]),
        insight(3, "otro", [30]),
    ]
    r = ensamblar([convergencia([1, 2, 3])], insights)

    assert len(r.correlacionados) == 1
    assert r.correlacionados[0].ids_senal == [10, 20, 30]


# --------------------------------------------------------------------------
# CA-M4.4 — la trazabilidad se preserva
# --------------------------------------------------------------------------


def test_la_evidencia_del_consolidado_es_la_union_de_sus_origenes():
    insights = [
        insight(1, "obra_vial", [10, 11]),
        insight(2, "servicios_publicos", [20]),
    ]
    r = ensamblar([convergencia([1, 2])], insights)

    assert r.correlacionados[0].ids_senal == [10, 11, 20]
    assert len(r.correlacionados[0].evidencia) == 3


def test_ninguna_senal_se_pierde_al_consolidar():
    """La comprobación que sostiene H4."""
    insights = [
        insight(1, "obra_vial", [10, 11]),
        insight(2, "vivienda", [20]),
        insight(3, "equipamiento", [30]),
    ]
    r = ensamblar([convergencia([1, 2])], insights)

    assert r.trazabilidad_intacta
    assert r.senales_perdidas == []
    # El 3 no convergió, pero sigue alcanzable como suelto.
    assert r.sueltos == [3]


def test_los_insights_que_no_convergen_no_se_pierden():
    """No converger no es un defecto: el insight sigue su camino."""
    insights = [
        insight(1, "obra_vial", [10]),
        insight(2, "vivienda", [20]),
        insight(3, "ordenamiento", [30]),
    ]
    r = ensamblar([convergencia([1, 2])], insights)
    assert r.sueltos == [3]


def test_un_grupo_rechazado_devuelve_sus_insights_a_sueltos():
    insights = [insight(1, "obra_vial", [10]), insight(2, "obra_vial", [20])]
    r = ensamblar([convergencia([1, 2])], insights)
    assert r.sueltos == [1, 2]
    assert r.trazabilidad_intacta


def test_la_evidencia_repetida_se_deduplica_sin_perder_senales():
    """Dos insights pueden citar el mismo fragmento. Repetirlo no añade linaje."""
    compartida = evidencia(10, "la misma cita exacta")
    a = InsightValidado(1, "obra_vial", "a", "x", [compartida], [10])
    b = InsightValidado(2, "vivienda", "b", "y", [dict(compartida), evidencia(20)], [10, 20])

    r = ensamblar([convergencia([1, 2])], [a, b])
    consolidado = r.correlacionados[0]

    assert len(consolidado.evidencia) == 2  # no 3
    assert consolidado.ids_senal == [10, 20]
    assert r.trazabilidad_intacta


def test_citas_distintas_de_la_misma_senal_se_conservan_ambas():
    """Deduplicar por señal y no por cita borraría evidencia legítima."""
    a = InsightValidado(1, "obra_vial", "a", "x", [evidencia(10, "primera cita")], [10])
    b = InsightValidado(2, "vivienda", "b", "y", [evidencia(10, "segunda cita")], [10])

    r = ensamblar([convergencia([1, 2])], [a, b])
    assert len(r.correlacionados[0].evidencia) == 2


# --------------------------------------------------------------------------
# Salida del modelo: lo que llega mal se corrige o se rechaza
# --------------------------------------------------------------------------


def test_una_confianza_desconocida_cae_a_baja():
    """Preferible degradar que descartar una convergencia por una palabra."""
    insights = [insight(1, "obra_vial", [10]), insight(2, "vivienda", [20])]
    r = ensamblar([convergencia([1, 2], confianza="altísima")], insights)
    assert r.correlacionados[0].confianza == "baja"


def test_la_confianza_se_normaliza_en_minusculas():
    insights = [insight(1, "obra_vial", [10]), insight(2, "vivienda", [20])]
    r = ensamblar([convergencia([1, 2], confianza="  ALTA ")], insights)
    assert r.correlacionados[0].confianza == "alta"


def test_ids_repetidos_en_un_grupo_no_inflan_el_consolidado():
    insights = [insight(1, "obra_vial", [10]), insight(2, "vivienda", [20])]
    r = ensamblar([convergencia([1, 1, 2, 2])], insights)
    assert r.correlacionados[0].ids_insight == [1, 2]


def test_sin_convergencias_todos_quedan_sueltos():
    insights = [insight(1, "obra_vial", [10]), insight(2, "vivienda", [20])]
    r = ensamblar([], insights)
    assert r.sueltos == [1, 2]
    assert r.trazabilidad_intacta


# --------------------------------------------------------------------------
# CA-M4.3 — el bucle de aprendizaje
# --------------------------------------------------------------------------


def test_las_calificaciones_se_agregan_por_categoria():
    """Se ajusta el criterio de relevancia, no la memoria de casos sueltos."""
    califs = [
        CalificacionPrevia("obra_vial", 5.0, 1),
        CalificacionPrevia("obra_vial", 4.0, 1),
        CalificacionPrevia("suministro", 1.0, 1),
    ]
    texto = _resumen_calificaciones(califs)
    assert "obra_vial: 4.5 de 5 sobre 2 calificaciones" in texto
    assert "suministro: 1.0 de 5 sobre 1 calificaciones" in texto


def test_sin_calificaciones_no_se_inyecta_nada_al_prompt():
    """Ciclo 1: el agente aplica su criterio sin ajuste."""
    assert _resumen_calificaciones([]) == ""
