"""Fijezas comunes a todas las pruebas.

Lo único que hay aquí es una defensa contra un acoplamiento que apareció el
2026-09-21, al aprobar la bajada del peso de F4: `config/pesos.json` entró al
repositorio y **las pruebas empezaron a puntuar con los pesos de negocio**. Dos
que afirmaban sobre la redistribución fallaron, y las que no fallaron pasaron a
verificar la calibración vigente en vez del algoritmo.

Eso invierte para qué existe cada cosa. El archivo de pesos es la palanca que
CA-M5.3 le da a Gerencia para cambiar el score sin tocar código; si además
mueve las pruebas, cada recalibración rompe el suite por motivos que no son
defectos, y el suite deja de avisar cuando el defecto es real.

Así que las pruebas corren siempre contra los pesos **por defecto de D4**. Las
que quieran otros los construyen explícitamente con `Config(ruta_pesos=...)`,
que tiene prioridad sobre esto.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from territorial.config import obtener_config

CONFIG = Path(__file__).resolve().parents[1] / "config"

# El catálogo con el que corren las pruebas. **No es el de producción**, por la
# misma razón que los pesos: `config/gerencias.json` es una palanca de negocio
# —quién forma el núcleo del experimento— y si además moviera el suite, cada
# cambio de gerencias rompería pruebas por algo que no es un defecto. Las que
# quieran otro catálogo lo construyen con `Config(ruta_gerencias=...)`, que
# tiene prioridad; y la que fija el catálogo **real** lo hace a propósito.
GERENCIAS_DE_PRUEBA = {
    "gerencias": [
        {"id_gerencia": "comercial", "nombre": "Comercial", "tipo": "prd"},
        {"id_gerencia": "desarrollo", "nombre": "Desarrollo", "tipo": "prd"},
        {"id_gerencia": "activos", "nombre": "Activos", "tipo": "adicional"},
    ]
}


@pytest.fixture(autouse=True)
def pesos_de_d4(monkeypatch):
    """Apunta `ruta_pesos` a un archivo que no existe: rigen los de `pesos.py`."""
    monkeypatch.setenv("RUTA_PESOS", "config/pesos-que-no-existe-en-pruebas.json")


@pytest.fixture(autouse=True)
def catalogo_de_prueba(tmp_path_factory, monkeypatch):
    """Apunta `ruta_gerencias` a un catálogo de prueba, no al de producción."""
    ruta = tmp_path_factory.mktemp("config") / "gerencias.json"
    ruta.write_text(json.dumps(GERENCIAS_DE_PRUEBA), encoding="utf-8")
    monkeypatch.setenv("RUTA_GERENCIAS", str(ruta))
    # `obtener_config` está cacheada: sin limpiar, la variable no llegaría.
    obtener_config.cache_clear()
    yield
    obtener_config.cache_clear()


def _huella_config() -> dict[str, str]:
    if not CONFIG.is_dir():
        return {}
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(CONFIG.iterdir())
        if p.is_file()
    }


@pytest.fixture(autouse=True)
def config_intacta():
    """Ninguna prueba puede tocar `config/`. Se comprueba antes y después de cada una.

    `config/` es configuración **real y en producción**: los pesos que puntúan,
    las tarifas con las que se estima H5, el catálogo de gerencias que decide
    sobre quién se reporta H2 y la lista de quién puede calificar. Una prueba que
    escriba ahí no rompe una prueba: **cambia el experimento**, y lo hace en
    silencio, porque el suite seguiría en verde.

    Por qué existe esta guarda: el 2026-09-22 `config/gerencias.json` y
    `config/usuarios.csv` **desaparecieron del disco** a media sesión. Se
    investigó y **no se encontró la causa** —ningún código de `tests/`,
    `scripts/` ni `src/` escribe, mueve o borra bajo `config/`, y el suite
    completo deja los cuatro archivos con el mismo hash y el mismo mtime—. Esto
    no arregla aquello: **es el detector que faltaba**. Si vuelve a pasar desde
    dentro del suite, lo dirá la prueba que lo hizo, en vez de descubrirse tres
    pasos después con un catálogo vacío.

    Lo que una prueba necesite escribir va a `tmp_path`, y la ruta se apunta ahí
    con `Config(ruta_gerencias=...)` o con `monkeypatch.setenv`, nunca al archivo
    real. Leerlo sí está bien: hay pruebas que fijan el contenido real a
    propósito.
    """
    antes = _huella_config()
    yield
    despues = _huella_config()
    if antes == despues:
        return

    faltan = sorted(set(antes) - set(despues))
    sobran = sorted(set(despues) - set(antes))
    cambiados = sorted(n for n in set(antes) & set(despues) if antes[n] != despues[n])
    detalle = "; ".join(
        parte for parte in (
            f"desaparecieron {faltan}" if faltan else "",
            f"aparecieron {sobran}" if sobran else "",
            f"cambiaron {cambiados}" if cambiados else "",
        ) if parte
    )
    raise AssertionError(
        f"esta prueba tocó config/, que es configuración real: {detalle}. "
        "Escribe en tmp_path y apunta la ruta ahí (Config(ruta_...=...) o "
        "monkeypatch.setenv). Recupera lo perdido con: git checkout -- config/"
    )
