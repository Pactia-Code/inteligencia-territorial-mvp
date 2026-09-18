"""Dos pasadas seguidas del mismo ciclo, para medir A6.

A6 pregunta por la variación del Clasificador **con todo lo demás constante**,
así que las dos pasadas van seguidas: cualquier cosa en medio introduce una
variable que después no se puede descartar.

Dos precauciones, porque esto tarda cerca de dos horas y gasta unos USD 3:

  1. **La segunda no arranca si la primera no terminó limpia.** Si la primera
     se corta a mitad su cohorte queda incompleta, y comparar 18 municipios
     contra 11 no mide nada. Mejor fallar al arrancar que descubrirlo al
     analizar.
  2. **El progreso queda en la base**, no solo en el log. `ciclo.py` confirma
     municipio a municipio: una caída en el 17 no tira los 16 anteriores.
     LangGraph daría checkpointing (CA-M8.4) pero no está cableado.

Uso:
    & $py scripts\\dos_pasadas.py --ciclo 1
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from territorial.almacen.modelos import CorridaAgentes, Insight  # noqa: E402
from territorial.almacen.sesion import sesion  # noqa: E402
from territorial.ciclo import procesar_ciclo  # noqa: E402
from territorial.config import obtener_config  # noqa: E402


def _revisar(resumen, etiqueta: str) -> list[str]:
    """Motivos por los que esta pasada no cuenta como limpia."""
    problemas: list[str] = []
    corrida = resumen.corrida_agentes
    if corrida is None:
        problemas.append("no se abrió corrida de agentes")
        return problemas
    if corrida.tipo_corrida != "completa":
        faltan = sorted(set(corrida.municipios_objetivo) - set(corrida.municipios_en_cohorte))
        problemas.append(f"cohorte {corrida.tipo_corrida}: faltan {faltan}")
    if resumen.con_error:
        fallos = [f"{m.divipola} ({m.error[:50]})" for m in resumen.con_error]
        problemas.append(f"{len(fallos)} municipios con error: {fallos}")
    if resumen.error_scoring:
        problemas.append(f"scoring falló: {resumen.error_scoring}")
    return problemas


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    ap = argparse.ArgumentParser(description="Dos pasadas seguidas (A6)")
    ap.add_argument("--ciclo", type=int, default=1)
    ap.add_argument("--lote", type=int, default=None)
    args = ap.parse_args()

    cfg = obtener_config()
    if args.ciclo not in cfg.ventanas_ciclo:
        print(f"Ciclo {args.ciclo} no existe. Hay: {sorted(cfg.ventanas_ciclo)}")
        return 1

    ids: list[int] = []
    for n in (1, 2):
        print(f"\n{'=' * 78}\nPASADA {n} — ciclo {args.ciclo}\n{'=' * 78}", flush=True)
        inicio = time.perf_counter()

        with sesion(cfg) as s:
            resumen = procesar_ciclo(s, args.ciclo, args.lote, None, cfg)
            problemas = _revisar(resumen, f"pasada {n}")
            corrida_id = resumen.corrida_agentes.id if resumen.corrida_agentes else None

        print(resumen, flush=True)
        print(f"\nDuración: {(time.perf_counter() - inicio) / 60:.1f} min", flush=True)

        if problemas:
            print(f"\nPASADA {n} NO LIMPIA:", flush=True)
            for p in problemas:
                print(f"  - {p}", flush=True)
            if n == 1:
                print(
                    "\nNo se lanza la segunda pasada: comparar una cohorte "
                    "incompleta contra una completa no mide nada.",
                    flush=True,
                )
            return 1

        ids.append(corrida_id)
        print(f"Pasada {n} limpia. Corrida de agentes {corrida_id}.", flush=True)

    # --- Verificación que se pidió explícitamente antes de analizar ---
    print(f"\n{'=' * 78}\nVERIFICACIÓN\n{'=' * 78}", flush=True)
    with sesion(cfg) as s:
        for cid in ids:
            c = s.get(CorridaAgentes, cid)
            prompts = {
                p
                for (p,) in s.query(Insight.id_prompt)
                .filter(Insight.id_corrida == cid)
                .distinct()
            }
            print(
                f"  corrida {cid}: {len(c.municipios_en_cohorte)}/"
                f"{len(c.municipios_objetivo)} municipios, {c.tipo_corrida}, "
                f"id_prompt={sorted(x for x in prompts if x is not None)}",
                flush=True,
            )
        a, b = (s.get(CorridaAgentes, i) for i in ids)
        misma_cohorte = a.municipios_en_cohorte == b.municipios_en_cohorte
        mismo_prompt = (
            a.version_clasificador == b.version_clasificador
            and a.version_correlacionador == b.version_correlacionador
        )
        print(f"\n  misma cohorte : {misma_cohorte}")
        print(f"  mismos prompts: {mismo_prompt} "
              f"(clas {a.version_clasificador}, corr {a.version_correlacionador})")
        if not (misma_cohorte and mismo_prompt):
            print("\n  LAS PASADAS NO SON COMPARABLES.", flush=True)
            return 1

    print(f"\nComparables. Corridas de agentes: {ids}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
