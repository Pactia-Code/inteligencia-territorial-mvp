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
    VERSION_PROMPT as VERSION_CORRELACIONADOR,
)
from territorial.agentes.correlacionador import (
    CalificacionPrevia,
    InsightValidado,
    correlacionar,
)
from territorial.agentes.persistencia import (
    crear_corrida,
    guardar_correlaciones,
    guardar_insights,
    guardar_traza,
)
from territorial.almacen.modelos import (
    Calificacion,
    CorridaAgentes,
    Insight,
    Municipio,
    SenalCruda,
)
from territorial.config import Config, obtener_config
from territorial.reglas.normalizacion import normalizar
from territorial.reglas.prefiltro import clasificar as prefiltrar
from territorial.reglas.validador import Senal as SenalValidador
from territorial.reglas.validador import validar
from territorial.scoring.agregacion import cortes_por_fuente, entradas_del_ciclo
from territorial.scoring.persistencia import guardar as guardar_scores
from territorial.scoring.ranking import puntuar_ciclo

FUENTE_CONTRATOS = "SECOP II"
FUENTE_CONTEXTO = "Bing"


@dataclass
class ResumenMunicipio:
    divipola: str
    nombre: str
    crudas: int = 0
    tras_prefiltro: int = 0
    enviadas: int = 0
    lotes: int = 0
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
    # La pasada de agentes de la que cuelgan los insights.
    corrida_agentes: object | None = None
    # La corrida de scoring que se insertó al final. Es de donde saldrá
    # `informe.id_corrida` cuando M6 publique.
    corrida: object | None = None
    error_scoring: str | None = None

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
                f"{m.crudas:>5} crudas → {m.enviadas:>4} enviadas en {m.lotes} lotes → "
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
        if self.corrida_agentes is not None:
            lineas.append(
                f"Agentes: corrida {self.corrida_agentes.id} "
                f"({self.corrida_agentes.tipo_corrida})"
            )
        if self.corrida is not None:
            lineas.append(
                f"Scoring: corrida {self.corrida.id} ({self.corrida.tipo_corrida}), "
                f"versión {self.corrida.version_scoring}, "
                f"corte {self.corrida.fecha_corte_cohorte or 'sin determinar'}"
            )
        if self.error_scoring:
            lineas.append(f"Scoring FALLÓ: {self.error_scoring}")
        return "\n".join(lineas)


def _calificaciones_previas(
    sesion_bd: Session, divipola: str, id_ciclo: int
) -> list[CalificacionPrevia]:
    """Lo que las gerencias opinaron antes sobre este municipio. CA-M4.3."""
    if id_ciclo <= 1:
        return []
    filas = sesion_bd.execute(
        select(Insight.categoria, Calificacion.valor, CorridaAgentes.id_ciclo)
        .join(Calificacion, Calificacion.id_insight == Insight.id)
        .join(CorridaAgentes, CorridaAgentes.id == Insight.id_corrida)
        .where(Insight.divipola == divipola, CorridaAgentes.id_ciclo < id_ciclo)
    ).all()
    return [CalificacionPrevia(categoria=c, valor=float(v), id_ciclo=ci) for c, v, ci in filas]


def _en_lotes(senales: list[SenalCruda], tamano: int) -> list[list[SenalCruda]]:
    """Trocea las señales de un municipio, agrupando las de objeto parecido.

    El orden importa. El Clasificador agrupa por *frente de intervención*, así
    que si dos contratos del mismo frente caen en lotes distintos salen dos
    insights en vez de uno: es el pendiente A4, empeorado por el troceo.
    Ordenar por el objeto normalizado deja juntos los contratos de redacción
    casi idéntica, que es el caso frecuente cuando un frente se paga con varios
    contratos.

    No lo resuelve del todo: dos contratos del mismo frente redactados distinto
    seguirán separándose. Agruparlos de verdad exigiría medir similitud, y eso
    es trabajo del pendiente A4.
    """
    ordenadas = sorted(senales, key=lambda s: normalizar((s.datos or {}).get("objeto")))
    return [ordenadas[i : i + tamano] for i in range(0, len(ordenadas), tamano)]


