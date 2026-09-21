"""La propiedad que toda compuerta sobre la salida de un agente debe cumplir.

**Una compuerta que no conoce su piso de ruido no mide un efecto: mide varianza
y le pone una etiqueta de aprobado o suspenso.** La primera versión de la
compuerta del Correlacionador exigía que la versión nueva no correlacionara más
que la vieja en **ningún municipio**, y suspendió a v2. El control demostró que
habría suspendido a **v1 contra sí mismo**, con 14 de 18 municipios moviéndose.

De ahí sale el invariante que se prueba aquí: **la compuerta nunca puede
suspender a la línea base que la calibró.** Si lo hace, está midiendo ruido.

El instrumento vive en `scripts/`, así que se carga por ruta. Es feo, y aun así
conviene: el invariante es más importante que la elegancia del import, y sin
prueba se pierde en cuanto alguien toque el criterio.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def instrumento():
    ruta = RAIZ / "scripts" / "comparar_correlacionador.py"
    spec = importlib.util.spec_from_file_location("comparar_correlacionador", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_la_compuerta_no_suspende_a_su_propia_linea_base(instrumento):
    """El invariante. Si falla, la compuerta mide varianza, no efecto."""
    for metrica, observado in instrumento.PISO_RUIDO.items():
        techo = instrumento.techo_del_ruido(metrica)
        for valor in observado:
            assert valor <= techo, (
                f"{metrica}: la pasada {valor} de la línea base supera el techo "
                f"{techo}. La compuerta se suspendería a sí misma."
            )


def test_el_techo_es_el_rango_observado_y_no_un_margen_sobre_a(instrumento):
    """Un margen relativo sobre A tiene un filo que el rango no tiene.

    Si A cae en el fondo de su rango y B en lo alto, un margen sobre A suspende
    al mismo prompt. Con las cifras medidas no es hipotético: v1 dio 39 y 42 en
    dos pasadas seguidas, y un margen del 7,3% sobre 39 da 41,9 — suspendería a
    la pasada de 42.
    """
    assert instrumento.techo_del_ruido("convergencias") == 42
    margen_sobre_el_minimo = 39 * (1 + instrumento.oscilacion("convergencias"))
    assert margen_sobre_el_minimo < 42


def test_v2_cae_dentro_del_ruido_en_lo_que_preocupaba(instrumento):
    """40 convergencias contra un techo de 42: la diferencia es varianza."""
    assert 40 <= instrumento.techo_del_ruido("convergencias")


def test_v2_sale_del_ruido_en_el_efecto_buscado(instrumento):
    """35 implicaciones con tipología contra un techo de 24. Eso es un efecto."""
    assert 35 > instrumento.techo_del_ruido("tipologia")


def test_hay_piso_medido_para_cada_metrica_que_juzga(instrumento):
    """Sin al menos dos pasadas no hay rango, y sin rango no hay compuerta."""
    for metrica, observado in instrumento.PISO_RUIDO.items():
        assert len(observado) >= 2, f"{metrica}: una sola pasada no es un piso"


def test_el_piso_declara_sobre_que_corpus_se_midio(instrumento):
    """Un piso de otro corpus no es un piso: la compuerta se niega a juzgar."""
    assert isinstance(instrumento.CORPUS_DEL_PISO, int)
