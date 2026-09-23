"""Publica el informe de un ciclo. Un solo publicado a la vez, y congelado.

Publicar es un **acto deliberado** y tiene tres efectos que van juntos o no van:

  1. Se compone el contenido desde el almacén (`composicion.componer`).
  2. Se archiva el informe que estuviera publicado de ese ciclo.
  3. Entra el nuevo, con **las dos corridas congeladas**.

Los tres en la misma transacción. Si se separaran, habría un instante con dos
informes publicados del mismo ciclo o con ninguno, y «la última publicada» —que
es como se define la corrida canónica— dejaría de tener respuesta justo cuando
alguien la necesita.

**Esto es lo que resuelve A9, y sin flag.** La corrida canónica de un ciclo es
la que referencia su informe publicado. No hay `es_canonica` que mantener
sincronizado ni que pueda acabar en dos filas a la vez.

No se pregunta si archivar: la regla es que solo puede haber uno vigente, y un
índice único parcial lo garantiza en la base. Preguntar abriría la puerta al
estado que no debe existir.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from territorial.almacen.modelos import (
    CorridaAgentes,
    CorridaScoring,
    Informe,
    Insight,
    Usuario,
)
from territorial.config import Config
from territorial.informes.composicion import componer
from territorial.informes.gerencias import TIPO_PRD
from territorial.informes.gerencias import cargar as cargar_gerencias


class PublicacionInvalida(ValueError):
    """No se publica. Mejor no publicar que publicar algo que no se sostiene."""


def _exigir_completa(corrida: CorridaScoring | CorridaAgentes, que: str) -> None:
    """Una corrida parcial no se publica.

    `scoring/persistencia.py` ya lo dice al insertarla: «ninguna vista de
    gerencia debe leer esta corrida». Una parcial recalculó unos municipios y
    los demás arrastran datos de otra, así que su ranking mezcla dos momentos.

    **El mensaje dice cuán parcial**, y no es cosmético: una corrida con 17 de
    18 municipios y otra con 1 de 18 son las dos «parcial», y lo que hay que
    hacer con cada una es distinto. Hoy el ciclo 2 solo tiene una corrida de
    agentes, con **1 de 18**: no se corrió nunca entero.
    """
    if corrida.tipo_corrida == "completa":
        return
    hechos = len(corrida.municipios_en_cohorte or [])
    total = len(corrida.municipios_objetivo or [])
    raise PublicacionInvalida(
        f"la corrida de {que} {corrida.id} es «{corrida.tipo_corrida}»: "
        f"{hechos} de {total} municipios. Recalcula el ciclo entero antes de "
        "publicar — un informe sobre una corrida parcial mezcla municipios de "
        "dos momentos, y los que falten arrastran datos de otra corrida."
    )


def _corrio_la_cadena(sesion_bd: Session, id_corrida: int) -> bool:
    """¿Esa corrida de agentes pasó por el Clasificador, o solo por M4?

    **`tipo_corrida` dice cuántos municipios se cubrieron, no qué pasos se
    corrieron**, y esa diferencia tiene una trampa concreta: las corridas 11 y
    12 del ciclo 3 están marcadas «completa» —cubren los 18— y contienen **cero
    insights del Clasificador**. Las creó `comparar_correlacionador.py
    --persistir`, que solo guarda correlaciones.

    Publicar una de esas daría un informe con las convergencias y **sin los
    insights individuales**, que son el grueso de lo que la gerencia lee. Nada
    lo habría advertido: el tipo de corrida es correcto, solo que no significa
    lo que parece.
    """
    return bool(
        sesion_bd.scalar(
            select(Insight.id)
            .where(Insight.id_corrida == id_corrida, Insight.origen == "clasificador")
            .limit(1)
        )
    )


def ciclos_publicables(sesion_bd: Session) -> dict[int, dict]:
    """Qué ciclos se pueden publicar hoy, y qué le falta a cada uno.

    Existe para poder preguntar **antes** de intentarlo. El caso que la motiva
    es real y no estaba escrito en ninguna parte: el **ciclo 2 nunca se corrió
    entero**, así que no es publicable por mucho que tenga scoring completo.
    Sin esto, la única forma de enterarse era intentar publicar y leer el error.
    """
    ciclos: dict[int, dict] = {}
    for modelo, clave in ((CorridaScoring, "scoring"), (CorridaAgentes, "agentes")):
        for corrida in sesion_bd.scalars(select(modelo)).all():
            caja = ciclos.setdefault(
                corrida.id_ciclo, {"scoring": None, "agentes": None}
            )
            if corrida.tipo_corrida != "completa":
                continue
            # Una corrida de agentes que no paso por el Clasificador no sirve
            # aunque cubra los 18 municipios. Ver `_corrio_la_cadena`.
            if clave == "agentes" and not _corrio_la_cadena(sesion_bd, corrida.id):
                continue
            # La más reciente que valga, de cada tipo.
            if caja[clave] is None or corrida.id > caja[clave]:
                caja[clave] = corrida.id

    for caja in ciclos.values():
        caja["publicable"] = caja["scoring"] is not None and caja["agentes"] is not None
        caja["falta"] = [k for k in ("scoring", "agentes") if caja[k] is None]
    return dict(sorted(ciclos.items()))


def informe_vigente(sesion_bd: Session, id_ciclo: int) -> Informe | None:
    """El informe publicado del ciclo, si lo hay. Define la corrida canónica."""
    return sesion_bd.scalars(
        select(Informe).where(
            Informe.id_ciclo == id_ciclo, Informe.estado == "publicado"
        )
    ).one_or_none()


def commit_actual() -> str | None:
    """El commit del árbol de trabajo, o `None` si no se puede saber.

    No lanza: que no haya git no es razón para no publicar, pero sí para que el
    informe lo diga. Un `origen` con `commit: null` es un hecho registrado; un
    `origen` ausente es una laguna.
    """
    try:
        salida = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[3],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return salida.stdout.strip() or None


def exigir_calificadores(sesion_bd: Session, config: Config | None = None) -> list[str]:
    """Que haya quien pueda calificar lo que se va a publicar. Devuelve las «prd».

    **Por qué es una guarda de publicación y no un aviso.** El denominador de H2
    se congela al publicar (F0.1). Publicar sin calificadores produce un informe
    cuyo denominador es incompleto para siempre: la tasa de respuesta de ese
    ciclo se calcularía sobre quien estuviera dado de alta en ese instante, y
    dar de alta a alguien después **no lo arregla** —habría que republicar—.
    Más vale no publicar.

    Dos condiciones, y **ningún número fijo en el código**: el conjunto sale de
    `config/gerencias.json` y de la tabla `usuario`. Si mañana el núcleo son
    seis gerencias en vez de cinco, esto no se toca.
    """
    catalogo = cargar_gerencias(config)
    prd = sorted(g.id_gerencia for g in catalogo.values() if g.tipo == TIPO_PRD)
    if not prd:
        raise PublicacionInvalida(
            "no hay ninguna gerencia «prd» declarada en config/gerencias.json, así "
            "que H2 no se podría reportar sobre nadie. Declara el núcleo antes de "
            "publicar."
        )

    con_calificador = set(
        sesion_bd.scalars(
            select(Usuario.id_gerencia).where(
                Usuario.activo.is_(True), Usuario.rol == "gerencia"
            ).distinct()
        ).all()
    )
    huerfanas = [g for g in prd if g not in con_calificador]
    if huerfanas:
        raise PublicacionInvalida(
            f"estas gerencias «prd» no tienen ningún usuario activo con rol "
            f"«gerencia»: {huerfanas}. Su denominador de H2 quedaría congelado sin "
            "nadie que pueda responder. Carga los usuarios antes de publicar "
            "(scripts/cargar_usuarios.py)."
        )
    return prd


def publicar(
    sesion_bd: Session,
    id_corrida_scoring: int,
    id_corrida_agentes: int,
    config: Config | None = None,
    tope_calificable: int = 3,
    invocacion: str | None = None,
) -> Informe:
    """Compone, archiva el anterior y publica. Devuelve el informe nuevo."""
    exigir_calificadores(sesion_bd, config)
    contenido = componer(
        sesion_bd, id_corrida_scoring, id_corrida_agentes,
        config=config, tope_calificable=tope_calificable,
    )
    id_ciclo = contenido["ciclo"]

    _exigir_completa(sesion_bd.get(CorridaScoring, id_corrida_scoring), "scoring")
    _exigir_completa(sesion_bd.get(CorridaAgentes, id_corrida_agentes), "agentes")
    if not _corrio_la_cadena(sesion_bd, id_corrida_agentes):
        raise PublicacionInvalida(
            f"la corrida de agentes {id_corrida_agentes} no tiene ni un insight "
            "del Clasificador: cubre los municipios pero **no corrió la cadena "
            "entera**. Suele ser una corrida de comparación persistida con "
            "`comparar_correlacionador.py --persistir`, que solo guarda "
            "correlaciones. Publicarla daría un informe con las convergencias y "
            "sin los insights individuales. Usa `ciclos_publicables()` para ver "
            "cuál sirve."
        )

    if not contenido["municipios"]:
        raise PublicacionInvalida(
            f"la corrida de scoring {id_corrida_scoring} no deja ningún municipio "
            "que mostrar. Un informe vacío no es un informe."
        )

    anterior = informe_vigente(sesion_bd, id_ciclo)
    if anterior is not None:
        anterior.estado = "archivado"
        # **El flush va aquí y no al final.** El índice único parcial solo
        # admite un `publicado` por ciclo: si el nuevo se insertara antes de que
        # el viejo quede archivado, la base lo rechazaría.
        sesion_bd.flush()

    informe = Informe(
        id_ciclo=id_ciclo,
        id_corrida=id_corrida_scoring,
        id_corrida_agentes=id_corrida_agentes,
        contenido=contenido,
        # H-040: con qué código y por qué vía se compuso esto. Va fuera del
        # payload a propósito — el payload tiene que salir idéntico en dos
        # motores para poder compararse, y el commit no es parte de lo que se
        # compone sino de cómo se compuso.
        origen={
            "commit": commit_actual(),
            "invocacion": invocacion or "publicar() directo",
            "publicado_en": datetime.now(timezone.utc).isoformat(),
        },
        estado="publicado",
    )
    sesion_bd.add(informe)
    sesion_bd.flush()
    return informe
