"""El documento commiteado trae las cifras que la auditoría reprodujo. F0b.1.

Dos comprobaciones, y juntas cierran el criterio de la auditoría:

- **Aquí**: `docs/informe_resultados.md` contiene las 19 cifras que la
  auditoría reprodujo exactamente, todas con su etiqueta y el commit de la
  cabecera, sin huecos y sin ninguna hora.
- **En el script**: `scripts/informe_resultados.py --check` exige que el
  documento sea exactamente lo que el script produce sobre la base.

Si el documento las trae y el documento es lo que el script produce, **el
script produce las 19 cifras**. La prueba en vivo, a petición con
`RESULTADOS_EN_VIVO=1`, lo comprueba además directamente contra la base, en
solo lectura; se salta por defecto porque el suite no toca ninguna base.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from territorial.informes import mediciones as m

RAIZ = Path(__file__).resolve().parents[1]
DOCUMENTO = RAIZ / "docs" / "informe_resultados.md"


# ---------------------------------------------------------------------------
# 3. El documento commiteado
# ---------------------------------------------------------------------------

#: Las 19 cifras que la auditoría reprodujo exactamente (§8a.2 y §8b.1, filas
#: «Sí, exacto»). La auditoría da el número sin enumerarlas; esta es la lista,
#: con A11 contado una vez aunque aparezca en las dos mitades y sin las
#: «calificaciones 0» del inventario, que cambiaron por diseño. Cada entrada es
#: lo que el documento tiene que decir, tal como lo pinta el generador.
DIECINUEVE: dict[str, list[str]] = {
    "01 inventario: municipios, señales, fuentes y días": [
        "| Municipios | 18 `", "| Señales cargadas | 20.030 `", "SECOP II 19.640 `",
        "RSS 336 `", "Bing 54 `", "| Días de los tres ciclos | 51, 84 y 239 `"],
    "02 descartes y trazas del inventario": [
        "| Descartes registrados | 5.731 `", "| Trazas de agente | 266 `"],
    "03 A6: volumen de las pasadas 7 y 8": [
        "344 y 365 `[consulta: mediciones.volumen · corridas 7 y 8",
        "1.140 y 1.160 `[consulta: mediciones.volumen · corridas 7 y 8"],
    "04 A6: señales que cambian y que vuelcan": [
        "22,4 % (625 de 2.786)", "19,5 % (543 de 2.786)"],
    "05 A11: convergencias, agrupados, municipios, totales y tipología": [
        "14,1 % (10 de 71)", "26,4 % (85 de 322)", "14 de 18 `", "39 y 42 `", "23 y 24 `"],
    "06 H3: supervivencia por fuente": [
        "98,1 % (53 de 54)", "98,9 % (269 de 272)", "100,0 % (5 de 5)"],
    "07 H3: conversión RSS y SECOP": [
        "46,0 % (120 de 261)", "39,0 % (869 de 2.226)"],
    "08 H3: descartes RSS sin implicación inmobiliaria": ["128 de 141 `"],
    "09 H3: consolidados que cruzan RSS con SECOP": ["15 de 38 `"],
    "10 H3: volumen de las corridas 10 y 7": [
        "364 insights y 1.382 evidencias `", "1.140 `[consulta: mediciones.volumen · corrida 7"],
    "11 H4: descartes declarados y no declarados": [
        "5.455 `[consulta: mediciones.descartes", "276 `[consulta: mediciones.descartes"],
    "12 H5: consumo por agente": [
        "| clasificador | `gpt-5.4-mini` | 215 | 1.759.734 | 459.192 | 39,5 |",
        "| correlacionador | `gpt-5` | 51 | 140.172 | 264.562 | 48,6 |"],
    "13 H5: consumo del ciclo 1": [
        "170 llamadas, 1.276.657 tokens de entrada y 441.861 de salida, en 53,6 minutos"],
    "14 H5: señales tras el prefiltro": ["7.628 de 19.640 `"],
    "15 hallazgo 1: vuelco por municipio": ["10,0 % (90 de 897)", "87,5 % (35 de 40)"],
    "16 hallazgo 5: F4 de Apartadó y F4 constante": [
        "-43,5 % en los tres ciclos `", "18 de 18 `[consulta: mediciones.factor_constante (F4)"],
    "17 hallazgo 5: top 3 de los ciclos 1 y 2, antes y después": [
        "| 1 | Carepa, Barranquilla y Armenia (16) | Barranquilla, Carepa y Pereira (19) |",
        "| 2 | Ibagué, Carepa y Buenaventura (8) | Carepa, Ibagué y Buenaventura (20) |"],
    "18 hallazgo 7: fracciones informadas y los cinco por debajo": [
        "20,1 % y 77,8 % `", "5: Armenia, Barranquilla, Cartagena de Indias, Ibagué y Pereira"],
    "19 anexo CA-M2.1": [
        "95,2 % (313 validados de 6.454 señales)", "94,9 % (327 validados de 6.454 señales)",
        "95,3 % (322 validados de 6.831 señales)"],
}


def test_son_diecinueve():
    assert len(DIECINUEVE) == 19


@pytest.fixture(scope="module")
def documento() -> str:
    if not DOCUMENTO.exists():
        pytest.fail("no existe docs/informe_resultados.md: genéralo con el script")
    return DOCUMENTO.read_text(encoding="utf-8")


@pytest.mark.parametrize("nombre", sorted(DIECINUEVE))
def test_el_documento_trae_las_cifras_que_la_auditoria_reprodujo(documento, nombre):
    faltan = [x for x in DIECINUEVE[nombre] if x not in documento]
    assert not faltan, f"{nombre}: no aparece {faltan}"


def test_el_documento_no_tiene_huecos_sin_llenar(documento):
    assert "{{" not in documento and "}}" not in documento


def test_cada_etiqueta_lleva_el_commit_de_la_cabecera(documento):
    cabecera = re.search(r"\| Commit del código y de las consultas \| `([0-9a-f]{7,40})` \|",
                         documento)
    assert cabecera, "la cabecera no declara el commit"
    commits = set(re.findall(r"`\[consulta: [^`]*· ([0-9a-f]{7})\]`", documento))
    assert commits == {cabecera.group(1)[:7]}


def test_el_documento_no_lleva_ninguna_hora(documento):
    """Determinismo: los cortes van con hora porque son parámetros; nada más."""
    horas = re.findall(r"\b\d{2}:\d{2}(?::\d{2})?\b", documento)
    assert set(horas) <= {"23:59:59", "04:59:59"}, horas


def test_las_afirmaciones_retiradas_no_vuelven(documento):
    """H-030, H-027, H-028 y H-032: lo retirado solo aparece en su tabla."""
    fuera = re.sub(r"## Lo retirado.*?\n---\n", "", documento, flags=re.DOTALL)
    assert "Entre el 25" not in fuera and "25 % y el 50 %" not in fuera   # H-030
    assert "es **0,0%**" not in documento                                # H-028
    assert "hashes de entrada y de salida" not in fuera                  # H-027
    assert "[PRD §11]" not in documento                                  # H-032
    assert "[PRD §9]" in documento


# ---------------------------------------------------------------------------
# 4. En vivo, contra la base (opcional)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(os.environ.get("RESULTADOS_EN_VIVO") != "1",
                    reason="contra la base real; actívalo con RESULTADOS_EN_VIVO=1")
def test_en_vivo_las_mediciones_dan_las_cifras_de_la_auditoria():
    from sqlalchemy.orm import Session

    from territorial.almacen.sesion import obtener_motor

    motor = obtener_motor()
    with motor.connect() as conn:
        if motor.dialect.name == "postgresql":
            conn = conn.execution_options(postgresql_readonly=True)
        with Session(bind=conn) as s:
            inv = m.inventario(s)
            assert (inv.municipios, inv.senales, inv.descartes, inv.trazas) == (18, 20030, 5731, 266)
            assert m.comparar_pasadas(s, 7, 8) == m.Pasadas(2786, 625, 543)
            co = m.comparar_correlaciones(s, 11, 12, 10)
            assert (co.identicas, co.distintas, co.agrupados_que_cambian, co.corpus,
                    co.municipios_que_cambian, co.convergencias, co.con_tipologia) == (
                10, 71, 85, 322, 14, (39, 42), (23, 24))
            assert m.conversion_por_fuente(s, 10).convertidas == {"SECOP II": 869, "RSS": 120}
            assert m.descartes(s) == m.Descartes(5455, 276)
            assert m.senales_tras_prefiltro(s) == (7628, 19640)
            assert m.reduccion_clasificador(s, 10) == (322, 6831)
        conn.rollback()
