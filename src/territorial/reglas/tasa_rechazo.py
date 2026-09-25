"""La tasa de rechazo del validador, **desglosada por regla**. F0b.3 (H-028, H-010).

**Qué mide, y qué no.** Es fidelidad de cita contra el contenido ingerido, no
veracidad respecto del mundo (**H-029**): una cita fiel a una fuente equivocada
pasa las siete reglas. El texto de `FRASE_H029` acompaña siempre a la cifra
—F3.1 del plan de auditoría lo exige— y no se publica una sin la otra.

**Por qué hace falta desglosarla.** R1–R7 comprueban que la evidencia sostiene
lo que el insight dice; **R8 comprueba otra cosa**: que ninguna cifra de la
prosa falte en lo que el agente recibió (CA-M6.3). Son fallos distintos del
modelo —citar mal y calcular de su cosecha— y una sola tasa los suma como si
fueran el mismo.

**El denominador son los insights del Clasificador, y esto es la decisión que
más mueve la cifra.** Los consolidados del Correlacionador **se excluyen**:
salen de insights ya validados y su evidencia la une el código, no el modelo,
así que nunca han producido un rechazo. Incluirlos solo diluye la tasa con
filas que no pueden fallar — en la corrida 10 serían 38 más en el denominador y
la tasa bajaría de 1,2 % a 1,1 % sin que el Clasificador hubiera mejorado nada.
Es también el denominador que usó la auditoría, y por eso las cifras de aquí
son comparables con las suyas.

**R8 no se ha evaluado en ninguna corrida persistida, y eso incluye la
publicada.** La añadió F0.2 el 2026-09-23, y las doce corridas que hay son del
18 al 21 de septiembre. Su conteo es 0 **porque no se midió**, no porque
saliera limpia. `evaluaba_r8()` distingue las dos cosas comparando la fecha de
la corrida con la de la regla — por fecha y no por id, para que la primera
corrida que sí la evalúe se cuente sola sin tocar este módulo.

Un cero que significa «sin medir» presentado como «ninguna violación» sería
justo la clase de afirmación que F0b existe para quitar del informe.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from territorial.almacen.modelos import CorridaAgentes, Insight

#: Lo que hay que decir junto a la cifra, siempre (H-029, F3.1).
FRASE_H029 = (
    "mide fidelidad de cita contra el contenido ingerido, no veracidad"
)

#: El origen que cuenta para el denominador. Ver la cabecera.
ORIGEN_EVALUADO = "clasificador"

#: Las dos familias de regla, que miden cosas distintas.
FIDELIDAD = "fidelidad de cita"
CIFRA = "cifra sin fuente"

#: Cada regla con su familia y qué comprueba. El orden es el de `validador.py`.
REGLAS: dict[str, tuple[str, str]] = {
    "R1": (FIDELIDAD, "el insight declara al menos un elemento de evidencia"),
    "R2": (FIDELIDAD, "ningún elemento se apoya en Bing (D1)"),
    "R3": (FIDELIDAD, "cada elemento trae url, fecha y cita textual"),
    "R4": (FIDELIDAD, "la URL está bien formada y es http(s)"),
    "R5": (FIDELIDAD, "la fecha es una fecha real"),
    "R6": (FIDELIDAD, "la cita aparece en la señal de origen"),
    "R7": (FIDELIDAD, "la señal citada existe y es del mismo municipio y ciclo"),
    "R8": (CIFRA, "ninguna cifra de la prosa falta en su entrada (CA-M6.3)"),
}

#: Cuándo empezó a existir R8: el commit de F0.2 que la añadió (`caca6f8`,
#: 2026-09-22 19:23:19 -05). Una corrida anterior **no la evaluó**.
FECHA_R8 = datetime(2026, 9, 23, 0, 23, 19, tzinfo=timezone.utc)


def evaluaba_r8(fecha_corrida: datetime | None) -> bool:
    """¿Esa corrida llegó a comprobar R8?

    Distingue «0 violaciones» de «no se midió». Hoy **devuelve `False` para las
    doce corridas que hay**, incluida la 10, que es la publicada.

    Sin fecha se responde `False`: ante la duda, «no se midió» es la respuesta
    que no afirma de más.
    """
    if fecha_corrida is None:
        return False
    if fecha_corrida.tzinfo is None:
        fecha_corrida = fecha_corrida.replace(tzinfo=timezone.utc)
    return fecha_corrida >= FECHA_R8


# Cada patrón identifica un fragmento de motivo. Salen literalmente de los
# mensajes de `validador.py`; si allí cambia el texto, `tests/test_tasa_rechazo.py`
# lo detecta comparándolos contra el validador de verdad.
_PATRONES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("R1", re.compile(r"no declara evidencia")),
    ("R2", re.compile(r"no puede sustentar evidencia|es de bing", re.I)),
    ("R3", re.compile(r"falta (url|fecha|cita_textual)")),
    ("R4", re.compile(r"url mal formada")),
    ("R5", re.compile(r"fecha no interpretable")),
    ("R6", re.compile(r"la cita no aparece en la señal")),
    ("R7", re.compile(
        r"no referencia ninguna señal|la señal \d+ no existe"
        r"|es de \d{5}, no de|es del ciclo \d+, no del"
    )),
    ("R8", re.compile(r"cifras que no están en la entrada del agente")),
)


def regla_del_fragmento(fragmento: str) -> str | None:
    """A qué regla corresponde un motivo suelto, o `None` si no se reconoce.

    **Devolver `None` es deliberado y hay que mirarlo**: significa que el
    validador emitió un motivo que este mapa no contempla, y el desglose lo
    cuenta aparte en vez de repartirlo o callarlo.
    """
    for codigo, patron in _PATRONES:
        if patron.search(fragmento):
            return codigo
    return None


def reglas_del_motivo(motivo: str | None) -> list[str]:
    """Las reglas que un insight incumplió. **Puede ser más de una.**

    `motivo_rechazo` guarda los fragmentos unidos por «; », y un mismo insight
    puede fallar por varias evidencias y varias reglas. Se devuelven sin
    repetir y en el orden de `REGLAS`, para que dos insights con los mismos
    fallos den la misma lista.
    """
    if not motivo:
        return []
    encontradas = {
        codigo
        for fragmento in motivo.split(";")
        if (codigo := regla_del_fragmento(fragmento.strip()))
    }
    return [c for c in REGLAS if c in encontradas]


def sin_clasificar(motivo: str | None) -> list[str]:
    """Fragmentos que ninguna regla reconoce. Vacío es lo normal."""
    if not motivo:
        return []
    return [
        f.strip()
        for f in motivo.split(";")
        if f.strip() and regla_del_fragmento(f.strip()) is None
    ]


@dataclass(frozen=True)
class DesgloseCorrida:
    """La tasa de una corrida, con el reparto por regla."""

    id_corrida: int
    evaluados: int
    rechazados: int
    #: Cuántos insights incumplieron cada regla. Un insight puede estar en
    #: varias, así que **la suma puede superar a `rechazados`**.
    por_regla: dict[str, int]
    #: Fragmentos de motivo que el mapa no reconoció.
    no_reconocidos: list[str] = field(default_factory=list)
    #: De `corrida_agentes`. Decide si R8 llegó a evaluarse.
    fecha_corrida: datetime | None = None

    @property
    def tasa(self) -> float:
        """En porcentaje. 0.0 si no hubo insights, no división por cero."""
        return 100.0 * self.rechazados / self.evaluados if self.evaluados else 0.0

    @property
    def r8_evaluada(self) -> bool:
        return evaluaba_r8(self.fecha_corrida)

    def por_familia(self) -> dict[str, int]:
        """Insights rechazados por cada familia de regla."""
        salida = {FIDELIDAD: 0, CIFRA: 0}
        for codigo, n in self.por_regla.items():
            salida[REGLAS[codigo][0]] += n
        return salida


def desglose(filas: list[dict]) -> list[DesgloseCorrida]:
    """Agrupa por corrida. **Función pura**, para poder probarla sin base.

    `filas` son dicts con `id_corrida`, `origen`, `estado_validacion` y
    `motivo_rechazo`. **Las que no son del Clasificador se descartan aquí**, no
    en la consulta, para que la regla del denominador viva en un solo sitio y
    se pueda probar.
    """
    por_corrida: dict[int, list[dict]] = {}
    for f in filas:
        if f.get("origen") != ORIGEN_EVALUADO:
            continue
        por_corrida.setdefault(f["id_corrida"], []).append(f)

    salida = []
    for id_corrida in sorted(por_corrida):
        suyas = por_corrida[id_corrida]
        rechazadas = [f for f in suyas if f.get("estado_validacion") == "rechazado"]
        conteo: dict[str, int] = {}
        huerfanos: list[str] = []
        for f in rechazadas:
            for codigo in reglas_del_motivo(f.get("motivo_rechazo")):
                conteo[codigo] = conteo.get(codigo, 0) + 1
            huerfanos.extend(sin_clasificar(f.get("motivo_rechazo")))
        salida.append(
            DesgloseCorrida(
                id_corrida=id_corrida,
                evaluados=len(suyas),
                rechazados=len(rechazadas),
                por_regla=conteo,
                no_reconocidos=huerfanos,
                fecha_corrida=suyas[0].get("fecha_corrida"),
            )
        )
    return salida


def leer(sesion: Session, corridas: list[int] | None = None) -> list[dict]:
    """Las filas que `desglose` necesita. **Solo lectura.**

    No filtra por origen: eso lo decide `desglose`, que es lo que se prueba.
    Trae la fecha de la corrida porque es lo que dice si R8 se evaluó.
    """
    consulta = (
        select(
            Insight.id_corrida, Insight.origen,
            Insight.estado_validacion, Insight.motivo_rechazo,
            CorridaAgentes.fecha_corrida,
        )
        .join(CorridaAgentes, CorridaAgentes.id == Insight.id_corrida)
    )
    if corridas:
        consulta = consulta.where(Insight.id_corrida.in_(corridas))
    return [
        {"id_corrida": c, "origen": o, "estado_validacion": e,
         "motivo_rechazo": m, "fecha_corrida": f}
        for c, o, e, m, f in sesion.execute(consulta)
    ]


def desde_la_base(
    sesion: Session, corridas: list[int] | None = None
) -> list[DesgloseCorrida]:
    """Atajo: leer y desglosar. Es lo que usará el script de F0b.1."""
    return desglose(leer(sesion, corridas))
