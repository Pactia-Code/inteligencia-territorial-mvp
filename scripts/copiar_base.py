r"""Copia una base completa a otra, fila a fila y por SQLAlchemy.

**Por qué no `pg_dump`.** La base de desarrollo es SQLite (D8), no PostgreSQL,
así que no hay volcado nativo que restaurar en Neon. Y aunque lo hubiera, la
regla 2.1 dice que todo acceso a datos pasa por SQLAlchemy: un volcado con SQL
de un motor concreto es exactamente lo que esa regla prohíbe, porque ata el
procedimiento a un motor y deja de servir para el otro.

Copiar por el ORM tiene además una ventaja que aquí importa: los tipos los
traduce SQLAlchemy. Las columnas `JSON` portátiles salen de SQLite como texto y
entran en Postgres como `json` sin que este script sepa nada del asunto.

**Los identificadores se conservan.** No se reasignan: `informe.id_corrida`,
`insight.id_corrida` y `calificacion.id_insight` apuntan a números concretos, y
renumerar rompería el linaje que sostiene H4. Por eso al final hay que mover las
secuencias de Postgres, que si no arrancarían en 1 y chocarían con lo copiado.

**Las fechas se reetiquetan como UTC.** El código escribe `datetime.now(UTC)`,
SQLite no guarda la zona y las devuelve ingenuas. Si se insertan así en un
`timestamptz`, Postgres las interpreta en la zona del servidor. Neon está en
UTC y saldría bien por casualidad; se hace explícito para que no dependa de eso.

Uso:

    $py scripts\copiar_base.py --destino "postgresql://...neon.tech/territorial"
    $py scripts\copiar_base.py --origen sqlite:///data/territorial.db --destino ... --vaciar
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sqlalchemy import create_engine, func, inspect, select, text  # noqa: E402

from territorial.almacen.modelos import Base  # noqa: E402
from territorial.almacen.sesion import es_pooled, normalizar_url  # noqa: E402
from territorial.config import obtener_config  # noqa: E402

# Filas por INSERT. 500 va sobrado para las 20.030 de `senal_cruda` y mantiene
# el tamaño de cada sentencia lejos de cualquier límite de parámetros.
LOTE = 500


def _utc(valor):
    """Etiqueta como UTC una fecha-hora ingenua. El resto pasa intacto."""
    if isinstance(valor, datetime) and valor.tzinfo is None:
        return valor.replace(tzinfo=UTC)
    return valor


def _resetear_secuencias(conexion, tablas) -> list[str]:
    """Deja cada secuencia por encima del id más alto copiado.

    Sin esto el primer `INSERT` en Postgres pide el id 1, que ya existe, y falla
    con una violación de clave primaria — lejos de aquí y sin relación aparente
    con la copia.
    """
    movidas = []
    for tabla in tablas:
        columnas = [c for c in tabla.primary_key if c.type.python_type is int]
        if len(columnas) != 1:
            continue
        col = columnas[0].name
        secuencia = conexion.execute(
            text("SELECT pg_get_serial_sequence(:t, :c)"), {"t": tabla.name, "c": col}
        ).scalar()
        if not secuencia:
            continue
        maximo = conexion.execute(
            text(f'SELECT COALESCE(MAX("{col}"), 0) FROM "{tabla.name}"')  # noqa: S608
        ).scalar()
        conexion.execute(
            text("SELECT setval(:s, :v, true)"), {"s": secuencia, "v": max(int(maximo), 1)}
        )
        movidas.append(f"{tabla.name}.{col} -> {maximo}")
    return movidas


def main() -> int:
    cfg = obtener_config()
    p = argparse.ArgumentParser(description="Copia una base a otra por SQLAlchemy")
    p.add_argument("--origen", default="sqlite:///data/territorial.db")
    p.add_argument("--destino", default=cfg.url_base_datos,
                   help="por defecto, la DATABASE_URL configurada")
    p.add_argument("--vaciar", action="store_true",
                   help="borra las filas del destino antes de copiar")
    p.add_argument("--seco", action="store_true", help="cuenta y no escribe nada")
    args = p.parse_args()

    origen = normalizar_url(args.origen, cfg)
    destino = normalizar_url(args.destino, cfg)

    if origen == destino:
        print(f"ERROR: origen y destino son la misma base:\n  {origen}")
        return 1
    if es_pooled(destino):
        print("ERROR: el destino es el endpoint pooled. Usa la conexión directa, "
              "el mismo host sin '-pooler'.")
        return 1

    print(f"origen : {origen.split('@')[-1]}")
    print(f"destino: {destino.split('@')[-1]}")
    print()

    mo = create_engine(origen, future=True)
    md = create_engine(destino, future=True, pool_pre_ping=not destino.startswith("sqlite"))

    tablas = list(Base.metadata.sorted_tables)

    # El destino tiene que venir migrado. Crearlo aquí saltándose Alembic es la
    # regla 2 de D8 al revés, y dejaría la base sin `alembic_version`.
    faltan = set(t.name for t in tablas) - set(inspect(md).get_table_names())
    if faltan:
        print(f"ERROR: al destino le faltan {len(faltan)} tablas: {sorted(faltan)}")
        print("Corre primero:  alembic upgrade head  apuntando al destino.")
        return 1

    with mo.connect() as co, md.begin() as cd:
        ocupadas = {
            t.name: cd.execute(select(func.count()).select_from(t)).scalar()
            for t in tablas
        }
        con_filas = {k: v for k, v in ocupadas.items() if v}
        if con_filas and not args.vaciar:
            print(f"ERROR: el destino ya tiene datos en {len(con_filas)} tablas: {con_filas}")
            print("Usa --vaciar si de verdad quieres reemplazarlos.")
            return 1

        if con_filas and args.vaciar and not args.seco:
            # En orden inverso de dependencias, para no chocar con las FK.
            for t in reversed(tablas):
                cd.execute(t.delete())
            print(f"destino vaciado ({sum(con_filas.values())} filas)\n")

        total = 0
        print(f"{'tabla':<24} {'filas':>8}")
        for t in tablas:
            columnas = [c.name for c in t.columns]
            filas = [
                {c: _utc(v) for c, v in zip(columnas, fila, strict=True)}
                for fila in co.execute(select(t)).fetchall()
            ]
            if filas and not args.seco:
                for i in range(0, len(filas), LOTE):
                    cd.execute(t.insert(), filas[i : i + LOTE])
            print(f"{t.name:<24} {len(filas):>8}")
            total += len(filas)

        if args.seco:
            print(f"\n[SECO] no se escribió nada. {total} filas contadas.")
            cd.rollback()
            return 0

        if destino.startswith("postgresql"):
            movidas = _resetear_secuencias(cd, tablas)
            print(f"\nsecuencias reiniciadas: {len(movidas)}")

    print(f"\n{total} filas copiadas.")
    # Cadena cruda: sin la `r`, el `\v` de `\verificar` es una tabulacion
    # vertical y la linea sale impresa como "scriptserificar_copia.py".
    print(r"Verifica ahora con:  scripts\verificar_copia.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
