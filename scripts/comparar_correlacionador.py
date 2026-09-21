r"""Compara dos pasadas del Correlacionador sobre los mismos insights validados.

Sirve para dos cosas distintas con el mismo instrumento, que es el punto:

  **Contraste de versiones** (`--a v1 --b v2`). v2 añade el contexto estructural
  bandeado. Como cambia lo que el agente produce, va como A7: se mide antes, se
  versiona y el antes y el después conviven.

  **Control de reproducibilidad** (`--a v1 --b v1`). Dos pasadas idénticas. Sin
  esto, un contraste de versiones atribuye al prompt una diferencia que podría
  ser varianza del modelo: el Clasificador no es reproducible (A6, 19,5% de
  señales voltean) y la de M4 **no está medida en ninguna parte**.

**Con versiones distintas, dos comprobaciones no se reportan: fallan.**

1. **La versión B no correlaciona más que A, sobre el AGREGADO y contra el piso
   de ruido medido.** La regla 1 del prompt v2 dice que el contexto explica una
   convergencia y nunca la crea; si B se sale del ruido hacia arriba, la regla
   se rompió y un dato constante —los indicadores son anuales, idénticos en los
   tres ciclos— estaría decidiendo qué se publica. Es el defecto de F4 entrando
   por la puerta de atrás.

   **Sobre el agregado y no municipio a municipio, y aprenderlo costó.** La
   primera versión exigía monotonía por municipio y suspendió a v2; el control
   demostró que habría suspendido a **v1 contra sí mismo**, con 14 de 18
   municipios moviéndose. Si no hay piso medido para el corpus que se compara,
   la compuerta **se niega a juzgar** en vez de dar un veredicto sin base.
2. **Ninguna cifra de la salida puede faltar en los insights de entrada.** Y eso
   **incluye las de `contexto_municipal`**: si el modelo escribe «3.480
   hogares» y el número es real pero no estaba en los insights, es una violación
   de CA-M6.3 igual. El número lo escribió el modelo. Se marca aparte, porque
   una cifra real inventada es más difícil de ver que una falsa.

**Con la misma versión en las dos, la compuerta 1 no aplica**: el movimiento
entre pasadas es justo lo que se está midiendo, no un fallo.

Cuesta tokens de gpt-5, que es el 89% del gasto. **Prueba primero con un
municipio.**

Uso:

    $py scripts\comparar_correlacionador.py --municipio 05837
    $py scripts\comparar_correlacionador.py --a v1 --b v1 --persistir
"""

from __future__ import annotations

import argparse
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
from territorial.agentes.persistencia import (  # noqa: E402
    crear_corrida,
    guardar_correlaciones,
)
from territorial.almacen.modelos import (  # noqa: E402
    ContextoMunicipal,
    CorridaAgentes,
    Insight,
    Municipio,
)
from territorial.almacen.sesion import sesion  # noqa: E402
from territorial.reglas.cifras import cifras as numeros  # noqa: E402
from territorial.reglas.cifras import variantes_de_cifra  # noqa: E402
from territorial.reglas.contexto import contexto_de  # noqa: E402

# --------------------------------------------------------------------------
# El piso de ruido, medido y no supuesto
# --------------------------------------------------------------------------
#
# **Una compuerta que no conoce su piso de ruido no mide un efecto: mide
# varianza y le pone una etiqueta de aprobado o suspenso.** La primera versión
# de este script exigía que B no correlacionara más que A en NINGÚN municipio, y
# el control demostró que eso habría suspendido a v1 contra sí mismo, con 14 de
# 18 municipios moviéndose.
#
# Estas cifras salen de correr **la misma versión contra sí misma** sobre el
# mismo corpus: corridas 11 y 12, más la pasada A del contraste v1/v2, sobre los
# 322 insights validados de la corrida 10. Si el corpus cambia, hay que volver a
# medirlas: la compuerta se niega a juzgar sobre un corpus sin piso.
CORPUS_DEL_PISO = 10

PISO_RUIDO: dict[str, tuple[int, ...]] = {
    # Tres pasadas de v1. Oscila 3 sobre una media de 41: un 7,3%.
    "convergencias": (42, 39, 42),
    # Las mismas tres pasadas. Oscila 4 sobre 22,3: un 17,9%.
    "tipologia": (20, 23, 24),
}


