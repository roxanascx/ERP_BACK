"""
Persistencia de los centros de costo.

Un documento por (empresa, código) en la colección `centros_costo`. Calcado
del patrón de `subdiario_repository.py`.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class CentroCostoRepository:
    """Lectura y escritura del catálogo de centros de costo de una empresa."""

    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.collection = database["centros_costo"]

    async def asegurar_indices(self) -> None:
        try:
            await self.collection.create_index(
                [("empresa_id", 1), ("codigo", 1)],
                unique=True,
                name="idx_empresa_codigo_centro_costo",
            )
        except Exception as e:  # pragma: no cover - depende del estado de Mongo
            logger.warning(f"No se pudo crear el índice de centros de costo: {e}")

    async def listar(
        self, empresa_id: str, solo_activos: bool = False
    ) -> List[Dict[str, Any]]:
        filtro: Dict[str, Any] = {"empresa_id": empresa_id}
        if solo_activos:
            filtro["activo"] = True

        cursor = self.collection.find(filtro).sort("codigo", 1)
        return [self._limpiar(doc) async for doc in cursor]

    async def obtener(self, empresa_id: str, codigo: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"empresa_id": empresa_id, "codigo": codigo})
        return self._limpiar(doc) if doc else None

    async def crear(
        self, empresa_id: str, datos: Dict[str, Any], usuario: Optional[str] = None
    ) -> Dict[str, Any]:
        documento = {
            **datos,
            "empresa_id": empresa_id,
            "creado_en": datetime.utcnow(),
            "creado_por": usuario,
            "modificado_en": None,
            "modificado_por": None,
        }
        await self.collection.insert_one(documento)
        return self._limpiar(documento)

    async def actualizar(
        self,
        empresa_id: str,
        codigo: str,
        cambios: Dict[str, Any],
        usuario: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not cambios:
            return await self.obtener(empresa_id, codigo)

        doc = await self.collection.find_one_and_update(
            {"empresa_id": empresa_id, "codigo": codigo},
            {
                "$set": {
                    **cambios,
                    "modificado_en": datetime.utcnow(),
                    "modificado_por": usuario,
                }
            },
            return_document=True,
        )
        return self._limpiar(doc) if doc else None

    async def eliminar(self, empresa_id: str, codigo: str) -> bool:
        resultado = await self.collection.delete_one(
            {"empresa_id": empresa_id, "codigo": codigo}
        )
        return resultado.deleted_count > 0

    async def contar(self, empresa_id: str) -> int:
        return await self.collection.count_documents({"empresa_id": empresa_id})

    async def sembrar(
        self, empresa_id: str, catalogo: List[Dict[str, Any]]
    ) -> int:
        """Crear los centros de costo del catálogo que aún no existan."""
        from pymongo.errors import DuplicateKeyError

        creados = 0
        for entrada in catalogo:
            try:
                await self.collection.insert_one({
                    **entrada,
                    "empresa_id": empresa_id,
                    "activo": entrada.get("activo", True),
                    "creado_en": datetime.utcnow(),
                    "creado_por": "sistema",
                })
                creados += 1
            except DuplicateKeyError:
                continue

        return creados

    @staticmethod
    def _limpiar(doc: Dict[str, Any]) -> Dict[str, Any]:
        salida = dict(doc)
        _id = salida.pop("_id", None)
        salida["id"] = str(_id) if _id is not None else salida.get("codigo", "")
        return salida
