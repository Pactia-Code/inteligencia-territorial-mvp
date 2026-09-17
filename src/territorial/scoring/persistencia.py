"""Guarda el resultado de M5 en `score_municipio`.

El desglose de CA-M5.5 va a la columna `factores`, que es JSON portátil: sin
operadores JSONB, o SQLite deja de servir como entorno local (regla 3 de D8).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from territorial.almacen.modelos import ScoreMunicipio as FilaScore
from territorial.scoring.ranking import ResultadoCiclo


def guardar(sesion_bd: Session, resultado: ResultadoCiclo) -> int:
    """Escribe o actualiza los scores del ciclo. Devuelve cuántas filas tocó.

    Es idempotente: `uq_score_ciclo_municipio` impide duplicar un municipio en
    un ciclo, así que recalcular sobrescribe en vez de acumular. Hace falta
    porque el score se va a recalcular cada vez que cambien los pesos, y los
    pesos son el pendiente A1.
    """
    existentes = {
        fila.divipola: fila
        for fila in sesion_bd.scalars(
            select(FilaScore).where(FilaScore.id_ciclo == resultado.id_ciclo)
        ).all()
    }

    tocadas = 0
    for s in resultado.scores:
        desglose = {
            "pesos_origen": resultado.juego_pesos.origen,
            "fraccion_informada": s.fraccion_informada,
            "no_priorizable": s.no_priorizable,
            "motivo_no_priorizable": s.motivo_no_priorizable,
            "aportes": [a.a_dict() for a in s.aportes],
        }
        fila = existentes.get(s.divipola)
        if fila is None:
            fila = FilaScore(id_ciclo=s.id_ciclo, divipola=s.divipola)
            sesion_bd.add(fila)

        fila.score = s.score
        fila.ranking = s.ranking
        fila.factores = desglose
        fila.dias_cubiertos = s.dias_cubiertos
        fila.dias_ventana = s.dias_ventana
        fila.sin_cobertura = s.sin_cobertura
        tocadas += 1

    return tocadas
