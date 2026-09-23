"""El avance de la ronda tiene que contar lo pedido, y por los dos ejes.

Lo que más importa probar no es la aritmética, sino las dos confusiones que
harían tomar una decisión equivocada durante la ronda:

  · contar sobre los 241 insights del informe en vez de sobre los 15 pedidos,
    que haría parecer que nadie avanza;
  · mezclar «por persona» con «por gerencia», que son ejes distintos y solo
    coinciden mientras haya una persona por gerencia.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def script():
    ruta = RAIZ / "scripts" / "avance_calificacion.py"
    spec = importlib.util.spec_from_file_location("avance_calificacion", ruta)
    modulo = importlib.util.module_from_spec(spec)
    # `@dataclass` resuelve sus anotaciones mirando `sys.modules`.
    sys.modules["avance_calificacion"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


PEDIDOS = [101, 102, 103, 104, 105, 201, 202, 203, 204, 205]

USUARIOS = [
    {"id": 1, "correo": "a@p.co", "nombre": "A", "id_gerencia": "general",
     "tipo_gerencia": "prd"},
    {"id": 2, "correo": "b@p.co", "nombre": "B", "id_gerencia": "juridica",
     "tipo_gerencia": "prd"},
]


def calificacion(insight, gerencia, usuario, comentario=None):
    return {"id_insight": insight, "id_gerencia": gerencia,
            "id_usuario": usuario, "comentario": comentario}


# --------------------------------------------------------------------------
# El denominador es lo pedido
# --------------------------------------------------------------------------


def test_el_denominador_son_los_insights_pedidos(script):
    filas = script.avance(PEDIDOS, USUARIOS, [])
    assert [f.de for f in filas] == [10, 10]
    assert [f.calificados for f in filas] == [0, 0]


def test_los_pedidos_salen_solo_de_los_municipios_calificables(script):
    payload = {"municipios": [
        {"calificable": True, "insights_pedidos": [1, 2, 3, 4, 5]},
        {"calificable": True, "insights_pedidos": [6, 7, 8, 9, 10]},
        {"calificable": False, "insights_pedidos": []},
        {"calificable": False, "insights_pedidos": [99]},  # no debería pasar
    ]}
    assert script.pedidos_del_payload(payload) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


def test_una_calificacion_fuera_de_lo_pedido_no_suma(script):
    """No debería existir —el servidor la rechaza— y si aparece, que no cuadre."""
    filas = script.avance(
        PEDIDOS, USUARIOS,
        [calificacion(999, "general", 1), calificacion(101, "general", 1)],
    )
    assert filas[0].calificados == 1


def test_el_porcentaje_sale_del_pedido(script):
    filas = script.avance(
        PEDIDOS, USUARIOS,
        [calificacion(p, "general", 1) for p in PEDIDOS[:5]],
    )
    assert filas[0].porcentaje == 50.0


def test_sin_pedidos_no_se_divide_por_cero(script):
    filas = script.avance([], USUARIOS, [])
    assert [f.porcentaje for f in filas] == [0.0, 0.0]


# --------------------------------------------------------------------------
# Persona y gerencia no son el mismo eje
# --------------------------------------------------------------------------


def test_cuenta_por_persona_no_por_gerencia(script):
    """Dos personas de la misma gerencia tienen avances distintos."""
    usuarios = USUARIOS + [
        {"id": 3, "correo": "c@p.co", "nombre": "C", "id_gerencia": "general",
         "tipo_gerencia": "prd"},
    ]
    califs = [calificacion(101, "general", 1), calificacion(102, "general", 3)]
    por_correo = {f.correo: f.calificados for f in script.avance(PEDIDOS, usuarios, califs)}
    assert por_correo == {"a@p.co": 1, "b@p.co": 0, "c@p.co": 1}


def test_por_gerencia_suma_lo_de_todas_sus_personas(script):
    """El eje de H1 y H2: a quién se atribuye, no quién tecleó."""
    califs = [calificacion(101, "general", 1), calificacion(102, "general", 3),
              calificacion(201, "juridica", 2)]
    assert script.por_gerencia(PEDIDOS, califs) == {"general": 2, "juridica": 1}


def test_por_gerencia_ignora_lo_no_pedido(script):
    califs = [calificacion(999, "general", 1), calificacion(101, "general", 1)]
    assert script.por_gerencia(PEDIDOS, califs) == {"general": 1}


def test_solo_aparecen_los_calificadores(script):
    """Un administrador con 0 de 15 al lado se leería como retrasado, y no lo es.

    La lista de usuarios ya llega filtrada a rol `gerencia` y activos; esto fija
    que la función no añade a nadie por su cuenta.
    """
    filas = script.avance(PEDIDOS, USUARIOS, [calificacion(101, "analitica", 9)])
    assert {f.correo for f in filas} == {"a@p.co", "b@p.co"}
    assert sum(f.calificados for f in filas) == 0


# --------------------------------------------------------------------------
# Detalles que se leen durante la ronda
# --------------------------------------------------------------------------


def test_los_comentarios_se_cuentan_aparte_y_solo_si_traen_texto(script):
    califs = [
        calificacion(101, "general", 1, "esto sí"),
        calificacion(102, "general", 1, "   "),
        calificacion(103, "general", 1, None),
    ]
    fila = script.avance(PEDIDOS, USUARIOS, califs)[0]
    assert (fila.calificados, fila.comentarios) == (3, 1)


def test_el_orden_es_por_gerencia_y_correo(script):
    """Para poder leer la tabla de un vistazo durante la reunión."""
    usuarios = [
        {"id": 1, "correo": "z@p.co", "nombre": "Z", "id_gerencia": "juridica",
         "tipo_gerencia": "prd"},
        {"id": 2, "correo": "a@p.co", "nombre": "A", "id_gerencia": "juridica",
         "tipo_gerencia": "prd"},
        {"id": 3, "correo": "m@p.co", "nombre": "M", "id_gerencia": "general",
         "tipo_gerencia": "prd"},
    ]
    filas = script.avance(PEDIDOS, usuarios, [])
    assert [f.correo for f in filas] == ["m@p.co", "a@p.co", "z@p.co"]


def test_el_script_no_escribe_en_la_base(script):
    """Solo lectura, y comprobado sobre el propio archivo.

    Se buscan las formas con las que este proyecto escribe —mutar la sesión o
    mandar SQL de escritura— y no la palabra «insert» suelta, que aparece en
    `sys.path.insert` y haría fallar la prueba por algo que no es una escritura.
    """
    fuente = (RAIZ / "scripts" / "avance_calificacion.py").read_text(encoding="utf-8")
    codigo = "\n".join(
        l for l in fuente.split("\n") if not l.strip().startswith(("#", "·", '"'))
    )
    prohibidos = [
        ".add(", ".add_all(", ".merge(", ".commit(", ".flush(", ".execute(",
        "INSERT ", "UPDATE ", "DELETE ", "sqlalchemy import insert",
        "sqlalchemy import update", "sqlalchemy import delete",
    ]
    encontrados = [p for p in prohibidos if p in codigo]
    assert not encontrados, f"el script podría escribir: {encontrados}"
    # Y lo que sí hace: leer.
    assert "select(" in codigo
