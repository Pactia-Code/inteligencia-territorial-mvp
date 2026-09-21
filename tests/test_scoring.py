"""Pruebas de M5 — scoring y priorización (Addendum 01 D4, PRD CA-M5.1 a 5.5).

M5 es capa determinista, así que todo aquí es verificable de forma exacta: no
hay LLM de por medio y las cifras del informe salen de estas funciones
(CA-M6.3).

Lo que más importa probar no es que la aritmética sume, sino que se respeten
las tres defensas de D4 contra sesgos que un score ingenuo incorporaría sin que
nadie los viera:

  · ningún factor puede depender del tamaño del municipio
  · la cobertura baja no se puntúa como cero, se redistribuye
  · la base pequeña de ELIC no puede mover el ranking
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from territorial.reglas.cobertura import Cobertura
from territorial.scoring import factores as fx
from territorial.scoring import pesos as pz
from territorial.scoring.factores import EntradaMunicipio, ValorFactor
from territorial.scoring.ranking import TOPE_TOP, puntuar_ciclo

VENTANA = 51


def cobertura(dias_cubiertos: int, dias_ventana: int = VENTANA) -> Cobertura:
    return Cobertura(
        divipola="00000",
        id_ciclo=1,
        dias_ventana=dias_ventana,
        dias_cubiertos=dias_cubiertos,
        primera_fecha=date(2025, 9, 1),
        ultima_fecha=date(2025, 9, 1),
    )


def entrada(divipola: str, **kw) -> EntradaMunicipio:
    base = {
        "divipola": divipola,
        "id_ciclo": 1,
        "cobertura": cobertura(VENTANA),
    }
    base.update(kw)
    return EntradaMunicipio(**base)


# --------------------------------------------------------------------------
# Factores uno a uno
# --------------------------------------------------------------------------


def test_f1_es_una_proporcion_no_un_conteo():
    """La propiedad central de D4: el tamaño del municipio no debe influir."""
    pequeno = fx.f1_intensidad_obra(entrada("A", n_secop=10, n_obra=5))
    grande = fx.f1_intensidad_obra(entrada("B", n_secop=1000, n_obra=500))
    assert pequeno.crudo == grande.crudo == 0.5


def test_f1_sin_registros_no_es_cero_sino_no_disponible():
    f = fx.f1_intensidad_obra(entrada("A", n_secop=0))
    assert not f.disponible
    assert f.crudo is None


def test_f2_es_un_promedio_no_una_suma():
    tres = fx.f2_ticket_medio(entrada("A", n_obra=3, valor_obra=300.0))
    treinta = fx.f2_ticket_medio(entrada("B", n_obra=30, valor_obra=3000.0))
    assert tres.crudo == treinta.crudo == 100.0


def test_f3_no_aplica_en_el_ciclo_1():
    """No hay contra qué comparar, y D4 lo saca de los pesos del ciclo 1."""
    f = fx.f3_aceleracion(entrada("A", id_ciclo=1, n_obra=10))
    assert not f.disponible
    assert "ciclo 1" in f.motivo


def test_f3_compara_tasas_diarias_no_conteos():
    e = EntradaMunicipio(
        divipola="A",
        id_ciclo=2,
        cobertura=cobertura(dias_cubiertos=10, dias_ventana=10),
        n_obra=20,  # 2,0 por día
        n_obra_previa=10,  # 1,0 por día sobre 10 días
        dias_cubiertos_previos=10,
    )
    assert fx.f3_aceleracion(e).crudo == pytest.approx(2.0)


def test_f3_sin_obra_previa_no_inventa_un_tope():
    """Dividir entre cero daría aceleración infinita. Mejor no puntuar."""
    e = EntradaMunicipio(
        divipola="A",
        id_ciclo=2,
        cobertura=cobertura(10, 10),
        n_obra=5,
        n_obra_previa=0,
        dias_cubiertos_previos=10,
    )
    f = fx.f3_aceleracion(e)
    assert not f.disponible


def test_f4_se_anula_bajo_el_piso_de_area():
    """El caso de Chigorodó: +430,63% sobre 5.768 m² es ruido, no señal."""
    f = fx.f4_dinamica_licencias(
        entrada("05172", variacion_elic_pct=430.63, area_elic_m2=5768.0)
    )
    assert not f.disponible
    assert "piso" in f.motivo
    # Decisión 2: el dato existe y se conserva. No puntúa, pero sí informa.
    assert f.hay_dato
    assert f.crudo == pytest.approx(430.63)


def test_f4_pasa_por_encima_del_piso():
    f = fx.f4_dinamica_licencias(
        entrada("08001", variacion_elic_pct=-28.47, area_elic_m2=204028.0)
    )
    assert f.disponible
    assert f.crudo == pytest.approx(-28.47)


def test_f5_es_una_tasa_sobre_la_ventana_del_ciclo():
    """El divisor es la ventana, no los días cubiertos (A7).

    Dos municipios con la misma ventana y el mismo número de noticias dan lo
    mismo, aunque uno haya contratado obra y el otro no: son fuentes
    independientes.
    """
    a = fx.f5_densidad_mediatica(
        EntradaMunicipio("A", 1, cobertura(10, VENTANA), n_noticias=5)
    )
    b = fx.f5_densidad_mediatica(
        EntradaMunicipio("B", 1, cobertura(40, VENTANA), n_noticias=5)
    )
    assert a.crudo == b.crudo == 5 / VENTANA


def test_f5_sobrevive_a_un_municipio_sin_una_sola_senal_de_secop():
    """El caso de Barranquilla en el ciclo 3: 47 noticias y 0 días cubiertos.

    Con el divisor viejo quedaba sin F5 por no haber contratado obra, que es
    el defecto A7 y contradice el principio de D4 que el módulo cita.
    """
    f = fx.f5_densidad_mediatica(
        EntradaMunicipio("08001", 3, cobertura(0, 239), n_noticias=47)
    )
    assert f.disponible
    assert f.crudo == pytest.approx(47 / 239)


def test_f6_pondera_por_gerencia_no_por_volumen_de_calificaciones():
    """Una gerencia que califica mucho no debe decidir el ranking.

    Ventas pone veinte cincos; Riesgos pone un uno. La media simple daría 4,81;
    la media de medias da 3,0, que es lo que D4 quiere decir con «ponderada por
    gerencia».
    """
    califs = [("ventas", 5.0)] * 20 + [("riesgos", 1.0)]
    e = EntradaMunicipio("A", 2, cobertura(VENTANA), calificaciones_previas=califs)
    assert fx.f6_calificaciones_previas(e).crudo == pytest.approx(3.0)


def test_f6_no_aplica_en_el_ciclo_1():
    e = EntradaMunicipio("A", 1, cobertura(VENTANA), calificaciones_previas=[("v", 5.0)])
    assert not fx.f6_calificaciones_previas(e).disponible


# --------------------------------------------------------------------------
# Cobertura: la defensa contra el truncamiento de R7
# --------------------------------------------------------------------------


def test_cobertura_baja_marca_los_factores_secop_y_solo_esos():
    """R7: el truncamiento afecta a las seis ciudades de mayor volumen.

    Marcar F1-F3 es lo que impide que Barranquilla salga con score cero en el
    ciclo 3 por falta de datos y el informe lo lea como falta de actividad.
    """
    e = entrada(
        "08001",
        cobertura=cobertura(dias_cubiertos=5),  # 9,8% de 51 días
        n_secop=100,
        n_obra=60,
        valor_obra=1000.0,
        n_noticias=10,
        variacion_elic_pct=-28.47,
        area_elic_m2=204028.0,
    )
    resultado = fx.crudos(e, umbral_cobertura=0.30)

    for codigo in ("F1", "F2", "F3"):
        assert not resultado[codigo].disponible, codigo
    # F4 y F5 no dependen de SECOP y sobreviven.
    assert resultado["F4"].disponible
    assert resultado["F5"].disponible


def test_cobertura_suficiente_no_marca_nada():
    e = entrada("08001", cobertura=cobertura(40), n_secop=100, n_obra=60, valor_obra=1.0)
    resultado = fx.crudos(e, umbral_cobertura=0.30)
    assert resultado["F1"].disponible
    assert resultado["F2"].disponible


# --------------------------------------------------------------------------
# Normalización de cohorte
# --------------------------------------------------------------------------


def test_normalizacion_lleva_a_cero_y_uno_conservando_el_orden():
    cohorte = {
        "A": {"F1": ValorFactor("F1", 0.1)},
        "B": {"F1": ValorFactor("F1", 0.5)},
        "C": {"F1": ValorFactor("F1", 0.9)},
    }
    n = fx.normalizar_cohorte(cohorte)
    assert n["A"]["F1"].normalizado == pytest.approx(0.0)
    assert n["B"]["F1"].normalizado == pytest.approx(0.5)
    assert n["C"]["F1"].normalizado == pytest.approx(1.0)


def test_empate_total_queda_en_medio_no_en_cero():
    """Sin información para distinguirlos, ni premiarlos ni castigarlos."""
    cohorte = {d: {"F1": ValorFactor("F1", 0.4)} for d in ("A", "B", "C")}
    n = fx.normalizar_cohorte(cohorte)
    assert all(n[d]["F1"].normalizado == 0.5 for d in cohorte)


def test_los_no_disponibles_no_entran_en_la_escala():
    """Si entraran como cero, estarían puntuando, y D4 lo prohíbe."""
    cohorte = {
        "A": {"F1": ValorFactor("F1", 10.0)},
        "B": {"F1": ValorFactor("F1", 20.0)},
        "C": {"F1": ValorFactor("F1", None, disponible=False, motivo="sin datos")},
    }
    n = fx.normalizar_cohorte(cohorte)
    assert n["A"]["F1"].normalizado == pytest.approx(0.0)
    assert n["B"]["F1"].normalizado == pytest.approx(1.0)
    assert n["C"]["F1"].normalizado is None
    assert not n["C"]["F1"].disponible


def test_winsorizado_de_f4_impide_que_un_extremo_aplaste_la_cohorte():
    """Ibagué marca +899,66%. Sin winsorizar fija el máximo y hunde al resto."""
    valores = [-64.93, -59.64, -28.47, 6.84, 17.06, 76.75, 85.73, 90.33, 899.66]
    recortados = fx.winsorizar(valores, 0.10, 0.90)

    assert max(recortados) < 899.66  # el extremo se recortó
    assert len(recortados) == len(valores)  # pero nadie se descartó


def test_winsorizado_no_toca_el_centro():
    valores = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    recortados = fx.winsorizar(valores, 0.10, 0.90)
    assert recortados[4:6] == [5.0, 6.0]


# --------------------------------------------------------------------------
# Pesos — CA-M5.3
# --------------------------------------------------------------------------


def test_pesos_por_defecto_suman_uno_en_los_tres_ciclos():
    for ciclo, p in pz.PESOS_POR_DEFECTO.items():
        assert sum(p.values()) == pytest.approx(1.0), f"ciclo {ciclo}"


def test_el_ciclo_1_no_pondera_f3_ni_f6():
    """D4: no hay ciclos previos, así que ninguno de los dos aplica."""
    assert "F3" not in pz.PESOS_POR_DEFECTO[1]
    assert "F6" not in pz.PESOS_POR_DEFECTO[1]


def test_un_archivo_sustituye_los_pesos_sin_tocar_codigo(tmp_path, monkeypatch):
    """Es CA-M5.3 literal."""
    ruta = tmp_path / "pesos.json"
    ruta.write_text(json.dumps({"1": {"F1": 1.0}}), encoding="utf-8")

    from territorial.config import Config

    cfg = Config(ruta_pesos=ruta)
    juego = pz.del_ciclo(1, cfg)
    assert juego.pesos == {"F1": 1.0}
    assert juego.origen == "pesos.json"
    # Los ciclos que el archivo no menciona conservan el valor por defecto.
    assert pz.del_ciclo(2, cfg).pesos == pz.PESOS_POR_DEFECTO[2]


def test_pesos_que_no_suman_uno_fallan_en_vez_de_puntuar_mal(tmp_path):
    from territorial.config import Config

    ruta = tmp_path / "pesos.json"
    ruta.write_text(json.dumps({"1": {"F1": 0.3, "F2": 0.3}}), encoding="utf-8")
    with pytest.raises(pz.PesosInvalidos, match="deberían sumar"):
        pz.cargar(Config(ruta_pesos=ruta))


def test_factor_desconocido_falla(tmp_path):
    from territorial.config import Config

    ruta = tmp_path / "pesos.json"
    ruta.write_text(json.dumps({"1": {"F9": 1.0}}), encoding="utf-8")
    with pytest.raises(pz.PesosInvalidos, match="desconocidos"):
        pz.cargar(Config(ruta_pesos=ruta))


# --------------------------------------------------------------------------
# Ranking — CA-M5.1, 5.4 y 5.5
# --------------------------------------------------------------------------


def cohorte_basica() -> list[EntradaMunicipio]:
    """Cinco municipios que solo se diferencian en intensidad de obra."""
    return [
        entrada(
            f"0000{i}",
            n_secop=100,
            n_obra=10 * i,
            valor_obra=1_000_000.0 * i,
            n_noticias=i,
            variacion_elic_pct=10.0 * i,
            area_elic_m2=50_000.0,
        )
        for i in range(1, 6)
    ]


def test_el_ranking_es_completo_y_ordenado():
    r = puntuar_ciclo(cohorte_basica(), id_ciclo=1)
    assert len(r.scores) == 5
    assert [s.ranking for s in r.scores] == [1, 2, 3, 4, 5]
    scores = [s.score for s in r.scores]
    assert scores == sorted(scores, reverse=True)


def test_top_es_fijo_de_tres():
    """CA-M5.4 — top 3 fijo, no top N por umbral."""
    r = puntuar_ciclo(cohorte_basica(), id_ciclo=1)
    assert TOPE_TOP == 3
    assert len(r.top) == 3


def test_cada_municipio_del_top_puede_listar_que_lo_empujo():
    """CA-M5.5 literal."""
    r = puntuar_ciclo(cohorte_basica(), id_ciclo=1)
    for s in r.top:
        empujaron = s.factores_que_empujaron
        assert empujaron, f"{s.divipola} no explica su score"
        # De mayor a menor aporte, que es como lo lee el informe.
        aportes = [a.aporte for a in empujaron]
        assert aportes == sorted(aportes, reverse=True)


def test_el_score_es_la_suma_de_sus_aportes():
    """Explicable factor por factor: CA-M5.1 no admite un score opaco."""
    r = puntuar_ciclo(cohorte_basica(), id_ciclo=1)
    for s in r.scores:
        assert s.score == pytest.approx(sum(a.aporte for a in s.aportes))


def test_el_peso_de_un_factor_sin_cobertura_se_redistribuye():
    """D4: nunca se puntúa cero. El municipio compite con lo que sí tiene."""
    cohorte = cohorte_basica()
    # Al tercero le quitamos ELIC: pierde F4, que en el ciclo 1 pesa 30%.
    cohorte[2] = entrada(
        cohorte[2].divipola,
        n_secop=100,
        n_obra=30,
        valor_obra=3_000_000.0,
        n_noticias=3,
        variacion_elic_pct=None,
        area_elic_m2=None,
    )
    r = puntuar_ciclo(cohorte, id_ciclo=1)
    afectado = next(s for s in r.scores if s.divipola == cohorte[2].divipola)

    f4 = next(a for a in afectado.aportes if a.codigo == "F4")
    assert f4.sin_cobertura
    assert f4.aporte == 0.0

    # Los pesos efectivos de los demás siguen sumando 1: el 30% de F4 se
    # repartió, no desapareció.
    efectivos = sum(a.peso for a in afectado.aportes if not a.sin_cobertura)
    assert efectivos == pytest.approx(1.0)


def test_el_orden_es_reproducible_ante_empate():
    """H4 pide que dos corridas del mismo ciclo den el mismo top 3."""
    iguales = [
        entrada(d, n_secop=10, n_obra=5, valor_obra=100.0, n_noticias=1,
                variacion_elic_pct=5.0, area_elic_m2=50_000.0)
        for d in ("05001", "08001", "11001")
    ]
    primero = puntuar_ciclo(iguales, id_ciclo=1)
    segundo = puntuar_ciclo(list(reversed(iguales)), id_ciclo=1)
    assert [s.divipola for s in primero.scores] == [s.divipola for s in segundo.scores]


def test_entradas_de_otro_ciclo_se_rechazan():
    mezcla = [entrada("05001"), EntradaMunicipio("08001", 2, cobertura(VENTANA))]
    with pytest.raises(ValueError, match="otro ciclo"):
        puntuar_ciclo(mezcla, id_ciclo=1)


def test_municipio_sin_ningun_factor_puntuable_no_revienta():
    """Sale con score cero, pero con el motivo escrito en cada factor.

    Tras A7 hace falta también una ventana de cero días para llegar aquí: con
    ventana positiva, F5 siempre se puede calcular aunque no haya ni una
    noticia, porque el divisor ya no depende de SECOP.
    """
    mudo = entrada("05001", cobertura=cobertura(0, dias_ventana=0), n_secop=0)
    r = puntuar_ciclo([mudo, *cohorte_basica()], id_ciclo=1)
    s = next(x for x in r.scores if x.divipola == "05001")
    assert s.score == 0.0
    assert all(a.sin_cobertura for a in s.aportes)
    assert all(a.motivo for a in s.aportes)


# --------------------------------------------------------------------------
# Umbral de información — la guarda que no está en D4
# --------------------------------------------------------------------------


def test_la_fraccion_informada_refleja_cuantos_datos_sostienen_el_score():
    completo = entrada(
        "05001", n_secop=100, n_obra=50, valor_obra=1e6, n_noticias=5,
        variacion_elic_pct=50.0, area_elic_m2=50_000.0,
    )
    # Sin ELIC pierde F4, que en el ciclo 1 pesa el 30%.
    parcial = entrada(
        "08001", n_secop=100, n_obra=40, valor_obra=1e6, n_noticias=4,
        variacion_elic_pct=None, area_elic_m2=None,
    )
    r = puntuar_ciclo([completo, parcial], id_ciclo=1)
    por_muni = {s.divipola: s for s in r.scores}
    assert por_muni["05001"].fraccion_informada == pytest.approx(1.0)
    assert por_muni["08001"].fraccion_informada == pytest.approx(0.70)


# --------------------------------------------------------------------------
# Decisión 2 de Analítica — el piso de ELIC castigaba dos veces
# --------------------------------------------------------------------------


def test_el_piso_de_elic_no_descuenta_de_la_fraccion_informada():
    """Tener poca área no es lo mismo que no tener dato.

    Carepa, Turbo y Chigorodó salían al 62% en los ciclos 2 y 3 porque el piso
    de ELIC les quitaba F4 dos veces: del score, que es lo correcto, y de la
    fracción informada, que no. El municipio sí sabe cuánto se licenció; lo que
    no tiene es una base suficiente para que el porcentaje signifique algo.
    """
    comun = {"n_secop": 100, "n_obra": 40, "valor_obra": 1e6, "n_noticias": 4}
    bajo_el_piso = entrada("05147", variacion_elic_pct=273.15, area_elic_m2=4239.0, **comun)
    sin_elic = entrada("08001", variacion_elic_pct=None, area_elic_m2=None, **comun)
    sobre_el_piso = entrada("11001", variacion_elic_pct=20.0, area_elic_m2=50_000.0, **comun)

    r = puntuar_ciclo([bajo_el_piso, sin_elic, sobre_el_piso], id_ciclo=1)
    por_muni = {s.divipola: s for s in r.scores}

    assert por_muni["05147"].fraccion_informada == pytest.approx(1.0)
    # El contraste es el punto: sin dato sí se descuenta el 30% de F4.
    assert por_muni["08001"].fraccion_informada == pytest.approx(0.70)


def test_el_piso_de_elic_sigue_sin_puntuar():
    """La defensa de D4 queda intacta: informar no es puntuar.

    Si el crudo bajo el piso llegara al score, volveríamos al problema que el
    piso existe para evitar — tres municipios pequeños copando el top 3 por el
    ruido de una sola licencia.
    """
    comun = {"n_secop": 100, "n_obra": 40, "valor_obra": 1e6, "n_noticias": 4}
    r = puntuar_ciclo(
        [
            entrada("05147", variacion_elic_pct=273.15, area_elic_m2=4239.0, **comun),
            entrada("11001", variacion_elic_pct=20.0, area_elic_m2=50_000.0, **comun),
        ],
        id_ciclo=1,
    )
    carepa = next(s for s in r.scores if s.divipola == "05147")
    f4 = next(a for a in carepa.aportes if a.codigo == "F4")

    assert f4.sin_cobertura
    assert f4.aporte == 0.0
    assert f4.hay_dato
    assert f4.crudo == pytest.approx(273.15)
    # Su 30% se redistribuyó, igual que un factor ausente.
    assert sum(a.peso for a in carepa.aportes if not a.sin_cobertura) == pytest.approx(1.0)


def test_el_crudo_bajo_el_piso_no_fija_la_escala_de_la_cohorte():
    """+430,63% no puede aplastar a los demás por la puerta de atrás."""
    cohorte = {
        "05172": {"F4": fx._no_puntuable("F4", 430.63, "bajo el piso")},
        "08001": {"F4": ValorFactor("F4", 10.0)},
        "11001": {"F4": ValorFactor("F4", 20.0)},
    }
    n = fx.normalizar_cohorte(cohorte)
    assert n["08001"]["F4"].normalizado == pytest.approx(0.0)
    assert n["11001"]["F4"].normalizado == pytest.approx(1.0)
    assert n["05172"]["F4"].normalizado is None


def test_el_caso_armenia_no_puede_ganar_con_un_solo_factor():
    """El hallazgo del ciclo 3: 0 días de cobertura y score perfecto.

    Armenia solo conserva F4, que pasa a valer el 100% del score. Sigue en el
    ranking con su posición real, pero no ocupa un puesto del top 3.
    """
    armenia = EntradaMunicipio(
        divipola="63001",
        id_ciclo=3,
        cobertura=cobertura(dias_cubiertos=0, dias_ventana=239),
        variacion_elic_pct=808.2,
        area_elic_m2=498_013.0,
    )
    solidos = [
        EntradaMunicipio(
            divipola=f"2528{i}",
            id_ciclo=3,
            cobertura=cobertura(238, 239),
            n_secop=100, n_obra=10 * i, valor_obra=1e6 * i, n_noticias=i,
            n_obra_previa=10, dias_cubiertos_previos=100,
            variacion_elic_pct=10.0, area_elic_m2=50_000.0,
        )
        for i in range(1, 5)
    ]
    r = puntuar_ciclo([armenia, *solidos], id_ciclo=3)
    por_muni = {s.divipola: s for s in r.scores}

    assert por_muni["63001"].no_priorizable
    assert "63001" not in {s.divipola for s in r.top}
    # No se le puso cero: sigue puntuado y rankeado, como manda D4.
    assert por_muni["63001"].score > 0
    assert por_muni["63001"].ranking is not None
    # El top 3 se completa con los siguientes, no se queda corto.
    assert len(r.top) == 3


def test_el_excluido_dice_por_que():
    """El informe tiene que poder explicarlo: CA-M6.1 exige justificación."""
    armenia = EntradaMunicipio(
        "63001", 3, cobertura(0, 239), variacion_elic_pct=808.2, area_elic_m2=498_013.0
    )
    otro = EntradaMunicipio(
        "25286", 3, cobertura(238, 239), n_secop=50, n_obra=25, valor_obra=1e6,
        n_noticias=3, n_obra_previa=10, dias_cubiertos_previos=100,
        variacion_elic_pct=20.0, area_elic_m2=50_000.0,
    )
    r = puntuar_ciclo([armenia, otro], id_ciclo=3)
    excluidos = r.excluidos_del_top
    assert excluidos
    assert "top 3" in excluidos[0].motivo_no_priorizable
    assert "FUERA DEL TOP 3" in excluidos[0].explicar()


def test_el_umbral_es_configurable():
    from territorial.config import Config

    armenia = EntradaMunicipio(
        "63001", 3, cobertura(0, 239), variacion_elic_pct=808.2, area_elic_m2=498_013.0
    )
    otro = EntradaMunicipio(
        "25286", 3, cobertura(238, 239), n_secop=50, n_obra=25, valor_obra=1e6,
        n_noticias=3, n_obra_previa=10, dias_cubiertos_previos=100,
        variacion_elic_pct=20.0, area_elic_m2=50_000.0,
    )
    # Con el umbral en cero, la guarda se apaga y vuelve el comportamiento
    # literal de D4.
    r = puntuar_ciclo([armenia, otro], id_ciclo=3, config=Config(umbral_informacion=0.0))
    assert not any(s.no_priorizable for s in r.scores)


def test_los_ciclos_1_y_2_no_se_ven_afectados_por_la_guarda():
    """Medido sobre el snapshot: allí la información va del 62% al 100%."""
    r = puntuar_ciclo(cohorte_basica(), id_ciclo=1)
    assert not any(s.no_priorizable for s in r.scores)
    assert len(r.top) == TOPE_TOP


def test_el_tamano_no_decide_el_ranking():
    """La prueba que resume D4.

    Dos municipios con la misma composición y distinto tamaño tienen que
    empatar. Si esto falla, el score mide tamaño de ciudad y el MVP habría
    necesitado TerriData.
    """
    pequeno = entrada(
        "05147", n_secop=42, n_obra=20, valor_obra=20 * 5_000_000.0,
        n_noticias=1, variacion_elic_pct=50.0, area_elic_m2=50_000.0,
    )
    grande = entrada(
        "08001", n_secop=4200, n_obra=2000, valor_obra=2000 * 5_000_000.0,
        n_noticias=100, variacion_elic_pct=50.0, area_elic_m2=50_000.0,
    )
    # Misma proporción de obra, mismo ticket medio, misma variación ELIC.
    # F5 difiere a propósito: la densidad mediática sí es una tasa distinta.
    r = puntuar_ciclo([pequeno, grande], id_ciclo=1)
    por_muni = {s.divipola: s for s in r.scores}

    for codigo in ("F1", "F2", "F4"):
        a = next(x for x in por_muni["05147"].aportes if x.codigo == codigo)
        b = next(x for x in por_muni["08001"].aportes if x.codigo == codigo)
        assert a.crudo == pytest.approx(b.crudo), codigo
        assert a.aporte == pytest.approx(b.aporte), codigo
