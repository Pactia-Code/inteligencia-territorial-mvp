"""Corre un ciclo completo y persiste el resultado (B6).

    prefiltro → Clasificador → Validador → persistir
              → Correlacionador → persistir

El scoring va aparte, en `calcular_scores.py`, porque no gasta tokens y se
recalcula cada vez que cambien los pesos.

Uso:
    & $py scripts\\correr_ciclo.py --ciclo 1 --municipio 05147   # uno, barato
    & $py scripts\\correr_ciclo.py --ciclo 1                     # los 18
    & $py scripts\\correr_ciclo.py --ciclo 1 --seco              # sin escribir

**Gasta tokens.** Los 18 municipios de un ciclo son 18 llamadas al Clasificador
más las del Correlacionador. Prueba primero con --municipio.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from territorial.almacen.modelos import Insight, TrazaAgente  # noqa: E402
from territorial.almacen.sesion import sesion  # noqa: E402
from territorial.ciclo import procesar_ciclo  # noqa: E402
from territorial.config import obtener_config  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Corre un ciclo completo (M2 → M3 → M4)")
    p.add_argument("--ciclo", type=int, default=1)
    p.add_argument("--municipio", action="append", help="DIVIPOLA; repetible")
    p.add_argument(
        "--lote", type=int, default=None, help="señales por llamada (Config.senales_por_lote)"
    )
    p.add_argument("--seco", action="store_true", help="no escribe en la base")
    args = p.parse_args()

    cfg = obtener_config()
    if args.ciclo not in cfg.ventanas_ciclo:
        print(f"Ciclo {args.ciclo} no existe. Hay: {sorted(cfg.ventanas_ciclo)}")
        return 1

    with sesion(cfg) as s:
        resumen = procesar_ciclo(s, args.ciclo, args.lote, args.municipio, cfg)

        print()
        print(resumen)

        if args.seco:
            s.rollback()
            print()
            print("Modo seco: nada escrito.")
            return 1 if resumen.con_error else 0

        s.flush()
        total = s.query(Insight).filter_by(id_ciclo=args.ciclo).count()
        trazas = s.query(TrazaAgente).filter_by(id_ciclo=args.ciclo).count()
        print()
        print(f"En la base: {total} insights y {trazas} trazas para el ciclo {args.ciclo}.")

    for m in resumen.con_error:
        print(f"  ERROR {m.divipola} {m.nombre}: {m.error}")

    return 1 if resumen.con_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