def procesar_municipio(
    sesion_bd: Session,
    municipio: Municipio,
    corrida: CorridaAgentes,
    tamano_lote: int | None = None,
    config: Config | None = None,
) -> ResumenMunicipio:
    """Corre la cadena completa sobre un municipio y persiste el resultado.

    Procesa **todas** las señales que pasan el prefiltro, en lotes. Antes se
    mandaba solo el primer lote y el resto se descartaba en silencio: de las
    897 señales de Barranquilla en el ciclo 1 se clasificaban 25.
    """
    cfg = config or obtener_config()
    id_ciclo = corrida.id_ciclo
    tamano = tamano_lote or cfg.senales_por_lote
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

    if not pasan:
        return resumen

    lotes = _en_lotes(pasan, tamano)
    resumen.lotes = len(lotes)
    resumen.enviadas = len(pasan)

    # --- M2, lote a lote ---
    lote_plano: list[SenalCruda] = []
    insights_crudos: list[dict] = []
    fallos: list[str] = []

    for lote in lotes:
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
            tokens_cache_lectura=res.tokens_cache_lectura,
            duracion_ms=res.duracion_ms,
            hash_input=hash_clasificador(entradas),
        )

        if res.error:
            # Un lote malo no tira el municipio: se anota y se sigue con los
            # demás. Perder un municipio entero por un lote de cincuenta
            # señales sería peor que procesarlo incompleto y decirlo.
            fallos.append(res.error)
            continue

        lote_plano.extend(lote)
        insights_crudos.extend(res.insights)

    if fallos and not insights_crudos:
        resumen.error = f"todos los lotes fallaron; el primero: {fallos[0]}"
        return resumen
    if fallos:
        resumen.error = f"{len(fallos)} de {len(lotes)} lotes fallaron: {fallos[0]}"

    resumen.insights = len(insights_crudos)
    lote = lote_plano
    res_insights = insights_crudos

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
    for ins in res_insights:
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
        sesion_bd, juzgados, corrida.id, municipio.divipola, VERSION_CLASIFICADOR
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
            tokens_cache_lectura=corr.tokens_cache_lectura,
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

    guardar_correlaciones(sesion_bd, corr, corrida.id, municipio.divipola, mapa_ids)
    resumen.correlacionados = len(corr.correlacionados)

    return resumen


def procesar_ciclo(
    sesion_bd: Session,
    id_ciclo: int,
    tamano_lote: int | None = None,
    solo: list[str] | None = None,
    config: Config | None = None,
) -> ResumenCiclo:
    """Corre la cadena sobre los municipios del ciclo y puntúa al final.

    **El scoring se encadena siempre**, sin ramas por `solo`. Es seguro
    precisamente por las corridas append-only: cada ejecución inserta una
    corrida nueva y ninguna pisa a otra.

    Y sale `completa` aunque se haya pedido un solo municipio, lo cual **es
    correcto y no un descuido**: el scoring no lee insights, lee `senal_cruda`,
    `municipio.elic` y —solo para F6— calificaciones. Así que puntúa siempre la
    cohorte entera y sus cifras no dependen de a quién se acabe de clasificar.
    Restringir la cohorte a lo reprocesado sería peor: normalizar min-max sobre
    un municipio da 0,5 a todo el mundo, que no significa nada.

    `tipo_corrida` marcará `parcial` el día que alguien puntúe un subconjunto
    de verdad. La guarda vive en `scoring/persistencia.py`, así que ese día no
    hay que acordarse de nada.
    """
    cfg = config or obtener_config()
    consulta = select(Municipio).order_by(Municipio.divipola)
    if solo:
        consulta = consulta.where(Municipio.divipola.in_(solo))
    municipios = sesion_bd.scalars(consulta).all()

    # La corrida se abre **antes** del bucle: los insights cuelgan de ella. La
    # cohorte son los municipios que se van a procesar, no los que acaben bien;
    # excluir a los que fallan haría parecer la pasada más completa de lo que
    # fue. `tipo_corrida` lo decide `crear_corrida`, no este bucle.
    corrida = crear_corrida(
        sesion_bd,
        id_ciclo,
        [m.divipola for m in municipios],
        version_clasificador=VERSION_CLASIFICADOR,
        version_correlacionador=VERSION_CORRELACIONADOR,
    )

    resumen = ResumenCiclo(id_ciclo=id_ciclo, corrida_agentes=corrida)
    for municipio in municipios:
        try:
            resumen.municipios.append(
                procesar_municipio(sesion_bd, municipio, corrida, tamano_lote, cfg)
            )
        except Exception as exc:  # noqa: BLE001 — un municipio no tumba el ciclo
            resumen.municipios.append(
                ResumenMunicipio(
                    divipola=municipio.divipola,
                    nombre=municipio.nombre,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )

    corrida.senales_procesadas = sum(m.enviadas for m in resumen.municipios)
    corrida.tokens_entrada = resumen.tokens_entrada
    corrida.tokens_salida = resumen.tokens_salida
    sesion_bd.flush()

    # --- M5, determinista y sin tokens ---
    try:
        entradas = entradas_del_ciclo(sesion_bd, id_ciclo, cfg)
        cortes = cortes_por_fuente(sesion_bd, id_ciclo, cfg)
        corrida = guardar_scores(
            sesion_bd, puntuar_ciclo(entradas, id_ciclo, cfg, cortes)
        )
        resumen.corrida = corrida
    except Exception as exc:  # noqa: BLE001
        # Puntuar va después de gastar tokens en M2 y M4. Perder esa salida
        # porque el scoring falló sería el peor cambio posible.
        resumen.error_scoring = f"{type(exc).__name__}: {exc}"

    return resumen
