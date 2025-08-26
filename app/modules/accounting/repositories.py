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
        """Búsqueda optimizada y inteligente por código y descripción"""
        filtros = filtros or {}
        termino_limpio = termino.strip()
        
        if not termino_limpio:
            return []
        
        # Crear una copia de filtros sin OR para cada consulta
        base_filtros = {k: v for k, v in filtros.items() if k != "$or"}
        empresa_filtros = filtros.get("$or", [])
        
        all_results = []
        
        # 1. Búsqueda exacta por código (máxima prioridad)
        exact_filtros = base_filtros.copy()
        exact_filtros["codigo"] = termino_limpio.upper()
        if empresa_filtros:
            exact_filtros["$or"] = empresa_filtros
        
        exact_results = await self._collection().find(exact_filtros).sort("codigo", 1).limit(5).to_list(length=None)
        all_results.extend([(r, 0) for r in exact_results])  # Prioridad 0 (máxima)
        
        # 2. Búsqueda por código que empiece con el término (alta prioridad)
        if len(exact_results) < limit:
            start_filtros = base_filtros.copy()
            start_filtros["codigo"] = {"$regex": f"^{termino_limpio.upper()}", "$options": "i"}
            if empresa_filtros:
                start_filtros["$or"] = empresa_filtros
            
            # Excluir resultados exactos ya encontrados
            if exact_results:
                exact_codes = [r["codigo"] for r in exact_results]
                start_filtros["codigo"]["$nin"] = exact_codes
            
            start_results = await self._collection().find(start_filtros).sort("codigo", 1).limit(limit - len(exact_results)).to_list(length=None)
            all_results.extend([(r, 1) for r in start_results])  # Prioridad 1
        
        # 3. Búsqueda por código que contenga el término (prioridad media)
        current_count = len([r for r, _ in all_results])
        if current_count < limit:
            contains_filtros = base_filtros.copy()
            contains_filtros["codigo"] = {"$regex": termino_limpio.upper(), "$options": "i"}
            if empresa_filtros:
                contains_filtros["$or"] = empresa_filtros
            
            # Excluir resultados ya encontrados
            found_codes = [r["codigo"] for r, _ in all_results]
            if found_codes:
                if "$nin" in contains_filtros.get("codigo", {}):
                    contains_filtros["codigo"]["$nin"].extend(found_codes)
                else:
                    contains_filtros["codigo"]["$nin"] = found_codes
            
            contains_results = await self._collection().find(contains_filtros).sort("codigo", 1).limit(limit - current_count).to_list(length=None)
            all_results.extend([(r, 2) for r in contains_results])  # Prioridad 2
        
        # 4. Búsqueda por descripción que contenga el término (prioridad baja)
        current_count = len([r for r, _ in all_results])
        if current_count < limit:
            desc_filtros = base_filtros.copy()
            desc_filtros["descripcion"] = {"$regex": termino_limpio, "$options": "i"}
            if empresa_filtros:
                desc_filtros["$or"] = empresa_filtros
            
            # Excluir resultados ya encontrados
            found_codes = [r["codigo"] for r, _ in all_results]
            if found_codes:
                desc_filtros["codigo"] = {"$nin": found_codes}
            
            desc_results = await self._collection().find(desc_filtros).sort("codigo", 1).limit(limit - current_count).to_list(length=None)
            all_results.extend([(r, 3) for r in desc_results])  # Prioridad 3
        
        # 5. Búsqueda por descripción que empiece con el término (prioridad muy baja)
        current_count = len([r for r, _ in all_results])
        if current_count < limit:
            desc_start_filtros = base_filtros.copy()
            desc_start_filtros["descripcion"] = {"$regex": f"^{termino_limpio}", "$options": "i"}
            if empresa_filtros:
                desc_start_filtros["$or"] = empresa_filtros
            
            # Excluir resultados ya encontrados
            found_codes = [r["codigo"] for r, _ in all_results]
            if found_codes:
                desc_start_filtros["codigo"] = {"$nin": found_codes}
            
            desc_start_results = await self._collection().find(desc_start_filtros).sort("codigo", 1).limit(limit - current_count).to_list(length=None)
            all_results.extend([(r, 4) for r in desc_start_results])  # Prioridad 4
        
        # Ordenar por prioridad y luego por código
        all_results.sort(key=lambda x: (x[1], x[0].get("codigo", "")))
        
        # Extraer solo los documentos (sin prioridad) y limitar
        final_results = [r for r, _ in all_results[:limit]]
        
        return final_results

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

    # Nuevos métodos para gestión de planes personalizados
    async def get_planes_by_empresa(self, empresa_id: str, tipo_plan: str = None) -> List[Dict]:
        """Obtiene cuentas filtradas por empresa y tipo de plan"""
        filtros = {"empresa_id": empresa_id}
        if tipo_plan:
            filtros["tipo_plan"] = tipo_plan
        
        cursor = self._collection().find(filtros).sort("codigo", 1)
        return await cursor.to_list(length=None)

    async def delete_plan_personalizado(self, empresa_id: str) -> Any:
        """Elimina todas las cuentas personalizadas de una empresa"""
        return await self._collection().delete_many({
            "empresa_id": empresa_id,
            "tipo_plan": "personalizado"
        })

    async def count_by_tipo_plan(self, empresa_id: str, tipo_plan: str) -> int:
        """Cuenta documentos por empresa y tipo de plan"""
        return await self._collection().count_documents({
            "empresa_id": empresa_id,
            "tipo_plan": tipo_plan
        })

    async def get_plan_info(self, empresa_id: str) -> Dict[str, Any]:
        """Obtiene información sobre los planes disponibles para una empresa"""
        # Contar plan estándar (sin empresa_id o con empresa_id None)
        estandar_count = await self._collection().count_documents({
            "$or": [
                {"tipo_plan": "estandar"},
                {"empresa_id": {"$exists": False}},
                {"empresa_id": None}
            ]
        })
        
        # Contar plan personalizado
        personalizado_count = await self.count_by_tipo_plan(empresa_id, "personalizado")
        
        # Obtener info del plan personalizado si existe
        personalizado_info = None
        if personalizado_count > 0:
            sample = await self._collection().find_one({
                "empresa_id": empresa_id,
                "tipo_plan": "personalizado"
            })
            personalizado_info = {
                "archivo_origen": sample.get("archivo_origen"),
                "fecha_creacion": sample.get("fecha_creacion")
            }
        
        return {
            "estandar": {
                "total_cuentas": estandar_count,
                "disponible": estandar_count > 0
            },
            "personalizado": {
                "total_cuentas": personalizado_count,
                "disponible": personalizado_count > 0,
                "info": personalizado_info
            }
        }

    async def set_plan_activo(self, empresa_id: str, tipo_plan: str) -> bool:
        """Marca un tipo de plan como activo para una empresa"""
        # Esto se puede implementar con una tabla de configuración por empresa
        # Por ahora, asumimos que el plan activo se determina por el que se consulta
        return True

