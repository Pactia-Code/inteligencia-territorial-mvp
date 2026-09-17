"""Pesos del score (CA-M5.3: configurables sin cambio de código).

Los valores que trae este módulo son los **provisionales** del Addendum 01 D4.
Los definitivos los decide Gerencia General y son el pendiente A1 del PRD, así
que están puestos para que M5 corra, no porque estén calibrados.

Un archivo JSON en `Config.ruta_pesos` los sustituye sin tocar código. Si no
existe, rigen estos. El archivo puede traer solo los ciclos o factores que
quiera cambiar: lo que no mencione conserva el valor por defecto.

Sobre el ciclo 1: no existen ciclos previos, así que F3 (aceleración, que
compara contra ciclos anteriores) y F6 (calificaciones previas) no aplican. D4
los deja fuera y reparte su peso entre los demás.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from territorial.config import Config, obtener_config

# Nombre canónico de cada factor. El orden es el de D4 y se conserva en el
# desglose de CA-M5.5, para que el informe siempre los liste igual.
FACTORES: tuple[str, ...] = ("F1", "F2", "F3", "F4", "F5", "F6")

DESCRIPCIONES: dict[str, str] = {
    "F1": "Intensidad de obra — proporción de contratos de obra sobre el total SECOP",
    "F2": "Ticket medio de obra — valor medio por contrato de obra",
    "F3": "Aceleración de obra — tasa diaria del ciclo contra la del mismo municipio antes",
    "F4": "Dinámica de licencias — variación interanual del área licenciada (ELIC)",
    "F5": "Densidad mediática — noticias por día cubierto",
    "F6": "Calificaciones previas — media 1-5 de las gerencias en ciclos anteriores",
}

# Addendum 01, D4. Un factor ausente en un ciclo es un factor que no aplica.
PESOS_POR_DEFECTO: dict[int, dict[str, float]] = {
    1: {"F1": 0.30, "F2": 0.15, "F4": 0.30, "F5": 0.25},
    2: {"F1": 0.22, "F2": 0.10, "F3": 0.20, "F4": 0.18, "F5": 0.10, "F6": 0.20},
    3: {"F1": 0.22, "F2": 0.10, "F3": 0.20, "F4": 0.18, "F5": 0.10, "F6": 0.20},
}


class PesosInvalidos(ValueError):
    """El archivo de pesos no cumple el contrato. Mejor fallar que puntuar mal."""


@dataclass(frozen=True)
class JuegoDePesos:
    """Los pesos de un ciclo, ya validados."""

    id_ciclo: int
    pesos: dict[str, float]
    origen: str  # "defecto" o la ruta del archivo. Va a la traza de CA-M8.2.

    def __str__(self) -> str:
        detalle = ", ".join(f"{k} {v:.0%}" for k, v in sorted(self.pesos.items()))
        return f"ciclo {self.id_ciclo} [{self.origen}]: {detalle}"


def _validar(id_ciclo: int, pesos: dict[str, float], origen: str) -> None:
    if not pesos:
        raise PesosInvalidos(f"ciclo {id_ciclo}: no tiene ningún factor con peso ({origen})")

    desconocidos = sorted(set(pesos) - set(FACTORES))
    if desconocidos:
        raise PesosInvalidos(
            f"ciclo {id_ciclo}: factores desconocidos {desconocidos} ({origen}). "
            f"Los válidos son {list(FACTORES)}"
        )

    negativos = sorted(k for k, v in pesos.items() if v < 0)
    if negativos:
        raise PesosInvalidos(f"ciclo {id_ciclo}: pesos negativos en {negativos} ({origen})")

    total = sum(pesos.values())
    if total <= 0:
        raise PesosInvalidos(f"ciclo {id_ciclo}: los pesos suman {total} ({origen})")

    # Se tolera una desviación mínima por redondeo al escribir el JSON a mano,
    # pero no un error de dedo: unos pesos que suman 0,7 cambiarían el score
    # entero sin que nadie lo notara en el informe.
    if abs(total - 1.0) > 0.001:
        raise PesosInvalidos(
            f"ciclo {id_ciclo}: los pesos suman {total:.4f}, deberían sumar 1,0 ({origen}). "
            "Si un factor no aplica en este ciclo, omítelo en vez de dejarlo en cero: "
            "su peso se redistribuye entre los demás."
        )


def cargar(config: Config | None = None) -> dict[int, JuegoDePesos]:
    """Pesos por ciclo, con el archivo de configuración aplicado si existe."""
    cfg = config or obtener_config()
    ruta = cfg.ruta_absoluta(cfg.ruta_pesos)

    crudos: dict[int, dict[str, float]] = {c: dict(p) for c, p in PESOS_POR_DEFECTO.items()}
    origen = "defecto (D4 provisional)"

    if ruta.exists():
        origen = str(ruta.name)
        try:
            contenido = json.loads(ruta.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise PesosInvalidos(f"{ruta} no es JSON válido: {e}") from e

        if not isinstance(contenido, dict):
            raise PesosInvalidos(f"{ruta}: se esperaba un objeto {{ciclo: {{factor: peso}}}}")

        for clave, pesos_ciclo in contenido.items():
            try:
                ciclo = int(clave)
            except (TypeError, ValueError) as e:
                raise PesosInvalidos(f"{ruta}: '{clave}' no es un número de ciclo") from e
            if not isinstance(pesos_ciclo, dict):
                raise PesosInvalidos(f"{ruta}, ciclo {ciclo}: se esperaba {{factor: peso}}")
            # Sustituye el ciclo entero, no factor a factor: mezclar los pesos
            # del archivo con los de defecto daría un juego que nadie escribió.
            crudos[ciclo] = {k: float(v) for k, v in pesos_ciclo.items()}

    for ciclo, pesos_ciclo in crudos.items():
        _validar(ciclo, pesos_ciclo, origen)

    return {c: JuegoDePesos(c, p, origen) for c, p in crudos.items()}


def del_ciclo(id_ciclo: int, config: Config | None = None) -> JuegoDePesos:
    juegos = cargar(config)
    if id_ciclo not in juegos:
        raise PesosInvalidos(
            f"no hay pesos definidos para el ciclo {id_ciclo}. "
            f"Definidos: {sorted(juegos)}"
        )
    return juegos[id_ciclo]


def escribir_plantilla(destino: Path) -> Path:
    """Vuelca los pesos vigentes a un JSON, para que alguien los edite.

    Es la vía prevista por CA-M5.3: se genera el archivo, Gerencia ajusta los
    números y el score cambia sin que nadie toque Python.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    cuerpo = {str(c): p for c, p in PESOS_POR_DEFECTO.items()}
    destino.write_text(json.dumps(cuerpo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return destino
