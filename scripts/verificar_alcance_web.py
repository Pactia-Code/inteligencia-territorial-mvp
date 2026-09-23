r"""Verifica el alcance de escritura de M9 con la app corriendo (F0.4, H-013).

**Qué hace y por qué así.** Invoca los formularios de la app **como lo haría un
navegador sin JavaScript**: el mismo POST multipart que Next renderiza para la
mejora progresiva. No se simula la capa de servidor ni se llama a las funciones
por dentro, así que lo que se comprueba es el camino real — cookie firmada,
Server Action, consulta de alcance y escritura.

**Solo contra un branch de Neon, nunca contra la base principal.** Escribe una
calificación de prueba en el caso que debe aceptar. Necesita:

  · un branch con las migraciones aplicadas y un informe publicado **con la
    lista de gerencias congelada** (si no la lleva, todo se rechaza, que es el
    comportamiento conservador de F0.4 y no un fallo);
  · usuarios de prueba: uno con rol `gerencia` en esa lista, un
    `administrador`, y uno de una gerencia dada de alta **después** de publicar;
  · la app levantada contra ese branch:

        cd web
        DATABASE_URL="<cadena del branch>&connect_timeout=5"         COOKIE_SECRET="<cualquiera>" npx next dev --port 3100

Los identificadores de insight se pasan por línea de órdenes porque dependen de
qué corridas tenga el branch.
"""
import json
import re
import sys

from urllib.parse import unquote

import httpx

BASE = "http://localhost:3100"
PAG = "/ciclo/3?m=73001"

# Valores por defecto: los del branch `remediacion-f0` el 2026-09-22.
INSIGHT_VALIDO = int(sys.argv[1]) if len(sys.argv) > 1 else 834
INSIGHT_CICLO_CERRADO = int(sys.argv[2]) if len(sys.argv) > 2 else 416
INSIGHT_SIN_INFORME = int(sys.argv[3]) if len(sys.argv) > 3 else 1148


def campos_de_accion(html: str, n: int) -> dict:
    """Los campos ocultos con que Next invoca la accion n-esima de la pagina."""
    ref = f"$ACTION_REF_{n}"
    if f'name="{ref}"' not in html:
        return {}
    campos = {ref: ""}
    for clave in (f"$ACTION_{n}:0", f"$ACTION_{n}:1"):
        m = re.search(rf'name="{re.escape(clave)}" value="([^"]*)"', html)
        if m:
            campos[clave] = m.group(1).replace("&quot;", '"').replace("&amp;", "&")
    m = re.search(r'name="\$ACTION_KEY" value="([^"]*)"', html)
    if m:
        campos["$ACTION_KEY"] = m.group(1)
    return campos


def acciones_de(html: str) -> list[dict]:
    return [c for n in range(1, 12) if (c := campos_de_accion(html, n))]


def post(cliente: httpx.Client, campos: dict, extra: dict) -> str:
    datos = {**campos, **extra}
    r = cliente.post(BASE + PAG, files={k: (None, v) for k, v in datos.items()},
                     headers={"Accept": "text/x-component"}, timeout=120)
    return r.text


def veredicto(respuesta: str) -> str:
    m = re.search(r"No se guard\\u00f3[^\"]*", respuesta) or re.search(r"No se guardó[^\"]*", respuesta)
    if m:
        return "RECHAZA -> " + m.group(0).encode().decode("unicode_escape")[:95]
    if "Calificación registrada" in respuesta or "registrada" in respuesta:
        return "ACEPTA"
    return "sin mensaje reconocible"


def sesion_de(correo: str) -> httpx.Client:
    c = httpx.Client(follow_redirects=True, timeout=120)
    html = c.get(BASE + PAG).text
    campos = acciones_de(html)
    assert campos, "no se encontro el formulario de identificacion"
    post(c, campos[0], {"correo": correo})
    return c


print("=== 1. identificacion y cookie firmada")
for correo in ("prueba@territorial.local", "admin@territorial.local",
               "tardio@territorial.local", "intruso@otraempresa.com"):
    c = sesion_de(correo)
    galleta = c.cookies.get("correo") or ""
    firmada = "|" in unquote(galleta)
    print(f"  {correo:<30} cookie: "
          f"{'firmada, ' + str(len(galleta)) + ' car.' if firmada else 'NO se emite'}")
    c.close()

print("\n=== 2. calificar con las Server Actions corriendo")
casos = [
    ("gerencia en la lista congelada", "prueba@territorial.local", INSIGHT_VALIDO),
    ("ADMINISTRADOR", "admin@territorial.local", INSIGHT_VALIDO),
    ("gerencia dada de alta DESPUES de publicar", "tardio@territorial.local", INSIGHT_VALIDO),
    ("insight de la corrida 11 (sin informe)", "prueba@territorial.local", INSIGHT_SIN_INFORME),
    ("insight de ciclo CERRADO (ciclo 1)", "prueba@territorial.local", INSIGHT_CICLO_CERRADO),
]
for etiqueta, correo, insight in casos:
    c = sesion_de(correo)
    html = c.get(BASE + PAG).text
    formularios = acciones_de(html)
    # Con identidad, la primera accion de la pagina ya es calificar.
    campos = formularios[0]
    r = post(c, campos, {"id_insight": str(insight), "valor": "4"})
    print(f"  {etiqueta:<45} {veredicto(r)}")
    c.close()
