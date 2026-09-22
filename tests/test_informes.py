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

import json
from datetime import date
from pathlib import Path

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
    Usuario,
)
from territorial.config import Config
from territorial.informes.composicion import (
    AVISO_MVP,
    agrupar_por_fuente,
    campos_de_contexto,
    componer,
    gerencias_autorizadas,
    resumir_fuentes,
)
from territorial.informes.gerencias import GerenciasInvalidas, cargar_prd
from territorial.informes.publicacion import (
    PublicacionInvalida,
    ciclos_publicables,
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
        # Tres gerencias activas (una con dos personas), una desactivada y un
        # administrador: el denominador de H2 tiene que ser exactamente tres.
        s.add_all([
            Usuario(id_gerencia="comercial", nombre="A", correo="a@p.co"),
            Usuario(id_gerencia="comercial", nombre="A2", correo="a2@p.co"),
            Usuario(id_gerencia="desarrollo", nombre="B", correo="b@p.co"),
            Usuario(id_gerencia="activos", nombre="C", correo="c@p.co"),
            Usuario(id_gerencia="antigua", nombre="D", correo="d@p.co", activo=False),
            Usuario(id_gerencia="analitica", nombre="E", correo="e@p.co",
                    rol="administrador"),
        ])
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


# --------------------------------------------------------------------------
# Aportes por fuente — el mismo dato en dos niveles, que no pueden divergir
# --------------------------------------------------------------------------


def test_el_aporte_por_fuente_es_la_suma_de_sus_factores():
    """La garantía que pidió Analítica: los dos niveles no pueden divergir.

    La vista de ciclo pinta por fuente y el desglose audita factor a factor. Si
    el agregado no cuadrara con sus partes, el informe diría dos cosas distintas
    sobre el mismo score y no habría forma de saber cuál.
    """
    factores = [
        aporte("F1", aporte=0.20), aporte("F2", aporte=0.07),
        aporte("F3", aporte=0.04), aporte("F5", aporte=0.14),
    ]
    por_fuente = {f["fuente"]: f for f in agrupar_por_fuente(factores)}
    assert por_fuente["contratación"]["aporte"] == pytest.approx(0.31)
    assert por_fuente["prensa"]["aporte"] == pytest.approx(0.14)
    assert sum(f["aporte"] for f in por_fuente.values()) == pytest.approx(
        sum(f["aporte"] for f in factores)
    )


def test_cuadra_tambien_sobre_el_payload_completo(bd):
    """No solo en la función suelta: en lo que de verdad se publica."""
    s, sc, ag = bd
    for m in componer(s, sc, ag)["municipios"]:
        suma_factores = sum(
            f["aporte"] for f in m["factores"] if not f["sin_cobertura"]
        )
        suma_fuentes = sum(f["aporte"] for f in m["aportes_por_fuente"])
        assert suma_fuentes == pytest.approx(suma_factores), m["nombre"]


def test_una_fuente_con_un_factor_vivo_no_cuenta_como_sin_datos():
    """F1 truncado y F2 con cobertura siguen siendo contratación, y la hay."""
    factores = [aporte("F1", sin_cobertura=True), aporte("F2", aporte=0.1)]
    contratacion = agrupar_por_fuente(factores)[0]
    assert contratacion["fuente"] == "contratación"
    assert not contratacion["sin_datos"]
    assert contratacion["aporte"] == pytest.approx(0.1)


def test_las_fuentes_sin_datos_se_muestran_al_final_y_no_se_omiten():
    """§3.4 del design system: la ausencia informa, así que se pinta."""
    factores = [aporte("F4", aporte=0.3), aporte("F1", sin_cobertura=True)]
    fuentes = agrupar_por_fuente(factores)
    assert [f["fuente"] for f in fuentes] == ["licencias", "contratación"]
    assert fuentes[-1]["sin_datos"]
    assert fuentes[-1]["aporte"] == 0.0


def test_el_mapa_de_factor_a_fuente_vive_en_un_solo_sitio():
    """M9 lee los nombres del payload; no los vuelve a declarar.

    Si el mapa se duplicara, un cambio en uno de los dos lados daría dos
    informes que nombran distinto la misma fuente.
    """
    from territorial.informes import composicion

    assert set(composicion.FUENTES) == {"F1", "F2", "F3", "F4", "F5", "F6"}
    # Todo lo que la frase puede nombrar sale del mismo mapa.
    cortos = {corto for _, corto in composicion.FUENTES.values()}
    assert set(composicion.ORDEN_FUENTES) == cortos
    assert set(composicion.FUENTES_EN_RESUMEN) <= cortos


# --------------------------------------------------------------------------
# Qué se puede publicar: cubrir los municipios no es haber corrido la cadena
# --------------------------------------------------------------------------


def test_una_corrida_sin_insights_del_clasificador_no_se_publica(bd):
    """La trampa real: «completa» dice cuántos municipios, no qué pasos.

    Las corridas 11 y 12 del ciclo 3 cubren los 18 y tienen cero insights del
    Clasificador — las creó `comparar_correlacionador.py --persistir`, que solo
    guarda correlaciones. Publicar una daría un informe con las convergencias y
    sin los insights individuales, que son el grueso de lo que se lee.
    """
    s, sc, _ = bd
    solo_m4 = CorridaAgentes(
        id_ciclo=3, tipo_corrida="completa", version_pipeline="p2",
        municipios_objetivo=["25286", "73001"],
        municipios_en_cohorte=["25286", "73001"],
    )
    s.add(solo_m4)
    s.flush()
    s.add(Insight(
        id_corrida=solo_m4.id, divipola="73001", categoria="obra_vial+vivienda",
        resumen="Convergencia", estado_validacion="validado",
        origen="correlacionador",
    ))
    s.flush()

    with pytest.raises(PublicacionInvalida, match="no corrió la cadena"):
        publicar(s, sc, solo_m4.id)


def test_ciclos_publicables_ignora_las_corridas_que_no_corrieron_la_cadena(bd):
    """No basta con «la más reciente completa»: hay que mirar qué trae."""
    s, sc, ag = bd
    solo_m4 = CorridaAgentes(
        id_ciclo=3, tipo_corrida="completa", version_pipeline="p2",
        municipios_objetivo=["25286", "73001"],
        municipios_en_cohorte=["25286", "73001"],
    )
    s.add(solo_m4)
    s.flush()

    publicables = ciclos_publicables(s)
    # La de solo correlaciones es mas reciente y aun asi no se propone.
    assert publicables[3]["agentes"] == ag
    assert publicables[3]["publicable"]


def test_un_ciclo_sin_corrida_completa_de_agentes_no_es_publicable(bd):
    """El caso del ciclo 2: nunca se corrió entero, y no estaba escrito.

    Antes solo se descubría intentando publicar y leyendo el error.
    """
    s, sc, _ = bd
    s.add(Ciclo(id=2, fecha_desde=date(2025, 10, 22), fecha_hasta=date(2026, 1, 14)))
    s.add(CorridaScoring(
        id_ciclo=2, tipo_corrida="completa", version_scoring="v3+abc",
        municipios_objetivo=["25286", "73001"],
        municipios_en_cohorte=["25286", "73001"], pesos={"F1": 1.0},
    ))
    s.add(CorridaAgentes(
        id_ciclo=2, tipo_corrida="parcial", version_pipeline="p1",
        municipios_objetivo=["25286", "73001"], municipios_en_cohorte=["73001"],
    ))
    s.flush()

    ciclo2 = ciclos_publicables(s)[2]
    assert not ciclo2["publicable"]
    assert ciclo2["falta"] == ["agentes"]


def test_el_error_de_una_parcial_dice_cuan_parcial(bd):
    """17 de 18 y 1 de 18 son las dos «parcial», y no piden lo mismo."""
    s, sc, ag = bd
    corrida = s.get(CorridaAgentes, ag)
    corrida.tipo_corrida = "parcial"
    corrida.municipios_en_cohorte = ["73001"]
    s.flush()
    with pytest.raises(PublicacionInvalida, match=r"1 de 2 municipios"):
        publicar(s, sc, ag)


# --------------------------------------------------------------------------
# El contexto son tres tarjetas, y ninguna es de ELIC
# --------------------------------------------------------------------------


def test_el_contexto_son_tres_tarjetas_de_terridata():
    campos = campos_de_contexto(ContextoMunicipal(
        codigo_divipola="25286", poblacion_total=125_880, anio_poblacion=2026,
        deficit_cuantitativo=10.64, anio_deficit=2018,
        avaluo_catastral_urbano=3_228_451.0, predios_urbanos=28_053,
        anio_catastro=2024,
    ))
    assert [c["clave"] for c in campos] == [
        "deficit_cuantitativo", "poblacion_total", "avaluo_por_predio",
    ]


def test_el_avaluo_va_por_predio_no_total():
    """El total mide tamaño de ciudad; el valor del suelo es el cociente."""
    campos = campos_de_contexto(ContextoMunicipal(
        codigo_divipola="25286", avaluo_catastral_urbano=1000.0,
        predios_urbanos=10, anio_catastro=2024,
    ))
    avaluo = next(c for c in campos if c["clave"] == "avaluo_por_predio")
    assert avaluo["valor"] == pytest.approx(100.0)


def test_elic_no_aparece_en_el_contexto():
    """Ya está abajo como F4: arriba lo contaría dos veces."""
    campos = campos_de_contexto(ContextoMunicipal(
        codigo_divipola="25286", poblacion_total=1, anio_poblacion=2026,
    ))
    texto = " ".join(c["etiqueta"].lower() for c in campos)
    assert "licencia" not in texto
    assert "elic" not in texto


# --------------------------------------------------------------------------
# Lo que se pide calificar viaja en el payload, y la semilla congelada
# --------------------------------------------------------------------------


def test_solo_los_municipios_pedidos_traen_insights_pedidos(bd):
    s, sc, ag = bd
    d = componer(s, sc, ag, tope_calificable=1)
    assert d["municipios"][0]["insights_pedidos"]
    assert d["municipios"][1]["insights_pedidos"] == []


def test_la_semilla_queda_congelada_en_el_payload(bd):
    """Para poder recomputar la muestra y comprobar que fue la misma (CA-M6.6)."""
    s, sc, ag = bd
    d = componer(s, sc, ag)
    assert d["calificacion"]["semilla"] == d["ciclo"]
    assert d["calificacion"]["pedidas_por_municipio"] == 5


# --------------------------------------------------------------------------
# H-005 / F0.1 — el denominador de H2 se congela en el payload
# --------------------------------------------------------------------------


def ids(gerencias: list[dict]) -> list[str]:
    return [g["id_gerencia"] for g in gerencias]


def test_el_payload_congela_las_gerencias_autorizadas(bd):
    """Quién podía calificar cuando se publicó, no quién puede hoy.

    Sin esto, sustituir los usuarios de prueba por los reales tras publicar
    recalculaba la tasa de respuesta del ciclo con otro denominador (H-005).
    """
    s, sc, ag = bd
    assert ids(componer(s, sc, ag)["calificacion"]["gerencias"]) == [
        "activos", "comercial", "desarrollo",
    ]


def test_el_denominador_excluye_inactivos_y_administradores(bd):
    """El administrador tiene panel, no papeleta (CA-M9.14); el inactivo, nada."""
    s, _, _ = bd
    gerencias = ids(gerencias_autorizadas(s))
    assert "antigua" not in gerencias
    assert "analitica" not in gerencias


def test_dos_personas_de_una_gerencia_cuentan_una_vez(bd):
    """`calificacion` atribuye por gerencia, así que el denominador también."""
    s, _, _ = bd
    assert ids(gerencias_autorizadas(s)).count("comercial") == 1


def test_el_informe_publicado_guarda_las_gerencias_y_no_cambia_si_usuario_cambia(bd):
    """La garantía completa: lo que quedó en `informe.contenido` es inmune a
    altas, bajas y cambios posteriores en `usuario`."""
    s, sc, ag = bd
    inf = publicar(s, sc, ag)
    congeladas = inf.contenido["calificacion"]["gerencias"]
    assert ids(congeladas) == ["activos", "comercial", "desarrollo"]

    # Después de publicar: una gerencia nueva, otra se desactiva.
    s.add(Usuario(id_gerencia="nueva", nombre="F", correo="f@p.co"))
    s.query(Usuario).filter_by(correo="c@p.co").one().activo = False
    s.flush()
    assert ids(gerencias_autorizadas(s)) == ["comercial", "desarrollo", "nueva"]

    s.expire_all()
    guardado = s.get(Informe, inf.id).contenido["calificacion"]["gerencias"]
    assert ids(guardado) == ["activos", "comercial", "desarrollo"]


def test_sin_usuarios_el_denominador_es_una_lista_vacia_no_un_hueco(bd):
    """Explícito y vacío: el lector del payload ve que no había nadie."""
    s, sc, ag = bd
    s.query(Usuario).delete()
    s.flush()
    assert componer(s, sc, ag)["calificacion"]["gerencias"] == []


# --------------------------------------------------------------------------
# F0.1b — la marca prd/adicional viaja con cada gerencia congelada
# --------------------------------------------------------------------------


def config_con_prd(tmp_path, *gerencias: str) -> Config:
    """Un `Config` que declara esas `id_gerencia` como las del PRD."""
    ruta = tmp_path / "gerencias.json"
    ruta.write_text(json.dumps({"prd": list(gerencias)}), encoding="utf-8")
    return Config(ruta_gerencias=ruta)


def test_las_declaradas_salen_marcadas_prd_y_el_resto_adicional(bd, tmp_path):
    """La razón de existir de F0.1b: separar H2 de los calificadores añadidos."""
    s, sc, ag = bd
    cfg = config_con_prd(tmp_path, "comercial", "desarrollo", "activos")
    marcas = {
        g["id_gerencia"]: g["tipo"]
        for g in componer(s, sc, ag, config=cfg)["calificacion"]["gerencias"]
    }
    assert marcas == {"comercial": "prd", "desarrollo": "prd", "activos": "prd"}


def test_una_gerencia_fuera_de_la_lista_es_adicional(bd, tmp_path):
    """El caso del dueño: Analítica califica y no es una de las 7."""
    s, sc, ag = bd
    s.add(Usuario(id_gerencia="analitica_califica", nombre="G", correo="g@p.co"))
    s.flush()
    cfg = config_con_prd(tmp_path, "comercial", "desarrollo", "activos")
    marcas = {
        g["id_gerencia"]: g["tipo"]
        for g in componer(s, sc, ag, config=cfg)["calificacion"]["gerencias"]
    }
    assert marcas["analitica_califica"] == "adicional"
    assert marcas["comercial"] == "prd"


def test_las_siete_del_prd_salen_todas_como_prd(bd, tmp_path):
    """Con las 7 declaradas, ninguna de ellas se cuela como adicional."""
    siete = [f"gerencia_{n}" for n in range(1, 8)]
    s, sc, ag = bd
    s.query(Usuario).delete()
    s.add_all([
        Usuario(id_gerencia=g, nombre=g, correo=f"{g}@p.co") for g in siete
    ])
    s.flush()
    gerencias = componer(s, sc, ag, config=config_con_prd(tmp_path, *siete))[
        "calificacion"
    ]["gerencias"]
    assert ids(gerencias) == siete
    assert {g["tipo"] for g in gerencias} == {"prd"}


def test_la_marca_queda_congelada_aunque_cambie_la_configuracion(bd, tmp_path):
    """Lo mismo que la lista: el informe publicado no se mueve.

    Si la marca se recalculara al leer, reclasificar una gerencia después
    cambiaría a posteriori sobre quién se computó H2 en un ciclo ya cerrado.
    """
    s, sc, ag = bd
    ruta = tmp_path / "gerencias.json"
    ruta.write_text(json.dumps({"prd": ["comercial"]}), encoding="utf-8")
    cfg = Config(ruta_gerencias=ruta)

    inf = publicar(s, sc, ag, config=cfg)
    congeladas = {
        g["id_gerencia"]: g["tipo"] for g in inf.contenido["calificacion"]["gerencias"]
    }
    assert congeladas == {
        "activos": "adicional", "comercial": "prd", "desarrollo": "adicional",
    }

    # La configuración cambia: ahora las tres son del PRD.
    ruta.write_text(
        json.dumps({"prd": ["comercial", "desarrollo", "activos"]}), encoding="utf-8"
    )
    s.expire_all()
    guardado = {
        g["id_gerencia"]: g["tipo"]
        for g in s.get(Informe, inf.id).contenido["calificacion"]["gerencias"]
    }
    assert guardado == congeladas


def test_sin_archivo_de_configuracion_todas_son_adicionales(bd, tmp_path):
    """El estado de hoy, y es deliberado: el PRD nunca nombra las 7.

    Se comprueba antes de la republicación definitiva de F0.6; hasta entonces
    la marca dice la verdad, que es que no hay ninguna declarada.
    """
    s, sc, ag = bd
    cfg = Config(ruta_gerencias=tmp_path / "no-existe.json")
    tipos = {g["tipo"] for g in componer(s, sc, ag, config=cfg)["calificacion"]["gerencias"]}
    assert tipos == {"adicional"}


def test_el_archivo_de_gerencias_del_repositorio_es_valido():
    """Se entrega vacío, pero tiene que cumplir el contrato desde el día uno."""
    assert cargar_prd(Config(ruta_gerencias=Path("config/gerencias.json"))) == frozenset()


@pytest.mark.parametrize("contenido, error", [
    ("[]", "se esperaba un objeto"),
    ('{"prd": "comercial"}', "lista de id_gerencia"),
    ('{"prd": ["a", "a"]}', "repetidas"),
    ('{"prd": ["  "]}', "vacía"),
    ('{"otra": []}', "claves desconocidas"),
    ("{", "no es JSON válido"),
])
def test_un_archivo_de_gerencias_mal_escrito_falla_en_vez_de_marcar_mal(
    tmp_path, contenido, error
):
    """Marcar mal es peor que no arrancar: H2 se reportaría sobre otro conjunto."""
    ruta = tmp_path / "gerencias.json"
    ruta.write_text(contenido, encoding="utf-8")
    with pytest.raises(GerenciasInvalidas, match=error):
        cargar_prd(Config(ruta_gerencias=ruta))


def test_las_notas_del_archivo_no_estorban(tmp_path):
    """El JSON no tiene comentarios, así que las notas van en claves `_…`."""
    ruta = tmp_path / "gerencias.json"
    ruta.write_text(
        json.dumps({"_nota": "algo que explicar", "prd": ["comercial"]}),
        encoding="utf-8",
    )
    assert cargar_prd(Config(ruta_gerencias=ruta)) == frozenset({"comercial"})


def test_cada_insight_dice_como_llego(bd):
    """Directo o Correlacionado: es el trabajo de M4 hecho visible."""
    s, sc, ag = bd
    trayectos = {
        i["trayecto"] for m in componer(s, sc, ag)["municipios"] for i in m["insights"]
    }
    assert trayectos <= {"Directo", "Correlacionado"}
    assert "Directo" in trayectos
