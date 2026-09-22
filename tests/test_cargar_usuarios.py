"""La carga de usuarios decide el denominador de H2, así que valida antes de escribir.

Lo que más importa probar no es que el CSV se lea, sino las tres reglas que
evitan que la ventana de calificación empiece con un universo que nadie decidió:

  · una fila inválida **impide la carga entera**, no solo la suya;
  · una `id_gerencia` no declarada en `config/gerencias.json` no entra;
  · quien desaparece del archivo **se desactiva, no se borra**.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from territorial.almacen.modelos import Base, Usuario
from territorial.config import Config
from territorial.informes.gerencias import cargar as cargar_gerencias

RAIZ = Path(__file__).resolve().parents[1]
CSV_REAL = RAIZ / "config" / "usuarios.csv"

CABECERA = "nombre;id_gerencia;cargo;correo;puede_calificar;es_administrador"


@pytest.fixture(scope="module")
def script():
    ruta = RAIZ / "scripts" / "cargar_usuarios.py"
    spec = importlib.util.spec_from_file_location("cargar_usuarios", ruta)
    modulo = importlib.util.module_from_spec(spec)
    # `@dataclass` resuelve sus anotaciones mirando `sys.modules`, así que un
    # módulo cargado a mano tiene que estar registrado antes de ejecutarlo.
    sys.modules["cargar_usuarios"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def catalogo():
    return cargar_gerencias(Config(ruta_gerencias=RAIZ / "config" / "gerencias.json"))


@pytest.fixture
def csv_con(tmp_path):
    def escribir(*lineas: str) -> Path:
        ruta = tmp_path / "usuarios.csv"
        ruta.write_text("\n".join((CABECERA, *lineas)) + "\n", encoding="utf-8")
        return ruta
    return escribir


@pytest.fixture
def bd():
    motor = create_engine("sqlite://", future=True)
    Base.metadata.create_all(motor)
    with Session(motor) as s:
        yield s


# --------------------------------------------------------------------------
# El archivo real
# --------------------------------------------------------------------------


def test_el_csv_real_se_lee_entero_y_con_los_roles_esperados(script, catalogo):
    """Si esto falla, la carga de la ventana de calificación no arrancaría."""
    filas = script.leer(CSV_REAL, catalogo)
    por_correo = {f["correo"]: f for f in filas}
    assert len(filas) == len(por_correo)
    assert por_correo["wsanchez@pactia.com"]["rol"] == "gerencia"
    assert por_correo["wsanchez+admin@pactia.com"]["rol"] == "administrador"
    # Las cinco «prd» tienen quien las califique; sin eso H2 no se puede medir.
    califican = {f["id_gerencia"] for f in filas if f["rol"] == "gerencia"}
    assert {g.id_gerencia for g in catalogo.values() if g.tipo == "prd"} <= califican


def test_el_cargo_vacio_queda_en_nulo_no_en_cadena_vacia(script, catalogo):
    filas = {f["correo"]: f for f in script.leer(CSV_REAL, catalogo)}
    assert filas["abejarano@pactia.com"]["cargo"] is None
    assert filas["egomez@pactia.com"]["cargo"] == "Gerente de Logística"


# --------------------------------------------------------------------------
# Validación: una fila mala tumba la carga entera
# --------------------------------------------------------------------------


def test_las_dos_marcas_en_si_son_error(script, catalogo, csv_con):
    """Son roles distintos y el sistema no elige por la persona."""
    ruta = csv_con("A;general;;a@pactia.com;si;si")
    with pytest.raises(script.UsuariosInvalidos, match="no pueden ser los dos"):
        script.leer(ruta, catalogo)


def test_las_dos_marcas_en_no_avisan_de_que_el_rol_no_existe(script, catalogo, csv_con):
    """Solo lectura no es un rol de la base; hay que decidir crearlo."""
    ruta = csv_con("A;general;;a@pactia.com;no;no")
    with pytest.raises(script.UsuariosInvalidos, match="no existe"):
        script.leer(ruta, catalogo)


def test_una_gerencia_no_declarada_no_entra(script, catalogo, csv_con):
    """Entraría como «adicional» sin que nadie lo hubiera decidido."""
    ruta = csv_con("A;financiera;;a@pactia.com;si;no")
    with pytest.raises(script.UsuariosInvalidos, match="no está declarada"):
        script.leer(ruta, catalogo)


def test_un_correo_repetido_no_entra(script, catalogo, csv_con):
    ruta = csv_con(
        "A;general;;a@pactia.com;si;no",
        "B;juridica;;A@PACTIA.COM;si;no",
    )
    with pytest.raises(script.UsuariosInvalidos, match="ya está en la línea"):
        script.leer(ruta, catalogo)


def test_una_marca_que_no_es_si_ni_no_es_error(script, catalogo, csv_con):
    ruta = csv_con("A;general;;a@pactia.com;quizá;no")
    with pytest.raises(script.UsuariosInvalidos, match="se esperaba si o no"):
        script.leer(ruta, catalogo)


def test_la_fila_mala_impide_leer_tambien_las_buenas(script, catalogo, csv_con):
    """La carga es todo o nada: media lista es un denominador que nadie decidió."""
    ruta = csv_con(
        "A;general;;a@pactia.com;si;no",
        "B;juridica;;b@pactia.com;si;si",
        "C;analitica;;c@pactia.com;si;no",
    )
    with pytest.raises(script.UsuariosInvalidos):
        script.leer(ruta, catalogo)


def test_falta_una_columna_y_lo_dice_con_el_formato_esperado(script, catalogo, tmp_path):
    ruta = tmp_path / "usuarios.csv"
    ruta.write_text("correo;rol\na@pactia.com;gerencia\n", encoding="utf-8")
    with pytest.raises(script.UsuariosInvalidos, match="faltan columnas"):
        script.leer(ruta, catalogo)


def test_el_separador_es_punto_y_coma_no_coma(script, catalogo, tmp_path):
    """Con comas, el lector ve una sola columna y hay que decirlo claro."""
    ruta = tmp_path / "usuarios.csv"
    ruta.write_text(
        "nombre,id_gerencia,cargo,correo,puede_calificar,es_administrador\n"
        "A,general,,a@pactia.com,si,no\n",
        encoding="utf-8",
    )
    with pytest.raises(script.UsuariosInvalidos, match="faltan columnas"):
        script.leer(ruta, catalogo)


# --------------------------------------------------------------------------
# El plan y su aplicación
# --------------------------------------------------------------------------


def test_el_plan_distingue_alta_cambio_desactivacion_y_reactivacion(script, bd):
    bd.add_all([
        Usuario(correo="queda@pactia.com", nombre="Queda", id_gerencia="general",
                rol="gerencia"),
        Usuario(correo="cambia@pactia.com", nombre="Viejo", id_gerencia="general",
                rol="gerencia"),
        Usuario(correo="vuelve@pactia.com", nombre="Vuelve", id_gerencia="juridica",
                rol="gerencia", activo=False),
        Usuario(correo="se_va@pactia.com", nombre="Se va", id_gerencia="juridica",
                rol="gerencia"),
    ])
    bd.flush()

    filas = [
        {"correo": "queda@pactia.com", "nombre": "Queda", "id_gerencia": "general",
         "cargo": None, "rol": "gerencia"},
        {"correo": "cambia@pactia.com", "nombre": "Nuevo", "id_gerencia": "general",
         "cargo": "Jefe", "rol": "gerencia"},
        {"correo": "vuelve@pactia.com", "nombre": "Vuelve", "id_gerencia": "juridica",
         "cargo": None, "rol": "gerencia"},
        {"correo": "nueva@pactia.com", "nombre": "Nueva", "id_gerencia": "analitica",
         "cargo": None, "rol": "gerencia"},
    ]
    plan = script.planificar(list(bd.query(Usuario).all()), filas)

    assert [a["correo"] for a in plan.altas] == ["nueva@pactia.com"]
    assert [u.correo for u, _ in plan.cambios] == ["cambia@pactia.com"]
    assert sorted(plan.cambios[0][1]) == ["cargo", "nombre"]
    assert [u.correo for u in plan.reactivaciones] == ["vuelve@pactia.com"]
    assert [u.correo for u in plan.desactivaciones] == ["se_va@pactia.com"]
    assert plan.iguales == 1


def test_quien_falta_en_el_archivo_se_desactiva_y_no_se_borra(script, bd):
    """Su calificación cuelga de su gerencia; borrarlo dejaría el denominador cojo."""
    bd.add(Usuario(correo="se_va@pactia.com", nombre="Se va", id_gerencia="general",
                   rol="gerencia"))
    bd.flush()

    plan = script.planificar(list(bd.query(Usuario).all()), [])
    script.aplicar(bd, plan, [])
    bd.flush()

    quedan = bd.query(Usuario).all()
    assert len(quedan) == 1
    assert quedan[0].activo is False


def test_aplicar_escribe_altas_cambios_y_reactivaciones(script, bd):
    bd.add(Usuario(correo="vuelve@pactia.com", nombre="Viejo", id_gerencia="general",
                   rol="gerencia", activo=False))
    bd.flush()
    filas = [
        {"correo": "vuelve@pactia.com", "nombre": "Nuevo", "id_gerencia": "juridica",
         "cargo": "Jefa", "rol": "administrador"},
        {"correo": "nueva@pactia.com", "nombre": "Nueva", "id_gerencia": "analitica",
         "cargo": None, "rol": "gerencia"},
    ]
    plan = script.planificar(list(bd.query(Usuario).all()), filas)
    script.aplicar(bd, plan, filas)
    bd.flush()

    vuelve = bd.query(Usuario).filter_by(correo="vuelve@pactia.com").one()
    assert (vuelve.activo, vuelve.nombre, vuelve.id_gerencia, vuelve.rol, vuelve.cargo) == (
        True, "Nuevo", "juridica", "administrador", "Jefa"
    )
    assert bd.query(Usuario).filter_by(correo="nueva@pactia.com").one().activo is True
