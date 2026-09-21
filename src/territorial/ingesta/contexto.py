"""Extrae el contexto municipal de TerriData por streaming (capa determinista).

El archivo son **3,31 GB y 14,5 millones de filas** con 1.750 indicadores. Se
lee comprimido y de una sola pasada, quedándose con seis indicadores y con un
año de cada uno. No se extrae: descomprimirlo para leer el 0,05% sería absurdo.

De los 1.750 indicadores se cargan **seis**, porque son los que el
Correlacionador puede usar para explicar una implicación inmobiliaria. El resto
responde preguntas que nadie está haciendo.

Cinco trampas del formato, todas encontradas mirando el archivo:

1. **Decimales con coma y miles con punto**: `7.945.996,00`. Leerlo con
   `float()` directo da 7.945 o revienta, según el número.
2. **Filas duplicadas.** 1.101 municipios traen la misma fila dos veces en
   déficit cuantitativo 2018. Se deduplica por (entidad, indicador, año).
3. **Series viejas y nuevas del mismo concepto conviven** con códigos
   distintos: valor agregado `120010012` (base 2005, hasta 2015) y `120210001`
   (hasta 2023). Se usa la nueva.
4. **`delineación` (150050003) no sirve**: es binario SÍ/NO, dice si el
   municipio cobra el impuesto, no cuánto.
5. **La población es una proyección que llega a 2070.** «El último año
   disponible» daría una proyección a 44 años vista, así que para este
   indicador el año se **fija**. Es la única excepción a la regla, y está
   aquí porque la regla sola daba un resultado absurdo.

El déficit es un **porcentaje de hogares**, no un conteo: TerriData lo entrega
como «Porcentaje (el valor está multiplicado por 100)». A nivel municipal está
congelado en el censo 2018.
"""

from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

# Nombre de la columna en la cabecera de TerriData.
COL_ENTIDAD = "Código Entidad"
COL_INDICADOR = "Código Indicador"
COL_VALOR = "Dato Numérico"
COL_ANIO = "Año"
SEPARADOR = "|"


@dataclass(frozen=True)
class Indicador:
    """Un indicador de TerriData y a qué campo de `contexto_municipal` va."""

    codigo: str
    campo: str
    campo_anio: str
    # Si se fija, se toma **ese** año y no el último. Ver la trampa 5.
    anio_fijo: int | None = None
    entero: bool = False


INDICADORES: tuple[Indicador, ...] = (
    # La proyección DANE llega a 2070: sin año fijo tomaríamos 2070.
    Indicador("010010009", "poblacion_total", "anio_poblacion", anio_fijo=2026, entero=True),
    # Serie nueva, base 2015. La vieja (120010012) muere en 2015.
    Indicador("120210001", "valor_agregado", "anio_valor_agregado"),
    # Porcentaje de hogares. Censo 2018.
    Indicador("030010008", "deficit_cuantitativo", "anio_deficit"),
    Indicador("030010009", "deficit_cualitativo", "anio_deficit"),
    # Millones de pesos corrientes y conteo de predios.
    Indicador("150070005", "avaluo_catastral_urbano", "anio_catastro"),
    Indicador("150070002", "predios_urbanos", "anio_catastro", entero=True),
)

POR_CODIGO = {i.codigo: i for i in INDICADORES}


@dataclass
class Conteos:
    """Lo que pasó durante la pasada. Se reporta; los duplicados importan."""

    filas_leidas: int = 0
    filas_usadas: int = 0
    duplicados: int = 0
    no_numericos: int = 0
    municipios: int = 0
    por_indicador: dict[str, int] = field(default_factory=dict)
    anios_elegidos: dict[str, int] = field(default_factory=dict)


def a_numero(crudo: str) -> float | None:
    """`7.945.996,00` -> 7945996.0. Devuelve None si no hay número.

    El punto es separador de miles y la coma es decimal. Hacerlo al revés es
    silencioso: `32.991,69` se convierte en 32,99 y nadie lo nota.
    """
    texto = (crudo or "").strip()
    if not texto:
        return None
    try:
        return float(texto.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def es_municipio(codigo_entidad: str) -> bool:
    """Municipio, no departamento (`dd000`) ni nacional (`01001`)."""
    return (
        len(codigo_entidad) == 5
        and codigo_entidad.isdigit()
        and not codigo_entidad.endswith("000")
        and codigo_entidad != "01001"
    )


def extraer(ruta_zip: Path) -> tuple[dict[str, dict], Conteos]:
    """Una pasada por el zip. Devuelve {divipola: {campo: valor}} y los conteos.

    Por cada (municipio, indicador) se guarda el valor del año más alto, salvo
    los indicadores con `anio_fijo`. La deduplicación sale gratis de quedarse
    con un valor por año: la segunda fila idéntica simplemente no gana.
    """
    datos: dict[str, dict] = {}
    # (divipola, codigo) -> (anio, valor), para resolver el «último año».
    mejor: dict[tuple[str, str], tuple[int, float]] = {}
    c = Conteos()

    z = zipfile.ZipFile(ruta_zip)
    interno = z.infolist()[0].filename
    with z.open(interno) as f:
        tx = io.TextIOWrapper(f, encoding="utf-8", errors="replace", newline="")
        lector = csv.DictReader(tx, delimiter=SEPARADOR)
        for fila in lector:
            c.filas_leidas += 1
            codigo = fila[COL_INDICADOR]
            ind = POR_CODIGO.get(codigo)
            if ind is None:
                continue
            entidad = fila[COL_ENTIDAD]
            if not es_municipio(entidad):
                continue

            try:
                anio = int(fila[COL_ANIO])
            except (TypeError, ValueError):
                continue
            if ind.anio_fijo is not None and anio != ind.anio_fijo:
                continue

            valor = a_numero(fila[COL_VALOR])
            if valor is None:
                c.no_numericos += 1
                continue

            clave = (entidad, codigo)
            previo = mejor.get(clave)
            if previo is not None:
                if previo[0] > anio:
                    continue
                if previo[0] == anio:
                    # Misma entidad, mismo indicador, mismo año: es la fila
                    # repetida. Se cuenta y se ignora.
                    c.duplicados += 1
                    continue
            mejor[clave] = (anio, valor)
            c.filas_usadas += 1

    for (entidad, codigo), (anio, valor) in mejor.items():
        ind = POR_CODIGO[codigo]
        caja = datos.setdefault(entidad, {"codigo_divipola": entidad})
        caja[ind.campo] = int(round(valor)) if ind.entero else valor
        caja[ind.campo_anio] = anio
        c.por_indicador[codigo] = c.por_indicador.get(codigo, 0) + 1
        c.anios_elegidos[codigo] = anio

    c.municipios = len(datos)
    return datos, c
