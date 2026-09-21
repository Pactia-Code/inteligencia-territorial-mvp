r"""Comprueba que una copia de la base es fiel al origen.

Tres preguntas, de la más barata a la más exigente:

  1. **¿Está todo?** Filas por tabla, origen contra destino.
  2. **¿Están las corridas y sus scores?** Es el dato que sostiene H4: si se
     perdiera una corrida, un informe publicado dejaría de poder reconstruirse.
  3. **¿Sobrevive un invariante conocido?** Las corridas de scoring 3 y 4 son
     hoy idénticas municipio por municipio pese a llevar `version_scoring`
     distinta —la 3 viene del esquema viejo y quedó etiquetada `v1+migrado`—.
     Que sigan siéndolo en el destino prueba que los `float`, los enteros y el
     JSON cruzaron sin deformarse. Un contador de filas no lo detectaría.

La 3 es la que de verdad vale: dos bases pueden tener el mismo número de filas
y distintos números dentro.

Uso:

    $py scripts\verificar_copia.py --destino "postgresql://...neon.tech/territorial"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sqlalchemy import create_engine, func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from territorial.almacen.modelos import (  # noqa: E402
    Base,
    CorridaAgentes,
    CorridaScoring,
    Insight,
    ScoreMunicipio,
)
from territorial.almacen.sesion import normalizar_url  # noqa: E402
from territorial.config import obtener_config  # noqa: E402


def conteos(sesion: Session) -> dict[str, int]:
    return {
        t.name: sesion.execute(select(func.count()).select_from(t)).scalar()
        for t in Base.metadata.sorted_tables
    }


def resumen_corridas(sesion: Session) -> dict:
    return {
        "corrida_scoring": sesion.scalar(select(func.count()).select_from(CorridaScoring)),
        "corrida_agentes": sesion.scalar(select(func.count()).select_from(CorridaAgentes)),
        "score_municipio": sesion.scalar(select(func.count()).select_from(ScoreMunicipio)),
        "insight": sesion.scalar(select(func.count()).select_from(Insight)),
    }


def scores_de(sesion: Session, id_corrida: int) -> dict[str, tuple]:
    """Huella comparable de una corrida: por municipio, lo que el informe usaría."""
    filas = sesion.scalars(
        select(ScoreMunicipio).where(ScoreMunicipio.id_corrida == id_corrida)
    ).all()
    return {
        f.divipola: (
            round(f.score, 12),
            f.ranking,
            f.dias_cubiertos,
            f.dias_ventana,
            f.sin_cobertura,
            (f.factores or {}).get("fraccion_informada"),
            (f.factores or {}).get("no_priorizable"),
        )
        for f in filas
    }


def comparar_pareja(sesion: Session, a: int, b: int, etiqueta: str) -> bool:
    """¿Las corridas `a` y `b` son idénticas municipio por municipio?"""
    ia, ib = scores_de(sesion, a), scores_de(sesion, b)
    if not ia or not ib:
        print(f"  {etiqueta}: FALTA una de las dos corridas ({len(ia)} y {len(ib)} scores)")
        return False
    if set(ia) != set(ib):
        print(f"  {etiqueta}: municipios distintos ({len(ia)} vs {len(ib)})")
        return False
    difieren = [d for d in ia if ia[d] != ib[d]]
    if difieren:
        print(f"  {etiqueta}: DIFIEREN en {len(difieren)} municipios: {sorted(difieren)[:5]}")
        for d in sorted(difieren)[:3]:
            print(f"      {d}\n        origen  {ia[d]}\n        destino {ib[d]}")
        return False
    print(f"  {etiqueta}: idénticas en los {len(ia)} municipios")
    return True


def main() -> int:
    cfg = obtener_config()
    p = argparse.ArgumentParser(description="Verifica una copia de la base")
    p.add_argument("--origen", default="sqlite:///data/territorial.db")
    p.add_argument("--destino", default=cfg.url_base_datos)
    p.add_argument("--pareja", default="3,4",
                   help="corridas de scoring que deben ser idénticas")
    args = p.parse_args()

    origen = normalizar_url(args.origen, cfg)
    destino = normalizar_url(args.destino, cfg)
    a, b = (int(x) for x in args.pareja.split(","))

    if origen == destino:
        print(f"ERROR: origen y destino son la misma base:\n  {origen}")
        return 1

    mo = create_engine(origen, future=True)
    md = create_engine(destino, future=True, pool_pre_ping=not destino.startswith("sqlite"))
    fallos = 0

    with Session(mo) as so, Session(md) as sd:
        # --- 1. filas por tabla ---
        co, cd = conteos(so), conteos(sd)
        print("=== 1. Filas por tabla ===")
        print(f"{'tabla':<24} {'origen':>9} {'destino':>9}")
        for t in sorted(co):
            marca = "" if co[t] == cd[t] else "   <<< NO CUADRA"
            if co[t] != cd[t]:
                fallos += 1
            print(f"{t:<24} {co[t]:>9} {cd[t]:>9}{marca}")
        print(f"  total: {sum(co.values())} vs {sum(cd.values())}")

        # --- 2. corridas y scores ---
        print("\n=== 2. Corridas y scores ===")
        ro, rd = resumen_corridas(so), resumen_corridas(sd)
        for clave in ro:
            marca = "" if ro[clave] == rd[clave] else "   <<< NO CUADRA"
            if ro[clave] != rd[clave]:
                fallos += 1
            print(f"  {clave:<20} {ro[clave]:>6} vs {rd[clave]:>6}{marca}")

        # --- 3. el invariante ---
        print(f"\n=== 3. Corridas {a} y {b}, municipio por municipio ===")
        if not comparar_pareja(so, a, b, "en el ORIGEN "):
            fallos += 1
        if not comparar_pareja(sd, a, b, "en el DESTINO"):
            fallos += 1

        # Y que el destino diga lo mismo que el origen, no solo que sea
        # coherente consigo mismo: una copia vacía en las dos pasaría el test
        # anterior sin haber copiado nada.
        iguales = scores_de(so, a) == scores_de(sd, a)
        print(f"  origen vs destino en la corrida {a}: "
              f"{'idénticas' if iguales else 'DIFIEREN'}")
        if not iguales:
            fallos += 1

    print()
    if fallos:
        print(f"VERIFICACIÓN FALLIDA: {fallos} comprobaciones no cuadran. "
              "No apuntes nada a esta base todavía.")
        return 1
    print("VERIFICACIÓN CORRECTA: la copia es fiel al origen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
