"""Los modulos puros de la app son TypeScript, y aun asi corren aqui.

F0.4 (H-013) puso en `web/lib/alcance.ts` quién puede escribir qué, y F0.7
(H-045) puso en `web/lib/mensajes.ts` qué se le dice a alguien cuando no se
guarda. Las dos son lógicas que no pueden quedarse sin comprobación
automática —una decide quién escribe, la otra decide si un fallo se ve—, pero
el proyecto no tiene corredor de pruebas de TypeScript y montar uno para un
puñado de funciones puras habría sido más infraestructura que la que se prueba.

Esto lanza con Node cada `web/lib/*.prueba.mts` y exige que salga en verde. Si
alguien relaja una regla o añade un motivo sin texto, el suite de Python se
entera.

Se **salta** si no hay Node en el PATH: el pipeline no lo necesita para nada
más y no vale la pena volverlo un requisito. Un salto se ve en la salida de
pytest; un falso verde, no.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
PRUEBAS = sorted((RAIZ / "web" / "lib").glob("*.prueba.mts"))

sin_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node no está en el PATH"
)


def test_hay_pruebas_que_correr():
    """Si el glob deja de encontrar nada, el resto pasaría en falso."""
    assert PRUEBAS, "no se encontró ningún web/lib/*.prueba.mts"


@sin_node
@pytest.mark.parametrize("ruta", PRUEBAS, ids=lambda p: p.name)
def test_el_modulo_puro_pasa_sus_comprobaciones(ruta: Path):
    proceso = subprocess.run(
        ["node", "--experimental-strip-types", str(ruta)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=RAIZ,
    )
    assert proceso.returncode == 0, proceso.stdout + proceso.stderr
    assert "todas pasan" in proceso.stdout, proceso.stdout
