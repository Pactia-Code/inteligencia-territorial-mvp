"""El prompt que corre por defecto y lo que el repositorio dice que corre.

**Por qué esto merece una prueba.** El 2026-09-21 se promovió v2 del
Correlacionador cambiando una constante, y la promoción se quedó ahí: ninguna
corrida se ejecutó con v2, `prompt_version` nunca tuvo fila suya y el informe
publicado se compuso con v1. Durante un día, cuatro documentos afirmaban que v2
estaba vigente mientras lo publicado era v1 (hallazgo H-023, subfase F0.5).

Una constante de una línea puede cambiar qué modelo corre en el próximo ciclo,
y eso **no se ve en ninguna revisión de código a menos que alguien lo busque**.
Esta prueba ata las dos cosas: la constante y la frase del documento donde se
decide. Cambiar una sin la otra rompe el suite.

No comprueba que v1 sea mejor que v2 — eso es lo que hará F2.3, con linaje
persistido. Comprueba que **lo que corre y lo que está escrito digan lo mismo**.
"""

from __future__ import annotations

import re
from pathlib import Path

from territorial.agentes.correlacionador import (
    PROMPTS,
    VERSION_PROMPT,
    VERSIONES_CON_CONTEXTO,
)

RAIZ = Path(__file__).resolve().parents[1]
DECISIONES = RAIZ / "docs" / "decisiones-remediacion.md"
DECLARACION = re.compile(r"`VERSION_PROMPT = (v\d+)`")


def test_el_documento_declara_el_valor_por_defecto():
    """Si esta línea desaparece, la prueba deja de proteger nada."""
    declarados = DECLARACION.findall(DECISIONES.read_text(encoding="utf-8"))
    assert declarados, (
        "falta en docs/decisiones-remediacion.md la línea que declara el valor "
        "por defecto, con la forma `VERSION_PROMPT = vN`"
    )
    assert len(set(declarados)) == 1, (
        f"el documento declara más de un valor por defecto: {sorted(set(declarados))}"
    )


def test_lo_que_corre_es_lo_que_el_documento_dice_que_corre():
    """El caso que esto existe para impedir: cambiar el prompt en silencio."""
    declarado = DECLARACION.findall(DECISIONES.read_text(encoding="utf-8"))[0]
    assert VERSION_PROMPT == declarado, (
        f"el Correlacionador corre por defecto con «{VERSION_PROMPT}» y "
        f"docs/decisiones-remediacion.md dice «{declarado}». Cambiar el prompt "
        "por defecto es cambiar qué se publica en el próximo ciclo: actualiza el "
        "documento con el motivo, o devuelve la constante a su sitio."
    )


def test_v1_sigue_siendo_el_valor_por_defecto_hasta_F2_3():
    """La decisión vigente. Se cambia cuando F2.3 valide v2, no antes."""
    assert VERSION_PROMPT == "v1"


def test_las_dos_versiones_siguen_existiendo():
    """v2 no se borra: se conserva como opción explícita (y v1 como línea base)."""
    for version in ("v1", "v2"):
        assert (PROMPTS / f"correlacionador_{version}.md").exists()


def test_el_contexto_solo_viaja_con_las_versiones_que_lo_documentan():
    """Mandar el bloque a un prompt que no lo explica es peor que no mandarlo.

    Con v1 por defecto, el contexto **no viaja** — igual que en la corrida 10,
    que es la del informe publicado.
    """
    assert VERSION_PROMPT not in VERSIONES_CON_CONTEXTO
    assert VERSIONES_CON_CONTEXTO == frozenset({"v2"})
