"""Genera las hojas de revisión humana de insights.

**Diseño ciego con dos bloques.** Cada hoja mezcla insights *estables* —los que
aparecen en las dos pasadas con el mismo conjunto de señales— con insights que
*voltearon* —los que existen en una pasada y no en la otra—, sin marcar cuál es
cuál. El revisor los califica todos igual y la comparación se hace después.

Por qué mezclados y no solo los inestables: un equipo que revisa únicamente
casos limítrofes concluye que el sistema no distingue nada, porque no vio ni un
acierto claro. Y se perdería la otra pregunta, que sigue abierta: si lo que el
sistema produce en su día normal es correcto.

De una sola pasada del equipo salen tres cosas:

  1. Si los estables son correctos — calidad de base.
  2. Si los que voltearon son genuinamente ambiguos para un humano, o el modelo
     está dudando de casos que una persona resuelve sin pestañear.
  3. El acuerdo entre las cinco personas **dentro de cada grupo**. Si el
     desacuerdo humano se concentra en los que voltearon, queda confirmado que
     A6 no es un defecto del modelo sino una **frontera mal definida**, que es
     lo que hay que decidir.

**Se toma la corrida 7 por ser la primera**, y eso no fuerza el pendiente A9:
los estables están en las dos por definición, y de los que voltean da igual qué
versión mande — lo que se quiere saber es si el caso es ambiguo, no cuál de las
dos lecturas era mejor.

**El reparto es por ronda entre municipios**, no proporcional al volumen. Si los
45 salieran de los de más insights, la hoja sería casi toda Barranquilla,
Armenia y Cartagena, y no se vería Funza — que es donde vive el problema.

La clave que dice qué insight es de qué grupo se escribe **aparte** y no se
reparte.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sqlalchemy import select  # noqa: E402

from territorial.almacen.modelos import Insight, Municipio  # noqa: E402
from territorial.almacen.sesion import sesion  # noqa: E402

CABECERA = [
    "id_insight", "municipio", "resumen", "n_evidencias",
    "cita_textual", "fuente_url", "fecha_fuente",
    "verificacion", "que_esta_mal", "relevancia", "que_le_falta",
]

INSTRUCCIONES = (
    "INSTRUCCIONES: verifica solo las TRES PRIMERAS citas de cada insight, no todas. "
    "Hay insights con muchas evidencias y la pregunta no tendria respuesta unica. "
    "Rellena verificacion, que_esta_mal, relevancia y que_le_falta una vez por insight. "
    "Responde sobre los 45, en el orden en que aparecen."
)


def por_ronda(pool: list[Insight], cuantos: int, semilla: int) -> list[Insight]:
    """Reparte entre municipios dando una vuelta a cada uno antes de repetir.

    Maximiza la cobertura de municipios distintos, que es lo que evita que los
    de más volumen copen la hoja.
    """
    grupos: dict[str, list[Insight]] = defaultdict(list)
    for x in pool:
        grupos[x.divipola].append(x)
    rnd = random.Random(semilla)
    for g in grupos.values():
        rnd.shuffle(g)

    elegidos: list[Insight] = []
    municipios = sorted(grupos)
    ronda = 0
    while len(elegidos) < cuantos:
        quedan = [d for d in municipios if len(grupos[d]) > ronda]
        if not quedan:
            break
        for d in quedan:
            if len(elegidos) >= cuantos:
                break
            elegidos.append(grupos[d][ronda])
        ronda += 1
    return elegidos


def fila(ins: Insight, nombre: str) -> list:
    ev = ins.evidencia or []
    return [
        ins.id,
        nombre,
        (ins.resumen or "").strip(),
        len(ev),
        "\n".join(f"{n}. {(e.get('cita_textual') or '').strip()}" for n, e in enumerate(ev, 1)),
        "\n".join(f"{n}. {e.get('url') or 'SIN URL'}" for n, e in enumerate(ev, 1)),
        "\n".join(f"{n}. {e.get('fecha') or 'SIN FECHA'}" for n, e in enumerate(ev, 1)),
        "", "", "", "",
    ]


def main() -> int:
    p = argparse.ArgumentParser(description="Hojas de revisión ciegas")
    p.add_argument("--corrida", type=int, default=7, help="pasada de la que salen")
    p.add_argument("--contra", type=int, default=8, help="pasada con la que se compara")
    p.add_argument("--estables", type=int, default=30)
    p.add_argument("--volteados", type=int, default=15)
    p.add_argument("--copias", type=int, default=5)
    p.add_argument("--semilla", type=int, default=20260921)
    p.add_argument("--destino", default="data/revision")
    args = p.parse_args()

    with sesion() as s:
        nom = {m.divipola: m.nombre for m in s.query(Municipio).all()}
        ia = s.scalars(select(Insight).where(Insight.id_corrida == args.corrida)).all()
        ib = s.scalars(select(Insight).where(Insight.id_corrida == args.contra)).all()
        sets_b = {frozenset(x.ids_senal or []) for x in ib}

        estables = [x for x in ia if frozenset(x.ids_senal or []) in sets_b]
        volteados = [x for x in ia if frozenset(x.ids_senal or []) not in sets_b]
        print(f"Pool: {len(estables)} estables, {len(volteados)} volteados "
              f"(corrida {args.corrida} contra {args.contra})")

        elegidos_e = por_ronda(estables, args.estables, args.semilla)
        elegidos_v = por_ronda(volteados, args.volteados, args.semilla + 1)
        if len(elegidos_e) < args.estables or len(elegidos_v) < args.volteados:
            print(f"  AVISO: el pool no da para {args.estables}+{args.volteados}; "
                  f"salen {len(elegidos_e)}+{len(elegidos_v)}")

        marcados = [(x, "estable") for x in elegidos_e] + [(x, "volteado") for x in elegidos_v]
        random.Random(args.semilla).shuffle(marcados)

        destino = RAIZ / args.destino
        destino.mkdir(parents=True, exist_ok=True)
        for viejo in destino.glob("revision_insights_persona*.csv"):
            viejo.unlink()

        filas = [fila(x, nom.get(x.divipola, x.divipola)) for x, _ in marcados]
        for n in range(1, args.copias + 1):
            ruta = destino / f"revision_insights_persona{n}.csv"
            with ruta.open("w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow([INSTRUCCIONES] + [""] * (len(CABECERA) - 1))
                w.writerow(CABECERA)
                w.writerows(filas)
            print(f"  {ruta.name}: {len(filas)} insights")

        clave = destino / "CLAVE_NO_REPARTIR.csv"
        with clave.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["id_insight", "municipio", "grupo", "corrida"])
            for x, g in marcados:
                w.writerow([x.id, nom.get(x.divipola, x.divipola), g, args.corrida])
        print(f"  {clave.name}: la clave. NO va al equipo.")

        from collections import Counter
        c = Counter((nom.get(x.divipola, x.divipola), g) for x, g in marcados)
        print()
        print(f"{'municipio':22} {'estables':>9} {'voltean':>8}")
        for d in sorted({k[0] for k in c}):
            print(f"{d[:22]:22} {c[(d, 'estable')]:>9} {c[(d, 'volteado')]:>8}")
        print(f"{'TOTAL':22} {len(elegidos_e):>9} {len(elegidos_v):>8}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
