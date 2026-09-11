"""Configuración del MVP, leída desde .env.

Las credenciales del LLM son opcionales a propósito: la ingesta del snapshot
y la carga a base de datos deben poder correr sin clave de Foundry.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ = Path(__file__).resolve().parents[2]


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=RAIZ / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM: Azure OpenAI (Addendum 02, D6) ---
    # Opcionales: la ingesta y la capa determinista no los necesitan.
    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_api_version: str = "2024-10-21"
    # Nombres de DESPLIEGUE en Azure, no nombres de modelo.
    modelo_clasificador: str = "gpt-4o-mini"
    modelo_correlacionador: str = "gpt-4o"
    modelo_sintetizador: str = "gpt-4o"

    # --- Observabilidad ---
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # --- Almacenamiento (Addendum 02, D7 y D8) ---
    modo_almacen: Literal["local", "azure"] = "local"
    ruta_blob_local: Path = Path("data/blob")
    url_base_datos: str = "sqlite:///data/territorial.db"
    azure_storage_connection_string: str | None = None
    azure_blob_contenedor: str = "territorial"

    # --- Parámetros del experimento (Addendum 01, D2) ---
    ruta_snapshot: Path = Path("docs/territorial_data_cruda_v3.json")
    ventana_inicio: date = date(2025, 9, 1)
    ciclo_corte_1: date = date(2025, 10, 22)
    ciclo_corte_2: date = date(2026, 1, 14)
    ventana_fin: date = date(2026, 9, 9)

    umbral_cobertura: float = Field(default=0.30, ge=0.0, le=1.0)

    @property
    def ventanas_ciclo(self) -> dict[int, tuple[date, date]]:
        """Ventanas [desde, hasta) de los 3 ciclos. El último día es inclusivo."""
        from datetime import timedelta

        fin_exclusivo = self.ventana_fin + timedelta(days=1)
        return {
            1: (self.ventana_inicio, self.ciclo_corte_1),
            2: (self.ciclo_corte_1, self.ciclo_corte_2),
            3: (self.ciclo_corte_2, fin_exclusivo),
        }

    def ruta_absoluta(self, ruta: Path) -> Path:
        """Resuelve una ruta relativa contra la raíz del repositorio."""
        return ruta if ruta.is_absolute() else RAIZ / ruta


@lru_cache
def obtener_config() -> Config:
    return Config()
