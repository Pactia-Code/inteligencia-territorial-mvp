"""Carga el snapshot territorial a la base de datos y al almacén de objetos.

Uso:
    %LOCALAPPDATA%\\venvs\\territorial\\Scripts\\python.exe scripts\\cargar_snapshot.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Permite ejecutar el script sin instalar el paquete.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from territorial.config import obtener_config  # noqa: E402
from territorial.ingesta.snapshot import cargar  # noqa: E402


def main() -> int:
    cfg = obtener_config()
    ruta = cfg.ruta_absoluta(cfg.ruta_snapshot)

    if not ruta.exists():
        print(f"ERROR: no se encontró el snapshot en {ruta}", file=sys.stderr)
        return 1

    print(f"Snapshot : {ruta}")
    print(f"Almacén  : {cfg.modo_almacen}")
    print(f"Base     : {cfg.url_base_datos}")
    print("\nVentanas de ciclo (Addendum 01, D2):")
    for num, (desde, hasta) in cfg.ventanas_ciclo.items():
        print(f"  ciclo {num}: {desde} → {hasta} (fin exclusivo)")
    print("\nCargando...\n")

    inicio = time.perf_counter()
    resumen = cargar(cfg)
    print(resumen)
    print(f"\nCompletado en {time.perf_counter() - inicio:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
