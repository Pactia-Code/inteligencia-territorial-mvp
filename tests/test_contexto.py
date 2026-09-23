"""Pruebas del contexto estructural: extracción de TerriData y bandas.

Dos cosas distintas y las dos frágiles:

  · **La extracción** tiene que sobrevivir al formato de TerriData, que trae
    decimales con coma, miles con punto, filas duplicadas y series viejas
    conviviendo con nuevas. Cada trampa tiene su prueba.
  · **Las bandas** son la frontera de CA-M6.3: si una cifra se colara al
    prompt, el modelo podría escribirla. `ContextoBandeado.como_texto()` no
    puede contener un solo dígito de dato.

El zip real son 3,31 GB y no viaja en el repositorio, así que la extracción se
prueba contra un zip sintético con las mismas trampas en miniatura.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from territorial.almacen.modelos import ContextoMunicipal
from territorial.ingesta.contexto import a_numero, es_municipio, extraer
from territorial.reglas.contexto import (
    ContextoBandeado,
    bandear,
    clase_de_tamano,
    cortes_nacionales,
    derivar,
    etiqueta_de,
)

CABECERA = (
    "Código Departamento|Departamento|Código Entidad|Entidad|Dimensión|"
    "Subcategoría|Indicador|Código Indicador|Dato Numérico|Dato Cualitativo|"
    "Año|Mes|Fuente|Unidad de Medida"
)


def fila(entidad: str, codigo_ind: str, valor: str, anio: str) -> str:
    return (
        f"05|Antioquia|{entidad}|X|Dim|Sub|Ind|{codigo_ind}|{valor}||{anio}|0|DANE|U"
    )


@pytest.fixture
def zip_sintetico(tmp_path: Path) -> Path:
    """Un TerriData en miniatura con las cinco trampas del original."""
    lineas = [
        CABECERA,
        # Nacional y departamental: no son municipios, deben ignorarse.
        fila("01001", "010010009", "50.000.000,00", "2026"),
        fila("05000", "010010009", "7.000.000,00", "2026"),
        # Población: la serie llega a 2070 y solo vale 2026.
        fila("05001", "010010009", "2.600.000,00", "2026"),
        fila("05001", "010010009", "3.100.000,00", "2070"),
        # Valor agregado: la serie vieja muere en 2015, la nueva manda.
        fila("05001", "120010012", "32.991,69", "2015"),
        fila("05001", "120210001", "34.442,54", "2023"),
        # Déficit: la MISMA fila dos veces, como en el original.
        fila("05001", "030010008", "20,90", "2018"),
        fila("05001", "030010008", "20,90", "2018"),
        fila("05001", "030010009", "5,13", "2018"),
        # Catastro: 2022 y 2024; gana el último año.
        fila("05001", "150070005", "70.000.000,00", "2022"),
        fila("05001", "150070005", "82.967.640,00", "2024"),
        fila("05001", "150070002", "433.369,00", "2024"),
        # Un indicador que no pedimos: no debe aparecer.
        fila("05001", "150050003", "SI", "2024"),
        # Un segundo municipio, para que haya cohorte.
        fila("05002", "010010009", "12.000,00", "2026"),
        fila("05002", "120210001", "100,00", "2023"),
        fila("05002", "030010008", "55,00", "2018"),
        fila("05002", "030010009", "30,00", "2018"),
        fila("05002", "150070005", "50.000,00", "2024"),
        fila("05002", "150070002", "5.000,00", "2024"),
    ]
    ruta = tmp_path / "mini.zip"
    with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("TerriData.txt", "\n".join(lineas) + "\n")
    return ruta


# --------------------------------------------------------------------------
# Formato numérico — la trampa que falla en silencio
# --------------------------------------------------------------------------


def test_el_punto_es_separador_de_miles_y_la_coma_decimal():
    """`32.991,69` leído al revés da 32,99 y nadie lo nota."""
    assert a_numero("7.945.996,00") == pytest.approx(7_945_996.0)
    assert a_numero("32.991,69") == pytest.approx(32_991.69)
    assert a_numero("20,90") == pytest.approx(20.90)


def test_lo_que_no_es_numero_devuelve_none():
    assert a_numero("") is None
    assert a_numero("   ") is None
    assert a_numero("SI") is None
    assert a_numero(None) is None


def test_se_distingue_municipio_de_departamento_y_nacion():
    assert es_municipio("05001")
    assert not es_municipio("05000")  # departamento
    assert not es_municipio("01001")  # nacional
    assert not es_municipio("0500")


# --------------------------------------------------------------------------
# Extracción
# --------------------------------------------------------------------------


def test_se_extrae_un_solo_valor_por_municipio(zip_sintetico):
    datos, c = extraer(zip_sintetico)
    assert set(datos) == {"05001", "05002"}
    assert c.municipios == 2


def test_la_poblacion_se_fija_a_2026_y_no_toma_la_proyeccion_a_2070(zip_sintetico):
    """«El último año disponible» daría una proyección a 44 años vista."""
    datos, _ = extraer(zip_sintetico)
    assert datos["05001"]["anio_poblacion"] == 2026
    assert datos["05001"]["poblacion_total"] == 2_600_000


def test_gana_la_serie_nueva_de_valor_agregado(zip_sintetico):
    """La vieja (120010012) muere en 2015 y no se carga."""
    datos, _ = extraer(zip_sintetico)
    assert datos["05001"]["valor_agregado"] == pytest.approx(34_442.54)
    assert datos["05001"]["anio_valor_agregado"] == 2023


def test_la_fila_duplicada_de_deficit_se_cuenta_y_se_ignora(zip_sintetico):
    """1.101 municipios traen dos veces la misma fila en el archivo real."""
    datos, c = extraer(zip_sintetico)
    assert c.duplicados == 1
    assert datos["05001"]["deficit_cuantitativo"] == pytest.approx(20.90)


def test_del_catastro_gana_el_anio_mas_reciente(zip_sintetico):
    datos, _ = extraer(zip_sintetico)
    assert datos["05001"]["anio_catastro"] == 2024
    assert datos["05001"]["avaluo_catastral_urbano"] == pytest.approx(82_967_640.0)
    assert datos["05001"]["predios_urbanos"] == 433_369


def test_no_se_cargan_departamentos_ni_la_nacion(zip_sintetico):
    datos, _ = extraer(zip_sintetico)
    assert "05000" not in datos
    assert "01001" not in datos


def test_delineacion_no_entra_porque_es_binaria(zip_sintetico):
    """150050003 dice si el municipio cobra el impuesto, no cuánto."""
    _, c = extraer(zip_sintetico)
    assert "150050003" not in c.por_indicador


# --------------------------------------------------------------------------
# Bandas
# --------------------------------------------------------------------------


def contexto(**kw) -> ContextoMunicipal:
    base = {"codigo_divipola": "05001"}
    base.update(kw)
    return ContextoMunicipal(**base)


def test_el_valor_agregado_se_bandea_per_capita_no_total():
    """Un total es un proxy del tamaño; los factores del score nunca lo son."""
    grande_pobre = contexto(valor_agregado=1000.0, poblacion_total=1_000_000)
    pequeno_rico = contexto(valor_agregado=100.0, poblacion_total=10_000)
    assert (
        derivar(pequeno_rico)["valor_agregado_per_capita"]
        > derivar(grande_pobre)["valor_agregado_per_capita"]
    )


def test_el_avaluo_se_bandea_por_predio_no_total():
    muchos = contexto(avaluo_catastral_urbano=1000.0, predios_urbanos=1000)
    pocos = contexto(avaluo_catastral_urbano=500.0, predios_urbanos=100)
    assert derivar(pocos)["avaluo_por_predio"] > derivar(muchos)["avaluo_por_predio"]


def test_sin_poblacion_no_hay_per_capita():
    """Dividir por cero o por None daría una banda inventada."""
    assert derivar(contexto(valor_agregado=100.0))["valor_agregado_per_capita"] is None
    assert derivar(
        contexto(valor_agregado=100.0, poblacion_total=0)
    )["valor_agregado_per_capita"] is None


def test_las_clases_de_tamano_son_cortes_fijos_no_cuantiles():
    """Con cuartiles nacionales los 18 del MVP salían todos «alto»."""
    assert clase_de_tamano(5_000) == "pequeño"
    assert clase_de_tamano(51_298) == "intermedio"
    assert clase_de_tamano(307_103) == "grande"
    assert clase_de_tamano(1_275_854) == "metropolitano"
    assert clase_de_tamano(None) is None


def test_la_etiqueta_respeta_los_cuartiles():
    cortes = [10.0, 20.0, 30.0]
    assert etiqueta_de(5.0, cortes) == "bajo"
    assert etiqueta_de(15.0, cortes) == "medio-bajo"
    assert etiqueta_de(25.0, cortes) == "medio-alto"
    assert etiqueta_de(99.0, cortes) == "alto"
    assert etiqueta_de(None, cortes) is None
    assert etiqueta_de(5.0, None) is None


def test_los_municipios_sin_dato_no_corren_los_cortes():
    """Contarlos como cero bajaría los cortes y subiría de banda a todos."""
    filas = [
        contexto(deficit_cuantitativo=10.0),
        contexto(deficit_cuantitativo=20.0),
        contexto(deficit_cuantitativo=30.0),
        contexto(deficit_cuantitativo=None),
    ]
    cortes = cortes_nacionales(filas)
    assert cortes["deficit_cuantitativo"][1] == pytest.approx(20.0)


def test_un_indicador_sin_datos_no_tiene_banda():
    filas = [contexto(deficit_cuantitativo=10.0), contexto(deficit_cuantitativo=20.0)]
    b = bandear(filas[0], cortes_nacionales(filas))
    assert b.deficit_cuantitativo is not None
    assert b.avaluo_por_predio is None


# --------------------------------------------------------------------------
# La frontera de CA-M6.3: al prompt no llega un solo dígito
# --------------------------------------------------------------------------


def test_el_texto_del_prompt_no_contiene_ninguna_cifra_del_municipio():
    """Si una cifra llegara al prompt, el modelo podría escribirla.

    Lo único numérico permitido es el «1.102» de la referencia nacional, que no
    es un dato del municipio sino el tamaño de la cohorte.
    """
    b = ContextoBandeado(
        divipola="05001",
        tamano="metropolitano",
        valor_agregado_per_capita="alto",
        deficit_cuantitativo="bajo",
        deficit_cualitativo="medio-bajo",
        avaluo_por_predio="alto",
    )
    texto = b.como_texto()
    sin_cohorte = texto.replace("1.102", "")
    assert not any(ch.isdigit() for ch in sin_cohorte), texto
    # Y las bandas sí están, que es el punto de pasarlo.
    assert "metropolitano" in texto
    assert "bajo" in texto


def test_sin_datos_no_se_escribe_bloque_alguno():
    """Un encabezado vacío haría que el modelo se pregunte qué falta."""
    assert ContextoBandeado(divipola="05001").como_texto() == ""
    assert not ContextoBandeado(divipola="05001").hay_algo


def test_un_contexto_parcial_solo_lista_lo_que_tiene():
    b = ContextoBandeado(divipola="05001", deficit_cuantitativo="alto")
    texto = b.como_texto()
    assert "Déficit habitacional cuantitativo: alto" in texto
    assert "Avalúo" not in texto
    assert "Tamaño" not in texto


# --------------------------------------------------------------------------
# El contexto solo llega a un prompt que sepa qué hacer con él
# --------------------------------------------------------------------------


def test_solo_las_versiones_declaradas_reciben_el_contexto():
    """Mandarlo a un prompt que no lo documenta sería darle datos sin reglas.

    v1 no documenta el bloque, así que no sabría que el contexto explica una
    convergencia y nunca la crea — que es justo la regla que hay que sostener.
    Condicionarlo a la versión evita que cambiar `VERSION_PROMPT` deje el bloque
    viajando, o dejando de viajar, por su cuenta.
    """
    from territorial.agentes import correlacionador as co

    assert "v2" in co.VERSIONES_CON_CONTEXTO
    assert "v1" not in co.VERSIONES_CON_CONTEXTO

    # **Antes esto exigía que la versión por defecto entendiera el bloque**, con
    # el argumento de que si no, el contexto no llegaría a nadie. Desde el
    # 2026-09-22 el valor por defecto es v1 hasta que F2.3 valide v2, así que el
    # contexto **deliberadamente no viaja**: es el mismo comportamiento que la
    # corrida 10, la del informe publicado. Lo que sigue siendo invariante es que
    # el bloque solo llega a una versión que lo documente, se elija como se elija.
    if co.VERSION_PROMPT in co.VERSIONES_CON_CONTEXTO:
        assert co.VERSION_PROMPT == "v2", "solo v2 documenta el bloque"
    else:
        assert co.VERSION_PROMPT == "v1", (
            "si el valor por defecto no entiende el contexto, tiene que ser v1: "
            "cualquier otra versión sin bloque sería una tercera, sin decidir"
        )


def test_el_prompt_v1_se_conserva_como_linea_base():
    """§10: las versiones anteriores documentan contra qué se midió."""
    from territorial.agentes.correlacionador import instrucciones

    assert "Agente Correlacionador" in instrucciones("v1")
    assert "Contexto estructural del municipio" not in instrucciones("v1")


def test_el_prompt_v2_lleva_las_tres_reglas():
    """Son lo que hace segura la concesión de dejar enunciar la banda."""
    from territorial.agentes.correlacionador import instrucciones

    v2 = instrucciones("v2")
    assert "explica una convergencia; nunca la crea" in v2
    assert "Usa la banda, nunca inventes el número" in v2
    assert "no es novedad de este ciclo" in v2
