r"""Regenera `docs/informe_resultados.md` desde la base. F0b.1 (H-034). **Solo lectura.**

El documento ya no se escribe a mano: la prosa vive en
`src/territorial/informes/plantilla_resultados.md` y cada cifra sale de una
medición con su consulta, sus corridas y el commit. Ver
`src/territorial/informes/resultados.py`.

**Determinista.** Con los mismos parámetros y la misma base, la salida es la
misma byte a byte: no se escribe ninguna hora. El commit y los cortes son
parámetros; `--a-fecha` solo decide si la ronda extendida ya cerró, y no
aparece en el documento.

**Cierre de la auditoría:** `--check` regenera en memoria y falla si difiere
del archivo commiteado.

**Solo lectura, garantizado por la base**: en PostgreSQL la conexión se abre
con la transacción en READ ONLY, así que una escritura accidental fallaría en
vez de pasar. Al terminar se revierte igualmente.

Uso:

    $py = "$env:LOCALAPPDATA\venvs\territorial\Scripts\python.exe"
    & $py scripts\informe_resultados.py --commit <commit>
    & $py scripts\informe_resultados.py --commit <commit> --check
"""

from __future__ import annotations

import argparse
import difflib
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sqlalchemy.orm import Session  # noqa: E402

from territorial.almacen.sesion import obtener_motor  # noqa: E402
from territorial.config import obtener_config  # noqa: E402
from territorial.informes.mediciones import CorteNoCoincide  # noqa: E402
from territorial.informes.resultados import Parametros, generar  # noqa: E402

#: Decisiones registradas en docs/decisiones-remediacion.md (2026-10-01).
CORTE_PRINCIPAL = "2026-09-30T04:59:59+00:00"
CORTE_EXTENDIDA = "2026-10-09T04:59:59+00:00"
EXPORTACION_PRINCIPAL = "C:/dev/respaldos/corte-ronda-2026-09-29"


def instante(texto: str) -> datetime:
    t = datetime.fromisoformat(texto)
    if t.tzinfo is None:
        raise argparse.ArgumentTypeError(f"{texto!r} no lleva zona horaria")
    return t


def main() -> int:
    ap = argparse.ArgumentParser(description="Regenera docs/informe_resultados.md")
    ap.add_argument("--commit", required=True,
                    help="commit del código que genera (va en el documento y en cada cifra)")
    ap.add_argument("--salida", default=str(RAIZ / "docs" / "informe_resultados.md"))
    ap.add_argument("--check", action="store_true",
                    help="no escribe: falla si lo generado difiere del archivo")
    ap.add_argument("--corte-principal", type=instante, default=instante(CORTE_PRINCIPAL))
    ap.add_argument("--corte-extendida", type=instante, default=instante(CORTE_EXTENDIDA))
    ap.add_argument("--a-fecha", type=instante, default=datetime.now(timezone.utc),
                    help="solo decide si la ronda extendida ya cerró; no se escribe")
    ap.add_argument("--exportacion-principal", default=EXPORTACION_PRINCIPAL)
    ap.add_argument("--tarifas", default=str(RAIZ / "config" / "tarifas.json"))
    args = ap.parse_args()

    cfg = obtener_config()
    parametros = Parametros(
        commit=args.commit,
        corte_principal=args.corte_principal,
        corte_extendida=args.corte_extendida,
        a_fecha=args.a_fecha,
        carpeta_principal=Path(args.exportacion_principal),
        ruta_snapshot=cfg.ruta_absoluta(cfg.ruta_snapshot),
        ruta_tarifas=Path(args.tarifas),
    )

    motor = obtener_motor()
    with motor.connect() as conn:
        if motor.dialect.name == "postgresql":
            conn = conn.execution_options(postgresql_readonly=True)
        with Session(bind=conn) as s:
            try:
                texto = generar(s, parametros)
            except CorteNoCoincide as e:
                print(f"NO SE GENERA: la ronda principal ya no es la del corte.\n  {e}")
                return 2
        conn.rollback()

    salida = Path(args.salida)
    if args.check:
        actual = salida.read_text(encoding="utf-8") if salida.exists() else ""
        if actual == texto:
            print(f"sin diferencias: {salida.name} es exactamente lo que el script produce")
            return 0
        diff = list(difflib.unified_diff(
            actual.splitlines(), texto.splitlines(), "commiteado", "generado", lineterm="", n=1))
        print(f"DIFIERE: {sum(1 for l in diff if l[:1] in '+-') - 2} líneas cambian")
        print("\n".join(diff[:60]))
        return 1

    # UTF-8 sin BOM y saltos LF, como el resto del repositorio.
    salida.write_text(texto, encoding="utf-8", newline="\n")
    print(f"escrito {salida} ({len(texto.splitlines())} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
