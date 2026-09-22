r"""Precarga los usuarios autorizados a calificar. Idempotente.

**La app nunca escribe en `usuario`** (M9-acceso): quien no esté en esta tabla
puede leer el informe entero y no puede calificar. Por eso la lista entra por
aquí y no por la pantalla.

Dos consecuencias de que sea así, y las dos importan para H2:

· **El denominador se conoce antes de medir.** El universo queda fijado de
  antemano en vez de descubrirse al final, que es la forma habitual de que una
  tasa de respuesta acabe siendo indiscutible y a la vez incomparable.
· **Las escrituras de la app siguen siendo dos** —`calificacion` y
  `seguimiento`, las de CA-M9.16— y no tres.

El CSV **no viaja en el repositorio**: son datos personales y `data/` está en
`.gitignore`. La ruta se pasa por `--csv` o por `RUTA_USUARIOS`.

Columnas: `correo`, `id_gerencia`, `nombre`, `rol`. `rol` es `gerencia` o
`administrador`; solo el administrador ve el panel de métricas (CA-M9.14).

Uso:

    $py scripts\cargar_usuarios.py --csv data\usuarios.csv
    $py scripts\cargar_usuarios.py --csv ... --seco
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sqlalchemy import select  # noqa: E402

from territorial.almacen.modelos import Usuario  # noqa: E402
from territorial.almacen.sesion import aplicar_migraciones, sesion  # noqa: E402

COLUMNAS = ("correo", "id_gerencia", "nombre", "rol")
ROLES = ("gerencia", "administrador")


def leer(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        filas = list(csv.DictReader(f))
    if not filas:
        raise ValueError(f"{ruta}: el CSV no tiene filas")
    faltan = set(COLUMNAS) - set(filas[0])
    if faltan:
        raise ValueError(f"{ruta}: faltan columnas {sorted(faltan)}")

    limpias = []
    for n, f in enumerate(filas, start=2):
        rol = (f["rol"] or "gerencia").strip()
        if rol not in ROLES:
            raise ValueError(f"{ruta} línea {n}: rol «{rol}» no es {ROLES}")
        correo = f["correo"].strip().lower()
        if "@" not in correo:
            raise ValueError(f"{ruta} línea {n}: «{correo}» no parece un correo")
        limpias.append({
            "correo": correo,
            "id_gerencia": f["id_gerencia"].strip(),
            "nombre": f["nombre"].strip(),
            "rol": rol,
            "activo": True,
        })

    repes = sorted({c for c in (x["correo"] for x in limpias)
                    if [x["correo"] for x in limpias].count(c) > 1})
    if repes:
        raise ValueError(f"{ruta}: correos repetidos {repes}")
    return limpias


def main() -> int:
    p = argparse.ArgumentParser(description="Precarga los usuarios autorizados")
    p.add_argument("--csv", default=os.environ.get("RUTA_USUARIOS"),
                   help="ruta del CSV; por defecto, la variable RUTA_USUARIOS")
    p.add_argument("--seco", action="store_true", help="valida y no escribe")
    args = p.parse_args()

    if not args.csv:
        print("ERROR: falta la ruta del CSV. Pásala con --csv o en RUTA_USUARIOS.\n"
              "  Son datos personales: data/ no viaja en el repositorio.")
        return 1
    ruta = Path(args.csv)
    if not ruta.is_absolute():
        ruta = RAIZ / ruta
    if not ruta.exists():
        print(f"ERROR: no existe {ruta}")
        return 1

    filas = leer(ruta)
    print(f"{ruta.name}: {len(filas)} usuarios")
    for f in filas:
        print(f"  {f['id_gerencia']:<22} {f['rol']:<14} {f['correo']}")

    if args.seco:
        print("\n[SECO] no se escribió nada.")
        return 0

    aplicar_migraciones()
    nuevos = actualizados = iguales = 0
    with sesion() as s:
        existentes = {u.correo.lower(): u for u in s.scalars(select(Usuario)).all()}
        for f in filas:
            actual = existentes.pop(f["correo"], None)
            if actual is None:
                s.add(Usuario(**f))
                nuevos += 1
                continue
            cambios = {k: v for k, v in f.items() if getattr(actual, k) != v}
            if cambios:
                for k, v in cambios.items():
                    setattr(actual, k, v)
                actualizados += 1
            else:
                iguales += 1
        sobrantes = sorted(existentes)

    print(f"\ninsertados {nuevos} · actualizados {actualizados} · sin cambios {iguales}")
    if sobrantes:
        # No se borran: una calificación ya emitida cuelga de su gerencia, y
        # borrar el usuario no la borra pero sí deja huérfano el denominador.
        print(f"AVISO: {len(sobrantes)} usuarios en la base que el CSV ya no trae "
              f"(no se borran): {sobrantes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
