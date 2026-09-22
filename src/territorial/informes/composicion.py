"""Compone el informe de un ciclo desde el almacén. Ni una cifra del LLM.

Es la mitad determinista de M6. Lee dos corridas **congeladas** —la de scoring,
que da el orden, y la de agentes, que da el contenido— y arma el payload que M9
pinta. El Sintetizador añadirá después la prosa de CA-M6.1 en el hueco
`justificacion`, que hoy sale vacío: la parte que se puede probar sin gastar un
token se construye y se prueba entera primero.

**CA-M6.3 se cumple por construcción, no por disciplina.** Aquí no hay ninguna
llamada a un modelo. Si algún día la hay, estará en otro módulo.

**CA-M6.4 también:** cada dato del bloque de contexto viaja con su fuente y su
año, y cada evidencia con su URL y su fecha. Un informe de septiembre de 2026
que muestre déficit del censo 2018 necesita que el «2018» se vea, o alguien lo
leerá como dato de hoy.


Por qué el payload no lleva códigos de factor a la vista
--------------------------------------------------------
«Apoyado en F4+F5» es correcto y no significa nada para una gerencia
(pendiente M6-src). Cada factor viaja con su `fuente` en castellano, y además
se compone `resumen_fuentes`, una frase como **«licencias y prensa, sin
contratación»**.

La frase nombra **lo que falta**, y eso no es adorno: para Barranquilla el dato
que importa es el «sin contratación en el ciclo», no la lista de lo presente.
M9 la pinta junto al puesto y al score, con el mismo peso visual, porque si va
al pie el desglose llega tarde (pendiente M6-orden).

F1, F2 y F3 salen los tres de SECOP, así que cinco factores colapsan en tres
fuentes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from territorial.almacen.modelos import (
    ContextoMunicipal,
    CorridaAgentes,
    CorridaScoring,
    Insight,
    Municipio,
    ScoreMunicipio,
)
from territorial.config import Config, obtener_config

# CA-M6.5: la marca va en el payload, no en la plantilla, para que ninguna
# superficie pueda publicar sin ella por descuido.
AVISO_MVP = "MVP — contenido no validado por Analítica"

# De código de factor a fuente legible (M6-src). El nombre largo es para la
# ficha; el corto, para la frase de una línea.
FUENTES: dict[str, tuple[str, str]] = {
    "F1": ("contratación pública (SECOP II)", "contratación"),
    "F2": ("contratación pública (SECOP II)", "contratación"),
    "F3": ("contratación pública (SECOP II)", "contratación"),
    "F4": ("licencias de construcción (ELIC/DANE)", "licencias"),
    "F5": ("prensa", "prensa"),
    "F6": ("calificaciones de las gerencias", "calificaciones"),
}

# Orden en que se nombran las fuentes. Fijo, para que dos municipios no
# describan lo mismo con palabras en distinto orden.
ORDEN_FUENTES: tuple[str, ...] = ("contratación", "licencias", "prensa", "calificaciones")

# Las que entran en la frase de una línea: solo evidencia sobre el territorio.
# Ver `resumir_fuentes`.
FUENTES_EN_RESUMEN: tuple[str, ...] = ("contratación", "licencias", "prensa")


@dataclass(frozen=True)
class CampoContexto:
    """Un indicador estructural con su procedencia. CA-M6.4."""

    clave: str
    etiqueta: str
    valor: float | int | None
    unidad: str
    fuente: str
    anio: int | None

    def a_dict(self) -> dict:
        return {
            "clave": self.clave,
            "etiqueta": self.etiqueta,
            "valor": self.valor,
            "unidad": self.unidad,
            "fuente": self.fuente,
            "anio": self.anio,
        }


def _iso(valor: date | datetime | None) -> str | None:
    return valor.isoformat() if valor is not None else None


def campos_de_contexto(fila: ContextoMunicipal | None) -> list[dict]:
    """El bloque de contexto estructural, cada dato con fuente y año.

    **El déficit es un porcentaje de hogares, no un conteo.** TerriData no trae
    el número absoluto, así que el informe no puede decir «3.480 hogares en
    déficit» por mucho que sea la frase natural: diría algo que la fuente no
    sostiene.
    """
    if fila is None:
        return []
    campos = [
        CampoContexto("poblacion_total", "Habitantes", fila.poblacion_total,
                      "personas", "DANE, proyección", fila.anio_poblacion),
        CampoContexto("valor_agregado", "Valor agregado municipal", fila.valor_agregado,
                      "miles de millones de pesos corrientes", "DANE",
                      fila.anio_valor_agregado),
        CampoContexto("deficit_cuantitativo", "Hogares en déficit cuantitativo",
                      fila.deficit_cuantitativo, "% de hogares", "DANE, censo",
                      fila.anio_deficit),
        CampoContexto("deficit_cualitativo", "Hogares en déficit cualitativo",
                      fila.deficit_cualitativo, "% de hogares", "DANE, censo",
                      fila.anio_deficit),
        CampoContexto("avaluo_catastral_urbano", "Avalúo catastral urbano",
                      fila.avaluo_catastral_urbano,
                      "millones de pesos corrientes", "IGAC", fila.anio_catastro),
        CampoContexto("predios_urbanos", "Predios urbanos", fila.predios_urbanos,
                      "predios", "IGAC", fila.anio_catastro),
    ]
    return [c.a_dict() for c in campos if c.valor is not None]


def resumir_fuentes(presentes: set[str], ausentes: set[str]) -> str:
    """«licencias y prensa, sin contratación». Nombra también lo que falta.

    **Solo entran las fuentes territoriales**, no las calificaciones. F6 es el
    bucle de aprendizaje, no evidencia sobre el territorio, y hoy falta en los
    18 municipios porque no hay ni una calificación. Una línea que dijera «sin
    calificaciones» en los diez enseñaría al lector a saltársela, y esta línea
    es justo la que tiene que leerse (M6-orden). Sigue apareciendo en el
    desglose factor a factor, que es donde toca.
    """
    def enumerar(nombres: set[str], union: str) -> str:
        ordenados = [n for n in FUENTES_EN_RESUMEN if n in nombres]
        if len(ordenados) <= 1:
            return "".join(ordenados)
        return ", ".join(ordenados[:-1]) + f" {union} " + ordenados[-1]

    # «sin contratación ni calificaciones», no «sin contratación y ...».
    hay, falta = enumerar(presentes, "y"), enumerar(ausentes, "ni")
    if hay and falta:
        return f"{hay}, sin {falta}"
    if hay:
        return hay
    return f"sin {falta}" if falta else "sin datos"


def _factores(fila: ScoreMunicipio) -> tuple[list[dict], set[str], set[str]]:
    """Los aportes con su fuente, y qué fuentes sostienen el score y cuáles no.

    Un factor que el ciclo no pondera —F3 y F6 en el ciclo 1— no aparece en
    `aportes`, así que no cuenta ni como presente ni como ausente: no es que
    falte el dato, es que no aplica.
    """
    detalle, presentes, ausentes = [], set(), set()
    for a in (fila.factores or {}).get("aportes", []):
        largo, corto = FUENTES.get(a["codigo"], ("desconocida", "desconocida"))
        detalle.append({**a, "fuente": largo})
        (ausentes if a.get("sin_cobertura") else presentes).add(corto)
    # Una fuente con al menos un factor vivo cuenta como presente: F1 sin
    # cobertura y F2 con ella siguen siendo contratación, y sí hay contratación.
    return detalle, presentes, ausentes - presentes


def componer(
    sesion_bd: Session,
    id_corrida_scoring: int,
    id_corrida_agentes: int,
    config: Config | None = None,
    tope_calificable: int = 3,
) -> dict:
    """El informe compuesto de un ciclo, listo para que M9 lo pinte.

    Las dos corridas se pasan **explícitas** y no se resuelve «la última»: es lo
    que el informe congela y la razón de que un informe publicado se pueda
    reconstruir meses después.
    """
    corrida = sesion_bd.get(CorridaScoring, id_corrida_scoring)
    if corrida is None:
        raise ValueError(f"no existe la corrida de scoring {id_corrida_scoring}")
    agentes = sesion_bd.get(CorridaAgentes, id_corrida_agentes)
    if agentes is None:
        raise ValueError(f"no existe la corrida de agentes {id_corrida_agentes}")
    if agentes.id_ciclo != corrida.id_ciclo:
        raise ValueError(
            f"las corridas son de ciclos distintos: scoring del ciclo "
            f"{corrida.id_ciclo}, agentes del {agentes.id_ciclo}. Un informe no "
            "puede mezclar el orden de un ciclo con el contenido de otro."
        )

    nombres = {
        m.divipola: (m.nombre, m.departamento)
        for m in sesion_bd.scalars(select(Municipio)).all()
    }

    filas = sesion_bd.scalars(
        select(ScoreMunicipio)
        .where(ScoreMunicipio.id_corrida == id_corrida_scoring)
        .order_by(ScoreMunicipio.ranking)
    ).all()
    # El tope sale del Config, no de la corrida: cuántos municipios **muestra
    # el informe** es una decisión del informe, y el scoring puntúa los 18
    # siempre. Queda registrado en `calificacion.mostrados` del payload, que es
    # donde hay que mirarlo meses después.
    tope = (config or obtener_config()).tope_top
    mostrados = [
        f for f in filas if not (f.factores or {}).get("no_priorizable")
    ][:tope]

    insights_por_muni: dict[str, list[Insight]] = {}
    for ins in sesion_bd.scalars(
        select(Insight).where(
            Insight.id_corrida == id_corrida_agentes,
            Insight.estado_validacion == "validado",
        )
    ).all():
        insights_por_muni.setdefault(ins.divipola, []).append(ins)

    municipios = []
    for puesto, fila in enumerate(mostrados, start=1):
        nombre, depto = nombres.get(fila.divipola, (fila.divipola, ""))
        detalle, presentes, ausentes = _factores(fila)
        datos = fila.factores or {}
        municipios.append({
            "puesto": puesto,
            "ranking_en_la_corrida": fila.ranking,
            "divipola": fila.divipola,
            "nombre": nombre,
            "departamento": depto,
            "score": fila.score,
            "fuentes": {
                "presentes": [f for f in ORDEN_FUENTES if f in presentes],
                "ausentes": [f for f in ORDEN_FUENTES if f in ausentes],
                # M6-orden: M9 la pinta junto al puesto, no al pie.
                "resumen": resumir_fuentes(presentes, ausentes),
            },
            "factores": detalle,
            "cobertura": {
                "dias_cubiertos": fila.dias_cubiertos,
                "dias_ventana": fila.dias_ventana,
                "sin_cobertura": fila.sin_cobertura,
                "ultima_fecha_captura": _iso(fila.ultima_fecha_captura),
            },
            "fraccion_informada": datos.get("fraccion_informada"),
            "contexto": campos_de_contexto(
                sesion_bd.get(ContextoMunicipal, fila.divipola)
            ),
            # CA-M6.1: lo escribe el Sintetizador, después. Va explícito y vacío
            # para que M9 sepa que el hueco existe y no lo invente.
            "justificacion": None,
            "sugerencias": [],
            "calificable": puesto <= tope_calificable,
            "insights": [
                {
                    "id": i.id,
                    "categoria": i.categoria,
                    "resumen": i.resumen,
                    "implicacion_inmobiliaria": i.implicacion_inmobiliaria,
                    "origen": i.origen,
                    "evidencia": i.evidencia or [],
                }
                for i in insights_por_muni.get(fila.divipola, [])
            ],
        })

    return {
        "aviso": AVISO_MVP,
        "ciclo": corrida.id_ciclo,
        "ventana": {
            "desde": _iso(corrida.ventana_desde),
            "hasta": _iso(corrida.ventana_hasta),
        },
        "corridas": {
            "scoring": corrida.id,
            "agentes": agentes.id,
            "version_scoring": corrida.version_scoring,
            "version_pipeline": agentes.version_pipeline,
            "version_clasificador": agentes.version_clasificador,
            "version_correlacionador": agentes.version_correlacionador,
            "pesos": corrida.pesos,
        },
        "corte": {
            "cohorte": _iso(corrida.fecha_corte_cohorte),
            "por_fuente": corrida.corte_por_fuente,
            "municipios_sin_fecha": corrida.municipios_sin_fecha,
        },
        # M9-carga: se muestran todos, se piden los primeros. El denominador de
        # H2 sale de aquí, no de cuántos se pintaron.
        "calificacion": {
            "mostrados": len(municipios),
            "pedida_hasta_puesto": tope_calificable,
        },
        "municipios": municipios,
    }
