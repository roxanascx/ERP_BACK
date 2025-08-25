"""
Repositorio para configuración del sistema
==========================================

Manejo de acceso a datos para configuraciones y configuración de tiempo
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

from ...database import get_database
from .models import SystemConfigModel, TimeConfigModel
from .utils import PeruTimeUtils


class SystemConfigRepository:
    """Repositorio para configuraciones del sistema"""
    
    def __init__(self):
        self.collection_name = "system_configs"
    
    async def get_database(self) -> AsyncIOMotorDatabase:
        """Obtiene la instancia de la base de datos"""
        return get_database()
    
    async def create_config(self, config: SystemConfigModel) -> SystemConfigModel:
        """Crea una nueva configuración"""
        db = await self.get_database()
        collection = db[self.collection_name]
        
        # Verificar que la clave no exista
        existing = await collection.find_one({"config_key": config.config_key})
        if existing:
            raise ValueError(f"La configuración con clave '{config.config_key}' ya existe")
        
        config.created_at = PeruTimeUtils.now_peru()
        config.updated_at = PeruTimeUtils.now_peru()
        
        config_dict = config.model_dump(exclude={"id"})
        result = await collection.insert_one(config_dict)
        
        config.id = str(result.inserted_id)
        return config
    
    async def get_config_by_key(self, config_key: str) -> Optional[SystemConfigModel]:
        """Obtiene una configuración por su clave"""
        db = await self.get_database()
        collection = db[self.collection_name]
        
        document = await collection.find_one({"config_key": config_key})
        if document:
            document["_id"] = str(document["_id"])
            return SystemConfigModel(**document)
        return None
    
    async def get_config_by_id(self, config_id: str) -> Optional[SystemConfigModel]:
        """Obtiene una configuración por su ID"""
        db = await self.get_database()
        collection = db[self.collection_name]
        
        document = await collection.find_one({"_id": ObjectId(config_id)})
        if document:
            document["_id"] = str(document["_id"])
            return SystemConfigModel(**document)
        return None
    
    async def list_configs(
        self,
        category: Optional[str] = None,
        config_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_system: Optional[bool] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[SystemConfigModel], int]:
        """Lista configuraciones con filtros"""
        db = await self.get_database()
        collection = db[self.collection_name]
        
        # Construir filtros
        filters = {}
        if category:
            filters["category"] = category
        if config_type:
            filters["config_type"] = config_type
        if is_active is not None:
            filters["is_active"] = is_active
        if is_system is not None:
            filters["is_system"] = is_system
        if search:
            filters["$or"] = [
                {"config_key": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}}
            ]
        
        # Contar total
        total = await collection.count_documents(filters)
        
        # Obtener documentos
        cursor = collection.find(filters).skip(skip).limit(limit).sort("config_key", ASCENDING)
        documents = await cursor.to_list(length=limit)
        
        configs = []
        for doc in documents:
            doc["_id"] = str(doc["_id"])
            configs.append(SystemConfigModel(**doc))
        
        return configs, total
    
    async def update_config(self, config_id: str, updates: Dict[str, Any]) -> Optional[SystemConfigModel]:
        """Actualiza una configuración"""
        db = await self.get_database()
        collection = db[self.collection_name]
        
        updates["updated_at"] = PeruTimeUtils.now_peru()
        
        result = await collection.update_one(
            {"_id": ObjectId(config_id)},
            {"$set": updates}
        )
        
        if result.matched_count > 0:
            return await self.get_config_by_id(config_id)
        return None
    
    async def delete_config(self, config_id: str) -> bool:
        """Elimina una configuración"""
        db = await self.get_database()
        collection = db[self.collection_name]
        
        # Verificar que no sea configuración del sistema
        config = await self.get_config_by_id(config_id)
        if config and config.is_system:
            raise ValueError("No se puede eliminar una configuración del sistema")
        
        result = await collection.delete_one({"_id": ObjectId(config_id)})
        return result.deleted_count > 0
    
    async def get_configs_by_category(self, category: str) -> List[SystemConfigModel]:
        """Obtiene todas las configuraciones de una categoría"""
        configs, _ = await self.list_configs(category=category, is_active=True)
        return configs


class TimeConfigRepository:
    """Repositorio para configuración de tiempo"""
    
    def __init__(self):
        self.collection_name = "time_configs"
    
    async def get_database(self) -> AsyncIOMotorDatabase:
        """Obtiene la instancia de la base de datos"""
        return get_database()
    
    async def get_time_config(self) -> Optional[TimeConfigModel]:
        """Obtiene la configuración de tiempo (solo debe existir una)"""
        db = await self.get_database()
        collection = db[self.collection_name]
        
        document = await collection.find_one({})
        if document:
            document["_id"] = str(document["_id"])
            return TimeConfigModel(**document)
        return None
    
    async def create_or_update_time_config(self, time_config: TimeConfigModel) -> TimeConfigModel:
        """Crea o actualiza la configuración de tiempo"""
        db = await self.get_database()
        collection = db[self.collection_name]
        
        existing = await collection.find_one({})
        
        if existing:
            # Actualizar existente
            time_config.updated_at = PeruTimeUtils.now_peru()
            config_dict = time_config.model_dump(exclude={"id", "created_at"})
            
            await collection.update_one(
                {"_id": existing["_id"]},
                {"$set": config_dict}
            )
            
            time_config.id = str(existing["_id"])
        else:
            # Crear nuevo
            time_config.created_at = PeruTimeUtils.now_peru()
            time_config.updated_at = PeruTimeUtils.now_peru()
            
            config_dict = time_config.model_dump(exclude={"id"})
            result = await collection.insert_one(config_dict)
            
            time_config.id = str(result.inserted_id)
        
        return time_config
    
    async def update_time_config(self, updates: Dict[str, Any]) -> Optional[TimeConfigModel]:
        """Actualiza la configuración de tiempo"""
        db = await self.get_database()
        collection = db[self.collection_name]
        
        updates["updated_at"] = PeruTimeUtils.now_peru()
        
        existing = await collection.find_one({})
        if existing:
            await collection.update_one(
                {"_id": existing["_id"]},
                {"$set": updates}
            )
            return await self.get_time_config()
        
        return None
