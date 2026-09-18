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


class Insight(Base):
    __tablename__ = "insight"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_ciclo: Mapped[int] = mapped_column(ForeignKey("ciclo.id"), index=True)
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
    # Versión del prompt que lo generó. Linaje de D7.
    version_prompt: Mapped[str | None] = mapped_column(String(20))

    # --- Solo para los consolidados por el Correlacionador ---
    # De qué insights salió. **Es la trazabilidad de CA-M4.4 en la base**: sin
    # esto, un consolidado no se puede deshacer hasta sus insights de origen.
    ids_insight_origen: Mapped[list] = mapped_column(JSON, default=list)
    por_que_convergen: Mapped[str | None] = mapped_column(Text)
    confianza: Mapped[str | None] = mapped_column(String(10))

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
    # {fuente: fecha} — el corte de cada fuente por separado. Responde sola la
    # pregunta "¿por qué esta corrida dice enero si hay noticias de junio?".
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
    score: Mapped[float] = mapped_column(Float)
    ranking: Mapped[int | None] = mapped_column(Integer)
    # {factor: {valor, peso, aporte, sin_cobertura}} — Addendum 01, D4.
    factores: Mapped[dict] = mapped_column(JSON, default=dict)
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
