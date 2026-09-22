r"""Genera el contrato TypeScript de las tablas que escribe M9, desde `modelos.py`.

**Por qué existe.** La app va en Next.js y escribe directamente sobre Neon: la
regla 1 de D8 protege escrituras y esquema, no lecturas, y el PRD §4.3 prohíbe
una API intermedia. Pero la misma regla pone una condición: *«las escrituras de
la app pasan por Python, o **su forma se verifica contra `modelos.py`**»*.

Esto es esa verificación, y la resuelve **generando en vez de duplicando**. Una
lista de columnas escrita a mano en TypeScript es una segunda fuente de verdad
que envejece en silencio: alguien renombra un campo en `modelos.py`, las pruebas
de Python siguen verdes y la app escribe contra una columna que ya no existe.
Aquí no hay nada que mantener sincronizado, porque hay un solo original.

**La prueba es la mitad importante.** `tests/test_contrato.py` regenera el
contrato y lo compara con el archivo en disco: si alguien toca `modelos.py` y no
regenera, el suite falla. Es el mismo mecanismo que `alembic check` —comparar lo
declarado contra lo real y fallar si divergen— aplicado al lenguaje que no
comparte el modelo.

**Solo las dos tablas que M9 escribe** (CA-M9.16): `calificacion` y
`seguimiento`. El resto del esquema la app solo lo lee, y una lectura no puede
corromper nada.

Uso:

    $py scripts\generar_contrato_ts.py            # escribe el archivo
    $py scripts\generar_contrato_ts.py --check    # falla si esta desactualizado
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sqlalchemy import (  # noqa: E402
    CheckConstraint,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)

from territorial.almacen.modelos import Base  # noqa: E402

# Exactamente las de CA-M9.16. Añadir una aquí es ampliar lo que la app puede
# escribir, así que no se hace sin decidirlo.
TABLAS: tuple[str, ...] = ("calificacion", "seguimiento")

DESTINO = Path("web/lib/contrato.generado.ts")

CABECERA = """// GENERADO AUTOMÁTICAMENTE — NO EDITAR A MANO.
//
// Sale de `src/territorial/almacen/modelos.py` vía
// `scripts/generar_contrato_ts.py`. Si cambias el modelo, regenera:
//
//     $py scripts\\generar_contrato_ts.py
//
// `tests/test_contrato.py` falla si este archivo se queda atrás, que es lo que
// impide que la app escriba contra una columna que ya no existe.
//
// Solo las dos tablas que M9 puede escribir (CA-M9.16). Todo lo demás se lee.
"""


def _tipo_ts(columna) -> str:
    """Del tipo SQLAlchemy al de TypeScript. Conservador a propósito."""
    tipo = columna.type
    if isinstance(tipo, (Integer, Float)):
        base = "number"
    elif isinstance(tipo, (String, Text)):
        base = "string"
    elif isinstance(tipo, (DateTime, Date)):
        # Viajan como ISO 8601: el driver de Neon no devuelve Date.
        base = "string"
    elif tipo.__class__.__name__ == "Boolean":
        base = "boolean"
    else:  # pragma: no cover — hoy ninguna columna de las dos tablas cae aquí
        base = "unknown"
    return f"{base} | null" if columna.nullable else base


def _valores_permitidos(tabla, columna_nombre: str) -> list[str] | None:
    """Los valores de un CHECK `col IN ('a','b')`, si los hay.

    Se extraen para que la app no pueda mandar un estado que la base va a
    rechazar: mejor un error de compilación que un 500 en la ventana de
    calificación.
    """
    for restriccion in tabla.constraints:
        if not isinstance(restriccion, CheckConstraint):
            continue
        texto = str(restriccion.sqltext)
        if f"{columna_nombre} IN (" not in texto:
            continue
        crudo = texto.split("IN (", 1)[1].rsplit(")", 1)[0]
        return [v.strip().strip("'\"") for v in crudo.split(",")]
    return None


def _rango(tabla, columna_nombre: str) -> tuple[int, int] | None:
    """El rango de un CHECK `col BETWEEN a AND b`. Hoy, el 1-5 de CA-M7.2."""
    for restriccion in tabla.constraints:
        if not isinstance(restriccion, CheckConstraint):
            continue
        texto = str(restriccion.sqltext)
        if f"{columna_nombre} BETWEEN " not in texto:
            continue
        crudo = texto.split("BETWEEN ", 1)[1]
        desde, hasta = crudo.split(" AND ")
        return int(desde.strip()), int(hasta.strip().rstrip(")"))
    return None


def _nombre_ts(tabla: str) -> str:
    return "".join(p.capitalize() for p in tabla.split("_"))


def generar() -> str:
    """El contenido completo del archivo. Determinista: mismo modelo, mismo texto."""
    partes = [CABECERA]
    tablas = {t.name: t for t in Base.metadata.sorted_tables}

    for nombre in TABLAS:
        tabla = tablas[nombre]
        clase = _nombre_ts(nombre)
        columnas = list(tabla.columns)

        partes.append(f"\n// ---- {nombre} ----\n")
        partes.append(
            f"export const COLUMNAS_{nombre.upper()} = [\n"
            + "".join(f'  "{c.name}",\n' for c in columnas)
            + "] as const;\n"
        )

        campos = []
        for c in columnas:
            valores = _valores_permitidos(tabla, c.name)
            tipo = (
                " | ".join(f'"{v}"' for v in valores) if valores else _tipo_ts(c)
            )
            if valores and c.nullable:
                tipo += " | null"
            comentario = ""
            rango = _rango(tabla, c.name)
            if rango:
                comentario = f"  // {rango[0]}-{rango[1]}, exigido por la base"
            campos.append(f"  {c.name}: {tipo};{comentario}\n")
        partes.append(f"\nexport interface Fila{clase} {{\n" + "".join(campos) + "}\n")

        # Lo que la app rellena: sin la clave primaria ni lo que tiene default.
        escribibles = [
            c.name for c in columnas
            if not c.primary_key and c.default is None and c.server_default is None
        ]
        partes.append(
            f"\nexport type Nueva{clase} = Pick<\n  Fila{clase},\n"
            + "".join(f'  | "{n}"\n' for n in escribibles)
            + ">;\n"
        )

        for c in columnas:
            valores = _valores_permitidos(tabla, c.name)
            if valores:
                partes.append(
                    f"\nexport const {c.name.upper()}_{nombre.upper()} = [\n"
                    + "".join(f'  "{v}",\n' for v in valores)
                    + "] as const;\n"
                )
            rango = _rango(tabla, c.name)
            if rango:
                # Con el nombre de la tabla dentro: dos tablas con una columna
                # `valor` acotada colisionarían en un único espacio de nombres.
                partes.append(
                    f"\nexport const {c.name.upper()}_{nombre.upper()}_MIN = "
                    f"{rango[0]};\n"
                    f"export const {c.name.upper()}_{nombre.upper()}_MAX = "
                    f"{rango[1]};\n"
                )

    return "".join(partes)


def main() -> int:
    p = argparse.ArgumentParser(description="Contrato TS desde modelos.py")
    p.add_argument("--check", action="store_true",
                   help="no escribe; falla si el archivo está desactualizado")
    p.add_argument("--destino", default=str(DESTINO))
    args = p.parse_args()

    ruta = Path(args.destino)
    if not ruta.is_absolute():
        ruta = RAIZ / ruta
    contenido = generar()

    if args.check:
        if not ruta.exists():
            print(f"FALTA: {ruta.relative_to(RAIZ)} no existe. Regenera.")
            return 1
        if ruta.read_text(encoding="utf-8") != contenido:
            print(f"DESACTUALIZADO: {ruta.relative_to(RAIZ)} no concuerda con "
                  "modelos.py. Regenera con scripts/generar_contrato_ts.py")
            return 1
        print(f"{ruta.relative_to(RAIZ)} al día.")
        return 0

    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8")
    print(f"{ruta.relative_to(RAIZ)} · {len(contenido.splitlines())} líneas · "
          f"{dt.date.today().isoformat()}")
    for nombre in TABLAS:
        print(f"  {nombre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
