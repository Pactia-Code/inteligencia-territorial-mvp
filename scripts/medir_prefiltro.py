"""Mide el prefiltro determinista contra las señales ya cargadas.

Responde dos preguntas abiertas:
  - Pendiente A2: ¿el diccionario de obra separa señal de ruido?
  - CA-M2.1: ¿cuánto volumen llega al Clasificador, y cuánto cuesta?

No usa LLM. Solo cuenta.

Uso:
    %LOCALAPPDATA%\\venvs\\territorial\\Scripts\\python.exe scripts\\medir_prefiltro.py
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import select  # noqa: E402

from territorial.almacen.modelos import Municipio, SenalCruda  # noqa: E402
from territorial.almacen.sesion import sesion  # noqa: E402
from territorial.reglas.prefiltro import clasificar  # noqa: E402


def main() -> int:
    with sesion() as s:
        nombres = {m.divipola: m.nombre for m in s.scalars(select(Municipio)).all()}

        total = Counter()
        pasan = Counter()
        motivos = Counter()
        por_muni: dict[str, list[int]] = defaultdict(lambda: [0, 0])

        consulta = select(SenalCruda).where(SenalCruda.fuente == "SECOP II")
        for sen in s.scalars(consulta).yield_per(2000):
            ok, motivo = clasificar(sen.contenido)
            total[sen.id_ciclo] += 1
            motivos[motivo.split(":")[0]] += 1
            por_muni[sen.divipola][0] += 1
            if ok:
                pasan[sen.id_ciclo] += 1
                por_muni[sen.divipola][1] += 1

    n_total = sum(total.values())
    n_pasan = sum(pasan.values())
    reduccion = 100 * (1 - n_pasan / n_total) if n_total else 0.0

    print("=== PREFILTRO SOBRE SECOP II ===\n")
    print(f"{'CICLO':<8}{'TOTAL':>9}{'PASAN':>9}{'REDUCCION':>12}")
    for c in sorted(total):
        red = 100 * (1 - pasan[c] / total[c]) if total[c] else 0.0
        print(f"{c:<8}{total[c]:>9}{pasan[c]:>9}{red:>11.1f}%")
    print(f"{'TOTAL':<8}{n_total:>9}{n_pasan:>9}{reduccion:>11.1f}%")

    print("\n=== MOTIVOS DE DESCARTE ===")
    for motivo, n in motivos.most_common():
        print(f"  {motivo:<28}{n:>8}  ({100*n/n_total:>5.1f}%)")

    print("\n=== DISPERSION POR MUNICIPIO (% que pasa) ===")
    filas = sorted(
        ((nombres.get(d, d), t, p, 100 * p / t if t else 0) for d, (t, p) in por_muni.items()),
        key=lambda f: f[3],
    )
    for nombre, t, p, pct in filas:
        print(f"  {nombre:<22}{t:>7}{p:>7}{pct:>8.1f}%")

    print("\n=== LECTURA ===")
    print(f"Reduccion determinista : {reduccion:.1f}%")
    print(f"Llegan al Clasificador : {n_pasan} registros")
    if reduccion >= 85:
        print("CA-M2.1 (>=85%) se cumple SOLO con el prefiltro, sin LLM.")
    else:
        falta = 100 * (1 - (n_total * 0.15) / n_pasan) if n_pasan else 0
        print(f"CA-M2.1 (>=85%) NO se alcanza solo con el prefiltro.")
        print(f"El Clasificador debe descartar otro {falta:.1f}% de lo que recibe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
