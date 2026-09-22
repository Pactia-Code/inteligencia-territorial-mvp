"""Pruebas de M6 — composición y publicación del informe.

Todo aquí es determinista: no hay LLM de por medio, que es lo que CA-M6.3 exige
del lado de las cifras. Lo que más importa probar no es que el payload se arme,
sino las tres garantías que sostienen que un informe publicado siga
significando lo mismo dentro de seis meses:

  · congela **las dos** corridas, y ninguna se puede reapuntar;
  · solo hay un informe publicado por ciclo, y publicar archiva el anterior;
  · cada dato lleva su fuente y su año (CA-M6.4).
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from territorial.almacen.modelos import (
    Base,
    Ciclo,
    ContextoMunicipal,
    CorridaAgentes,
    CorridaScoring,
    Informe,
    Insight,
    Municipio,
    ScoreMunicipio,
)
from territorial.config import Config
from territorial.informes.composicion import (
    AVISO_MVP,
    campos_de_contexto,
    componer,
    resumir_fuentes,
)
from territorial.informes.publicacion import (
    PublicacionInvalida,
    informe_vigente,
    publicar,
)


def aporte(codigo: str, sin_cobertura: bool = False, **kw) -> dict:
    base = {
        "codigo": codigo, "descripcion": codigo, "crudo": 1.0,
        "normalizado": 0.5, "peso": 0.2, "aporte": 0.1,
        "sin_cobertura": sin_cobertura, "hay_dato": not sin_cobertura, "motivo": "",
    }
    base.update(kw)
    return base


@pytest.fixture
def bd():
    """Un ciclo con dos municipios, una corrida de cada tipo y sus insights."""
    motor = create_engine("sqlite://", future=True)
    Base.metadata.create_all(motor)
    with Session(motor) as s:
        s.add(Ciclo(id=3, fecha_desde=date(2026, 1, 14), fecha_hasta=date(2026, 9, 10)))
        s.add_all([
            Municipio(divipola="73001", nombre="Ibagué", departamento="Tolima"),
            Municipio(divipola="25286", nombre="Funza", departamento="Cundinamarca"),
        ])
        s.add(ContextoMunicipal(
            codigo_divipola="73001", poblacion_total=557_317, anio_poblacion=2026,
            deficit_cuantitativo=15.27, anio_deficit=2018,
        ))
        sc = CorridaScoring(
            id_ciclo=3, tipo_corrida="completa", version_scoring="v3+abc",
            ventana_desde=date(2026, 1, 14), ventana_hasta=date(2026, 9, 10),
            municipios_objetivo=["25286", "73001"],
            municipios_en_cohorte=["25286", "73001"], pesos={"F1": 1.0},
        )
        ag = CorridaAgentes(
            id_ciclo=3, tipo_corrida="completa", version_pipeline="p2",
            municipios_objetivo=["25286", "73001"],
            municipios_en_cohorte=["25286", "73001"],
        )
        s.add_all([sc, ag])
        s.flush()

        # Ibagué: solo licencias y prensa. Funza: todo.
        s.add(ScoreMunicipio(
            id_corrida=sc.id, divipola="73001", score=0.856, ranking=1,
            dias_cubiertos=3, dias_ventana=239, sin_cobertura=True,
            factores={"fraccion_informada": 0.2, "no_priorizable": False, "aportes": [
                aporte("F1", True), aporte("F2", True), aporte("F3", True),
                aporte("F4"), aporte("F5"),
            ]},
        ))
        s.add(ScoreMunicipio(
            id_corrida=sc.id, divipola="25286", score=0.595, ranking=2,
            dias_cubiertos=238, dias_ventana=239, sin_cobertura=False,
            factores={"fraccion_informada": 0.78, "no_priorizable": False, "aportes": [
                aporte("F1"), aporte("F4"), aporte("F5"),
            ]},
        ))
        s.add(Insight(
            id_corrida=ag.id, divipola="73001", categoria="obra_vial",
            resumen="Pavimentación", implicacion_inmobiliaria="Suelo habilitado",
            estado_validacion="validado", origen="clasificador",
            evidencia=[{"url": "http://x", "fecha": "2026-03-01", "cita_textual": "c"}],
        ))
        s.add(Insight(
            id_corrida=ag.id, divipola="73001", categoria="obra_vial",
            resumen="Rechazado", estado_validacion="rechazado", origen="clasificador",
        ))
        s.commit()
        yield s, sc.id, ag.id


# --------------------------------------------------------------------------
# La frase de fuentes — M6-src y M6-orden
# --------------------------------------------------------------------------


def test_la_frase_nombra_lo_que_falta():
    """Para Barranquilla, el «sin contratación» es el dato que importa."""
    assert resumir_fuentes({"licencias", "prensa"}, {"contratación"}) == (
        "licencias y prensa, sin contratación"
    )


def test_las_ausencias_se_unen_con_ni_no_con_y():
    assert resumir_fuentes({"prensa"}, {"contratación", "licencias"}) == (
        "prensa, sin contratación ni licencias"
    )


def test_las_calificaciones_no_entran_en_la_frase():
    """F6 falta en los 18 hoy: repetirlo enseñaría a saltarse la línea."""
    frase = resumir_fuentes({"contratación"}, {"calificaciones"})
    assert "calificaciones" not in frase
    assert frase == "contratación"


def test_el_orden_de_las_fuentes_es_fijo():
    """Dos municipios no pueden describir lo mismo con otro orden."""
    assert resumir_fuentes({"prensa", "contratación"}, set()) == "contratación y prensa"


# --------------------------------------------------------------------------
# CA-M6.4 — cada dato con su fuente y su año
# --------------------------------------------------------------------------


def test_cada_campo_de_contexto_lleva_fuente_y_anio():
    campos = campos_de_contexto(ContextoMunicipal(
        codigo_divipola="73001", poblacion_total=557_317, anio_poblacion=2026,
        deficit_cuantitativo=15.27, anio_deficit=2018,
    ))
    assert campos
    for c in campos:
        assert c["fuente"], c
        assert c["anio"], c


def test_el_deficit_se_declara_en_porcentaje_no_en_hogares():
    """TerriData no trae el conteo absoluto: decir «hogares» sería inventarlo."""
    campos = campos_de_contexto(ContextoMunicipal(
        codigo_divipola="73001", deficit_cuantitativo=15.27, anio_deficit=2018,
    ))
    deficit = next(c for c in campos if c["clave"] == "deficit_cuantitativo")
    assert deficit["unidad"] == "% de hogares"


def test_un_indicador_sin_dato_no_aparece():
    """Mejor ausente que con un hueco que parezca un cero."""
    campos = campos_de_contexto(ContextoMunicipal(codigo_divipola="73001"))
    assert campos == []


def test_sin_contexto_el_bloque_va_vacio():
    assert campos_de_contexto(None) == []


# --------------------------------------------------------------------------
# Composición
# --------------------------------------------------------------------------


def test_el_payload_lleva_la_marca_de_no_validado(bd):
    """CA-M6.5. Va en el payload y no en la plantilla, para que no se olvide."""
    s, sc, ag = bd
    assert componer(s, sc, ag)["aviso"] == AVISO_MVP


def test_el_payload_congela_de_que_corridas_sale(bd):
    s, sc, ag = bd
    d = componer(s, sc, ag)
    assert d["corridas"]["scoring"] == sc
    assert d["corridas"]["agentes"] == ag


def test_los_factores_viajan_con_su_fuente_en_castellano(bd):
    """M6-src: M9 no debería necesitar conocer los códigos de factor."""
    s, sc, ag = bd
    ibague = componer(s, sc, ag)["municipios"][0]
    fuentes = {f["codigo"]: f["fuente"] for f in ibague["factores"]}
    assert fuentes["F1"] == "contratación pública (SECOP II)"
    assert fuentes["F4"] == "licencias de construcción (ELIC/DANE)"
    assert fuentes["F5"] == "prensa"


def test_solo_entran_los_insights_validados(bd):
    """Un rechazado no se muestra: no pasó M3."""
    s, sc, ag = bd
    ibague = componer(s, sc, ag)["municipios"][0]
    assert [i["resumen"] for i in ibague["insights"]] == ["Pavimentación"]


def test_se_pide_calificar_solo_los_primeros(bd):
    """M9-carga: se muestran todos, se piden unos pocos."""
    s, sc, ag = bd
    d = componer(s, sc, ag, tope_calificable=1)
    assert [m["calificable"] for m in d["municipios"]] == [True, False]
    assert d["calificacion"]["pedida_hasta_puesto"] == 1
    assert d["calificacion"]["mostrados"] == 2


def test_el_hueco_de_la_prosa_va_explicito_y_vacio(bd):
    """Para que M9 sepa que existe y no lo rellene por su cuenta."""
    s, sc, ag = bd
    for m in componer(s, sc, ag)["municipios"]:
        assert m["justificacion"] is None
        assert m["sugerencias"] == []


def test_el_tope_de_municipios_sale_del_config(bd):
    s, sc, ag = bd
    d = componer(s, sc, ag, config=Config(tope_top=1))
    assert len(d["municipios"]) == 1


def test_no_se_mezclan_ciclos(bd):
    """El orden de un ciclo con el contenido de otro no es un informe."""
    s, sc, _ = bd
    otro = CorridaAgentes(
        id_ciclo=1, tipo_corrida="completa", version_pipeline="p2",
        municipios_objetivo=[], municipios_en_cohorte=[],
    )
    s.add(otro)
    s.flush()
    with pytest.raises(ValueError, match="ciclos distintos"):
        componer(s, sc, otro.id)


# --------------------------------------------------------------------------
# Publicación — A9 sin flag
# --------------------------------------------------------------------------


def test_publicar_congela_las_dos_corridas(bd):
    s, sc, ag = bd
    inf = publicar(s, sc, ag)
    assert inf.id_corrida == sc
    assert inf.id_corrida_agentes == ag
    assert inf.estado == "publicado"


def test_id_corrida_agentes_es_inmutable(bd):
    """La misma guarda que ya tenía el ranking, ahora también el contenido."""
    s, sc, ag = bd
    inf = publicar(s, sc, ag)
    with pytest.raises(ValueError, match="id_corrida_agentes es inmutable"):
        inf.id_corrida_agentes = 999


def test_id_corrida_sigue_siendo_inmutable(bd):
    s, sc, ag = bd
    inf = publicar(s, sc, ag)
    with pytest.raises(ValueError, match="id_corrida es inmutable"):
        inf.id_corrida = 999


def test_publicar_archiva_el_anterior_del_mismo_ciclo(bd):
    """Y en la misma transacción: no hay instante con dos publicados."""
    s, sc, ag = bd
    primero = publicar(s, sc, ag)
    segundo = publicar(s, sc, ag)
    assert primero.estado == "archivado"
    assert segundo.estado == "publicado"
    assert informe_vigente(s, 3).id == segundo.id


def test_la_base_impide_dos_publicados_del_mismo_ciclo(bd):
    """No depende de que el código se acuerde: es un índice único parcial."""
    s, sc, ag = bd
    publicar(s, sc, ag)
    s.add(Informe(id_ciclo=3, id_corrida=sc, id_corrida_agentes=ag,
                  contenido={}, estado="publicado"))
    with pytest.raises(IntegrityError):
        s.flush()
    s.rollback()


def test_los_archivados_no_compiten_entre_si(bd):
    """Caben tantas correcciones como hagan falta."""
    s, sc, ag = bd
    for _ in range(3):
        publicar(s, sc, ag)
    archivados = s.query(Informe).filter_by(id_ciclo=3, estado="archivado").count()
    assert archivados == 2
    assert informe_vigente(s, 3) is not None


def test_una_corrida_parcial_no_se_publica(bd):
    """Su ranking mezcla municipios de dos momentos."""
    s, sc, ag = bd
    s.get(CorridaScoring, sc).tipo_corrida = "parcial"
    s.flush()
    with pytest.raises(PublicacionInvalida, match="parcial"):
        publicar(s, sc, ag)


def test_sin_municipios_no_hay_informe(bd):
    s, sc, ag = bd
    for fila in s.query(ScoreMunicipio).all():
        fila.factores = {**fila.factores, "no_priorizable": True}
    s.flush()
    with pytest.raises(PublicacionInvalida, match="ningún municipio"):
        publicar(s, sc, ag)
