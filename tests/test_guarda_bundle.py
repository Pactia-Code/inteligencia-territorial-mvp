"""La guarda que impide que la base de datos viaje al navegador.

**El fallo que la motiva no lo ve ninguna de las comprobaciones que ya
teníamos.** Una línea —`import { EXIGEN_NOTA } from "@/lib/tablero"` en un
componente `"use client"`— arrastraba `lib/db.ts` y el driver de Neon a
`.next/static`. Allí `process.env.DATABASE_URL` no existe nunca, así que el
módulo lanzaba al evaluarse y tumbaba `/priorizados` en cualquier navegador.

Y sin embargo: `tsc --noEmit` pasaba, `next build` pasaba y `curl` devolvía
**200 con el HTML correcto**, porque el servidor renderiza bien y curl no
ejecuta JavaScript. Tres verdes y la página rota.

Aquí se comprueban dos cosas distintas, y la primera importa más de lo que
parece:

1. **Que la guarda detecta.** Se le da un fragmento que sabemos malo y otro que
   sabemos bueno. Una guarda que nunca ha fallado no ha demostrado nada, y el
   modo de fallo silencioso —que deje de detectar y siga diciendo «limpio»— es
   exactamente el que nos costó esta página.
2. **Que el código fuente no vuelve a crear el camino.** Ningún componente de
   cliente puede importar de un módulo que toque la base. Esto se lee del
   fuente y no necesita build, así que corre siempre.

La comprobación sobre el build real vive en `npm run build`, que encadena
`verificar_bundle.mjs`. Aquí no se construye: `next build` tarda y necesita
Node y `node_modules`, y esto tiene que poder correr en cualquier sitio.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web"
GUARDA = WEB / "scripts" / "verificar_bundle.mjs"

sin_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node no está en el PATH"
)

#: Módulos de `web/lib` que abren conexión. Importarlos desde el cliente es el
#: fallo. Se detectan por su import de `./db`, no por una lista a mano.
def _modulos_con_base() -> set[str]:
    modulos = set()
    for ruta in (WEB / "lib").glob("*.ts"):
        texto = ruta.read_text(encoding="utf-8")
        if re.search(r'from\s+"\./db"', texto):
            modulos.add(ruta.stem)
    return modulos


def _componentes_de_cliente() -> list[Path]:
    return [
        ruta
        for ruta in list(WEB.glob("app/**/*.tsx")) + list(WEB.glob("lib/**/*.ts"))
        if ruta.read_text(encoding="utf-8").lstrip().startswith('"use client"')
    ]


def test_la_guarda_existe_y_esta_enganchada_al_build():
    assert GUARDA.exists(), "falta web/scripts/verificar_bundle.mjs"
    package = (WEB / "package.json").read_text(encoding="utf-8")
    assert "verificar_bundle.mjs" in package, (
        "la guarda existe pero no corre: engánchala al script `build` de "
        "web/package.json, o no protegerá ningún despliegue"
    )


def test_se_reconocen_los_modulos_que_tocan_la_base():
    """Si el detector deja de encontrarlos, el resto pasaría en falso."""
    con_base = _modulos_con_base()
    assert "db" not in con_base  # `db.ts` no se importa a sí mismo
    assert {"tablero", "consultas", "escrituras"} <= con_base, con_base


def test_hay_componentes_de_cliente_que_revisar():
    assert _componentes_de_cliente(), "no se encontró ningún componente de cliente"


@pytest.mark.parametrize(
    "ruta", _componentes_de_cliente(), ids=lambda p: p.name
)
def test_un_componente_de_cliente_no_importa_nada_con_base(ruta: Path):
    """La regla que se rompió: `"use client"` + módulo con base = página caída.

    Se mira el import directo, que es como entró el fallo. La cadena indirecta
    la cubre la guarda sobre el build.
    """
    prohibidos = _modulos_con_base() | {"db"}
    texto = ruta.read_text(encoding="utf-8")
    for modulo in sorted(prohibidos):
        patron = rf'^import\s[^;]*\sfrom\s+"(@/lib/{modulo}|\./{modulo}|\.\./lib/{modulo})"'
        encontrado = re.search(patron, texto, re.MULTILINE)
        assert not encontrado, (
            f"{ruta.relative_to(RAIZ)} es un componente de cliente e importa "
            f"`{modulo}`, que toca la base. Eso arrastra el driver al navegador "
            f"y tumba la página. Saca lo que necesites a un módulo sin "
            f"dependencias de servidor, como `web/lib/estados.ts`."
        )


@sin_node
def test_la_guarda_detecta_de_verdad():
    """Contra un caso malo y uno bueno. Sin esto, «limpio» no significa nada."""
    proceso = subprocess.run(
        ["node", str(GUARDA), "--probar"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=WEB,
    )
    assert proceso.returncode == 0, proceso.stdout + proceso.stderr
    assert "guarda probada" in proceso.stdout, proceso.stdout


@sin_node
def test_la_guarda_falla_si_no_hay_build_en_vez_de_decir_que_esta_limpio():
    """El modo de fallo peligroso es el falso verde.

    Si `.next/static` no existe, tiene que salir con error y decirlo, no
    imprimir «bundle limpio» porque no encontró nada que revisar.
    """
    proceso = subprocess.run(
        ["node", str(GUARDA)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(RAIZ),  # sin `.next/` aquí
    )
    assert proceso.returncode == 2, proceso.stdout + proceso.stderr
    assert "limpio" not in proceso.stdout
