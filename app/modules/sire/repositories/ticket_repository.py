"""
Repositorio para gestión de tickets SIRE
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING
import logging

from ..models.tickets import (
    SireTicket, TicketStatus, TicketOperationType, 
    TicketFilter, TicketSummary, TicketPriority
)


class SireTicketRepository:
    """Repositorio para operaciones CRUD de tickets SIRE"""
    
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection
        self.logger = logging.getLogger(__name__)
    
    async def create_ticket(self, ticket: SireTicket) -> str:
        """Crear un nuevo ticket"""
        try:
            ticket_data = ticket.model_dump()
            
            # Asegurar que las fechas sean datetime
            for field in ['created_at', 'updated_at', 'expires_at', 'processing_start', 'processing_end']:
                if ticket_data.get(field):
                    if isinstance(ticket_data[field], str):
                        ticket_data[field] = datetime.fromisoformat(ticket_data[field].replace('Z', '+00:00'))
            
            await self.collection.insert_one(ticket_data)
            self.logger.info(f"Ticket creado: {ticket.ticket_id}")
            return ticket.ticket_id
            
        except Exception as e:
            self.logger.error(f"Error creando ticket {ticket.ticket_id}: {e}")
            raise
    
    async def get_ticket(self, ticket_id: str) -> Optional[SireTicket]:
        """Obtener un ticket por ID"""
        try:
            doc = await self.collection.find_one({"ticket_id": ticket_id})
            if doc:
                # Remover el _id de MongoDB
                doc.pop('_id', None)
                return SireTicket(**doc)
            return None
            
        except Exception as e:
            self.logger.error(f"Error obteniendo ticket {ticket_id}: {e}")
            return None
    
    async def update_ticket(self, ticket: SireTicket) -> bool:
        """Actualizar un ticket existente"""
        try:
            ticket_data = ticket.model_dump()
            ticket_data.pop('_id', None)  # Remover _id si existe
            
            # Asegurar que updated_at sea la fecha actual
            ticket_data['updated_at'] = datetime.utcnow()
            
            result = await self.collection.replace_one(
                {"ticket_id": ticket.ticket_id},
                ticket_data
            )
            
            success = result.modified_count > 0
            if success:
                self.logger.info(f"Ticket actualizado: {ticket.ticket_id}")
            else:
                self.logger.warning(f"No se pudo actualizar ticket: {ticket.ticket_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error actualizando ticket {ticket.ticket_id}: {e}")
            return False
    
    async def update_ticket_status(self, 
                                  ticket_id: str, 
                                  status: TicketStatus,
                                  message: str = "",
                                  progress: Optional[float] = None,
                                  detailed_message: Optional[str] = None) -> bool:
        """Actualizar solo el estado de un ticket"""
        try:
            update_data = {
                'status': status.value,
                'status_message': message,
                'updated_at': datetime.utcnow()
            }
            
            if progress is not None:
                update_data['progress_percentage'] = min(100.0, max(0.0, progress))
            
            if detailed_message:
                update_data['detailed_message'] = detailed_message
            
            # Marcar tiempos según el estado
            if status == TicketStatus.PROCESANDO:
                update_data['processing_start'] = datetime.utcnow()
            elif status in [TicketStatus.TERMINADO, TicketStatus.ERROR, TicketStatus.CANCELADO]:
                update_data['processing_end'] = datetime.utcnow()
                if status == TicketStatus.TERMINADO:
                    update_data['progress_percentage'] = 100.0
            
            result = await self.collection.update_one(
                {"ticket_id": ticket_id},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                self.logger.info(f"Estado actualizado para ticket {ticket_id}: {status.value}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error actualizando estado de ticket {ticket_id}: {e}")
            return False
    
    async def set_ticket_completed(self, 
                                  ticket_id: str,
                                  file_name: str,
                                  file_size: int,
                                  file_type: str,
                                  file_hash: str,
                                  file_url: Optional[str] = None) -> bool:
        """Marcar ticket como completado con archivo"""
        try:
            update_data = {
                'status': TicketStatus.TERMINADO.value,
                'status_message': f"Archivo generado: {file_name}",
                'progress_percentage': 100.0,
                'updated_at': datetime.utcnow(),
                'processing_end': datetime.utcnow(),
                'output_file_name': file_name,
                'output_file_size': file_size,
                'output_file_type': file_type,
                'output_file_hash': file_hash
            }
            
            if file_url:
                update_data['output_file_url'] = file_url
            
            result = await self.collection.update_one(
                {"ticket_id": ticket_id},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                self.logger.info(f"Ticket completado: {ticket_id} -> {file_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error completando ticket {ticket_id}: {e}")
            return False
    
    async def set_ticket_error(self, 
                              ticket_id: str,
                              error_code: str,
                              error_message: str,
                              error_details: Optional[List[str]] = None) -> bool:
        """Marcar ticket como error"""
        try:
            update_data = {
                'status': TicketStatus.ERROR.value,
                'status_message': f"Error: {error_message}",
                'updated_at': datetime.utcnow(),
                'processing_end': datetime.utcnow(),
                'error_code': error_code,
                'error_message': error_message,
                'error_details': error_details or []
            }
            
            # Incrementar contador de reintentos
            await self.collection.update_one(
                {"ticket_id": ticket_id},
                {"$inc": {"retry_count": 1}}
            )
            
            result = await self.collection.update_one(
                {"ticket_id": ticket_id},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                self.logger.error(f"Ticket marcado como error: {ticket_id} -> {error_code}: {error_message}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error marcando ticket como error {ticket_id}: {e}")
            return False
    
    async def get_tickets_by_ruc(self, 
                                ruc: str, 
                                limit: int = 50, 
                                offset: int = 0,
                                status_filter: Optional[TicketStatus] = None) -> List[TicketSummary]:
        """Obtener tickets de un RUC específico"""
        try:
            query = {"ruc": ruc}
            
            if status_filter:
                query["status"] = status_filter.value
            
            cursor = self.collection.find(query) \
                                  .sort("created_at", DESCENDING) \
                                  .skip(offset) \
                                  .limit(limit)
            
            tickets = []
            async for doc in cursor:
                doc.pop('_id', None)
                tickets.append(TicketSummary(
                    ticket_id=doc['ticket_id'],
                    operation_type=doc['operation_type'],
                    status=doc['status'],
                    created_at=doc['created_at'],
                    progress_percentage=doc.get('progress_percentage', 0.0),
                    status_message=doc.get('status_message', ''),
                    output_file_name=doc.get('output_file_name')
                ))
            
            return tickets
            
        except Exception as e:
            self.logger.error(f"Error obteniendo tickets para RUC {ruc}: {e}")
            return []
    
    async def get_active_tickets(self, limit: int = 100) -> List[SireTicket]:
        """Obtener tickets activos (pendientes o procesando)"""
        try:
            query = {
                "status": {
                    "$in": [TicketStatus.PENDIENTE.value, TicketStatus.PROCESANDO.value]
                }
            }
            
            cursor = self.collection.find(query) \
                                  .sort("created_at", ASCENDING) \
                                  .limit(limit)
            
            tickets = []
            async for doc in cursor:
                doc.pop('_id', None)
                tickets.append(SireTicket(**doc))
            
            return tickets
            
        except Exception as e:
            self.logger.error(f"Error obteniendo tickets activos: {e}")
            return []
    
    async def get_expired_tickets(self) -> List[SireTicket]:
        """Obtener tickets expirados"""
        try:
            query = {
                "expires_at": {"$lt": datetime.utcnow()},
                "status": {
                    "$in": [TicketStatus.PENDIENTE.value, TicketStatus.PROCESANDO.value]
                }
            }
            
            cursor = self.collection.find(query)
            
            tickets = []
            async for doc in cursor:
                doc.pop('_id', None)
                tickets.append(SireTicket(**doc))
            
            return tickets
            
        except Exception as e:
            self.logger.error(f"Error obteniendo tickets expirados: {e}")
            return []
    
    async def mark_expired_tickets(self) -> int:
        """Marcar tickets expirados como EXPIRADO"""
        try:
            query = {
                "expires_at": {"$lt": datetime.utcnow()},
                "status": {
                    "$in": [TicketStatus.PENDIENTE.value, TicketStatus.PROCESANDO.value]
                }
            }
            
            update_data = {
                "$set": {
                    "status": TicketStatus.EXPIRADO.value,
                    "status_message": "Ticket expirado por tiempo límite",
                    "updated_at": datetime.utcnow(),
                    "processing_end": datetime.utcnow()
                }
            }
            
            result = await self.collection.update_many(query, update_data)
            
            if result.modified_count > 0:
                self.logger.info(f"Marcados {result.modified_count} tickets como expirados")
            
            return result.modified_count
            
        except Exception as e:
            self.logger.error(f"Error marcando tickets expirados: {e}")
            return 0
    
    async def delete_old_tickets(self, days_old: int = 30) -> int:
        """Eliminar tickets antiguos (más de X días)"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            query = {
                "created_at": {"$lt": cutoff_date},
                "status": {
                    "$in": [
                        TicketStatus.TERMINADO.value,
                        TicketStatus.ERROR.value,
                        TicketStatus.EXPIRADO.value,
                        TicketStatus.CANCELADO.value
                    ]
                }
            }
            
            result = await self.collection.delete_many(query)
            
            if result.deleted_count > 0:
                self.logger.info(f"Eliminados {result.deleted_count} tickets antiguos")
            
            return result.deleted_count
            
        except Exception as e:
            self.logger.error(f"Error eliminando tickets antiguos: {e}")
            return 0
    
    async def get_ticket_stats(self, ruc: Optional[str] = None) -> Dict[str, Any]:
        """Obtener estadísticas de tickets"""
        try:
            match_query = {}
            if ruc:
                match_query["ruc"] = ruc
            
            pipeline = [
                {"$match": match_query},
                {
                    "$group": {
                        "_id": "$status",
                        "count": {"$sum": 1},
                        "latest_created": {"$max": "$created_at"}
                    }
                }
            ]
            
            stats = {
                "total": 0,
                "by_status": {},
                "latest_activity": None
            }
            
            cursor = self.collection.aggregate(pipeline)
            async for doc in cursor:
                status = doc["_id"]
                count = doc["count"]
                stats["by_status"][status] = count
                stats["total"] += count
                
                if not stats["latest_activity"] or doc["latest_created"] > stats["latest_activity"]:
                    stats["latest_activity"] = doc["latest_created"]
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas de tickets: {e}")
            return {"total": 0, "by_status": {}, "latest_activity": None}
    
    async def create_indexes(self):
        """Crear índices necesarios para optimizar consultas"""
        try:
            # Índice por ticket_id (único)
            await self.collection.create_index("ticket_id", unique=True)
            
            # Índice por RUC y fecha de creación
            await self.collection.create_index([("ruc", ASCENDING), ("created_at", DESCENDING)])
            
            # Índice por estado
            await self.collection.create_index("status")
            
            # Índice por fecha de expiración
            await self.collection.create_index("expires_at")
            
            # Índice compuesto para tickets activos
            await self.collection.create_index([
                ("status", ASCENDING),
                ("created_at", ASCENDING)
            ])
            
            self.logger.info("Índices de tickets creados correctamente")
            
        except Exception as e:
            self.logger.error(f"Error creando índices de tickets: {e}")
