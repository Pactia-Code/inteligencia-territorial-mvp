"""Entorno de Alembic (regla 2 de D8).

Dos decisiones que importan aquí:

1. **La URL no vive en alembic.ini.** Sale de `Config.url_base_datos`, igual que
   para el resto de la aplicación, porque D8 exige que la misma capa de datos
   sirva a SQLite en local y a PostgreSQL en nube. Duplicar la URL en el .ini
   sería la forma más fácil de que los dos entornos se separen sin avisar.

2. **`render_as_batch=True`.** SQLite no sabe hacer casi ningún `ALTER TABLE`:
   no puede eliminar una columna, cambiarle el tipo ni añadir una restricción.
   El modo batch recrea la tabla y copia los datos. Sin esto, la primera
   migración que toque una columna existente falla en local y pasa en nube, que
   es justo la divergencia que D8 quiere evitar.
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import create_engine

from alembic import context
from territorial.almacen.modelos import Base
from territorial.almacen.sesion import obtener_motor

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# El autogenerate compara contra esto. Importar `modelos` completo es lo que
# puebla el metadata: una entidad que no se importe aquí no se migra.
target_metadata = Base.metadata


def _motor():
    """Motor contra el que se migra.

    Si quien invoca fijó `sqlalchemy.url` en la configuración —lo hace
    `aplicar_migraciones` para no arrastrar la base global— se respeta. Si no
    (uso normal por CLI), se usa el motor de la aplicación.
    """
    url = config.get_main_option("sqlalchemy.url", None)
    if url:
        return create_engine(url, future=True)
    return obtener_motor()


def _url() -> str:
    """URL efectiva, ya resuelta a ruta absoluta."""
    return _motor().url.render_as_string(hide_password=False)


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse, para revisarlo antes de aplicarlo."""
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica las migraciones contra el motor de la aplicación.

    Se reutiliza `obtener_motor` en vez de crear uno nuevo para que el PRAGMA
    de claves foráneas de SQLite quede activo también durante la migración.
    """
    motor = _motor()
    with motor.connect() as conexion:
        context.configure(
            connection=conexion,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
