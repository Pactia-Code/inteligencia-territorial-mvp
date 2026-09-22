"""El contrato TypeScript no puede quedarse atrás de `modelos.py`.

La app de M9 escribe directamente sobre Neon, y la regla 1 de D8 lo permite con
una condición: *«las escrituras de la app pasan por Python, o su forma se
verifica contra `modelos.py`»*. Esta prueba **es** esa verificación.

Sin ella, el mecanismo no sirve de nada: un generador que nadie ejecuta deja un
archivo obsoleto, que es exactamente el problema que venía a resolver —una
segunda fuente de verdad que envejece en silencio—. **Es el mismo papel que
`alembic check`**: comparar lo declarado contra lo real y fallar si divergen.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CONTRATO = RAIZ / "web" / "lib" / "contrato.generado.ts"


@pytest.fixture(scope="module")
def generador():
    ruta = RAIZ / "scripts" / "generar_contrato_ts.py"
    spec = importlib.util.spec_from_file_location("generar_contrato_ts", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_el_contrato_esta_al_dia(generador):
    """Si esto falla, corre `scripts/generar_contrato_ts.py` y revisa el diff.

    Falla cuando alguien toca `modelos.py` y no regenera. Ese es el escenario
    que el contrato existe para volver imposible: un campo cambia, las pruebas
    de Python siguen verdes, y la app escribe contra una columna que ya no
    existe.
    """
    assert CONTRATO.exists(), f"falta {CONTRATO.relative_to(RAIZ)}; regenera"
    assert CONTRATO.read_text(encoding="utf-8") == generador.generar(), (
        "el contrato TypeScript no concuerda con modelos.py. "
        "Corre: scripts/generar_contrato_ts.py"
    )


def test_solo_cubre_las_dos_tablas_que_la_app_escribe(generador):
    """CA-M9.16. Ampliarlo aquí sería ampliar lo que la app puede escribir."""
    assert generador.TABLAS == ("calificacion", "seguimiento")


def test_los_valores_del_check_llegan_como_union_de_tipos(generador):
    """Una errata en un estado tiene que ser error de compilación, no un 500.

    Si los estados viajaran como `string`, la app podría mandar uno inventado y
    enterarse cuando la base lo rechace — en la ventana de calificación.
    """
    ts = generador.generar()
    assert '"priorizado" | "en_revision" | "en_estructuracion" | "descartado"' in ts


def test_el_rango_de_la_calificacion_viaja_al_contrato(generador):
    """El 1-5 de CA-M7.2 lo impone la base; la app no debería redeclararlo."""
    ts = generador.generar()
    assert "VALOR_CALIFICACION_MIN = 1" in ts
    assert "VALOR_CALIFICACION_MAX = 5" in ts


def test_lo_escribible_excluye_la_clave_y_lo_que_tiene_default(generador):
    """La app no inventa identificadores ni fechas de creación."""
    ts = generador.generar()
    escribibles = ts.split("export type NuevaCalificacion = Pick<", 1)[1].split(">;", 1)[0]
    assert '"id_insight"' in escribibles
    assert '"valor"' in escribibles
    assert '"id"' not in escribibles
    assert '"creado_en"' not in escribibles


def test_el_generador_es_determinista(generador):
    """Mismo modelo, mismo texto: si no, el `--check` daría falsos positivos."""
    assert generador.generar() == generador.generar()


def test_el_archivo_avisa_de_que_no_se_edita_a_mano(generador):
    assert "NO EDITAR A MANO" in generador.generar()
