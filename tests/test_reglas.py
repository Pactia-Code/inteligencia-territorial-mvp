"""Pruebas de la capa determinista: validador, prefiltro y cobertura.

Todo aquí es código sin LLM, así que es verificable de forma exacta. El
validador es el que más importa: su tasa de rechazo es la tasa de alucinación
medida (CA-M3.3), y de ella depende H4.
"""

from __future__ import annotations

from datetime import date

import pytest

from territorial.reglas import cobertura as cob
from territorial.reglas import prefiltro
from territorial.reglas.normalizacion import contiene, normalizar
from territorial.reglas.validador import Senal, validar

DIVIPOLA = "25286"
CICLO = 1

SENAL_SECOP = Senal(
    id=1,
    divipola=DIVIPOLA,
    id_ciclo=CICLO,
    fuente="SECOP II",
    contenido="CONSTRUCCIÓN DE PAVIMENTO EN LA VÍA MOSQUERA-FUNZA, TRAMO 2",
    url="https://community.secop.gov.co/Public/Tendering/OpportunityDetail/Index",
    fecha_publicacion=date(2025, 9, 15),
)

SENAL_BING = Senal(
    id=2,
    divipola=DIVIPOLA,
    id_ciclo=CICLO,
    fuente="Bing",
    contenido="Se está desarrollando un proyecto de 696 apartamentos.",
    url=None,
    fecha_publicacion=None,
)

SENALES = {1: SENAL_SECOP, 2: SENAL_BING}


def evidencia_valida(**cambios):
    base = {
        "id_senal": 1,
        "fuente": "SECOP II",
        "url": SENAL_SECOP.url,
        "fecha": "2025-09-15",
        "cita_textual": "CONSTRUCCIÓN DE PAVIMENTO EN LA VÍA MOSQUERA-FUNZA",
    }
    base.update(cambios)
    return base


# --------------------------------------------------------------------------
# Normalización
# --------------------------------------------------------------------------


def test_normalizar_quita_acentos_y_colapsa_espacios():
    assert normalizar("  CONSTRUCCIÓN   DE   VÍA  ") == "construccion de via"


def test_contiene_ignora_mayusculas_y_acentos():
    assert contiene("CONSTRUCCIÓN DE LA VÍA", "construccion de la via")


def test_contiene_no_acepta_texto_ausente():
    assert not contiene("CONSTRUCCIÓN DE LA VÍA", "demolición del puente")


def test_contiene_rechaza_cita_vacia():
    assert not contiene("cualquier cosa", "")


# --- Variación de separadores: SECOP intercambia coma y punto y coma ---


def test_contiene_tolera_coma_contra_punto_y_coma():
    fuente = "PAVIMENTACIÓN MEDIANTE REPOSICIÓN DE PAVIMENTO, ANDENES Y SILVICULTURA URBANA"
    cita = "PAVIMENTACIÓN MEDIANTE REPOSICIÓN DE PAVIMENTO; ANDENES Y SILVICULTURA URBANA"
    assert contiene(fuente, cita)


def test_normalizar_conserva_comas_dentro_de_numeros():
    """Quitar la coma de '1,000' lo convertiría en otro número."""
    assert normalizar("valor 1,000 millones") == "valor 1,000 millones"


def test_contiene_no_confunde_cifras_distintas():
    assert not contiene("el contrato es por 1,000 millones", "el contrato es por 1,500 millones")


def test_contiene_sigue_detectando_palabras_inventadas():
    """La tolerancia a puntuación no puede dejar pasar una invención."""
    fuente = "CONSTRUCCIÓN DE PAVIMENTO, ANDENES Y SILVICULTURA"
    assert not contiene(fuente, "CONSTRUCCIÓN DE AEROPUERTO; ANDENES Y SILVICULTURA")


def test_contiene_respeta_el_orden_de_las_palabras():
    assert not contiene("andenes y pavimento", "pavimento y andenes")


# --------------------------------------------------------------------------
# Validador — casos que deben pasar
# --------------------------------------------------------------------------


def test_evidencia_completa_es_valida():
    r = validar([evidencia_valida()], DIVIPOLA, CICLO, SENALES)
    assert r.valido, r.motivos


def test_cita_con_acentos_distintos_sigue_siendo_valida():
    # El modelo devolvió la cita sin tildes: no es una alucinación.
    ev = evidencia_valida(cita_textual="construccion de pavimento en la via mosquera-funza")
    assert validar([ev], DIVIPOLA, CICLO, SENALES).valido


# --------------------------------------------------------------------------
# Validador — CA-M3.1: rechaza lo que no tiene evidencia verificable
# --------------------------------------------------------------------------


def test_rechaza_insight_sin_evidencia():
    r = validar([], DIVIPOLA, CICLO, SENALES)
    assert not r.valido
    assert "no declara evidencia" in r.motivo


@pytest.mark.parametrize("campo", ["url", "fecha", "cita_textual"])
def test_rechaza_evidencia_sin_campo_obligatorio(campo):
    r = validar([evidencia_valida(**{campo: None})], DIVIPOLA, CICLO, SENALES)
    assert not r.valido
    assert f"falta {campo}" in r.motivo


def test_rechaza_url_mal_formada():
    r = validar([evidencia_valida(url="no-es-una-url")], DIVIPOLA, CICLO, SENALES)
    assert not r.valido
    assert "url mal formada" in r.motivo


def test_rechaza_fecha_no_interpretable():
    r = validar([evidencia_valida(fecha="el martes pasado")], DIVIPOLA, CICLO, SENALES)
    assert not r.valido
    assert "fecha no interpretable" in r.motivo


