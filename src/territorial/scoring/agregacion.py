"""Del almacén a las entradas del score.

Aquí vive el único código de M5 que conoce el ORM. `factores.py` y `ranking.py`
trabajan sobre dataclasses planas, igual que el validador: así se pueden probar
con datos escritos a mano y sin base de datos de por medio.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from territorial.almacen.modelos import Calificacion, Insight, Municipio, SenalCruda
from territorial.config import Config, obtener_config
from territorial.reglas.cobertura import calcular
from territorial.reglas.prefiltro import es_obra
from territorial.scoring.factores import EntradaMunicipio

# D1: Bing es contexto cualitativo. No origina insights y tampoco puntúa.
FUENTE_NOTICIAS = "RSS"
FUENTE_CONTRATOS = "SECOP II"


def _valor(datos: dict | None) -> float:
    """Valor del contrato, tolerando que falte o venga como texto."""
    if not datos:
        return 0.0
    bruto = datos.get("valor")
    if bruto is None:
        return 0.0
    try:
        return float(bruto)
    except (TypeError, ValueError):
        return 0.0


def _objeto(datos: dict | None) -> str:
    return (datos or {}).get("objeto") or ""


def _area_elic(elic: dict | None) -> float | None:
    """Área de referencia del piso de D4: la del año más reciente que traiga.

    Se elige el año más reciente porque la variación se calcula contra él y es
    el que dice si la base sigue siendo pequeña hoy.
    """
    if not elic:
        return None
    anios = sorted((k for k in elic if k.startswith("anio_")), reverse=True)
    for clave in anios:
        bloque = elic.get(clave) or {}
        area = bloque.get("area_real_m2")
        if area is not None:
            return float(area)
    return None


def cortes_por_fuente(
    sesion_bd: Session,
    id_ciclo: int,
    config: Config | None = None,
) -> dict[str, dict]:
    """Hasta cuándo llega cada fuente en la cohorte, por separado.

    **Es informativo y no alimenta ningún factor.** `Cobertura.ultima_fecha`
    sigue siendo solo SECOP II y sigue siendo lo único que entra en F1–F3;
    esta función se limita a añadir la foto por fuente.

    Existe porque `fecha_corte_cohorte` se computa solo con SECOP, y eso
    provoca una pregunta legítima al leer una corrida meses después: «¿por qué
    dice enero si hay noticias de junio?». Medido sobre el snapshot, el corte
    difiere entre SECOP y el resto de fuentes en 2 de los 3 ciclos — casi cinco
    meses en el ciclo 3.

    Mismo criterio que `fecha_corte_cohorte`: por cada fuente, el **mínimo** de
    la última fecha de cada municipio, sobre los que tienen fecha. Se guarda
    también cuántos la tienen, para que un corte apoyado en un solo municipio
    no se lea igual que uno apoyado en dieciocho.

    Bing aparece con corte `None`: llega sin fecha por definición (D1), y verlo
    explícito vale más que omitirlo.
    """
    cfg = config or obtener_config()
    ventanas = cfg.ventanas_ciclo
    if id_ciclo not in ventanas:
        raise ValueError(f"ciclo {id_ciclo} fuera de las ventanas de D2: {sorted(ventanas)}")
    desde, hasta = ventanas[id_ciclo]

    # Última fecha de cada (fuente, municipio). Son pocas filas: 4 fuentes por
    # 18 municipios como mucho.
    filas = sesion_bd.execute(
        select(
            SenalCruda.fuente,
            SenalCruda.divipola,
            func.max(SenalCruda.fecha_publicacion),
        )
        .where(
            SenalCruda.id_ciclo == id_ciclo,
            SenalCruda.fecha_publicacion >= desde,
            SenalCruda.fecha_publicacion < hasta,
        )
        .group_by(SenalCruda.fuente, SenalCruda.divipola)
    ).all()

    fuentes_presentes = set(
        sesion_bd.scalars(
            select(SenalCruda.fuente).where(SenalCruda.id_ciclo == id_ciclo).distinct()
        ).all()
    )

    ultimas: dict[str, list[date]] = {f: [] for f in fuentes_presentes}
    for fuente, _divipola, ultima in filas:
        if ultima is not None:
            ultimas.setdefault(fuente, []).append(
                ultima if isinstance(ultima, date) else date.fromisoformat(str(ultima)[:10])
            )

    return {
        fuente: {
            "corte": min(fechas).isoformat() if fechas else None,
            "municipios_con_fecha": len(fechas),
        }
        for fuente, fechas in sorted(ultimas.items())
    }


def entradas_del_ciclo(
    sesion_bd: Session,
    id_ciclo: int,
    config: Config | None = None,
) -> list[EntradaMunicipio]:
    """Construye una entrada por municipio para el ciclo dado.

    Los municipios sin una sola señal en el ciclo también entran: excluirlos
    los sacaría del ranking sin decir por qué, y D4 insiste en que ausencia de
    dato no es ausencia de actividad.
    """
    cfg = config or obtener_config()
    ventanas = cfg.ventanas_ciclo
    if id_ciclo not in ventanas:
        raise ValueError(f"ciclo {id_ciclo} fuera de las ventanas de D2: {sorted(ventanas)}")

    desde, hasta = ventanas[id_ciclo]
    municipios = sesion_bd.scalars(select(Municipio).order_by(Municipio.divipola)).all()

    # Una sola pasada por las señales del ciclo, y otra por las de los ciclos
    # previos para F3. Con 20.030 filas cabe en memoria de sobra.
    senales = sesion_bd.scalars(
        select(SenalCruda).where(SenalCruda.id_ciclo == id_ciclo)
    ).all()
    previas = (
        sesion_bd.scalars(select(SenalCruda).where(SenalCruda.id_ciclo < id_ciclo)).all()
        if id_ciclo > 1
        else []
    )

    acumulado: dict[str, dict] = {
        m.divipola: {
            "n_secop": 0,
            "n_obra": 0,
            "valor_obra": 0.0,
            "n_noticias": 0,
            "fechas": [],
        }
        for m in municipios
    }

    for s in senales:
        caja = acumulado.get(s.divipola)
        if caja is None:
            continue  # señal de un municipio fuera del MVP; ver pendiente A3
        if s.fuente == FUENTE_CONTRATOS:
            caja["n_secop"] += 1
            if s.fecha_publicacion:
                caja["fechas"].append(s.fecha_publicacion)
            if es_obra(_objeto(s.datos)):
                caja["n_obra"] += 1
                caja["valor_obra"] += _valor(s.datos)
        elif s.fuente == FUENTE_NOTICIAS:
            caja["n_noticias"] += 1

    # --- Ciclos previos, solo para F3 ---
    previo: dict[str, dict] = {
        m.divipola: {"n_obra": 0, "fechas_por_ciclo": {}} for m in municipios
    }
    for s in previas:
        caja = previo.get(s.divipola)
        if caja is None or s.fuente != FUENTE_CONTRATOS:
            continue
        if s.fecha_publicacion:
            caja["fechas_por_ciclo"].setdefault(s.id_ciclo, []).append(s.fecha_publicacion)
        if es_obra(_objeto(s.datos)):
            caja["n_obra"] += 1

    # --- Calificaciones de ciclos anteriores, para F6 ---
    calificaciones: dict[str, list[tuple[str, float]]] = {}
    if id_ciclo > 1:
        filas = sesion_bd.execute(
            select(Insight.divipola, Calificacion.id_gerencia, Calificacion.valor)
            .join(Calificacion, Calificacion.id_insight == Insight.id)
            .where(Insight.id_ciclo < id_ciclo)
        ).all()
        for divipola, gerencia, valor in filas:
            calificaciones.setdefault(divipola, []).append((gerencia, float(valor)))

    entradas: list[EntradaMunicipio] = []
    for m in municipios:
        caja = acumulado[m.divipola]
        cobertura = calcular(m.divipola, id_ciclo, desde, hasta, caja["fechas"])

        dias_previos = _dias_cubiertos_previos(
            m.divipola, previo[m.divipola]["fechas_por_ciclo"], ventanas, id_ciclo
        )

        elic = m.elic or {}
        entradas.append(
            EntradaMunicipio(
                divipola=m.divipola,
                id_ciclo=id_ciclo,
                cobertura=cobertura,
                n_secop=caja["n_secop"],
                n_obra=caja["n_obra"],
                valor_obra=caja["valor_obra"],
                n_obra_previa=previo[m.divipola]["n_obra"],
                dias_cubiertos_previos=dias_previos,
                n_noticias=caja["n_noticias"],
                variacion_elic_pct=elic.get("variacion_area_real_pct"),
                area_elic_m2=_area_elic(elic),
                calificaciones_previas=calificaciones.get(m.divipola, []),
            )
        )

    return entradas


def _dias_cubiertos_previos(
    divipola: str,
    fechas_por_ciclo: dict[int, list[date]],
    ventanas: dict[int, tuple[date, date]],
    id_ciclo: int,
) -> int:
    """Suma de días cubiertos en los ciclos anteriores.

    Se suma ciclo a ciclo y no de corrido porque la cobertura se define dentro
    de una ventana: un municipio truncado en el ciclo 2 no debe parecer cubierto
    porque el ciclo 1 sí lo estuviera.
    """
    total = 0
    for ciclo_previo in range(1, id_ciclo):
        if ciclo_previo not in ventanas:
            continue
        desde, hasta = ventanas[ciclo_previo]
        cob = calcular(
            divipola, ciclo_previo, desde, hasta, fechas_por_ciclo.get(ciclo_previo, [])
        )
        total += cob.dias_cubiertos
    return total
