r"""Cuánto lleva calificado cada persona en la ronda. **Solo lectura.**

Sirve para acompañar la ronda 1 a 1: saber a quién falta antes del corte, sin
tener que abrir la base a mano ni preguntar.

**No escribe nada y no cierra nada.** La app no cierra el ciclo sola: el corte
es una exportación de `calificacion` a CSV al final del martes, y esa foto es la
que se analiza.

**Lo que cuenta es lo pedido.** El denominador son los `insights_pedidos` del
informe publicado —5 en cada uno de los 3 municipios calificables, 15 en
total—, no los 241 que el informe muestra. Es la misma regla que aplica la app
(F4.1): se califica solo lo pedido, para que H1 y H2 comparen sobre la misma
base.

**Dos columnas que no miden lo mismo, y conviene no confundirlas:**

· **Por persona** (`id_usuario`): quién tecleó. Es lo que sirve para acompañar
  la ronda y lo que permite aislar las calificaciones del operador del
  pipeline, que también califica.
· **Por gerencia** (`id_gerencia`): a quién se atribuye. Es el eje de H1 y H2, y
  el que tiene la restricción de unicidad: una calificación por gerencia y por
  insight. Si dos personas de una misma gerencia califican el mismo insight, la
  segunda **corrige** a la primera y por gerencia sigue contando una.

**Y el aviso que hay que llevar hasta el informe:** esta ronda se califica
**acompañada**, así que su tasa de respuesta no es comparable con el criterio de
H2 del PRD, que mide calificación sostenida sin acompañamiento. Ver
`docs/plan-siguientes-pasos.md`.

Uso:

    $py scripts\avance_calificacion.py                 # ciclo del informe publicado
    $py scripts\avance_calificacion.py --ciclo 3
    $py scripts\avance_calificacion.py --csv           # para pegar en otro sitio
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sqlalchemy import select  # noqa: E402

from territorial.almacen.modelos import Calificacion, Informe, Insight, Usuario  # noqa: E402
from territorial.almacen.sesion import sesion  # noqa: E402
from territorial.informes.gerencias import TIPO_PRD  # noqa: E402
from territorial.informes.gerencias import cargar as cargar_gerencias  # noqa: E402


@dataclass(frozen=True)
class FilaAvance:
    """Lo que lleva una persona. `de` es siempre el total pedido del informe."""

    correo: str
    nombre: str
    id_gerencia: str
    tipo_gerencia: str
    calificados: int
    de: int
    comentarios: int

    @property
    def porcentaje(self) -> float:
        return 100.0 * self.calificados / self.de if self.de else 0.0


def pedidos_del_payload(contenido: dict) -> list[int]:
    """Los `insights_pedidos` de los municipios calificables. En orden fijo."""
    return [
        i
        for m in contenido.get("municipios", [])
        if m.get("calificable")
        for i in m.get("insights_pedidos", [])
    ]


def avance(
    pedidos: list[int],
    usuarios: list[dict],
    calificaciones: list[dict],
) -> list[FilaAvance]:
    """Cuántos de los pedidos lleva cada persona. Función pura, para probarla.

    `usuarios` son los calificadores —rol `gerencia` y activos—; quien no
    califica no aparece, porque un 0 de 15 al lado de un administrador se lee
    como que va retrasado y no es cierto.

    **Solo cuentan las calificaciones sobre insights pedidos.** Si apareciera
    una sobre otro insight, no suma aquí; el alcance del servidor no debería
    permitirla, y que no cuadre es justamente la señal.
    """
    del_pedido = set(pedidos)
    total = len(del_pedido)
    filas = []
    for u in sorted(usuarios, key=lambda x: (x["id_gerencia"], x["correo"])):
        suyas = [
            c for c in calificaciones
            if c["id_usuario"] == u["id"] and c["id_insight"] in del_pedido
        ]
        filas.append(FilaAvance(
            correo=u["correo"],
            nombre=u["nombre"],
            id_gerencia=u["id_gerencia"],
            tipo_gerencia=u.get("tipo_gerencia", "?"),
            calificados=len(suyas),
            de=total,
            comentarios=sum(1 for c in suyas if (c.get("comentario") or "").strip()),
        ))
    return filas


def por_gerencia(
    pedidos: list[int], calificaciones: list[dict]
) -> dict[str, int]:
    """Cuántos pedidos tiene calificados cada gerencia. El eje de H1 y H2."""
    del_pedido = set(pedidos)
    conteo: dict[str, int] = {}
    for c in calificaciones:
        if c["id_insight"] in del_pedido:
            conteo[c["id_gerencia"]] = conteo.get(c["id_gerencia"], 0) + 1
    return conteo


def main() -> int:
    p = argparse.ArgumentParser(description="Avance de la ronda de calificación")
    p.add_argument("--ciclo", type=int, help="por defecto, el del informe publicado")
    p.add_argument("--csv", action="store_true", help="salida en CSV por persona")
    args = p.parse_args()

    catalogo = cargar_gerencias()

    with sesion() as s:
        consulta = select(Informe).where(Informe.estado == "publicado")
        if args.ciclo is not None:
            consulta = consulta.where(Informe.id_ciclo == args.ciclo)
        informes = list(s.scalars(consulta.order_by(Informe.id_ciclo.desc())))
        if not informes:
            print("no hay ningún informe publicado")
            return 1
        informe = informes[0]

        pedidos = pedidos_del_payload(informe.contenido)
        usuarios = [
            {"id": u.id, "correo": u.correo, "nombre": u.nombre,
             "id_gerencia": u.id_gerencia,
             "tipo_gerencia": (catalogo[u.id_gerencia].tipo
                               if u.id_gerencia in catalogo else "sin declarar")}
            for u in s.scalars(
                select(Usuario).where(Usuario.activo.is_(True),
                                      Usuario.rol == "gerencia")
            )
        ]
        calificaciones = [
            {"id_insight": c.id_insight, "id_gerencia": c.id_gerencia,
             "id_usuario": c.id_usuario, "comentario": c.comentario}
            for c in s.scalars(
                select(Calificacion)
                .join(Insight, Insight.id == Calificacion.id_insight)
                .where(Insight.id_corrida == informe.id_corrida_agentes)
            )
        ]

    filas = avance(pedidos, usuarios, calificaciones)
    conteo_gerencia = por_gerencia(pedidos, calificaciones)

    if args.csv:
        w = csv.writer(sys.stdout, lineterminator="\n")
        w.writerow(["correo", "nombre", "id_gerencia", "tipo", "calificados",
                    "de", "porcentaje", "comentarios"])
        for f in filas:
            w.writerow([f.correo, f.nombre, f.id_gerencia, f.tipo_gerencia,
                        f.calificados, f.de, f"{f.porcentaje:.0f}", f.comentarios])
        return 0

    print(f"Informe {informe.id} · ciclo {informe.id_ciclo} · "
          f"{len(pedidos)} insights pedidos\n")
    print(f"  {'persona':<28} {'gerencia':<26} {'tipo':<10} avance")
    for f in filas:
        barra = "#" * f.calificados + "·" * (f.de - f.calificados)
        com = f" · {f.comentarios} comentario(s)" if f.comentarios else ""
        print(f"  {f.correo:<28} {f.id_gerencia:<26} {f.tipo_gerencia:<10} "
              f"{f.calificados:>2}/{f.de}  {barra}{com}")

    # El eje que importa para H1 y H2 es la gerencia, no la persona.
    prd = sorted(g.id_gerencia for g in catalogo.values() if g.tipo == TIPO_PRD)
    print(f"\n  por gerencia (lo que cuenta para H1 y H2):")
    for g in sorted(conteo_gerencia) or []:
        marca = "prd" if g in prd else "adicional"
        print(f"    {g:<26} {conteo_gerencia[g]:>2}/{len(pedidos)}  [{marca}]")
    sin_empezar = [g for g in prd if g not in conteo_gerencia]
    if sin_empezar:
        print(f"    sin empezar: {sin_empezar}")

    completas = sum(1 for g in prd if conteo_gerencia.get(g, 0) == len(pedidos))
    print(f"\n  gerencias «prd» que terminaron: {completas} de {len(prd)}")
    print("\n  La ronda se califica ACOMPAÑADA: esta tasa no es comparable con el\n"
          "  criterio de H2 del PRD, que mide calificación sostenida sin\n"
          "  acompañamiento. Ver docs/plan-siguientes-pasos.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
