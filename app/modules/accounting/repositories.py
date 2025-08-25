"""Repositorio del módulo Contabilidad - implementación mínima usando MongoDB
"""
from typing import List, Dict, Any, Optional
from app.database import get_database


class AccountingRepository:
    def __init__(self):
        # nombre de la colección usada para el plan contable
        self.collection_name = "plan_contable"

    def _collection(self):
        db = get_database()
        return db[self.collection_name]

    async def list_cuentas(self, filtros: Dict[str, Any] = None, limit: Optional[int] = None) -> List[Dict]:
        filtros = filtros or {}
        cursor = self._collection().find(filtros).sort("codigo", 1)
        if limit:
            cursor = cursor.limit(limit)
        return await cursor.to_list(length=None)

    async def buscar_texto(self, termino: str, filtros: Dict[str, Any] = None, limit: int = 50) -> List[Dict]:
        """Búsqueda optimizada usando regex para código y descripción"""
        filtros = filtros or {}
        
        # Crear expresión regular case-insensitive
        regex_pattern = {"$regex": termino, "$options": "i"}
        
        # Agregar condición OR para buscar en código y descripción
        filtros["$or"] = [
            {"codigo": regex_pattern},
            {"descripcion": regex_pattern}
        ]
        
        cursor = self._collection().find(filtros).sort("codigo", 1).limit(limit)
        return await cursor.to_list(length=None)

    async def find_by_codigo(self, codigo: str) -> Optional[Dict]:
        return await self._collection().find_one({"codigo": codigo})

    async def insert_cuenta(self, documento: Dict) -> Any:
        return await self._collection().insert_one(documento)

    async def update_cuenta(self, codigo: str, update: Dict) -> Any:
        return await self._collection().update_one({"codigo": codigo}, {"$set": update})

    async def count_documents(self, filtros: Dict[str, Any] = None) -> int:
        return await self._collection().count_documents(filtros or {})

    async def aggregate(self, pipeline: List[Dict]) -> List[Dict]:
        cursor = self._collection().aggregate(pipeline)
        return await cursor.to_list(length=None)

