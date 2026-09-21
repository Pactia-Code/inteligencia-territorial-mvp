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

import pytest


@pytest.fixture(autouse=True)
def pesos_de_d4(monkeypatch):
    """Apunta `ruta_pesos` a un archivo que no existe: rigen los de `pesos.py`."""
    monkeypatch.setenv("RUTA_PESOS", "config/pesos-que-no-existe-en-pruebas.json")
