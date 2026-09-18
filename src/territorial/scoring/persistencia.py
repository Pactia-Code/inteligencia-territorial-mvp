"""Escritura append-only del scoring.

**Nada se sobrescribe.** Cada ejecución inserta una `corrida_scoring` nueva con
sus filas colgando de ella. Antes el score vivía bajo
`uq_score_ciclo_municipio`, así que un recálculo pisaba el ranking anterior en
su sitio: un informe publicado empezaba a mostrar un orden distinto del que las
gerencias calificaron, sin forma de reconstruir el original. Eso rompe H4, que
es bloqueante.

`tipo_corrida` se decide **aquí** y no en el llamador. El invariante vive donde
vive el dato, de modo que cualquier punto de entrada futuro queda protegido sin
tener que acordarse de comprobarlo.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from territorial.almacen.modelos import CorridaScoring, Municipio
from territorial.almacen.modelos import ScoreMunicipio as FilaScore
from territorial.scoring.ranking import ResultadoCiclo

log = logging.getLogger(__name__)

# Se sube a mano cuando cambia la fórmula, no los pesos.
#
#   v1  Como se corrió hasta el 2026-09-18.
#   v2  Arreglo de F5 (pendiente A7): la densidad mediática se divide por la
#       ventana del ciclo y no por los días cubiertos, que salían solo de
#       SECOP. Ni un peso cambió, así que la huella no se movió: **de no
#       subirla a mano, dos algoritmos distintos habrían quedado
#       indistinguibles**, que es justo lo que este campo existe para evitar.
VERSION_ALGORITMO = "v2"


def huella_pesos(pesos: dict[str, float]) -> str:
    """8 caracteres del sha256 de los pesos ordenados.

    Automático, a diferencia de `VERSION_ALGORITMO`: se mueve solo cuando los
    pesos cambian, sin depender de que nadie se acuerde.
    """
    crudo = json.dumps(pesos, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(crudo.encode()).hexdigest()[:8]


def version_scoring(pesos: dict[str, float]) -> str:
    return f"{VERSION_ALGORITMO}+{huella_pesos(pesos)}"


def _corte(ultimas: list[date | None]) -> tuple[date | None, int]:
    """Mínimo sobre las fechas que existen. Devuelve (corte, cuántas faltan).

    Sobre los municipios **que tienen fecha**, no sobre todos: propagar la
    ausencia al conjunto dejaría el ciclo 3 siempre en NULL por Barranquilla,
    Armenia y Cartagena, que tienen noticias hasta agosto pero no contratación.
    Sería el mismo error que el defecto de F5 — confundir ausencia de SECOP con
    ausencia de datos — y volvería inútil un campo de auditoría en un tercio de
    los ciclos.
    """
    con_fecha = [f for f in ultimas if f is not None]
    return (min(con_fecha) if con_fecha else None, len(ultimas) - len(con_fecha))


def guardar(sesion_bd: Session, resultado: ResultadoCiclo) -> CorridaScoring:
    """Inserta una corrida nueva con sus scores. Devuelve la corrida.

    El llamador necesita la corrida —no un conteo— porque es de donde sale
    `informe.id_corrida` al publicar.
    """
    objetivo = sorted(
        d for (d,) in sesion_bd.execute(select(Municipio.divipola)).all()
    )
    cohorte = sorted(s.divipola for s in resultado.scores)
    completa = set(cohorte) >= set(objetivo)

    ultimas = [s.ultima_fecha_captura for s in resultado.scores]
    corte, faltantes = _corte(ultimas)
    sin_fecha = sorted(
        s.divipola for s in resultado.scores if s.ultima_fecha_captura is None
    )

    corrida = CorridaScoring(
        id_ciclo=resultado.id_ciclo,
        tipo_corrida="completa" if completa else "parcial",
        ventana_desde=resultado.ventana_desde,
        ventana_hasta=resultado.ventana_hasta,
        fecha_corte_cohorte=corte,
        municipios_sin_fecha=sin_fecha,
        corte_por_fuente=dict(resultado.corte_por_fuente or {}),
        municipios_objetivo=objetivo,
        municipios_en_cohorte=cohorte,
        version_scoring=version_scoring(resultado.juego_pesos.pesos),
        pesos=dict(resultado.juego_pesos.pesos),
    )
    sesion_bd.add(corrida)
    sesion_bd.flush()  # para que las filas tengan a qué apuntar

    for s in resultado.scores:
        sesion_bd.add(
            FilaScore(
                id_corrida=corrida.id,
                divipola=s.divipola,
                score=s.score,
                ranking=s.ranking,
                factores={
                    "fraccion_informada": s.fraccion_informada,
                    "no_priorizable": s.no_priorizable,
                    "motivo_no_priorizable": s.motivo_no_priorizable,
                    "aportes": [a.a_dict() for a in s.aportes],
                },
                dias_cubiertos=s.dias_cubiertos,
                dias_ventana=s.dias_ventana,
                sin_cobertura=s.sin_cobertura,
                ultima_fecha_captura=s.ultima_fecha_captura,
            )
        )
    sesion_bd.flush()

    if not completa:
        # No falla ni se salta: inserta y deja constancia de qué se recalculó y
        # qué arrastra datos previos.
        arrastran = sorted(set(objetivo) - set(cohorte))
        log.warning(
            "Corrida %s del ciclo %s es PARCIAL: se recalcularon %d de %d municipios. "
            "Los otros %d arrastran datos de corridas anteriores: %s. "
            "Ninguna vista de gerencia debe leer esta corrida.",
            corrida.id, resultado.id_ciclo, len(cohorte), len(objetivo),
            len(arrastran), arrastran,
        )
    if faltantes:
        log.warning(
            "Corrida %s: %d de %d municipios sin fecha de SECOP (%s). El corte de "
            "cohorte (%s) se calculó sobre los que sí la tienen.",
            corrida.id, faltantes, len(ultimas), sin_fecha, corte,
        )

    return corrida
