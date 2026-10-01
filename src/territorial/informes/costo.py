"""La proyección de costo de H5. F0b.1, con la decisión P-5 del dueño.

Vivía en `scripts/estimar_costo.py`. Se trae aquí para que el informe de
resultados y el script calculen **con la misma fórmula y las mismas
constantes**: la auditoría encontró que las cifras de H5 publicadas no
coincidían con lo que el script daba (H-035), y dos copias de la fórmula
volverían a separarse.

**Lo que esta proyección arrastra, y hay que decirlo junto a la cifra:**

- `SENALES_POR_QUINCENA_18 = 615` **no tiene productor** en el repositorio. La
  regla que lo justifica —tasa diaria × 14— da otra cosa sobre el snapshot, y
  el informe lo enseña. Es una afirmación sin medición que entra en el cálculo.
- `ENTRADA_POR_SENAL` y `SALIDA_POR_SENAL` se midieron el 2026-09-17 sobre
  Barranquilla en el ciclo 2. La base da otros valores según la corrida.
- El Correlacionador se promedia sobre **todas** las trazas, no sobre una
  corrida: la traza no lleva `id_corrida` (H-006). Lo arregla F0b.2.
- **No incluye el Sintetizador**, que no existe.

La tarifa del Clasificador está sin verificar (P-5), así que el total se publica
como condicional: **correlacionador + clasificador × k**, con k = 1 hasta que
haya tarifa real.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Medido sobre el snapshot el 2026-09-17: Barranquilla ciclo 2, 284 señales en
# 6 lotes, 68.058 tokens de entrada y 25.986 de salida.
ENTRADA_POR_SENAL = 240
SALIDA_POR_SENAL = 92
SENALES_CARGA_INICIAL = 7_628
#: Sin productor en el repositorio (auditoría 8b.1). Ver la cabecera.
SENALES_POR_QUINCENA_18 = 615
MUNICIPIOS_MVP = 18
MUNICIPIOS_NACIONAL = 1_103
QUINCENAS_POR_ANIO = 26


def leer_tarifas(ruta: Path) -> dict[str, tuple[float, float]]:
    """{despliegue: (entrada, salida)} en USD por millón de tokens."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return {
        k: (float(v["entrada"]), float(v["salida"]))
        for k, v in datos.items()
        if not k.startswith("_") and isinstance(v, dict)
    }


@dataclass(frozen=True)
class Proyeccion:
    """Costo en USD, separado por agente para poder aplicar k al Clasificador."""

    correlacionador: float
    clasificador: float

    def total(self, k: float = 1.0) -> float:
        return self.correlacionador + self.clasificador * k

    def parte_correlacionador(self, k: float = 1.0) -> float:
        return self.correlacionador / self.total(k)


def proyectar(
    senales: float,
    municipios: float,
    tokens_correlacionador: tuple[int, int],
    llamadas_correlacionador: int,
    tarifa_clasificador: tuple[float, float],
    tarifa_correlacionador: tuple[float, float],
) -> Proyeccion:
    """La fórmula de `estimar_costo.py`, sin cambios.

    El Clasificador escala por **señal**, con la tasa medida; el
    Correlacionador por **municipio**, con el promedio de sus trazas.
    """
    ent_muni = tokens_correlacionador[0] / llamadas_correlacionador
    sal_muni = tokens_correlacionador[1] / llamadas_correlacionador
    t_ec, t_sc = tarifa_clasificador
    t_er, t_sr = tarifa_correlacionador
    return Proyeccion(
        correlacionador=municipios * (ent_muni * t_er + sal_muni * t_sr) / 1e6,
        clasificador=senales * (ENTRADA_POR_SENAL * t_ec + SALIDA_POR_SENAL * t_sc) / 1e6,
    )


def escenario_anual_nacional() -> tuple[float, float]:
    """(señales, corridas de municipio) de un año a escala nacional."""
    por_muni = SENALES_POR_QUINCENA_18 / MUNICIPIOS_MVP
    return (por_muni * MUNICIPIOS_NACIONAL * QUINCENAS_POR_ANIO,
            MUNICIPIOS_NACIONAL * QUINCENAS_POR_ANIO)


def escenario_anual_piloto() -> tuple[float, float]:
    """(señales, corridas de municipio) de un año con los 18 municipios."""
    return (SENALES_POR_QUINCENA_18 * QUINCENAS_POR_ANIO,
            MUNICIPIOS_MVP * QUINCENAS_POR_ANIO)
