"""M5 — Score, ranking y top 3 (PRD §5, CA-M5.1 a CA-M5.5).

  CA-M5.1  Ranking de los municipios del ciclo con score explicable.
  CA-M5.2  Features objetivas + calificaciones previas ponderadas por gerencia.
           **Modificado por D4**: las features objetivas son de composición y
           tasa sobre SECOP y ELIC, no de TerriData. F6 cumple la cláusula de
           calificaciones íntegra.
  CA-M5.3  Pesos configurables sin cambio de código. Ver `pesos.py`.
  CA-M5.4  Top 3 fijo.
  CA-M5.5  Para cada municipio del top 3, qué factores lo empujaron.

Esto es **capa determinista**: ni un LLM toca el score. Las cifras del informe
salen de aquí, y CA-M6.3 las exige así — ninguna cifra publicada puede venir
del modelo.


El umbral de información — añadido, no está en D4
--------------------------------------------------
D4 manda redistribuir el peso de los factores sin cobertura «proporcionalmente
entre los factores restantes», para que un municipio truncado no se puntúe como
cero. Corriéndolo sobre el snapshot aparece el efecto contrario:

  Ciclo 3, Armenia:  0 de 239 días cubiertos. Pierde F1, F2, F3 y F6. Su único
                     factor vivo es F4, que pasa a valer el 100% del score. Como
                     su F4 es el máximo de la cohorte, normaliza a 1,0 y Armenia
                     sale con **score perfecto y segundo puesto**.
  Ciclo 3, Ibagué:   3 de 239 días. Mismo mecanismo, primer puesto.

La redistribución, pensada para no castigar, acaba premiando al que no tiene
datos. Y el factor que los sostiene es el peor posible para eso: ELIC es
constante en los 3 ciclos (D2/R3), así que el informe estaría priorizando dos
municipios por un número que no cambia de un ciclo a otro.

La guarda: se registra qué fracción del peso nominal tenía datos y, por debajo
de `Config.umbral_informacion` (50% por defecto), el municipio **queda fuera del
top 3 pero no fuera del ranking**. No se le pone cero —la regla de D4 se
respeta—, simplemente no ocupa un puesto del informe, donde CA-M6.1 obliga a
justificar la priorización con algo que aquí no existe.

Los ciclos 1 y 2 no se ven afectados: allí la información va del 62% al 100%.

**Esto es una decisión de implementación, no de D4.** El umbral es configurable
y queda para confirmar con Analítica junto al pendiente A1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from territorial.config import Config, obtener_config
from territorial.reglas.cobertura import redistribuir_pesos
from territorial.scoring.factores import (
    EntradaMunicipio,
    ValorFactor,
    crudos,
    normalizar_cohorte,
)
from territorial.scoring.pesos import DESCRIPCIONES, JuegoDePesos, del_ciclo

TOPE_TOP = 3  # CA-M5.4: top 3 fijo, no top N por umbral.


@dataclass(frozen=True)
class Aporte:
    """Lo que un factor le puso al score de un municipio. Es CA-M5.5."""

    codigo: str
    descripcion: str
    crudo: float | None
    normalizado: float | None
    peso: float
    aporte: float
    sin_cobertura: bool
    motivo: str

    def a_dict(self) -> dict:
        """Forma que se guarda en `score_municipio.factores` (JSON portátil)."""
        return {
            "codigo": self.codigo,
            "descripcion": self.descripcion,
            "crudo": self.crudo,
            "normalizado": self.normalizado,
            "peso": self.peso,
            "aporte": self.aporte,
            "sin_cobertura": self.sin_cobertura,
            "motivo": self.motivo,
        }


@dataclass(frozen=True)
class ScoreMunicipio:
    divipola: str
    id_ciclo: int
    score: float
    aportes: list[Aporte]
    dias_cubiertos: int
    dias_ventana: int
    sin_cobertura: bool
    # Fracción del peso nominal del ciclo que sí tenía datos. Un municipio con
    # 0,18 sacó su score de un solo factor: el resto se redistribuyó.
    fraccion_informada: float = 1.0
    # No entra al top 3 por apoyarse en muy pocos datos. Sigue en el ranking.
    no_priorizable: bool = False
    motivo_no_priorizable: str = ""
    # Última fecha observada de **este** municipio, no de la cohorte. Solo
    # SECOP II: es `Cobertura.ultima_fecha`, la misma que alimenta F1-F3.
    ultima_fecha_captura: date | None = None
    ranking: int | None = None

    @property
    def factores_que_empujaron(self) -> list[Aporte]:
        """Los factores con aporte real, de mayor a menor. CA-M5.5."""
        return sorted(
            (a for a in self.aportes if a.aporte > 0),
            key=lambda a: a.aporte,
            reverse=True,
        )

    @property
    def factores_redistribuidos(self) -> list[Aporte]:
        return [a for a in self.aportes if a.sin_cobertura]

    def explicar(self) -> str:
        """Texto plano del desglose. Lo consume el informe; no lo escribe un LLM."""
        lineas = [f"{self.divipola} · ciclo {self.id_ciclo} · score {self.score:.4f}"]
        if self.ranking:
            lineas[0] += f" · puesto {self.ranking}"
        lineas.append(
            f"  cobertura: {self.dias_cubiertos}/{self.dias_ventana} días"
            + ("  [BAJO UMBRAL]" if self.sin_cobertura else "")
        )
        lineas.append(f"  score informado por el {self.fraccion_informada:.0%} del peso nominal")
        if self.no_priorizable:
            lineas.append(f"  FUERA DEL TOP 3 — {self.motivo_no_priorizable}")
        for a in self.factores_que_empujaron:
            lineas.append(
                f"  {a.codigo}  aporta {a.aporte:.4f}  "
                f"(norm {a.normalizado:.3f} × peso {a.peso:.0%})  crudo {a.crudo:,.4f}"
            )
        for a in self.factores_redistribuidos:
            lineas.append(f"  {a.codigo}  sin cobertura — {a.motivo}")
        return "\n".join(lineas)


@dataclass(frozen=True)
class ResultadoCiclo:
    id_ciclo: int
    scores: list[ScoreMunicipio]  # ordenados, mejor primero
    juego_pesos: JuegoDePesos
    # Ventana del ciclo, declarada por configuración (D2).
    ventana_desde: date | None = None
    ventana_hasta: date | None = None
    # {fuente: última fecha observada}. Va aparte de `fecha_corte_cohorte`
    # porque responde sola por qué una corrida dice enero si hay noticias de
    # junio. No alimenta ningún factor.
    corte_por_fuente: dict = field(default_factory=dict)

    @property
    def top(self) -> list[ScoreMunicipio]:
        """CA-M5.4 — top 3 fijo, saltando los no priorizables.

        Se respeta el orden del ranking; lo único que cambia es que un
        municipio cuyo score se apoya en muy pocos datos cede el puesto al
        siguiente. Sigue apareciendo en `scores` con su posición real.
        """
        return [s for s in self.scores if not s.no_priorizable][:TOPE_TOP]

    @property
    def excluidos_del_top(self) -> list[ScoreMunicipio]:
        """Los que habrían entrado al top 3 y no entraron, con el motivo."""
        umbral = TOPE_TOP + len([s for s in self.scores if s.no_priorizable])
        return [s for s in self.scores[:umbral] if s.no_priorizable]

    def __str__(self) -> str:
        lineas = [f"Ciclo {self.id_ciclo} — {len(self.scores)} municipios"]
        lineas.append(f"Pesos: {self.juego_pesos}")
        en_top = {s.divipola for s in self.top}
        for s in self.scores:
            marca = "★" if s.divipola in en_top else " "
            aviso = "  (cobertura baja)" if s.sin_cobertura else ""
            if s.no_priorizable:
                aviso += "  [no priorizable]"
            lineas.append(f" {marca} {s.ranking:>2}. {s.divipola}  {s.score:.4f}{aviso}")
        return "\n".join(lineas)


def _aportes(
    factores: dict[str, ValorFactor], pesos: dict[str, float]
) -> tuple[float, list[Aporte], float]:
    """Aplica los pesos, redistribuyendo los de los factores sin cobertura.

    Devuelve (score, aportes, fracción informada). La fracción es la porción
    del peso nominal que de verdad tenía datos, y es lo que permite distinguir
    un 0,9 sólido de un 0,9 sacado de un único factor.
    """
    # Solo se consideran los factores que este ciclo pondera. Un factor que D4
    # no pondera en el ciclo 1 (F3, F6) no es "sin cobertura": no aplica.
    relevantes = {c: f for c, f in factores.items() if c in pesos}

    sin_cobertura = {c for c, f in relevantes.items() if not f.disponible}
    con_cobertura = set(relevantes) - sin_cobertura

    if not con_cobertura:
        # Ningún factor puntuable. Score cero y el motivo queda escrito en cada
        # aporte, para que el informe pueda decir por qué y no parezca inactivo.
        aportes = [
            Aporte(
                codigo=c,
                descripcion=DESCRIPCIONES[c],
                crudo=f.crudo,
                normalizado=f.normalizado,
                peso=pesos[c],
                aporte=0.0,
                sin_cobertura=True,
                motivo=f.motivo,
            )
            for c, f in sorted(relevantes.items())
        ]
        return 0.0, aportes, 0.0

    nominal = sum(pesos.values())
    informada = sum(pesos[c] for c in con_cobertura) / nominal if nominal > 0 else 0.0

    efectivos = redistribuir_pesos(pesos, sin_cobertura)

    score = 0.0
    aportes: list[Aporte] = []
    for codigo, factor in sorted(relevantes.items()):
        if codigo in sin_cobertura:
            aportes.append(
                Aporte(
                    codigo=codigo,
                    descripcion=DESCRIPCIONES[codigo],
                    crudo=factor.crudo,
                    normalizado=None,
                    peso=0.0,  # se redistribuyó
                    aporte=0.0,
                    sin_cobertura=True,
                    motivo=factor.motivo,
                )
            )
            continue

        peso = efectivos[codigo]
        aporte = (factor.normalizado or 0.0) * peso
        score += aporte
        aportes.append(
            Aporte(
                codigo=codigo,
                descripcion=DESCRIPCIONES[codigo],
                crudo=factor.crudo,
                normalizado=factor.normalizado,
                peso=peso,
                aporte=aporte,
                sin_cobertura=False,
                motivo=factor.motivo,
            )
        )

    return score, aportes, informada


def puntuar_ciclo(
    entradas: list[EntradaMunicipio],
    id_ciclo: int,
    config: Config | None = None,
    cortes_por_fuente: dict | None = None,
) -> ResultadoCiclo:
    """Puntúa y ordena los municipios de un ciclo.

    La normalización es por cohorte, así que esto recibe el ciclo entero y no
    un municipio suelto: el score de uno depende de dónde caen los demás.
    """
    cfg = config or obtener_config()
    juego = del_ciclo(id_ciclo, cfg)

    ventana = cfg.ventanas_ciclo.get(id_ciclo, (None, None))
    if not entradas:
        return ResultadoCiclo(id_ciclo, [], juego, ventana[0], ventana[1])

    ajenas = {e.divipola for e in entradas if e.id_ciclo != id_ciclo}
    if ajenas:
        raise ValueError(f"entradas de otro ciclo en el ciclo {id_ciclo}: {sorted(ajenas)}")

    sin_normalizar = {e.divipola: crudos(e, cfg.umbral_cobertura) for e in entradas}
    normalizados = normalizar_cohorte(sin_normalizar)

    scores: list[ScoreMunicipio] = []
    for e in entradas:
        score, aportes, informada = _aportes(normalizados[e.divipola], juego.pesos)
        flojo = informada < cfg.umbral_informacion
        scores.append(
            ScoreMunicipio(
                divipola=e.divipola,
                id_ciclo=id_ciclo,
                score=score,
                aportes=aportes,
                dias_cubiertos=e.cobertura.dias_cubiertos,
                dias_ventana=e.cobertura.dias_ventana,
                sin_cobertura=e.cobertura.sin_cobertura(cfg.umbral_cobertura),
                ultima_fecha_captura=e.cobertura.ultima_fecha,
                fraccion_informada=informada,
                no_priorizable=flojo,
                motivo_no_priorizable=(
                    f"solo el {informada:.0%} del peso nominal tenía datos, "
                    f"por debajo del {cfg.umbral_informacion:.0%} exigido para el top 3"
                    if flojo
                    else ""
                ),
            )
        )

    # Desempate por DIVIPOLA: sin esto el orden dependería del de entrada y dos
    # corridas del mismo ciclo podrían dar top 3 distintos. H4 pide que una
    # corrida sea reproducible.
    scores.sort(key=lambda s: (-s.score, s.divipola))

    ordenados = [
        ScoreMunicipio(
            divipola=s.divipola,
            id_ciclo=s.id_ciclo,
            score=s.score,
            aportes=s.aportes,
            dias_cubiertos=s.dias_cubiertos,
            dias_ventana=s.dias_ventana,
            sin_cobertura=s.sin_cobertura,
            ultima_fecha_captura=s.ultima_fecha_captura,
            fraccion_informada=s.fraccion_informada,
            no_priorizable=s.no_priorizable,
            motivo_no_priorizable=s.motivo_no_priorizable,
            ranking=i,
        )
        for i, s in enumerate(scores, start=1)
    ]

    return ResultadoCiclo(
        id_ciclo,
        ordenados,
        juego,
        ventana_desde=ventana[0],
        ventana_hasta=ventana[1],
        corte_por_fuente=cortes_por_fuente or {},
    )
