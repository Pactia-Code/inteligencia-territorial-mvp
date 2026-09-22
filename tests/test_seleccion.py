"""Pruebas de qué insights se pide calificar (M9-carga).

Es lo que hace medible H1, así que lo que hay que probar no es que elija cinco,
sino las **garantías** que sostienen la medición:

  · misma semilla y mismo municipio ⇒ misma muestra, siempre;
  · las siete gerencias reciben lo mismo (CA-M6.6);
  · entra al menos un insight de prensa cuando el municipio tiene;
  · las dos de más peso siempre están.
"""

from __future__ import annotations

from territorial.informes.seleccion import (
    FIJAS,
    PEDIDAS,
    es_de_prensa,
    pedir_calificacion,
)


def insight(id_: int, senales: int = 1, prensa: bool = False) -> dict:
    return {
        "id": id_,
        "ids_senal": list(range(senales)),
        "evidencia": [{"fuente": "RSS" if prensa else "SECOP II"}],
    }


def test_misma_semilla_y_municipio_dan_siempre_la_misma_muestra():
    """Si variara, las calificaciones dejarían de ser comparables."""
    insights = [insight(i, senales=i % 7) for i in range(1, 40)]
    primera = pedir_calificacion(insights, semilla=3, divipola="25286")
    for _ in range(5):
        assert pedir_calificacion(insights, semilla=3, divipola="25286") == primera


def test_el_orden_de_entrada_no_cambia_la_muestra():
    """Dos procesos pueden leer la base en otro orden y deben coincidir."""
    insights = [insight(i, senales=i % 7) for i in range(1, 40)]
    assert pedir_calificacion(insights, 3, "25286") == pedir_calificacion(
        list(reversed(insights)), 3, "25286"
    )


def test_dos_municipios_del_mismo_ciclo_no_sacan_la_misma_posicion():
    """La semilla se combina con el DIVIPOLA, no se reutiliza tal cual."""
    insights = [insight(i, senales=i % 7) for i in range(1, 40)]
    assert pedir_calificacion(insights, 3, "25286") != pedir_calificacion(
        insights, 3, "73001"
    )


def test_las_dos_de_mas_peso_siempre_entran():
    """Miden lo que el sistema priorizó; las aleatorias, lo que produce."""
    insights = [insight(1, senales=20), insight(2, senales=18)] + [
        insight(i, senales=1) for i in range(3, 30)
    ]
    elegidos = pedir_calificacion(insights, 3, "25286")
    assert 1 in elegidos
    assert 2 in elegidos


def test_entra_prensa_si_el_municipio_la_tiene():
    """Con 47 de contratación y 2 de prensa, el azar casi nunca la sacaría.

    Y sin prensa en la muestra, H1 no diría nada sobre la fuente que mejor
    convierte: 46% frente al 40% de SECOP.
    """
    insights = [insight(i, senales=10 - (i % 5)) for i in range(1, 48)]
    insights.append(insight(99, senales=1, prensa=True))
    elegidos = pedir_calificacion(insights, 3, "25286")
    por_id = {i["id"]: i for i in insights}
    assert any(es_de_prensa(por_id[e]) for e in elegidos)


def test_sin_prensa_en_el_municipio_no_se_inventa():
    insights = [insight(i, senales=3) for i in range(1, 30)]
    elegidos = pedir_calificacion(insights, 3, "25286")
    assert len(elegidos) == PEDIDAS


def test_la_garantia_de_prensa_no_desplaza_a_las_fijas():
    """Se sustituye la última aleatoria, nunca una de las de más peso."""
    insights = [insight(1, senales=30), insight(2, senales=29)] + [
        insight(i, senales=2) for i in range(3, 40)
    ]
    insights.append(insight(99, senales=1, prensa=True))
    elegidos = pedir_calificacion(insights, 3, "25286")
    assert {1, 2} <= set(elegidos)
    assert 99 in elegidos


def test_un_municipio_con_pocos_insights_los_pide_todos():
    insights = [insight(i) for i in range(1, 4)]
    assert pedir_calificacion(insights, 3, "25286") == [1, 2, 3]


def test_sin_insights_no_pide_nada():
    assert pedir_calificacion([], 3, "25286") == []


def test_siempre_pide_cinco_cuando_los_hay():
    insights = [insight(i, senales=i % 4) for i in range(1, 30)]
    assert len(pedir_calificacion(insights, 3, "25286")) == PEDIDAS
    assert PEDIDAS > FIJAS


def test_la_muestra_no_repite():
    insights = [insight(i, senales=i % 4) for i in range(1, 30)]
    elegidos = pedir_calificacion(insights, 3, "25286")
    assert len(set(elegidos)) == len(elegidos)


def test_es_de_prensa_mira_la_fuente_de_la_evidencia():
    assert es_de_prensa({"evidencia": [{"fuente": "RSS"}]})
    assert not es_de_prensa({"evidencia": [{"fuente": "SECOP II"}]})
    assert not es_de_prensa({"evidencia": []})
    assert not es_de_prensa({})
