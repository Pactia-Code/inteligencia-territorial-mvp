r"""Carga `contexto_municipal` desde TerriData. Idempotente.

Lee el zip de 3,31 GB **por streaming** —no lo extrae— y se queda con seis
indicadores de los 1.750. La lógica vive en `territorial.ingesta.contexto`.

El zip **no viaja en el repositorio**: la ruta va por `--zip` o por la variable
`RUTA_TERRIDATA`. Y como la pasada tarda unos tres minutos, el resultado se
exporta también a un CSV pequeño en `data/`, para no depender del archivo
grande cada vez: `--desde-csv` recarga desde ahí en un segundo.

**Este contexto no entra al scoring.** Ver el encabezado de `ContextoMunicipal`.

Uso:

    $py scripts\cargar_contexto.py --zip data\TerriData.txt.zip
    $py scripts\cargar_contexto.py --desde-csv data\contexto_municipal.csv
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

from territorial.almacen.modelos import ContextoMunicipal  # noqa: E402
from territorial.almacen.sesion import aplicar_migraciones, sesion  # noqa: E402
from territorial.ingesta.contexto import INDICADORES, extraer  # noqa: E402

CAMPOS = [
    "codigo_divipola",
    "poblacion_total", "anio_poblacion",
    "valor_agregado", "anio_valor_agregado",
    "deficit_cuantitativo", "deficit_cualitativo", "anio_deficit",
    "avaluo_catastral_urbano", "predios_urbanos", "anio_catastro",
]
ENTEROS = {"poblacion_total", "predios_urbanos", "anio_poblacion",
           "anio_valor_agregado", "anio_deficit", "anio_catastro"}


def exportar_csv(datos: dict[str, dict], destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        for codigo in sorted(datos):
            w.writerow({c: datos[codigo].get(c, "") for c in CAMPOS})


def leer_csv(ruta: Path) -> dict[str, dict]:
    datos: dict[str, dict] = {}
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        for fila in csv.DictReader(f):
            caja: dict = {"codigo_divipola": fila["codigo_divipola"]}
            for campo in CAMPOS[1:]:
                crudo = (fila.get(campo) or "").strip()
                if not crudo:
                    continue
                caja[campo] = int(float(crudo)) if campo in ENTEROS else float(crudo)
            datos[caja["codigo_divipola"]] = caja
    return datos


def cargar(datos: dict[str, dict]) -> tuple[int, int, int]:
    """Inserta lo que falta, actualiza lo que cambió. Idempotente."""
    nuevas = actualizadas = iguales = 0
    with sesion() as s:
        existentes = {c.codigo_divipola: c for c in s.scalars(select(ContextoMunicipal)).all()}
        for codigo in sorted(datos):
            fila = {c: datos[codigo].get(c) for c in CAMPOS}
            actual = existentes.get(codigo)
            if actual is None:
                s.add(ContextoMunicipal(**fila))
                nuevas += 1
                continue
            cambios = {c: v for c, v in fila.items() if getattr(actual, c) != v}
            if cambios:
                for campo, valor in cambios.items():
                    setattr(actual, campo, valor)
                actualizadas += 1
            else:
                iguales += 1
    return nuevas, actualizadas, iguales


def main() -> int:
    p = argparse.ArgumentParser(description="Carga el contexto municipal de TerriData")
    p.add_argument("--zip", default=os.environ.get("RUTA_TERRIDATA"),
                   help="ruta del TerriData.txt.zip; por defecto, RUTA_TERRIDATA")
    p.add_argument("--desde-csv", help="recarga desde el CSV exportado, sin tocar el zip")
    p.add_argument("--csv-salida", default="data/contexto_municipal.csv")
    args = p.parse_args()

    if args.desde_csv:
        ruta = Path(args.desde_csv)
        if not ruta.is_absolute():
            ruta = RAIZ / ruta
        if not ruta.exists():
            print(f"ERROR: no existe {ruta}")
            return 1
        datos = leer_csv(ruta)
        print(f"{ruta.name}: {len(datos)} municipios")
    else:
        if not args.zip:
            print("ERROR: falta la ruta del zip. Pásala con --zip o en RUTA_TERRIDATA,\n"
                  "  o recarga desde el CSV exportado con --desde-csv.")
            return 1
        ruta = Path(args.zip)
        if not ruta.is_absolute():
            ruta = RAIZ / ruta
        if not ruta.exists():
            print(f"ERROR: no existe {ruta}")
            return 1

        print(f"Leyendo {ruta.name} por streaming. Son 14,5 millones de filas, "
              "unos tres minutos.")
        datos, c = extraer(ruta)
        print(f"\n{c.filas_leidas:,} filas leídas · {c.filas_usadas:,} usadas · "
              f"{c.duplicados:,} duplicados ignorados · {c.no_numericos:,} sin número")
        print(f"{c.municipios} municipios\n")
        print(f"{'indicador':<12} {'campo':<26} {'año':>6} {'municipios':>11}")
        for ind in INDICADORES:
            print(f"{ind.codigo:<12} {ind.campo:<26} "
                  f"{c.anios_elegidos.get(ind.codigo, '-'):>6} "
                  f"{c.por_indicador.get(ind.codigo, 0):>11}")

        salida = Path(args.csv_salida)
        if not salida.is_absolute():
            salida = RAIZ / salida
        exportar_csv(datos, salida)
        print(f"\nexportado a {salida.relative_to(RAIZ)} "
              f"({salida.stat().st_size / 1024:.0f} KB) — recárgalo con --desde-csv")

    aplicar_migraciones()
    nuevas, actualizadas, iguales = cargar(datos)
    print(f"\ninsertadas {nuevas} · actualizadas {actualizadas} · sin cambios {iguales}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
