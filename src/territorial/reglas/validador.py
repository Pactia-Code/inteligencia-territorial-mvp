"""M3 — Validador determinista (PRD §5, CA-M3.1 a CA-M3.4).

Esta es la pieza más importante del experimento y es **código, nunca LLM**
(PRD §3.1): si un modelo decidiera qué evidencia es suficiente, el experimento
perdería su ancla de honestidad, porque un agente elocuente parece funcionar
aunque invente.

Su tasa de rechazo **es la tasa de alucinación medida** (CA-M3.3), y de ella
depende H4, que es bloqueante.

Reglas, en orden de aplicación:
  R1  El insight declara al menos un elemento de evidencia.
  R2  Ningún elemento se apoya en Bing              (Addendum 01, D1).
  R3  Cada elemento trae url, fecha y cita_textual  (CA-M3.1).
  R4  La URL está bien formada y es http(s)         (CA-M3.1, "accesible").
  R5  La fecha es una fecha real.
  R6  La cita aparece en la señal de origen         (CA-M3.1, "localizable").
  R7  La señal citada existe, y es del mismo municipio y ciclo del insight.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urlparse

from territorial.reglas.normalizacion import contiene

# D1: Bing es contexto cualitativo. Nunca evidencia.
FUENTES_PROHIBIDAS = {"Bing"}

ESQUEMAS_VALIDOS = {"http", "https"}


@dataclass(frozen=True)
class Senal:
    """Vista mínima de una señal cruda, para no acoplar el validador al ORM."""

    id: int
    divipola: str
    id_ciclo: int
    fuente: str
    contenido: str
    url: str | None
    fecha_publicacion: date | None


@dataclass
class Resultado:
    valido: bool
    motivos: list[str] = field(default_factory=list)

    @property
    def motivo(self) -> str | None:
        return "; ".join(self.motivos) if self.motivos else None


def _fecha_valida(valor) -> bool:
    if isinstance(valor, date):
        return True
    try:
        date.fromisoformat(str(valor)[:10])
    except (TypeError, ValueError):
        return False
    return True


def _url_valida(valor) -> bool:
    if not valor or not isinstance(valor, str):
        return False
    try:
        p = urlparse(valor.strip())
    except ValueError:
        return False
    return p.scheme.lower() in ESQUEMAS_VALIDOS and bool(p.netloc)


def validar_evidencia(
    evidencia: dict,
    indice: int,
    senales: dict[int, Senal],
    divipola: str,
    id_ciclo: int,
) -> list[str]:
    """Aplica R2–R7 a un elemento de evidencia. Devuelve los motivos de rechazo."""
    fallos: list[str] = []
    etiqueta = f"evidencia[{indice}]"

    if not isinstance(evidencia, dict):
        return [f"{etiqueta}: no es un objeto"]

    # R2 — origen prohibido
    fuente = evidencia.get("fuente")
    if fuente in FUENTES_PROHIBIDAS:
        fallos.append(f"{etiqueta}: origen {fuente} no puede sustentar evidencia (D1)")

    # R3 — campos obligatorios
    for campo in ("url", "fecha", "cita_textual"):
        if not evidencia.get(campo):
            fallos.append(f"{etiqueta}: falta {campo}")

    # R4 — URL bien formada
    if evidencia.get("url") and not _url_valida(evidencia["url"]):
        fallos.append(f"{etiqueta}: url mal formada o sin esquema http(s)")

    # R5 — fecha real
    if evidencia.get("fecha") and not _fecha_valida(evidencia["fecha"]):
        fallos.append(f"{etiqueta}: fecha no interpretable")

    # R6 y R7 — la cita tiene que existir en una señal real de este municipio y ciclo
    id_senal = evidencia.get("id_senal")
    if id_senal is None:
        fallos.append(f"{etiqueta}: no referencia ninguna señal de origen")
        return fallos

    senal = senales.get(id_senal)
    if senal is None:
        fallos.append(f"{etiqueta}: la señal {id_senal} no existe")
        return fallos

    if senal.fuente in FUENTES_PROHIBIDAS:
        fallos.append(f"{etiqueta}: la señal {id_senal} es de {senal.fuente} (D1)")

    if senal.divipola != divipola:
        fallos.append(
            f"{etiqueta}: la señal {id_senal} es de {senal.divipola}, no de {divipola}"
        )

    if senal.id_ciclo != id_ciclo:
        fallos.append(
            f"{etiqueta}: la señal {id_senal} es del ciclo {senal.id_ciclo}, no del {id_ciclo}"
        )

    cita = evidencia.get("cita_textual")
    if cita and not contiene(senal.contenido, cita):
        fallos.append(f"{etiqueta}: la cita no aparece en la señal {id_senal}")

    return fallos


def validar(
    evidencia: list,
    divipola: str,
    id_ciclo: int,
    senales: dict[int, Senal],
) -> Resultado:
    """Valida la evidencia completa de un insight.

    `senales` es el índice de señales del ciclo, por id. El validador nunca
    consulta la red: comprueba contra lo que se ingirió, que es lo único
    auditable.
    """
    # R1
    if not evidencia:
        return Resultado(False, ["el insight no declara evidencia"])

    motivos: list[str] = []
    for i, ev in enumerate(evidencia):
        motivos.extend(validar_evidencia(ev, i, senales, divipola, id_ciclo))

    return Resultado(not motivos, motivos)
