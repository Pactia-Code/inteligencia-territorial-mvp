"""Compara dos pasadas del mismo ciclo, señal a señal (pendiente A6).

**Por señal, no por insight.** Contar insights mide volumen; lo que A6 pregunta
es si el Clasificador ve lo mismo dos veces. El caso de Chigorodó —1 insight en
una pasada y 0 en otra sobre las mismas 6 señales— mostró que la variación no es
de formato sino **de existencia**: una pasada ve un hallazgo y la otra no ve
nada. Eso apunta a que A6 y A4 no son el mismo defecto.

Cada señal que entró al agente cae en uno de tres sitios por pasada:

    insight          se convirtió en hallazgo
    descarte         el modelo la rechazó y dijo por qué
    sin_contabilizar el modelo **no la mencionó**: ni insight ni descarte

El tercero es el que más importa. Una señal que desaparece sin motivo no es lo
mismo que una descartada con criterio, y hasta CA-M2.5 ese número no existía en
ninguna parte.

Uso:
    & $py scripts\\comparar_pasadas.py --a 7 --b 8
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sqlalchemy import select  # noqa: E402

from territorial.almacen.modelos import (  # noqa: E402
    CorridaAgentes,
    Descarte,
    Insight,
    Municipio,
)
from territorial.almacen.sesion import sesion  # noqa: E402


def destino_por_senal(sesion_bd, id_corrida: int) -> dict[int, tuple[str, str]]:
    """{id_senal: (destino, detalle)} para una pasada."""
    mapa: dict[int, tuple[str, str]] = {}

    for ins in sesion_bd.scalars(
        select(Insight).where(Insight.id_corrida == id_corrida)
    ).all():
        for s in ins.ids_senal or []:
            mapa[s] = ("insight", ins.categoria)

    for d in sesion_bd.scalars(
        select(Descarte).where(Descarte.id_corrida == id_corrida)
    ).all():
        # Un insight gana sobre un descarte: si aparece en ambos, se usó.
        if d.id_senal in mapa:
            continue
        mapa[d.id_senal] = (
            "descarte" if d.declarado else "sin_contabilizar",
            d.motivo[:60],
        )

    return mapa


def main() -> int:
    ap = argparse.ArgumentParser(description="Compara dos pasadas señal a señal")
    ap.add_argument("--a", type=int, required=True, help="id de la primera corrida")
    ap.add_argument("--b", type=int, required=True, help="id de la segunda")
    ap.add_argument("--detalle", action="store_true", help="lista las señales que cambian")
    args = ap.parse_args()

    with sesion() as s:
        ca, cb = s.get(CorridaAgentes, args.a), s.get(CorridaAgentes, args.b)
        if ca is None or cb is None:
            print("Alguna corrida no existe.")
            return 1
        if ca.id_ciclo != cb.id_ciclo:
            print(f"Ciclos distintos ({ca.id_ciclo} y {cb.id_ciclo}): no son comparables.")
            return 1

        nom = {m.divipola: m.nombre for m in s.query(Municipio).all()}
        a = destino_por_senal(s, args.a)
        b = destino_por_senal(s, args.b)

        print("=" * 78)
        print(f"PASADAS {args.a} y {args.b} — ciclo {ca.id_ciclo}")
        print("=" * 78)
        print(f"  cohortes iguales : {ca.municipios_en_cohorte == cb.municipios_en_cohorte}")
        print(f"  prompts iguales  : {ca.version_clasificador == cb.version_clasificador}")
        print(f"  señales vistas   : {len(a)} y {len(b)}")

        todas = sorted(set(a) | set(b))
        pares = Counter((a.get(i, ("ausente", ""))[0], b.get(i, ("ausente", ""))[0])
                        for i in todas)

        print()
        print("--- Dónde cayó cada señal en una pasada y en la otra ---")
        print(f"{'pasada A':18} {'pasada B':18} {'señales':>8}")
        estables = cambian = 0
        for (da, db), n in sorted(pares.items(), key=lambda kv: -kv[1]):
            marca = "" if da == db else "   <-- cambia"
            if da == db:
                estables += n
            else:
                cambian += n
            print(f"{da:18} {db:18} {n:>8}{marca}")

        total = estables + cambian
        print()
        print(f"  estables : {estables:>5} de {total}  ({estables/total:.1%})" if total else "")
        print(f"  cambian  : {cambian:>5} de {total}  ({cambian/total:.1%})" if total else "")

        print()
        print("--- Lo que A6 pregunta: insight en una, no-insight en la otra ---")
        vuelco = [
            i for i in todas
            if (a.get(i, ("ausente",))[0] == "insight") != (b.get(i, ("ausente",))[0] == "insight")
        ]
        print(f"  {len(vuelco)} señales de {total} ({len(vuelco)/total:.1%})" if total else "")

        print()
        print("--- sin_contabilizar: el modelo ni las mencionó ---")
        for etiqueta, mapa in ((f"pasada {args.a}", a), (f"pasada {args.b}", b)):
            c = Counter(v[0] for v in mapa.values())
            n = c["sin_contabilizar"]
            tot = sum(c.values())
            if tot:
                print(f"  {etiqueta}: {n} de {tot} ({n / tot:.1%})")
            else:
                print(f"  {etiqueta}: sin datos")
        ambas = [i for i in todas
                 if a.get(i, ("",))[0] == "sin_contabilizar" == b.get(i, ("",))[0]]
        print(f"  ignoradas por las DOS: {len(ambas)}")

        if args.detalle and vuelco:
            print()
            print("--- Señales que voltearon ---")
            for i in vuelco[:40]:
                da = a.get(i, ("ausente", ""))
                db = b.get(i, ("ausente", ""))
                print(f"  {i}: {da[0]:16} -> {db[0]:16}  {da[1][:35]} | {db[1][:35]}")

        print()
        print("--- Por municipio: insights en cada pasada ---")
        ia = Counter(
            x.divipola for x in s.scalars(
                select(Insight).where(Insight.id_corrida == args.a)
            ).all()
        )
        ib = Counter(
            x.divipola for x in s.scalars(
                select(Insight).where(Insight.id_corrida == args.b)
            ).all()
        )
        print(f"{'municipio':22} {'A':>4} {'B':>4}")
        for d in sorted(set(ia) | set(ib)):
            dif = "" if ia[d] == ib[d] else f"   {ia[d] - ib[d]:+d}"
            print(f"{nom.get(d, d)[:22]:22} {ia[d]:>4} {ib[d]:>4}{dif}")
        print(f"{'TOTAL':22} {sum(ia.values()):>4} {sum(ib.values()):>4}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
