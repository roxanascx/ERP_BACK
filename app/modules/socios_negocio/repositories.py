"""
Repositorio MongoDB para Socios de Negocio
Maneja todas las operaciones de base de datos
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pymongo import IndexModel, ASCENDING, TEXT

from .models import SocioNegocioModel
from .exceptions import SocioNotFoundException, SocioAlreadyExistsException

class SocioNegocioRepository:
    """Repositorio para operaciones CRUD de socios de negocio"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.collection = database.socios_negocio
        
    async def create_indexes(self):
        """Crea índices optimizados para búsquedas frecuentes"""
        indexes = [
            # Índice único por empresa y documento
            IndexModel(
                [("empresa_id", ASCENDING), ("numero_documento", ASCENDING)], 
                unique=True,
                name="idx_empresa_documento_unique"
            ),
            
            # Índice para búsquedas por empresa
            IndexModel([("empresa_id", ASCENDING)], name="idx_empresa"),
            
            # Índice para búsquedas por tipo de socio
            IndexModel([("tipo_socio", ASCENDING)], name="idx_tipo_socio"),
            
            # Índice para búsquedas por estado
            IndexModel([("activo", ASCENDING)], name="idx_activo"),
            
            # Índice de texto para búsquedas
            IndexModel(
                [
                    ("razon_social", TEXT),
                    ("nombre_comercial", TEXT),
                    ("numero_documento", TEXT)
                ],
                name="idx_text_search"
            ),
            
            # Índice para consultas de sincronización SUNAT
            IndexModel([("requiere_actualizacion", ASCENDING)], name="idx_sync_sunat"),
            
            # Índice para auditoría
            IndexModel([("created_at", ASCENDING)], name="idx_created_at"),
            IndexModel([("updated_at", ASCENDING)], name="idx_updated_at")
        ]
        
        await self.collection.create_indexes(indexes)
    
    async def create(self, socio: SocioNegocioModel) -> str:
        """
        Crea un nuevo socio de negocio
        
        Args:
            socio: Modelo del socio a crear
            
        Returns:
            str: ID del socio creado
            
        Raises:
            SocioAlreadyExistsException: Si ya existe un socio con el mismo documento
        """
        try:
            # Verificar si ya existe un socio con el mismo documento en la empresa
            existing = await self.get_by_documento(socio.empresa_id, socio.numero_documento)
            if existing:
                raise SocioAlreadyExistsException(
                    f"Ya existe un socio con el documento {socio.numero_documento} en esta empresa"
                )
            
            # Preparar datos para inserción
            socio_data = socio.model_dump(exclude={'id'}, by_alias=True)
            socio_data['created_at'] = datetime.utcnow()
            socio_data['updated_at'] = datetime.utcnow()
            
            # Insertar en MongoDB
            result = await self.collection.insert_one(socio_data)
            return str(result.inserted_id)
            
        except SocioAlreadyExistsException:
            raise
        except Exception as e:
            raise Exception(f"Error creando socio: {str(e)}")
    
    async def get_by_id(self, socio_id: str) -> Optional[SocioNegocioModel]:
        """
        Obtiene un socio por su ID
        
        Args:
            socio_id: ID del socio
            
        Returns:
            SocioNegocioModel: Socio encontrado o None
        """
        try:
            if not ObjectId.is_valid(socio_id):
                return None
                
            socio_data = await self.collection.find_one({"_id": ObjectId(socio_id)})
            if socio_data:
                socio_data['_id'] = str(socio_data['_id'])
                return SocioNegocioModel(**socio_data)
            return None
            
        except Exception as e:
            raise Exception(f"Error obteniendo socio por ID: {str(e)}")
    
    async def get_by_documento(self, empresa_id: str, numero_documento: str) -> Optional[SocioNegocioModel]:
        """
        Obtiene un socio por número de documento en una empresa específica
        
        Args:
            empresa_id: ID de la empresa
            numero_documento: Número de documento del socio
            
        Returns:
            SocioNegocioModel: Socio encontrado o None
        """
        try:
            socio_data = await self.collection.find_one({
                "empresa_id": empresa_id,
                "numero_documento": numero_documento
            })
            
            if socio_data:
                socio_data['_id'] = str(socio_data['_id'])
                return SocioNegocioModel(**socio_data)
            return None
            
        except Exception as e:
            raise Exception(f"Error obteniendo socio por documento: {str(e)}")
    
    async def list_by_empresa(
        self, 
        empresa_id: str, 
        filters: Optional[Dict] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[SocioNegocioModel]:
        """
        Lista socios de una empresa con filtros opcionales
        
        Args:
            empresa_id: ID de la empresa
            filters: Filtros adicionales
            limit: Límite de resultados
            offset: Offset para paginación
            
        Returns:
            List[SocioNegocioModel]: Lista de socios
        """
        try:
            query = {"empresa_id": empresa_id}
            
            # Aplicar filtros adicionales
            if filters:
                if filters.get('tipo_socio'):
                    query['tipo_socio'] = filters['tipo_socio']
                
                if filters.get('categoria'):
                    query['categoria'] = filters['categoria']
                
                if filters.get('activo') is not None:
                    query['activo'] = filters['activo']
                
                if filters.get('tipo_documento'):
                    query['tipo_documento'] = filters['tipo_documento']
            
            # Ejecutar consulta con paginación
            cursor = self.collection.find(query).skip(offset).limit(limit).sort("razon_social", 1)
            socios_data = await cursor.to_list(length=limit)
            
            # Convertir a modelos
            socios = []
            for socio_data in socios_data:
                socio_data['_id'] = str(socio_data['_id'])
                socios.append(SocioNegocioModel(**socio_data))
            
            return socios
            
        except Exception as e:
            raise Exception(f"Error listando socios: {str(e)}")
    
    async def search(
        self, 
        empresa_id: str, 
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[SocioNegocioModel]:
        """
        Búsqueda de texto en socios
        
        Args:
            empresa_id: ID de la empresa
            query: Texto a buscar
            filters: Filtros adicionales
            limit: Límite de resultados
            offset: Offset para paginación
            
        Returns:
            List[SocioNegocioModel]: Lista de socios encontrados
        """
        try:
            # Construir consulta de búsqueda
            search_query = {
                "empresa_id": empresa_id,
                "$or": [
                    {"razon_social": {"$regex": query, "$options": "i"}},
                    {"nombre_comercial": {"$regex": query, "$options": "i"}},
                    {"numero_documento": {"$regex": query, "$options": "i"}},
                    {"contacto_principal": {"$regex": query, "$options": "i"}}
                ]
            }
            
            # Aplicar filtros adicionales
            if filters:
                if filters.get('tipo_socio'):
                    search_query['tipo_socio'] = filters['tipo_socio']
                
                if filters.get('activo') is not None:
                    search_query['activo'] = filters['activo']
            
            # Ejecutar búsqueda
            cursor = self.collection.find(search_query).skip(offset).limit(limit).sort("razon_social", 1)
            socios_data = await cursor.to_list(length=limit)
            
            # Convertir a modelos
            socios = []
            for socio_data in socios_data:
                socio_data['_id'] = str(socio_data['_id'])
                socios.append(SocioNegocioModel(**socio_data))
            
            return socios
            
        except Exception as e:
            raise Exception(f"Error en búsqueda de socios: {str(e)}")
    
    async def update(self, socio_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Actualiza un socio de negocio
        
        Args:
            socio_id: ID del socio
            update_data: Datos a actualizar
            
        Returns:
            bool: True si se actualizó, False si no se encontró
            
        Raises:
            SocioNotFoundException: Si no se encuentra el socio
        """
        try:
            if not ObjectId.is_valid(socio_id):
                raise SocioNotFoundException(f"ID de socio inválido: {socio_id}")
            
            # Añadir timestamp de actualización
            update_data['updated_at'] = datetime.utcnow()
            
            # Realizar actualización
            result = await self.collection.update_one(
                {"_id": ObjectId(socio_id)},
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                raise SocioNotFoundException(f"Socio no encontrado: {socio_id}")
            
            return result.modified_count > 0
            
        except SocioNotFoundException:
            raise
        except Exception as e:
            raise Exception(f"Error actualizando socio: {str(e)}")
    
    async def delete(self, socio_id: str) -> bool:
        """
        Elimina un socio de negocio (soft delete)
        
        Args:
            socio_id: ID del socio
            
        Returns:
            bool: True si se eliminó
            
        Raises:
            SocioNotFoundException: Si no se encuentra el socio
        """
        try:
            if not ObjectId.is_valid(socio_id):
                raise SocioNotFoundException(f"ID de socio inválido: {socio_id}")
            
            # Realizar soft delete (marcar como inactivo)
            result = await self.collection.update_one(
                {"_id": ObjectId(socio_id)},
                {"$set": {"activo": False, "updated_at": datetime.utcnow()}}
            )
            
            if result.matched_count == 0:
                raise SocioNotFoundException(f"Socio no encontrado: {socio_id}")
            
            return result.modified_count > 0
            
        except SocioNotFoundException:
            raise
        except Exception as e:
            raise Exception(f"Error eliminando socio: {str(e)}")
    
    async def count_by_empresa(self, empresa_id: str, filters: Optional[Dict] = None) -> int:
        """
        Cuenta socios de una empresa
        
        Args:
            empresa_id: ID de la empresa
            filters: Filtros opcionales
            
        Returns:
            int: Número de socios
        """
        try:
            query = {"empresa_id": empresa_id}
            
            if filters:
                if filters.get('tipo_socio'):
                    query['tipo_socio'] = filters['tipo_socio']
                
                if filters.get('activo') is not None:
                    query['activo'] = filters['activo']
            
            return await self.collection.count_documents(query)
            
        except Exception as e:
            raise Exception(f"Error contando socios: {str(e)}")
    
    async def get_stats_by_empresa(self, empresa_id: str) -> Dict[str, int]:
        """
        Obtiene estadísticas de socios por empresa
        
        Args:
            empresa_id: ID de la empresa
            
        Returns:
            Dict: Estadísticas de socios
        """
        try:
            pipeline = [
                {"$match": {"empresa_id": empresa_id}},
                {
                    "$group": {
                        "_id": None,
                        "total_socios": {"$sum": 1},
                        "total_activos": {"$sum": {"$cond": [{"$eq": ["$activo", True]}, 1, 0]}},
                        "total_inactivos": {"$sum": {"$cond": [{"$eq": ["$activo", False]}, 1, 0]}},
                        "total_proveedores": {"$sum": {"$cond": [{"$in": ["$tipo_socio", ["proveedor", "ambos"]]}, 1, 0]}},
                        "total_clientes": {"$sum": {"$cond": [{"$in": ["$tipo_socio", ["cliente", "ambos"]]}, 1, 0]}},
                        "total_ambos": {"$sum": {"$cond": [{"$eq": ["$tipo_socio", "ambos"]}, 1, 0]}},
                        "total_con_ruc": {"$sum": {"$cond": [{"$eq": ["$tipo_documento", "RUC"]}, 1, 0]}},
                        "total_sincronizados_sunat": {"$sum": {"$cond": [{"$eq": ["$datos_sunat_disponibles", True]}, 1, 0]}}
                    }
                }
            ]
            
            result = await self.collection.aggregate(pipeline).to_list(1)
            
            if result:
                stats = result[0]
                del stats['_id']  # Remover _id del resultado
                return stats
            
            return {
                "total_socios": 0,
                "total_activos": 0,
                "total_inactivos": 0,
                "total_proveedores": 0,
                "total_clientes": 0,
                "total_ambos": 0,
                "total_con_ruc": 0,
                "total_sincronizados_sunat": 0
            }
            
        except Exception as e:
            raise Exception(f"Error obteniendo estadísticas: {str(e)}")
    
    async def get_socios_for_sync(self, empresa_id: str, limit: int = 10) -> List[SocioNegocioModel]:
        """
        Obtiene socios que requieren sincronización con SUNAT
        
        Args:
            empresa_id: ID de la empresa
            limit: Límite de socios a retornar
            
        Returns:
            List[SocioNegocioModel]: Socios que requieren sincronización
        """
        try:
            query = {
                "empresa_id": empresa_id,
                "tipo_documento": "RUC",
                "requiere_actualizacion": True,
                "activo": True
            }
            
            cursor = self.collection.find(query).limit(limit).sort("ultimo_sync_sunat", 1)
            socios_data = await cursor.to_list(length=limit)
            
            socios = []
            for socio_data in socios_data:
                socio_data['_id'] = str(socio_data['_id'])
                socios.append(SocioNegocioModel(**socio_data))
            
            return socios
            
        except Exception as e:
            raise Exception(f"Error obteniendo socios para sincronización: {str(e)}")
    
    async def mark_as_synced(self, socio_id: str, datos_sunat: Dict[str, Any]) -> bool:
        """
        Marca un socio como sincronizado con SUNAT
        
        Args:
            socio_id: ID del socio
            datos_sunat: Datos obtenidos de SUNAT
            
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            if not ObjectId.is_valid(socio_id):
                return False
            
            update_data = {
                "ultimo_sync_sunat": datetime.utcnow(),
                "requiere_actualizacion": False,
                "datos_sunat_disponibles": True,
                "updated_at": datetime.utcnow()
            }
            
            # Actualizar con datos de SUNAT si están disponibles
            if datos_sunat:
                if datos_sunat.get('estado_contribuyente'):
                    update_data['estado_sunat'] = datos_sunat['estado_contribuyente']
                
                if datos_sunat.get('condicion_contribuyente'):
                    update_data['condicion_sunat'] = datos_sunat['condicion_contribuyente']
                
                if datos_sunat.get('actividad_economica'):
                    update_data['actividad_economica'] = datos_sunat['actividad_economica']
                
                if datos_sunat.get('domicilio_fiscal'):
                    update_data['direccion'] = datos_sunat['domicilio_fiscal']
            
            result = await self.collection.update_one(
                {"_id": ObjectId(socio_id)},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            raise Exception(f"Error marcando como sincronizado: {str(e)}")
