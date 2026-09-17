"""F1–F6 del score (Addendum 01, D4).

Todos los factores son **independientes del tamaño del municipio** por
construcción: proporciones, promedios y tasas, nunca sumas. Esa es la propiedad
que permitió dejar TerriData fuera del MVP, y romperla invalidaría el ranking
entero, no solo un factor.

  F1  Intensidad de obra      n_obra / n_secop                      proporción
  F2  Ticket medio de obra    valor_obra / n_obra                   promedio
  F3  Aceleración de obra     tasa diaria del ciclo / tasa previa   razón
  F4  Dinámica de licencias   variación % del área ELIC             porcentaje
  F5  Densidad mediática      n_noticias / días cubiertos           tasa
  F6  Calificaciones previas  media 1-5 ponderada por gerencia      media


Sobre la escala común — decisión no cubierta por D4
---------------------------------------------------
D4 fija cómo se calcula cada factor y cuánto pesa, pero no en qué escala se
suman. Y sin eso los pesos no significan nada: F1 vive en [0, 1], F4 va de -65%
a +900% y F2 son millones de pesos. Ponderar esos números tal cual daría un
score donde F2 lo decide todo y el 30% de F1 es decorativo.

Aquí se normaliza **min-max dentro de la cohorte del ciclo**: por cada factor,
el municipio más bajo de ese ciclo queda en 0 y el más alto en 1. Se eligió por
tres razones:

  1. No inventa constantes de escala. Cualquier divisor fijo («F2 entre mil
     millones») sería un peso encubierto que nadie decidió.
  2. El entregable es un ranking dentro de un ciclo (CA-M5.4, top 3 fijo), y
     min-max preserva el orden de cada factor exactamente.
  3. Se explica en una frase en el informe, que es lo que pide CA-M5.5.

Lo que cuesta: **los scores no son comparables entre ciclos**, solo dentro de
uno. Un 0,8 en el ciclo 1 y un 0,8 en el ciclo 3 no significan lo mismo. Para
el top 3 por ciclo da igual; si algún día se quiere una serie temporal del
score, esto hay que rehacerlo. Queda anotado como decisión de implementación
pendiente de confirmar con Analítica, junto al pendiente A1 de los pesos.

F4 se winsoriza a p10–p90 **antes** de normalizar, como manda D4: sin eso,
Ibagué (+899,66%) fijaría el máximo de la cohorte y aplastaría a los demás
municipios contra el cero.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from territorial.reglas.cobertura import Cobertura

# D4: por debajo de esta área, la variación interanual de ELIC es ruido. Una
# sola licencia mueve el indicador cientos de puntos.
PISO_AREA_ELIC_M2 = 10_000.0

# D4: winsorizado de F4.
PERCENTIL_INFERIOR = 0.10
PERCENTIL_SUPERIOR = 0.90

# Factores que dependen de SECOP. Son los que se marcan `sin_cobertura` cuando
# el municipio no llega al umbral de días (D4).
FACTORES_SECOP: frozenset[str] = frozenset({"F1", "F2", "F3"})


@dataclass(frozen=True)
class EntradaMunicipio:
    """Lo que hace falta para puntuar un municipio en un ciclo.

    Es una vista plana a propósito, igual que `Senal` en el validador: el
    cálculo del score no debe conocer el ORM.
    """

    divipola: str
    id_ciclo: int
    cobertura: Cobertura

    # SECOP del ciclo
    n_secop: int = 0
    n_obra: int = 0
    valor_obra: float = 0.0

    # SECOP de ciclos anteriores, para F3
    n_obra_previa: int = 0
    dias_cubiertos_previos: int = 0

    # Noticias del ciclo (RSS). Bing queda fuera: D1 lo excluye como evidencia
    # y como insumo de puntuación.
    n_noticias: int = 0

    # ELIC del municipio. Es constante en los 3 ciclos (D2/R3).
    variacion_elic_pct: float | None = None
    area_elic_m2: float | None = None

    # (gerencia, valor 1-5) de ciclos anteriores, para F6
    calificaciones_previas: list[tuple[str, float]] = field(default_factory=list)


@dataclass(frozen=True)
class ValorFactor:
    """Un factor de un municipio: lo crudo, lo normalizado y por qué."""

    codigo: str
    crudo: float | None
    normalizado: float | None = None
    disponible: bool = True
    motivo: str = ""

    @property
    def sin_cobertura(self) -> bool:
        return not self.disponible


def _no_disponible(codigo: str, motivo: str) -> ValorFactor:
    return ValorFactor(codigo=codigo, crudo=None, disponible=False, motivo=motivo)


# --------------------------------------------------------------------------
# Factores crudos, uno a uno
# --------------------------------------------------------------------------


def f1_intensidad_obra(e: EntradaMunicipio) -> ValorFactor:
    """Proporción de contratos de obra sobre el total SECOP del ciclo."""
    if e.n_secop <= 0:
        return _no_disponible("F1", "sin registros SECOP en el ciclo")
    return ValorFactor("F1", e.n_obra / e.n_secop)


def f2_ticket_medio(e: EntradaMunicipio) -> ValorFactor:
    """Valor medio por contrato de obra.

    Promedio, no suma: un municipio con tres contratos grandes puntúa igual que
    uno con treinta del mismo tamaño, que es justo lo que D4 busca.
    """
    if e.n_obra <= 0:
        return _no_disponible("F2", "sin contratos de obra en el ciclo")
    return ValorFactor("F2", e.valor_obra / e.n_obra)


def f3_aceleracion(e: EntradaMunicipio) -> ValorFactor:
    """Tasa diaria de obra del ciclo contra la del mismo municipio antes.

    Comparación intra-municipal: no mide cuánta obra hay, sino si el ritmo
    subió. Por eso el ciclo 1 no lo tiene — no hay contra qué comparar.
    """
    if e.id_ciclo <= 1:
        return _no_disponible("F3", "ciclo 1: no hay ciclos previos")
    if e.dias_cubiertos_previos <= 0:
        return _no_disponible("F3", "sin cobertura en ciclos previos")
    if e.cobertura.dias_cubiertos <= 0:
        return _no_disponible("F3", "sin cobertura en el ciclo")

    tasa_previa = e.n_obra_previa / e.dias_cubiertos_previos
    tasa_actual = e.n_obra / e.cobertura.dias_cubiertos

    if tasa_previa <= 0:
        # Arrancar de cero es aceleración infinita, que no es un número útil.
        # Se marca no disponible en vez de inventar un tope: el municipio se
        # puntúa con los factores restantes y su peso se redistribuye.
        if tasa_actual <= 0:
            return _no_disponible("F3", "sin obra antes ni ahora")
        return _no_disponible("F3", "sin obra en ciclos previos: la razón no está definida")

    return ValorFactor("F3", tasa_actual / tasa_previa)


def f4_dinamica_licencias(e: EntradaMunicipio) -> ValorFactor:
    """Variación interanual del área licenciada, con piso de área.

    El piso de 10.000 m² es de D4 y no es cosmético: Chigorodó marca +430,63%
    sobre 5.768 m² y Carepa +273,15% sobre 4.239 m². Sin el piso, tres
    municipios pequeños coparían el top 3 por el ruido de una sola licencia.
    """
    if e.variacion_elic_pct is None:
        return _no_disponible("F4", "sin datos ELIC")
    if e.area_elic_m2 is None:
        return _no_disponible("F4", "ELIC sin área de referencia")
    if e.area_elic_m2 < PISO_AREA_ELIC_M2:
        return _no_disponible(
            "F4", f"área ELIC {e.area_elic_m2:,.0f} m² bajo el piso de {PISO_AREA_ELIC_M2:,.0f}"
        )
    return ValorFactor("F4", e.variacion_elic_pct)


def f5_densidad_mediatica(e: EntradaMunicipio) -> ValorFactor:
    """Noticias por día cubierto. Tasa, no conteo."""
    dias = e.cobertura.dias_cubiertos
    if dias <= 0:
        return _no_disponible("F5", "sin días cubiertos en el ciclo")
    return ValorFactor("F5", e.n_noticias / dias)


def f6_calificaciones_previas(e: EntradaMunicipio) -> ValorFactor:
    """Media de las calificaciones 1-5 de ciclos anteriores.

    «Ponderada por gerencia» (D4) se implementa como media de las medias por
    gerencia: una gerencia que califica veinte insights no pesa más que otra
    que califica dos. Sin esto, la gerencia más participativa decidiría el
    ranking, que es lo contrario de lo que H2 quiere medir.
    """
    if e.id_ciclo <= 1:
        return _no_disponible("F6", "ciclo 1: no hay calificaciones previas")
    if not e.calificaciones_previas:
        return _no_disponible("F6", "sin calificaciones en ciclos previos")

    por_gerencia: dict[str, list[float]] = {}
    for gerencia, valor in e.calificaciones_previas:
        por_gerencia.setdefault(gerencia, []).append(valor)

    medias = [sum(v) / len(v) for v in por_gerencia.values()]
    return ValorFactor("F6", sum(medias) / len(medias))


CALCULOS = {
    "F1": f1_intensidad_obra,
    "F2": f2_ticket_medio,
    "F3": f3_aceleracion,
    "F4": f4_dinamica_licencias,
    "F5": f5_densidad_mediatica,
    "F6": f6_calificaciones_previas,
}


def crudos(e: EntradaMunicipio, umbral_cobertura: float) -> dict[str, ValorFactor]:
    """Los seis factores de un municipio, sin normalizar todavía.

    Si el municipio no llega al umbral de cobertura, F1, F2 y F3 se marcan
    `sin_cobertura` aunque hubieran podido calcularse: D4 exige no puntuar con
    datos truncados, y R7 dice que el truncamiento afecta justo a las seis
    ciudades de mayor volumen. Ausencia de dato no es ausencia de actividad.
    """
    resultado = {codigo: calculo(e) for codigo, calculo in CALCULOS.items()}

    if e.cobertura.sin_cobertura(umbral_cobertura):
        pct = e.cobertura.fraccion * 100
        motivo = (
            f"cobertura {pct:.0f}% bajo el umbral de {umbral_cobertura:.0%} "
            f"({e.cobertura.dias_cubiertos}/{e.cobertura.dias_ventana} días)"
        )
        for codigo in FACTORES_SECOP:
            resultado[codigo] = _no_disponible(codigo, motivo)

    return resultado


# --------------------------------------------------------------------------
# Normalización a escala común, dentro de la cohorte del ciclo
# --------------------------------------------------------------------------


def _percentil(ordenados: list[float], q: float) -> float:
    """Percentil por interpolación lineal. Igual criterio que numpy por defecto."""
    if not ordenados:
        raise ValueError("no hay valores")
    if len(ordenados) == 1:
        return ordenados[0]
    pos = q * (len(ordenados) - 1)
    bajo = int(pos)
    alto = min(bajo + 1, len(ordenados) - 1)
    peso = pos - bajo
    return ordenados[bajo] * (1 - peso) + ordenados[alto] * peso


def winsorizar(valores: list[float], inferior: float, superior: float) -> list[float]:
    """Recorta los extremos a los percentiles dados, sin descartar municipios.

    D4 lo pide para F4. Recortar y no eliminar importa: el municipio extremo
    sigue en el ranking, simplemente deja de fijar la escala de los demás.
    """
    if not valores:
        return []
    ordenados = sorted(valores)
    p_bajo = _percentil(ordenados, inferior)
    p_alto = _percentil(ordenados, superior)
    return [min(max(v, p_bajo), p_alto) for v in valores]


def normalizar_cohorte(
    por_municipio: dict[str, dict[str, ValorFactor]],
) -> dict[str, dict[str, ValorFactor]]:
    """Lleva cada factor a [0, 1] comparando dentro del ciclo.

    Solo entran los municipios que tienen el factor disponible: incluir a los
    que no lo tienen como cero sería puntuarlos, y D4 lo prohíbe expresamente.

    Si todos los municipios empatan en un factor, ese factor queda en 0,5 para
    todos. No en 0 ni en 1: no hay información para distinguirlos, y cualquiera
    de los extremos sería una afirmación que los datos no sostienen.
    """
    salida: dict[str, dict[str, ValorFactor]] = {d: {} for d in por_municipio}

    codigos = {c for factores in por_municipio.values() for c in factores}

    for codigo in sorted(codigos):
        presentes = {
            divipola: factores[codigo]
            for divipola, factores in por_municipio.items()
            if codigo in factores and factores[codigo].disponible
        }

        for divipola, factores in por_municipio.items():
            if codigo in factores and not factores[codigo].disponible:
                salida[divipola][codigo] = factores[codigo]

        if not presentes:
            continue

        valores = [f.crudo for f in presentes.values()]
        if codigo == "F4":
            valores = winsorizar(valores, PERCENTIL_INFERIOR, PERCENTIL_SUPERIOR)

        minimo, maximo = min(valores), max(valores)
        rango = maximo - minimo

        for (divipola, factor), valor in zip(presentes.items(), valores, strict=True):
            normalizado = 0.5 if rango == 0 else (valor - minimo) / rango
            salida[divipola][codigo] = ValorFactor(
                codigo=codigo,
                crudo=factor.crudo,
                normalizado=normalizado,
                disponible=True,
                motivo=factor.motivo,
            )

    return salida
