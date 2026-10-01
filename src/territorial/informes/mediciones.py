"""Las mediciones de `informe_resultados.md`. F0b.1 (H-034). **Solo lectura.**

**Por qué existe este módulo.** La auditoría encontró que ninguna cifra del
informe de resultados estaba ligada a la consulta que la produce: 53 de 67
procedencias apuntaban a otro documento, y varias eran falsas o no tenían
productor (H-034). Aquí vive **cada medición** que el informe publica, como una
función sobre la base. `informes/resultados.py` las convierte en cifras con su
etiqueta `[consulta: …]`, y `scripts/informe_resultados.py` regenera el
documento entero desde ellas.

**Una medición, una definición.** Donde ya había código que medía algo —el
destino de cada señal de `comparar_pasadas.py`, las palabras de tipología de
`comparar_correlacionador.py`, el prefiltro, la tasa de rechazo de F0b.3, la
reconstrucción de señales de la ingesta— **se reutiliza, no se reescribe**. Dos
definiciones de lo mismo envejecen por separado, y eso es exactamente el
defecto que este módulo existe para quitar.

**Nada de aquí escribe.** Todas las funciones reciben una sesión y solo hacen
`SELECT`. El script que las llama abre además la conexión en modo READ ONLY.

Las cifras de referencia de cada función —las que la auditoría reprodujo— están
en `tests/test_informe_resultados.py`.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from territorial.almacen.modelos import (
    Calificacion,
    Ciclo,
    CorridaAgentes,
    CorridaScoring,
    Descarte,
    Informe,
    Insight,
    Municipio,
    VersionPrompt,
    ScoreMunicipio,
    SenalCruda,
    TrazaAgente,
    VersionDataset,
)

# ---------------------------------------------------------------------------
# Definiciones compartidas con los scripts de calibración
# ---------------------------------------------------------------------------

#: Palabras que indican que una implicación se moja con una tipología, que es lo
#: que CA-M4.2 pide. Vivía en `scripts/comparar_correlacionador.py`, que ahora
#: la importa de aquí: una sola lista para la compuerta y para el informe.
TIPOLOGIA = (
    "vivienda", "residencial", "vis", "interés social", "interes social",
    "industrial", "logístic", "logistic", "comercial", "oficina", "bodega",
    "renovación", "renovacion", "estrato",
)


def destino_por_senal(sesion: Session, id_corrida: int) -> dict[int, tuple[str, str]]:
    """{id_senal: (destino, detalle)} de una pasada. A6, CA-M2.5.

    Cada señal que entró al agente cae en uno de tres sitios: `insight`,
    `descarte` o `sin_contabilizar` —el modelo ni la mencionó—. Un insight gana
    sobre un descarte: si aparece en los dos, se usó.

    Vivía en `scripts/comparar_pasadas.py`, que ahora la importa de aquí.
    """
    mapa: dict[int, tuple[str, str]] = {}
    for ins in sesion.scalars(
        select(Insight).where(Insight.id_corrida == id_corrida).order_by(Insight.id)
    ):
        for s in ins.ids_senal or []:
            mapa[s] = ("insight", ins.categoria)
    for d in sesion.scalars(
        select(Descarte).where(Descarte.id_corrida == id_corrida).order_by(Descarte.id)
    ):
        if d.id_senal in mapa:
            continue
        mapa[d.id_senal] = (
            "descarte" if d.declarado else "sin_contabilizar",
            d.motivo[:60],
        )
    return mapa


# ---------------------------------------------------------------------------
# Inventario (H-031)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Inventario:
    municipios: int
    senales: int
    senales_por_fuente: dict[str, int]
    dias_por_ciclo: dict[int, int]
    corridas_agentes: int
    corridas_scoring: int
    insights: int
    descartes: int
    trazas: int
    informes_publicados: int
    informes_archivados: int


def inventario(sesion: Session) -> Inventario:
    """Conteos de las tablas que no cambian sin correr un ciclo.

    **Las calificaciones no están aquí** a propósito: crecen mientras dure la
    ronda extendida, y un conteo sin corte haría el documento irreproducible.
    Van con su corte, en H1 y H2.
    """
    contar = lambda m: sesion.scalar(select(func.count()).select_from(m))  # noqa: E731
    por_fuente = dict(
        sesion.execute(
            select(SenalCruda.fuente, func.count())
            .group_by(SenalCruda.fuente).order_by(SenalCruda.fuente)
        ).all()
    )
    dias = {
        c.id: (c.fecha_hasta - c.fecha_desde).days
        for c in sesion.scalars(select(Ciclo).order_by(Ciclo.id))
    }
    estados = dict(
        sesion.execute(select(Informe.estado, func.count()).group_by(Informe.estado)).all()
    )
    return Inventario(
        municipios=contar(Municipio),
        senales=contar(SenalCruda),
        senales_por_fuente=por_fuente,
        dias_por_ciclo=dias,
        corridas_agentes=contar(CorridaAgentes),
        corridas_scoring=contar(CorridaScoring),
        insights=contar(Insight),
        descartes=contar(Descarte),
        trazas=contar(TrazaAgente),
        informes_publicados=estados.get("publicado", 0),
        informes_archivados=estados.get("archivado", 0),
    )


# ---------------------------------------------------------------------------
# H1 y H2 — definiciones congeladas en docs/javelin.md (2026-10-01)
# ---------------------------------------------------------------------------

#: Lo que el tablero congela para H1.
MINIMO_CALIFICACIONES_PRD = 2
UMBRAL_PROMEDIO_H1 = 4.0


@dataclass(frozen=True)
class Pedidos:
    """Los insights pedidos del informe publicado y las gerencias congeladas."""

    id_informe: int
    id_ciclo: int
    ids: tuple[int, ...]
    #: id_gerencia -> "prd" | "adicional", congelado en el payload (F0.1b).
    tipo_por_gerencia: dict[str, str]


def pedidos_del_informe(sesion: Session, id_informe: int) -> Pedidos:
    informe = sesion.get(Informe, id_informe)
    if informe is None:
        raise LookupError(f"no existe el informe {id_informe}")
    contenido = informe.contenido
    ids = tuple(
        i
        for m in contenido.get("municipios", [])
        if m.get("calificable")
        for i in m.get("insights_pedidos", [])
    )
    tipos = {g["id_gerencia"]: g["tipo"] for g in contenido["calificacion"]["gerencias"]}
    return Pedidos(informe.id, informe.id_ciclo, ids, tipos)


def calificaciones_hasta(sesion: Session, corte: datetime) -> list[dict]:
    """Las calificaciones con `creado_en` hasta el corte, en orden estable."""
    filas = sesion.execute(
        select(
            Calificacion.id, Calificacion.id_insight, Calificacion.id_gerencia,
            Calificacion.id_usuario, Calificacion.valor, Calificacion.comentario,
        )
        .where(Calificacion.creado_en <= corte)
        .order_by(Calificacion.creado_en, Calificacion.id)
    ).all()
    return [
        {"id": i, "id_insight": ins, "id_gerencia": g, "id_usuario": u,
         "valor": v, "comentario": c}
        for i, ins, g, u, v, c in filas
    ]


@dataclass(frozen=True)
class ResultadoH1:
    pedidos: int
    #: Insights con al menos 2 calificaciones «prd»: los que cuentan.
    cuentan: int
    #: Los que no llegan a 2 calificaciones «prd»: «insuficiente», fuera.
    insuficientes: int
    #: De los que cuentan, cuántos tienen promedio «prd» >= 4.
    altos_prd: int
    #: Los mismos insights, con el promedio incluyendo las adicionales.
    altos_con_adicionales: int

    @property
    def porcentaje_prd(self) -> float | None:
        return 100.0 * self.altos_prd / self.cuentan if self.cuentan else None

    @property
    def porcentaje_con_adicionales(self) -> float | None:
        return 100.0 * self.altos_con_adicionales / self.cuentan if self.cuentan else None


def h1(pedidos: Pedidos, calificaciones: list[dict]) -> ResultadoH1:
    """H1 con las definiciones congeladas en `docs/javelin.md`. Función pura.

    - Base: los 15 insights pedidos.
    - Promedio de cada insight con las calificaciones de las gerencias «prd».
    - Cuenta solo si tiene **al menos 2** calificaciones «prd»; si no, es
      «insuficiente» y queda fuera, ni en el numerador ni en el denominador.
    - Versión con adicionales: **sobre los mismos insights**, con el promedio
      incluyendo además las adicionales.
    """
    pedidos_set = set(pedidos.ids)
    prd: dict[int, list[int]] = {i: [] for i in pedidos.ids}
    todas: dict[int, list[int]] = {i: [] for i in pedidos.ids}
    for c in calificaciones:
        if c["id_insight"] not in pedidos_set:
            continue
        tipo = pedidos.tipo_por_gerencia.get(c["id_gerencia"])
        if tipo is None:
            continue
        todas[c["id_insight"]].append(c["valor"])
        if tipo == "prd":
            prd[c["id_insight"]].append(c["valor"])

    cuentan = [i for i in pedidos.ids if len(prd[i]) >= MINIMO_CALIFICACIONES_PRD]
    media = lambda xs: sum(xs) / len(xs)  # noqa: E731
    return ResultadoH1(
        pedidos=len(pedidos.ids),
        cuentan=len(cuentan),
        insuficientes=len(pedidos.ids) - len(cuentan),
        altos_prd=sum(1 for i in cuentan if media(prd[i]) >= UMBRAL_PROMEDIO_H1),
        altos_con_adicionales=sum(
            1 for i in cuentan if media(todas[i]) >= UMBRAL_PROMEDIO_H1
        ),
    )


@dataclass(frozen=True)
class TasaGerencia:
    id_gerencia: str
    tipo: str
    calificados: int
    pedidos: int

    @property
    def porcentaje(self) -> float:
        return 100.0 * self.calificados / self.pedidos if self.pedidos else 0.0


@dataclass(frozen=True)
class ResultadoH2:
    por_gerencia: tuple[TasaGerencia, ...]

    def de_tipo(self, tipo: str) -> tuple[TasaGerencia, ...]:
        return tuple(g for g in self.por_gerencia if g.tipo == tipo)

    @property
    def promedio_prd(self) -> float | None:
        prd = self.de_tipo("prd")
        return sum(g.porcentaje for g in prd) / len(prd) if prd else None

    @property
    def n_prd(self) -> int:
        return len(self.de_tipo("prd"))


def h2(pedidos: Pedidos, calificaciones: list[dict]) -> ResultadoH2:
    """H2 con las definiciones congeladas. Función pura.

    Tasa por gerencia = insights pedidos calificados ÷ insights pedidos. El
    promedio es **sobre las gerencias «prd»** de la lista congelada; las
    adicionales se listan aparte. Cuentan **todas** las gerencias congeladas,
    también las que no calificaron nada: su 0 % es un dato.
    """
    pedidos_set = set(pedidos.ids)
    hechos: dict[str, set[int]] = {g: set() for g in pedidos.tipo_por_gerencia}
    for c in calificaciones:
        if c["id_insight"] in pedidos_set and c["id_gerencia"] in hechos:
            hechos[c["id_gerencia"]].add(c["id_insight"])
    return ResultadoH2(tuple(
        TasaGerencia(g, pedidos.tipo_por_gerencia[g], len(hechos[g]), len(pedidos.ids))
        for g in sorted(pedidos.tipo_por_gerencia)
    ))


# ---------------------------------------------------------------------------
# La foto del corte: la base tiene que coincidir con la exportación
# ---------------------------------------------------------------------------

class CorteNoCoincide(Exception):
    """La base ya no dice lo mismo que la exportación del corte."""


def verificar_contra_exportacion(calificaciones: list[dict], carpeta: Path) -> int:
    """Compara las calificaciones del corte con su exportación. Devuelve las filas.

    Tres comprobaciones, de la más barata a la más fuerte:

    1. el `calificacion.csv` sigue teniendo el sha256 del manifiesto;
    2. el número de filas coincide con el del manifiesto;
    3. **fila a fila**, id, insight, gerencia, usuario, valor y comentario son
       iguales en la base y en el CSV.

    La tercera es la que vale. H-008 dice que una corrección posterior al corte
    no cambia `creado_en`, así que un filtro por fecha no la vería; comparar
    contra la foto sí. Si alguien corrige una calificación de la ronda
    principal, el informe se niega a regenerarse en vez de publicar una cifra
    que ya no es la del corte.
    """
    manifiesto = json.loads((carpeta / "manifiesto.json").read_text(encoding="utf-8"))
    declarado = manifiesto["archivos"]["calificacion.csv"]
    ruta_csv = carpeta / "calificacion.csv"
    real = hashlib.sha256(ruta_csv.read_bytes()).hexdigest()
    if real != declarado["sha256"]:
        raise CorteNoCoincide(
            f"calificacion.csv no tiene el sha256 del manifiesto ({real[:12]}…)"
        )
    if len(calificaciones) != declarado["filas"]:
        raise CorteNoCoincide(
            f"la base da {len(calificaciones)} calificaciones hasta el corte y "
            f"el manifiesto declara {declarado['filas']}"
        )

    import csv  # solo aquí

    with ruta_csv.open(encoding="utf-8", newline="") as f:
        foto = {
            int(r["id"]): (int(r["id_insight"]), r["id_gerencia"], int(r["id_usuario"]),
                           int(r["valor"]), r["comentario"] or None)
            for r in csv.DictReader(f)
        }
    base = {
        c["id"]: (c["id_insight"], c["id_gerencia"], c["id_usuario"], c["valor"],
                  c["comentario"] or None)
        for c in calificaciones
    }
    if base != foto:
        distintas = sorted(i for i in set(base) | set(foto) if base.get(i) != foto.get(i))
        raise CorteNoCoincide(
            f"{len(distintas)} calificación(es) distintas entre la base y la foto "
            f"del corte, ids {distintas[:10]}: alguien la(s) modificó después"
        )
    return len(calificaciones)


# ---------------------------------------------------------------------------
# H3 — supervivencia, fuentes y conversión
# ---------------------------------------------------------------------------

def _fuentes_de_senales(sesion: Session, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return dict(sesion.execute(
        select(SenalCruda.id, SenalCruda.fuente).where(SenalCruda.id.in_(ids))
    ).all())


@dataclass(frozen=True)
class PorFuente:
    """Insights del Clasificador de una corrida, por la fuente de su evidencia."""

    validados: dict[str, int]
    total: dict[str, int]
    #: Insights del Clasificador cuya evidencia mezcla fuentes.
    mixtos: int


def supervivencia_por_fuente(sesion: Session, id_corrida: int) -> PorFuente:
    """Validados / total de los insights del Clasificador, por fuente.

    La fuente de un insight es la de las señales que cita su evidencia. Un
    insight del Clasificador sale de una sola fuente; si alguno mezclara, se
    cuenta aparte en `mixtos` en vez de asignarlo a una.
    """
    filas = sesion.scalars(
        select(Insight)
        .where(Insight.id_corrida == id_corrida, Insight.origen == "clasificador")
        .order_by(Insight.id)
    ).all()
    ids = {e.get("id_senal") for ins in filas for e in (ins.evidencia or [])}
    fuente = _fuentes_de_senales(sesion, {i for i in ids if i is not None})
    validados: Counter = Counter()
    total: Counter = Counter()
    mixtos = 0
    for ins in filas:
        fs = {fuente.get(e.get("id_senal")) for e in (ins.evidencia or [])} - {None}
        if len(fs) != 1:
            mixtos += 1
            continue
        f = fs.pop()
        total[f] += 1
        if ins.estado_validacion == "validado":
            validados[f] += 1
    return PorFuente(dict(validados), dict(total), mixtos)


@dataclass(frozen=True)
class Conversion:
    """Señales enviadas al Clasificador que acaban en un insight validado."""

    convertidas: dict[str, int]
    enviadas: dict[str, int]


def conversion_por_fuente(sesion: Session, id_corrida: int) -> Conversion:
    """Por fuente: señales en un insight validado del Clasificador / enviadas.

    «Enviadas» son las que el agente recibió: las que acabaron en un insight o
    en un descarte, declarado o no (CA-M2.5 obliga a que cada una caiga en uno
    de los dos). Es el rendimiento del prefiltro que discute A2.
    """
    destinos = destino_por_senal(sesion, id_corrida)
    convertidas_ids: set[int] = set()
    for ins in sesion.scalars(
        select(Insight).where(
            Insight.id_corrida == id_corrida,
            Insight.origen == "clasificador",
            Insight.estado_validacion == "validado",
        )
    ):
        convertidas_ids.update(ins.ids_senal or [])
    fuente = _fuentes_de_senales(sesion, set(destinos))
    enviadas = Counter(fuente[i] for i in destinos if i in fuente)
    convertidas = Counter(fuente[i] for i in convertidas_ids if i in fuente)
    return Conversion(dict(convertidas), dict(enviadas))


@dataclass(frozen=True)
class DescartesFuente:
    total: int
    con_motivo: int


def descartes_de_fuente(
    sesion: Session, id_corrida: int, fuente: str, motivo: str
) -> DescartesFuente:
    """Descartes de una corrida cuyas señales son de esa fuente, y cuántos con
    ese motivo **exacto**. El total cuenta declarados y no declarados."""
    base = (
        select(func.count())
        .select_from(Descarte)
        .join(SenalCruda, SenalCruda.id == Descarte.id_senal)
        .where(Descarte.id_corrida == id_corrida, SenalCruda.fuente == fuente)
    )
    return DescartesFuente(
        total=sesion.scalar(base),
        con_motivo=sesion.scalar(base.where(Descarte.motivo == motivo)),
    )


@dataclass(frozen=True)
class Cruces:
    cruzan: int
    consolidados: int


def consolidados_que_cruzan(sesion: Session, id_corrida: int, a: str, b: str) -> Cruces:
    """Consolidados del Correlacionador con evidencia de las dos fuentes (CA-M4.1)."""
    filas = sesion.scalars(
        select(Insight)
        .where(Insight.id_corrida == id_corrida, Insight.origen == "correlacionador")
        .order_by(Insight.id)
    ).all()
    ids = {e.get("id_senal") for ins in filas for e in (ins.evidencia or [])}
    fuente = _fuentes_de_senales(sesion, {i for i in ids if i is not None})
    cruzan = sum(
        1 for ins in filas
        if {a, b} <= {fuente.get(e.get("id_senal")) for e in (ins.evidencia or [])}
    )
    return Cruces(cruzan, len(filas))


@dataclass(frozen=True)
class Volumen:
    insights: int
    evidencias: int


def volumen(sesion: Session, id_corrida: int) -> Volumen:
    """Insights de una corrida y la suma de sus elementos de evidencia."""
    filas = sesion.scalars(select(Insight).where(Insight.id_corrida == id_corrida)).all()
    return Volumen(len(filas), sum(len(i.evidencia or []) for i in filas))


# ---------------------------------------------------------------------------
# H4 — trazas, descartes y la traza extremo a extremo del informe
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Trazas:
    total: int
    con_hash_entrada: int
    con_hash_salida: int


def trazas(sesion: Session) -> Trazas:
    """H-027: el documento afirmaba hashes de entrada **y de salida**."""
    contar = lambda *w: sesion.scalar(  # noqa: E731
        select(func.count()).select_from(TrazaAgente).where(*w)
    )
    return Trazas(
        total=contar(),
        con_hash_entrada=contar(TrazaAgente.hash_input.is_not(None)),
        con_hash_salida=contar(TrazaAgente.hash_output.is_not(None)),
    )


@dataclass(frozen=True)
class Descartes:
    declarados: int
    no_declarados: int


def descartes(sesion: Session) -> Descartes:
    """CA-M2.5: los no declarados son señales que el modelo ni mencionó."""
    filas = dict(sesion.execute(
        select(Descarte.declarado, func.count()).group_by(Descarte.declarado)
    ).all())
    return Descartes(filas.get(True, 0), filas.get(False, 0))


def prompts_registrados(sesion: Session) -> list[tuple[str, str]]:
    """(agente, versión) con linaje por contenido en `prompt_version` (D7)."""
    return [
        (a, v) for a, v in sesion.execute(
            select(VersionPrompt.agente, VersionPrompt.version)
            .order_by(VersionPrompt.agente, VersionPrompt.version)
        ).all()
    ]


@dataclass(frozen=True)
class TrazaInforme:
    """La traza de la auditoría §4.7, sobre todos los insights de un informe."""

    insights: int
    sin_fallo: int
    consolidados: int
    directos: int
    citas_localizables: int
    citas: int
    senales_iguales_al_snapshot: int
    insights_con_senales_iguales: int
    scores_iguales: int
    municipios: int
    snapshot_anclado: bool
    fallos: list[str] = field(default_factory=list)


def traza_informe(sesion: Session, id_informe: int, ruta_snapshot: Path) -> TrazaInforme:
    """Recorre señal → insight → validación → correlación → score → informe.

    Es la verificación de la auditoría §4.7, ahora con productor. Por cada
    insight del payload comprueba que:

    1. existe en la corrida del informe, con su municipio y validado;
    2. sus `ids_senal` y su `evidencia` son idénticos a los del payload;
    3. si es un consolidado, sus orígenes existen, son del Clasificador, están
       validados y la unión de sus señales es exactamente la del consolidado;
    4. cada evidencia apunta a una señal del mismo municipio y ciclo, con la
       misma URL y fecha, y la cita es **localizable** en su contenido;
    5. cada señal es **igual al registro del snapshot**, reconstruido con la
       misma función de la ingesta, y el snapshot es el anclado por hash;

    y, por municipio, que el score y el puesto de la corrida de scoring son los
    del payload.
    """
    from territorial.config import obtener_config
    from territorial.ingesta.snapshot import _senales_del_municipio
    from territorial.reglas.normalizacion import contiene
    from territorial.utiles.divipola import desde_bloque

    informe = sesion.get(Informe, id_informe)
    payload = informe.contenido
    corrida = informe.id_corrida_agentes
    fallos: list[str] = []

    # --- El snapshot, anclado por hash, y reconstruido con la ingesta ------
    crudo = ruta_snapshot.read_bytes()
    huella = hashlib.sha256(crudo).hexdigest()
    anclado = sesion.scalar(
        select(func.count()).select_from(VersionDataset)
        .where(VersionDataset.hash_sha256 == huella)
    ) == 1
    if not anclado:
        fallos.append("el snapshot no coincide con ningún dataset_version por hash")
    ventanas = obtener_config().ventanas_ciclo
    esperadas: dict[tuple[int, str], dict] = {}
    for muni in json.loads(crudo.decode("utf-8")).get("municipios", []):
        divipola = desde_bloque(muni["cod_divipola"])
        senales, _ = _senales_del_municipio(muni, divipola, ventanas)
        for sen in senales:
            esperadas.setdefault((sen["id_ciclo"], sen["hash_dedup"]), {**sen, "divipola": divipola})

    def igual_al_snapshot(s: SenalCruda) -> bool:
        e = esperadas.get((s.id_ciclo, s.hash_dedup))
        return e is not None and (
            e["fuente"], e["divipola"], e["contenido"], e["url"], e["fecha_publicacion"]
        ) == (s.fuente, s.divipola, s.contenido, s.url, s.fecha_publicacion)

    # --- Insight a insight -------------------------------------------------
    n = sin_fallo = consolidados = directos = 0
    citas = localizables = senales_ok = insights_senales_ok = 0
    for m in payload["municipios"]:
        for p in m["insights"]:
            n += 1
            mal: list[str] = []
            fila = sesion.get(Insight, p["id"])
            if fila is None or fila.id_corrida != corrida:
                fallos.append(f"insight {p['id']}: no está en la corrida {corrida}")
                continue
            if fila.divipola != m["divipola"] or fila.estado_validacion != "validado":
                mal.append("municipio o estado")
            if list(fila.ids_senal or []) != list(p["ids_senal"]):
                mal.append("ids_senal")
            if list(fila.evidencia or []) != list(p["evidencia"]):
                mal.append("evidencia")
            if fila.origen == "correlacionador":
                consolidados += 1
                origenes = [sesion.get(Insight, i) for i in fila.ids_insight_origen or []]
                if not origenes or any(
                    o is None or o.origen != "clasificador" or o.estado_validacion != "validado"
                    for o in origenes
                ):
                    mal.append("orígenes")
                elif {s for o in origenes for s in (o.ids_senal or [])} != set(fila.ids_senal or []):
                    mal.append("unión de señales")
            else:
                directos += 1
            todas_iguales = True
            for e in fila.evidencia or []:
                citas += 1
                s = sesion.get(SenalCruda, e.get("id_senal"))
                if s is None:
                    mal.append(f"señal {e.get('id_senal')} inexistente")
                    todas_iguales = False
                    continue
                if (s.divipola != fila.divipola or s.id_ciclo != informe.id_ciclo
                        or e.get("url") != s.url
                        or str(e.get("fecha")) != str(s.fecha_publicacion)):
                    mal.append(f"señal {s.id}: municipio, ciclo, url o fecha")
                if contiene(s.contenido, e.get("cita_textual")):
                    localizables += 1
                else:
                    mal.append(f"cita no localizable en {s.id}")
                if igual_al_snapshot(s):
                    senales_ok += 1
                else:
                    todas_iguales = False
                    mal.append(f"señal {s.id} distinta del snapshot")
            insights_senales_ok += todas_iguales
            if mal:
                fallos.append(f"insight {p['id']}: {', '.join(mal)}")
            else:
                sin_fallo += 1

    # --- Score y puesto por municipio --------------------------------------
    scores_ok = 0
    for m in payload["municipios"]:
        sm = sesion.scalar(select(ScoreMunicipio).where(
            ScoreMunicipio.id_corrida == informe.id_corrida,
            ScoreMunicipio.divipola == m["divipola"],
        ))
        if sm is not None and abs(sm.score - m["score"]) < 1e-12 \
                and sm.ranking == m["ranking_en_la_corrida"]:
            scores_ok += 1
        else:
            fallos.append(f"municipio {m['divipola']}: score o puesto distinto del payload")

    return TrazaInforme(
        insights=n, sin_fallo=sin_fallo, consolidados=consolidados, directos=directos,
        citas_localizables=localizables, citas=citas,
        senales_iguales_al_snapshot=senales_ok,
        insights_con_senales_iguales=insights_senales_ok,
        scores_iguales=scores_ok, municipios=len(payload["municipios"]),
        snapshot_anclado=anclado, fallos=fallos,
    )


# ---------------------------------------------------------------------------
# H5 — consumo medido en traza_agente
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Consumo:
    llamadas: int
    tokens_entrada: int
    tokens_salida: int
    minutos: float


def consumo_por_agente(sesion: Session) -> dict[str, Consumo]:
    filas = sesion.execute(
        select(
            TrazaAgente.agente, func.count(), func.sum(TrazaAgente.tokens_entrada),
            func.sum(TrazaAgente.tokens_salida), func.sum(TrazaAgente.duracion_ms),
        ).group_by(TrazaAgente.agente).order_by(TrazaAgente.agente)
    ).all()
    return {
        a: Consumo(n, int(e or 0), int(s or 0), (ms or 0) / 60_000)
        for a, n, e, s, ms in filas
    }


def modelo_de(sesion: Session, agente: str) -> str:
    """El despliegue que la traza registra para un agente. Falla si hay varios:
    la proyección de H5 asume uno por agente."""
    modelos = sesion.scalars(
        select(TrazaAgente.modelo).where(TrazaAgente.agente == agente).distinct()
    ).all()
    if len(modelos) != 1:
        raise ValueError(f"{agente}: se esperaba un despliegue y hay {modelos}")
    return modelos[0]


def consumo_de_ciclo(sesion: Session, id_ciclo: int) -> Consumo:
    """Todo lo trazado de un ciclo. **No se puede repartir por corrida**: la
    traza no lleva `id_corrida` (H-006), así que el total de un ciclo corrido
    varias veces no se divide entre pasadas."""
    n, e, s, ms = sesion.execute(
        select(
            func.count(), func.sum(TrazaAgente.tokens_entrada),
            func.sum(TrazaAgente.tokens_salida), func.sum(TrazaAgente.duracion_ms),
        ).where(TrazaAgente.id_ciclo == id_ciclo)
    ).one()
    return Consumo(n, int(e or 0), int(s or 0), (ms or 0) / 60_000)


def senales_tras_prefiltro(sesion: Session) -> tuple[int, int]:
    """(pasan, total) de SECOP II por el prefiltro. Lo de `medir_prefiltro.py`."""
    from territorial.reglas.prefiltro import clasificar

    total = pasan = 0
    for contenido in sesion.scalars(
        select(SenalCruda.contenido).where(SenalCruda.fuente == "SECOP II")
    ).yield_per(2000):
        total += 1
        pasan += clasificar(contenido)[0]
    return pasan, total


# ---------------------------------------------------------------------------
# Hallazgos
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Pasadas:
    """A6: dos pasadas del Clasificador sobre el mismo ciclo, señal a señal."""

    senales: int
    cambian_destino: int
    vuelcan_insight: int


def comparar_pasadas(sesion: Session, a: int, b: int, divipola: str | None = None) -> Pasadas:
    """La misma cuenta que `comparar_pasadas.py`, opcionalmente por municipio."""
    da, db = destino_por_senal(sesion, a), destino_por_senal(sesion, b)
    todas = set(da) | set(db)
    if divipola is not None:
        de_muni = set(sesion.scalars(
            select(SenalCruda.id).where(SenalCruda.id.in_(todas),
                                        SenalCruda.divipola == divipola)
        ).all())
        todas &= de_muni
    destino = lambda m, i: m.get(i, ("ausente",))[0]  # noqa: E731
    return Pasadas(
        senales=len(todas),
        cambian_destino=sum(1 for i in todas if destino(da, i) != destino(db, i)),
        vuelcan_insight=sum(
            1 for i in todas
            if (destino(da, i) == "insight") != (destino(db, i) == "insight")
        ),
    )


@dataclass(frozen=True)
class Correlaciones:
    """A11: dos pasadas del Correlacionador sobre los mismos insights."""

    distintas: int
    identicas: int
    agrupados_que_cambian: int
    corpus: int
    municipios_que_cambian: int
    municipios: int
    convergencias: tuple[int, int]
    con_tipologia: tuple[int, int]


def comparar_correlaciones(
    sesion: Session, a: int, b: int, id_corrida_corpus: int
) -> Correlaciones:
    """Huellas por conjunto de insights de origen, como `comparar_correlacionador.py`.

    El corpus son los insights validados del Clasificador de la corrida que
    las dos pasadas tomaron como entrada.
    """
    def consolidados(c):
        return sesion.scalars(
            select(Insight)
            .where(Insight.id_corrida == c, Insight.origen == "correlacionador")
            .order_by(Insight.id)
        ).all()

    ca, cb = consolidados(a), consolidados(b)
    huellas = lambda fs: {frozenset(f.ids_insight_origen or []) for f in fs}  # noqa: E731
    ha, hb = huellas(ca), huellas(cb)
    agrup = lambda fs: {i for f in fs for i in (f.ids_insight_origen or [])}  # noqa: E731
    por_muni = lambda fs: {  # noqa: E731
        d: {frozenset(f.ids_insight_origen or []) for f in fs if f.divipola == d}
        for d in {f.divipola for f in fs}
    }
    ma, mb = por_muni(ca), por_muni(cb)
    corpus = sesion.scalar(select(func.count()).select_from(Insight).where(
        Insight.id_corrida == id_corrida_corpus, Insight.origen == "clasificador",
        Insight.estado_validacion == "validado",
    ))
    municipios = sesion.scalar(select(func.count()).select_from(Municipio))
    tipologia = lambda fs: sum(  # noqa: E731
        1 for f in fs
        if any(p in (f.implicacion_inmobiliaria or "").lower() for p in TIPOLOGIA)
    )
    return Correlaciones(
        distintas=len(ha | hb),
        identicas=len(ha & hb),
        agrupados_que_cambian=len(agrup(ca) ^ agrup(cb)),
        corpus=corpus,
        municipios_que_cambian=sum(
            1 for d in set(ma) | set(mb) if ma.get(d, set()) != mb.get(d, set())
        ),
        municipios=municipios,
        convergencias=(len(ca), len(cb)),
        con_tipologia=(tipologia(ca), tipologia(cb)),
    )


def motivos_de_descarte(sesion: Session, limite: int = 3) -> list[tuple[str, int]]:
    """Los motivos **exactos** más frecuentes de toda la tabla `descarte`."""
    return [
        (m, n) for m, n in sesion.execute(
            select(Descarte.motivo, func.count().label("n"))
            .group_by(Descarte.motivo)
            .order_by(func.count().desc(), Descarte.motivo)
            .limit(limite)
        ).all()
    ]


def scores_identicos(sesion: Session, a: int, b: int) -> tuple[int, int]:
    """(municipios con score distinto, municipios comparados) entre dos corridas
    de scoring. Es la reproducibilidad del código determinista."""
    sa = dict(sesion.execute(select(ScoreMunicipio.divipola, ScoreMunicipio.score)
                             .where(ScoreMunicipio.id_corrida == a)).all())
    sb = dict(sesion.execute(select(ScoreMunicipio.divipola, ScoreMunicipio.score)
                             .where(ScoreMunicipio.id_corrida == b)).all())
    comunes = set(sa) & set(sb)
    return sum(1 for d in comunes if sa[d] != sb[d]), len(comunes)


def top(sesion: Session, id_corrida_scoring: int, n: int = 3) -> list[str]:
    """Los nombres del top n de una corrida de scoring, por puesto."""
    return list(sesion.scalars(
        select(Municipio.nombre)
        .join(ScoreMunicipio, ScoreMunicipio.divipola == Municipio.divipola)
        .where(ScoreMunicipio.id_corrida == id_corrida_scoring,
               ScoreMunicipio.ranking.is_not(None))
        .order_by(ScoreMunicipio.ranking).limit(n)
    ).all())


def valor_crudo(sesion: Session, id_corrida_scoring: int, divipola: str, factor: str):
    sm = sesion.scalar(select(ScoreMunicipio).where(
        ScoreMunicipio.id_corrida == id_corrida_scoring,
        ScoreMunicipio.divipola == divipola,
    ))
    return None if sm is None else (sm.valores_crudos or {}).get(factor)


def factor_constante(sesion: Session, corridas: list[int], factor: str) -> tuple[int, int]:
    """(municipios con el factor idéntico en todas las corridas, municipios)."""
    por_muni: dict[str, list] = {}
    for c in corridas:
        for d, crudos in sesion.execute(
            select(ScoreMunicipio.divipola, ScoreMunicipio.valores_crudos)
            .where(ScoreMunicipio.id_corrida == c)
        ).all():
            por_muni.setdefault(d, []).append((crudos or {}).get(factor))
    completos = {d: v for d, v in por_muni.items() if len(v) == len(corridas)}
    return sum(1 for v in completos.values() if len(set(map(repr, v))) == 1), len(completos)


def fracciones_informadas(sesion: Session, id_corrida_scoring: int) -> dict[str, float]:
    """{divipola: fracción informada} de una corrida de scoring."""
    salida = {}
    for d, factores in sesion.execute(
        select(ScoreMunicipio.divipola, ScoreMunicipio.factores)
        .where(ScoreMunicipio.id_corrida == id_corrida_scoring)
        .order_by(ScoreMunicipio.divipola)
    ).all():
        f = (factores or {}).get("fraccion_informada")
        if f is not None:
            salida[d] = f
    return salida


def insights_validados_de_fuente(
    sesion: Session, id_corrida: int, divipola: str, fuente: str
) -> tuple[int, int]:
    """(directos, consolidados) validados de un municipio cuya evidencia es solo
    de esa fuente. Es «Barranquilla tiene 12 insights de prensa» (P1).

    Se devuelven separados porque la cifra suelta engaña en las dos
    direcciones: los 12 de Barranquilla son 10 del Clasificador y 2
    consolidados del Correlacionador, y contar solo los primeros da 10.
    """
    filas = sesion.scalars(select(Insight).where(
        Insight.id_corrida == id_corrida, Insight.divipola == divipola,
        Insight.estado_validacion == "validado",
    ).order_by(Insight.id)).all()
    ids = {e.get("id_senal") for i in filas for e in (i.evidencia or [])} - {None}
    fuentes = _fuentes_de_senales(sesion, ids)
    solo = [
        i for i in filas
        if {fuentes.get(e.get("id_senal")) for e in (i.evidencia or [])} == {fuente}
    ]
    return (sum(1 for i in solo if i.origen == "clasificador"),
            sum(1 for i in solo if i.origen == "correlacionador"))


@dataclass(frozen=True)
class MunicipioPublicado:
    puesto: int
    divipola: str
    nombre: str
    score: float
    fuentes: str
    dias_cubiertos: int | None
    dias_ventana: int | None


def municipios_del_informe(sesion: Session, id_informe: int) -> list[MunicipioPublicado]:
    """Los municipios **tal como se publicaron**, leídos del payload congelado.

    Es la fuente de verdad de lo que vieron las gerencias: no se recalcula desde
    el scoring, que es justo lo que la traza de H4 comprueba que coincide.
    """
    payload = sesion.get(Informe, id_informe).contenido
    return [
        MunicipioPublicado(
            puesto=m["puesto"], divipola=m["divipola"], nombre=m["nombre"],
            score=m["score"], fuentes=m["fuentes"]["resumen"],
            dias_cubiertos=(m.get("cobertura") or {}).get("dias_cubiertos"),
            dias_ventana=(m.get("cobertura") or {}).get("dias_ventana"),
        )
        for m in sorted(payload["municipios"], key=lambda x: x["puesto"])
    ]


def nombres(sesion: Session) -> dict[str, str]:
    return dict(sesion.execute(select(Municipio.divipola, Municipio.nombre)).all())


def reduccion_clasificador(sesion: Session, id_corrida: int) -> tuple[int, int]:
    """CA-M2.1: (validados del Clasificador, señales del ciclo de la corrida)."""
    corrida = sesion.get(CorridaAgentes, id_corrida)
    validados = sesion.scalar(select(func.count()).select_from(Insight).where(
        Insight.id_corrida == id_corrida, Insight.origen == "clasificador",
        Insight.estado_validacion == "validado",
    ))
    senales = sesion.scalar(select(func.count()).select_from(SenalCruda)
                            .where(SenalCruda.id_ciclo == corrida.id_ciclo))
    return validados, senales
