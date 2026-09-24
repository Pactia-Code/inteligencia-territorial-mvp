"""Ninguna pantalla puede quedarse sin puerta de entrada.

Desde el 2026-09-24 se entra con el correo antes de leer. La comprobación vive
en `exigirIdentidad`, que cada página llama al empezar.

**Eso es una convención, y las convenciones se olvidan.** Una página nueva que
no la llame queda abierta a cualquiera con el enlace, y no lo detectaría ni
`tsc` ni el suite: se vería perfecta. Es el mismo patrón que dejó `/priorizados`
rota con tres comprobaciones en verde, así que se resuelve igual — con una
guarda que recorre lo que hay en disco en vez de fiarse de que alguien se
acuerde.

`/entrar` es la única excepción, por razones evidentes.

Y aparte se lanza `destino.prueba.mts`, que cubre la redirección abierta: el
destino al que se vuelve después de entrar lo escribe quien manda el enlace.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web"
APP = WEB / "app"

#: La pantalla de entrada no puede exigir haber entrado.
SIN_PUERTA = {"entrar"}

sin_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node no está en el PATH"
)


def _paginas() -> list[Path]:
    return sorted(APP.glob("**/page.tsx"))


def _ruta_de(pagina: Path) -> str:
    """`app/priorizados/page.tsx` -> `priorizados`; la raíz -> `""`."""
    return pagina.parent.relative_to(APP).as_posix().strip(".")


def test_hay_paginas_que_revisar():
    """Si el glob deja de encontrar nada, el resto pasaría en falso."""
    assert len(_paginas()) >= 5, [p.name for p in _paginas()]


def test_existe_la_pantalla_de_entrada():
    assert (APP / "entrar" / "page.tsx").exists()


@pytest.mark.parametrize("pagina", _paginas(), ids=_ruta_de)
def test_toda_pagina_exige_identidad(pagina: Path):
    ruta = _ruta_de(pagina)
    texto = pagina.read_text(encoding="utf-8")
    llama = "exigirIdentidad(" in texto

    if ruta.split("/")[0] in SIN_PUERTA:
        assert not llama, (
            f"/{ruta} es la pantalla de entrada: no puede exigir haber entrado"
        )
        return

    assert llama, (
        f"/{ruta} no llama a `exigirIdentidad`, así que se puede abrir sin "
        f"identificarse. Añádela al principio de la página, con la ruta a la "
        f"que volver."
    )


def test_la_vista_de_ciclo_ya_no_pide_el_correo():
    """El formulario de identificación se retiró: la identidad viene de /entrar.

    Se comprueba que no queda ni el componente ni una referencia colgando, que
    es como se cuela un import a un archivo borrado.
    """
    assert not (APP / "ciclo" / "[id]" / "Identificarse.tsx").exists()
    sueltas = [
        p.relative_to(RAIZ).as_posix()
        for p in list(APP.glob("**/*.tsx")) + list(WEB.glob("lib/**/*.ts"))
        if "Identificarse" in p.read_text(encoding="utf-8")
    ]
    assert not sueltas, sueltas


def test_la_cookie_y_la_firma_son_las_de_f0_3():
    """No se inventa un mecanismo nuevo de identidad para la entrada.

    `entrar` reusa `identificarse`, que es quien comprueba contra `usuario`,
    firma la cookie y registra la fila en `identificacion`. Si alguien
    reimplementara eso aparte, la fila dejaría de escribirse y nadie lo notaría
    hasta auditar una calificación discutida.
    """
    acciones = (APP / "acciones.ts").read_text(encoding="utf-8")
    cuerpo = re.search(
        r"export async function entrar\((.|\n)*?\n}", acciones
    )
    assert cuerpo, "no se encontró la acción `entrar`"
    assert "identificarse(" in cuerpo.group(0), (
        "`entrar` no reusa `identificarse`: la fila de `identificacion` y la "
        "firma de la cookie tienen que seguir viniendo de F0.3"
    )


def test_el_destino_se_sanea_antes_de_redirigir():
    """Una redirección abierta en la pantalla de entrada es de las peores."""
    acciones = (APP / "acciones.ts").read_text(encoding="utf-8")
    assert "destinoSeguro(" in acciones, (
        "`entrar` redirige sin sanear el destino que viene del formulario"
    )
    entrada = (APP / "entrar" / "page.tsx").read_text(encoding="utf-8")
    assert "destinoSeguro(" in entrada


@sin_node
def test_las_reglas_del_destino_se_cumplen():
    proceso = subprocess.run(
        ["node", "--experimental-strip-types", str(WEB / "lib" / "destino.prueba.mts")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=RAIZ,
    )
    assert proceso.returncode == 0, proceso.stdout + proceso.stderr
    assert "todas pasan" in proceso.stdout, proceso.stdout
