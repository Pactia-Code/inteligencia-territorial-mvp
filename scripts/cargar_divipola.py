r"""Carga el nomenclátor DIVIPOLA en `entidad_divipola`. Idempotente.

La lógica vive en `territorial.ingesta.nomenclator`, que es capa determinista y
se prueba sin base de datos. Esto es la línea de comandos y lo que se imprime.

El CSV de origen **no viaja en el repositorio** —`data/` está en `.gitignore`—
así que la ruta se pasa por `--csv` o por la variable `RUTA_DIVIPOLA`. No hay
ninguna ruta escrita en el código: si el archivo se mueve, no hay que tocar
esto.

Uso:

    $py scripts\cargar_divipola.py --csv data\divipola_terridata_1102.csv
    $py scripts\cargar_divipola.py --csv ... --homonimos data\homonimos_municipios.csv
    $env:RUTA_DIVIPOLA = "data\divipola_terridata_1102.csv"; $py scripts\cargar_divipola.py
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from territorial.almacen.sesion import aplicar_migraciones, sesion  # noqa: E402
from territorial.ingesta.nomenclator import (  # noqa: E402
    cargar,
    construir,
    homonimos,
    leer_csv,
)


def informe_homonimos(entidades: list[dict], ruta: Path | None) -> None:
    repes = homonimos(entidades)
    afectados = sum(len(c) for c in repes.values())
    municipios = sum(1 for e in entidades if e["tipo"] == "municipio")
    print(
        f"\nHomónimos: {len(repes)} nombres se repiten entre departamentos "
        f"y afectan a {afectados} municipios ({afectados / municipios:.0%})."
    )
    peores = sorted(repes.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:4]
    print("  los más repetidos: " + ", ".join(f"{n} ({len(c)})" for n, c in peores))
    print("  Resolver por nombre suelto es inviable: el par (departamento, "
          "municipio) es obligatorio.")

    if ruta and ruta.exists():
        with ruta.open(encoding="utf-8-sig", newline="") as f:
            esperados = {fila["municipio"].strip() for fila in csv.DictReader(f)}
        if esperados == set(repes):
            print(f"  concuerda con {ruta.name} ({len(esperados)} nombres)")
        else:
            print(f"  NO concuerda con {ruta.name}: "
                  f"{len(set(repes) - esperados)} de más, "
                  f"{len(esperados - set(repes))} de menos")


def main() -> int:
    p = argparse.ArgumentParser(description="Carga el nomenclátor DIVIPOLA")
    p.add_argument("--csv", default=os.environ.get("RUTA_DIVIPOLA"),
                   help="ruta del CSV; por defecto, la variable RUTA_DIVIPOLA")
    p.add_argument("--homonimos", help="CSV del spike, para contrastar el conteo")
    p.add_argument("--seco", action="store_true", help="calcula y no escribe nada")
    args = p.parse_args()

    if not args.csv:
        print("ERROR: falta la ruta del CSV. Pásala con --csv o en RUTA_DIVIPOLA.\n"
              "  data/ no viaja en el repositorio, así que no hay ruta por defecto.")
        return 1

    ruta = Path(args.csv)
    if not ruta.is_absolute():
        ruta = RAIZ / ruta
    if not ruta.exists():
        print(f"ERROR: no existe {ruta}")
        return 1

    entidades = construir(leer_csv(ruta))
    por_tipo = Counter(e["tipo"] for e in entidades)
    print(f"{ruta.name}: {len(entidades)} entidades")
    for tipo in ("nacional", "departamento", "municipio"):
        print(f"  {tipo:<14} {por_tipo[tipo]:>5}")

    ruta_hom = Path(args.homonimos) if args.homonimos else None
    if ruta_hom and not ruta_hom.is_absolute():
        ruta_hom = RAIZ / ruta_hom

    if args.seco:
        informe_homonimos(entidades, ruta_hom)
        print("\n[SECO] no se escribió nada.")
        return 0

    aplicar_migraciones()
    with sesion() as s:
        r = cargar(s, entidades)

    print(f"\ninsertadas {r.nuevas} · actualizadas {r.actualizadas} "
          f"· sin cambios {r.iguales}")
    if r.sobrantes:
        print(f"AVISO: {len(r.sobrantes)} entidades en la base que el CSV ya no trae "
              f"(no se borran): {r.sobrantes[:10]}")

    informe_homonimos(entidades, ruta_hom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
