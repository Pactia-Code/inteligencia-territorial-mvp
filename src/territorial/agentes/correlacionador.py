"""M4 — Agente Correlacionador (PRD §5).

Cruza insights validados de categorías distintas sobre un mismo municipio y
produce insights consolidados cuando hay convergencia.

  CA-M4.1  Cruza señales de categorías distintas y consolida si convergen.
  CA-M4.2  Extrapola explícitamente la implicación inmobiliaria.
  CA-M4.3  Lee calificaciones de ciclos previos y ajusta su criterio.
           **Es el bucle de aprendizaje del MVP.**
  CA-M4.4  La consolidación preserva la trazabilidad de todas las señales de
           origen.


Por qué el modelo no toca la evidencia
--------------------------------------
CA-M4.4 es requisito de H4, que es bloqueante. Si el agente tuviera que copiar
la evidencia de los insights que consolida, bastaría con que omitiera una cita
para que una señal desapareciera del linaje, y el fallo sería invisible: el
insight consolidado se vería perfectamente bien.

Así que el modelo **no copia evidencia**. Devuelve qué insights convergen y por
qué; la unión de la evidencia la calcula este módulo. La trazabilidad deja de
depender de que el modelo se porte bien y pasa a ser una propiedad estructural,
igual que el validador es código y no un prompt (PRD §3.1).

Lo mismo con las dos reglas que definen una convergencia. Se comprueban aquí:

  · el grupo abarca **al menos dos categorías conocidas distintas** — CA-M4.1
    pide cruce de categorías, no de contratos. Agrupar dos frentes de obra vial
    es trabajo del Clasificador, y es justo el pendiente A4. `otro` no cuenta:
    es lo que el Clasificador escribe cuando no reconoce la categoría, así que
    admitirla dejaría correlacionar cualquier cosa con un fallo suyo.
  · el grupo tiene **al menos dos insights**, todos de los entregados.

Un grupo que no las cumpla se rechaza con su motivo, y los insights vuelven a
quedar sueltos. No se pierde ninguno.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from territorial.agentes.cliente import (
    cliente_compartido,
    desglosar_uso,
    despliegue_de,
    techo_de,
)
from territorial.config import Config, obtener_config
from territorial.reglas.contexto import ContextoBandeado

PROMPTS = Path(__file__).parent / "prompts"
# **v1 sigue siendo la versión vigente.** v2 existe y funciona, pero no pasó su
# compuerta: ver `scripts/comparar_correlacionador.py` y el pendiente A10. Se
# conserva porque §10 lo pide —las versiones que no se promueven documentan una
# hipótesis— y porque la medición que la frenó tiene un confundido sin resolver.
VERSION_PROMPT = "v1"

# Qué versiones entienden el bloque de contexto estructural. Mandar el bloque a
# un prompt que no lo documenta es peor que no mandarlo: el modelo recibe datos
# sin ninguna regla sobre qué puede hacer con ellos, y la regla «el contexto
# explica, nunca crea» es justo lo que hay que sostener.
VERSIONES_CON_CONTEXTO = frozenset({"v2"})

CONFIANZAS = {"alta", "media", "baja"}

# CA-M4.1: una convergencia cruza categorías. Por debajo de esto no es
# correlación, es consolidación, y le toca al Clasificador.
MIN_CATEGORIAS = 2
MIN_INSIGHTS = 2

# `otro` no es una categoría: es lo que el Clasificador escribe cuando el
# modelo devolvió una que no reconoce. Dejar que cuente para el cruce de
# CA-M4.1 permitiría correlacionar cualquier cosa con un fallo de
# categorización, así que no cuenta.
CATEGORIA_DESCONOCIDA = "otro"


# --------------------------------------------------------------------------
# Entrada
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class InsightValidado:
    """Un insight que ya pasó el validador determinista.

    Vista plana, sin ORM, por la misma razón que en el validador: se puede
    construir a mano en una prueba.
    """

    id: int
    categoria: str
    resumen: str
    implicacion_inmobiliaria: str
    # [{id_senal, cita_textual, url, fecha, fuente}]
    evidencia: list[dict]
    ids_senal: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class CalificacionPrevia:
    """Lo que una gerencia opinó de un insight de un ciclo anterior. CA-M4.3."""

    categoria: str
    valor: float
    id_ciclo: int
    comentario: str | None = None


# --------------------------------------------------------------------------
# Esquema de salida del modelo
# --------------------------------------------------------------------------


class Convergencia(BaseModel):
    ids_insight: list[int] = Field(
        description="Identificadores de los insights recibidos que convergen"
    )
    por_que_convergen: str = Field(
        description="El hecho territorial concreto que los une: un corredor, un sector, un plazo"
    )
    resumen: str = Field(description="Qué está pasando, consolidado")
    implicacion_inmobiliaria: str = Field(
        description="Lo que se deduce del cruce y no se deducía de ningún insight por separado"
    )
    confianza: str = Field(description="alta, media o baja")


class SalidaCorrelacionador(BaseModel):
    convergencias: list[Convergencia]


# --------------------------------------------------------------------------
# Resultado
# --------------------------------------------------------------------------


@dataclass
class InsightCorrelacionado:
    """Una convergencia aceptada, con la evidencia ya unida por código."""

    ids_insight: list[int]
    categorias: list[str]
    por_que_convergen: str
    resumen: str
    implicacion_inmobiliaria: str
    confianza: str
    evidencia: list[dict]
    ids_senal: list[int]

    def a_dict(self) -> dict:
        return {
            "ids_insight": self.ids_insight,
            "categorias": self.categorias,
            "por_que_convergen": self.por_que_convergen,
            "resumen": self.resumen,
            "implicacion_inmobiliaria": self.implicacion_inmobiliaria,
            "confianza": self.confianza,
            "evidencia": self.evidencia,
            "ids_senal": self.ids_senal,
        }


@dataclass
class GrupoRechazado:
    ids_insight: list[int]
    motivo: str


@dataclass
class ResultadoCorrelacion:
    correlacionados: list[InsightCorrelacionado] = field(default_factory=list)
    rechazados: list[GrupoRechazado] = field(default_factory=list)
    # Los que no entraron en ninguna convergencia. Siguen su camino intactos:
    # no converger no es un defecto.
    sueltos: list[int] = field(default_factory=list)
    # CA-M4.4: señales que entraron y ya no son alcanzables. Debe ir vacía.
    senales_perdidas: list[int] = field(default_factory=list)
    tokens_entrada: int = 0
    tokens_salida: int = 0
    tokens_razonamiento: int = 0
    tokens_cache_lectura: int = 0
    duracion_ms: int = 0
    error: str | None = None
    version_prompt: str = VERSION_PROMPT

    @property
    def trazabilidad_intacta(self) -> bool:
        """CA-M4.4: ninguna señal de origen se perdió al consolidar."""
        return not self.senales_perdidas


@lru_cache
def instrucciones(version: str = VERSION_PROMPT) -> str:
    ruta = PROMPTS / f"correlacionador_{version}.md"
    if not ruta.exists():
        raise FileNotFoundError(f"no existe el prompt {ruta}")
    return ruta.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# Serialización del bloque variable
# --------------------------------------------------------------------------


def _resumen_calificaciones(calificaciones: list[CalificacionPrevia]) -> str:
    """Media por categoría de lo que las gerencias valoraron antes. CA-M4.3.

    Se agrega por categoría y no insight a insight porque lo que el agente debe
    ajustar es su criterio de relevancia, no su memoria de casos concretos.
    """
    if not calificaciones:
        return ""

    por_categoria: dict[str, list[float]] = {}
    for c in calificaciones:
        por_categoria.setdefault(c.categoria, []).append(c.valor)

    lineas = ["", "## Calificaciones de las gerencias en ciclos anteriores", ""]
    for categoria, valores in sorted(por_categoria.items()):
        media = sum(valores) / len(valores)
        lineas.append(f"- {categoria}: {media:.1f} de 5 sobre {len(valores)} calificaciones")
    return "\n".join(lineas)


def _serializar(
    insights: list[InsightValidado],
    municipio: str,
    departamento: str,
    contexto_bing: list[str],
    calificaciones: list[CalificacionPrevia],
    contexto: ContextoBandeado | None = None,
) -> str:
    lineas = [
        f"Municipio: {municipio} ({departamento})",
        f"Insights validados: {len(insights)}",
        "",
    ]
    for i in insights:
        lineas.append(f"[id_insight={i.id}] ({i.categoria})")
        lineas.append(f"  resumen: {i.resumen.strip()}")
        if i.implicacion_inmobiliaria:
            lineas.append(f"  implicación: {i.implicacion_inmobiliaria.strip()}")
        lineas.append("")

    # Bandas, nunca cifras: lo calcula `reglas/contexto.py` y por eso puede
    # enunciarse en la salida. Ver CA-M6.3 y el prompt v2.
    if contexto is not None and contexto.hay_algo:
        lineas.append(contexto.como_texto())
        lineas.append("")

    if contexto_bing:
        lineas.append("## Contexto Bing — orientativo, nunca evidencia (D1)")
        lineas.append("")
        for fragmento in contexto_bing:
            lineas.append(f"- {fragmento.strip()[:400]}")
        lineas.append("")

    resumen = _resumen_calificaciones(calificaciones)
    if resumen:
        lineas.append(resumen)

    return "\n".join(lineas)


# --------------------------------------------------------------------------
# Ensamblado determinista de la salida
# --------------------------------------------------------------------------


def _unir_evidencia(elegidos: list[InsightValidado]) -> tuple[list[dict], list[int]]:
    """Une la evidencia de los insights consolidados sin perder ninguna.

    Es la garantía de CA-M4.4. Se deduplica por (id_senal, cita_textual): dos
    insights pueden citar el mismo fragmento de la misma señal, y repetirlo en
    el consolidado no añade trazabilidad, solo ruido en el informe.
    """
    vistas: set[tuple] = set()
    evidencia: list[dict] = []
    for ins in elegidos:
        for e in ins.evidencia:
            clave = (e.get("id_senal"), e.get("cita_textual"))
            if clave in vistas:
                continue
            vistas.add(clave)
            evidencia.append(dict(e))

    ids_senal = sorted({e["id_senal"] for e in evidencia if e.get("id_senal") is not None})
    return evidencia, ids_senal


def ensamblar(
    convergencias: list[Convergencia],
    insights: list[InsightValidado],
) -> ResultadoCorrelacion:
    """Valida los grupos propuestos y une su evidencia. Sin LLM.

    Separado de la llamada al modelo a propósito: es la parte que decide si una
    correlación es admisible, y se prueba con datos escritos a mano.
    """
    por_id = {i.id: i for i in insights}
    resultado = ResultadoCorrelacion()
    usados: set[int] = set()

    for c in convergencias:
        ids = sorted(set(c.ids_insight))

        desconocidos = [i for i in ids if i not in por_id]
        if desconocidos:
            resultado.rechazados.append(
                GrupoRechazado(ids, f"referencia insights no entregados: {desconocidos}")
            )
            continue

        if len(ids) < MIN_INSIGHTS:
            resultado.rechazados.append(
                GrupoRechazado(ids, f"un grupo de {len(ids)} no es una convergencia")
            )
            continue

        elegidos = [por_id[i] for i in ids]
        categorias = sorted({i.categoria for i in elegidos})
        conocidas = [c for c in categorias if c != CATEGORIA_DESCONOCIDA]

        if len(conocidas) < MIN_CATEGORIAS:
            if len(categorias) < MIN_CATEGORIAS:
                motivo = (
                    f"todos son de la categoría {categorias[0]!r}: es consolidación, "
                    "no correlación (le toca al Clasificador, pendiente A4)"
                )
            else:
                motivo = (
                    f"solo {len(conocidas)} categoría conocida entre {categorias}: "
                    f"{CATEGORIA_DESCONOCIDA!r} es un fallo de categorización del "
                    "Clasificador, no una categoría con la que cruzar"
                )
            resultado.rechazados.append(GrupoRechazado(ids, motivo))
            continue

        confianza = c.confianza.strip().lower()
        if confianza not in CONFIANZAS:
            confianza = "baja"

        evidencia, ids_senal = _unir_evidencia(elegidos)

        resultado.correlacionados.append(
            InsightCorrelacionado(
                ids_insight=ids,
                categorias=categorias,
                por_que_convergen=c.por_que_convergen,
                resumen=c.resumen,
                implicacion_inmobiliaria=c.implicacion_inmobiliaria,
                confianza=confianza,
                evidencia=evidencia,
                ids_senal=ids_senal,
            )
        )
        usados.update(ids)

    resultado.sueltos = sorted(set(por_id) - usados)

    # CA-M4.4 comprobado, no supuesto: toda señal que entró tiene que seguir
    # alcanzable, sea desde un consolidado o desde un insight suelto.
    entraron = {s for i in insights for s in _senales_de(i)}
    alcanzables = {s for c in resultado.correlacionados for s in c.ids_senal}
    alcanzables |= {s for i in resultado.sueltos for s in _senales_de(por_id[i])}
    resultado.senales_perdidas = sorted(entraron - alcanzables)

    return resultado


def _senales_de(i: InsightValidado) -> set[int]:
    de_evidencia = {
        e["id_senal"] for e in i.evidencia if e.get("id_senal") is not None
    }
    return de_evidencia | set(i.ids_senal)


# --------------------------------------------------------------------------
# Llamada al modelo
# --------------------------------------------------------------------------


def correlacionar(
    insights: list[InsightValidado],
    municipio: str,
    departamento: str,
    contexto_bing: list[str] | None = None,
    calificaciones: list[CalificacionPrevia] | None = None,
    contexto: ContextoBandeado | None = None,
    config: Config | None = None,
    version: str = VERSION_PROMPT,
) -> ResultadoCorrelacion:
    """Correlaciona los insights validados de un municipio en un ciclo.

    Como el Clasificador, no lanza por fallo del modelo: devuelve el error en
    el resultado para que un municipio malo no aborte el ciclo.
    """
    cfg = config or obtener_config()

    # Con menos de dos insights no hay nada que cruzar, y llamar al modelo
    # sería gasto puro: sobre 18 municipios por 3 ciclos se nota.
    if len(insights) < MIN_INSIGHTS:
        return ResultadoCorrelacion(sueltos=sorted(i.id for i in insights))

    conocidas = {i.categoria for i in insights} - {CATEGORIA_DESCONOCIDA}
    if len(conocidas) < MIN_CATEGORIAS:
        return ResultadoCorrelacion(sueltos=sorted(i.id for i in insights))

    cliente = cliente_compartido()
    modelo = despliegue_de("correlacionador", cfg)
    inicio = time.perf_counter()

    try:
        respuesta = cliente.responses.parse(
            model=modelo,
            instructions=instrucciones(version),
            input=_serializar(
                insights, municipio, departamento, contexto_bing or [],
                calificaciones or [],
                contexto if version in VERSIONES_CON_CONTEXTO else None,
            ),
            text_format=SalidaCorrelacionador,
            max_output_tokens=techo_de("correlacionador", cfg),
        )
    except Exception as exc:
        return ResultadoCorrelacion(
            sueltos=sorted(i.id for i in insights),
            duracion_ms=int((time.perf_counter() - inicio) * 1000),
            error=f"{type(exc).__name__}: {exc}",
            version_prompt=version,
        )

    duracion = int((time.perf_counter() - inicio) * 1000)
    salida = respuesta.output_parsed
    uso = desglosar_uso(respuesta.usage)

    if salida is None:
        return ResultadoCorrelacion(
            sueltos=sorted(i.id for i in insights),
            tokens_entrada=uso["entrada"],
            tokens_salida=uso["salida"],
            tokens_razonamiento=uso["razonamiento"],
            tokens_cache_lectura=uso["cache_lectura"],
            duracion_ms=duracion,
            error="el modelo no devolvio salida estructurada (posible corte por max_output_tokens)",
            version_prompt=version,
        )

    resultado = ensamblar(salida.convergencias, insights)
    resultado.tokens_entrada = uso["entrada"]
    resultado.tokens_salida = uso["salida"]
    resultado.tokens_razonamiento = uso["razonamiento"]
    resultado.tokens_cache_lectura = uso["cache_lectura"]
    resultado.duracion_ms = duracion
    resultado.version_prompt = version
    return resultado


def hash_entrada(insights: list[InsightValidado]) -> str:
    """Huella del lote, para `traza_agente.hash_input` (CA-M8.2)."""
    crudo = json.dumps(sorted(i.id for i in insights))
    return hashlib.sha256(crudo.encode()).hexdigest()
