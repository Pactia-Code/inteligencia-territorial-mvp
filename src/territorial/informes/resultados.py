"""Compone `docs/informe_resultados.md` desde las mediciones. F0b.1 (H-034).

**El documento se genera, no se escribe.** La prosa vive en
`plantilla_resultados.md`, con un hueco `{{nombre}}` donde va cada cifra, y
este módulo llena los huecos con lo que miden `mediciones.py`, `costo.py` y
`reglas/tasa_rechazo.py`.

**Tres reglas lo hacen fiable, y las tres se comprueban al renderizar:**

1. **Ninguna cifra sin su consulta.** Una `Cifra` cuyo texto lleva un dígito
   no se puede construir sin decir qué la produce. Se pinta siempre con su
   etiqueta `[consulta: … · corridas … · commit …]`.
2. **Ningún hueco sin cifra ni cifra sin hueco.** Si la plantilla pide algo que
   no se midió, o se mide algo que la plantilla no usa, el render falla en vez
   de dejar un `{{…}}` o perder una cifra en silencio.
3. **Salida determinista.** Nada dentro del documento depende de la hora: el
   commit y los cortes son parámetros, y todas las consultas ordenan. La única
   dependencia del reloj es si la ronda extendida ya cerró, y eso solo decide
   si se imprime «pendiente de cierre» o el cálculo, sin escribir la hora.

**Este documento reporta valores contra criterios. No da veredictos**: eso lo
hace la evaluación del piloto, con `docs/prompts/evaluacion-piloto.md` y el
tablero congelado en `docs/javelin.md`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from territorial.informes import costo, mediciones as m
from territorial.reglas import tasa_rechazo as tr

PLANTILLA = Path(__file__).with_name("plantilla_resultados.md")
BOGOTA = ZoneInfo("America/Bogota")
COMMIT_VALIDO = re.compile(r"^[0-9a-f]{7,40}$")
HUECO = re.compile(r"\{\{([a-z0-9_]+)\}\}")

# --- Lo que el informe mide, fijado por la historia que reporta ----------
#: El informe publicado de la ronda.
INFORME = 8
#: La corrida de agentes publicada (la del informe 8).
CORRIDA_PUBLICADA = 10
#: A6: las dos pasadas completas del Clasificador sobre el ciclo 1.
PASADAS_A6 = (7, 8)
#: A11: las dos pasadas del Correlacionador v1 contra sí mismo, sobre la 10.
PASADAS_A11 = (11, 12)
#: Dos corridas de scoring del mismo ciclo y versión: la reproducibilidad del código.
SCORING_GEMELAS = (3, 4)
#: Hallazgo 5: top 3 antes y después de bajar F4, por ciclo.
TOP_ANTES_DESPUES = ((1, 16, 19), (2, 8, 20), (3, 18, 21))
#: Las corridas de scoring vigentes de los tres ciclos (la 24 es la publicada).
SCORING_VIGENTES = (22, 23, 24)
SCORING_PUBLICADA = 24
#: Municipios que el informe nombra.
APARTADO, BARRANQUILLA, FUNZA, IBAGUE = "05045", "08001", "25286", "73001"


# ---------------------------------------------------------------------------
# Formato en castellano
# ---------------------------------------------------------------------------

def entero(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def decimal(x: float, d: int = 1) -> str:
    return f"{x:,.{d}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def pct(num: int, den: int, d: int = 1) -> str:
    """«98,8 % (322 de 326)». Con el n siempre: una tasa sin su n no es un dato."""
    if not den:
        return "sin casos"
    return f"{decimal(100 * num / den, d)} % ({entero(num)} de {entero(den)})"


def lista(xs: list[str]) -> str:
    xs = list(xs)
    return xs[0] if len(xs) == 1 else f"{', '.join(xs[:-1])} y {xs[-1]}"


def corridas_texto(ids: tuple[int, ...]) -> str:
    if not ids:
        return "sin corrida"
    if len(ids) == 1:
        return f"corrida {ids[0]}"
    return f"corridas {lista([str(i) for i in ids])}"


# ---------------------------------------------------------------------------
# Cifras y parámetros
# ---------------------------------------------------------------------------

class CifraSinConsulta(ValueError):
    """Un número sin la consulta que lo produce es justo lo que H-034 quitó."""


@dataclass(frozen=True)
class Cifra:
    texto: str
    consulta: str | None = None
    corridas: tuple[int, ...] = ()
    #: Tabla o bloque de varias líneas: la etiqueta va debajo, no en línea.
    bloque: bool = False
    #: Un parámetro de la generación (commit, corte): se pinta sin etiqueta.
    parametro: bool = False

    def __post_init__(self) -> None:
        if not self.parametro and self.consulta is None and re.search(r"\d", self.texto):
            raise CifraSinConsulta(f"«{self.texto[:40]}» lleva cifras y no dice qué las produce")

    def pintar(self, commit: str) -> str:
        if self.consulta is None:
            return self.texto
        etiqueta = (f"`[consulta: {self.consulta} · {corridas_texto(self.corridas)}"
                    f" · {commit[:7]}]`")
        return f"{self.texto}\n\n{etiqueta}" if self.bloque else f"{self.texto} {etiqueta}"


PENDIENTE = "*pendiente de cierre*"


@dataclass(frozen=True)
class Parametros:
    commit: str
    corte_principal: datetime
    corte_extendida: datetime
    #: Solo decide si la extendida ya cerró. **No se escribe en el documento.**
    a_fecha: datetime
    carpeta_principal: Path
    ruta_snapshot: Path
    ruta_tarifas: Path

    def __post_init__(self) -> None:
        if not COMMIT_VALIDO.match(self.commit):
            raise ValueError(f"commit no válido: {self.commit!r}")
        for nombre in ("corte_principal", "corte_extendida", "a_fecha"):
            if getattr(self, nombre).tzinfo is None:
                raise ValueError(f"{nombre} tiene que llevar zona horaria")

    @property
    def extendida_cerrada(self) -> bool:
        return self.a_fecha > self.corte_extendida


def _corte(t: datetime) -> str:
    return (f"{t.astimezone(BOGOTA):%Y-%m-%d %H:%M:%S} de Bogotá "
            f"(`{t.astimezone(timezone.utc):%Y-%m-%d %H:%M:%S}+00`)")


# ---------------------------------------------------------------------------
# Medir
# ---------------------------------------------------------------------------

def _tabla_h2(r: m.ResultadoH2) -> str:
    filas = ["| Gerencia | Tipo | Pedidos calificados | Tasa |", "|---|---|---:|---:|"]
    for g in sorted(r.por_gerencia, key=lambda g: (g.tipo != "prd", g.id_gerencia)):
        filas.append(f"| `{g.id_gerencia}` | {g.tipo} | {g.calificados} de {g.pedidos} | "
                     f"{decimal(g.porcentaje)} % |")
    return "\n".join(filas)


def _rondas(cifras: dict, sufijo: str, pedidos: m.Pedidos, cal: list[dict] | None) -> None:
    """H1 y H2 de una ronda. Con `cal=None`, la ronda aún no ha cerrado."""
    claves = (f"h1{sufijo}_cuentan", f"h1{sufijo}_insuficientes", f"h1{sufijo}_prd",
              f"h1{sufijo}_adic", f"h2{sufijo}_promedio", f"h2{sufijo}_tabla")
    if cal is None:
        for k in claves:
            cifras[k] = Cifra(PENDIENTE)
        return
    fuente = f"mediciones.h1 + calificaciones_hasta (corte {'principal' if sufijo == 'p' else 'extendido'})"
    r1 = m.h1(pedidos, cal)
    cifras[f"h1{sufijo}_cuentan"] = Cifra(f"{r1.cuentan} de {r1.pedidos}", fuente)
    cifras[f"h1{sufijo}_insuficientes"] = Cifra(entero(r1.insuficientes), fuente)
    cifras[f"h1{sufijo}_prd"] = Cifra(pct(r1.altos_prd, r1.cuentan), fuente)
    cifras[f"h1{sufijo}_adic"] = Cifra(pct(r1.altos_con_adicionales, r1.cuentan), fuente)
    r2 = m.h2(pedidos, cal)
    fuente2 = fuente.replace("h1", "h2")
    promedio = r2.promedio_prd
    cifras[f"h2{sufijo}_promedio"] = Cifra(
        f"{decimal(promedio)} % (n = {r2.n_prd} gerencias «prd»)" if promedio is not None
        else "sin gerencias «prd»", fuente2)
    cifras[f"h2{sufijo}_tabla"] = Cifra(_tabla_h2(r2), fuente2, bloque=True)


def medir(sesion: Session, p: Parametros) -> dict[str, Cifra]:
    """Todas las cifras del documento, por nombre. **Solo lectura.**"""
    c: dict[str, Cifra] = {}
    nom = m.nombres(sesion)

    # --- Parámetros de la generación --------------------------------------
    c["p_commit"] = Cifra(f"`{p.commit}`", parametro=True)
    c["p_corte_principal"] = Cifra(_corte(p.corte_principal), parametro=True)
    c["p_corte_extendida"] = Cifra(_corte(p.corte_extendida), parametro=True)
    c["p_estado_extendida"] = Cifra(
        "cerrada" if p.extendida_cerrada else "**pendiente de cierre**", parametro=True)

    # --- Inventario (H-031) -----------------------------------------------
    inv = m.inventario(sesion)
    q = "mediciones.inventario"
    c["inv_municipios"] = Cifra(entero(inv.municipios), q)
    c["inv_senales"] = Cifra(entero(inv.senales), q)
    c["inv_secop"] = Cifra(entero(inv.senales_por_fuente.get("SECOP II", 0)), q)
    c["inv_rss"] = Cifra(entero(inv.senales_por_fuente.get("RSS", 0)), q)
    c["inv_bing"] = Cifra(entero(inv.senales_por_fuente.get("Bing", 0)), q)
    c["inv_dias"] = Cifra(lista([entero(d) for _, d in sorted(inv.dias_por_ciclo.items())]), q)
    c["inv_corridas_agentes"] = Cifra(entero(inv.corridas_agentes), q)
    c["inv_corridas_scoring"] = Cifra(entero(inv.corridas_scoring), q)
    c["inv_insights"] = Cifra(entero(inv.insights), q)
    c["inv_descartes"] = Cifra(entero(inv.descartes), q)
    c["inv_trazas"] = Cifra(entero(inv.trazas), q)
    c["inv_informes"] = Cifra(
        f"{inv.informes_publicados} publicado y {inv.informes_archivados} archivados", q)

    # --- La ronda principal, verificada contra su exportación ------------
    pedidos = m.pedidos_del_informe(sesion, INFORME)
    cal_p = m.calificaciones_hasta(sesion, p.corte_principal)
    filas = m.verificar_contra_exportacion(cal_p, p.carpeta_principal)
    c["inv_calif_principal"] = Cifra(
        entero(filas), "calificaciones_hasta (corte principal) = manifiesto de la exportación")
    c["h1_pedidos"] = Cifra(entero(len(pedidos.ids)), "mediciones.pedidos_del_informe")
    _rondas(c, "p", pedidos, cal_p)
    cal_e = m.calificaciones_hasta(sesion, p.corte_extendida) if p.extendida_cerrada else None
    _rondas(c, "e", pedidos, cal_e)

    # --- A6 y A11, que condicionan la lectura de H1 -----------------------
    a, b = PASADAS_A6
    va, vb = m.volumen(sesion, a), m.volumen(sesion, b)
    c["a6_insights"] = Cifra(f"{entero(va.insights)} y {entero(vb.insights)}",
                             "mediciones.volumen", PASADAS_A6)
    c["a6_evidencias"] = Cifra(f"{entero(va.evidencias)} y {entero(vb.evidencias)}",
                               "mediciones.volumen", PASADAS_A6)
    pa = m.comparar_pasadas(sesion, a, b)
    q = "mediciones.comparar_pasadas (destino_por_senal)"
    c["a6_cambian"] = Cifra(pct(pa.cambian_destino, pa.senales), q, PASADAS_A6)
    c["a6_vuelcan"] = Cifra(pct(pa.vuelcan_insight, pa.senales), q, PASADAS_A6)
    for clave, divipola in (("a6_barranquilla", BARRANQUILLA), ("a6_funza", FUNZA)):
        pm = m.comparar_pasadas(sesion, a, b, divipola)
        c[clave] = Cifra(pct(pm.vuelcan_insight, pm.senales), q + f" ({nom[divipola]})",
                         PASADAS_A6)

    co = m.comparar_correlaciones(sesion, *PASADAS_A11, CORRIDA_PUBLICADA)
    q = "mediciones.comparar_correlaciones (huellas por ids_insight_origen)"
    corr_a11 = (*PASADAS_A11, CORRIDA_PUBLICADA)
    c["a11_identicas"] = Cifra(pct(co.identicas, co.distintas), q, corr_a11)
    c["a11_agrupados"] = Cifra(pct(co.agrupados_que_cambian, co.corpus), q, corr_a11)
    c["a11_municipios"] = Cifra(f"{co.municipios_que_cambian} de {co.municipios}", q, corr_a11)
    c["a11_convergencias"] = Cifra(lista([str(x) for x in co.convergencias]), q, PASADAS_A11)
    c["a11_tipologia"] = Cifra(lista([str(x) for x in co.con_tipologia]),
                               "mediciones.comparar_correlaciones (TIPOLOGIA)", PASADAS_A11)
    for clave, i in (("hz_pisoruido_11", 0), ("hz_pisoruido_12", 1)):
        c[clave] = Cifra(f"{co.convergencias[i]} y {co.con_tipologia[i]}",
                         "mediciones.comparar_correlaciones", (PASADAS_A11[i],))
    distintos, comparados = m.scores_identicos(sesion, *SCORING_GEMELAS)
    c["scoring_identico"] = Cifra(f"{distintos} de {comparados}", "mediciones.scores_identicos",
                                  SCORING_GEMELAS)

    # --- H3 ----------------------------------------------------------------
    desglose = tr.desde_la_base(sesion)
    filas_rt = ["| Corrida | Insights del Clasificador | Rechazados | Sobreviven | Rechazos por regla | R8 |",
                "|---:|---:|---:|---:|---|---|"]
    # Todas las corridas con insights del Clasificador, también las de prueba
    # con un puñado: filtrarlas sería un umbral elegido a mano, y cada fila
    # lleva su n para que se lea con su peso.
    for d in desglose:
        reglas = lista([f"{k}: {v}" for k, v in sorted(d.por_regla.items())]) if d.por_regla else "—"
        marca = " **(publicada)**" if d.id_corrida == CORRIDA_PUBLICADA else ""
        filas_rt.append(
            f"| {d.id_corrida}{marca} | {entero(d.evaluados)} | {entero(d.rechazados)} | "
            f"{pct(d.evaluados - d.rechazados, d.evaluados)} | {reglas} | "
            f"{'evaluada' if d.r8_evaluada else 'no evaluada'} |")
    usadas = tuple(d.id_corrida for d in desglose)
    c["h3_tabla"] = Cifra("\n".join(filas_rt), "tasa_rechazo.desde_la_base", usadas, bloque=True)
    publicada = next(d for d in desglose if d.id_corrida == CORRIDA_PUBLICADA)
    c["h3_superv_10"] = Cifra(
        pct(publicada.evaluados - publicada.rechazados, publicada.evaluados),
        "tasa_rechazo.desde_la_base", (CORRIDA_PUBLICADA,))
    evaluan_r8 = [d.id_corrida for d in desglose if d.r8_evaluada]
    c["h3_r8"] = Cifra(
        f"ninguna de las {len(desglose)} corridas con insights del Clasificador"
        if not evaluan_r8 else f"las corridas {lista([str(x) for x in evaluan_r8])}",
        "tasa_rechazo.evaluaba_r8 (fecha de la corrida frente a FECHA_R8)",
        tuple(d.id_corrida for d in desglose))
    c["h3_frase"] = Cifra(tr.FRASE_H029)
    s10, s9 = m.supervivencia_por_fuente(sesion, 10), m.supervivencia_por_fuente(sesion, 9)
    q = "mediciones.supervivencia_por_fuente"
    c["h3_rss_10"] = Cifra(pct(s10.validados.get("RSS", 0), s10.total.get("RSS", 0)), q, (10,))
    c["h3_secop_10"] = Cifra(pct(s10.validados.get("SECOP II", 0), s10.total.get("SECOP II", 0)), q, (10,))
    c["h3_rss_9"] = Cifra(pct(s9.validados.get("RSS", 0), s9.total.get("RSS", 0)), q, (9,))
    cv = m.conversion_por_fuente(sesion, CORRIDA_PUBLICADA)
    q = "mediciones.conversion_por_fuente"
    c["h3_conv_rss"] = Cifra(pct(cv.convertidas.get("RSS", 0), cv.enviadas.get("RSS", 0)), q, (10,))
    c["h3_conv_secop"] = Cifra(
        pct(cv.convertidas.get("SECOP II", 0), cv.enviadas.get("SECOP II", 0)), q, (10,))
    dr = m.descartes_de_fuente(sesion, CORRIDA_PUBLICADA, "RSS", "sin_implicacion_inmobiliaria")
    c["h3_desc_rss"] = Cifra(f"{entero(dr.con_motivo)} de {entero(dr.total)}",
                             "mediciones.descartes_de_fuente (motivo exacto)", (10,))
    cr = m.consolidados_que_cruzan(sesion, CORRIDA_PUBLICADA, "RSS", "SECOP II")
    c["h3_cruces"] = Cifra(f"{cr.cruzan} de {cr.consolidados}",
                           "mediciones.consolidados_que_cruzan", (10,))
    v10, v7 = m.volumen(sesion, 10), m.volumen(sesion, 7)
    c["h3_vol_10"] = Cifra(f"{entero(v10.insights)} insights y {entero(v10.evidencias)} evidencias",
                           "mediciones.volumen", (10,))
    c["h3_evid_7"] = Cifra(entero(v7.evidencias), "mediciones.volumen", (7,))

    # --- H4 ----------------------------------------------------------------
    tz = m.traza_informe(sesion, INFORME, p.ruta_snapshot)
    q = f"mediciones.traza_informe (informe {INFORME}, auditoría §4.7)"
    c["h4_insights"] = Cifra(f"{tz.sin_fallo} de {tz.insights}", q, (CORRIDA_PUBLICADA, SCORING_PUBLICADA))
    c["h4_tipos"] = Cifra(f"{tz.consolidados} consolidados y {tz.directos} directos", q, (CORRIDA_PUBLICADA,))
    c["h4_citas"] = Cifra(f"{entero(tz.citas_localizables)} de {entero(tz.citas)}", q, (CORRIDA_PUBLICADA,))
    c["h4_snapshot"] = Cifra(f"{entero(tz.senales_iguales_al_snapshot)} de {entero(tz.citas)}",
                             q, (CORRIDA_PUBLICADA,))
    c["h4_scores"] = Cifra(f"{tz.scores_iguales} de {tz.municipios}", q, (SCORING_PUBLICADA,))
    c["h4_fallos"] = Cifra(entero(len(tz.fallos)), q, (CORRIDA_PUBLICADA, SCORING_PUBLICADA))
    c["h4_anclado"] = Cifra("anclado por hash en `dataset_version`" if tz.snapshot_anclado
                            else "**no** coincide con ningún `dataset_version`")
    t = m.trazas(sesion)
    c["h4_trazas"] = Cifra(entero(t.total), "mediciones.trazas")
    c["h4_hash_in"] = Cifra(entero(t.con_hash_entrada), "mediciones.trazas")
    c["h4_hash_out"] = Cifra(entero(t.con_hash_salida), "mediciones.trazas")
    ds = m.descartes(sesion)
    c["h4_desc_decl"] = Cifra(entero(ds.declarados), "mediciones.descartes")
    c["h4_desc_nodecl"] = Cifra(entero(ds.no_declarados), "mediciones.descartes")
    c["h4_prompts"] = Cifra(lista([f"{a} {v}" for a, v in m.prompts_registrados(sesion)]),
                            "mediciones.prompts_registrados (version_prompt)")

    # --- H5 ----------------------------------------------------------------
    consumo = m.consumo_por_agente(sesion)
    cla, cor = consumo["clasificador"], consumo["correlacionador"]
    tarifas = costo.leer_tarifas(p.ruta_tarifas)
    t_cla = tarifas[m.modelo_de(sesion, "clasificador")]
    t_cor = tarifas[m.modelo_de(sesion, "correlacionador")]
    nac = costo.proyectar(*costo.escenario_anual_nacional(),
                          (cor.tokens_entrada, cor.tokens_salida), cor.llamadas, t_cla, t_cor)
    pil = costo.proyectar(*costo.escenario_anual_piloto(),
                          (cor.tokens_entrada, cor.tokens_salida), cor.llamadas, t_cla, t_cor)
    c["h5_nacional"] = Cifra(entero(costo.MUNICIPIOS_NACIONAL), "costo.MUNICIPIOS_NACIONAL (PRD §1)")
    c["h5_constante_quincena"] = Cifra(
        entero(costo.SENALES_POR_QUINCENA_18),
        "costo.SENALES_POR_QUINCENA_18 — constante sin productor")
    q = "costo.proyectar sobre consumo_por_agente y config/tarifas.json"
    c["h5_corr"] = Cifra(entero(round(nac.correlacionador)), q)
    c["h5_clas"] = Cifra(entero(round(nac.clasificador)), q)
    c["h5_total_k1"] = Cifra(entero(round(nac.total(1.0))), q)
    c["h5_piloto"] = Cifra(decimal(pil.total(1.0)), q)
    c["h5_parte_corr"] = Cifra(f"{decimal(100 * nac.parte_correlacionador(1.0))} %", q)
    filas_c = ["| Agente | Despliegue | Llamadas | Tokens de entrada | Tokens de salida | Minutos |",
               "|---|---|---:|---:|---:|---:|"]
    for agente, cs in sorted(consumo.items()):
        filas_c.append(f"| {agente} | `{m.modelo_de(sesion, agente)}` | {entero(cs.llamadas)} | "
                       f"{entero(cs.tokens_entrada)} | {entero(cs.tokens_salida)} | "
                       f"{decimal(cs.minutos)} |")
    c["h5_tabla_consumo"] = Cifra("\n".join(filas_c), "mediciones.consumo_por_agente", bloque=True)
    c1 = m.consumo_de_ciclo(sesion, 1)
    c["h5_ciclo1"] = Cifra(
        f"{entero(c1.llamadas)} llamadas, {entero(c1.tokens_entrada)} tokens de entrada y "
        f"{entero(c1.tokens_salida)} de salida, en {decimal(c1.minutos)} minutos",
        "mediciones.consumo_de_ciclo (ciclo 1)")
    pasan, total_secop = m.senales_tras_prefiltro(sesion)
    c["h5_prefiltro"] = Cifra(f"{entero(pasan)} de {entero(total_secop)}",
                              "mediciones.senales_tras_prefiltro (reglas/prefiltro.clasificar)")
    dias = sum(inv.dias_por_ciclo.values())
    c["h5_dias_snapshot"] = Cifra(entero(dias), "mediciones.inventario (días de los 3 ciclos)")
    c["h5_tasa_diaria"] = Cifra(decimal(pasan / dias * 14),
                                "senales_tras_prefiltro ÷ días del snapshot × 14")

    # --- Hallazgos ---------------------------------------------------------
    c["hz_motivos"] = Cifra(
        lista([f"`{mo}` {entero(n)}" for mo, n in m.motivos_de_descarte(sesion, 3)]),
        "mediciones.motivos_de_descarte (motivo exacto)")
    crudos = [m.valor_crudo(sesion, x, APARTADO, "F4") for x in SCORING_VIGENTES]
    if None in crudos:
        texto_f4 = "sin dato en alguna corrida"
    elif len(set(crudos)) == 1:
        texto_f4 = f"{decimal(crudos[0])} % en los tres ciclos"
    else:
        texto_f4 = lista([f"{decimal(v)} %" for v in crudos])
    c["hz_f4_apartado"] = Cifra(
        texto_f4,
        "mediciones.valor_crudo (F4, Apartadó)", SCORING_VIGENTES)
    const_f4, total_m = m.factor_constante(sesion, list(SCORING_VIGENTES), "F4")
    c["hz_f4_constante"] = Cifra(f"{const_f4} de {total_m}", "mediciones.factor_constante (F4)",
                                 SCORING_VIGENTES)
    varian = []
    for f in ("F1", "F3", "F5"):
        k, n = m.factor_constante(sesion, list(SCORING_VIGENTES), f)
        varian.append(f"{f} en {n - k} de {n}")
    c["hz_f_varian"] = Cifra(lista(varian), "mediciones.factor_constante", SCORING_VIGENTES)
    filas_t = ["| Ciclo | Antes (corrida) | Después (corrida) |", "|---:|---|---|"]
    usadas_t = []
    for ciclo, antes, despues in TOP_ANTES_DESPUES:
        filas_t.append(f"| {ciclo} | {lista(m.top(sesion, antes))} ({antes}) | "
                       f"{lista(m.top(sesion, despues))} ({despues}) |")
        usadas_t += [antes, despues]
    c["hz_top_tabla"] = Cifra("\n".join(filas_t), "mediciones.top", tuple(usadas_t), bloque=True)
    fr = m.fracciones_informadas(sesion, SCORING_PUBLICADA)
    valores = sorted(set(round(v, 4) for v in fr.values()))
    c["hz_fracciones"] = Cifra(lista([f"{decimal(100 * v)} %" for v in valores]),
                               "mediciones.fracciones_informadas", (SCORING_PUBLICADA,))
    bajas = sorted(nom[d] for d, v in fr.items() if v < 0.5)
    c["hz_fraccion_baja"] = Cifra(f"{len(bajas)}: {lista(bajas)}",
                                  "mediciones.fracciones_informadas (< 50 %)", (SCORING_PUBLICADA,))
    publicados = m.municipios_del_informe(sesion, INFORME)
    filas_5 = ["| Puesto | Municipio | Score | Fuentes |", "|---:|---|---:|---|"]
    for mp in publicados[:5]:
        filas_5.append(f"| {mp.puesto} | {mp.nombre} | {decimal(mp.score, 4)} | {mp.fuentes} |")
    c["hz_top5"] = Cifra("\n".join(filas_5), f"mediciones.municipios_del_informe (payload del informe {INFORME})",
                         bloque=True)
    ib = next(x for x in publicados if x.divipola == IBAGUE)
    c["hz_ibague_dias"] = Cifra(f"{ib.dias_cubiertos} de {ib.dias_ventana}",
                                f"mediciones.municipios_del_informe (cobertura, informe {INFORME})")
    directos, consolidados = m.insights_validados_de_fuente(sesion, 10, BARRANQUILLA, "RSS")
    c["hz_barranquilla"] = Cifra(
        f"{directos + consolidados} ({directos} directos y {consolidados} consolidados)",
        "mediciones.insights_validados_de_fuente (Barranquilla, RSS)", (10,))

    # --- Anexo CA-M2.1 ------------------------------------------------------
    for clave, corrida in (("m21_7", 7), ("m21_8", 8), ("m21_10", 10)):
        val, sen = m.reduccion_clasificador(sesion, corrida)
        c[clave] = Cifra(f"{decimal(100 * (1 - val / sen))} % ({entero(val)} validados de "
                         f"{entero(sen)} señales)", "mediciones.reduccion_clasificador", (corrida,))
    return c


# ---------------------------------------------------------------------------
# Renderizar
# ---------------------------------------------------------------------------

class PlantillaIncompleta(ValueError):
    pass


def renderizar(plantilla: str, cifras: dict[str, Cifra], commit: str) -> str:
    """Llena los huecos. Falla si sobra o falta cualquiera de los dos lados."""
    pedidos = set(HUECO.findall(plantilla))
    faltan = sorted(pedidos - set(cifras))
    sobran = sorted(set(cifras) - pedidos)
    if faltan or sobran:
        raise PlantillaIncompleta(f"huecos sin cifra: {faltan}; cifras sin hueco: {sobran}")
    salida = HUECO.sub(lambda mt: cifras[mt.group(1)].pintar(commit), plantilla)
    return salida.rstrip("\n") + "\n"


def generar(sesion: Session, p: Parametros, plantilla: str | None = None) -> str:
    texto = plantilla if plantilla is not None else PLANTILLA.read_text(encoding="utf-8")
    return renderizar(texto, medir(sesion, p), p.commit)
