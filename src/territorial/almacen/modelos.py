"""Esquema relacional del MVP (PRD §4.2, con el linaje de Addendum 02 D7).

Regla de D8: todo pasa por SQLAlchemy y el tipo JSON portátil. Nada de
operadores JSONB de Postgres (->>, @>, jsonb_path_query), o SQLite deja de
servir como entorno local.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    validates,
)


def ahora() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


# --------------------------------------------------------------------------
# Linaje (Addendum 02, D7 — cubre el versionado con linaje de dataset)
# --------------------------------------------------------------------------


class VersionDataset(Base):
    """Un snapshot inmutable en el almacén de objetos, anclado por su hash."""

    __tablename__ = "dataset_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    uri_blob: Mapped[str] = mapped_column(Text)
    hash_sha256: Mapped[str] = mapped_column(String(64), unique=True)
    n_registros: Mapped[int | None] = mapped_column(Integer)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class VersionPrompt(Base):
    """Una versión de prompt de agente, archivada en el almacén de objetos."""

    __tablename__ = "prompt_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    agente: Mapped[str] = mapped_column(String(40))
    version: Mapped[str] = mapped_column(String(20))
    uri_blob: Mapped[str] = mapped_column(Text)
    hash_sha256: Mapped[str] = mapped_column(String(64))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    __table_args__ = (UniqueConstraint("agente", "version", name="uq_prompt_agente_version"),)


# --------------------------------------------------------------------------
# Entidades del dominio
# --------------------------------------------------------------------------


class Municipio(Base):
    __tablename__ = "municipio"

    divipola: Mapped[str] = mapped_column(String(5), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    departamento: Mapped[str] = mapped_column(String(80))
    corredores: Mapped[list] = mapped_column(JSON, default=list)
    # Contexto ELIC: constante en los 3 ciclos (Addendum 01, D2/R3)
    elic: Mapped[dict | None] = mapped_column(JSON)

    __table_args__ = (
        CheckConstraint("length(divipola) = 5", name="ck_divipola_5_chars"),
    )


# --------------------------------------------------------------------------
# Nomenclátor DIVIPOLA — tabla maestra de referencia
# --------------------------------------------------------------------------


class EntidadDivipola(Base):
    """Las 1.135 entidades territoriales del nomenclátor, según TerriData.

    **No amplía el universo del MVP.** Los 18 municipios que el experimento
    procesa siguen en `municipio`, y esta tabla **no tiene ninguna relación con
    ella** a propósito: el MVP valida el mecanismo, no la cobertura (PRD §7).
    Una clave foránea entre las dos sugeriría lo contrario.

    Se codifica igual que TerriData, para que un `join` futuro no necesite
    traducir nada:

        nacional      01001   Colombia
        departamento  05000   código de departamento + '000'
        municipio     05001

    Cuatro rarezas del nomenclátor, escritas aquí porque van a confundir a
    alguien que cuente filas y no le cuadren:

    · **Son 1.102 municipios, no 1.103.** Falta San Andrés (88001); del
      departamento 88 solo está Providencia (88564).
    · **Bogotá aparece solo como municipio** (11001). No existe la fila 11000,
      así que los departamentos son **32 y no 33**.
    · **Las áreas no municipalizadas no están.**
    · **63 nombres se repiten entre departamentos** y afectan a 144 municipios,
      el 13%. Resolver por nombre suelto es inviable: el par (departamento,
      municipio) es obligatorio. Hay cuatro «La Unión» y cuatro «Buenavista».
    """

    __tablename__ = "entidad_divipola"

    codigo: Mapped[str] = mapped_column(String(5), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    codigo_departamento: Mapped[str] = mapped_column(String(2), index=True)
    nombre_departamento: Mapped[str] = mapped_column(String(80))
    tipo: Mapped[str] = mapped_column(String(12))

    __table_args__ = (
        CheckConstraint("length(codigo) = 5", name="ck_entidad_divipola_5_chars"),
        CheckConstraint(
            "tipo IN ('nacional', 'departamento', 'municipio')",
            name="ck_entidad_divipola_tipo",
        ),
    )


class ContextoMunicipal(Base):
    """Contexto estructural del municipio: DANE/TerriData, anual.

    **No entra al scoring, y no es un descuido.** Todos estos indicadores son
    anuales, así que dentro de los tres ciclos del MVP serían idénticos en los
    tres — exactamente el defecto de F4, que era una constante ocupando el 18%
    del peso y que hubo que corregir. El catastro es el más tentador y por eso
    mismo el más peligroso. El score prioriza por lo que pasa en la ventana.

    Donde sí entra es en el **Correlacionador**, y **bandeado, nunca crudo**:
    lo que llega al prompt es «déficit alto», no un número. Ver
    `reglas/contexto.py`. Un número real escrito por el modelo sigue siendo un
    número escrito por el modelo, y CA-M6.3 lo prohíbe.

    Las cifras **sí** van al informe, compuestas por código desde esta tabla y
    con su año a la vista: un informe de 2026 que muestre déficit del censo
    2018 necesita que el 2018 se lea, o alguien lo tomará por dato de hoy.

    Dos cosas del origen que conviene saber antes de usar los campos:

    · **El déficit es un PORCENTAJE de hogares, no un conteo.** TerriData lo
      entrega como «Porcentaje (el valor está multiplicado por 100)». A nivel
      municipal está congelado en el censo **2018**; solo Bogotá tiene 2024.
    · **La población es la proyección DANE**, y la serie llega hasta **2070**.
      Se fija el año a propósito en vez de tomar el último disponible, que
      sería una proyección a 44 años vista.
    """

    __tablename__ = "contexto_municipal"

    codigo_divipola: Mapped[str] = mapped_column(String(5), primary_key=True)

    poblacion_total: Mapped[int | None] = mapped_column(Integer)
    anio_poblacion: Mapped[int | None] = mapped_column(Integer)

    # Miles de millones de pesos corrientes. Serie nueva (120210001), base 2015.
    valor_agregado: Mapped[float | None] = mapped_column(Float)
    anio_valor_agregado: Mapped[int | None] = mapped_column(Integer)

    # Porcentaje de hogares, no conteo. Censo 2018.
    deficit_cuantitativo: Mapped[float | None] = mapped_column(Float)
    deficit_cualitativo: Mapped[float | None] = mapped_column(Float)
    anio_deficit: Mapped[int | None] = mapped_column(Integer)

    # Millones de pesos corrientes, y conteo de predios.
    avaluo_catastral_urbano: Mapped[float | None] = mapped_column(Float)
    predios_urbanos: Mapped[int | None] = mapped_column(Integer)
    anio_catastro: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        CheckConstraint(
            "length(codigo_divipola) = 5", name="ck_contexto_municipal_5_chars"
        ),
    )


class Ciclo(Base):
    __tablename__ = "ciclo"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha_desde: Mapped[date] = mapped_column(Date)
    fecha_hasta: Mapped[date] = mapped_column(Date)
    id_dataset: Mapped[int | None] = mapped_column(ForeignKey("dataset_version.id"))
    n_senales: Mapped[int] = mapped_column(Integer, default=0)
    n_insights: Mapped[int] = mapped_column(Integer, default=0)
    n_validados: Mapped[int] = mapped_column(Integer, default=0)
    n_rechazados: Mapped[int] = mapped_column(Integer, default=0)
    costo_tokens: Mapped[float] = mapped_column(Float, default=0.0)
    duracion_seg: Mapped[float | None] = mapped_column(Float)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class SenalCruda(Base):
    __tablename__ = "senal_cruda"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_ciclo: Mapped[int] = mapped_column(ForeignKey("ciclo.id"), index=True)
    divipola: Mapped[str] = mapped_column(ForeignKey("municipio.divipola"), index=True)
    fuente: Mapped[str] = mapped_column(String(20), index=True)  # SECOP II | RSS | ELIC | Bing
    id_externo: Mapped[str | None] = mapped_column(String(120))
    fecha_publicacion: Mapped[date | None] = mapped_column(Date, index=True)
    contenido: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    hash_dedup: Mapped[str] = mapped_column(String(64), index=True)
    # Lo voluminoso vive en el almacén de objetos; aquí solo el puntero (D7).
    uri_blob: Mapped[str | None] = mapped_column(Text)
    datos: Mapped[dict | None] = mapped_column(JSON)
    capturado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    __table_args__ = (
        UniqueConstraint("id_ciclo", "hash_dedup", name="uq_senal_ciclo_hash"),
    )


class CorridaAgentes(Base):
    """Una pasada de la cadena de agentes. **Nada se sobrescribe.**

    El hermano de `CorridaScoring` un nivel más abajo. Los insights vivían como
    atributo de `(ciclo, municipio, origen)` y una segunda pasada **borraba** la
    primera, así que dos pasadas del mismo ciclo no podían compararse — que es
    justo lo que el pendiente A6 necesita medir.

    Y tenía una segunda cara peor: `calificacion.id_insight` apunta a
    `insight.id`. Mientras no hubiera calificaciones no mordía, pero desde que
    exista M7 un reproceso habría borrado los insights que las gerencias
    calificaron. Es el mismo agujero de H4 que se cerró para el ranking,
    esperando a la semana 7 para aparecer.

    Leer una calificación lleva ahora a su insight, y el insight a la corrida
    bajo la que nació.
    """

    __tablename__ = "corrida_agentes"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_ciclo: Mapped[int] = mapped_column(ForeignKey("ciclo.id"), index=True)
    fecha_corrida: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    # `completa` si la cohorte cubrió todos los municipios objetivo. Aquí sí se
    # ejercita: el Clasificador se puede correr sobre un solo municipio.
    tipo_corrida: Mapped[str] = mapped_column(String(10), default="completa", index=True)

    # Las **dos** listas, como en `corrida_scoring`: `tipo_corrida` se decide
    # comparándolas, y guardar solo la cohorte haría imposible auditar una
    # corrida vieja después de que alguien añada un municipio.
    municipios_objetivo: Mapped[list] = mapped_column(JSON, default=list)
    municipios_en_cohorte: Mapped[list] = mapped_column(JSON, default=list)

    # Versiones de prompt que corrieron. El linaje por contenido —hash y blob—
    # está en `prompt_version` (D7); esto es la etiqueta.
    version_clasificador: Mapped[str | None] = mapped_column(String(20))
    version_correlacionador: Mapped[str | None] = mapped_column(String(20))

    # Qué **cadena** corrió, que no es lo mismo que qué prompt. Dos pasadas con
    # el mismo `version_clasificador` pueden no ser comparables si entre ellas
    # cambió qué señales entran al agente.
    #
    #   p1  solo SECOP II, con prefiltro.
    #   p2  SECOP II con prefiltro **+ RSS sin filtro**, en lotes separados.
    #       RSS quedaba fuera por tres barreras —un filtro por fuente, la
    #       lectura de `datos["objeto"]` que RSS no tiene, y el diccionario de
    #       obra— y las 336 señales se perdían sin que ningún log lo dijera.
    #
    # Se sube a mano, como `VERSION_ALGORITMO` en el scoring y por lo mismo: el
    # prompt no cambió, así que nada automático lo detectaría.
    version_pipeline: Mapped[str | None] = mapped_column(String(20), index=True)

    # Para auditar CA-M2.1 sin recontar: cuántas señales entraron al agente.
    senales_procesadas: Mapped[int] = mapped_column(Integer, default=0)
    tokens_entrada: Mapped[int] = mapped_column(Integer, default=0)
    tokens_salida: Mapped[int] = mapped_column(Integer, default=0)

    insights: Mapped[list[Insight]] = relationship(back_populates="corrida")

    __table_args__ = (
        CheckConstraint(
            "tipo_corrida IN ('completa', 'parcial')", name="ck_tipo_corrida_agentes"
        ),
    )


class Insight(Base):
    """Un insight **de una pasada**, no del par (ciclo, municipio).

    No lleva `id_ciclo`: el ciclo es de la corrida. Denormalizarlo permitiría
    que una fila discrepara de su propia pasada, igual que en `score_municipio`.
    """

    __tablename__ = "insight"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_corrida: Mapped[int] = mapped_column(ForeignKey("corrida_agentes.id"), index=True)
    divipola: Mapped[str] = mapped_column(ForeignKey("municipio.divipola"), index=True)
    categoria: Mapped[str] = mapped_column(String(60))
    resumen: Mapped[str] = mapped_column(Text)
    implicacion_inmobiliaria: Mapped[str | None] = mapped_column(Text)
    # [{url, fecha, cita_textual, fuente}] — CA-M3.1 exige los tres primeros.
    evidencia: Mapped[list] = mapped_column(JSON, default=list)
    ids_senal: Mapped[list] = mapped_column(JSON, default=list)
    estado_validacion: Mapped[str] = mapped_column(String(20), default="pendiente")
    motivo_rechazo: Mapped[str | None] = mapped_column(Text)  # CA-M3.2
    # Addendum 01, D1: Bing puede dar contexto, nunca evidencia.
    contexto_no_verificado: Mapped[bool] = mapped_column(default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    # --- Qué agente lo produjo (M2 o M4) ---
    origen: Mapped[str] = mapped_column(String(20), default="clasificador", index=True)
    # Versión del prompt que lo generó. La **etiqueta**.
    version_prompt: Mapped[str | None] = mapped_column(String(20))
    # La fila de linaje, anclada por hash del contenido (D7). La etiqueta sola
    # no ancla nada: editar `clasificador_v4.md` sin renombrarlo dejaría todos
    # los insights diciendo v4 para dos contenidos distintos, y con dos pasadas
    # del mismo ciclo no habría forma de descartar que el prompt cambió entre
    # una y otra — que es justo lo que A6 necesita poder descartar.
    id_prompt: Mapped[int | None] = mapped_column(
        ForeignKey("prompt_version.id"), index=True
    )

    # --- Solo para los consolidados por el Correlacionador ---
    # De qué insights salió. **Es la trazabilidad de CA-M4.4 en la base**: sin
    # esto, un consolidado no se puede deshacer hasta sus insights de origen.
    ids_insight_origen: Mapped[list] = mapped_column(JSON, default=list)
    por_que_convergen: Mapped[str | None] = mapped_column(Text)
    confianza: Mapped[str | None] = mapped_column(String(10))

    corrida: Mapped[CorridaAgentes] = relationship(back_populates="insights")
    calificaciones: Mapped[list[Calificacion]] = relationship(back_populates="insight")

    __table_args__ = (
        CheckConstraint(
            "estado_validacion IN ('pendiente', 'validado', 'rechazado')",
            name="ck_estado_validacion",
        ),
        CheckConstraint(
            "origen IN ('clasificador', 'correlacionador')",
            name="ck_origen_insight",
        ),
        CheckConstraint(
            "confianza IS NULL OR confianza IN ('alta', 'media', 'baja')",
            name="ck_confianza",
        ),
    )


class Descarte(Base):
    """Una señal que el Clasificador no convirtió en insight (CA-M2.5).

    El criterio exige **registrar en la traza qué se descartó y por qué**. El
    agente producía `descartes` con su motivo y `ciclo.py` los tiraba: la tasa
    de reducción de CA-M2.1 no era auditable, porque solo quedaba el numerador
    —los insights— y el denominador se perdía con el proceso.

    Cuelga de la corrida, no del par (ciclo, municipio): dos pasadas descartan
    cosas distintas, y comparar qué descartó cada una es parte de medir A6.
    """

    __tablename__ = "descarte"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_corrida: Mapped[int] = mapped_column(ForeignKey("corrida_agentes.id"), index=True)
    id_senal: Mapped[int] = mapped_column(ForeignKey("senal_cruda.id"), index=True)
    motivo: Mapped[str] = mapped_column(Text)
    # False cuando el modelo **no mencionó** la señal: ni insight ni descarte.
    # Es `sin_contabilizar`, y se guarda porque una señal que desaparece sin
    # motivo es peor que una descartada con uno malo — CA-M2.5 no se cumple
    # dejándola fuera del registro.
    declarado: Mapped[bool] = mapped_column(default=True, index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    __table_args__ = (
        UniqueConstraint("id_corrida", "id_senal", name="uq_descarte_corrida_senal"),
    )


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_gerencia: Mapped[str] = mapped_column(String(60), index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    correo: Mapped[str] = mapped_column(String(160), unique=True)
    rol: Mapped[str] = mapped_column(String(20), default="gerencia")
    activo: Mapped[bool] = mapped_column(default=True)

    __table_args__ = (
        CheckConstraint("rol IN ('gerencia', 'administrador')", name="ck_rol"),
    )


class Calificacion(Base):
    __tablename__ = "calificacion"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_insight: Mapped[int] = mapped_column(ForeignKey("insight.id"), index=True)
    id_gerencia: Mapped[str] = mapped_column(String(60), index=True)
    valor: Mapped[int] = mapped_column(Integer)
    comentario: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    insight: Mapped[Insight] = relationship(back_populates="calificaciones")

    __table_args__ = (
        # CA-M7.2: una calificación por gerencia por insight.
        UniqueConstraint("id_insight", "id_gerencia", name="uq_calificacion_insight_gerencia"),
        CheckConstraint("valor BETWEEN 1 AND 5", name="ck_valor_1_5"),
    )


class CorridaScoring(Base):
    """Una ejecución del scoring. **Nada se sobrescribe: cada corrida es una fila.**

    El score se normaliza min-max dentro de la cohorte, así que **solo es
    comparable contra los de su propia corrida**. Mientras el score vivió como
    atributo de `(ciclo, municipio)`, cualquier recálculo pisaba el ranking
    anterior en su sitio: un informe publicado empezaba a mostrar un orden
    distinto del que las gerencias calificaron, y no quedaba forma de
    reconstruir el original. Eso rompe H4, que es bloqueante.

    El score deja de ser un atributo del municipio y pasa a ser **un hecho de
    una corrida**.
    """

    __tablename__ = "corrida_scoring"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_ciclo: Mapped[int] = mapped_column(ForeignKey("ciclo.id"), index=True)
    fecha_corrida: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    # `completa` si la cohorte cubrió todos los municipios objetivo.
    tipo_corrida: Mapped[str] = mapped_column(String(10), default="completa", index=True)

    # Ventana del ciclo, declarada por configuración (D2).
    ventana_desde: Mapped[date | None] = mapped_column(Date)
    ventana_hasta: Mapped[date | None] = mapped_column(Date)

    # Hasta dónde llega la comparabilidad del conjunto: el **mínimo** de la
    # última fecha observada por municipio. Se computa **solo con SECOP II**,
    # que es de donde salen F1, F2 y F3.
    #
    # Se eligió el criterio conservador porque los dos errores posibles no
    # cuestan lo mismo: decir enero cuando hay noticias hasta junio hace
    # desconfiar de una corrida buena —molesto y recuperable—, mientras que
    # decir junio cuando la contratación se corta en enero hace comparar dos
    # corridas como equivalentes sin que nada en la auditoría lo delate.
    #
    # Se computa sobre los municipios **que tienen fecha**, no sobre todos.
    # Propagar la ausencia al conjunto haría que el ciclo 3 saliera siempre
    # NULL por Barranquilla, Armenia y Cartagena, que no están ciegos: tienen
    # noticias hasta agosto, julio y junio, lo que no tienen es contratación.
    # Sería el mismo error que el defecto de F5 (pendiente A7), tratar la
    # ausencia de SECOP como ausencia de datos, y dejaría inútil en un tercio
    # de los ciclos un campo cuyo trabajo es auditar.
    #
    # **NULL es un valor legítimo, no un pendiente**, y queda reservado para el
    # caso real de que **ningún** municipio tenga fecha, más las corridas
    # migradas, anteriores a que el campo existiera. Ningún lector debe
    # interpretarlo como «sin restricción de comparabilidad»: es lo contrario.
    # Una corrida sin corte conocido es la **menos** comparable de todas.
    fecha_corte_cohorte: Mapped[date | None] = mapped_column(Date)
    # Los de la cohorte que no aportaron ni una fecha de SECOP. La
    # incertidumbre queda declarada como lista explícita en vez de aniquilar
    # el campo de arriba: leído después, dice «estos 15 son comparables hasta
    # enero; estos 3 no aportaron contratación», que es la verdad completa.
    municipios_sin_fecha: Mapped[list] = mapped_column(JSON, default=list)
    # {fuente: {corte, municipios_con_fecha}} — el corte de cada fuente por
    # separado, con el mismo criterio de mínimo. Responde sola la pregunta
    # "¿por qué esta corrida dice enero si hay noticias de junio?", y el conteo
    # evita leer igual un corte apoyado en un municipio que en dieciocho.
    #
    # **Informativo: no alimenta ningún factor.** Medido sobre el snapshot, RSS
    # no es uniformemente más fresco que SECOP — en los ciclos 1 y 2 corta
    # antes y solo llega a 11 y 14 de los 18 municipios.
    corte_por_fuente: Mapped[dict] = mapped_column(JSON, default=dict)

    # Las **dos** listas, completas. `tipo_corrida` se decide comparándolas, y
    # guardar solo la cohorte haría imposible auditar una corrida vieja después
    # de que alguien añada un municipio: la marca dejaría de ser reverificable.
    municipios_objetivo: Mapped[list] = mapped_column(JSON, default=list)
    municipios_en_cohorte: Mapped[list] = mapped_column(JSON, default=list)

    # "v1+a3f9c1d2": versión del algoritmo + huella de los pesos. La constante
    # se sube a mano cuando cambia la fórmula; el hash se mueve solo cuando
    # cambian los pesos. Hacen falta las dos: el arreglo de F5 (pendiente A7)
    # cambia el algoritmo sin tocar un solo peso.
    #
    # **No se puede agrupar por igualdad de esta cadena** asumiendo «mismo
    # algoritmo y mismos pesos». Las corridas migradas llevan `v1+migrado`, que
    # no coincide con ningún `v1+<hash>` aunque el algoritmo sí sea el mismo:
    # de ellas simplemente no se sabe con qué pesos corrieron.
    version_scoring: Mapped[str | None] = mapped_column(String(40), index=True)
    # Los pesos **verbatim**, no solo su hash. Un hash dice que algo cambió,
    # no qué cambió, y calibrar el umbral con la curva de scores exige leerlos
    # sin arqueología.
    pesos: Mapped[dict] = mapped_column(JSON, default=dict)

    scores: Mapped[list[ScoreMunicipio]] = relationship(back_populates="corrida")

    __table_args__ = (
        CheckConstraint(
            "tipo_corrida IN ('completa', 'parcial')", name="ck_tipo_corrida"
        ),
    )


class ScoreMunicipio(Base):
    """Score de un municipio **en una corrida**, con el desglose de CA-M5.5.

    No lleva `id_ciclo`: el ciclo es de la corrida. Denormalizarlo permitiría
    que una fila discrepara de su propia corrida, y no hay consulta que lo
    necesite sin pasar por ella.
    """

    __tablename__ = "score_municipio"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_corrida: Mapped[int] = mapped_column(ForeignKey("corrida_scoring.id"), index=True)
    divipola: Mapped[str] = mapped_column(ForeignKey("municipio.divipola"), index=True)

    # **El score es ORDINAL dentro de su corrida, no una magnitud.** Sale de
    # normalizar min-max contra la cohorte, así que un 0,80 significa «de los
    # puntuados en esta corrida, está arriba» y **nada más**: no es comparable
    # con el 0,80 de otro ciclo ni de otra corrida. Sirve para ordenar y para
    # elegir el top 3, que es para lo que lo usa CA-M5.4.
    #
    # La escala absoluta no se ancló porque habría que inventar los topes sin
    # datos (decisión de Analítica, pendiente A5). Para construirla en la
    # semana 8 con 3 ciclos de evidencia están los valores crudos de abajo.
    score: Mapped[float] = mapped_column(Float)
    ranking: Mapped[int | None] = mapped_column(Integer)
    # {factor: {valor, peso, aporte, sin_cobertura}} — Addendum 01, D4.
    factores: Mapped[dict] = mapped_column(JSON, default=dict)
    # {F1: 0.4762, F2: 2765698367.1, ...} — los factores **sin normalizar**.
    #
    # **Es el mismo dato que `factores["aportes"][i]["crudo"]`**, en plano. Se
    # duplica a propósito: construir una escala absoluta desde un array anidado
    # obliga a un script, y desde una columna plana es un `SELECT`. La
    # comparación entre corridas —que es el punto entero de guardarlos— pasa de
    # programa a consulta.
    #
    # Los escribe `scoring/persistencia.guardar()` en el mismo sitio y a partir
    # de la misma fuente, así que no pueden desincronizarse sin tocar esa
    # función. **Si alguien cambia uno, tiene que cambiar el otro.**
    valores_crudos: Mapped[dict] = mapped_column(JSON, default=dict)
    dias_cubiertos: Mapped[int | None] = mapped_column(Integer)
    dias_ventana: Mapped[int | None] = mapped_column(Integer)
    sin_cobertura: Mapped[bool] = mapped_column(default=False)
    # La de **este** municipio, no la de la cohorte. Solo SECOP II.
    ultima_fecha_captura: Mapped[date | None] = mapped_column(Date)

    corrida: Mapped[CorridaScoring] = relationship(back_populates="scores")

    __table_args__ = (
        UniqueConstraint("id_corrida", "divipola", name="uq_score_corrida_municipio"),
    )


class Seguimiento(Base):
    """Tabla de historial: cada cambio inserta una fila (PRD §4.2)."""

    __tablename__ = "seguimiento"

    id: Mapped[int] = mapped_column(primary_key=True)
    divipola: Mapped[str] = mapped_column(ForeignKey("municipio.divipola"), index=True)
    id_ciclo_origen: Mapped[int] = mapped_column(ForeignKey("ciclo.id"))
    estado: Mapped[str] = mapped_column(String(30))
    nota: Mapped[str | None] = mapped_column(Text)
    id_usuario: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    fecha_cambio: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    __table_args__ = (
        CheckConstraint(
            "estado IN ('priorizado', 'en_revision', 'en_estructuracion', 'descartado')",
            name="ck_estado_seguimiento",
        ),
    )


class Informe(Base):
    """Un informe publicado, atado a la corrida de scoring que lo sustenta.

    **`id_corrida` se fija al publicar y no se reescribe.** El informe y su top
    3 leen siempre su propia corrida, nunca «la más reciente»: si leyeran la
    última, un recálculo posterior cambiaría el ranking que las gerencias ya
    calificaron, y las calificaciones quedarían colgando de un orden que nadie
    puede reconstruir.

    Corregir un informe no es editarlo: el viejo pasa a `archivado` y el
    corregido entra como fila nueva con su propia corrida. Ambos quedan
    consultables, y la divergencia entre los dos es auditable.
    """

    __tablename__ = "informe"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_ciclo: Mapped[int] = mapped_column(ForeignKey("ciclo.id"), index=True)
    # Nullable solo porque M6 todavía no existe; al publicar es obligatoria.
    id_corrida: Mapped[int | None] = mapped_column(
        ForeignKey("corrida_scoring.id"), index=True
    )
    uri_html: Mapped[str] = mapped_column(Text)
    infografias: Mapped[list] = mapped_column(JSON, default=list)  # [{divipola, uri}]
    estado: Mapped[str] = mapped_column(String(20), default="publicado")
    fecha_publicacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    __table_args__ = (
        CheckConstraint(
            "estado IN ('publicado', 'archivado')", name="ck_estado_informe"
        ),
    )

    @validates("id_corrida")
    def _congelar_corrida(self, _clave: str, valor: int | None) -> int | None:
        """Impide reapuntar un informe a otra corrida.

        Se aplica en la capa ORM y no con un trigger porque la regla 1 de D8
        exige que todo pase por SQLAlchemy, y un trigger divergiría entre
        SQLite y PostgreSQL. **Limitación conocida:** un `UPDATE` crudo lo
        saltaría; el proyecto no emite SQL crudo.
        """
        actual = getattr(self, "id_corrida", None)
        if actual is not None and valor != actual:
            raise ValueError(
                f"informe {self.id}: id_corrida es inmutable (era {actual}, se intentó "
                f"{valor}). Para corregir un informe, archívalo y publica uno nuevo."
            )
        return valor


class TrazaAgente(Base):
    """CA-M8.2 y CA-M8.3. Amarra cada corrida a su dataset, prompt y modelo (D7)."""

    __tablename__ = "traza_agente"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_ciclo: Mapped[int] = mapped_column(ForeignKey("ciclo.id"), index=True)
    agente: Mapped[str] = mapped_column(String(40), index=True)
    modelo: Mapped[str | None] = mapped_column(String(80))
    id_prompt: Mapped[int | None] = mapped_column(ForeignKey("prompt_version.id"))
    id_dataset: Mapped[int | None] = mapped_column(ForeignKey("dataset_version.id"))
    hash_input: Mapped[str | None] = mapped_column(String(64))
    hash_output: Mapped[str | None] = mapped_column(String(64))
    tokens_entrada: Mapped[int | None] = mapped_column(Integer)
    tokens_salida: Mapped[int | None] = mapped_column(Integer)
    tokens_cache_lectura: Mapped[int | None] = mapped_column(Integer)
    duracion_ms: Mapped[int | None] = mapped_column(Integer)
    id_traza_langfuse: Mapped[str | None] = mapped_column(String(80))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
