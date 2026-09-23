r"""Carga los usuarios autorizados desde `config/usuarios.csv`. Idempotente.

**La app nunca escribe en `usuario`** (M9-acceso): quien no esté en esta tabla
puede leer el informe entero y no puede calificar. Por eso la lista entra por
aquí y no por la pantalla.

Dos consecuencias de que sea así, y las dos importan para H2:

· **El denominador se conoce antes de medir.** El universo queda fijado de
  antemano en vez de descubrirse al final, que es la forma habitual de que una
  tasa de respuesta acabe siendo indiscutible y a la vez incomparable.
· **Las escrituras de la app no incluyen `usuario`**, así que nadie se da de
  alta a sí mismo a mitad de la ventana.

**El archivo se versiona en git** (decisión del dueño del 2026-09-22: no
contiene datos sensibles). Antes se pedía por `--csv` o `RUTA_USUARIOS` porque
iba a vivir fuera; hoy el valor por defecto es `config/usuarios.csv` y las dos
formas de apuntarlo a otro sitio siguen funcionando.

Formato: **UTF-8, separador punto y coma**, columnas

    nombre;id_gerencia;cargo;correo;puede_calificar;es_administrador

· `puede_calificar=si` → rol `gerencia`. `es_administrador=si` → rol
  `administrador`. **Las dos en `si` es un error** y no se carga nada: son roles
  distintos y elegir uno por la persona sería inventar la decisión. El dueño
  tiene dos filas, una por rol, precisamente por esto.
· **Las dos en `no` no se puede cargar todavía**: sería un usuario de solo
  lectura y ese rol **no existe** (`ck_rol` admite `gerencia` y
  `administrador`). Leer no requiere estar en `usuario`, así que esa fila
  probablemente sobra; si se quiere dejar constancia igualmente, hay que
  ampliar `ck_rol` con una migración. Está registrado en
  `docs/decisiones-remediacion.md`.
· `id_gerencia` **debe existir en `config/gerencias.json`**. Una gerencia no
  declarada saldría marcada `adicional` en el payload sin que nadie lo hubiera
  decidido, y H2 se reportaría sobre otro conjunto.
· `correo` único; `cargo` puede ir vacío.

**Previsualiza por defecto y no escribe nada.** Hay que pedirlo con
`--confirmar`. Y **si una fila falla, no se escribe ninguna**: una carga a
medias deja el denominador de H2 en un estado que nadie decidió.

Los usuarios que estén en la base y **no** en el archivo **se desactivan, no se
borran**: una calificación ya emitida cuelga de su gerencia, y borrar la fila no
la borra pero sí deja huérfano el denominador.

Uso:

    $py scripts\cargar_usuarios.py                      # previsualiza
    $py scripts\cargar_usuarios.py --confirmar          # escribe
    $py scripts\cargar_usuarios.py --csv otro.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sqlalchemy import select  # noqa: E402

from territorial.almacen.modelos import Usuario  # noqa: E402
from territorial.almacen.sesion import aplicar_migraciones, sesion  # noqa: E402
from territorial.informes.gerencias import Gerencia  # noqa: E402
from territorial.informes.gerencias import cargar as cargar_gerencias  # noqa: E402

COLUMNAS = ("nombre", "id_gerencia", "cargo", "correo", "puede_calificar", "es_administrador")
CSV_POR_DEFECTO = Path("config/usuarios.csv")
# Lo que cuenta como sí y como no. Se admite `sí` con tilde porque el archivo lo
# escribe una persona y la tilde es lo natural en castellano.
SI = {"si", "sí", "s", "true", "1", "x"}
NO = {"no", "n", "false", "0", ""}

# Campos que se comparan y actualizan sobre una fila existente. `activo` va
# aparte porque lo decide la presencia en el archivo, no una columna.
CAMPOS = ("nombre", "id_gerencia", "cargo", "rol")


class UsuariosInvalidos(ValueError):
    """El archivo no cumple el contrato. Mejor no cargar que cargar a medias."""


@dataclass
class Plan:
    """Lo que la carga haría. Se imprime igual se confirme o no."""

    altas: list[dict] = field(default_factory=list)
    cambios: list[tuple[Usuario, dict[str, tuple]]] = field(default_factory=list)
    reactivaciones: list[Usuario] = field(default_factory=list)
    desactivaciones: list[Usuario] = field(default_factory=list)
    iguales: int = 0

    @property
    def hay_cambios(self) -> bool:
        return bool(
            self.altas or self.cambios or self.reactivaciones or self.desactivaciones
        )


def _booleano(valor: str, columna: str, donde: str) -> bool:
    limpio = (valor or "").strip().lower()
    if limpio in SI:
        return True
    if limpio in NO:
        return False
    raise UsuariosInvalidos(
        f"{donde}: «{columna}» vale «{valor}» y se esperaba si o no"
    )


def _rol(puede_calificar: bool, es_administrador: bool, donde: str) -> str:
    if puede_calificar and es_administrador:
        raise UsuariosInvalidos(
            f"{donde}: «puede_calificar» y «es_administrador» no pueden ser los dos "
            "«si». Son roles distintos y el sistema no elige por la persona: pon dos "
            "filas con correos distintos, una por rol."
        )
    if es_administrador:
        return "administrador"
    if puede_calificar:
        return "gerencia"
    raise UsuariosInvalidos(
        f"{donde}: con «puede_calificar» y «es_administrador» en «no» sería un usuario "
        "de solo lectura, y ese rol **no existe** (la base admite «gerencia» y "
        "«administrador»). Leer el informe no requiere estar en esta tabla, así que "
        "la fila probablemente sobra; si se quiere dejar constancia, hay que decidir "
        "crear el rol y ampliar `ck_rol` con una migración."
    )


def leer(ruta: Path, catalogo: dict[str, Gerencia]) -> list[dict]:
    """Las filas del CSV, validadas. Levanta a la primera que no cumpla."""
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        filas = list(csv.DictReader(f, delimiter=";"))
    if not filas:
        raise UsuariosInvalidos(f"{ruta}: el CSV no tiene filas")

    faltan = [c for c in COLUMNAS if c not in filas[0]]
    if faltan:
        raise UsuariosInvalidos(
            f"{ruta}: faltan columnas {faltan}. Se esperaba «{';'.join(COLUMNAS)}» "
            "separado por punto y coma"
        )

    limpias: list[dict] = []
    vistos: dict[str, int] = {}
    for n, f in enumerate(filas, start=2):
        donde = f"{ruta.name} línea {n}"
        correo = (f["correo"] or "").strip().lower()
        if "@" not in correo:
            raise UsuariosInvalidos(f"{donde}: «{correo}» no parece un correo")
        if correo in vistos:
            raise UsuariosInvalidos(
                f"{donde}: el correo «{correo}» ya está en la línea {vistos[correo]}"
            )
        vistos[correo] = n

        nombre = (f["nombre"] or "").strip()
        if not nombre:
            raise UsuariosInvalidos(f"{donde}: falta el nombre")

        id_gerencia = (f["id_gerencia"] or "").strip()
        if id_gerencia not in catalogo:
            raise UsuariosInvalidos(
                f"{donde}: la gerencia «{id_gerencia}» no está declarada en "
                f"config/gerencias.json. Declaradas: {sorted(catalogo)}"
            )

        rol = _rol(
            _booleano(f["puede_calificar"], "puede_calificar", donde),
            _booleano(f["es_administrador"], "es_administrador", donde),
            donde,
        )
        limpias.append({
            "nombre": nombre,
            "id_gerencia": id_gerencia,
            "cargo": (f["cargo"] or "").strip() or None,
            "correo": correo,
            "rol": rol,
        })
    return limpias


def planificar(existentes: list[Usuario], filas: list[dict]) -> Plan:
    """Compara el archivo con la base. No escribe nada."""
    por_correo = {u.correo.lower(): u for u in existentes}
    plan = Plan()
    for f in filas:
        actual = por_correo.pop(f["correo"], None)
        if actual is None:
            plan.altas.append(f)
            continue
        cambios = {
            c: (getattr(actual, c), f[c]) for c in CAMPOS if getattr(actual, c) != f[c]
        }
        if cambios:
            plan.cambios.append((actual, cambios))
        if not actual.activo:
            plan.reactivaciones.append(actual)
        elif not cambios:
            plan.iguales += 1
    plan.desactivaciones = [u for u in por_correo.values() if u.activo]
    return plan


def aplicar(sesion_bd, plan: Plan, filas: list[dict]) -> None:
    """Escribe el plan. Una sola transacción: o entra todo o no entra nada."""
    for f in plan.altas:
        sesion_bd.add(Usuario(**f, activo=True))
    for usuario, cambios in plan.cambios:
        for campo, (_, nuevo) in cambios.items():
            setattr(usuario, campo, nuevo)
    for usuario in plan.reactivaciones:
        usuario.activo = True
    for usuario in plan.desactivaciones:
        usuario.activo = False


def imprimir(plan: Plan, filas: list[dict], catalogo: dict[str, Gerencia]) -> None:
    def etiqueta(id_gerencia: str) -> str:
        g = catalogo.get(id_gerencia)
        return f"{id_gerencia} [{g.tipo}]" if g else f"{id_gerencia} [sin declarar]"

    print(f"\nEl archivo trae {len(filas)} usuarios:")
    for f in filas:
        cargo = f" · {f['cargo']}" if f["cargo"] else ""
        print(f"  {f['correo']:<28} {f['rol']:<14} {etiqueta(f['id_gerencia'])}{cargo}")

    print("\nQué haría la carga:")
    for f in plan.altas:
        print(f"  ALTA          {f['correo']:<28} {f['rol']} · {f['id_gerencia']}")
    for usuario, cambios in plan.cambios:
        detalle = ", ".join(
            f"{c}: «{viejo}» → «{nuevo}»" for c, (viejo, nuevo) in sorted(cambios.items())
        )
        print(f"  CAMBIO        {usuario.correo:<28} {detalle}")
    for usuario in plan.reactivaciones:
        print(f"  REACTIVA      {usuario.correo:<28} estaba inactivo")
    for usuario in plan.desactivaciones:
        print(f"  DESACTIVA     {usuario.correo:<28} no está en el archivo (no se borra)")
    if plan.iguales:
        print(f"  sin cambios   {plan.iguales}")
    if not plan.hay_cambios:
        print("  nada que hacer")

    # Las gerencias declaradas que se quedarían sin nadie que califique. No es
    # un error aquí —lo será al publicar, F0.6— pero verlo ahora evita
    # descubrirlo con el informe delante.
    con_calificador = {f["id_gerencia"] for f in filas if f["rol"] == "gerencia"}
    huerfanas = [
        g.id_gerencia for g in catalogo.values()
        if g.tipo == "prd" and g.id_gerencia not in con_calificador
    ]
    if huerfanas:
        print(f"\nAVISO: gerencias «prd» sin ningún calificador: {sorted(huerfanas)}")


def main() -> int:
    p = argparse.ArgumentParser(description="Carga los usuarios autorizados")
    p.add_argument("--csv", default=os.environ.get("RUTA_USUARIOS"),
                   help=f"ruta del CSV; por defecto {CSV_POR_DEFECTO}")
    p.add_argument("--confirmar", action="store_true",
                   help="escribe los cambios; sin esto solo previsualiza")
    p.add_argument("--previsualizar", action="store_true",
                   help="explícito, aunque ya es lo que pasa por defecto")
    args = p.parse_args()

    ruta = Path(args.csv) if args.csv else CSV_POR_DEFECTO
    if not ruta.is_absolute():
        ruta = RAIZ / ruta
    if not ruta.exists():
        print(f"ERROR: no existe {ruta}")
        return 1

    try:
        catalogo = cargar_gerencias()
        filas = leer(ruta, catalogo)
    except ValueError as e:
        print(f"ERROR: {e}")
        print("\nNo se escribió nada.")
        return 1

    if args.confirmar:
        aplicar_migraciones()

    with sesion() as s:
        existentes = list(s.scalars(select(Usuario)).all())
        plan = planificar(existentes, filas)
        imprimir(plan, filas, catalogo)

        if not args.confirmar:
            print("\n[PREVISUALIZACIÓN] no se escribió nada. Añade --confirmar.")
            # `sesion()` confirma al salir y aquí no hay nada sucio, pero el
            # rollback deja la intención escrita: por este camino no se escribe.
            s.rollback()
            return 0

        aplicar(s, plan, filas)

    print(
        f"\nEscrito: {len(plan.altas)} altas · {len(plan.cambios)} cambios · "
        f"{len(plan.reactivaciones)} reactivados · {len(plan.desactivaciones)} "
        f"desactivados · {plan.iguales} sin cambios"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
