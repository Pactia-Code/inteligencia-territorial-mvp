"""Orquestación de un ciclo completo (B6).

Encadena el orden real de ejecución de Arquitectura §3:

    prefiltro → M2 Clasificador → M3 Validador → persistir
              → M4 Correlacionador → persistir → M5 Scoring

Es configuración determinista, no un agente: el PRD §2.2 excluye el agente
orquestador precisamente porque su función de planificación es fija. Cuando se
cablee LangGraph (`grafo/`, CA-M8.4) este módulo es lo que se convierte en el
grafo; hasta entonces un bucle explícito se lee mejor y se depura antes.

Un municipio que falla no aborta el ciclo, igual que CA-M1.4 exige para las
fuentes: se registra el error y se sigue. Un ciclo de 18 municipios que se cae
en el tercero no deja nada utilizable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from territorial.agentes.clasificador import (
    VERSION_PROMPT as VERSION_CLASIFICADOR,
)
from territorial.agentes.clasificador import (
    SenalEntrada,
    clasificar_lote,
)
from territorial.agentes.clasificador import (
    hash_entrada as hash_clasificador,
)
from territorial.agentes.cliente import despliegue_de
from territorial.agentes.correlacionador import (
    CalificacionPrevia,
    InsightValidado,
    correlacionar,
)
from territorial.agentes.persistencia import (
    guardar_correlaciones,
    guardar_insights,
    guardar_traza,
)
from territorial.almacen.modelos import Calificacion, Insight, Municipio, SenalCruda
from territorial.config import Config, obtener_config
from territorial.reglas.prefiltro import clasificar as prefiltrar
from territorial.reglas.validador import Senal as SenalValidador
from territorial.reglas.validador import validar

FUENTE_CONTRATOS = "SECOP II"
FUENTE_CONTEXTO = "Bing"


@dataclass
class ResumenMunicipio:
    divipola: str
    nombre: str
    crudas: int = 0
    tras_prefiltro: int = 0
    enviadas: int = 0
    insights: int = 0
    validados: int = 0
    rechazados: int = 0
    correlacionados: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0
    error: str | None = None

    @property
    def reduccion(self) -> float:
        """Fracción de señales crudas que no llegó a insight válido. CA-M2.1."""
        if self.crudas <= 0:
            return 0.0
        return 1.0 - (self.validados / self.crudas)


@dataclass
class ResumenCiclo:
    id_ciclo: int
    municipios: list[ResumenMunicipio] = field(default_factory=list)

    @property
    def tokens_entrada(self) -> int:
        return sum(m.tokens_entrada for m in self.municipios)

    @property
    def tokens_salida(self) -> int:
        return sum(m.tokens_salida for m in self.municipios)

    @property
    def con_error(self) -> list[ResumenMunicipio]:
        return [m for m in self.municipios if m.error]

    @property
    def reduccion_global(self) -> float:
        crudas = sum(m.crudas for m in self.municipios)
        validados = sum(m.validados for m in self.municipios)
        return 1.0 - (validados / crudas) if crudas else 0.0

    def __str__(self) -> str:
        lineas = [f"Ciclo {self.id_ciclo} — {len(self.municipios)} municipios"]
        for m in self.municipios:
            if m.error:
                lineas.append(f"  {m.divipola} {m.nombre:<22} ERROR: {m.error[:60]}")
                continue
            lineas.append(
                f"  {m.divipola} {m.nombre:<22} "
                f"{m.crudas:>5} crudas → {m.enviadas:>3} enviadas → "
                f"{m.validados:>2} válidos, {m.correlacionados} correlacionados"
            )
        lineas.append("")
        lineas.append(
            f"Reducción global: {self.reduccion_global:.1%}  "
            f"(CA-M2.1 exige ≥85%)"
        )
        lineas.append(
            f"Tokens: {self.tokens_entrada:,} entrada + {self.tokens_salida:,} salida"
        )
        if self.con_error:
            lineas.append(f"Municipios con error: {len(self.con_error)}")
        return "\n".join(lineas)


def _calificaciones_previas(
    sesion_bd: Session, divipola: str, id_ciclo: int
) -> list[CalificacionPrevia]:
    """Lo que las gerencias opinaron antes sobre este municipio. CA-M4.3."""
    if id_ciclo <= 1:
        return []
    filas = sesion_bd.execute(
        select(Insight.categoria, Calificacion.valor, Insight.id_ciclo)
        .join(Calificacion, Calificacion.id_insight == Insight.id)
        .where(Insight.divipola == divipola, Insight.id_ciclo < id_ciclo)
    ).all()
    return [CalificacionPrevia(categoria=c, valor=float(v), id_ciclo=ci) for c, v, ci in filas]


def procesar_municipio(
    sesion_bd: Session,
    municipio: Municipio,
    id_ciclo: int,
    limite: int = 25,
    config: Config | None = None,
) -> ResumenMunicipio:
    """Corre la cadena completa sobre un municipio y persiste el resultado.

    `limite` acota cuántas señales se mandan al Clasificador en una llamada.
    No es un ajuste de gusto: con 40 señales de Barranquilla el Clasificador
    devuelve el JSON truncado (pendiente B5). 25 es lo que cabe hoy.
    """
    cfg = config or obtener_config()
    resumen = ResumenMunicipio(divipola=municipio.divipola, nombre=municipio.nombre)

    crudas = sesion_bd.scalars(
        select(SenalCruda)
        .where(SenalCruda.id_ciclo == id_ciclo, SenalCruda.divipola == municipio.divipola)
        .order_by(SenalCruda.id)
    ).all()
    resumen.crudas = len(crudas)

    contratos = [s for s in crudas if s.fuente == FUENTE_CONTRATOS]
    pasan = [s for s in contratos if prefiltrar((s.datos or {}).get("objeto"))[0]]
    resumen.tras_prefiltro = len(pasan)

    lote = pasan[:limite]
    resumen.enviadas = len(lote)
    if not lote:
        return resumen

    # --- M2 ---
    entradas = [
        SenalEntrada(
            id=s.id,
            fuente=s.fuente,
            fecha=s.fecha_publicacion,
            contenido=(s.datos or {}).get("objeto") or s.contenido,
            url=s.url,
        )
        for s in lote
    ]
    res = clasificar_lote(entradas, municipio.nombre, municipio.departamento, cfg)
    resumen.tokens_entrada += res.tokens_entrada
    resumen.tokens_salida += res.tokens_salida

    guardar_traza(
        sesion_bd,
        id_ciclo=id_ciclo,
        agente="clasificador",
        modelo=despliegue_de("clasificador", cfg),
        tokens_entrada=res.tokens_entrada,
        tokens_salida=res.tokens_salida,
        duracion_ms=res.duracion_ms,
        hash_input=hash_clasificador(entradas),
    )

    if res.error:
        resumen.error = res.error
        return resumen
    resumen.insights = len(res.insights)

    # --- M3: determinista, sobre cada insight ---
    vistas = {
        s.id: SenalValidador(
            id=s.id,
            divipola=s.divipola,
            id_ciclo=s.id_ciclo,
            fuente=s.fuente,
            contenido=(s.datos or {}).get("objeto") or s.contenido,
            url=s.url,
            fecha_publicacion=s.fecha_publicacion,
        )
        for s in lote
    }

    juzgados: list[dict] = []
    for ins in res.insights:
        veredicto = validar(ins["evidencia"], municipio.divipola, id_ciclo, vistas)
        juzgados.append(
            {
                **ins,
                "estado_validacion": "validado" if veredicto.valido else "rechazado",
                "motivo_rechazo": veredicto.motivo,
            }
        )
    resumen.validados = sum(1 for i in juzgados if i["estado_validacion"] == "validado")
    resumen.rechazados = len(juzgados) - resumen.validados

    # --- Persistir M2 + M3 ---
    filas = guardar_insights(
        sesion_bd, juzgados, id_ciclo, municipio.divipola, VERSION_CLASIFICADOR
    )

    # El agente numera el lote de 1 en adelante; la base asigna otros ids. El
    # mapa los une para que `ids_insight_origen` apunte a filas reales.
    validadas = [
        (n, fila)
        for n, (fila, ins) in enumerate(zip(filas, juzgados, strict=True), start=1)
        if ins["estado_validacion"] == "validado"
    ]
    mapa_ids = {n: fila.id for n, fila in validadas}

    para_correlacionar = [
        InsightValidado(
            id=n,
            categoria=fila.categoria,
            resumen=fila.resumen,
            implicacion_inmobiliaria=fila.implicacion_inmobiliaria or "",
            evidencia=fila.evidencia,
            ids_senal=fila.ids_senal,
        )
        for n, fila in validadas
    ]

    # --- M4 ---
    contexto = [s.contenido for s in crudas if s.fuente == FUENTE_CONTEXTO]
    corr = correlacionar(
        para_correlacionar,
        municipio.nombre,
        municipio.departamento,
        contexto_bing=contexto,
        calificaciones=_calificaciones_previas(sesion_bd, municipio.divipola, id_ciclo),
        config=cfg,
    )
    resumen.tokens_entrada += corr.tokens_entrada
    resumen.tokens_salida += corr.tokens_salida

    if corr.tokens_entrada or corr.error:
        guardar_traza(
            sesion_bd,
            id_ciclo=id_ciclo,
            agente="correlacionador",
            modelo=despliegue_de("correlacionador", cfg),
            tokens_entrada=corr.tokens_entrada,
            tokens_salida=corr.tokens_salida,
            duracion_ms=corr.duracion_ms,
        )

    if corr.error:
        resumen.error = f"correlacionador: {corr.error}"
        return resumen

    if not corr.trazabilidad_intacta:
        # CA-M4.4 es requisito de H4. Si se rompe, no se guarda: una base con
        # linaje incompleto es peor que una sin el consolidado.
        resumen.error = f"CA-M4.4 rota, señales perdidas: {corr.senales_perdidas}"
        return resumen

    guardar_correlaciones(sesion_bd, corr, id_ciclo, municipio.divipola, mapa_ids)
    resumen.correlacionados = len(corr.correlacionados)

    return resumen


def procesar_ciclo(
    sesion_bd: Session,
    id_ciclo: int,
    limite: int = 25,
    solo: list[str] | None = None,
    config: Config | None = None,
) -> ResumenCiclo:
    """Corre la cadena sobre todos los municipios del ciclo."""
    cfg = config or obtener_config()
    consulta = select(Municipio).order_by(Municipio.divipola)
    if solo:
        consulta = consulta.where(Municipio.divipola.in_(solo))

    resumen = ResumenCiclo(id_ciclo=id_ciclo)
    for municipio in sesion_bd.scalars(consulta).all():
        try:
            resumen.municipios.append(
                procesar_municipio(sesion_bd, municipio, id_ciclo, limite, cfg)
            )
        except Exception as exc:  # noqa: BLE001 — un municipio no tumba el ciclo
            resumen.municipios.append(
                ResumenMunicipio(
                    divipola=municipio.divipola,
                    nombre=municipio.nombre,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
    return resumen
