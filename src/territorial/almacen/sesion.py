"""Motor y sesiones de SQLAlchemy (Addendum 02, D8).

Local es SQLite, Azure es PostgreSQL. La URL sale del .env, así que migrar
no toca código.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from territorial.almacen.modelos import Base
from territorial.config import Config, obtener_config


def _preparar_sqlite(url: str, cfg: Config) -> str:
    """Crea la carpeta del archivo .db y devuelve la URL con ruta absoluta."""
    prefijo = "sqlite:///"
    if not url.startswith(prefijo):
        return url
    ruta = Path(url[len(prefijo) :])
    ruta = cfg.ruta_absoluta(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    return f"{prefijo}{ruta}"


# Un motor por URL. No se puede usar lru_cache sobre el Config: los modelos de
# pydantic no son hashables.
_motores: dict[str, Engine] = {}


def obtener_motor(config: Config | None = None) -> Engine:
    cfg = config or obtener_config()
    url = _preparar_sqlite(cfg.url_base_datos, cfg)
    if url in _motores:
        return _motores[url]

    motor = create_engine(url, echo=False, future=True)

    if url.startswith("sqlite"):
        # SQLite no aplica claves foráneas si no se le pide explícitamente.
        @event.listens_for(motor, "connect")
        def _activar_fk(conexion, _record):  # pragma: no cover
            cur = conexion.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    _motores[url] = motor
    return motor


def crear_esquema(config: Config | None = None) -> None:
    """Crea las tablas que falten.

    Atajo para el arranque del MVP. A partir de la primera migración, el esquema
    lo gobierna Alembic (regla 2 de D8).
    """
    Base.metadata.create_all(obtener_motor(config))


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
