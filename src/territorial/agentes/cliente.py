"""Cliente LLM contra Azure AI Foundry en el tenant de Pactia (Addendum 02, D6).

Un único punto de construcción del cliente, para que los cuatro agentes no
repitan credenciales ni criterios de reintento.

Se usa el cliente `OpenAI` con `base_url` apuntando a la superficie v1 de
Foundry, que es compatible con la API de OpenAI. **No** se usa `AzureOpenAI`:
esa clase es para la superficie clásica de Azure OpenAI, que tiene otra forma
de URL y exige `api_version`.

Las llamadas van por la **Responses API** (`client.responses.create`), no por
chat.completions.

Nota sobre Azure: el parámetro `model` espera el **nombre del despliegue**, no
el del modelo. Son cosas distintas y es el error más común.
"""

from __future__ import annotations

from functools import lru_cache

from territorial.config import Config, obtener_config

# La superficie v1 de Foundry vive bajo esta ruta. El SDK le añade el recurso
# concreto (/responses, /models), así que la base no debe incluirlo.
SUFIJO_BASE = "/openai/v1"


class ConfiguracionLLMIncompleta(RuntimeError):
    """Falta la clave o el endpoint en el .env."""


def normalizar_base_url(endpoint: str) -> str:
    """Deja el endpoint en la forma que espera el SDK.

    Tolera que venga con barra final o con el recurso ya pegado — pegarle
    `/responses` es el error más fácil de cometer al copiar del portal.
    """
    url = endpoint.strip().rstrip("/")
    for recurso in ("/responses", "/chat/completions", "/models"):
        if url.endswith(recurso):
            url = url[: -len(recurso)]
    if not url.endswith(SUFIJO_BASE):
        url = f"{url}{SUFIJO_BASE}"
    return url


def construir_cliente(config: Config | None = None):
    """Devuelve un cliente OpenAI apuntando al tenant de Pactia.

    El SDK se importa dentro de la función para que la capa determinista
    (ingesta, validador, scoring) siga funcionando sin tenerlo instalado.
    """
    cfg = config or obtener_config()

    if not cfg.azure_openai_api_key:
        raise ConfiguracionLLMIncompleta(
            "Falta AZURE_OPENAI_API_KEY en el .env. Corre: python scripts/verificar_llm.py"
        )
    if not cfg.azure_openai_endpoint:
        raise ConfiguracionLLMIncompleta(
            "Falta AZURE_OPENAI_ENDPOINT en el .env. Debe ser, por ejemplo, "
            "https://contratosai.services.ai.azure.com/openai/v1"
        )

    try:
        from openai import OpenAI
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise RuntimeError(
            "Falta el SDK de OpenAI. Instálalo con: uv pip install 'openai>=1.50'"
        ) from exc

    return OpenAI(
        api_key=cfg.azure_openai_api_key,
        base_url=normalizar_base_url(cfg.azure_openai_endpoint),
    )


@lru_cache
def cliente_compartido():
    """Cliente único para todo el proceso. Reutiliza la conexión HTTP."""
    return construir_cliente()


def despliegue_de(agente: str, config: Config | None = None) -> str:
    """Nombre del despliegue que corresponde a cada agente."""
    cfg = config or obtener_config()
    mapa = {
        "clasificador": cfg.modelo_clasificador,
        "correlacionador": cfg.modelo_correlacionador,
        "sintetizador": cfg.modelo_sintetizador,
    }
    if agente not in mapa:
        raise KeyError(f"agente desconocido: {agente!r}. Opciones: {sorted(mapa)}")
    return mapa[agente]


# Agentes que corren sobre un modelo de razonamiento. Gastan tokens de
# pensamiento que no aparecen en el texto pero sí en la factura, y un techo
# bajo los corta antes de que lleguen a escribir: la llamada vuelve vacía y sin
# error, que es la forma más difícil de diagnosticar (D6.2).
AGENTES_QUE_RAZONAN = frozenset({"correlacionador", "sintetizador"})


def techo_de(agente: str, config: Config | None = None) -> int:
    """Máximo de tokens de salida que corresponde a cada agente."""
    cfg = config or obtener_config()
    if agente in AGENTES_QUE_RAZONAN:
        return cfg.max_tokens_salida_razonamiento
    return cfg.max_tokens_salida


def texto_de(respuesta) -> str:
    """Extrae el texto de una respuesta de la Responses API.

    El SDK expone `output_text` como atajo, pero no en todas las versiones.
    Si no está, se recorre la estructura.
    """
    atajo = getattr(respuesta, "output_text", None)
    if atajo:
        return atajo

    partes: list[str] = []
    for bloque in getattr(respuesta, "output", []) or []:
        for contenido in getattr(bloque, "content", []) or []:
            if getattr(contenido, "type", None) == "output_text":
                partes.append(contenido.text)
    return "".join(partes).strip()
