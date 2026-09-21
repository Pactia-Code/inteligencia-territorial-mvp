"""Pruebas de cómo se resuelve la URL de la base (D8, migración a Neon).

Lo que se prueba aquí no es SQLAlchemy sino **las tres formas conocidas de
pegar mal una cadena de conexión**, que son las que cuestan una tarde:

  · la URL de Neon empieza por `postgresql://` y ese prefijo busca psycopg2,
    que no está instalado;
  · Neon publica un host `-pooler` que no sirve para migrar;
  · la ruta de SQLite es relativa y cambia según desde dónde se invoque.
"""

from __future__ import annotations

import pytest

from territorial.almacen.sesion import aplicar_migraciones, es_pooled, normalizar_url
from territorial.config import Config

NEON = "ep-royal-bird-12345.us-east-2.aws.neon.tech/territorial?sslmode=require"


@pytest.fixture
def cfg() -> Config:
    return Config()


def test_la_url_de_neon_se_reescribe_al_driver_instalado(cfg):
    """`postgresql://` busca psycopg2 y aquí hay psycopg 3."""
    url = normalizar_url(f"postgresql://usuario:clave@{NEON}", cfg)
    assert url.startswith("postgresql+psycopg://")
    # Lo demás no se toca: credenciales, host, base y parámetros.
    assert url.endswith(NEON)


def test_el_prefijo_corto_de_postgres_tambien(cfg):
    """Algunos proveedores entregan `postgres://`, que SQLAlchemy ni reconoce."""
    assert normalizar_url(f"postgres://u:c@{NEON}", cfg).startswith("postgresql+psycopg://")


def test_una_url_ya_explicita_se_respeta(cfg):
    url = f"postgresql+psycopg://u:c@{NEON}"
    assert normalizar_url(url, cfg) == url


def test_la_ruta_de_sqlite_se_vuelve_absoluta(cfg):
    url = normalizar_url("sqlite:///data/territorial.db", cfg)
    assert url.startswith("sqlite:///")
    assert "data" in url
    # Sin esto, el mismo comando escribe en bases distintas segun el directorio.
    assert url != "sqlite:///data/territorial.db"


def test_se_reconoce_el_endpoint_pooled():
    assert es_pooled("postgresql://u:c@ep-royal-bird-12345-pooler.us-east-2.aws.neon.tech/t")
    assert not es_pooled(f"postgresql://u:c@{NEON}")


def test_no_se_migra_por_el_endpoint_pooled():
    """PgBouncer en modo transacción no conserva la sesión entre sentencias.

    Alembic se rompería a media migración, y el estado en que quedara la base
    dependería de por dónde fuera. Mejor negarse antes de empezar.
    """
    cfg = Config(url_base_datos="postgresql://u:c@ep-abc-pooler.aws.neon.tech/territorial")
    with pytest.raises(ValueError, match="pooled"):
        aplicar_migraciones(cfg)
