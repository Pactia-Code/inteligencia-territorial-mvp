"""Prueba el Correlacionador sobre un municipio, con la cadena completa.

Corre prefiltro → Clasificador → Validador → **Correlacionador**, que es el
orden real de ejecución (Arquitectura §3). Hace falta encadenar porque todavía
no hay insights persistidos: M2 corre pero no guarda.

Uso:
    python scripts\\probar_correlacionador.py [--ciclo N] [--municipio DIVIPOLA] [--n 40]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sqlalchemy import select  # noqa: E402

from territorial.agentes.clasificador import SenalEntrada, clasificar_lote  # noqa: E402
from territorial.agentes.correlacionador import (  # noqa: E402
    InsightValidado,
    correlacionar,
)
from territorial.almacen.modelos import Municipio, SenalCruda  # noqa: E402
from territorial.almacen.sesion import sesion  # noqa: E402
from territorial.reglas.prefiltro import clasificar as prefiltrar  # noqa: E402
from territorial.reglas.validador import Senal as SenalValidador  # noqa: E402
from territorial.reglas.validador import validar  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ciclo", type=int, default=1)
    p.add_argument("--municipio", default=None, help="DIVIPOLA; por defecto el primero")
    p.add_argument("--n", type=int, default=40, help="señales a enviar al Clasificador")
    args = p.parse_args()

    with sesion() as s:
        if args.municipio:
            muni = s.get(Municipio, args.municipio)
        else:
            muni = s.scalars(select(Municipio).order_by(Municipio.divipola)).first()
        if muni is None:
            print("No hay municipios. Corre antes scripts/cargar_snapshot.py")
            return 1

        crudas = s.scalars(
            select(SenalCruda)
            .where(SenalCruda.id_ciclo == args.ciclo, SenalCruda.divipola == muni.divipola)
            .order_by(SenalCruda.id)
        ).all()

        # --- Prefiltro determinista ---
        pasan = [r for r in crudas if prefiltrar((r.datos or {}).get("objeto"))[0]]
        lote = pasan[: args.n]

        print(f"{muni.nombre} ({muni.divipola}) · ciclo {args.ciclo}")
        print(f"  crudas {len(crudas)} → prefiltro {len(pasan)} → lote {len(lote)}")
        if not lote:
            print("  el prefiltro no dejó nada; prueba otro municipio o ciclo")
            return 1

        # --- M2 Clasificador ---
        entradas = [
            SenalEntrada(
                id=r.id,
                fuente=r.fuente,
                fecha=r.fecha_publicacion,
                contenido=(r.datos or {}).get("objeto") or r.contenido,
                url=r.url,
            )
            for r in lote
        ]
        res = clasificar_lote(entradas, muni.nombre, muni.departamento)
        if res.error:
            print(f"  ERROR del Clasificador: {res.error}")
            return 1
        print(f"  Clasificador: {len(res.insights)} insights, {len(res.descartes)} descartes")
        print(f"    tokens {res.tokens_entrada} entrada + {res.tokens_salida} salida")

        # --- M3 Validador determinista ---
        vistas = {
            r.id: SenalValidador(
                id=r.id,
                divipola=r.divipola,
                id_ciclo=r.id_ciclo,
                fuente=r.fuente,
                contenido=(r.datos or {}).get("objeto") or r.contenido,
                url=r.url,
                fecha_publicacion=r.fecha_publicacion,
            )
            for r in lote
        }

        validados: list[InsightValidado] = []
        rechazados = 0
        for n, ins in enumerate(res.insights, start=1):
            veredicto = validar(ins["evidencia"], muni.divipola, args.ciclo, vistas)
            if not veredicto.valido:
                rechazados += 1
                continue
            validados.append(
                InsightValidado(
                    id=n,
                    categoria=ins["categoria"],
                    resumen=ins["resumen"],
                    implicacion_inmobiliaria=ins.get("implicacion_inmobiliaria", ""),
                    evidencia=ins["evidencia"],
                    ids_senal=ins["ids_senal"],
                )
            )
        print(f"  Validador: {len(validados)} válidos, {rechazados} rechazados")

        categorias = sorted({i.categoria for i in validados})
        print(f"  categorías presentes: {categorias}")

        if len(categorias) < 2:
            print()
            print("  Con una sola categoría no hay nada que cruzar (CA-M4.1).")
            print("  El Correlacionador los devolvería sueltos sin llamar al modelo.")
            return 0

        # --- Contexto Bing: orientativo, nunca evidencia (D1) ---
        bing = s.scalars(
            select(SenalCruda).where(
                SenalCruda.id_ciclo == args.ciclo,
                SenalCruda.divipola == muni.divipola,
                SenalCruda.fuente == "Bing",
            )
        ).all()
        contexto = [b.contenido for b in bing]

        # --- M4 Correlacionador ---
        print()
        print("--- M4 Correlacionador ---")
        corr = correlacionar(
            validados,
            muni.nombre,
            muni.departamento,
            contexto_bing=contexto,
            calificaciones=[],  # ciclo 1: no hay. CA-M4.3 queda sin ejercitar.
        )
        if corr.error:
            print(f"  ERROR: {corr.error}")
            return 1

        print(f"  correlacionados {len(corr.correlacionados)}")
        print(f"  rechazados      {len(corr.rechazados)}")
        print(f"  sueltos         {len(corr.sueltos)}")
        print(f"  tokens {corr.tokens_entrada} entrada + {corr.tokens_salida} salida")
        print(f"  trazabilidad intacta (CA-M4.4): {corr.trazabilidad_intacta}")
        if not corr.trazabilidad_intacta:
            print(f"  SEÑALES PERDIDAS: {corr.senales_perdidas}")

        for c in corr.correlacionados:
            print()
            print(f"  [{'+'.join(c.categorias)}] confianza {c.confianza}")
            print(f"    insights de origen: {c.ids_insight}  señales: {c.ids_senal}")
            print(f"    convergen porque: {c.por_que_convergen}")
            print(f"    {c.resumen}")
            print(f"    implicación: {c.implicacion_inmobiliaria}")

        for r in corr.rechazados:
            print()
            print(f"  RECHAZADO {r.ids_insight}: {r.motivo}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
