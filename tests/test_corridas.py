"""Pruebas de la persistencia append-only del scoring.

**Escritas antes de reescribir `guardar()`**, contra el fallo real que dejó la
migración `41d077a78426`. El módulo era el único de M5 sin cobertura, y las 106
pruebas siguieron en verde mientras estaba roto: la red no cubría la única
pieza que toca la base.

Lo que se protege aquí no es aritmética, es una propiedad: **un score solo es
comparable dentro de su corrida**. Mientras vivió bajo `uq_score_ciclo_municipio`
cualquier recálculo pisaba el ranking anterior en su sitio, y un informe
publicado empezaba a mostrar un orden distinto del que las gerencias
calificaron. Eso rompe H4, que es bloqueante.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from territorial.almacen.modelos import (
    Base,
    Ciclo,
    CorridaScoring,
    Informe,
    Municipio,
)
from territorial.almacen.modelos import ScoreMunicipio as FilaScore
from territorial.scoring.persistencia import VERSION_ALGORITMO, guardar
from territorial.scoring.pesos import JuegoDePesos
from territorial.scoring.ranking import Aporte, ResultadoCiclo, ScoreMunicipio

CICLO = 1
LOS_TRES = ["05001", "08001", "11001"]


@pytest.fixture
def bd():
    motor = create_engine("sqlite://")
    Base.metadata.create_all(motor)
    with Session(motor) as s:
        for i, d in enumerate(LOS_TRES):
            s.add(Municipio(divipola=d, nombre=f"Muni{i}", departamento="Dep"))
        s.add(Ciclo(id=CICLO, fecha_desde=date(2025, 9, 1), fecha_hasta=date(2025, 10, 22)))
        s.commit()
        yield s


def aporte(codigo: str = "F1") -> Aporte:
    return Aporte(
        codigo=codigo,
        descripcion="d",
        crudo=1.0,
        normalizado=1.0,
        peso=1.0,
        aporte=1.0,
        sin_cobertura=False,
        motivo="",
    )


def score(divipola: str, valor: float, puesto: int, ultima: date | None) -> ScoreMunicipio:
    return ScoreMunicipio(
        divipola=divipola,
        id_ciclo=CICLO,
        score=valor,
        aportes=[aporte()],
        dias_cubiertos=51,
        dias_ventana=51,
        sin_cobertura=False,
        fraccion_informada=1.0,
        ranking=puesto,
        ultima_fecha_captura=ultima,
    )


def resultado(scores: list[ScoreMunicipio]) -> ResultadoCiclo:
    return ResultadoCiclo(
        id_ciclo=CICLO,
        scores=scores,
        juego_pesos=JuegoDePesos(CICLO, {"F1": 1.0}, "prueba"),
    )


def cohorte_completa(ultimas: dict[str, date | None] | None = None) -> ResultadoCiclo:
    u = ultimas or dict.fromkeys(LOS_TRES, date(2025, 10, 20))
    return resultado(
        [score(d, 1.0 - i / 10, i + 1, u[d]) for i, d in enumerate(LOS_TRES)]
    )


# --------------------------------------------------------------------------
# Append-only: nada se sobrescribe
# --------------------------------------------------------------------------


def test_guardar_crea_una_corrida_y_cuelga_los_scores_de_ella(bd):
    corrida = guardar(bd, cohorte_completa())
    bd.commit()

    assert corrida.id is not None
    assert corrida.id_ciclo == CICLO
    filas = bd.scalars(select(FilaScore)).all()
    assert len(filas) == 3
    assert {f.id_corrida for f in filas} == {corrida.id}


def test_una_segunda_corrida_no_pisa_la_primera(bd):
    """La propiedad central. Con el esquema viejo esto era imposible."""
    primera = guardar(bd, cohorte_completa())
    bd.commit()
    puestos_originales = {
        f.divipola: f.ranking
        for f in bd.scalars(select(FilaScore).where(FilaScore.id_corrida == primera.id)).all()
    }

    # Un recálculo que da el orden invertido.
    invertido = resultado(
        [score(d, i / 10, 3 - i, date(2025, 10, 20)) for i, d in enumerate(LOS_TRES)]
    )
    segunda = guardar(bd, invertido)
    bd.commit()

    assert segunda.id != primera.id
    assert bd.query(CorridaScoring).count() == 2
    assert bd.query(FilaScore).count() == 6

    # La primera corrida sigue exactamente como estaba.
    ahora = {
        f.divipola: f.ranking
        for f in bd.scalars(select(FilaScore).where(FilaScore.id_corrida == primera.id)).all()
    }
    assert ahora == puestos_originales


# --------------------------------------------------------------------------
# tipo_corrida se calcula, no se declara
# --------------------------------------------------------------------------


def test_cohorte_completa_se_marca_completa(bd):
    corrida = guardar(bd, cohorte_completa())
    bd.commit()
    assert corrida.tipo_corrida == "completa"
    assert sorted(corrida.municipios_objetivo) == LOS_TRES
    assert sorted(corrida.municipios_en_cohorte) == LOS_TRES


def test_cohorte_parcial_se_marca_parcial_sin_fallar(bd):
    """No falla ni se salta: inserta sus filas marcadas y deja constancia."""
    parcial = resultado([score(LOS_TRES[0], 1.0, 1, date(2025, 10, 20))])
    corrida = guardar(bd, parcial)
    bd.commit()

    assert corrida.tipo_corrida == "parcial"
    assert corrida.municipios_en_cohorte == [LOS_TRES[0]]
    assert sorted(corrida.municipios_objetivo) == LOS_TRES
    assert bd.query(FilaScore).count() == 1


def test_el_tipo_es_reverificable_sin_consultar_la_tabla_actual(bd):
    """El punto entero de guardar las dos listas.

    Se relee desde la base, no del objeto en memoria: lo que se verifica es que
    `tipo_corrida` se puede **recalcular** a partir de lo persistido aunque la
    tabla `municipio` haya cambiado desde entonces. Si solo se guardara la
    cohorte, una corrida vieja quedaría sin forma de auditarse.
    """
    id_corrida = guardar(bd, cohorte_completa()).id
    bd.commit()
    bd.expunge_all()

    # Alguien añade el municipio 19 tres semanas después.
    bd.add(Municipio(divipola="76001", nombre="Nuevo", departamento="Dep"))
    bd.commit()

    releida = bd.get(CorridaScoring, id_corrida)
    assert releida.tipo_corrida == "completa"
    # La marca se recalcula con los datos del momento, no con la tabla de hoy.
    recalculado = (
        "completa"
        if set(releida.municipios_en_cohorte) >= set(releida.municipios_objetivo)
        else "parcial"
    )
    assert recalculado == releida.tipo_corrida
    # Y contra la tabla actual daría lo contrario, que es justo el error que
    # guardar las dos listas evita.
    hoy = {d for (d,) in bd.execute(select(Municipio.divipola)).all()}
    assert not set(releida.municipios_en_cohorte) >= hoy


# --------------------------------------------------------------------------
# fecha_corte_cohorte — el MÍNIMO, y el criterio conservador
# --------------------------------------------------------------------------


def test_el_corte_es_el_minimo_no_el_maximo(bd):
    """Con capturas mixtas, frescas y viejas.

    Es el test que pediste: decir junio cuando la contratación de un municipio
    se corta en noviembre haría comparar dos corridas como equivalentes sin que
    nada en la auditoría lo delate.
    """
    corrida = guardar(
        bd,
        cohorte_completa(
            {
                "05001": date(2026, 6, 11),  # fresco
                "08001": date(2025, 11, 21),  # truncado — este manda
                "11001": date(2026, 1, 15),
            }
        ),
    )
    bd.commit()

    assert corrida.fecha_corte_cohorte == date(2025, 11, 21)
    assert corrida.fecha_corte_cohorte != date(2026, 6, 11)


def test_un_municipio_sin_fecha_no_aniquila_el_corte(bd):
    """El corte se calcula sobre los que tienen fecha, y los que no se declaran.

    Propagar la ausencia al conjunto dejaría el ciclo 3 siempre en NULL por
    Barranquilla, Armenia y Cartagena, que no están ciegas: tienen noticias
    hasta agosto, lo que no tienen es contratación. Sería el mismo error que el
    defecto de F5, y volvería inútil el campo en un tercio de los ciclos.
    """
    corrida = guardar(
        bd,
        cohorte_completa(
            {"05001": date(2026, 6, 11), "08001": None, "11001": date(2026, 1, 15)}
        ),
    )
    bd.commit()

    assert corrida.fecha_corte_cohorte == date(2026, 1, 15)
    assert corrida.municipios_sin_fecha == ["08001"]


def test_sin_ninguna_fecha_el_corte_si_es_nulo(bd):
    """NULL queda para el caso real: nadie aportó nada."""
    corrida = guardar(bd, cohorte_completa(dict.fromkeys(LOS_TRES, None)))
    bd.commit()
    assert corrida.fecha_corte_cohorte is None
    assert corrida.municipios_sin_fecha == LOS_TRES


def test_cada_fila_guarda_su_propia_ultima_fecha(bd):
    """La del municipio, no la de la cohorte."""
    guardar(
        bd,
        cohorte_completa(
            {
                "05001": date(2026, 6, 11),
                "08001": date(2025, 11, 21),
                "11001": date(2026, 1, 15),
            }
        ),
    )
    bd.commit()
    por_muni = {f.divipola: f.ultima_fecha_captura for f in bd.scalars(select(FilaScore)).all()}
    assert por_muni["05001"] == date(2026, 6, 11)
    assert por_muni["08001"] == date(2025, 11, 21)


# --------------------------------------------------------------------------
# version_scoring y pesos
# --------------------------------------------------------------------------


def test_la_version_lleva_algoritmo_y_huella_de_pesos(bd):
    corrida = guardar(bd, cohorte_completa())
    bd.commit()
    algoritmo, _, huella = corrida.version_scoring.partition("+")
    assert algoritmo == VERSION_ALGORITMO
    assert len(huella) == 8


def test_pesos_distintos_dan_versiones_distintas(bd):
    a = guardar(bd, cohorte_completa())
    bd.commit()

    otro = cohorte_completa()
    otro = ResultadoCiclo(
        id_ciclo=CICLO,
        scores=otro.scores,
        juego_pesos=JuegoDePesos(CICLO, {"F1": 0.5, "F2": 0.5}, "prueba"),
    )
    b = guardar(bd, otro)
    bd.commit()

    assert a.version_scoring != b.version_scoring


def test_los_pesos_se_guardan_verbatim_no_solo_su_hash(bd):
    """Un hash dice que algo cambió, no qué cambió."""
    corrida = guardar(bd, cohorte_completa())
    bd.commit()
    assert corrida.pesos == {"F1": 1.0}


# --------------------------------------------------------------------------
# El informe lee su propia corrida, y no se reapunta
# --------------------------------------------------------------------------


def test_una_corrida_parcial_no_altera_lo_que_lee_un_informe_publicado(bd):
    """El test que pediste. Es la razón entera de este cambio."""
    publicada = guardar(bd, cohorte_completa())
    bd.commit()

    informe = Informe(
        id_ciclo=CICLO,
        id_corrida=publicada.id,
        estado="publicado",
    )
    bd.add(informe)
    bd.commit()

    top_publicado = [
        f.divipola
        for f in bd.scalars(
            select(FilaScore)
            .where(FilaScore.id_corrida == informe.id_corrida)
            .order_by(FilaScore.ranking)
        ).all()
    ]

    # Llega una corrida parcial que invierte el orden del municipio que tocó.
    guardar(bd, resultado([score(LOS_TRES[2], 99.0, 1, date(2025, 10, 20))]))
    bd.commit()

    top_despues = [
        f.divipola
        for f in bd.scalars(
            select(FilaScore)
            .where(FilaScore.id_corrida == informe.id_corrida)
            .order_by(FilaScore.ranking)
        ).all()
    ]
    assert top_despues == top_publicado


def test_id_corrida_de_un_informe_no_se_puede_reescribir(bd):
    """Ataca la restricción directamente: M6 no existe, así que un test contra
    su comportamiento quedaría vacío pasando en verde."""
    a = guardar(bd, cohorte_completa())
    bd.commit()
    b = guardar(bd, cohorte_completa())
    bd.commit()

    informe = Informe(id_ciclo=CICLO, id_corrida=a.id)
    bd.add(informe)
    bd.commit()

    with pytest.raises(ValueError, match="inmutable"):
        informe.id_corrida = b.id


def test_el_estado_del_informe_solo_admite_publicado_o_archivado(bd):
    from sqlalchemy.exc import IntegrityError

    corrida = guardar(bd, cohorte_completa())
    bd.commit()
    bd.add(Informe(id_ciclo=CICLO, id_corrida=corrida.id, estado="loquesea"))
    with pytest.raises(IntegrityError):
        bd.commit()


# --------------------------------------------------------------------------
# El orquestador encadena el scoring — la mentira original de ciclo.py
# --------------------------------------------------------------------------


def test_procesar_ciclo_encadena_el_scoring(bd, monkeypatch):
    """El docstring de `ciclo.py` decía «→ M5 Scoring» y no lo hacía.

    Se sustituyen las piezas de scoring por dobles para no depender de que haya
    señales cargadas: lo que se verifica es el cableado, no el cálculo.
    """
    from territorial import ciclo as mod

    llamadas = {}

    def fake_entradas(sesion, id_ciclo, cfg=None):
        llamadas["entradas"] = id_ciclo
        return ["lo que sea"]

    def fake_puntuar(entradas, id_ciclo, cfg=None, cortes_por_fuente=None):
        llamadas["puntuar"] = id_ciclo
        return cohorte_completa()

    monkeypatch.setattr(mod, "entradas_del_ciclo", fake_entradas)
    monkeypatch.setattr(mod, "puntuar_ciclo", fake_puntuar)

    # Sin municipios que procesar: solo interesa la cola de la función.
    resumen = mod.procesar_ciclo(bd, CICLO, solo=["00000"])
    bd.commit()

    assert llamadas == {"entradas": CICLO, "puntuar": CICLO}
    assert resumen.error_scoring is None
    assert resumen.corrida is not None
    assert bd.query(CorridaScoring).count() == 1


def test_si_el_scoring_falla_no_se_pierde_lo_que_costo_tokens(bd, monkeypatch):
    """Puntuar va después de gastar en M2 y M4. Que un fallo ahí tirara el
    resultado de los agentes sería el peor cambio posible."""
    from territorial import ciclo as mod

    def revienta(*_a, **_k):
        raise RuntimeError("scoring roto")

    monkeypatch.setattr(mod, "entradas_del_ciclo", revienta)

    resumen = mod.procesar_ciclo(bd, CICLO, solo=["00000"])

    assert resumen.corrida is None
    assert "scoring roto" in resumen.error_scoring
    assert bd.query(CorridaScoring).count() == 0


# --------------------------------------------------------------------------
# corte_por_fuente — informativo, no alimenta factores
# --------------------------------------------------------------------------


def test_el_corte_por_fuente_se_persiste_tal_cual(bd):
    cortes = {
        "SECOP II": {"corte": "2025-11-21", "municipios_con_fecha": 18},
        "RSS": {"corte": "2025-10-26", "municipios_con_fecha": 14},
        "Bing": {"corte": None, "municipios_con_fecha": 0},
    }
    base = cohorte_completa()
    corrida = guardar(
        bd,
        ResultadoCiclo(
            id_ciclo=CICLO,
            scores=base.scores,
            juego_pesos=base.juego_pesos,
            corte_por_fuente=cortes,
        ),
    )
    bd.commit()
    assert corrida.corte_por_fuente == cortes


def test_el_corte_por_fuente_no_altera_el_corte_de_cohorte(bd):
    """Es informativo. Que RSS llegue más lejos no mueve la comparabilidad,
    que se mide sobre SECOP porque de ahí salen F1, F2 y F3."""
    base = cohorte_completa(
        {
            "05001": date(2025, 11, 21),
            "08001": date(2026, 1, 15),
            "11001": date(2026, 1, 20),
        }
    )
    corrida = guardar(
        bd,
        ResultadoCiclo(
            id_ciclo=CICLO,
            scores=base.scores,
            juego_pesos=base.juego_pesos,
            corte_por_fuente={"RSS": {"corte": "2026-08-01", "municipios_con_fecha": 3}},
        ),
    )
    bd.commit()

    # El corte sigue siendo el mínimo de SECOP, no el de RSS.
    assert corrida.fecha_corte_cohorte == date(2025, 11, 21)
    assert corrida.corte_por_fuente["RSS"]["corte"] == "2026-08-01"


def test_sin_cortes_por_fuente_el_campo_queda_vacio_no_nulo(bd):
    corrida = guardar(bd, cohorte_completa())
    bd.commit()
    assert corrida.corte_por_fuente == {}


# --------------------------------------------------------------------------
# A5 — valores crudos, para construir la escala absoluta en la semana 8
# --------------------------------------------------------------------------


def test_los_valores_crudos_se_guardan_en_plano(bd):
    guardar(bd, cohorte_completa())
    bd.commit()
    fila = bd.scalars(select(FilaScore)).first()
    assert fila.valores_crudos == {"F1": 1.0}


def test_la_columna_plana_y_el_array_anidado_son_el_mismo_dato(bd):
    """Se duplican a propósito, y por eso hay que comprobar que no divergen.

    La columna plana existe para que construir la escala absoluta sea un SELECT
    en vez de un script. Si alguien cambia uno de los dos caminos sin el otro,
    esta prueba falla.
    """
    guardar(bd, cohorte_completa())
    bd.commit()

    for fila in bd.scalars(select(FilaScore)).all():
        desde_anidado = {
            a["codigo"]: a["crudo"]
            for a in fila.factores["aportes"]
            if a["crudo"] is not None
        }
        assert fila.valores_crudos == desde_anidado


def test_un_factor_sin_valor_no_ensucia_la_columna_plana(bd):
    """Un factor no disponible tiene `crudo=None`: no entra."""
    base = cohorte_completa()
    sin_dato = Aporte(
        codigo="F4", descripcion="d", crudo=None, normalizado=None,
        peso=0.0, aporte=0.0, sin_cobertura=True, motivo="sin ELIC",
    )
    scores = [
        ScoreMunicipio(
            divipola=s.divipola, id_ciclo=CICLO, score=s.score,
            aportes=[*s.aportes, sin_dato], dias_cubiertos=51, dias_ventana=51,
            sin_cobertura=False, ranking=s.ranking,
            ultima_fecha_captura=s.ultima_fecha_captura,
        )
        for s in base.scores
    ]
    guardar(bd, resultado(scores))
    bd.commit()

    fila = bd.scalars(select(FilaScore)).first()
    assert "F4" not in fila.valores_crudos
    assert fila.valores_crudos == {"F1": 1.0}
