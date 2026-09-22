"""Cuáles de las gerencias que califican son las 7 del PRD y cuáles se añadieron.

F0.1b de la remediación, que amplía H-005. F0.1 congeló **quién** podía
calificar cuando se publicó cada informe; esto añade **de qué clase es cada
uno**, porque el dueño decidió el 2026-09-22 que el conjunto de calificadores
**no se cierra a las 7 gerencias del PRD** y puede incluir gerencias
adicionales, por ejemplo Analítica.

**Por qué hace falta la marca y no basta con la lista.** H2 se reporta siempre
sobre **las 7 del PRD** y los adicionales **por separado**; H1, con y sin ellos.
Sin la marca congelada junto a la lista, esas dos cifras no se pueden separar
después: habría que reconstruir meses más tarde quién era quién, que es
exactamente el problema que F0.1 vino a resolver. Y hay un motivo concreto para
poder separarlas: **el operador del pipeline también califica**, así que sus
calificaciones tienen un conflicto de interés en H1 y deben poder aislarse
(decisión c del dueño).

Por qué un archivo de configuración y no una columna en `usuario`
-----------------------------------------------------------------
Se eligió lo más simple de las dos opciones que el dueño planteó:

· **Ser una de las 7 es una propiedad del diseño del experimento, no de una
  persona.** Dos usuarios de la misma gerencia no pueden discrepar sobre la
  marca, y una columna por usuario permite justamente eso: una fila marcada
  `prd` y otra `adicional` para la misma `id_gerencia`. El archivo lo hace
  imposible por construcción.
· **No necesita migración** ni regenerar el contrato de TypeScript.
· Es el mismo patrón que `config/pesos.json` (CA-M5.3): una palanca editable
  sin tocar código, versionada y revisable en el repositorio.
· **Los nombres de las gerencias no son datos personales**, así que el archivo
  sí puede vivir en git — al contrario que el CSV de usuarios, que no viaja
  (decisión d).

**El archivo se entrega vacío, y es a propósito: el PRD nunca nombra las 7.**
Habla de «las 7 gerencias» y de «7 perfiles de gerencia + 1 administrador»
(§1, §2.2, CA-M9.1) sin dar ni un `id_gerencia`. Inventarlos aquí sería fabricar
línea base. **Mientras la lista esté vacía, toda gerencia sale `adicional`**, que
es visible en el payload y es una de las cosas a comprobar antes de la
republicación definitiva de F0.6: la lista se llena al decidir quién califica,
que por decisión (a) ocurre antes de esa republicación.
"""

from __future__ import annotations

import json

from territorial.config import Config, obtener_config

TIPO_PRD = "prd"
TIPO_ADICIONAL = "adicional"

# El PRD no nombra las 7. Ver el encabezado: el valor por defecto es vacío
# porque no hay línea base que copiar, no porque falte cargarlo.
GERENCIAS_PRD_POR_DEFECTO: frozenset[str] = frozenset()


class GerenciasInvalidas(ValueError):
    """El archivo de gerencias no cumple el contrato. Mejor fallar que marcar mal."""


def cargar_prd(config: Config | None = None) -> frozenset[str]:
    """Las `id_gerencia` que son de las 7 del PRD, según `config/gerencias.json`.

    Formato: `{"prd": ["comercial", "activos", ...]}`. Las claves que empiezan
    por `_` se ignoran, que es como se dejan notas en un JSON sin comentarios.
    Si el archivo no existe, no hay ninguna declarada.
    """
    cfg = config or obtener_config()
    ruta = cfg.ruta_absoluta(cfg.ruta_gerencias)
    if not ruta.exists():
        return GERENCIAS_PRD_POR_DEFECTO

    try:
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise GerenciasInvalidas(f"{ruta} no es JSON válido: {e}") from e

    if not isinstance(contenido, dict):
        raise GerenciasInvalidas(f'{ruta}: se esperaba un objeto {{"prd": [...]}}')

    desconocidas = sorted(
        k for k in contenido if k != "prd" and not k.startswith("_")
    )
    if desconocidas:
        raise GerenciasInvalidas(
            f"{ruta}: claves desconocidas {desconocidas}. Solo «prd» (y notas «_…»)"
        )

    crudas = contenido.get("prd", [])
    if not isinstance(crudas, list) or not all(isinstance(g, str) for g in crudas):
        raise GerenciasInvalidas(f'{ruta}: «prd» debe ser una lista de id_gerencia')

    limpias = [g.strip() for g in crudas]
    if any(not g for g in limpias):
        raise GerenciasInvalidas(f"{ruta}: hay una id_gerencia vacía en «prd»")

    repes = sorted({g for g in limpias if limpias.count(g) > 1})
    if repes:
        raise GerenciasInvalidas(f"{ruta}: id_gerencia repetidas en «prd»: {repes}")

    return frozenset(limpias)


def clasificar(id_gerencia: str, prd: frozenset[str]) -> str:
    """`prd` si es una de las 7 declaradas; `adicional` en cualquier otro caso.

    Solo dos valores, porque el reporte solo distingue dos cosas (decisión b).
    """
    return TIPO_PRD if id_gerencia in prd else TIPO_ADICIONAL
