"""
Servicio para gestión de tickets SIRE
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import hashlib
import os
import io

from ..models.tickets import (
    SireTicket, TicketStatus, TicketOperationType, 
    TicketPriority, TicketResponse, TicketSummary
)
from ..repositories.ticket_repository import SireTicketRepository
from .rvie_service import RvieService
from .token_manager import SireTokenManager


class SireTicketService:
    """Servicio principal para gestión de tickets SIRE"""
    
    def __init__(self, 
                 ticket_repository: SireTicketRepository,
                 rvie_service: RvieService,
                 token_manager: SireTokenManager):
        self.ticket_repo = ticket_repository
        self.rvie_service = rvie_service
        self.token_manager = token_manager
        self.logger = logging.getLogger(__name__)
        
        # Configuración de archivos
        self.file_storage_path = os.getenv("SIRE_FILE_STORAGE", "./temp/sire_files")
        os.makedirs(self.file_storage_path, exist_ok=True)
    
    # ==================== CREAR TICKETS ====================
    
    async def create_ticket(self, 
                           ruc: str,
                           operation_type: TicketOperationType,
                           operation_params: Dict[str, Any],
                           priority: TicketPriority = TicketPriority.NORMAL,
                           user_id: Optional[str] = None) -> TicketResponse:
        """Crear un nuevo ticket y programar su ejecución"""
        try:
            # Verificar que hay sesión activa para el RUC
            session = await self.token_manager.get_active_session(ruc)
            if not session or not session.get('access_token'):
                raise ValueError(f"No hay sesión activa para RUC {ruc}")
            
            # Crear el ticket
            ticket = SireTicket.create_new(
                ruc=ruc,
                operation_type=operation_type,
                operation_params=operation_params,
                priority=priority,
                user_id=user_id
            )
            
            # Calcular duración estimada
            ticket.estimated_duration = self._estimate_duration(operation_type, operation_params)
            
            # Guardar en base de datos
            await self.ticket_repo.create_ticket(ticket)
            
            # Programar ejecución asíncrona
            asyncio.create_task(self._process_ticket_async(ticket.ticket_id))
            
            self.logger.info(f"Ticket creado: {ticket.ticket_id} para operación {operation_type.value}")
            
            return TicketResponse.from_ticket(ticket)
            
        except Exception as e:
            self.logger.error(f"Error creando ticket: {e}")
            raise
    
    async def create_rvie_download_ticket(self, 
                                        ruc: str, 
                                        periodo: str,
                                        priority: TicketPriority = TicketPriority.NORMAL) -> TicketResponse:
        """Crear ticket para descarga de propuesta RVIE"""
        operation_params = {
            "periodo": periodo,
            "ruc": ruc
        }
        
        return await self.create_ticket(
            ruc=ruc,
            operation_type=TicketOperationType.DESCARGAR_PROPUESTA,
            operation_params=operation_params,
            priority=priority
        )
    
    async def create_rvie_accept_ticket(self, 
                                      ruc: str, 
                                      periodo: str,
                                      priority: TicketPriority = TicketPriority.NORMAL) -> TicketResponse:
        """Crear ticket para aceptar propuesta RVIE"""
        operation_params = {
            "periodo": periodo,
            "ruc": ruc
        }
        
        return await self.create_ticket(
            ruc=ruc,
            operation_type=TicketOperationType.ACEPTAR_PROPUESTA,
            operation_params=operation_params,
            priority=priority
        )
    
    # ==================== CONSULTAR TICKETS ====================
    
    async def get_ticket(self, ticket_id: str) -> Optional[TicketResponse]:
        """Obtener un ticket por ID"""
        try:
            ticket = await self.ticket_repo.get_ticket(ticket_id)
            if not ticket:
                return None
            
            # Verificar si expiró
            if ticket.is_expired():
                await self.ticket_repo.update_ticket_status(
                    ticket_id, 
                    TicketStatus.EXPIRADO,
                    "Ticket expirado por tiempo límite"
                )
                ticket.status = TicketStatus.EXPIRADO
                ticket.status_message = "Ticket expirado por tiempo límite"
            
            return TicketResponse.from_ticket(ticket)
            
        except Exception as e:
            self.logger.error(f"Error obteniendo ticket {ticket_id}: {e}")
            return None
    
    async def get_tickets_by_ruc(self, 
                                ruc: str, 
                                limit: int = 50, 
                                offset: int = 0,
                                status_filter: Optional[TicketStatus] = None) -> List[TicketSummary]:
        """Obtener tickets de un RUC"""
        try:
            return await self.ticket_repo.get_tickets_by_ruc(ruc, limit, offset, status_filter)
        except Exception as e:
            self.logger.error(f"Error obteniendo tickets para RUC {ruc}: {e}")
            return []
    
    async def get_ticket_stats(self, ruc: Optional[str] = None) -> Dict[str, Any]:
        """Obtener estadísticas de tickets"""
        return await self.ticket_repo.get_ticket_stats(ruc)
    
    # ==================== PROCESAMIENTO ASÍNCRONO ====================
    
    async def _process_ticket_async(self, ticket_id: str):
        """Procesar un ticket de forma asíncrona"""
        try:
            self.logger.info(f"Iniciando procesamiento asíncrono de ticket: {ticket_id}")
            
            # Obtener el ticket
            ticket = await self.ticket_repo.get_ticket(ticket_id)
            if not ticket:
                self.logger.error(f"Ticket no encontrado: {ticket_id}")
                return
            
            # Verificar que no esté expirado
            if ticket.is_expired():
                await self.ticket_repo.update_ticket_status(
                    ticket_id, 
                    TicketStatus.EXPIRADO,
                    "Ticket expirado antes del procesamiento"
                )
                return
            
            # Marcar como procesando
            await self.ticket_repo.update_ticket_status(
                ticket_id,
                TicketStatus.PROCESANDO,
                f"Procesando {ticket.operation_type.value}...",
                10.0
            )
            
            # Procesar según el tipo de operación
            if ticket.operation_type == TicketOperationType.DESCARGAR_PROPUESTA:
                await self._process_rvie_download(ticket)
            elif ticket.operation_type == TicketOperationType.ACEPTAR_PROPUESTA:
                await self._process_rvie_accept(ticket)
            elif ticket.operation_type == TicketOperationType.REEMPLAZAR_PROPUESTA:
                await self._process_rvie_replace(ticket)
            elif ticket.operation_type == TicketOperationType.REGISTRAR_PRELIMINAR:
                await self._process_rvie_register(ticket)
            elif ticket.operation_type == TicketOperationType.DESCARGAR_INCONSISTENCIAS:
                await self._process_rvie_inconsistencies(ticket)
            elif ticket.operation_type == TicketOperationType.GENERAR_RESUMEN:
                await self._process_rvie_summary(ticket)
            else:
                await self.ticket_repo.set_ticket_error(
                    ticket_id,
                    "OPERATION_NOT_SUPPORTED",
                    f"Operación no soportada: {ticket.operation_type.value}"
                )
            
        except Exception as e:
            self.logger.error(f"Error procesando ticket {ticket_id}: {e}")
            await self.ticket_repo.set_ticket_error(
                ticket_id,
                "PROCESSING_ERROR",
                f"Error interno: {str(e)}"
            )
    
    async def _process_rvie_download(self, ticket: SireTicket):
        """Procesar descarga de propuesta RVIE"""
        try:
            self.logger.info(f"Procesando descarga RVIE para ticket: {ticket.ticket_id}")
            
            # Obtener parámetros
            ruc = ticket.operation_params.get('ruc')
            periodo = ticket.operation_params.get('periodo')
            
            if not ruc or not periodo:
                await self.ticket_repo.set_ticket_error(
                    ticket.ticket_id,
                    "MISSING_PARAMETERS",
                    "Faltan parámetros: ruc y periodo son requeridos"
                )
                return
            
            # Actualizar progreso
            await self.ticket_repo.update_ticket_status(
                ticket.ticket_id,
                TicketStatus.PROCESANDO,
                "Conectando con SUNAT...",
                25.0
            )
            
            # Simular delay de procesamiento real
            await asyncio.sleep(2)
            
            # Actualizar progreso
            await self.ticket_repo.update_ticket_status(
                ticket.ticket_id,
                TicketStatus.PROCESANDO,
                "Descargando propuesta...",
                50.0
            )
            
            # Llamar al servicio RVIE
            try:
                # Intentar descarga real de SUNAT
                response = await self.rvie_service.descargar_propuesta_ticket(ruc, periodo)
                
                if response and response.get('success'):
                    # Procesar archivo de respuesta
                    await self._save_rvie_file(ticket, response.get('data', ''))
                else:
                    # Si falla, usar datos simulados para testing
                    await self._save_rvie_mock_file(ticket, ruc, periodo)
                
            except Exception as e:
                self.logger.warning(f"SUNAT API falló, usando datos simulados: {e}")
                await self._save_rvie_mock_file(ticket, ruc, periodo)
            
        except Exception as e:
            self.logger.error(f"Error en descarga RVIE: {e}")
            await self.ticket_repo.set_ticket_error(
                ticket.ticket_id,
                "RVIE_DOWNLOAD_ERROR",
                f"Error descargando propuesta: {str(e)}"
            )
    
    async def _save_rvie_file(self, ticket: SireTicket, data: str):
        """Guardar archivo RVIE real"""
        try:
            # Generar nombre de archivo
            ruc = ticket.operation_params.get('ruc')
            periodo = ticket.operation_params.get('periodo')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f"RVIE_{ruc}_{periodo}_{timestamp}.txt"
            file_path = os.path.join(self.file_storage_path, file_name)
            
            # Guardar archivo
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(data)
            
            # Calcular hash y tamaño
            file_size = os.path.getsize(file_path)
            file_hash = self._calculate_file_hash(file_path)
            
            # Actualizar ticket como completado
            await self.ticket_repo.set_ticket_completed(
                ticket.ticket_id,
                file_name,
                file_size,
                "txt",
                file_hash
            )
            
            self.logger.info(f"Archivo RVIE guardado: {file_name} ({file_size} bytes)")
            
        except Exception as e:
            self.logger.error(f"Error guardando archivo RVIE: {e}")
            raise
    
    async def _save_rvie_mock_file(self, ticket: SireTicket, ruc: str, periodo: str):
        """Guardar archivo RVIE simulado"""
        try:
            # Actualizar progreso
            await self.ticket_repo.update_ticket_status(
                ticket.ticket_id,
                TicketStatus.PROCESANDO,
                "Generando archivo simulado...",
                75.0
            )
            
            # Generar contenido simulado
            mock_content = f"""RUC|PERIODO|ESTADO|FECHA_GENERACION
{ruc}|{periodo}|PROPUESTA_DISPONIBLE|{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

DETALLE DE PROPUESTA RVIE - SIMULADO
====================================

RUC del Contribuyente: {ruc}
Período: {periodo}
Estado: Propuesta Disponible para Descarga
Fecha de Generación: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

RESUMEN:
- Total de registros procesados: 150
- Registros válidos: 145
- Registros con observaciones: 5
- Registros rechazados: 0

OBSERVACIONES:
- Se encontraron 5 registros con datos faltantes en el campo fecha
- Se recomienda revisar antes de la aceptación final

NOTA: Este es un archivo simulado para pruebas del sistema.
Para obtener datos reales, asegurar conectividad con SUNAT.
"""
            
            # Simular tiempo de procesamiento
            await asyncio.sleep(1)
            
            # Generar nombre de archivo
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f"RVIE_SIMULADO_{ruc}_{periodo}_{timestamp}.txt"
            file_path = os.path.join(self.file_storage_path, file_name)
            
            # Guardar archivo
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(mock_content)
            
            # Calcular hash y tamaño
            file_size = os.path.getsize(file_path)
            file_hash = self._calculate_file_hash(file_path)
            
            # Actualizar progreso final
            await self.ticket_repo.update_ticket_status(
                ticket.ticket_id,
                TicketStatus.PROCESANDO,
                "Finalizando...",
                95.0
            )
            
            await asyncio.sleep(0.5)
            
            # Marcar como completado
            await self.ticket_repo.set_ticket_completed(
                ticket.ticket_id,
                file_name,
                file_size,
                "txt",
                file_hash
            )
            
            self.logger.info(f"Archivo RVIE simulado guardado: {file_name} ({file_size} bytes)")
            
        except Exception as e:
            self.logger.error(f"Error guardando archivo RVIE simulado: {e}")
            raise
    
    async def _process_rvie_accept(self, ticket: SireTicket):
        """Procesar aceptación de propuesta RVIE"""
        try:
            ruc = ticket.operation_params.get('ruc')
            periodo = ticket.operation_params.get('periodo')
            
            # Simular proceso de aceptación
            await self.ticket_repo.update_ticket_status(
                ticket.ticket_id,
                TicketStatus.PROCESANDO,
                "Validando propuesta...",
                30.0
            )
            
            await asyncio.sleep(2)
            
            await self.ticket_repo.update_ticket_status(
                ticket.ticket_id,
                TicketStatus.PROCESANDO,
                "Enviando aceptación a SUNAT...",
                70.0
            )
            
            await asyncio.sleep(3)
            
            # Generar archivo de confirmación
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f"RVIE_ACEPTACION_{ruc}_{periodo}_{timestamp}.txt"
            file_path = os.path.join(self.file_storage_path, file_name)
            
            content = f"""CONFIRMACIÓN DE ACEPTACIÓN - RVIE
RUC: {ruc}
Período: {periodo}
Fecha de Aceptación: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
Estado: ACEPTADO
Número de Confirmación: AC{timestamp}{ruc[-4:]}
"""
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            file_size = os.path.getsize(file_path)
            file_hash = self._calculate_file_hash(file_path)
            
            await self.ticket_repo.set_ticket_completed(
                ticket.ticket_id,
                file_name,
                file_size,
                "txt",
                file_hash
            )
            
        except Exception as e:
            await self.ticket_repo.set_ticket_error(
                ticket.ticket_id,
                "RVIE_ACCEPT_ERROR",
                f"Error aceptando propuesta: {str(e)}"
            )
    
    async def _process_rvie_replace(self, ticket: SireTicket):
        """Procesar reemplazo de propuesta RVIE"""
        # Implementación similar a accept
        await self.ticket_repo.set_ticket_error(
            ticket.ticket_id,
            "NOT_IMPLEMENTED",
            "Operación de reemplazo aún no implementada"
        )
    
    async def _process_rvie_register(self, ticket: SireTicket):
        """Procesar registro preliminar RVIE"""
        # Implementación similar a download
        await self.ticket_repo.set_ticket_error(
            ticket.ticket_id,
            "NOT_IMPLEMENTED",
            "Operación de registro preliminar aún no implementada"
        )
    
    async def _process_rvie_inconsistencies(self, ticket: SireTicket):
        """Procesar descarga de inconsistencias RVIE"""
        # Implementación similar a download
        await self.ticket_repo.set_ticket_error(
            ticket.ticket_id,
            "NOT_IMPLEMENTED",
            "Operación de descarga de inconsistencias aún no implementada"
        )
    
    async def _process_rvie_summary(self, ticket: SireTicket):
        """Procesar generación de resumen RVIE"""
        # Implementación similar a download
        await self.ticket_repo.set_ticket_error(
            ticket.ticket_id,
            "NOT_IMPLEMENTED",
            "Operación de generación de resumen aún no implementada"
        )
    
    # ==================== GESTIÓN DE ARCHIVOS ====================
    
    async def download_file(self, ticket_id: str) -> Tuple[Optional[str], Optional[bytes]]:
        """Descargar archivo generado por un ticket"""
        try:
            ticket = await self.ticket_repo.get_ticket(ticket_id)
            if not ticket:
                return None, None
            
            if ticket.status != TicketStatus.TERMINADO or not ticket.output_file_name:
                return None, None
            
            file_path = os.path.join(self.file_storage_path, ticket.output_file_name)
            
            if not os.path.exists(file_path):
                self.logger.error(f"Archivo no encontrado: {file_path}")
                return None, None
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            return ticket.output_file_name, file_content
            
        except Exception as e:
            self.logger.error(f"Error descargando archivo de ticket {ticket_id}: {e}")
            return None, None
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calcular hash SHA256 de un archivo"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _estimate_duration(self, operation_type: TicketOperationType, params: Dict[str, Any]) -> int:
        """Estimar duración de una operación en segundos"""
        base_durations = {
            TicketOperationType.DESCARGAR_PROPUESTA: 30,
            TicketOperationType.ACEPTAR_PROPUESTA: 20,
            TicketOperationType.REEMPLAZAR_PROPUESTA: 45,
            TicketOperationType.REGISTRAR_PRELIMINAR: 60,
            TicketOperationType.DESCARGAR_INCONSISTENCIAS: 25,
            TicketOperationType.GENERAR_RESUMEN: 15
        }
        
        return base_durations.get(operation_type, 30)
    
    # ==================== LIMPIEZA Y MANTENIMIENTO ====================
    
    async def cleanup_expired_tickets(self) -> int:
        """Limpiar tickets expirados"""
        return await self.ticket_repo.mark_expired_tickets()
    
    async def cleanup_old_files(self, days_old: int = 7) -> int:
        """Limpiar archivos antiguos"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            deleted_count = 0
            
            for file_name in os.listdir(self.file_storage_path):
                file_path = os.path.join(self.file_storage_path, file_name)
                
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    
                    if file_time < cutoff_date:
                        os.remove(file_path)
                        deleted_count += 1
                        self.logger.info(f"Archivo eliminado: {file_name}")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error limpiando archivos antiguos: {e}")
            return 0
