"""Cobertura real por municipio y ciclo (Addendum 01, D4 y R7).

Es la pieza que neutraliza el truncamiento de la extracción SECOP.

Seis municipios del snapshot — los seis de mayor volumen — tienen fecha máxima
muy anterior al cierre: Barranquilla corta en 2025-11-21, Cartagena en
2025-12-29, Armenia, Pereira e Ibagué en enero de 2026. Sin este cálculo,
cinco capitales saldrían con score cercano a cero en el ciclo 3 por ausencia
de datos, y el informe lo presentaría como ausencia de actividad: un sesgo
sistemático contra las ciudades grandes, invisible en el resultado.

Regla: todo factor SECOP se calcula sobre **días de cobertura real del
municipio dentro del ciclo**, no sobre la duración nominal de la ventana. Por
debajo del umbral, los factores se marcan `sin_cobertura` y su peso se
redistribuye entre los demás. Nunca se puntúa cero.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Cobertura:
    divipola: str
    id_ciclo: int
    dias_ventana: int
    dias_cubiertos: int
    primera_fecha: date | None
    ultima_fecha: date | None

    @property
    def fraccion(self) -> float:
        if self.dias_ventana <= 0:
            return 0.0
        return self.dias_cubiertos / self.dias_ventana

    def sin_cobertura(self, umbral: float) -> bool:
        return self.fraccion < umbral

    def __str__(self) -> str:
        pct = self.fraccion * 100
        return (
            f"{self.divipola} c{self.id_ciclo}: "
            f"{self.dias_cubiertos}/{self.dias_ventana} dias ({pct:.0f}%)"
        )


def calcular(
    divipola: str,
    id_ciclo: int,
    desde: date,
    hasta: date,
    fechas: list[date],
) -> Cobertura:
    """Cobertura de un municipio en un ciclo.

    `desde` es inclusivo y `hasta` exclusivo, igual que las ventanas de D2.
    `fechas` son las fechas de las señales fechadas de ese municipio.

    Los días cubiertos van del inicio de la ventana hasta la última fecha
    observada: lo que falta al final es exactamente lo que el truncamiento se
    llevó. Un hueco intermedio no resta, porque un municipio puede
    legítimamente no contratar durante unas semanas.
    """
    dias_ventana = max((hasta - desde).days, 0)

    en_ventana = sorted(f for f in fechas if f and desde <= f < hasta)
    if not en_ventana:
        return Cobertura(divipola, id_ciclo, dias_ventana, 0, None, None)

    primera, ultima = en_ventana[0], en_ventana[-1]
    dias_cubiertos = min((ultima - desde).days + 1, dias_ventana)

    return Cobertura(divipola, id_ciclo, dias_ventana, dias_cubiertos, primera, ultima)


def redistribuir_pesos(
    pesos: dict[str, float], factores_sin_cobertura: set[str]
) -> dict[str, float]:
    """Reparte el peso de los factores sin cobertura entre los que sí la tienen.

    Mantiene la suma original, así que los scores siguen siendo comparables
    entre municipios aunque unos tengan menos factores disponibles.
    """
    disponibles = {k: v for k, v in pesos.items() if k not in factores_sin_cobertura}
    if not disponibles:
        raise ValueError("ningun factor con cobertura: el municipio no es puntuable")

    total = sum(pesos.values())
    suma_disponible = sum(disponibles.values())
    if suma_disponible <= 0:
        raise ValueError("los factores con cobertura suman peso cero")

    escala = total / suma_disponible
    return {k: v * escala for k, v in disponibles.items()}