def techo_del_ruido(metrica: str) -> int:
    """El valor más alto que la misma versión produce contra sí misma.

    El criterio es **el rango observado**, no un margen relativo sobre A. Un
    margen sobre A tiene un filo: si A cae en el fondo de su rango y B en lo
    alto, el mismo prompt se suspendería a sí mismo. Con las cifras medidas eso
    no es hipotético — v1 dio 39 y 42 en dos pasadas seguidas.

    Propiedad que esto garantiza y que un margen no garantiza: **la compuerta
    nunca suspende a la línea base que la calibró.**
    """
    return max(PISO_RUIDO[metrica])


def oscilacion(metrica: str) -> float:
    """Cuánto se mueve la métrica sin que nada cambie. Solo para informar."""
    obs = PISO_RUIDO[metrica]
    return (max(obs) - min(obs)) / (sum(obs) / len(obs))


# Palabras que indican que la implicación se moja con una tipología, que es lo
# que CA-M4.2 pide y lo que el contexto debería mejorar.
TIPOLOGIA = (
    "vivienda", "residencial", "vis", "interés social", "interes social",
    "industrial", "logístic", "logistic", "comercial", "oficina", "bodega",
    "renovación", "renovacion", "estrato",
)


def numeros_del_contexto(fila: ContextoMunicipal | None) -> set[str]:
    """Las cifras reales del municipio. Si aparecen en la salida, es CA-M6.3."""
    if fila is None:
        return set()
    crudos = (
        fila.poblacion_total, fila.predios_urbanos, fila.valor_agregado,
        fila.deficit_cuantitativo, fila.deficit_cualitativo,
        fila.avaluo_catastral_urbano,
    )
    return set().union(*(variantes_de_cifra(v) for v in crudos))


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


def huellas(r: ResultadoCorrelacion) -> set[frozenset[int]]:
    """Cada convergencia por el conjunto de insights que agrupa.

    Es la comparación que de verdad mide reproducibilidad. Dos pasadas pueden
    dar el mismo NÚMERO de convergencias agrupando insights distintos, y contar
    convergencias lo daría por estable. Es el mismo criterio con el que se midió
    A6 señal a señal.
    """
    return {frozenset(c.ids_insight) for c in r.correlacionados}


def agrupados(r: ResultadoCorrelacion) -> set[int]:
    """Los insights que acabaron dentro de alguna convergencia."""
    return {i for c in r.correlacionados for i in c.ids_insight}


