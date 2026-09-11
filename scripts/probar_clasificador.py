"""Prueba el Clasificador sobre un lote pequeño y valida su salida.

Corre la cadena completa en miniatura: prefiltro → Clasificador → Validador.
Sirve para calibrar antes de gastar en los 7.628 registros del ciclo.

Uso:
    python scripts\\probar_clasificador.py [--ciclo N] [--municipio DIVIPOLA] [--n 30]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sqlalchemy import select  # noqa: E402

from territorial.agentes.clasificador import SenalEntrada, clasificar_lote  # noqa: E402
from territorial.almacen.modelos import Municipio, SenalCruda  # noqa: E402
from territorial.almacen.sesion import sesion  # noqa: E402
from territorial.reglas.prefiltro import clasificar as prefiltrar  # noqa: E402
from territorial.reglas.validador import Senal as SenalValidador  # noqa: E402
from territorial.reglas.validador import validar  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ciclo", type=int, default=1)
    p.add_argument("--municipio", default=None, help="DIVIPOLA; por defecto el primero")
    p.add_argument("--n", type=int, default=30, help="señales a enviar")
    args = p.parse_args()

    with sesion() as s:
        divipola = args.municipio
        if divipola is None:
            divipola = s.scalars(select(Municipio.divipola).order_by(Municipio.divipola)).first()
        muni = s.get(Municipio, divipola)
        if muni is None:
            print(f"No existe el municipio {divipola}")
            return 1

        consulta = (
            select(SenalCruda)
            .where(
                SenalCruda.id_ciclo == args.ciclo,
                SenalCruda.divipola == divipola,
                SenalCruda.fuente.in_(["SECOP II", "RSS"]),
            )
            .order_by(SenalCruda.id)
        )
        crudas = s.scalars(consulta).all()

        # Prefiltro determinista: solo pasa lo territorial.
        pasan = [c for c in crudas if prefiltrar(c.contenido)[0]][: args.n]

        entrada = [
            SenalEntrada(
                id=c.id, fuente=c.fuente, fecha=c.fecha_publicacion,
                contenido=c.contenido, url=c.url,
            )
            for c in pasan
        ]
        indice_validador = {
            c.id: SenalValidador(
                id=c.id, divipola=c.divipola, id_ciclo=c.id_ciclo, fuente=c.fuente,
                contenido=c.contenido, url=c.url, fecha_publicacion=c.fecha_publicacion,
            )
            for c in pasan
        }

    print(f"Municipio : {muni.nombre} ({divipola})  ciclo {args.ciclo}")
    print(f"Crudas    : {len(crudas)}")
    print(f"Tras prefiltro y tope --n : {len(entrada)}\n")

    if not entrada:
        print("No hay señales que enviar.")
        return 1

    print("Llamando al Clasificador...\n")
    r = clasificar_lote(entrada, muni.nombre, muni.departamento)

    if r.error:
        print(f"ERROR: {r.error}")
        return 1

    print(f"Insights   : {len(r.insights)}")
    print(f"Descartes  : {len(r.descartes)}")
    print(f"Tokens     : entrada={r.tokens_entrada} salida={r.tokens_salida}")
    print(f"Duracion   : {r.duracion_ms} ms")

    ids_en_insights = {i for ins in r.insights for i in ins["ids_senal"]}
    reduccion = 100 * (1 - len(ids_en_insights) / len(entrada))
    print(f"\nSeñales usadas en insights: {len(ids_en_insights)} de {len(entrada)}")
    print(f"Reduccion del Clasificador : {reduccion:.1f}%")

    print("\n=== VALIDADOR SOBRE LOS INSIGHTS ===\n")
    validos = 0
    for i, ins in enumerate(r.insights, 1):
        res = validar(ins["evidencia"], divipola, args.ciclo, indice_validador)
        marca = "OK  " if res.valido else "RECH"
        validos += res.valido
        print(f"  [{marca}] {ins['categoria']:<20} {ins['resumen'][:62]}")
        if not res.valido:
            print(f"         motivo: {res.motivo[:150]}")

    n = len(r.insights)
    tasa = 100 * (1 - validos / n) if n else 0.0
    print(f"\nValidados : {validos} de {n}")
    print(f"TASA DE RECHAZO: {tasa:.1f}%   <- es la tasa de alucinacion (CA-M3.3)")

    if r.insights:
        print("\n=== EJEMPLO DE INSIGHT ===\n")
        ej = r.insights[0]
        print(f"  categoria   : {ej['categoria']}")
        print(f"  resumen     : {ej['resumen']}")
        print(f"  implicacion : {ej['implicacion_inmobiliaria']}")
        for e in ej["evidencia"][:2]:
            print(f"  evidencia   : senal={e['id_senal']} fecha={e['fecha']}")
            print(f"                cita={e['cita_textual'][:90]!r}")

    if r.descartes:
        from collections import Counter

        print("\n=== MOTIVOS DE DESCARTE ===")
        for motivo, k in Counter(d["motivo"] for d in r.descartes).most_common():
            print(f"  {motivo:<32}{k:>5}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
