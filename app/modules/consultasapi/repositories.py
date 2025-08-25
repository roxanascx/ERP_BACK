"""
Repositorios para el módulo consultasapi
========================================

Manejo de operaciones de base de datos para tipos de cambio y consultas
"""

from datetime import date, datetime
from typing import Optional, List, Tuple
from decimal import Decimal
import logging

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from app.database import get_database
from .models import ExchangeRate
from .schemas import ExchangeRateQuery

logger = logging.getLogger(__name__)


class ExchangeRateRepository:
    """Repositorio para operaciones de tipos de cambio"""
    
    def __init__(self):
        self.collection_name = "exchange_rates"
    
    async def get_database(self) -> AsyncIOMotorDatabase:
        """Obtiene la conexión a la base de datos"""
        return get_database()
    
    async def create_exchange_rate(self, exchange_rate: ExchangeRate) -> ExchangeRate:
        """Crea un nuevo tipo de cambio"""
        try:
            db = await self.get_database()
            collection = db[self.collection_name]
            
            # Preparar documento para insertar
            document = exchange_rate.dict(exclude={"id"})
            document["created_at"] = datetime.utcnow()
            document["updated_at"] = datetime.utcnow()
            
            # Convertir date a datetime para MongoDB
            if isinstance(document.get("fecha"), date):
                document["fecha"] = datetime.combine(document["fecha"], datetime.min.time())
            
            # Convertir Decimal a float para MongoDB
            for field in ['compra', 'venta', 'oficial']:
                if field in document and document[field] is not None:
                    document[field] = float(document[field])
            
            # Insertar documento
            result = await collection.insert_one(document)
            
            # Recuperar el documento insertado
            created_doc = await collection.find_one({"_id": result.inserted_id})
            
            # Convertir _id a id string y datetime de vuelta a date
            created_doc["id"] = str(created_doc["_id"])
            del created_doc["_id"]
            
            if isinstance(created_doc.get("fecha"), datetime):
                created_doc["fecha"] = created_doc["fecha"].date()
            
            return ExchangeRate(**created_doc)
            
        except Exception as e:
            logger.error(f"Error creando tipo de cambio: {e}")
            raise
    
    async def get_exchange_rate_by_id(self, exchange_rate_id: str) -> Optional[ExchangeRate]:
        """Obtiene un tipo de cambio por su ID"""
        try:
            db = await self.get_database()
            collection = db[self.collection_name]
            
            document = await collection.find_one({"_id": ObjectId(exchange_rate_id)})
            
            if document:
                document["id"] = str(document["_id"])
                del document["_id"]
                return ExchangeRate(**document)
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo tipo de cambio por ID {exchange_rate_id}: {e}")
            raise
    
    async def get_exchange_rate_by_date(
        self, 
        fecha: date, 
        moneda_origen: str = "USD", 
        moneda_destino: str = "PEN"
    ) -> Optional[ExchangeRate]:
        """Obtiene un tipo de cambio por fecha y monedas"""
        try:
            db = await self.get_database()
            collection = db[self.collection_name]
            
            # Convertir date a datetime para MongoDB
            fecha_datetime = datetime.combine(fecha, datetime.min.time())
            
            query = {
                "fecha": fecha_datetime,
                "moneda_origen": moneda_origen,
                "moneda_destino": moneda_destino,
                "es_activo": True
            }
            
            document = await collection.find_one(
                query, 
                sort=[("es_oficial", DESCENDING), ("updated_at", DESCENDING)]
            )
            
            if document:
                document["id"] = str(document["_id"])
                del document["_id"]
                # Convertir datetime de vuelta a date si es necesario
                if isinstance(document.get("fecha"), datetime):
                    document["fecha"] = document["fecha"].date()
                return ExchangeRate(**document)
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo tipo de cambio por fecha {fecha}: {e}")
            raise
    
    async def get_latest_exchange_rate(
        self, 
        moneda_origen: str = "USD", 
        moneda_destino: str = "PEN"
    ) -> Optional[ExchangeRate]:
        """Obtiene el tipo de cambio más reciente"""
        try:
            db = await self.get_database()
            collection = db[self.collection_name]
            
            query = {
                "moneda_origen": moneda_origen,
                "moneda_destino": moneda_destino,
                "es_activo": True
            }
            
            document = await collection.find_one(
                query,
                sort=[("fecha", DESCENDING), ("es_oficial", DESCENDING), ("updated_at", DESCENDING)]
            )
            
            if document:
                document["id"] = str(document["_id"])
                del document["_id"]
                return ExchangeRate(**document)
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo último tipo de cambio: {e}")
            raise
    
    async def list_exchange_rates(
        self, 
        query: ExchangeRateQuery, 
        page: int = 1, 
        size: int = 10
    ) -> Tuple[List[ExchangeRate], int]:
        """Lista tipos de cambio con filtros y paginación"""
        try:
            db = await self.get_database()
            collection = db[self.collection_name]
            
            # Construir filtros
            filters = {}
            
            if query.fecha_desde and query.fecha_hasta:
                filters["fecha"] = {"$gte": query.fecha_desde, "$lte": query.fecha_hasta}
            elif query.fecha_desde:
                filters["fecha"] = {"$gte": query.fecha_desde}
            elif query.fecha_hasta:
                filters["fecha"] = {"$lte": query.fecha_hasta}
            
            if query.moneda_origen:
                filters["moneda_origen"] = query.moneda_origen
            
            if query.moneda_destino:
                filters["moneda_destino"] = query.moneda_destino
            
            if query.fuente:
                filters["fuente"] = query.fuente
            
            if query.es_oficial is not None:
                filters["es_oficial"] = query.es_oficial
            
            if query.es_activo is not None:
                filters["es_activo"] = query.es_activo
            
            # Contar total
            total = await collection.count_documents(filters)
            
            # Obtener documentos con paginación
            skip = (page - 1) * size
            cursor = collection.find(filters).sort([
                ("fecha", DESCENDING),
                ("es_oficial", DESCENDING),
                ("updated_at", DESCENDING)
            ]).skip(skip).limit(size)
            
            documents = await cursor.to_list(length=None)
            
            # Convertir documentos a modelos
            exchange_rates = []
            for doc in documents:
                doc["id"] = str(doc["_id"])
                del doc["_id"]
                exchange_rates.append(ExchangeRate(**doc))
            
            return exchange_rates, total
            
        except Exception as e:
            logger.error(f"Error listando tipos de cambio: {e}")
            raise
    
    async def update_exchange_rate(
        self, 
        exchange_rate_id: str, 
        updates: dict
    ) -> Optional[ExchangeRate]:
        """Actualiza un tipo de cambio"""
        try:
            db = await self.get_database()
            collection = db[self.collection_name]
            
            # Agregar timestamp de actualización
            updates["updated_at"] = datetime.utcnow()
            
            # Convertir Decimal a float para MongoDB
            for field in ['compra', 'venta', 'oficial']:
                if field in updates and updates[field] is not None:
                    updates[field] = float(updates[field])
            
            # Convertir date a datetime para MongoDB
            if 'fecha' in updates and isinstance(updates['fecha'], date):
                updates['fecha'] = datetime.combine(updates['fecha'], datetime.min.time())
            
            result = await collection.update_one(
                {"_id": ObjectId(exchange_rate_id)},
                {"$set": updates}
            )
            
            if result.modified_count > 0:
                return await self.get_exchange_rate_by_id(exchange_rate_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error actualizando tipo de cambio {exchange_rate_id}: {e}")
            raise
    
    async def delete_exchange_rate(self, exchange_rate_id: str) -> bool:
        """Elimina un tipo de cambio (soft delete)"""
        try:
            db = await self.get_database()
            collection = db[self.collection_name]
            
            result = await collection.update_one(
                {"_id": ObjectId(exchange_rate_id)},
                {"$set": {"es_activo": False, "updated_at": datetime.utcnow()}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error eliminando tipo de cambio {exchange_rate_id}: {e}")
            raise
    
    async def exchange_rate_exists(
        self, 
        fecha: date, 
        moneda_origen: str = "USD", 
        moneda_destino: str = "PEN"
    ) -> bool:
        """Verifica si existe un tipo de cambio para una fecha específica"""
        try:
            db = await self.get_database()
            collection = db[self.collection_name]
            
            # Convertir date a datetime para MongoDB
            fecha_datetime = datetime.combine(fecha, datetime.min.time())
            
            count = await collection.count_documents({
                "fecha": fecha_datetime,
                "moneda_origen": moneda_origen,
                "moneda_destino": moneda_destino,
                "es_activo": True
            })
            
            return count > 0
            
        except Exception as e:
            logger.error(f"Error verificando existencia de tipo de cambio: {e}")
            raise
    
    async def get_exchange_rates_by_date_range(
        self,
        fecha_desde: date,
        fecha_hasta: date,
        moneda_origen: str = "USD",
        moneda_destino: str = "PEN"
    ) -> List[ExchangeRate]:
        """Obtiene tipos de cambio en un rango de fechas"""
        try:
            db = await self.get_database()
            collection = db[self.collection_name]
            
            query = {
                "fecha": {"$gte": fecha_desde, "$lte": fecha_hasta},
                "moneda_origen": moneda_origen,
                "moneda_destino": moneda_destino,
                "es_activo": True
            }
            
            cursor = collection.find(query).sort([
                ("fecha", ASCENDING),
                ("es_oficial", DESCENDING)
            ])
            
            documents = await cursor.to_list(length=None)
            
            exchange_rates = []
            for doc in documents:
                doc["id"] = str(doc["_id"])
                del doc["_id"]
                exchange_rates.append(ExchangeRate(**doc))
            
            return exchange_rates
            
        except Exception as e:
            logger.error(f"Error obteniendo tipos de cambio por rango: {e}")
            raise
    
    async def bulk_create_exchange_rates(self, exchange_rates: List[ExchangeRate]) -> List[ExchangeRate]:
        """Crea múltiples tipos de cambio en lote"""
        try:
            db = await self.get_database()
            collection = db[self.collection_name]
            
            documents = []
            for rate in exchange_rates:
                doc = rate.dict(exclude={"id"})
                doc["created_at"] = datetime.utcnow()
                doc["updated_at"] = datetime.utcnow()
                
                # Convertir date a datetime para MongoDB
                if isinstance(doc.get("fecha"), date):
                    doc["fecha"] = datetime.combine(doc["fecha"], datetime.min.time())
                
                # Convertir Decimal a float para MongoDB
                for field in ['compra', 'venta', 'oficial']:
                    if field in doc and doc[field] is not None:
                        doc[field] = float(doc[field])
                
                documents.append(doc)
            
            result = await collection.insert_many(documents)
            
            # Recuperar documentos insertados
            inserted_docs = await collection.find(
                {"_id": {"$in": result.inserted_ids}}
            ).to_list(length=None)
            
            created_rates = []
            for doc in inserted_docs:
                doc["id"] = str(doc["_id"])
                del doc["_id"]
                
                # Convertir datetime de vuelta a date
                if isinstance(doc.get("fecha"), datetime):
                    doc["fecha"] = doc["fecha"].date()
                    
                created_rates.append(ExchangeRate(**doc))
            
            return created_rates
            
        except Exception as e:
            logger.error(f"Error en creación masiva de tipos de cambio: {e}")
            raise
    
    async def get_currency_pairs(self) -> List[dict]:
        """Obtiene todos los pares de monedas disponibles"""
        try:
            db = await self.get_database()
            collection = db[self.collection_name]
            
            pipeline = [
                {"$match": {"es_activo": True}},
                {
                    "$group": {
                        "_id": {
                            "moneda_origen": "$moneda_origen",
                            "moneda_destino": "$moneda_destino"
                        },
                        "count": {"$sum": 1},
                        "ultima_fecha": {"$max": "$fecha"}
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "moneda_origen": "$_id.moneda_origen",
                        "moneda_destino": "$_id.moneda_destino",
                        "registros": "$count",
                        "ultima_actualizacion": "$ultima_fecha"
                    }
                },
                {"$sort": {"moneda_origen": 1, "moneda_destino": 1}}
            ]
            
            cursor = collection.aggregate(pipeline)
            return await cursor.to_list(length=None)
            
        except Exception as e:
            logger.error(f"Error obteniendo pares de monedas: {e}")
            raise
