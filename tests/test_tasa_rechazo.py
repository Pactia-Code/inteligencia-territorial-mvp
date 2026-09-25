"""La tasa de rechazo, desglosada por regla. F0b.3 (H-028, H-010).

Tres cosas se prueban aquí, y la segunda es la que de verdad protege la cifra:

1. Que el desglose cuenta bien.
2. **Que el mapa de motivos sigue el paso al validador.** Los códigos R1–R8 no
   están persistidos: se reconstruyen leyendo `motivo_rechazo`, que es texto
   libre. Si alguien cambia un mensaje en `validador.py`, el reparto por regla
   empezaría a devolver «no reconocido» y la tasa total seguiría cuadrando —un
   fallo silencioso justo en la cifra que F0b existe para volver citable—. Por
   eso las pruebas **hacen fallar al validador de verdad** y clasifican lo que
   emite, en vez de inventarse cadenas de motivo.
3. Que «R8 no se evaluó» no se confunde con «R8 no encontró nada».
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from territorial.reglas import tasa_rechazo as tr
from territorial.reglas.validador import Senal, validar

ANTES = tr.FECHA_R8 - timedelta(days=1)
DESPUES = tr.FECHA_R8 + timedelta(days=1)


def fila(id_corrida=10, origen="clasificador", estado="validado", motivo=None,
         fecha=ANTES):
    return {"id_corrida": id_corrida, "origen": origen,
            "estado_validacion": estado, "motivo_rechazo": motivo,
            "fecha_corrida": fecha}


# --------------------------------------------------------------------------
# El mapa de motivos, contrastado contra el validador de verdad
# --------------------------------------------------------------------------

def _senal(contenido="Contrato de pavimentación de la vía principal.",
           divipola="05001", id_ciclo=1, fuente="secop"):
    return Senal(id=1, divipola=divipola, id_ciclo=id_ciclo, fuente=fuente,
                 contenido=contenido, url="https://ejemplo.gov.co/c/1",
                 fecha_publicacion=None)


def _evidencia(**cambios):
    base = {"url": "https://ejemplo.gov.co/c/1", "fecha": "2025-03-04",
            "cita_textual": "pavimentación de la vía principal",
            "fuente": "secop", "id_senal": 1}
    base.update(cambios)
    return base


CASOS = [
    ("R1", [], {}),
    ("R2", [_evidencia(fuente="Bing")], {}),
    ("R3", [_evidencia(cita_textual="")], {}),
    ("R4", [_evidencia(url="ftp://no")], {}),
    ("R5", [_evidencia(fecha="ayer por la tarde")], {}),
    ("R6", [_evidencia(cita_textual="una frase que no está")], {}),
    ("R7", [_evidencia(id_senal=999)], {}),
]


@pytest.mark.parametrize("esperada,evidencia,extra", CASOS, ids=[c[0] for c in CASOS])
def test_el_mapa_reconoce_lo_que_el_validador_emite(esperada, evidencia, extra):
    """Se provoca cada regla de verdad y se clasifica su mensaje real."""
    resultado = validar(evidencia, "05001", 1, {1: _senal()}, **extra)
    assert not resultado.valido, "el caso debería ser rechazado"
    reglas = tr.reglas_del_motivo(resultado.motivo)
    assert esperada in reglas, f"{resultado.motivo!r} -> {reglas}"
    assert not tr.sin_clasificar(resultado.motivo), resultado.motivo


def test_el_mapa_reconoce_r8():
    """R8 va aparte: solo se evalúa si la evidencia ya pasó."""
    resultado = validar(
        [_evidencia()], "05001", 1, {1: _senal()},
        prosa=["La obra suma 4.750 metros nuevos."],
    )
    assert not resultado.valido
    assert tr.reglas_del_motivo(resultado.motivo) == ["R8"]
    assert not tr.sin_clasificar(resultado.motivo)


def test_un_motivo_desconocido_no_se_reparte_ni_se_calla():
    """Si el validador emite algo nuevo, tiene que verse, no repartirse."""
    assert tr.reglas_del_motivo("evidencia[0]: algo que nadie previó") == []
    assert tr.sin_clasificar("evidencia[0]: algo que nadie previó") == [
        "evidencia[0]: algo que nadie previó"
    ]


def test_un_insight_puede_incumplir_varias_reglas():
    motivo = ("evidencia[0]: la cita no aparece en la señal 7; "
              "evidencia[1]: url mal formada o sin esquema http(s)")
    assert tr.reglas_del_motivo(motivo) == ["R4", "R6"]


def test_las_reglas_salen_en_el_orden_del_validador():
    motivo = ("evidencia[1]: url mal formada o sin esquema http(s); "
              "evidencia[0]: falta fecha")
    assert tr.reglas_del_motivo(motivo) == ["R3", "R4"]


# --------------------------------------------------------------------------
# El denominador: solo el Clasificador
# --------------------------------------------------------------------------

def test_los_consolidados_no_entran_en_el_denominador():
    """La decisión que más mueve la cifra, y por eso tiene prueba propia."""
    filas = (
        [fila()] * 8
        + [fila(estado="rechazado", motivo="evidencia[0]: la cita no aparece en la señal 1")] * 2
        + [fila(origen="correlacionador")] * 90
    )
    [d] = tr.desglose(filas)
    assert d.evaluados == 10
    assert d.rechazados == 2
    assert d.tasa == pytest.approx(20.0)


def test_una_corrida_solo_de_consolidados_no_aparece():
    """Sin insights del Clasificador no hay tasa que calcular, ni 0 % falso."""
    assert tr.desglose([]) == []
    assert tr.desglose([fila(origen="correlacionador")]) == []


def test_la_tasa_no_divide_por_cero():
    d = tr.DesgloseCorrida(id_corrida=1, evaluados=0, rechazados=0, por_regla={})
    assert d.tasa == 0.0


# --------------------------------------------------------------------------
# R8: «no se evaluó» no es «no encontró nada»
# --------------------------------------------------------------------------

def test_una_corrida_anterior_a_r8_no_la_evaluo():
    [d] = tr.desglose([fila(fecha=ANTES)])
    assert d.r8_evaluada is False


def test_una_corrida_posterior_a_r8_si_la_evaluo():
    [d] = tr.desglose([fila(id_corrida=13, fecha=DESPUES)])
    assert d.r8_evaluada is True


def test_sin_fecha_se_asume_que_no_se_evaluo():
    """Ante la duda, la respuesta que no afirma de más."""
    assert tr.evaluaba_r8(None) is False


def test_una_fecha_sin_zona_no_revienta():
    """SQLite devuelve fechas sin zona; no puede cambiar el veredicto."""
    assert tr.evaluaba_r8(datetime(2026, 9, 25)) is True
    assert tr.evaluaba_r8(datetime(2026, 9, 20)) is False


# --------------------------------------------------------------------------
# Conteo y presentación
# --------------------------------------------------------------------------

def test_la_suma_por_regla_puede_superar_a_los_rechazados():
    """Un insight que falla por dos reglas cuenta en las dos."""
    filas = [fila(estado="rechazado", motivo=(
        "evidencia[0]: la cita no aparece en la señal 1; "
        "evidencia[1]: falta url"))]
    [d] = tr.desglose(filas)
    assert d.rechazados == 1
    assert d.por_regla == {"R3": 1, "R6": 1}
    assert sum(d.por_regla.values()) == 2


def test_las_familias_separan_fidelidad_de_cifra():
    filas = [
        fila(estado="rechazado", motivo="evidencia[0]: la cita no aparece en la señal 1"),
        fila(estado="rechazado", motivo="cifras que no están en la entrada del agente: 4750 (CA-M6.3)"),
    ]
    [d] = tr.desglose(filas)
    assert d.por_familia() == {tr.FIDELIDAD: 1, tr.CIFRA: 1}


def test_cada_regla_declara_su_familia():
    assert set(tr.REGLAS) == {f"R{i}" for i in range(1, 9)}
    assert tr.REGLAS["R8"][0] == tr.CIFRA
    assert all(tr.REGLAS[f"R{i}"][0] == tr.FIDELIDAD for i in range(1, 8))


def test_la_frase_de_h029_esta_disponible():
    """F3.1: la cifra no se publica sin ella."""
    assert "fidelidad de cita" in tr.FRASE_H029
    assert "no veracidad" in tr.FRASE_H029


def test_las_corridas_salen_ordenadas():
    filas = [fila(id_corrida=10), fila(id_corrida=7), fila(id_corrida=8)]
    assert [d.id_corrida for d in tr.desglose(filas)] == [7, 8, 10]
