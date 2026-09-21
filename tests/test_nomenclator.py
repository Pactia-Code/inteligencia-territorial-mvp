"""Pruebas del nomenclátor DIVIPOLA (capa determinista).

**El CSV real no viaja en el repositorio** —`data/` está en `.gitignore`— así
que aquí se construye uno sintético con las mismas rarezas que el de verdad.
Que la prueba no pueda leer el archivo real es lo que obliga a que las rarezas
estén escritas y no solo observadas.

Lo que importa probar no es que el CSV se lea, sino las cuatro cosas que van a
confundir a alguien en seis semanas: Bogotá sin fila departamental, San Andrés
ausente, la convención de códigos de TerriData y los homónimos.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from territorial.almacen.modelos import Base, EntidadDivipola
from territorial.ingesta.nomenclator import (
    NomenclatorInvalido,
    cargar,
    construir,
    homonimos,
    leer_csv,
)

# Cuatro departamentos que reproducen el nomenclátor real en miniatura:
#   05  normal, dos municipios
#   11  Bogotá: existe como municipio y NO como departamento
#   88  solo Providencia; falta San Andrés (88001)
#   70  para que «La Unión» se repita entre departamentos
FILAS = [
    {"codigo_divipola": "05001", "codigo_departamento": "05",
     "departamento": "Antioquia", "municipio": "Medellín"},
    {"codigo_divipola": "05400", "codigo_departamento": "05",
     "departamento": "Antioquia", "municipio": "La Unión"},
    {"codigo_divipola": "11001", "codigo_departamento": "11",
     "departamento": "Bogotá", "municipio": "Bogotá"},
    {"codigo_divipola": "88564", "codigo_departamento": "88",
     "departamento": "San Andrés y Providencia", "municipio": "Providencia"},
    {"codigo_divipola": "70400", "codigo_departamento": "70",
     "departamento": "Sucre", "municipio": "La Unión"},
]


@pytest.fixture
def entidades() -> list[dict]:
    return construir([dict(f) for f in FILAS])


@pytest.fixture
def sesion_vacia():
    motor = create_engine("sqlite://", future=True)
    Base.metadata.create_all(motor)
    with Session(motor) as s:
        yield s


# --------------------------------------------------------------------------
# Construcción
# --------------------------------------------------------------------------


def test_de_las_filas_del_csv_salen_mas_entidades(entidades):
    """El CSV solo trae municipios; departamentos y nacional se derivan."""
    por_tipo = {t: [e for e in entidades if e["tipo"] == t]
                for t in ("nacional", "departamento", "municipio")}
    assert len(por_tipo["municipio"]) == len(FILAS)
    assert len(por_tipo["nacional"]) == 1
    # Tres departamentos, no cuatro: Bogotá no genera fila departamental.
    assert len(por_tipo["departamento"]) == 3


def test_bogota_no_genera_fila_departamental(entidades):
    """Por esto los departamentos son 32 y no 33 en el nomenclátor real."""
    codigos = {e["codigo"] for e in entidades}
    assert "11001" in codigos
    assert "11000" not in codigos


def test_san_andres_no_aparece_porque_no_esta_en_el_origen(entidades):
    """Del departamento 88 solo hay Providencia. Son 1.102 municipios, no 1.103."""
    codigos = {e["codigo"] for e in entidades}
    assert "88564" in codigos
    assert "88001" not in codigos
    # El departamento sí se deriva, aunque le falte su capital.
    assert "88000" in codigos


def test_los_codigos_siguen_la_convencion_de_terridata(entidades):
    """Un join futuro con TerriData no debe necesitar traducción."""
    por_codigo = {e["codigo"]: e for e in entidades}
    assert por_codigo["01001"]["tipo"] == "nacional"
    assert por_codigo["05000"]["tipo"] == "departamento"
    assert por_codigo["05001"]["tipo"] == "municipio"
    assert all(len(e["codigo"]) == 5 for e in entidades)


def test_el_departamento_hereda_su_nombre_de_los_municipios(entidades):
    depto = next(e for e in entidades if e["codigo"] == "88000")
    assert depto["nombre"] == "San Andrés y Providencia"
    assert depto["nombre_departamento"] == depto["nombre"]


def test_cada_municipio_lleva_el_nombre_de_su_departamento(entidades):
    medellin = next(e for e in entidades if e["codigo"] == "05001")
    assert medellin["nombre_departamento"] == "Antioquia"


def test_un_codigo_repetido_en_el_origen_falla(entidades):
    filas = [*[dict(f) for f in FILAS], dict(FILAS[0])]
    with pytest.raises(NomenclatorInvalido, match="repetidos"):
        construir(filas)


def test_un_codigo_no_canonico_falla():
    filas = [{"codigo_divipola": "5001", "codigo_departamento": "05",
              "departamento": "Antioquia", "municipio": "Medellín"}]
    with pytest.raises(NomenclatorInvalido, match="no canónico"):
        construir(filas)


# --------------------------------------------------------------------------
# Homónimos — la razón por la que no se puede resolver por nombre
# --------------------------------------------------------------------------


def test_los_homonimos_se_detectan_entre_departamentos(entidades):
    repes = homonimos(entidades)
    assert set(repes) == {"La Unión"}
    assert repes["La Unión"] == ["05400", "70400"]


def test_el_nombre_del_departamento_no_cuenta_como_homonimo(entidades):
    """Solo se comparan municipios: un departamento y su capital no colisionan."""
    assert "Antioquia" not in homonimos(entidades)


# --------------------------------------------------------------------------
# Carga idempotente
# --------------------------------------------------------------------------


def test_la_primera_carga_inserta_todo(sesion_vacia, entidades):
    r = cargar(sesion_vacia, entidades)
    assert r.nuevas == len(entidades)
    assert r.actualizadas == 0
    assert not r.sin_cambios


def test_la_segunda_carga_no_toca_nada(sesion_vacia, entidades):
    """Idempotente de verdad, no «no revienta al repetirla»."""
    cargar(sesion_vacia, entidades)
    r = cargar(sesion_vacia, entidades)
    assert r.nuevas == 0
    assert r.actualizadas == 0
    assert r.iguales == len(entidades)
    assert r.sin_cambios
    assert sesion_vacia.query(EntidadDivipola).count() == len(entidades)


def test_un_nombre_corregido_en_el_origen_se_actualiza(sesion_vacia, entidades):
    cargar(sesion_vacia, entidades)
    corregidas = [dict(e) for e in entidades]
    next(e for e in corregidas if e["codigo"] == "05001")["nombre"] = "Medellin"
    r = cargar(sesion_vacia, corregidas)
    assert (r.nuevas, r.actualizadas) == (0, 1)
    assert sesion_vacia.get(EntidadDivipola, "05001").nombre == "Medellin"


def test_lo_que_sobra_se_reporta_pero_no_se_borra(sesion_vacia, entidades):
    """Si el nomenclátor encoge, que alguien mire por qué antes de borrar."""
    cargar(sesion_vacia, entidades)
    sin_providencia = [e for e in entidades if e["codigo"] != "88564"]
    r = cargar(sesion_vacia, sin_providencia)
    assert r.sobrantes == ["88564"]
    assert sesion_vacia.get(EntidadDivipola, "88564") is not None


# --------------------------------------------------------------------------
# Lectura del CSV
# --------------------------------------------------------------------------


def test_un_csv_sin_las_columnas_esperadas_falla(tmp_path: Path):
    ruta = tmp_path / "malo.csv"
    with ruta.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["codigo", "nombre"])
        w.writerow(["05001", "Medellín"])
    with pytest.raises(NomenclatorInvalido, match="faltan columnas"):
        leer_csv(ruta)


def test_se_lee_con_bom_y_se_recortan_los_espacios(tmp_path: Path):
    """Excel guarda con BOM, y el spike salió de Excel."""
    ruta = tmp_path / "con_bom.csv"
    ruta.write_text(
        "codigo_divipola,codigo_departamento,departamento,municipio\n"
        " 05001 , 05 , Antioquia , Medellín \n",
        encoding="utf-8-sig",
    )
    entidades = construir(leer_csv(ruta))
    medellin = next(e for e in entidades if e["tipo"] == "municipio")
    assert medellin["codigo"] == "05001"
    assert medellin["nombre"] == "Medellín"
    assert medellin["nombre_departamento"] == "Antioquia"