def test_rechaza_cita_inventada():
    """El corazón del validador: la cita no está en la fuente."""
    ev = evidencia_valida(cita_textual="CONSTRUCCIÓN DE UN AEROPUERTO INTERNACIONAL")
    r = validar([ev], DIVIPOLA, CICLO, SENALES)
    assert not r.valido
    assert "la cita no aparece" in r.motivo


def test_rechaza_senal_inexistente():
    r = validar([evidencia_valida(id_senal=999)], DIVIPOLA, CICLO, SENALES)
    assert not r.valido
    assert "no existe" in r.motivo


def test_rechaza_evidencia_sin_referencia_a_senal():
    r = validar([evidencia_valida(id_senal=None)], DIVIPOLA, CICLO, SENALES)
    assert not r.valido
    assert "no referencia ninguna" in r.motivo


def test_rechaza_senal_de_otro_municipio():
    r = validar([evidencia_valida()], "17001", CICLO, SENALES)
    assert not r.valido
    assert "no de 17001" in r.motivo


def test_rechaza_senal_de_otro_ciclo():
    r = validar([evidencia_valida()], DIVIPOLA, 3, SENALES)
    assert not r.valido
    assert "no del 3" in r.motivo


# --------------------------------------------------------------------------
# Validador — Addendum 01 D1: Bing nunca es evidencia
# --------------------------------------------------------------------------


def test_rechaza_evidencia_declarada_como_bing():
    ev = evidencia_valida(fuente="Bing")
    r = validar([ev], DIVIPOLA, CICLO, SENALES)
    assert not r.valido
    assert "no puede sustentar evidencia" in r.motivo


def test_rechaza_evidencia_que_apunta_a_senal_bing():
    """Aunque el insight declare otra fuente, la señal citada es de Bing."""
    ev = evidencia_valida(
        id_senal=2,
        fuente="SECOP II",
        cita_textual="Se está desarrollando un proyecto de 696 apartamentos.",
    )
    r = validar([ev], DIVIPOLA, CICLO, SENALES)
    assert not r.valido
    assert "es de Bing" in r.motivo


# --------------------------------------------------------------------------
# Validador — una sola evidencia mala invalida el insight (CA-M3.4)
# --------------------------------------------------------------------------


def test_una_evidencia_invalida_tumba_el_insight():
    r = validar(
        [evidencia_valida(), evidencia_valida(cita_textual="texto inventado")],
        DIVIPOLA,
        CICLO,
        SENALES,
    )
    assert not r.valido


# --------------------------------------------------------------------------
# Prefiltro
# --------------------------------------------------------------------------


def test_prefiltro_detecta_obra():
    pasa, motivo = prefiltro.clasificar("CONSTRUCCIÓN DE VÍA TERCIARIA")
    assert pasa
    assert "construccion" in motivo


def test_prefiltro_descarta_ruido_administrativo():
    pasa, motivo = prefiltro.clasificar(
        "PRESTACIÓN DE SERVICIOS PROFESIONALES PARA APOYAR LA GESTIÓN"
    )
    assert not pasa
    assert motivo == "ruido administrativo"


def test_prefiltro_descarta_objeto_vacio():
    pasa, motivo = prefiltro.clasificar("")
    assert not pasa
    assert motivo == "objeto vacio"


def test_prefiltro_es_insensible_a_acentos():
    assert prefiltro.es_obra("ADECUACION DE PARQUE")
    assert prefiltro.es_obra("adecuación de parque")


# --------------------------------------------------------------------------
# Cobertura — Addendum 01 R7
# --------------------------------------------------------------------------

DESDE, HASTA = date(2026, 1, 14), date(2026, 9, 10)


def test_cobertura_completa():
    c = cob.calcular("25286", 3, DESDE, HASTA, [DESDE, date(2026, 9, 9)])
    assert c.fraccion > 0.99
    assert not c.sin_cobertura(0.30)


def test_cobertura_truncada_se_detecta():
    """Barranquilla: sus datos paran el 2025-11-21, muy antes del ciclo 3."""
    c = cob.calcular("08001", 3, DESDE, HASTA, [])
    assert c.dias_cubiertos == 0
    assert c.sin_cobertura(0.30)


def test_cobertura_parcial_bajo_umbral():
    # Datos solo durante el primer mes de una ventana de casi 8 meses.
    c = cob.calcular("63001", 3, DESDE, HASTA, [DESDE, date(2026, 2, 10)])
    assert c.sin_cobertura(0.30)
    assert c.dias_cubiertos == 28


def test_hueco_intermedio_no_resta_cobertura():
    """Un municipio puede no contratar unas semanas sin que sea truncamiento."""
    c = cob.calcular("25286", 3, DESDE, HASTA, [DESDE, date(2026, 5, 1), date(2026, 9, 9)])
    assert not c.sin_cobertura(0.30)


def test_redistribuir_pesos_conserva_la_suma():
    pesos = {"f1": 0.22, "f2": 0.10, "f3": 0.20, "f4": 0.18, "f5": 0.10, "f6": 0.20}
    nuevos = cob.redistribuir_pesos(pesos, {"f1", "f2", "f3"})
    assert set(nuevos) == {"f4", "f5", "f6"}
    assert sum(nuevos.values()) == pytest.approx(sum(pesos.values()))


def test_redistribuir_falla_si_no_queda_ningun_factor():
    with pytest.raises(ValueError, match="ningun factor"):
        cob.redistribuir_pesos({"f1": 1.0}, {"f1"})
