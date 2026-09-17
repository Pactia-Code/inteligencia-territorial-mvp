"""M5 — calcula el score y el top 3 de cada ciclo (Addendum 01, D4).

    & $py scripts\\calcular_scores.py            # los 3 ciclos, y guarda
    & $py scripts\\calcular_scores.py --ciclo 1  # uno solo
    & $py scripts\\calcular_scores.py --seco     # calcula y muestra, sin guardar

No llama a ningún LLM: M5 es capa determinista y las cifras del informe salen
de aquí (CA-M6.3).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from territorial.almacen.modelos import Municipio  # noqa: E402
from territorial.almacen.sesion import sesion  # noqa: E402
from territorial.config import obtener_config  # noqa: E402
from territorial.scoring.agregacion import entradas_del_ciclo  # noqa: E402
from territorial.scoring.persistencia import guardar  # noqa: E402
from territorial.scoring.ranking import puntuar_ciclo  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Score y top 3 por ciclo (M5)")
    ap.add_argument("--ciclo", type=int, help="solo este ciclo; por defecto, los tres")
    ap.add_argument("--seco", action="store_true", help="no escribe en la base")
    args = ap.parse_args()

    cfg = obtener_config()
    ciclos = [args.ciclo] if args.ciclo else sorted(cfg.ventanas_ciclo)

    with sesion(cfg) as s:
        nombres = {m.divipola: m.nombre for m in s.query(Municipio).all()}
        if not nombres:
            print("No hay municipios cargados. Corre antes scripts/cargar_snapshot.py")
            return 1

        for id_ciclo in ciclos:
            entradas = entradas_del_ciclo(s, id_ciclo, cfg)
            resultado = puntuar_ciclo(entradas, id_ciclo, cfg)

            print()
            print("=" * 78)
            print(f"CICLO {id_ciclo}")
            print("=" * 78)
            print(f"Pesos: {resultado.juego_pesos}")
            print()

            en_top = {s.divipola for s in resultado.top}
            for sc in resultado.scores:
                marca = "*" if sc.divipola in en_top else " "
                aviso = "  (cobertura baja)" if sc.sin_cobertura else ""
                if sc.no_priorizable:
                    aviso += f"  [no priorizable: {sc.fraccion_informada:.0%} informado]"
                nombre = nombres.get(sc.divipola, "?")
                print(f" {marca} {sc.ranking:>2}. {sc.divipola} {nombre:<22} {sc.score:.4f}{aviso}")

            if resultado.excluidos_del_top:
                print()
                print("--- Cedieron su puesto del top 3 ---")
                for sc in resultado.excluidos_del_top:
                    print(f"  {sc.divipola} {nombres.get(sc.divipola, '?')}: "
                          f"{sc.motivo_no_priorizable}")

            print()
            print(f"--- TOP {len(resultado.top)} · desglose (CA-M5.5) ---")
            for sc in resultado.top:
                print()
                print(f"{nombres.get(sc.divipola, '?')} ({sc.divipola})")
                print(sc.explicar())

            if not args.seco:
                n = guardar(s, resultado)
                print()
                print(f"Guardados {n} scores del ciclo {id_ciclo}.")

    if args.seco:
        print()
        print("Modo seco: no se escribió nada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
