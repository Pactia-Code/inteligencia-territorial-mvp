"""Cliente LLM contra Azure OpenAI en el tenant de Pactia (Addendum 02, D6).

Un único punto de construcción del cliente, para que los cuatro agentes no
repitan credenciales ni criterios de reintento.

Nota sobre Azure: el parámetro `model` de las llamadas espera el **nombre del
despliegue**, no el del modelo. Son cosas distintas y es el error más común.
"""

from __future__ import annotations

from functools import lru_cache

from territorial.config import Config, obtener_config


class ConfiguracionLLMIncompleta(RuntimeError):
    """Falta la clave o el endpoint de Azure OpenAI en el .env."""


def construir_cliente(config: Config | None = None):
    """Devuelve un AzureOpenAI listo para usar.

    Se importa el SDK dentro de la función para que la capa determinista
    (ingesta, validador, scoring) siga funcionando sin tenerlo instalado.
    """
    cfg = config or obtener_config()

    if not cfg.azure_openai_api_key:
        raise ConfiguracionLLMIncompleta(
            "Falta AZURE_OPENAI_API_KEY en el .env. "
            "Corre: python scripts/verificar_llm.py"
        )
    if not cfg.azure_openai_endpoint:
        raise ConfiguracionLLMIncompleta(
            "Falta AZURE_OPENAI_ENDPOINT en el .env. "
            "Debe ser la URL completa, por ejemplo "
            "https://nombre-del-recurso.openai.azure.com"
        )

    try:
        from openai import AzureOpenAI
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise RuntimeError(
            "Falta el SDK de OpenAI. Instálalo con: uv pip install 'openai>=1.50'"
        ) from exc

    return AzureOpenAI(
        api_key=cfg.azure_openai_api_key,
        azure_endpoint=cfg.azure_openai_endpoint.rstrip("/"),
        api_version=cfg.azure_openai_api_version,
    )


@lru_cache
def cliente_compartido():
    """Cliente único para todo el proceso. Reutiliza la conexión HTTP."""
    return construir_cliente()


def despliegue_de(agente: str, config: Config | None = None) -> str:
    """Nombre del despliegue Azure que corresponde a cada agente."""
    cfg = config or obtener_config()
    mapa = {
        "clasificador": cfg.modelo_clasificador,
        "correlacionador": cfg.modelo_correlacionador,
        "sintetizador": cfg.modelo_sintetizador,
    }
    if agente not in mapa:
        raise KeyError(f"agente desconocido: {agente!r}. Opciones: {sorted(mapa)}")
    return mapa[agente]
