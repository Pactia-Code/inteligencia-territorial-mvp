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


El umbral de información: por qué existió y por qué está apagado
----------------------------------------------------------------
D4 manda redistribuir el peso de los factores sin cobertura «proporcionalmente
entre los factores restantes», para que un municipio truncado no se puntúe como
cero. Corriéndolo sobre el snapshot aparece el efecto contrario:

  Ciclo 3, Ibagué:   3 de 239 días cubiertos. Pierde F1, F2 y F3. Le quedan F4
                     y F5, su peso se redistribuye entre esos dos y sale
                     **primero del ciclo con 0,8560**. F4 es constante entre
                     ciclos (D2/R3) y F5 cuenta noticias sin verificarlas.
  Ciclo 3, Armenia:  0 de 239 días. Mismo mecanismo, segundo puesto.

La redistribución, pensada para no castigar, acaba premiando al que no tiene
datos. Durante unos días eso se resolvió **excluyéndolos**: por debajo del 50%
del peso nominal respaldado por datos, el municipio quedaba fuera del informe
aunque siguiera en el ranking.

**Desde el 2026-09-21 se resuelve al revés: exponiendo en vez de excluyendo.**
`Config.umbral_informacion` está en 0 y el informe muestra el score **junto a
los factores que lo sostienen y los que no**. Ibagué aparece primero, y al lado
se lee que F1, F2 y F3 no tienen cobertura y que su score sale de F4 y F5. Quien
lee juzga.

El cambio vino de un caso que la exclusión no sabía tratar: Barranquilla tiene
**12 insights de prensa que pasaron el validador** y quedaba invisible, porque
el sistema solo sabía decir «top 3» o nada, y «no hay suficiente información» no
es lo mismo que «aquí hay algo, pero solo lo veo por un lado» (pendiente P1).
Bajar el umbral no servía: el dato tiene un hueco —las fracciones informadas son
20,10% o 77,80%, sin nada en medio— así que cualquier umbral por debajo de 20,10%
no dispara nunca y cualquiera por encima se comporta como el 50%. No había punto
intermedio que ajustar; la decisión era tener guarda o no tenerla.

**El mecanismo se conserva entero.** `fraccion_informada` se sigue calculando y
persistiendo como dato de auditoría, `no_priorizable` sigue existiendo, y subir
el umbral por encima de 0 lo reactiva. Hay pruebas de las dos cosas.

Y el tope del informe pasa de 3 a **`Config.tope_top`, 10 por defecto**. CA-M5.4
decía «top 3 fijo»; es una desviación deliberada y queda anotada aquí.
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

# CA-M5.4 dice "top 3 fijo". Se amplía a 10 por decisión de producto del
# 2026-09-21: `Config.tope_top` manda y esto es solo el valor por defecto.
TOPE_TOP = 10


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
    # ¿Existe el dato subyacente, aunque el factor no haya puntuado? Ver
    # `factores.ValorFactor`: es lo que separa «no hay dato» de «el dato
    # existe pero la métrica no es válida sobre él».
    hay_dato: bool = True

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
            "hay_dato": self.hay_dato,
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
    # Fracción del peso nominal del ciclo respaldada por datos reales. Un
    # municipio con 0,18 está a oscuras en el 82% de las dimensiones. No es lo
    # mismo que «fracción que puntuó»: un factor con dato pero métrica no
    # fiable cuenta aquí y no en el score (ver `_aportes`).
    fraccion_informada: float = 1.0
    # Se apoya en muy pocos datos. **Desde el 2026-09-21 no excluye de nada**:
    # `Config.umbral_informacion` está en 0, así que esto siempre es False y se
    # conserva como campo de auditoría y como interruptor si se quiere volver
    # a filtrar. Lo que hace el informe en su lugar es mostrar el score junto a
    # los factores que lo sostienen y los que no.
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
            lineas.append(f"  FUERA DEL INFORME — {self.motivo_no_priorizable}")
        for a in self.factores_que_empujaron:
            lineas.append(
                f"  {a.codigo}  aporta {a.aporte:.4f}  "
                f"(norm {a.normalizado:.3f} × peso {a.peso:.0%})  crudo {a.crudo:,.4f}"
            )
        for a in self.factores_redistribuidos:
            etiqueta = "con dato, no puntúa" if a.hay_dato else "sin cobertura"
            crudo = f"  crudo {a.crudo:,.4f}" if a.crudo is not None else ""
            lineas.append(f"  {a.codigo}  {etiqueta} — {a.motivo}{crudo}")
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
    # Cuántos municipios muestra el informe de esta corrida. Se guarda en el
    # resultado y no se lee del Config al vuelo: una corrida tiene que poder
    # explicarse a sí misma meses después, aunque la configuración haya cambiado.
    tope: int = TOPE_TOP

    @property
    def top(self) -> list[ScoreMunicipio]:
        """Los municipios que muestra el informe, en orden de score.

        CA-M5.4 pedía un top 3 fijo; desde el 2026-09-21 son `self.tope` —diez
        por defecto— y **no se salta a nadie**, porque el umbral de información
        está apagado. Si se reactivara, un municipio con muy pocos datos cedería
        el puesto al siguiente y seguiría apareciendo en `scores` con su
        posición real.
        """
        return [s for s in self.scores if not s.no_priorizable][: self.tope]

    @property
    def excluidos_del_top(self) -> list[ScoreMunicipio]:
        """Los que habrían entrado al informe y no entraron, con el motivo.

        Vacío mientras el umbral esté apagado, que es lo normal hoy.
        """
        umbral = self.tope + len([s for s in self.scores if s.no_priorizable])
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

    # La fracción informada mide **dato**, no puntuación (decisión 2 de
    # Analítica). Un factor con dato real cuenta aunque su métrica no sea
    # fiable y su peso se redistribuya: castigarlo en el score y otra vez en
    # la fracción era penalizar dos veces el mismo hecho.
    #
    # El único factor que hoy puede estar en ese estado es F4 bajo el piso de
    # área, y su peso nominal (30% en el ciclo 1, 18% en los otros) está por
    # debajo del umbral. Así que un municipio no puede volverse priorizable
    # solo con factores que no puntúan.
    nominal = sum(pesos.values())
    con_dato = {c for c, f in relevantes.items() if f.disponible or f.hay_dato}
    informada = sum(pesos[c] for c in con_dato) / nominal if nominal > 0 else 0.0

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
                hay_dato=f.hay_dato,
                motivo=f.motivo,
            )
            for c, f in sorted(relevantes.items())
        ]
        return 0.0, aportes, informada

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
                    hay_dato=factor.hay_dato,
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
        return ResultadoCiclo(id_ciclo, [], juego, ventana[0], ventana[1],
                              tope=cfg.tope_top)

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
                    f"por debajo del {cfg.umbral_informacion:.0%} exigido"
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
        tope=cfg.tope_top,
    )
