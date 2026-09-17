"""Carga del snapshot territorial (Addendum 01).

Aplica las decisiones ya tomadas:
  D1 — Bing se carga marcado como no verificable; no puede originar insights.
  D2 — las señales se reparten en 3 ciclos por la fecha de cada registro.
       ELIC y Bing no tienen fecha: son contexto constante, se atan al municipio.
  D3 — la PII de SECOP (proveedor, rep_legal) se conserva.
  D7 — DIVIPOLA se normaliza a 5 dígitos en ingesta.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from territorial.almacen.blob import Almacen, obtener_almacen
from territorial.almacen.modelos import Ciclo, Municipio, SenalCruda, VersionDataset
from territorial.almacen.sesion import aplicar_migraciones, sesion
from territorial.config import Config, obtener_config
from territorial.utiles.divipola import desde_bloque

# Fuentes sin fecha por registro: contexto constante en los 3 ciclos (D2, R3).
FUENTES_SIN_FECHA = {"ELIC", "Bing"}


@dataclass
class Resumen:
    municipios: int = 0
    senales_por_ciclo: dict[int, int] = field(default_factory=dict)
    senales_por_fuente: dict[str, int] = field(default_factory=dict)
    fuera_de_ventana: int = 0
    duplicadas: int = 0

    def __str__(self) -> str:
        lineas = [
            f"Municipios cargados      : {self.municipios}",
            f"Señales fuera de ventana : {self.fuera_de_ventana} (descartadas)",
            f"Señales duplicadas       : {self.duplicadas} (descartadas)",
            "",
            "Señales por ciclo:",
        ]
        for c in sorted(self.senales_por_ciclo):
            lineas.append(f"  ciclo {c}: {self.senales_por_ciclo[c]:>6}")
        lineas.append("")
        lineas.append("Señales por fuente:")
        for f in sorted(self.senales_por_fuente):
            lineas.append(f"  {f:<10}: {self.senales_por_fuente[f]:>6}")
        return "\n".join(lineas)


def _a_fecha(valor: Any) -> date | None:
    if not valor:
        return None
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def _hash(*partes: Any) -> str:
    crudo = "|".join("" if p is None else str(p) for p in partes)
    return hashlib.sha256(crudo.encode("utf-8")).hexdigest()


def _ciclo_de(fecha: date, ventanas: dict[int, tuple[date, date]]) -> int | None:
    for num, (desde, hasta) in ventanas.items():
        if desde <= fecha < hasta:
            return num
    return None


def _senales_del_municipio(
    muni: dict, divipola: str, ventanas: dict[int, tuple[date, date]]
) -> tuple[list[dict], int]:
    """Aplana las 4 fuentes de un municipio a señales, ya asignadas a ciclo."""
    senales: list[dict] = []
    fuera = 0

    # --- SECOP II: una señal por registro, fechada ---
    for reg in (muni.get("secop") or {}).get("registros", []):
        fecha = _a_fecha(reg.get("fecha"))
        ciclo = _ciclo_de(fecha, ventanas) if fecha else None
        if ciclo is None:
            fuera += 1
            continue
        senales.append(
            {
                "fuente": "SECOP II",
                "id_ciclo": ciclo,
                "id_externo": reg.get("id"),
                "fecha_publicacion": fecha,
                "contenido": reg.get("objeto") or "",
                "url": reg.get("url"),
                # D3: la PII se conserva tal como viene.
                "datos": reg,
                "hash_dedup": _hash("SECOP II", divipola, reg.get("id")),
            }
        )

    # --- RSS: solo las territoriales, fechadas ---
    for noticia in (muni.get("rss") or {}).get("noticias", []):
        fecha = _a_fecha(noticia.get("fecha"))
        ciclo = _ciclo_de(fecha, ventanas) if fecha else None
        if ciclo is None:
            fuera += 1
            continue
        senales.append(
            {
                "fuente": "RSS",
                "id_ciclo": ciclo,
                "id_externo": None,
                "fecha_publicacion": fecha,
                "contenido": noticia.get("titulo") or "",
                "url": noticia.get("link"),
                "datos": noticia,
                "hash_dedup": _hash("RSS", divipola, noticia.get("link")),
            }
        )

    # --- Bing: sin fecha, sin URL. Contexto no verificable en los 3 ciclos (D1) ---
    bing = muni.get("bing") or {}
    if bing.get("texto_completo"):
        for ciclo in ventanas:
            senales.append(
                {
                    "fuente": "Bing",
                    "id_ciclo": ciclo,
                    "id_externo": None,
                    "fecha_publicacion": None,
                    "contenido": bing["texto_completo"],
                    "url": None,
                    "datos": {"advertencia": bing.get("advertencia"), "no_verificable": True},
                    "hash_dedup": _hash("Bing", divipola, ciclo),
                }
            )

    return senales, fuera


def cargar(config: Config | None = None) -> Resumen:
    cfg = config or obtener_config()
    ventanas = cfg.ventanas_ciclo
    almacen: Almacen = obtener_almacen(cfg)

    ruta = cfg.ruta_absoluta(cfg.ruta_snapshot)
    crudo = ruta.read_bytes()
    datos = json.loads(crudo.decode("utf-8"))

    # Archiva el snapshot inmutable y ancla el linaje por hash (D7).
    uri = almacen.escribir_bytes(f"raw/{ruta.name}", crudo)
    huella = hashlib.sha256(crudo).hexdigest()

    aplicar_migraciones(cfg)
    resumen = Resumen()

    with sesion(cfg) as s:
        version = s.query(VersionDataset).filter_by(hash_sha256=huella).one_or_none()
        if version is None:
            version = VersionDataset(
                nombre=ruta.name,
                uri_blob=uri,
                hash_sha256=huella,
                n_registros=len(datos.get("municipios", [])),
            )
            s.add(version)
            s.flush()

        for num, (desde, hasta) in ventanas.items():
            if s.get(Ciclo, num) is None:
                s.add(
                    Ciclo(
                        id=num,
                        fecha_desde=desde,
                        fecha_hasta=hasta,
                        id_dataset=version.id,
                    )
                )
        s.flush()

        vistos: set[tuple[int, str]] = set()

        for muni in datos.get("municipios", []):
            divipola = desde_bloque(muni["cod_divipola"])
            resumen.municipios += 1

            if s.get(Municipio, divipola) is None:
                s.add(
                    Municipio(
                        divipola=divipola,
                        nombre=muni["municipio"],
                        departamento=muni["departamento"],
                        corredores=muni.get("corredores", []),
                        elic=muni.get("elic"),
                    )
                )
                s.flush()

            senales, fuera = _senales_del_municipio(muni, divipola, ventanas)
            resumen.fuera_de_ventana += fuera

            for sen in senales:
                clave = (sen["id_ciclo"], sen["hash_dedup"])
                if clave in vistos:
                    resumen.duplicadas += 1
                    continue
                vistos.add(clave)

                s.add(SenalCruda(divipola=divipola, **sen))
                resumen.senales_por_ciclo[sen["id_ciclo"]] = (
                    resumen.senales_por_ciclo.get(sen["id_ciclo"], 0) + 1
                )
                resumen.senales_por_fuente[sen["fuente"]] = (
                    resumen.senales_por_fuente.get(sen["fuente"], 0) + 1
                )

    return resumen
