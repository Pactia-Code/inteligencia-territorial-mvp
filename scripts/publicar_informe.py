r"""Publica el informe de un ciclo. **Único punto de entrada de la publicación.**

F0.6 de la remediación (hallazgo H-040). Antes se publicaba llamando a
`publicar()` desde donde fuera —una sesión interactiva, un script de una vez— y
el informe no guardaba con qué código se había compuesto. Eso es lo que hace que
un informe publicado no se pueda regenerar meses después: el payload depende de
`informes/composicion.py`, que cambia.

Por aquí, cada publicación deja en `informe.origen` el **commit** del árbol de
trabajo y la **invocación** exacta, además de la fecha. Con eso, reconstruir el
informe es `git checkout <commit>` y volver a componer.

**Las dos corridas se pasan explícitas y no se resuelve «la última».** Es lo que
el informe congela y la razón de que se pueda reconstruir. `--listar` enseña qué
hay disponible por ciclo.

**Guarda de calificadores.** Se niega a publicar si no hay ninguna gerencia
«prd» declarada en `config/gerencias.json`, o si alguna «prd» no tiene usuario
activo con rol `gerencia`. El motivo está en `exigir_calificadores`: el
denominador de H2 se congela al publicar, y darlo de alta después no lo arregla.

Uso:

    $py scripts\publicar_informe.py --listar
    $py scripts\publicar_informe.py --ciclo 3 --scoring 24 --agentes 10 --seco
    $py scripts\publicar_informe.py --ciclo 3 --scoring 24 --agentes 10

**Nunca contra la base principal sin decidirlo.** La base sale de
`DATABASE_URL`; el script la imprime enmascarada antes de escribir, y con
`--seco` compone, enseña el resumen y revierte.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from territorial.almacen.sesion import sesion  # noqa: E402
from territorial.config import obtener_config  # noqa: E402
from territorial.informes.publicacion import (  # noqa: E402
    PublicacionInvalida,
    ciclos_publicables,
    exigir_calificadores,
    informe_vigente,
    publicar,
)


def base_enmascarada() -> str:
    """La base a la que se apunta, sin credenciales. Se imprime siempre."""
    url = obtener_config().url_base_datos
    return re.sub(r"//[^@/]*@", "//***@", url)


def listar() -> int:
    with sesion() as s:
        cajas = ciclos_publicables(s)
        if not cajas:
            print("no hay ciclos con corridas")
            return 1
        for ciclo, caja in cajas.items():
            vigente = informe_vigente(s, ciclo)
            estado = f"informe {vigente.id} publicado" if vigente else "sin informe"
            if caja["publicable"]:
                print(f"  ciclo {ciclo}: scoring {caja['scoring']} · "
                      f"agentes {caja['agentes']} · {estado}")
            else:
                print(f"  ciclo {ciclo}: NO publicable, falta {caja['falta']} · {estado}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Publica el informe de un ciclo")
    p.add_argument("--listar", action="store_true", help="qué hay publicable y no publica")
    p.add_argument("--ciclo", type=int, help="ciclo a publicar; se comprueba contra las corridas")
    p.add_argument("--scoring", type=int, help="id de la corrida de scoring")
    p.add_argument("--agentes", type=int, help="id de la corrida de agentes")
    p.add_argument("--tope-calificable", type=int, default=3,
                   help="hasta qué puesto se pide calificar (M9-carga)")
    p.add_argument("--seco", action="store_true", help="compone, enseña el resumen y revierte")
    args = p.parse_args()

    print(f"base: {base_enmascarada()}")

    if args.listar:
        return listar()

    if args.ciclo is None or args.scoring is None or args.agentes is None:
        print("ERROR: hacen falta --ciclo, --scoring y --agentes. Usa --listar para verlos.")
        return 1

    invocacion = "scripts/publicar_informe.py " + " ".join(sys.argv[1:])

    try:
        with sesion() as s:
            # Se comprueba antes de componer para que el mensaje llegue rápido y
            # sin haber armado un payload que no se va a usar.
            prd = exigir_calificadores(s)
            print(f"gerencias «prd» con calificador activo: {prd}")

            informe = publicar(
                s, args.scoring, args.agentes,
                tope_calificable=args.tope_calificable,
                invocacion=invocacion,
            )
            if informe.id_ciclo != args.ciclo:
                raise PublicacionInvalida(
                    f"las corridas son del ciclo {informe.id_ciclo} y se pidió publicar "
                    f"el {args.ciclo}. No se publica: el ciclo se declara para que un "
                    "error de dedo en los ids no pase inadvertido."
                )

            contenido = informe.contenido
            gerencias = contenido["calificacion"]["gerencias"]
            print(f"\nciclo {informe.id_ciclo} · corridas "
                  f"{informe.id_corrida}/{informe.id_corrida_agentes}")
            print(f"  municipios mostrados: {contenido['calificacion']['mostrados']}")
            print(f"  se pide calificar hasta el puesto "
                  f"{contenido['calificacion']['pedida_hasta_puesto']}")
            print(f"  gerencias congeladas: {json.dumps(gerencias, ensure_ascii=False)}")
            print(f"  origen: {json.dumps(informe.origen, ensure_ascii=False)}")

            if args.seco:
                s.rollback()
                print("\n[SECO] revertido. No se publicó nada.")
                return 0

            print(f"\npublicado como informe {informe.id}. "
                  "El anterior del ciclo queda archivado, no borrado.")
    except PublicacionInvalida as e:
        print(f"\nNO SE PUBLICA: {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
