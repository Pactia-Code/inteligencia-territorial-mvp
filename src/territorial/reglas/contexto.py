"""De `contexto_municipal` a bandas para el Correlacionador. Capa determinista.

**Al prompt no llega ni una cifra.** Llega «déficit cuantitativo: alto». Una
cifra real escrita por el modelo sigue siendo una cifra escrita por el modelo, y
CA-M6.3 lo prohíbe; el adjetivo, en cambio, lo calcula este módulo, así que es
auditable y reproducible. Los números van al informe, compuestos por código
desde la tabla y con su año a la vista.

Y es lo que CA-M4.2 necesita: «una señal de obra en un municipio con déficit
habitacional **alto** implica tipología residencial» es una afirmación sobre el
adjetivo, no sobre el número.


Contra qué se compara, y por qué no contra los 18
--------------------------------------------------
Las bandas son **nacionales, sobre los 1.102 municipios**. Bandear contra la
cohorte del MVP repetiría el defecto que el scoring ya tiene documentado: la
normalización min-max por cohorte no es comparable entre corridas. Un adjetivo
que cambia según quién más corrió es tan poco comparable como un score que
cambia según quién más corrió.


Dos indicadores no se bandean por cuartil, y es una corrección medida
---------------------------------------------------------------------
Con cuartiles nacionales, **población y valor agregado salen «alto» para los 18
municipios del MVP**. No es un fallo del criterio: la distribución municipal
colombiana está muy sesgada —la mediana son 14.353 habitantes y el menor de los
18 es Carepa con 51.298— así que los 18 viven todos por encima del percentil 86.
Un adjetivo constante no informa de nada y cuesta tokens en el agente que ya es
el 89% del gasto.

Se corrige sin tocar el principio —los cortes siguen siendo fijos y ajenos a la
cohorte—, cambiando **qué** se mide:

· **Población** → clases de tamaño de corte fijo, no cuantiles. Reparte los 18
  en metropolitano / grande / intermedio, que es la distinción que hacía falta:
  un municipio de 51.000 no es uno de 1.275.000.
· **Valor agregado** → **per cápita**, no total. Un total es un proxy del
  tamaño, y los factores del score son todos independientes del tamaño por
  construcción (ver `scoring/factores.py`); no tendría sentido romper aquí esa
  propiedad. Per cápita reparte los 18 en tres bandas.

Lo mismo con el avalúo: se bandea **por predio**, no el total.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import quantiles

from sqlalchemy import select
from sqlalchemy.orm import Session

from territorial.almacen.modelos import ContextoMunicipal

# De menor a mayor. Cuatro etiquetas para cuatro cuartiles.
ETIQUETAS: tuple[str, ...] = ("bajo", "medio-bajo", "medio-alto", "alto")

# Cortes fijos de población. No son cuantiles a propósito: ver el encabezado.
CLASES_TAMANO: tuple[tuple[float, str], ...] = (
    (20_000, "pequeño"),
    (100_000, "intermedio"),
    (500_000, "grande"),
    (float("inf"), "metropolitano"),
)

# Los indicadores que se bandean por cuartil nacional, ya derivados.
POR_CUARTIL: tuple[str, ...] = (
    "valor_agregado_per_capita",
    "deficit_cuantitativo",
    "deficit_cualitativo",
    "avaluo_por_predio",
)

# Cómo se nombra cada uno en el prompt. El texto es para un lector humano.
NOMBRES: dict[str, str] = {
    "valor_agregado_per_capita": "Valor agregado por habitante",
    "deficit_cuantitativo": "Déficit habitacional cuantitativo",
    "deficit_cualitativo": "Déficit habitacional cualitativo",
    "avaluo_por_predio": "Avalúo catastral urbano por predio",
}


@dataclass(frozen=True)
class ContextoBandeado:
    """Lo único de contexto que puede ver el Correlacionador.

    **Sin un solo número, y tampoco los años.** Si el prompt llevara «censo
    2018», el modelo podría escribirlo, y una fecha en la prosa se lee como
    respaldo. El año va al informe, donde lo pone el código y se ve que es de
    2018.
    """

    divipola: str
    tamano: str | None = None
    valor_agregado_per_capita: str | None = None
    deficit_cuantitativo: str | None = None
    deficit_cualitativo: str | None = None
    avaluo_por_predio: str | None = None

    @property
    def hay_algo(self) -> bool:
        return any(
            getattr(self, c) is not None
            for c in ("tamano", *POR_CUARTIL)
        )

    def como_texto(self) -> str:
        """El bloque tal cual entra en el prompt. Adjetivos, nunca cifras."""
        if not self.hay_algo:
            return ""
        lineas = ["## Contexto estructural del municipio", ""]
        if self.tamano:
            lineas.append(f"- Tamaño del municipio: {self.tamano}")
        for campo in POR_CUARTIL:
            banda = getattr(self, campo)
            if banda:
                lineas.append(f"- {NOMBRES[campo]}: {banda} (frente a los 1.102 del país)")
        return "\n".join(lineas)


def clase_de_tamano(poblacion: int | None) -> str | None:
    if poblacion is None:
        return None
    for corte, etiqueta in CLASES_TAMANO:
        if poblacion < corte:
            return etiqueta
    return CLASES_TAMANO[-1][1]  # pragma: no cover — el último corte es infinito


def derivar(fila: ContextoMunicipal) -> dict[str, float | None]:
    """Los valores que de verdad se bandean: per cápita y por predio.

    Se derivan aquí y no se guardan en la tabla porque son un cociente de dos
    columnas que sí están: guardarlos permitiría que se desincronizaran.
    """
    per_capita = None
    if fila.valor_agregado is not None and fila.poblacion_total:
        # El valor agregado viene en miles de millones de pesos.
        per_capita = fila.valor_agregado * 1_000_000_000 / fila.poblacion_total

    por_predio = None
    if fila.avaluo_catastral_urbano is not None and fila.predios_urbanos:
        por_predio = fila.avaluo_catastral_urbano / fila.predios_urbanos

    return {
        "valor_agregado_per_capita": per_capita,
        "deficit_cuantitativo": fila.deficit_cuantitativo,
        "deficit_cualitativo": fila.deficit_cualitativo,
        "avaluo_por_predio": por_predio,
    }


def cortes_nacionales(filas: list[ContextoMunicipal]) -> dict[str, list[float]]:
    """Los tres cortes de cuartil de cada indicador, sobre los 1.102.

    Los municipios sin dato no entran en el cálculo: incluirlos como cero
    correría los cortes hacia abajo y subiría de banda a todo el mundo.
    """
    series: dict[str, list[float]] = {c: [] for c in POR_CUARTIL}
    for fila in filas:
        for campo, valor in derivar(fila).items():
            if valor is not None:
                series[campo].append(valor)

    cortes: dict[str, list[float]] = {}
    for campo, valores in series.items():
        # `quantiles` necesita al menos dos puntos; con menos no hay cuartil
        # que calcular y el indicador se queda sin banda.
        if len(valores) >= 2:
            cortes[campo] = quantiles(sorted(valores), n=4)
    return cortes


def etiqueta_de(valor: float | None, cortes: list[float] | None) -> str | None:
    """En qué cuartil cae. `bajo` es el primero; `alto`, el cuarto."""
    if valor is None or not cortes:
        return None
    for etiqueta, corte in zip(ETIQUETAS, cortes, strict=False):
        if valor <= corte:
            return etiqueta
    return ETIQUETAS[-1]


def bandear(fila: ContextoMunicipal, cortes: dict[str, list[float]]) -> ContextoBandeado:
    valores = derivar(fila)
    return ContextoBandeado(
        divipola=fila.codigo_divipola,
        tamano=clase_de_tamano(fila.poblacion_total),
        **{c: etiqueta_de(valores[c], cortes.get(c)) for c in POR_CUARTIL},
    )


def contexto_de(sesion_bd: Session, divipola: str) -> ContextoBandeado | None:
    """El contexto bandeado de un municipio, o None si no hay fila.

    Lee los 1.102 para los cortes. Son 1.102 filas de seis columnas: cabe de
    sobra y evita guardar cortes precalculados que se desactualizarían al
    recargar TerriData.
    """
    filas = list(sesion_bd.scalars(select(ContextoMunicipal)).all())
    propia = next((f for f in filas if f.codigo_divipola == divipola), None)
    if propia is None:
        return None
    return bandear(propia, cortes_nacionales(filas))
