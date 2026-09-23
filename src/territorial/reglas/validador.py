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
  R8  Ninguna cifra de la prosa falta en su entrada (CA-M6.3).

Sobre R8, que es la que añadió la remediación (F0.2, hallazgo H-009)
-------------------------------------------------------------------
La comprobación de cifras existía —`reglas/cifras.py`, con pruebas— pero **solo
se usaba en calibración**, en `scripts/comparar_correlacionador.py`. Es decir:
se comprobaba al comparar dos versiones de un prompt y **no al producir el
informe que leen las gerencias**, que es justo donde CA-M6.3 importa.

Aquí se convierte en compuerta: un insight cuya prosa trae una cifra que no
estaba en lo que el agente recibió **se rechaza con motivo**, igual que uno sin
evidencia. Da lo mismo que el número sea correcto; si el modelo lo escribió y no
estaba en su entrada, se lo inventó, y **una cifra real inventada es más difícil
de detectar que una falsa**.

Dos cosas que conviene no confundir:

· **CA-M6.3 sigue cumpliéndose por construcción en el informe**: las cifras del
  informe las compone `informes/composicion.py` desde el almacén, sin LLM. R8
  protege la **prosa** de los agentes, que es la otra superficie donde un número
  puede aparecer escrito por un modelo.
· **El límite de `cifras.py` se hereda**: solo se miran números de tres dígitos
  o más. Un «15%» escrito sin decimales puede colarse. Está declarado allí y no
  se tapa aquí.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urlparse

from territorial.reglas.cifras import inventadas
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


def _ids_referenciados(evidencia: list, ids_senal: Iterable[int] | None) -> set[int]:
    """Las señales que el insight dice usar, por las dos vías en que lo dice."""
    ids = {int(i) for i in (ids_senal or [])}
    for ev in evidencia or []:
        if isinstance(ev, dict) and ev.get("id_senal") is not None:
            ids.add(int(ev["id_senal"]))
    return ids


def validar_cifras(
    prosa: Iterable[str | None],
    evidencia: list,
    senales: dict[int, Senal],
    ids_senal: Iterable[int] | None = None,
    texto_extra: str = "",
) -> list[str]:
    """R8. Cifras de la prosa que no están en la entrada del agente.

    La entrada es **lo que el código le dio**: el contenido de las señales que
    el insight referencia, sus propias citas textuales y, para un consolidado de
    M4, la prosa de los insights de origen (`texto_extra`).

    Las citas cuentan como entrada porque R6 ya obliga a que estén en la señal:
    si una cifra está en la cita, está en la señal, y exigirla dos veces solo
    produciría falsos positivos por diferencias de recorte.
    """
    salida = " ".join(p for p in prosa if p)
    if not salida:
        return []

    partes = [texto_extra]
    for id_senal in _ids_referenciados(evidencia, ids_senal):
        senal = senales.get(id_senal)
        if senal is not None:
            partes.append(senal.contenido or "")
    for ev in evidencia or []:
        if isinstance(ev, dict):
            partes.append(str(ev.get("cita_textual") or ""))

    ajenas = inventadas(salida, " ".join(partes))
    if not ajenas:
        return []
    return [
        "cifras que no están en la entrada del agente: "
        + ", ".join(sorted(ajenas))
        + " (CA-M6.3)"
    ]


def validar(
    evidencia: list,
    divipola: str,
    id_ciclo: int,
    senales: dict[int, Senal],
    prosa: Iterable[str | None] = (),
    ids_senal: Iterable[int] | None = None,
    texto_extra: str = "",
) -> Resultado:
    """Valida la evidencia completa de un insight, y su prosa si se pasa.

    `senales` es el índice de señales del ciclo, por id. El validador nunca
    consulta la red: comprueba contra lo que se ingirió, que es lo único
    auditable.

    `prosa` son los textos que escribió el modelo —`resumen` e
    `implicacion_inmobiliaria`— y activa R8. Es opcional para que quien solo
    quiera juzgar evidencia siga pudiendo.
    """
    # R1
    if not evidencia:
        return Resultado(False, ["el insight no declara evidencia"])

    motivos: list[str] = []
    for i, ev in enumerate(evidencia):
        motivos.extend(validar_evidencia(ev, i, senales, divipola, id_ciclo))

    # R8 — va al final: si la evidencia ya no se sostiene, el motivo útil es
    # ese, y añadir cifras encima solo alarga el mensaje.
    if not motivos:
        motivos.extend(
            validar_cifras(prosa, evidencia, senales, ids_senal, texto_extra)
        )

    return Resultado(not motivos, motivos)
