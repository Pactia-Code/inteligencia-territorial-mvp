"""Las reglas de alcance de la app viven en TypeScript, y aun así corren aquí.

F0.4 (H-013) puso en `web/lib/alcance.ts` quién puede escribir qué. Es lógica
de autorización, así que dejarla sin comprobar automática no era una opción,
pero el proyecto no tiene corredor de pruebas de TypeScript y montar uno para
tres funciones puras habría sido más infraestructura que la que se prueba.

Esto lanza `web/lib/alcance.prueba.mts` con Node y exige que salga en verde. Si
alguien relaja una regla, el suite de Python se entera.

Se **salta** si no hay Node en el PATH: el pipeline no lo necesita para nada
más y no vale la pena volverlo un requisito de ejecutar las pruebas del
pipeline. Un salto se ve en la salida de pytest; un falso verde, no.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
PRUEBA = RAIZ / "web" / "lib" / "alcance.prueba.mts"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node no está en el PATH")
def test_las_reglas_de_alcance_de_la_app_pasan():
    assert PRUEBA.exists(), f"falta {PRUEBA.relative_to(RAIZ)}"
    proceso = subprocess.run(
        ["node", "--experimental-strip-types", str(PRUEBA)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=RAIZ,
    )
    assert proceso.returncode == 0, proceso.stdout + proceso.stderr
    assert "todas pasan" in proceso.stdout, proceso.stdout
