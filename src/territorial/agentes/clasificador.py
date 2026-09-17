"""M2 — Agente Clasificador (PRD §5).

Descarta ruido, categoriza y produce insights con evidencia enlazada.

Criterios que gobiernan este módulo:
  CA-M2.1  Reduce el volumen de señales crudas en ≥85% por ciclo.
  CA-M2.2  Cada insight lleva DIVIPOLA, categoría, resumen, implicación
           inmobiliaria y evidencia enlazada.
  CA-M2.3  Sin restricción de idioma.
  CA-M2.4  Sin restricción de tipología de activo a priori.
  CA-M2.5  Registra en la traza qué descartó y por qué.

El prefiltro determinista ya quitó el 61,2%. Este agente debe descartar otro
61,4% de lo que recibe para que el conjunto llegue al 85% (pendiente B2).

Sobre el orden del prompt: las instrucciones van en `instructions`, que es
estable entre llamadas, y las señales en `input`, que cambia. Esa separación es
la que permite que el proveedor reutilice el prefijo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from territorial.agentes.cliente import cliente_compartido, desglosar_uso, despliegue_de
from territorial.config import Config, obtener_config

PROMPTS = Path(__file__).parent / "prompts"
VERSION_PROMPT = "v4"

CATEGORIAS = {
    "obra_vial",
    "servicios_publicos",
    "equipamiento",
    "vivienda",
    "ordenamiento",
    "industria_logistica",
    "suelo_predios",
}


# --------------------------------------------------------------------------
# Esquema de salida
# --------------------------------------------------------------------------


class Evidencia(BaseModel):
    id_senal: int = Field(description="Identificador de la señal recibida")
    cita_textual: str = Field(description="Fragmento copiado literalmente de la señal")


class InsightPropuesto(BaseModel):
    # La prueba de sustancia, obligatoria: qué queda sobre el suelo cuando el
    # contrato termine. Obligar a escribirla es lo que impide clasificar por
    # tema en vez de por efecto.
    cambio_fisico: str = Field(
        description="Qué queda construido, ampliado, conectado o habilitado, en concreto"
    )
    categoria: str
    resumen: str
    implicacion_inmobiliaria: str
    evidencia: list[Evidencia]


class Descarte(BaseModel):
    id_senal: int
    motivo: str


class SalidaClasificador(BaseModel):
    insights: list[InsightPropuesto]
    descartes: list[Descarte]


# --------------------------------------------------------------------------
# Entrada
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SenalEntrada:
    id: int
    fuente: str
    fecha: date | None
    contenido: str
    url: str | None


@dataclass
class ResultadoLote:
    insights: list[dict] = field(default_factory=list)
    descartes: list[dict] = field(default_factory=list)
    tokens_entrada: int = 0
    tokens_salida: int = 0
    # Para el pendiente B4. El razonamiento ya va dentro de tokens_salida; se
    # desglosa aparte solo para saber cuánto de la factura es pensar.
    tokens_razonamiento: int = 0
    tokens_cache_lectura: int = 0
    duracion_ms: int = 0
    error: str | None = None
    # CA-M2.5 exige saber qué se descartó y por qué. Una señal que no aparece
    # ni en un insight ni en los descartes se perdió sin dejar rastro.
    sin_contabilizar: list[int] = field(default_factory=list)
    version_prompt: str = VERSION_PROMPT


@lru_cache
def instrucciones(version: str = VERSION_PROMPT) -> str:
    ruta = PROMPTS / f"clasificador_{version}.md"
    if not ruta.exists():
        raise FileNotFoundError(f"no existe el prompt {ruta}")
    return ruta.read_text(encoding="utf-8")


def _serializar(senales: list[SenalEntrada], municipio: str, departamento: str) -> str:
    """Arma el bloque variable del prompt."""
    lineas = [
        f"Municipio: {municipio} ({departamento})",
        f"Señales a clasificar: {len(senales)}",
        "",
    ]
    for s in senales:
        fecha = s.fecha.isoformat() if s.fecha else "sin fecha"
        # El contenido se recorta: los objetos contractuales muy largos
        # repiten formulas juridicas que no aportan a la decision.
        contenido = s.contenido.strip()[:1200]
        lineas.append(f"[id_senal={s.id}] ({s.fuente}, {fecha}) {contenido}")
    return "\n".join(lineas)


def clasificar_lote(
    senales: list[SenalEntrada],
    municipio: str,
    departamento: str,
    config: Config | None = None,
    version: str = VERSION_PROMPT,
) -> ResultadoLote:
    """Clasifica un lote de señales de un municipio.

    Nunca lanza por fallo del modelo: devuelve el error en el resultado para
    que un lote malo no aborte el ciclo, igual que CA-M1.4 exige para fuentes.
    """
    import time

    cfg = config or obtener_config()
    if not senales:
        return ResultadoLote()

    cliente = cliente_compartido()
    modelo = despliegue_de("clasificador", cfg)
    inicio = time.perf_counter()

    try:
        respuesta = cliente.responses.parse(
            model=modelo,
            instructions=instrucciones(version),
            input=_serializar(senales, municipio, departamento),
            text_format=SalidaClasificador,
            max_output_tokens=cfg.max_tokens_salida,
        )
    except Exception as exc:
        return ResultadoLote(
            duracion_ms=int((time.perf_counter() - inicio) * 1000),
            error=f"{type(exc).__name__}: {exc}",
            version_prompt=version,
        )

    duracion = int((time.perf_counter() - inicio) * 1000)
    salida = respuesta.output_parsed
    uso = desglosar_uso(respuesta.usage)

    if salida is None:
        return ResultadoLote(
            tokens_entrada=uso["entrada"],
            tokens_salida=uso["salida"],
            tokens_razonamiento=uso["razonamiento"],
            tokens_cache_lectura=uso["cache_lectura"],
            duracion_ms=duracion,
            error="el modelo no devolvio salida estructurada (posible corte por max_output_tokens)",
            version_prompt=version,
        )

    ids_validos = {s.id for s in senales}
    por_id = {s.id: s for s in senales}

    insights: list[dict] = []
    for prop in salida.insights:
        # Se descarta aqui lo que el validador rechazaria de todas formas:
        # referencias a señales que no se entregaron.
        evidencia = [
            {
                "id_senal": e.id_senal,
                "cita_textual": e.cita_textual,
                "url": por_id[e.id_senal].url,
                "fecha": por_id[e.id_senal].fecha.isoformat() if por_id[e.id_senal].fecha else None,
                "fuente": por_id[e.id_senal].fuente,
            }
            for e in prop.evidencia
            if e.id_senal in ids_validos
        ]
        if not evidencia:
            continue
        categoria = prop.categoria if prop.categoria in CATEGORIAS else "otro"
        insights.append(
            {
                "cambio_fisico": getattr(prop, "cambio_fisico", ""),
                "categoria": categoria,
                "resumen": prop.resumen,
                "implicacion_inmobiliaria": prop.implicacion_inmobiliaria,
                "evidencia": evidencia,
                "ids_senal": sorted({e["id_senal"] for e in evidencia}),
            }
        )

    descartes = [
        {"id_senal": d.id_senal, "motivo": d.motivo}
        for d in salida.descartes
        if d.id_senal in ids_validos
    ]

    # CA-M2.5: toda señal debe quedar en un insight o en un descarte. Lo que
    # no aparece en ninguno se perdió sin motivo registrado.
    usadas = {i for ins in insights for i in ins["ids_senal"]}
    descartadas = {d["id_senal"] for d in descartes}
    sin_contabilizar = sorted(ids_validos - usadas - descartadas)

    return ResultadoLote(
        insights=insights,
        descartes=descartes,
        tokens_entrada=uso["entrada"],
        tokens_salida=uso["salida"],
        tokens_razonamiento=uso["razonamiento"],
        tokens_cache_lectura=uso["cache_lectura"],
        duracion_ms=duracion,
        sin_contabilizar=sin_contabilizar,
        version_prompt=version,
    )


def hash_entrada(senales: list[SenalEntrada]) -> str:
    """Huella del lote, para `traza_agente.hash_input`."""
    import hashlib

    crudo = json.dumps([s.id for s in senales], sort_keys=True)
    return hashlib.sha256(crudo.encode()).hexdigest()
