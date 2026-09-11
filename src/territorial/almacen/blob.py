"""Almacén de objetos semi-estructurados (Addendum 02, D7 y D8).

Local usa carpetas; Azure usa Blob Storage. El código de negocio no distingue:
pide `obtener_almacen()` y escribe. Migrar de local a nube es cambiar
`MODO_ALMACEN` en el .env, no tocar código.

Regla de D7: aquí viven los objetos grandes, inmutables o binarios. La base SQL
guarda la URI que estos métodos devuelven, nunca el contenido.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from territorial.config import Config, obtener_config


class Almacen(ABC):
    """Interfaz común a local y Azure."""

    @abstractmethod
    def escribir_bytes(self, ruta: str, datos: bytes) -> str:
        """Escribe y devuelve la URI del objeto."""

    @abstractmethod
    def leer_bytes(self, ruta: str) -> bytes: ...

    @abstractmethod
    def existe(self, ruta: str) -> bool: ...

    @abstractmethod
    def uri(self, ruta: str) -> str: ...

    # --- Conveniencias comunes ---

    def escribir_texto(self, ruta: str, texto: str) -> str:
        return self.escribir_bytes(ruta, texto.encode("utf-8"))

    def leer_texto(self, ruta: str) -> str:
        return self.leer_bytes(ruta).decode("utf-8")

    def escribir_json(self, ruta: str, obj: Any) -> str:
        # sort_keys da bytes estables: el mismo contenido produce el mismo hash.
        texto = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2)
        return self.escribir_texto(ruta, texto)

    def leer_json(self, ruta: str) -> Any:
        return json.loads(self.leer_texto(ruta))

    def hash_de(self, ruta: str) -> str:
        """SHA-256 del objeto. Es la huella que ancla el linaje de dataset (D7)."""
        return hashlib.sha256(self.leer_bytes(ruta)).hexdigest()


class AlmacenLocal(Almacen):
    """Respaldado por una carpeta del disco."""

    def __init__(self, raiz: Path) -> None:
        self.raiz = raiz
        self.raiz.mkdir(parents=True, exist_ok=True)

    def _ruta(self, ruta: str) -> Path:
        destino = (self.raiz / ruta).resolve()
        raiz = self.raiz.resolve()
        if not destino.is_relative_to(raiz):
            raise ValueError(f"ruta fuera del almacén: {ruta!r}")
        return destino

    def escribir_bytes(self, ruta: str, datos: bytes) -> str:
        p = self._ruta(ruta)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(datos)
        return self.uri(ruta)

    def leer_bytes(self, ruta: str) -> bytes:
        return self._ruta(ruta).read_bytes()

    def existe(self, ruta: str) -> bool:
        return self._ruta(ruta).exists()

    def uri(self, ruta: str) -> str:
        return self._ruta(ruta).as_uri()


class AlmacenAzure(Almacen):
    """Respaldado por Azure Blob Storage. Requiere el extra `azure`."""

    def __init__(self, cadena_conexion: str, contenedor: str) -> None:
        try:
            from azure.storage.blob import ContainerClient
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError(
                "Falta azure-storage-blob. Instala el extra: uv pip install '.[azure]'"
            ) from exc

        self.contenedor = contenedor
        self._cliente = ContainerClient.from_connection_string(cadena_conexion, contenedor)
        if not self._cliente.exists():
            self._cliente.create_container()

    def escribir_bytes(self, ruta: str, datos: bytes) -> str:
        self._cliente.upload_blob(name=ruta, data=datos, overwrite=True)
        return self.uri(ruta)

    def leer_bytes(self, ruta: str) -> bytes:
        return self._cliente.download_blob(ruta).readall()

    def existe(self, ruta: str) -> bool:
        return self._cliente.get_blob_client(ruta).exists()

    def uri(self, ruta: str) -> str:
        return f"{self._cliente.url}/{ruta}"


def obtener_almacen(config: Config | None = None) -> Almacen:
    cfg = config or obtener_config()

    if cfg.modo_almacen == "local":
        return AlmacenLocal(cfg.ruta_absoluta(cfg.ruta_blob_local))

    if not cfg.azure_storage_connection_string:
        raise RuntimeError(
            "MODO_ALMACEN=azure pero AZURE_STORAGE_CONNECTION_STRING está vacío."
        )
    return AlmacenAzure(cfg.azure_storage_connection_string, cfg.azure_blob_contenedor)
