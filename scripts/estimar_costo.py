"""Estima el costo por ciclo y la extrapolación de H5 (pendiente B4).

**Las tarifas no están en el código a propósito.** Dependen del contrato del
tenant de Pactia y nadie las ha verificado todavía: eso es exactamente lo que
B4 pide cerrar. Este script toma los consumos **medidos** de `traza_agente` y
los multiplica por las tarifas que le pases.

    & $py scripts\\estimar_costo.py --tarifa gpt-5.4-mini=0.25,2.00 `
                                   --tarifa gpt-5=1.25,10.00 --moneda USD

El formato de cada tarifa es `despliegue=ENTRADA,SALIDA` por millón de tokens.
Se saca de Azure AI Foundry → el recurso → *Pricing*, con el contrato de Pactia
aplicado, no de la lista pública.

Sin `--tarifa` solo imprime los volúmenes, que es lo único medido.


Tres cosas que cambian la cifra y no son obvias
-----------------------------------------------
1. **Los tokens de razonamiento ya están dentro de `tokens_salida`.** Medido
   contra el tenant: 178 de salida traían 128 de razonamiento. No se suman
   aparte. El Correlacionador gasta más salida que entrada por esto.
2. **La carga inicial no es un ciclo normal.** El snapshot cubre 374 días y una
   quincena real es 12,4 veces menor. Extrapolar H5 con los totales del
   snapshot sobreestima la operación en un orden de magnitud.
3. **El Correlacionador escala por municipio, no por señal.** Duplicar el
   volumen de contratación no duplica su costo; añadir municipios sí.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sqlalchemy import func, select  # noqa: E402

from territorial.almacen.modelos import TrazaAgente  # noqa: E402
from territorial.almacen.sesion import sesion  # noqa: E402

# Medido sobre el snapshot el 2026-09-17.
# Tasa del Clasificador: Barranquilla ciclo 2, 284 señales en 6 lotes,
# 68.058 tokens de entrada y 25.986 de salida.
ENTRADA_POR_SENAL = 240
SALIDA_POR_SENAL = 92
SENALES_CARGA_INICIAL = 7_628
SENALES_POR_QUINCENA_18 = 615
MUNICIPIOS_MVP = 18
MUNICIPIOS_NACIONAL = 1_103
QUINCENAS_POR_ANIO = 26


def _escenarios() -> list[tuple[str, float, float]]:
    """(nombre, señales, corridas de municipio) de cada escenario.

    Las «corridas de municipio» son lo que factura el Correlacionador: corre
    una vez por municipio y ciclo, no una vez por señal.
    """
    por_muni = SENALES_POR_QUINCENA_18 / MUNICIPIOS_MVP
    return [
        ("Carga inicial: 3 ciclos del MVP", SENALES_CARGA_INICIAL, MUNICIPIOS_MVP * 3),
        ("Quincena de operación, 18 municipios", SENALES_POR_QUINCENA_18, MUNICIPIOS_MVP),
        ("Quincena, 1.103 municipios (H5)", por_muni * MUNICIPIOS_NACIONAL, MUNICIPIOS_NACIONAL),
        (
            "Año nacional (26 quincenas)",
            por_muni * MUNICIPIOS_NACIONAL * QUINCENAS_POR_ANIO,
            MUNICIPIOS_NACIONAL * QUINCENAS_POR_ANIO,
        ),
    ]


def parsear_tarifas(crudas: list[str]) -> dict[str, tuple[float, float]]:
    tarifas: dict[str, tuple[float, float]] = {}
    for item in crudas or []:
        try:
            modelo, valores = item.split("=", 1)
            ent, sal = valores.split(",", 1)
            tarifas[modelo.strip()] = (float(ent), float(sal))
        except ValueError:
            raise SystemExit(
                f"tarifa mal formada: {item!r}. Se espera despliegue=ENTRADA,SALIDA "
                "por millón de tokens, p. ej. gpt-5=1.25,10.00"
            ) from None
    return tarifas


def main() -> int:
    p = argparse.ArgumentParser(description="Estima el costo del ciclo (B4)")
    p.add_argument(
        "--tarifa",
        action="append",
        help="despliegue=ENTRADA,SALIDA por millón de tokens; repetible",
    )
    p.add_argument("--moneda", default="USD")
    args = p.parse_args()
    tarifas = parsear_tarifas(args.tarifa)

    with sesion() as s:
        filas = s.execute(
            select(
                TrazaAgente.agente,
                TrazaAgente.modelo,
                func.count().label("llamadas"),
                func.sum(TrazaAgente.tokens_entrada),
                func.sum(TrazaAgente.tokens_salida),
                func.sum(TrazaAgente.tokens_cache_lectura),
            ).group_by(TrazaAgente.agente, TrazaAgente.modelo)
        ).all()

    if not filas:
        print("No hay trazas. Corre antes scripts/correr_ciclo.py")
        return 1

    print("=" * 78)
    print("CONSUMO MEDIDO (traza_agente)")
    print("=" * 78)
    print(
        f"{'agente':16} {'despliegue':14} {'llamadas':>8} "
        f"{'entrada':>10} {'salida':>10} {'caché':>8}"
    )
    total_ent = total_sal = 0
    por_modelo: dict[str, list[int]] = {}
    for agente, modelo, n, ent, sal, cache in filas:
        ent, sal, cache = ent or 0, sal or 0, cache or 0
        print(f"{agente:16} {modelo or '?':14} {n:>8} {ent:>10,} {sal:>10,} {cache:>8,}")
        total_ent += ent
        total_sal += sal
        acum = por_modelo.setdefault(modelo or "?", [0, 0, 0])
        acum[0] += ent
        acum[1] += sal
        acum[2] += n

    print(f"{'TOTAL':31} {sum(f[2] for f in filas):>8} {total_ent:>10,} {total_sal:>10,}")

    # El Clasificador escala por señal; el Correlacionador por municipio.
    clas = [f for f in filas if f[0] == "clasificador"]
    corr = [f for f in filas if f[0] == "correlacionador"]
    modelo_clas = clas[0][1] if clas else None
    modelo_corr = corr[0][1] if corr else None
    # La tasa por señal se toma de la medición documentada arriba y no se deduce
    # de los propios tokens, que sería circular: la traza no guarda cuántas
    # señales llevaba cada lote.
    ent_sen, sal_sen = ENTRADA_POR_SENAL, SALIDA_POR_SENAL
    ent_muni = sum((f[3] or 0) for f in corr) / sum(f[2] for f in corr) if corr else 0
    sal_muni = sum((f[4] or 0) for f in corr) / sum(f[2] for f in corr) if corr else 0

    if clas and corr:
        print()
        print("=" * 78)
        print("TOKENS PROYECTADOS POR AGENTE Y MODELO")
        print("=" * 78)
        print(f"  Clasificador    {ent_sen:>6,.0f} entrada + {sal_sen:>6,.0f} salida por SEÑAL")
        print(
            f"  Correlacionador {ent_muni:>6,.0f} entrada + {sal_muni:>6,.0f} "
            "salida por MUNICIPIO"
        )
        print()
        print(f"{'escenario':38} {'agente':16} {'modelo':14} {'entrada':>13} {'salida':>13}")
        for nombre, señales, municipios in _escenarios():
            print(
                f"{nombre:38} {'Clasificador':16} {modelo_clas:14} "
                f"{señales * ent_sen:>13,.0f} {señales * sal_sen:>13,.0f}"
            )
            print(
                f"{'':38} {'Correlacionador':16} {modelo_corr:14} "
                f"{municipios * ent_muni:>13,.0f} {municipios * sal_muni:>13,.0f}"
            )
        print()
        print("  No incluye el Sintetizador (M6), que aún no existe.")

    if not tarifas:
        print()
        print("Sin --tarifa no se calcula precio: las del tenant son el pendiente B4.")
        print("Formato: --tarifa gpt-5.4-mini=ENTRADA,SALIDA --tarifa gpt-5=ENTRADA,SALIDA")
        return 0

    print()
    print("=" * 78)
    print(f"COSTO DE LO YA CORRIDO ({args.moneda})")
    print("=" * 78)
    faltan = [m for m in por_modelo if m not in tarifas]
    if faltan:
        print(f"  Sin tarifa para: {faltan}. Se omiten del total.")

    costo_medido = 0.0
    for modelo, (ent, sal, _n) in sorted(por_modelo.items()):
        if modelo not in tarifas:
            continue
        t_ent, t_sal = tarifas[modelo]
        c = ent / 1e6 * t_ent + sal / 1e6 * t_sal
        costo_medido += c
        print(f"  {modelo:14} {c:>12,.4f}")
    print(f"  {'TOTAL':14} {costo_medido:>12,.4f}")

    if clas and corr:

        def estimar(señales: float, municipios: float) -> float:
            total = 0.0
            if modelo_clas in tarifas:
                t_ent, t_sal = tarifas[modelo_clas]
                total += señales * ent_sen / 1e6 * t_ent + señales * sal_sen / 1e6 * t_sal
            if modelo_corr in tarifas:
                t_ent, t_sal = tarifas[modelo_corr]
                total += municipios * ent_muni / 1e6 * t_ent + municipios * sal_muni / 1e6 * t_sal
            return total

        print()
        print("=" * 78)
        print(f"PROYECCIONES ({args.moneda})")
        print("=" * 78)
        print(f"  base medida: {ent_sen:.0f}+{sal_sen:.0f} tokens/señal (Clasificador), "
              f"{ent_muni:.0f}+{sal_muni:.0f} por municipio (Correlacionador)")
        print()
        for nombre, señales, municipios in _escenarios():
            print(f"  {nombre:42} {estimar(señales, municipios):>14,.2f}")

        print()
        print("  No incluye el Sintetizador (M6), que aún no existe.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
