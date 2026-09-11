"""Compara dos versiones del prompt del Clasificador sobre el mismo lote.

Afinar un prompt a ojo es adivinar. Esto corre ambas versiones contra las
mismas señales y mide lo que importa:

  · reduccion       — cuanto descarta (CA-M2.1)
  · tasa de rechazo — cuanto inventa, segun el validador (CA-M3.3)
  · contabilidad    — si toda señal quedo en insight o descarte (CA-M2.5)
  · consolidacion   — si el mismo hecho salio en varios insights
  · diversidad      — si los codigos de descarte discriminan o son cajon de sastre
  · hedging         — si los resumenes son concretos o evasivos

Uso:
    python scripts\\comparar_prompts.py [--ciclo N] [--municipios 3] [--n 40]
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sqlalchemy import select  # noqa: E402

from territorial.agentes.clasificador import SenalEntrada, clasificar_lote  # noqa: E402
from territorial.almacen.modelos import Municipio, SenalCruda  # noqa: E402
from territorial.almacen.sesion import sesion  # noqa: E402
from territorial.reglas.normalizacion import normalizar  # noqa: E402
from territorial.reglas.prefiltro import clasificar as prefiltrar  # noqa: E402
from territorial.reglas.validador import Senal as SenalValidador  # noqa: E402
from territorial.reglas.validador import validar  # noqa: E402

# Formulas evasivas que el prompt v2 prohibe explicitamente.
HEDGES = (
    "se observa", "sugiere", "podria", "podría", "apunta a",
    "se refuerza la capacidad", "posible", "parece",
)


def metricas(resultados, indices, entradas):
    """Agrega las metricas de una version sobre todos los lotes."""
    n_entrada = sum(len(e) for e in entradas.values())
    insights = [(d, i) for d, r in resultados.items() for i in r.insights]
    usadas = sum(len({i for ins in r.insights for i in ins["ids_senal"]}) for r in resultados.values())

    validos = 0
    for divipola, ins in insights:
        if validar(ins["evidencia"], divipola, ins["_ciclo"], indices[divipola]).valido:
            validos += 1

    hedges = sum(
        1 for _, i in insights
        if any(h in normalizar(i["resumen"]) for h in map(normalizar, HEDGES))
    )

    # Consolidacion: dos insights del mismo municipio que comparten categoria
    # y solapan en palabras clave del resumen son un fallo de fusion.
    duplicados = 0
    por_muni: dict[str, list[dict]] = {}
    for divipola, ins in insights:
        por_muni.setdefault(divipola, []).append(ins)
    for lista in por_muni.values():
        for a in range(len(lista)):
            for b in range(a + 1, len(lista)):
                if lista[a]["categoria"] != lista[b]["categoria"]:
                    continue
                pa = set(normalizar(lista[a]["resumen"]).split())
                pb = set(normalizar(lista[b]["resumen"]).split())
                if pa and pb and len(pa & pb) / min(len(pa), len(pb)) > 0.5:
                    duplicados += 1

    codigos = Counter(d["motivo"] for r in resultados.values() for d in r.descartes)
    sin_cont = sum(len(r.sin_contabilizar) for r in resultados.values())

    return {
        "insights": len(insights),
        "usadas": usadas,
        "reduccion": 100 * (1 - usadas / n_entrada) if n_entrada else 0,
        "validos": validos,
        "rechazo": 100 * (1 - validos / len(insights)) if insights else 0,
        "sin_contabilizar": sin_cont,
        "duplicados": duplicados,
        "hedges": hedges,
        "codigos": codigos,
        "tokens_in": sum(r.tokens_entrada for r in resultados.values()),
        "tokens_out": sum(r.tokens_salida for r in resultados.values()),
        "errores": [r.error for r in resultados.values() if r.error],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ciclo", type=int, default=1)
    p.add_argument("--municipios", type=int, default=3)
    p.add_argument("--n", type=int, default=40)
    p.add_argument("--versiones", nargs=2, default=["v1", "v2"])
    args = p.parse_args()

    entradas: dict[str, list[SenalEntrada]] = {}
    indices: dict[str, dict] = {}
    nombres: dict[str, tuple[str, str]] = {}

    with sesion() as s:
        divipolas = s.scalars(
            select(Municipio.divipola).order_by(Municipio.divipola)
        ).all()[: args.municipios]

        for d in divipolas:
            m = s.get(Municipio, d)
            nombres[d] = (m.nombre, m.departamento)
            crudas = s.scalars(
                select(SenalCruda)
                .where(
                    SenalCruda.id_ciclo == args.ciclo,
                    SenalCruda.divipola == d,
                    SenalCruda.fuente.in_(["SECOP II", "RSS"]),
                )
                .order_by(SenalCruda.id)
            ).all()
            pasan = [c for c in crudas if prefiltrar(c.contenido)[0]][: args.n]
            entradas[d] = [
                SenalEntrada(id=c.id, fuente=c.fuente, fecha=c.fecha_publicacion,
                             contenido=c.contenido, url=c.url)
                for c in pasan
            ]
            indices[d] = {
                c.id: SenalValidador(
                    id=c.id, divipola=c.divipola, id_ciclo=c.id_ciclo, fuente=c.fuente,
                    contenido=c.contenido, url=c.url, fecha_publicacion=c.fecha_publicacion,
                )
                for c in pasan
            }

    total = sum(len(e) for e in entradas.values())
    print(f"Ciclo {args.ciclo} · {len(entradas)} municipios · {total} señales tras prefiltro")
    for d, e in entradas.items():
        print(f"  {nombres[d][0]:<22} {len(e):>4}")
    print()

    resumen = {}
    for version in args.versiones:
        print(f"Corriendo {version}...", flush=True)
        res = {}
        for d, e in entradas.items():
            if not e:
                continue
            r = clasificar_lote(e, nombres[d][0], nombres[d][1], version=version)
            for ins in r.insights:
                ins["_ciclo"] = args.ciclo
            res[d] = r
        resumen[version] = metricas(res, indices, entradas)
        resumen[version]["_res"] = res

    a, b = args.versiones
    ma, mb = resumen[a], resumen[b]

    print(f"\n{'MÉTRICA':<26}{a:>12}{b:>12}   MEJOR")
    filas = [
        ("Insights producidos", "insights", None),
        ("Señales usadas", "usadas", None),
        ("Reducción %", "reduccion", "alto"),
        ("Insights válidos", "validos", None),
        ("Tasa de rechazo %", "rechazo", "bajo"),
        ("Señales sin contabilizar", "sin_contabilizar", "bajo"),
        ("Insights duplicados", "duplicados", "bajo"),
        ("Resúmenes evasivos", "hedges", "bajo"),
        ("Códigos de descarte", None, "alto"),
        ("Tokens entrada", "tokens_in", None),
        ("Tokens salida", "tokens_out", None),
    ]
    for etiqueta, clave, sentido in filas:
        if clave is None:
            va, vb = len(ma["codigos"]), len(mb["codigos"])
        else:
            va, vb = ma[clave], mb[clave]
        fa = f"{va:.1f}" if isinstance(va, float) else str(va)
        fb = f"{vb:.1f}" if isinstance(vb, float) else str(vb)
        marca = ""
        if sentido == "alto":
            marca = b if vb > va else (a if va > vb else "=")
        elif sentido == "bajo":
            marca = b if vb < va else (a if va < vb else "=")
        print(f"{etiqueta:<26}{fa:>12}{fb:>12}   {marca}")

    for v in (a, b):
        print(f"\n=== Códigos de descarte en {v} ===")
        for cod, k in resumen[v]["codigos"].most_common():
            print(f"  {cod:<32}{k:>5}")
        if resumen[v]["errores"]:
            print(f"  ERRORES: {resumen[v]['errores']}")

    for v in (a, b):
        print(f"\n=== Insights RECHAZADOS por el validador en {v} ===")
        hubo = False
        for d, r in resumen[v]["_res"].items():
            for ins in r.insights:
                res = validar(ins["evidencia"], d, args.ciclo, indices[d])
                if res.valido:
                    continue
                hubo = True
                print(f"  [{ins['categoria']}] {ins['resumen'][:70]}")
                print(f"     motivo: {res.motivo[:220]}")
                for e in ins["evidencia"]:
                    origen = indices[d].get(e["id_senal"])
                    print(f"     cita   : {e['cita_textual'][:110]!r}")
                    if origen:
                        print(f"     fuente : {origen.contenido[:110]!r}")
        if not hubo:
            print("  ninguno")

    print(f"\n=== Resúmenes producidos por {b} ===")
    for d, r in resumen[b]["_res"].items():
        for ins in r.insights:
            print(f"  [{ins['categoria']:<20}] {ins['resumen'][:88]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
