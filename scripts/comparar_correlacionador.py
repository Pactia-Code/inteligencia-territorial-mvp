r"""Compara el Correlacionador v1 contra v2 sobre los mismos insights validados.

v2 añade el contexto estructural bandeado. Como cambia lo que el agente
produce, va como A7: se mide antes, se versiona y el antes y el después
conviven.

**Dos comprobaciones no se reportan: fallan.** El script devuelve código
distinto de cero y lo dice en la última línea.

1. **v2 no puede correlacionar MÁS que v1.** La regla 1 del prompt dice que el
   contexto explica una convergencia y nunca la crea. Si v2 encuentra más
   convergencias, la regla se rompió y un dato constante —los indicadores son
   anuales, idénticos en los tres ciclos— estaría decidiendo qué se publica.
   Es exactamente el defecto de F4 entrando por la puerta de atrás, y es el
   único sitio por donde podría entrar.

2. **Ninguna cifra de la salida puede faltar en los insights de entrada.** Y
   eso **incluye las de `contexto_municipal`**: si el modelo escribe «3.480
   hogares» y ese número es real pero no estaba en los insights, es una
   violación de CA-M6.3 igual. El número lo escribió el modelo. Se marca
   aparte, porque una cifra real inventada es más difícil de ver que una falsa.

Cuesta tokens de gpt-5, que es el 89% del gasto. **Prueba primero con un
municipio.**

Uso:

    $py scripts\comparar_correlacionador.py --municipio 05837
    $py scripts\comparar_correlacionador.py --corrida 10
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sqlalchemy import select  # noqa: E402

from territorial.agentes.correlacionador import (  # noqa: E402
    InsightValidado,
    ResultadoCorrelacion,
    correlacionar,
)
from territorial.almacen.modelos import (  # noqa: E402
    ContextoMunicipal,
    CorridaAgentes,
    Insight,
    Municipio,
)
from territorial.almacen.sesion import sesion  # noqa: E402
from territorial.reglas.contexto import contexto_de  # noqa: E402

# Números de cuatro dígitos o más, o con decimales: los que son «un dato».
# Un «2» o un «15» sueltos aparecen en cualquier prosa y perseguirlos daría
# solo falsos positivos.
NUMERO = re.compile(r"\d[\d.,]{2,}")

# Palabras que indican que la implicación se moja con una tipología, que es lo
# que CA-M4.2 pide y lo que el contexto debería mejorar.
TIPOLOGIA = (
    "vivienda", "residencial", "vis", "interés social", "interes social",
    "industrial", "logístic", "logistic", "comercial", "oficina", "bodega",
    "renovación", "renovacion", "estrato",
)


def numeros(texto: str) -> set[str]:
    """Los números de un texto, normalizados para poder compararlos."""
    return {
        n.strip(".,").replace(".", "").replace(",", "")
        for n in NUMERO.findall(texto or "")
    }


def numeros_del_contexto(fila: ContextoMunicipal | None) -> set[str]:
    """Las cifras reales del municipio. Si aparecen en la salida, es CA-M6.3."""
    if fila is None:
        return set()
    crudos = [
        fila.poblacion_total, fila.predios_urbanos,
        fila.valor_agregado, fila.deficit_cuantitativo,
        fila.deficit_cualitativo, fila.avaluo_catastral_urbano,
    ]
    salida: set[str] = set()
    for v in crudos:
        if v is None:
            continue
        salida.add(str(int(round(v))))
        salida.add(str(v).replace(".", "").replace(",", ""))
    return salida


def texto_de(r: ResultadoCorrelacion) -> str:
    return "\n".join(
        f"{c.por_que_convergen} {c.resumen} {c.implicacion_inmobiliaria}"
        for c in r.correlacionados
    )


def menciona_tipologia(r: ResultadoCorrelacion) -> int:
    return sum(
        1 for c in r.correlacionados
        if any(p in c.implicacion_inmobiliaria.lower() for p in TIPOLOGIA)
    )


def main() -> int:
    p = argparse.ArgumentParser(description="v1 contra v2 del Correlacionador")
    p.add_argument("--corrida", type=int, default=10,
                   help="corrida de agentes de la que salen los insights validados")
    p.add_argument("--municipio", help="DIVIPOLA; si se omite, todos los de la corrida")
    args = p.parse_args()

    filas_por_muni: dict[str, list[Insight]] = {}
    nombres: dict[str, tuple[str, str]] = {}
    contextos: dict[str, ContextoMunicipal | None] = {}
    bandas: dict[str, object] = {}

    with sesion() as s:
        corrida = s.get(CorridaAgentes, args.corrida)
        if corrida is None:
            print(f"ERROR: no existe la corrida de agentes {args.corrida}")
            return 1
        consulta = select(Insight).where(
            Insight.id_corrida == args.corrida,
            Insight.estado_validacion == "validado",
            Insight.origen == "clasificador",
        )
        if args.municipio:
            consulta = consulta.where(Insight.divipola == args.municipio)
        for ins in s.scalars(consulta).all():
            filas_por_muni.setdefault(ins.divipola, []).append(ins)
        for d in filas_por_muni:
            m = s.get(Municipio, d)
            nombres[d] = (m.nombre, m.departamento) if m else (d, "")
            contextos[d] = s.get(ContextoMunicipal, d)
            bandas[d] = contexto_de(s, d)

    if not filas_por_muni:
        print("ERROR: la corrida no tiene insights validados del clasificador")
        return 1

    print(f"Corrida {args.corrida}, ciclo {corrida.id_ciclo}: "
          f"{len(filas_por_muni)} municipios, "
          f"{sum(len(v) for v in filas_por_muni.values())} insights validados\n")

    tot = {"v1": Counter(), "v2": Counter()}
    fugas: list[tuple[str, str, set[str]]] = []
    fugas_reales: list[tuple[str, set[str]]] = []
    mas_en_v2: list[tuple[str, int, int]] = []

    print(f"{'municipio':<20} {'conv v1':>8} {'conv v2':>8} {'rech v1':>8} "
          f"{'rech v2':>8} {'tipol v1':>9} {'tipol v2':>9}")
    for d, insights in sorted(filas_por_muni.items(), key=lambda kv: nombres[kv[0]][0]):
        entrada = [
            InsightValidado(
                id=i.id, categoria=i.categoria, resumen=i.resumen,
                implicacion_inmobiliaria=i.implicacion_inmobiliaria or "",
                evidencia=i.evidencia, ids_senal=i.ids_senal,
            )
            for i in insights
        ]
        nombre, depto = nombres[d]

        r1 = correlacionar(entrada, nombre, depto, version="v1")
        r2 = correlacionar(entrada, nombre, depto, version="v2", contexto=bandas[d])

        for etiqueta, r in (("v1", r1), ("v2", r2)):
            tot[etiqueta]["convergencias"] += len(r.correlacionados)
            tot[etiqueta]["rechazados"] += len(r.rechazados)
            tot[etiqueta]["tipologia"] += menciona_tipologia(r)
            tot[etiqueta]["entrada"] += r.tokens_entrada
            tot[etiqueta]["salida"] += r.tokens_salida
            tot[etiqueta]["razonamiento"] += r.tokens_razonamiento
            for c in r.correlacionados:
                tot[etiqueta][f"conf_{c.confianza}"] += 1
            if r.error:
                tot[etiqueta]["errores"] += 1

        if len(r2.correlacionados) > len(r1.correlacionados):
            mas_en_v2.append((nombre, len(r1.correlacionados), len(r2.correlacionados)))

        # --- fuga de cifras ---
        permitidas: set[str] = set()
        for i in insights:
            permitidas |= numeros(i.resumen) | numeros(i.implicacion_inmobiliaria or "")
            for e in i.evidencia or []:
                permitidas |= numeros(e.get("cita_textual", ""))
        salidas = numeros(texto_de(r2))
        inventadas = salidas - permitidas
        if inventadas:
            fugas.append((nombre, "v2", inventadas))
            del_contexto = inventadas & numeros_del_contexto(contextos[d])
            if del_contexto:
                fugas_reales.append((nombre, del_contexto))

        print(f"{nombre[:20]:<20} {len(r1.correlacionados):>8} {len(r2.correlacionados):>8} "
              f"{len(r1.rechazados):>8} {len(r2.rechazados):>8} "
              f"{menciona_tipologia(r1):>9} {menciona_tipologia(r2):>9}")

    print("\n=== Totales ===")
    print(f"{'':<22} {'v1':>10} {'v2':>10}")
    for clave in ("convergencias", "rechazados", "tipologia",
                  "conf_alta", "conf_media", "conf_baja", "errores"):
        print(f"{clave:<22} {tot['v1'][clave]:>10} {tot['v2'][clave]:>10}")

    print("\n=== Tokens (el Correlacionador es el 89% del gasto) ===")
    for clave in ("entrada", "salida", "razonamiento"):
        a, b = tot["v1"][clave], tot["v2"][clave]
        delta = f"{(b - a) / a:+.1%}" if a else "-"
        print(f"{clave:<22} {a:>10,} {b:>10,}   {delta}")

    # ----------------------------------------------------------------------
    # Las dos compuertas
    # ----------------------------------------------------------------------
    fallos = 0

    print("\n=== Compuerta 1: v2 no puede correlacionar más que v1 ===")
    if mas_en_v2:
        fallos += 1
        print(f"  FALLA en {len(mas_en_v2)} municipios. El contexto está CREANDO "
              "convergencias, no explicándolas:")
        for nombre, a, b in mas_en_v2:
            print(f"    {nombre}: v1 {a} -> v2 {b}")
    elif tot["v2"]["convergencias"] > tot["v1"]["convergencias"]:
        fallos += 1
        print(f"  FALLA en el agregado: {tot['v1']['convergencias']} -> "
              f"{tot['v2']['convergencias']}")
    else:
        print(f"  pasa: {tot['v1']['convergencias']} -> {tot['v2']['convergencias']} "
              "convergencias")

    print("\n=== Compuerta 2: ninguna cifra de la salida fuera de los insights ===")
    if fugas:
        fallos += 1
        print(f"  FALLA: {len(fugas)} municipios con cifras que no están en su entrada")
        for nombre, version, nums in fugas:
            print(f"    {nombre} ({version}): {sorted(nums)[:8]}")
    else:
        print("  pasa: ninguna cifra inventada")

    if fugas_reales:
        print("\n  Y son cifras REALES de contexto_municipal, que es peor: el "
              "número es correcto pero lo escribió el modelo (CA-M6.3).")
        for nombre, nums in fugas_reales:
            print(f"    {nombre}: {sorted(nums)}")

    print()
    if fallos:
        print(f"COMPARACIÓN FALLIDA: {fallos} de 2 compuertas. No promuevas v2.")
        return 1
    print("COMPARACIÓN CORRECTA: v2 explica mejor sin correlacionar de más.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
