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
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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

    calificaciones: Mapped[list[Calificacion]] = relationship(back_populates="insight")

    __table_args__ = (
        CheckConstraint(
            "estado_validacion IN ('pendiente', 'validado', 'rechazado')",
            name="ck_estado_validacion",
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


class ScoreMunicipio(Base):
    """Score por municipio y ciclo, con el desglose que exige CA-M5.5."""

    __tablename__ = "score_municipio"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_ciclo: Mapped[int] = mapped_column(ForeignKey("ciclo.id"), index=True)
    divipola: Mapped[str] = mapped_column(ForeignKey("municipio.divipola"), index=True)
    score: Mapped[float] = mapped_column(Float)
    ranking: Mapped[int | None] = mapped_column(Integer)
    # {factor: {valor, peso, aporte, sin_cobertura}} — Addendum 01, D4.
    factores: Mapped[dict] = mapped_column(JSON, default=dict)
    dias_cubiertos: Mapped[int | None] = mapped_column(Integer)
    dias_ventana: Mapped[int | None] = mapped_column(Integer)
    sin_cobertura: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (
        UniqueConstraint("id_ciclo", "divipola", name="uq_score_ciclo_municipio"),
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
    __tablename__ = "informe"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_ciclo: Mapped[int] = mapped_column(ForeignKey("ciclo.id"), index=True)
    uri_html: Mapped[str] = mapped_column(Text)
    infografias: Mapped[list] = mapped_column(JSON, default=list)  # [{divipola, uri}]
    estado: Mapped[str] = mapped_column(String(20), default="publicado")
    fecha_publicacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


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
