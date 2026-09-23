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

**Se confirma municipio a municipio, no al final.** Un ciclo completo tarda
alrededor de una hora y cuesta tokens; si todo fuera en una sola transacción,
morir en el minuto 50 perdería los 50 minutos pagados. LangGraph daría
checkpointing (CA-M8.4) pero **no está cableado**, así que el punto de guardado
es el commit por municipio: lo procesado queda en la base pase lo que pase.
"""

from __future__ import annotations

import logging
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
from territorial.agentes.clasificador import (
    instrucciones as prompt_clasificador,
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
from territorial.agentes.correlacionador import (
    instrucciones as prompt_correlacionador,
)
from territorial.agentes.linaje import registrar_prompt
from territorial.agentes.persistencia import (
    crear_corrida,
    guardar_correlaciones,
    guardar_descartes,
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
from territorial.reglas.contexto import contexto_de
from territorial.reglas.normalizacion import normalizar
from territorial.reglas.prefiltro import clasificar as prefiltrar
from territorial.reglas.validador import Senal as SenalValidador
from territorial.reglas.validador import validar, validar_cifras
from territorial.scoring.agregacion import cortes_por_fuente, entradas_del_ciclo
from territorial.scoring.persistencia import guardar as guardar_scores
from territorial.scoring.ranking import puntuar_ciclo

log = logging.getLogger(__name__)

FUENTE_CONTRATOS = "SECOP II"
# RSS entra al Clasificador **sin prefiltro**. Bing no entra: D1 es explícito
# en que no origina insights, y llega al Correlacionador como contexto.
FUENTE_NOTICIAS = "RSS"
FUENTE_CONTEXTO = "Bing"


@dataclass
class ResumenMunicipio:
    divipola: str
    nombre: str
    crudas: int = 0
    tras_prefiltro: int = 0
    enviadas: int = 0
    enviadas_rss: int = 0
    lotes: int = 0
    insights: int = 0
    validados: int = 0
    rechazados: int = 0
    correlacionados: int = 0
    descartes: int = 0
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
                f"{m.validados:>2} válidos, {m.correlacionados} correlacionados, "
                f"{m.descartes} descartes"
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


def texto_de(senal: SenalCruda) -> str:
    """El texto que se le entrega al Clasificador, según la fuente.

    SECOP trae el objeto contractual en `datos["objeto"]`; RSS trae `titulo` y
    `resumen`, y **no tiene `objeto`**. Leer solo `objeto` dejaba a las
    noticias con cadena vacía, y el prefiltro las descartaba por «objeto
    vacío» — una de las tres barreras que las excluían en silencio.
    """
    d = senal.datos or {}
    if senal.fuente == FUENTE_NOTICIAS:
        titulo = (d.get("titulo") or "").strip()
        resumen = (d.get("resumen") or "").strip()
        # El resumen de Google News repite el titular a menudo; no se duplica.
        if resumen and resumen != titulo:
            return f"{titulo}. {resumen}"
        return titulo or senal.contenido or ""
    return d.get("objeto") or senal.contenido or ""


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
    ordenadas = sorted(senales, key=lambda s: normalizar(texto_de(s)))
    return [ordenadas[i : i + tamano] for i in range(0, len(ordenadas), tamano)]


def procesar_municipio(
    sesion_bd: Session,
    municipio: Municipio,
    corrida: CorridaAgentes,
    tamano_lote: int | None = None,
    config: Config | None = None,
    id_prompt_clasificador: int | None = None,
    id_prompt_correlacionador: int | None = None,
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

    # --- SECOP II: pasa por el prefiltro ---
    contratos = [s for s in crudas if s.fuente == FUENTE_CONTRATOS]
    pasan = [s for s in contratos if prefiltrar((s.datos or {}).get("objeto"))[0]]
    resumen.tras_prefiltro = len(pasan)

    # --- RSS: **sin filtro**, y en lotes propios ---
    #
    # El prefiltro no se aplica a las noticias por tres razones, en orden de
    # peso (ver el pendiente del registro):
    #
    #   1. El diccionario descarta justo lo que hace valiosa a la fuente. Sobre
    #      titulares dejaría pasar el 79%, pero lo que rechaza es «Tribunal
    #      ordena destrabar la concertación ambiental del POT de Madrid» o
    #      «servicios catastrales y asesoría predial» — eventos y anuncios de
    #      desarrollo territorial, que es exactamente el papel que el PRD §2.3
    #      le asigna a RSS y que SECOP no ve.
    #   2. **No hay coste que ahorrar.** Las 336 señales del año son +7,9% sobre
    #      lo que ya cuesta SECOP. Y para RSS el prefiltro tampoco cumple su
    #      otra función: `es_obra` alimenta F1–F3, que son de SECOP; RSS solo
    #      alimenta F5, que es un conteo y no usa el diccionario.
    #   3. Inventar un segundo diccionario sin datos para calibrarlo, teniendo
    #      A2 abierto justamente por un diccionario mal calibrado, sería repetir
    #      el error a sabiendas — y con 336 señales no habría volumen para
    #      detectar que se torció.
    #
    # Van en lotes propios porque el formato es otro: 232 caracteres de titular
    # contra 458 de objeto contractual. Mezclarlos en un lote le pediría al
    # prompt v4 —escrito para objetos contractuales— juzgar dos cosas distintas
    # a la vez. Si trata mal los titulares será un hallazgo medido, y entonces
    # un prompt propio se justificará con datos.
    noticias = [s for s in crudas if s.fuente == FUENTE_NOTICIAS]

    log.info(
        "%s ciclo %s: %d crudas -> SECOP %d de las que pasan %d (%.0f%%), "
        "RSS %d sin filtro, %s %d solo como contexto (D1)",
        municipio.divipola, id_ciclo, len(crudas), len(contratos), len(pasan),
        100 * len(pasan) / len(contratos) if contratos else 0,
        len(noticias), FUENTE_CONTEXTO,
        sum(1 for s in crudas if s.fuente == FUENTE_CONTEXTO),
    )

    if not pasan and not noticias:
        return resumen

    lotes = _en_lotes(pasan, tamano) + _en_lotes(noticias, tamano)
    resumen.lotes = len(lotes)
    resumen.enviadas = len(pasan) + len(noticias)
    resumen.enviadas_rss = len(noticias)

    # --- M2, lote a lote ---
    lote_plano: list[SenalCruda] = []
    insights_crudos: list[dict] = []
    descartes_crudos: list[dict] = []
    sin_contabilizar: list[int] = []
    fallos: list[str] = []

    for lote in lotes:
        entradas = [
            SenalEntrada(
                id=s.id,
                fuente=s.fuente,
                fecha=s.fecha_publicacion,
                contenido=texto_de(s),
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
        descartes_crudos.extend(res.descartes)
        sin_contabilizar.extend(res.sin_contabilizar)

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
            contenido=texto_de(s),
            url=s.url,
            fecha_publicacion=s.fecha_publicacion,
        )
        for s in lote
    }

    juzgados: list[dict] = []
    for ins in res_insights:
        veredicto = validar(
            ins["evidencia"], municipio.divipola, id_ciclo, vistas,
            # R8 (CA-M6.3): la prosa del Clasificador contra las señales que
            # dice haber usado. Ver el encabezado de `reglas/validador.py`.
            prosa=(ins.get("resumen"), ins.get("implicacion_inmobiliaria")),
            ids_senal=ins.get("ids_senal"),
        )
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
        sesion_bd, juzgados, corrida.id, municipio.divipola, VERSION_CLASIFICADOR,
        id_prompt=id_prompt_clasificador,
    )
    # CA-M2.5: sin esto la tasa de reducción de CA-M2.1 no es auditable.
    resumen.descartes = guardar_descartes(
        sesion_bd, descartes_crudos, sin_contabilizar, corrida.id
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
        # Bandas del contexto estructural (CA-M4.2). `None` si TerriData no
        # está cargado: el agente se comporta entonces como con el prompt v1.
        contexto=contexto_de(sesion_bd, municipio.divipola),
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

    # R8 sobre M4 (CA-M6.3): la prosa del Correlacionador contra **su** entrada,
    # que es la prosa y la evidencia de los insights que el código le pasó, más
    # las señales de esos insights. El contexto estructural no entra porque
    # viaja bandeado —adjetivos, nunca cifras (`reglas/contexto.py`)—, así que
    # un número que apareciera por ahí sí sería inventado.
    por_id = {i.id: i for i in para_correlacionar}
    motivos_m4: list[str | None] = []
    for c in corr.correlacionados:
        origenes = [por_id[i] for i in c.ids_insight if i in por_id]
        fallos = validar_cifras(
            (c.resumen, c.implicacion_inmobiliaria, c.por_que_convergen),
            c.evidencia,
            vistas,
            ids_senal=c.ids_senal,
            texto_extra=" ".join(
                f"{o.resumen} {o.implicacion_inmobiliaria}" for o in origenes
            ),
        )
        motivos_m4.append("; ".join(fallos) if fallos else None)
    resumen.rechazados += sum(1 for m in motivos_m4 if m)

    guardar_correlaciones(
        sesion_bd, corr, corrida.id, municipio.divipola, mapa_ids,
        id_prompt=id_prompt_correlacionador,
        motivos=motivos_m4,
    )
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

    # D7: se archivan los prompts y se anclan por hash antes de usarlos. Si
    # alguno cambió de contenido sin cambiar de versión, esto falla aquí y no
    # a mitad del ciclo con la mitad de los tokens gastados.
    pc = registrar_prompt(
        sesion_bd, "clasificador", VERSION_CLASIFICADOR, prompt_clasificador(), config=cfg
    )
    pr = registrar_prompt(
        sesion_bd,
        "correlacionador",
        VERSION_CORRELACIONADOR,
        prompt_correlacionador(),
        config=cfg,
    )

    resumen = ResumenCiclo(id_ciclo=id_ciclo, corrida_agentes=corrida)
    for municipio in municipios:
        try:
            resumen.municipios.append(
                procesar_municipio(
                    sesion_bd, municipio, corrida, tamano_lote, cfg,
                    id_prompt_clasificador=pc.id,
                    id_prompt_correlacionador=pr.id,
                )
            )
            # Punto de guardado: lo que costó tokens queda en la base antes de
            # seguir. Sin esto, una caída en el municipio 17 tira los 16
            # anteriores.
            sesion_bd.commit()
        except Exception as exc:  # noqa: BLE001 — un municipio no tumba el ciclo
            sesion_bd.rollback()
            resumen.municipios.append(
                ResumenMunicipio(
                    divipola=municipio.divipola,
                    nombre=municipio.nombre,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            # El rollback deshizo también la corrida si el fallo fue en el
            # primer municipio: se vuelve a adjuntar para no perder el hilo.
            sesion_bd.add(corrida)
            sesion_bd.commit()

    corrida.senales_procesadas = sum(m.enviadas for m in resumen.municipios)
    corrida.tokens_entrada = resumen.tokens_entrada
    corrida.tokens_salida = resumen.tokens_salida
    sesion_bd.commit()

    # --- M5, determinista y sin tokens ---
    try:
        entradas = entradas_del_ciclo(sesion_bd, id_ciclo, cfg)
        cortes = cortes_por_fuente(sesion_bd, id_ciclo, cfg)
        corrida_s = guardar_scores(
            sesion_bd, puntuar_ciclo(entradas, id_ciclo, cfg, cortes)
        )
        sesion_bd.commit()
        resumen.corrida = corrida_s
    except Exception as exc:  # noqa: BLE001
        # Puntuar va después de gastar tokens en M2 y M4. Perder esa salida
        # porque el scoring falló sería el peor cambio posible.
        resumen.error_scoring = f"{type(exc).__name__}: {exc}"

    return resumen
