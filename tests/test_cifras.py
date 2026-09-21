"""Pruebas de la detección de cifras (CA-M6.3).

La comprobación que sostiene «ninguna cifra de la salida puede faltar en la
entrada» tiene que medir las dos orillas con la misma vara. La primera versión
no lo hacía y acusó en falso a Carepa por «calles 76 y 80»: capturaba `80.` con
el punto final de la frase en la salida y no capturaba `80 ` en la entrada.
"""

from __future__ import annotations

from territorial.reglas.cifras import cifras, inventadas, variantes_de_cifra


def test_el_punto_final_de_la_frase_no_es_parte_del_numero():
    """El falso positivo real: Carepa, corrida 12, «calles 76 y 80.»"""
    entrada = "aguas residuales en la carrera 68 entre calles 76 y 80 y se mejoran"
    salida = "alcantarillado sobre la carrera 68 entre calles 76 y 80. Esto configura"
    assert inventadas(salida, entrada) == set()


def test_los_numeros_cortos_no_se_miran():
    """«dos frentes» o «el 15%» aparecen en cualquier prosa."""
    assert cifras("hay 15 predios y 2 frentes") == set()


def test_las_cifras_largas_si():
    assert cifras("3.480 hogares en déficit") == {"3480"}
    assert cifras("el 20,90% de los hogares") == {"2090"}
    assert cifras("78.412 habitantes") == {"78412"}


def test_una_cifra_inventada_se_detecta():
    entrada = "el contrato es por 1.200 millones"
    salida = "el contrato es por 1.200 millones y beneficia a 3.480 hogares"
    assert inventadas(salida, entrada) == {"3480"}


def test_da_igual_como_se_escriban_los_separadores():
    """`3.480` y `3480` son el mismo dato."""
    assert inventadas("son 3480 hogares", "son 3.480 hogares") == set()


def test_las_variantes_cubren_el_redondeo_del_modelo():
    """Un déficit de 20,9 puede salir como 20,9 o como 21."""
    v = variantes_de_cifra(20.9)
    assert "209" in v      # 20,9
    assert "2090" in v     # 20,90
    # «21» tiene dos dígitos y queda fuera por el mínimo: límite conocido.
    assert "21" not in v


def test_sin_valor_no_hay_variantes():
    assert variantes_de_cifra(None) == set()
