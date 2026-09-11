"""Comprueba que la configuración de Azure OpenAI está bien puesta y responde.

Hace tres cosas, en orden, y se detiene en la primera que falle:
  1. ¿Existe el .env y tiene los valores rellenados?
  2. ¿Se puede construir el cliente?
  3. ¿Responden los despliegues? (llamadas mínimas, de pocos centavos)

Uso:
    %LOCALAPPDATA%\\venvs\\territorial\\Scripts\\python.exe scripts\\verificar_llm.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from territorial.agentes.cliente import (  # noqa: E402
    ConfiguracionLLMIncompleta,
    construir_cliente,
)
from territorial.config import obtener_config  # noqa: E402

MARCADORES = {
    "",
    "pega-aqui-la-clave",
    "https://nombre-del-recurso.openai.azure.com",
    "nombre-del-recurso",
}


def main() -> int:
    print("=== 1. Configuración ===\n")

    env = RAIZ / ".env"
    if not env.exists():
        print(f"  FALTA el archivo {env}")
        print("  Créalo con:  Copy-Item .env.example .env")
        return 1
    print(f"  .env encontrado: {env}")

    cfg = obtener_config()

    if not cfg.azure_openai_api_key or cfg.azure_openai_api_key in MARCADORES:
        print("\n  AZURE_OPENAI_API_KEY sigue con el valor de ejemplo.")
        print("  Abre .env y reemplaza la línea:")
        print("      AZURE_OPENAI_API_KEY=pega-aqui-la-clave")
        return 1

    if not cfg.azure_openai_endpoint or cfg.azure_openai_endpoint in MARCADORES:
        print("\n  AZURE_OPENAI_ENDPOINT sigue con el valor de ejemplo.")
        print("  Abre .env y pon la URL completa de tu recurso, por ejemplo:")
        print("      AZURE_OPENAI_ENDPOINT=https://pactia-ia.openai.azure.com")
        return 1

    clave = cfg.azure_openai_api_key  # nunca se imprime completa
    print(f"  AZURE_OPENAI_API_KEY     : {clave[:6]}…{clave[-4:]}  ({len(clave)} caracteres)")
    print(f"  AZURE_OPENAI_ENDPOINT    : {cfg.azure_openai_endpoint}")
    print(f"  AZURE_OPENAI_API_VERSION : {cfg.azure_openai_api_version}")

    print("\n=== 2. Cliente ===\n")
    try:
        cliente = construir_cliente(cfg)
    except ConfiguracionLLMIncompleta as exc:
        print(f"  {exc}")
        return 1
    print("  Cliente AzureOpenAI construido.")

    print("\n=== 3. Despliegues ===\n")
    despliegues = {
        "clasificador": cfg.modelo_clasificador,
        "correlacionador": cfg.modelo_correlacionador,
        "sintetizador": cfg.modelo_sintetizador,
    }

    fallos = 0
    for agente, despliegue in despliegues.items():
        try:
            r = cliente.chat.completions.create(
                model=despliegue,
                max_completion_tokens=16,
                messages=[{"role": "user", "content": "Responde solo: ok"}],
            )
        except Exception as exc:
            fallos += 1
            print(f"  {agente:<16} {despliegue:<24} FALLÓ  {type(exc).__name__}")
            print(f"      {str(exc)[:180]}")
            continue

        uso = r.usage
        texto = (r.choices[0].message.content or "").strip()
        print(
            f"  {agente:<16} {despliegue:<24} OK  "
            f"respuesta={texto!r}  tokens={uso.prompt_tokens}+{uso.completion_tokens}"
        )

    if fallos:
        print(f"\n  {fallos} despliegue(s) fallaron. Revisa:")
        print("   · que el nombre sea el de la columna 'Deployment name' del portal,")
        print("     no el nombre del modelo")
        print("   · que AZURE_OPENAI_API_VERSION coincida con la del despliegue")
        print("   · que la clave corresponda a ese mismo recurso")
        return 1

    print("\n  Todo correcto. El Clasificador queda desbloqueado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
