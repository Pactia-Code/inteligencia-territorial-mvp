"""Motor y sesiones de SQLAlchemy (Addendum 02, D8).

Local es SQLite; la nube es PostgreSQL —Neon hoy, Azure en el diseño original—.
La URL sale de `DATABASE_URL`, así que cambiar de base no toca código.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from territorial.config import Config, obtener_config

# Neon publica **dos** hosts para el mismo proyecto: el directo y uno con
# `-pooler`, que va por PgBouncer en modo transacción. Se distinguen solo por
# ese trozo del nombre, y es fácil copiar el que no es.
MARCA_POOLED = "-pooler."


def normalizar_url(url: str, cfg: Config) -> str:
    """Deja la URL lista para SQLAlchemy, venga de donde venga.

    Dos arreglos, los dos por pegar una URL tal cual la da su proveedor:

    · **SQLite** — la ruta se vuelve absoluta y se crea su carpeta, para que el
      script corra igual desde cualquier directorio.
    · **PostgreSQL** — Neon (y casi todos) entregan `postgresql://…`, y con ese
      prefijo SQLAlchemy busca **psycopg2**, que no está instalado; el que hay
      es psycopg 3. Se reescribe a `postgresql+psycopg://`. Sin esto el fallo
      es un `ModuleNotFoundError` que no menciona la base de datos.
    """
    prefijo = "sqlite:///"
    if url.startswith(prefijo):
        ruta = cfg.ruta_absoluta(Path(url[len(prefijo) :]))
        ruta.parent.mkdir(parents=True, exist_ok=True)
        return f"{prefijo}{ruta}"

    for viejo in ("postgresql://", "postgres://"):
        if url.startswith(viejo):
            return "postgresql+psycopg://" + url[len(viejo) :]

    return url


def es_pooled(url: str) -> bool:
    """¿La URL apunta al endpoint con PgBouncer delante?"""
    return MARCA_POOLED in url


# Un motor por URL. No se puede usar lru_cache sobre el Config: los modelos de
# pydantic no son hashables.
_motores: dict[str, Engine] = {}


def obtener_motor(config: Config | None = None) -> Engine:
    cfg = config or obtener_config()
    url = normalizar_url(cfg.url_base_datos, cfg)
    if url in _motores:
        return _motores[url]

    # `pool_pre_ping` solo en Postgres: una base gestionada cierra las
    # conexiones ociosas por su cuenta, y sin esto la primera consulta después
    # de un rato falla con la conexión cerrada en vez de reconectar. No es
    # configuración de pooling —eso sigue sin tocarse—, es descartar conexiones
    # muertas antes de usarlas.
    motor = create_engine(
        url, echo=False, future=True, pool_pre_ping=not url.startswith("sqlite")
    )

    if url.startswith("sqlite"):
        # SQLite no aplica claves foráneas si no se le pide explícitamente.
        @event.listens_for(motor, "connect")
        def _activar_fk(conexion, _record):  # pragma: no cover
            cur = conexion.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    _motores[url] = motor
    return motor


def aplicar_migraciones(config: Config | None = None) -> None:
    """Lleva la base al `head` de Alembic (regla 2 de D8).

    Sustituye al `create_all` que usaba el arranque del MVP. La diferencia no es
    cosmética: `create_all` crea lo que falta y **calla ante lo que cambió**, así
    que una columna con tipo distinto al del modelo sobrevive sin aviso. Alembic
    falla, que es lo que se quiere.

    Se invoca desde código, y no solo por CLI, porque la ingesta tiene que poder
    correr en un entorno recién clonado sin un paso manual previo.
    """
    from alembic.config import Config as ConfigAlembic

    from alembic import command

    cfg = config or obtener_config()
    ini = cfg.ruta_absoluta(Path("alembic.ini"))
    if not ini.exists():  # pragma: no cover
        raise FileNotFoundError(
            f"No se encontró {ini}. El esquema se gobierna con Alembic (regla 2 de D8); "
            "sin alembic.ini no hay forma de crearlo."
        )

    alembic_cfg = ConfigAlembic(str(ini))
    alembic_cfg.set_main_option("script_location", str(ini.parent / "alembic"))
    # Se pasa la URL de ESTE Config, no la global: si no, migrar una base de
    # prueba acabaría migrando la de desarrollo sin que nadie lo notara.
    url = normalizar_url(cfg.url_base_datos, cfg)
    if es_pooled(url):
        raise ValueError(
            "DATABASE_URL apunta al endpoint *pooled* (el host lleva "
            f"'{MARCA_POOLED}'), y por ahí no se migra. PgBouncer en modo "
            "transacción no conserva la sesión entre sentencias, así que los "
            "bloqueos de DDL y las transacciones de Alembic se rompen a media "
            "migración. Usa la conexión directa: el mismo host sin '-pooler'."
        )
    alembic_cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(alembic_cfg, "head")


@contextmanager
def sesion(config: Config | None = None) -> Iterator[Session]:
    """Sesión transaccional: confirma al salir, revierte si algo falla."""
    fabrica = sessionmaker(bind=obtener_motor(config), expire_on_commit=False)
    s = fabrica()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