def main() -> int:
    p = argparse.ArgumentParser(description="Dos pasadas del Correlacionador")
    p.add_argument("--corrida", type=int, default=10,
                   help="corrida de agentes de la que salen los insights validados")
    p.add_argument("--a", default="v1", help="versión de prompt de la pasada A")
    p.add_argument("--b", default="v2", help="versión de prompt de la pasada B")
    p.add_argument("--municipio", help="DIVIPOLA; si se omite, todos los de la corrida")
    p.add_argument("--persistir", action="store_true",
                   help="guarda cada pasada como una corrida_agentes propia")
    args = p.parse_args()

    control = args.a == args.b

    filas_por_muni: dict[str, list[Insight]] = {}
    nombres: dict[str, tuple[str, str]] = {}
    contextos: dict[str, ContextoMunicipal | None] = {}
    bandas: dict[str, object] = {}

    with sesion() as s:
        corrida = s.get(CorridaAgentes, args.corrida)
        if corrida is None:
            print(f"ERROR: no existe la corrida de agentes {args.corrida}")
            return 1
        id_ciclo = corrida.id_ciclo
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

    n_insights = sum(len(v) for v in filas_por_muni.values())
    modo = "CONTROL de reproducibilidad" if control else "contraste de versiones"
    print(f"Corrida {args.corrida}, ciclo {id_ciclo}: {len(filas_por_muni)} municipios, "
          f"{n_insights} insights validados")
    print(f"{modo}: pasada A = {args.a}, pasada B = {args.b}\n")

    # Cada pasada es una corrida propia: es lo que `corrida_agentes` existe para
    # hacer, y sin ello las dos no podrían compararse después de este proceso.
    ids_corrida: dict[str, int] = {}
    if args.persistir:
        with sesion() as s:
            for etiqueta, version in (("A", args.a), ("B", args.b)):
                c = crear_corrida(
                    s, id_ciclo, sorted(filas_por_muni),
                    version_correlacionador=version,
                )
                s.flush()
                ids_corrida[etiqueta] = c.id
        print(f"pasadas persistidas: A = corrida {ids_corrida['A']}, "
              f"B = corrida {ids_corrida['B']}\n")

    tot = {"A": Counter(), "B": Counter()}
    fugas: list[tuple[str, set[str]]] = []
    fugas_reales: list[tuple[str, set[str]]] = []
    mas_en_b: list[tuple[str, int, int]] = []
    movidos: list[tuple[str, int, int, int, int]] = []  # nombre, A, B, iguales, distintas
    tot_huellas = Counter()
    tot_flip = Counter()

    print(f"{'municipio':<20} {'conv A':>7} {'conv B':>7} {'=':>4} {'solo A':>7} "
          f"{'solo B':>7} {'tipol A':>8} {'tipol B':>8}")
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

        # El contexto se pasa siempre: `correlacionar` lo ignora si la versión
        # no lo entiende (`VERSIONES_CON_CONTEXTO`).
        ra = correlacionar(entrada, nombre, depto, version=args.a, contexto=bandas[d])
        rb = correlacionar(entrada, nombre, depto, version=args.b, contexto=bandas[d])

        for etiqueta, r in (("A", ra), ("B", rb)):
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

        # --- reproducibilidad a nivel de convergencia ---
        ha, hb = huellas(ra), huellas(rb)
        iguales, solo_a, solo_b = len(ha & hb), len(ha - hb), len(hb - ha)
        tot_huellas["iguales"] += iguales
        tot_huellas["solo_a"] += solo_a
        tot_huellas["solo_b"] += solo_b
        if solo_a or solo_b:
            movidos.append((nombre, len(ra.correlacionados), len(rb.correlacionados),
                            iguales, solo_a + solo_b))

        # --- y a nivel de insight: ¿acabó dentro de una convergencia? ---
        ga, gb = agrupados(ra), agrupados(rb)
        tot_flip["en_ambas"] += len(ga & gb)
        tot_flip["voltean"] += len(ga ^ gb)
        tot_flip["total"] += len(entrada)

        if len(rb.correlacionados) > len(ra.correlacionados):
            mas_en_b.append((nombre, len(ra.correlacionados), len(rb.correlacionados)))

        # --- fuga de cifras, sobre la pasada B ---
        permitidas: set[str] = set()
        for i in insights:
            permitidas |= numeros(i.resumen) | numeros(i.implicacion_inmobiliaria or "")
            for e in i.evidencia or []:
                permitidas |= numeros(e.get("cita_textual", ""))
        inventadas = numeros(texto_de(rb)) - permitidas
        if inventadas:
            fugas.append((nombre, inventadas))
            del_contexto = inventadas & numeros_del_contexto(contextos[d])
            if del_contexto:
                fugas_reales.append((nombre, del_contexto))

        if args.persistir:
            with sesion() as s:
                for etiqueta, r in (("A", ra), ("B", rb)):
                    guardar_correlaciones(
                        s, r, ids_corrida[etiqueta], d,
                        {i.id: i.id for i in insights},
                    )

        print(f"{nombre[:20]:<20} {len(ra.correlacionados):>7} {len(rb.correlacionados):>7} "
              f"{iguales:>4} {solo_a:>7} {solo_b:>7} "
              f"{menciona_tipologia(ra):>8} {menciona_tipologia(rb):>8}")

    print("\n=== Totales ===")
    print(f"{'':<22} {args.a + ' (A)':>10} {args.b + ' (B)':>10}")
    for clave in ("convergencias", "rechazados", "tipologia",
                  "conf_alta", "conf_media", "conf_baja", "errores"):
        print(f"{clave:<22} {tot['A'][clave]:>10} {tot['B'][clave]:>10}")

    print("\n=== Tokens (el Correlacionador es el 89% del gasto) ===")
    for clave in ("entrada", "salida", "razonamiento"):
        a, b = tot["A"][clave], tot["B"][clave]
        delta = f"{(b - a) / a:+.1%}" if a else "-"
        print(f"{clave:<22} {a:>10,} {b:>10,}   {delta}")

    # ----------------------------------------------------------------------
    # Reproducibilidad — el dato que no existía
    # ----------------------------------------------------------------------
    total_h = tot_huellas["iguales"] + tot_huellas["solo_a"] + tot_huellas["solo_b"]
    print("\n=== Estabilidad de las convergencias (mismo conjunto de insights) ===")
    print(f"  idénticas en las dos pasadas : {tot_huellas['iguales']}")
    print(f"  solo en A ({args.a:<3})              : {tot_huellas['solo_a']}")
    print(f"  solo en B ({args.b:<3})              : {tot_huellas['solo_b']}")
    if total_h:
        print(f"  coincidencia                 : "
              f"{tot_huellas['iguales'] / total_h:.1%} de {total_h} convergencias distintas")
    if tot_flip["total"]:
        print(f"  insights que entran en una convergencia en una pasada y no en la "
              f"otra: {tot_flip['voltean']} de {tot_flip['total']} "
              f"({tot_flip['voltean'] / tot_flip['total']:.1%})")
    print(f"  municipios que se mueven     : {len(movidos)} de {len(filas_por_muni)}")
    for nombre, a, b, ig, dif in movidos:
        print(f"    {nombre:<20} {a} -> {b} convergencias · {ig} idénticas · {dif} distintas")

    # ----------------------------------------------------------------------
    # Compuertas
    # ----------------------------------------------------------------------
    fallos = 0

    print("\n=== Compuerta 1: B no correlaciona más que A, sobre el AGREGADO ===")
    if control:
        print("  NO APLICA: las dos pasadas son la misma versión. El movimiento "
              "entre ellas es lo que se está midiendo, no un fallo.")
        print(f"  ({len(mas_en_b)} de {len(filas_por_muni)} municipios suben. "
              "Municipio a municipio eso no significa nada: es el piso de ruido.)")
    elif args.corrida != CORPUS_DEL_PISO:
        fallos += 1
        print(f"  NO SE PUEDE JUZGAR: el piso de ruido se midió sobre la corrida "
              f"{CORPUS_DEL_PISO} y estás comparando sobre la {args.corrida}. "
              "Corre antes el control (--a X --b X) sobre este corpus. Sin piso, "
              "la comprobación mide varianza y le pone una etiqueta.")
    else:
        a, b = tot["A"]["convergencias"], tot["B"]["convergencias"]
        techo = techo_del_ruido("convergencias")
        print(f"  la misma versión consigo misma da {PISO_RUIDO['convergencias']}"
              f" -> oscila un {oscilacion('convergencias'):.1%}")
        print(f"  A = {a}, techo del rango = {techo}, B = {b}")
        if b > techo:
            fallos += 1
            print("  FALLA: B se sale del ruido hacia arriba. El contexto estaría "
                  "CREANDO convergencias, no explicándolas.")
            for nombre, x, y in mas_en_b:
                print(f"    (sube en {nombre}: {x} -> {y})")
        else:
            print("  pasa: la diferencia cabe dentro de lo que el agente se mueve "
                  "solo, sin que nada cambie.")

    # No es una compuerta —no hace fallar— pero sin esto se promovería ruido: si
    # el efecto buscado tampoco sale del piso, no hay efecto que promover.
    if not control:
        a, b = tot["A"]["tipologia"], tot["B"]["tipologia"]
        umbral = techo_del_ruido("tipologia")
        print("\n=== Efecto buscado (CA-M4.2): ¿sale del ruido? ===")
        print(f"  la misma versión consigo misma da {PISO_RUIDO['tipologia']} "
              f"-> oscila un {oscilacion('tipologia'):.1%}")
        print(f"  A = {a}, hace falta superar {umbral}, B = {b}")
        print("  " + ("EFECTO REAL: por encima del ruido."
                      if b > umbral else
                      "DENTRO DEL RUIDO: no hay efecto que promover."))

    print("\n=== Compuerta 2: ninguna cifra de la salida fuera de los insights ===")
    if fugas:
        fallos += 1
        print(f"  FALLA: {len(fugas)} municipios con cifras que no están en su entrada")
        for nombre, nums in fugas:
            print(f"    {nombre}: {sorted(nums)[:8]}")
    else:
        print("  pasa: ninguna cifra inventada")

    if fugas_reales:
        print("\n  Y son cifras REALES de contexto_municipal, que es peor: el número "
              "es correcto pero lo escribió el modelo (CA-M6.3).")
        for nombre, nums in fugas_reales:
            print(f"    {nombre}: {sorted(nums)}")

    print()
    if fallos:
        print(f"FALLIDA: {fallos} compuertas no pasan.")
        return 1
    print("CORRECTA.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
