"""El informe de resultados se genera, y lo que publica se puede comprobar. F0b.1.

Tres capas, de la más barata a la más cara:

1. **Las reglas del generador**: ninguna cifra sin consulta, ningún hueco sin
   cifra ni cifra sin hueco, formato en castellano, parámetros con zona.
2. **Las definiciones congeladas de H1 y H2** (`docs/javelin.md`), con datos
   inventados que ejercitan cada regla.
3. El documento commiteado y las 19 cifras de la auditoría están en
   `tests/test_informe_resultados_documento.py`.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from territorial.informes import costo
from territorial.informes import mediciones as m
from territorial.informes import resultados as r

RAIZ = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# 1. Reglas del generador
# ---------------------------------------------------------------------------

def test_formato_en_castellano():
    assert r.entero(20030) == "20.030"
    assert r.entero(1759734) == "1.759.734"
    assert r.decimal(39.47171) == "39,5"
    assert r.decimal(0.856, 4) == "0,8560"
    assert r.decimal(-43.5) == "-43,5"
    assert r.pct(322, 326) == "98,8 % (322 de 326)"
    assert r.pct(625, 2786) == "22,4 % (625 de 2.786)"
    assert r.pct(0, 0) == "sin casos"
    assert r.lista(["a"]) == "a"
    assert r.lista(["a", "b", "c"]) == "a, b y c"


def test_una_cifra_con_numeros_no_existe_sin_su_consulta():
    """Es la regla que H-034 exige, hecha imposible de saltar."""
    with pytest.raises(r.CifraSinConsulta):
        r.Cifra("98,8 %")
    r.Cifra("98,8 %", "mediciones.algo")          # con consulta: bien
    r.Cifra("*pendiente de cierre*")              # sin números: bien
    r.Cifra("`abc1234`", parametro=True)          # parámetro de la generación: bien


def test_la_etiqueta_lleva_consulta_corridas_y_commit():
    c = r.Cifra("98,8 %", "tasa_rechazo.desde_la_base", (10,))
    assert c.pintar("abcdef1234") == (
        "98,8 % `[consulta: tasa_rechazo.desde_la_base · corrida 10 · abcdef1]`")
    sin = r.Cifra("266", "mediciones.trazas")
    assert "sin corrida" in sin.pintar("abcdef1")
    varias = r.Cifra("1", "x", (7, 8))
    assert "corridas 7 y 8" in varias.pintar("abcdef1")


def test_un_bloque_lleva_la_etiqueta_debajo():
    c = r.Cifra("| a |\n|---|\n| 1 |", "x", bloque=True)
    assert c.pintar("abcdef1").endswith("\n\n`[consulta: x · sin corrida · abcdef1]`")


def test_falta_un_hueco_o_sobra_una_cifra_y_el_render_falla():
    cifras = {"a": r.Cifra("1", "x")}
    with pytest.raises(r.PlantillaIncompleta, match="huecos sin cifra"):
        r.renderizar("{{a}} {{b}}", cifras, "abcdef1")
    with pytest.raises(r.PlantillaIncompleta, match="cifras sin hueco"):
        r.renderizar("nada", cifras, "abcdef1")
    assert r.renderizar("x {{a}} y {{a}}", cifras, "abcdef1").count("1 `[consulta") == 2


def test_los_parametros_exigen_commit_valido_y_zona_horaria():
    base = dict(
        commit="abcdef1", corte_principal=datetime(2026, 9, 30, 4, 59, 59, tzinfo=timezone.utc),
        corte_extendida=datetime(2026, 10, 9, 4, 59, 59, tzinfo=timezone.utc),
        a_fecha=datetime(2026, 10, 1, tzinfo=timezone.utc),
        carpeta_principal=Path("."), ruta_snapshot=Path("."), ruta_tarifas=Path("."),
    )
    r.Parametros(**base)
    with pytest.raises(ValueError, match="commit"):
        r.Parametros(**{**base, "commit": "HEAD"})
    with pytest.raises(ValueError, match="zona"):
        r.Parametros(**{**base, "a_fecha": datetime(2026, 10, 1)})


def test_la_ronda_extendida_esta_pendiente_hasta_que_pasa_su_corte():
    corte = datetime(2026, 10, 9, 4, 59, 59, tzinfo=timezone.utc)
    p = lambda a: r.Parametros(  # noqa: E731
        "abcdef1", corte - timedelta(days=9), corte, a, Path("."), Path("."), Path("."))
    assert p(corte).extendida_cerrada is False            # justo en el corte: aún no
    assert p(corte + timedelta(seconds=1)).extendida_cerrada is True
    cifras: dict = {}
    r._rondas(cifras, "e", None, None)
    assert all(c.texto == r.PENDIENTE for c in cifras.values())
    assert len(cifras) == 6


# ---------------------------------------------------------------------------
# 2. H1 y H2 con las definiciones congeladas en docs/javelin.md
# ---------------------------------------------------------------------------

PEDIDOS = m.Pedidos(8, 3, (1, 2, 3), {
    "g1": "prd", "g2": "prd", "g3": "prd", "ad": "adicional",
})


def cal(insight, gerencia, valor):
    return {"id_insight": insight, "id_gerencia": gerencia, "valor": valor}


def test_h1_un_insight_con_menos_de_2_calificaciones_prd_es_insuficiente():
    califs = [cal(1, "g1", 5), cal(1, "g2", 4),          # cuenta, promedio 4,5
              cal(2, "g1", 5),                           # 1 sola prd: insuficiente
              cal(3, "g1", 2), cal(3, "g2", 2)]          # cuenta, promedio 2
    res = m.h1(PEDIDOS, califs)
    assert (res.cuentan, res.insuficientes, res.altos_prd) == (2, 1, 1)
    assert res.porcentaje_prd == pytest.approx(50.0)


def test_h1_una_adicional_no_completa_el_minimo():
    """El mínimo es de calificaciones «prd»: una adicional no lo rellena."""
    res = m.h1(PEDIDOS, [cal(1, "g1", 5), cal(1, "ad", 5)])
    assert res.cuentan == 0 and res.porcentaje_prd is None


def test_h1_la_version_con_adicionales_usa_los_mismos_insights():
    califs = [cal(1, "g1", 4), cal(1, "g2", 4), cal(1, "ad", 1),   # prd 4 → alto; con ad 3 → no
              cal(2, "ad", 5), cal(2, "ad", 5)]                    # sin prd: fuera de las dos
    res = m.h1(PEDIDOS, califs)
    assert (res.cuentan, res.altos_prd, res.altos_con_adicionales) == (1, 1, 0)


def test_h1_y_h2_ignoran_lo_que_no_se_pidio():
    califs = [cal(99, "g1", 5), cal(99, "g2", 5)]
    assert m.h1(PEDIDOS, califs).cuentan == 0
    assert all(g.calificados == 0 for g in m.h2(PEDIDOS, califs).por_gerencia)


def test_h2_promedia_sobre_las_prd_incluidas_las_que_no_calificaron():
    """Un 0 % es un dato: la gerencia que no calificó cuenta en el promedio."""
    califs = [cal(i, "g1", 3) for i in (1, 2, 3)] + [cal(1, "ad", 3)]
    res = m.h2(PEDIDOS, califs)
    assert res.n_prd == 3
    assert res.promedio_prd == pytest.approx(100 / 3)
    assert [g.id_gerencia for g in res.de_tipo("adicional")] == ["ad"]


# ---------------------------------------------------------------------------
# La foto del corte
# ---------------------------------------------------------------------------

def _exportacion(tmp_path: Path, filas: list[dict], filas_declaradas: int | None = None,
                 sha: str | None = None) -> Path:
    lineas = ["id,id_insight,id_gerencia,id_usuario,valor,comentario,creado_en,"
              "creado_en_bogota,correo,tipo_gerencia"]
    for f in filas:
        lineas.append(f"{f['id']},{f['id_insight']},{f['id_gerencia']},{f['id_usuario']},"
                      f"{f['valor']},{f['comentario'] or ''},x,x,x,prd")
    csv = tmp_path / "calificacion.csv"
    csv.write_text("\n".join(lineas) + "\n", encoding="utf-8", newline="")
    real = hashlib.sha256(csv.read_bytes()).hexdigest()
    (tmp_path / "manifiesto.json").write_text(json.dumps({"archivos": {"calificacion.csv": {
        "filas": len(filas) if filas_declaradas is None else filas_declaradas,
        "sha256": sha or real,
    }}}), encoding="utf-8")
    return tmp_path


FILAS = [{"id": 1, "id_insight": 10, "id_gerencia": "g1", "id_usuario": 5, "valor": 4,
          "comentario": None},
         {"id": 2, "id_insight": 11, "id_gerencia": "g1", "id_usuario": 5, "valor": 2,
          "comentario": "poco claro"}]


def test_la_base_igual_a_la_foto_pasa(tmp_path):
    assert m.verificar_contra_exportacion(FILAS, _exportacion(tmp_path, FILAS)) == 2


def test_una_correccion_posterior_al_corte_se_detecta(tmp_path):
    """H-008: la corrección no cambia creado_en, pero no escapa de la foto."""
    carpeta = _exportacion(tmp_path, FILAS)
    corregidas = [FILAS[0], {**FILAS[1], "valor": 5}]
    with pytest.raises(m.CorteNoCoincide, match="ids \\[2\\]"):
        m.verificar_contra_exportacion(corregidas, carpeta)


def test_un_comentario_anadido_despues_se_detecta(tmp_path):
    carpeta = _exportacion(tmp_path, FILAS)
    with pytest.raises(m.CorteNoCoincide):
        m.verificar_contra_exportacion([{**FILAS[0], "comentario": "nuevo"}, FILAS[1]], carpeta)


def test_otro_numero_de_filas_o_otro_sha_falla(tmp_path):
    with pytest.raises(m.CorteNoCoincide, match="manifiesto declara 3"):
        m.verificar_contra_exportacion(FILAS, _exportacion(tmp_path, FILAS, filas_declaradas=3))
    otra = tmp_path / "otra"
    otra.mkdir()
    with pytest.raises(m.CorteNoCoincide, match="sha256"):
        m.verificar_contra_exportacion(FILAS, _exportacion(otra, FILAS, sha="0" * 64))


# ---------------------------------------------------------------------------
# H5: la fórmula de siempre, con las cifras de la auditoría
# ---------------------------------------------------------------------------

def test_la_proyeccion_da_la_condicional_que_decidio_el_dueno():
    """Con el consumo del Correlacionador medido (auditoría 8b.1) y las tarifas
    del tenant, el año nacional es 1.586 + 239·k."""
    tarifas = costo.leer_tarifas(RAIZ / "config" / "tarifas.json")
    p = costo.proyectar(*costo.escenario_anual_nacional(), (140_172, 264_562), 51,
                        tarifas["gpt-5.4-mini"], tarifas["gpt-5"])
    assert round(p.correlacionador) == 1_586
    assert round(p.clasificador) == 239
    assert round(p.total(1.0)) == 1_825
    assert round(p.total(2.0)) == 2_064          # la condicional de la auditoría con k = 2


# ---------------------------------------------------------------------------
# Una definición por medición
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("script, nombre", [
    ("comparar_pasadas.py", "destino_por_senal"),
    ("comparar_correlacionador.py", "TIPOLOGIA"),
    ("estimar_costo.py", "SENALES_POR_QUINCENA_18"),
])
def test_los_scripts_importan_la_definicion_en_vez_de_copiarla(script, nombre):
    """Dos copias de la misma medición envejecen por separado (H-034)."""
    fuente = (RAIZ / "scripts" / script).read_text(encoding="utf-8")
    assert re.search(rf"from territorial\.informes\.\w+ import[^\n]*\b{nombre}\b"
                     rf"|from territorial\.informes\.\w+ import \([^)]*\b{nombre}\b", fuente)
    assert not re.search(rf"^(def {nombre}\b|{nombre} = )", fuente, re.MULTILINE)


# ---------------------------------------------------------------------------
# La plantilla no lleva cifras escritas a mano
# ---------------------------------------------------------------------------

#: Lo que sí puede llevar dígitos en la plantilla: los criterios del PRD y los
#: del tablero congelado, fechas, secciones, códigos del proyecto, despliegues,
#: rutas y código entre comillas.
PERMITIDOS = (r"≥(30|50|60|85)%", r"100%", r"≥ 1 de los 3 municipios", r"≤ 8 horas-persona",
              r"\d{4}-\d{2}-\d{2}", r"§\d+(\.\d+)?",
              r"\b8b\.1\b", r"\b[A-Z]+-?[A-Z]?\d+(\.\d+)?\b", r"gpt-5(\.4)?(-mini)?",
              r"\bv[124]\b", r"corte-ronda-\S+", r"\$py\b.*", r"`[^`]*`")
#: Forma de cifra medida: decimales, miles, porcentajes, números largos y
#: conteos del tipo «53 de 67» o «53 de sus 67», que son dos cifras cortas.
SOSPECHOSO = re.compile(
    r"\d+,\d+|\d{1,3}(?:\.\d{3})+|\d+\s?%|\b\d{3,}\b|\b\d+ de (?:sus |las |los )?\d+\b")


def _cifras_a_mano(texto: str) -> list[str]:
    texto = re.sub(r"## Lo retirado.*?\n---\n", "", texto, flags=re.DOTALL)
    texto = r.HUECO.sub("", texto)
    for permitido in PERMITIDOS:
        texto = re.sub(permitido, "", texto)
    return SOSPECHOSO.findall(texto)


def test_la_guarda_de_cifras_a_mano_detecta_de_verdad():
    """Contra casos que sabemos malos, incluido el que sí se coló: «53 de sus 67».
    Una guarda que nunca ha fallado no ha demostrado que detecte nada."""
    for malo in ("sobrevive el 98,8 %", "permitía: 53 de sus 67 procedencias",
                 "con 1.140 evidencias", "un 30 % de", "son 615 señales", "7 de 15"):
        assert _cifras_a_mano(malo), f"la guarda deja pasar {malo!r}"
    for bueno in ("≥30% de insights **[EST]**", "H-034 y CA-M4.1", "el 2026-10-01",
                  "{{h1p_prd}}", "en el PRD §9", "`gpt-5.4-mini`"):
        assert not _cifras_a_mano(bueno), f"la guarda acusa en falso {bueno!r}"


def test_la_plantilla_no_lleva_cifras_medidas_escritas_a_mano():
    """Las cifras van en huecos `{{…}}`. Fuera de la sección de lo retirado
    —que cita las afirmaciones viejas para decir por qué salen— no puede haber
    ninguna con forma de cifra medida."""
    sospechosos = _cifras_a_mano(r.PLANTILLA.read_text(encoding="utf-8"))
    assert not sospechosos, f"cifras escritas a mano en la plantilla: {sospechosos}"
