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
from ..models.sunat_ticket import (
    SunatTicketRequest, SunatTicketResponse, SunatTicketStatusResponse,
    SunatOperationType, SunatTicketStatus, map_sunat_error
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
    
    def _normalize_ruc(self, ruc: str) -> str:
        """
        Normalizar RUC eliminando espacios y caracteres extra
        
        Args:
            ruc: RUC a normalizar
            
        Returns:
            str: RUC normalizado
        """
        if not ruc:
            return ruc
            
        # Limpiar espacios y caracteres especiales
        normalized = ''.join(c for c in str(ruc).strip() if c.isdigit())
        
        # Validar longitud (RUC debe tener 11 dígitos)
        if len(normalized) != 11:
            pass  # RUC no tiene 11 dígitos
        
        return normalized
    
    # ==================== CREAR TICKETS ====================
    
    async def create_ticket(self, 
                           ruc: str,
                           operation_type: TicketOperationType,
                           operation_params: Dict[str, Any],
                           priority: TicketPriority = TicketPriority.NORMAL,
                           user_id: Optional[str] = None) -> TicketResponse:
        """Crear un nuevo ticket y programar su ejecución con validación SUNAT"""
        try:
            # Verificar que hay sesión activa para el RUC
            session = await self.token_manager.get_active_session(ruc)
            if not session or not session.get('access_token'):
                raise ValueError(f"No hay sesión activa para RUC {ruc}")
            
            # Validar parámetros según el manual SUNAT
            await self._validate_operation_params(operation_type, operation_params)
            
            # Mapear operación interna a operación SUNAT
            sunat_operation = self._map_to_sunat_operation(operation_type)
            
            # Crear request para SUNAT
            sunat_request = SunatTicketRequest(
                ruc=ruc,
                periodo=operation_params.get('periodo', ''),
                operacion=sunat_operation,
                parametros=operation_params
            )
            
            # Crear ticket en SUNAT primero
            try:
                sunat_response = await self._create_sunat_ticket(sunat_request, session['access_token'])
                
                # Crear el ticket local con ID de SUNAT
                ticket = SireTicket.create_new(
                    ruc=ruc,
                    operation_type=operation_type,
                    operation_params=operation_params,
                    priority=priority,
                    user_id=user_id
                )
                
                # Usar ID de ticket de SUNAT
                ticket.ticket_id = sunat_response.ticket
                ticket.status_message = f"Ticket creado en SUNAT: {sunat_response.mensaje}"
                
            except Exception as sunat_error:
                raise ValueError(f"Error creando ticket en SUNAT: {sunat_error}")
            
            # Calcular duración estimada
            ticket.estimated_duration = self._estimate_duration(operation_type, operation_params)
            
            # Guardar en base de datos
            await self.ticket_repo.create_ticket(ticket)
            
            # Programar ejecución asíncrona
            asyncio.create_task(self._process_ticket_async(ticket.ticket_id))
            
            return TicketResponse.from_ticket(ticket)
            
        except Exception as e:
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
    
        
    # ==================== VALIDACIONES SEGÚN MANUAL SUNAT ====================
    
    async def _validate_operation_params(self, operation_type: TicketOperationType, params: Dict[str, Any]):
        """Validar parámetros de operación según manual SUNAT v25"""
        # Validación de RUC
        ruc = params.get('ruc', '')
        if not ruc or len(ruc) != 11 or not ruc.isdigit():
            raise ValueError("RUC debe tener 11 dígitos")
        
        # Validación de período
        periodo = params.get('periodo', '')
        if not periodo or len(periodo) != 6 or not periodo.isdigit():
            raise ValueError("Período debe tener formato YYYYMM")
        
        # Validaciones específicas por tipo de operación
        if operation_type == TicketOperationType.DESCARGAR_PROPUESTA:
            # Validar que el período sea válido (no futuro)
            year = int(periodo[:4])
            month = int(periodo[4:])
            if year < 2018 or year > datetime.now().year:
                raise ValueError(f"Año {year} no válido para RVIE")
            if month < 1 or month > 12:
                raise ValueError(f"Mes {month} no válido")
            
            # No permitir períodos futuros
            current_year = datetime.now().year
            current_month = datetime.now().month
            if year > current_year or (year == current_year and month > current_month):
                raise ValueError(f"Período {periodo} es futuro, no permitido")
    
    def _map_to_sunat_operation(self, operation_type: TicketOperationType) -> SunatOperationType:
        """Mapear operación interna a operación SUNAT"""
        mapping = {
            TicketOperationType.DESCARGAR_PROPUESTA: SunatOperationType.RVIE_DESCARGAR_PROPUESTA,
            TicketOperationType.ACEPTAR_PROPUESTA: SunatOperationType.RVIE_ACEPTAR_PROPUESTA,
            TicketOperationType.REEMPLAZAR_PROPUESTA: SunatOperationType.RVIE_REEMPLAZAR_PROPUESTA,
            TicketOperationType.REGISTRAR_PRELIMINAR: SunatOperationType.RVIE_REGISTRAR_PRELIMINAR,
            TicketOperationType.DESCARGAR_INCONSISTENCIAS: SunatOperationType.RVIE_DESCARGAR_INCONSISTENCIAS,
        }
        
        sunat_op = mapping.get(operation_type)
        if not sunat_op:
            raise ValueError(f"Operación {operation_type} no soportada")
        
        return sunat_op
    
    async def _create_sunat_ticket(self, request: SunatTicketRequest, access_token: str) -> SunatTicketResponse:
        """Crear ticket directamente en SUNAT"""
        try:
            # Construir endpoint según el tipo de operación
            endpoint = self._get_sunat_endpoint(request.operacion)
            
            # Preparar headers y datos
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Datos específicos para SUNAT
            payload = {
                'ruc': request.ruc,
                'periodo': request.periodo,
                'parametros': request.parametros
            }
            
            # Hacer request a SUNAT
            response = await self.rvie_service.api_client._make_request(
                method='POST',
                url=f"{self.rvie_service.api_client.base_url}{endpoint}",
                headers=headers,
                data=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                return SunatTicketResponse(
                    ticket=data['ticket'],
                    fecha_generacion=datetime.fromisoformat(data['fecha_generacion']),
                    estado=SunatTicketStatus(data['estado']),
                    mensaje=data.get('mensaje', 'Ticket creado')
                )
            else:
                error_data = response.json()
                raise ValueError(f"Error SUNAT: {error_data.get('mensaje', 'Error desconocido')}")
                
        except Exception as e:
            raise
    
    def _get_sunat_endpoint(self, operation: SunatOperationType) -> str:
        """Obtener endpoint SUNAT según operación"""
        endpoints = {
            SunatOperationType.RVIE_DESCARGAR_PROPUESTA: "/sire/rvie/propuesta/descargar",
            SunatOperationType.RVIE_ACEPTAR_PROPUESTA: "/sire/rvie/propuesta/aceptar",
            SunatOperationType.RVIE_REEMPLAZAR_PROPUESTA: "/sire/rvie/propuesta/reemplazar",
            SunatOperationType.RVIE_REGISTRAR_PRELIMINAR: "/sire/rvie/preliminar/registrar",
            SunatOperationType.RVIE_DESCARGAR_INCONSISTENCIAS: "/sire/rvie/inconsistencias/descargar",
        }
        
        return endpoints.get(operation, "/sire/rvie/operacion")
    
    async def sync_with_sunat_status(self, ticket_id: str) -> bool:
        """Sincronizar estado de ticket con SUNAT"""
        try:
            # Obtener ticket local
            ticket = await self.ticket_repo.get_ticket(ticket_id)
            if not ticket:
                return False
            
            # Obtener sesión activa
            session = await self.token_manager.get_active_session(ticket.ruc)
            if not session:
                return False
            
            # Consultar estado en SUNAT
            sunat_status = await self._query_sunat_ticket_status(ticket_id, session['access_token'])
            
            # Mapear estado SUNAT a estado interno
            internal_status = self._map_sunat_status(sunat_status.estado)
            
            # Actualizar ticket local
            if internal_status != ticket.status:
                ticket.update_status(
                    new_status=internal_status,
                    message=sunat_status.mensaje,
                    progress=sunat_status.porcentaje_avance
                )
                
                # Si está terminado, actualizar info del archivo
                if internal_status == TicketStatus.TERMINADO and sunat_status.nombre_archivo:
                    ticket.set_completed(
                        file_name=sunat_status.nombre_archivo,
                        file_size=sunat_status.tamaño_archivo or 0,
                        file_type="ZIP",
                        file_hash=sunat_status.hash_archivo or ""
                    )
                
                # Si hay error, actualizar info del error
                elif internal_status == TicketStatus.ERROR:
                    ticket.set_error(
                        error_code=sunat_status.codigo_error or "UNKNOWN",
                        error_message=sunat_status.detalle_error or sunat_status.mensaje
                    )
                
                # Guardar cambios
                await self.ticket_repo.update_ticket_status(
                    ticket_id=ticket_id,
                    status=internal_status,
                    message=sunat_status.mensaje,
                    progress=sunat_status.porcentaje_avance
                )
            
            return True
            
        except Exception as e:
            return False
    
    async def _query_sunat_ticket_status(self, ticket_id: str, access_token: str) -> SunatTicketStatusResponse:
        """Consultar estado de ticket en SUNAT"""
        try:
            endpoint = f"/sire/ticket/{ticket_id}/estado"
            headers = {'Authorization': f'Bearer {access_token}'}
            
            response = await self.rvie_service.api_client._make_request(
                method='GET',
                url=f"{self.rvie_service.api_client.base_url}{endpoint}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return SunatTicketStatusResponse(**data)
            else:
                raise ValueError(f"Error consultando ticket en SUNAT: {response.status_code}")
                
        except Exception as e:
            raise
    
    def _map_sunat_status(self, sunat_status: SunatTicketStatus) -> TicketStatus:
        """Mapear estado SUNAT a estado interno"""
        mapping = {
            SunatTicketStatus.PENDIENTE: TicketStatus.PENDIENTE,
            SunatTicketStatus.PROCESANDO: TicketStatus.PROCESANDO,
            SunatTicketStatus.TERMINADO: TicketStatus.TERMINADO,
            SunatTicketStatus.ERROR: TicketStatus.ERROR,
            SunatTicketStatus.CANCELADO: TicketStatus.CANCELADO,
        }
        
        return mapping.get(sunat_status, TicketStatus.ERROR)
    
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
            return []
    
    async def get_ticket_stats(self, ruc: Optional[str] = None) -> Dict[str, Any]:
        """Obtener estadísticas de tickets"""
        return await self.ticket_repo.get_ticket_stats(ruc)
    
    # ==================== PROCESAMIENTO ASÍNCRONO ====================
    
    async def _process_ticket_async(self, ticket_id: str):
        """Procesar un ticket de forma asíncrona"""
        try:
            # Obtener el ticket
            ticket = await self.ticket_repo.get_ticket(ticket_id)
            if not ticket:
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
            await self.ticket_repo.set_ticket_error(
                ticket_id,
                "PROCESSING_ERROR",
                f"Error interno: {str(e)}"
            )
    
    async def _process_rvie_download(self, ticket: SireTicket):
        """Procesar descarga de propuesta RVIE"""
        try:
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
                    # Si no hay respuesta válida, marcar como error
                    await self.ticket_repo.set_ticket_error(
                        ticket.ticket_id,
                        "SUNAT_NO_DATA",
                        "SUNAT no devolvió datos válidos"
                    )
                    return
                
            except Exception as e:
                await self.ticket_repo.set_ticket_error(
                    ticket.ticket_id,
                    "SUNAT_CONNECTION_ERROR",
                    f"Error conectando con SUNAT: {str(e)}"
                )
                return
            
        except Exception as e:
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
        except Exception as e:
            raise
    
    async def _process_rvie_accept(self, ticket: SireTicket):
        """Procesar aceptación de propuesta RVIE"""
        try:
            ruc = ticket.operation_params.get('ruc')
            periodo = ticket.operation_params.get('periodo')
            
            # Validar propuesta con SUNAT antes de aceptar
            await self.ticket_repo.update_ticket_status(
                ticket.ticket_id,
                TicketStatus.PROCESANDO,
                "Validando propuesta...",
                30.0
            )
            
            # Enviar aceptación a SUNAT
            await self.ticket_repo.update_ticket_status(
                ticket.ticket_id,
                TicketStatus.PROCESANDO,
                "Enviando aceptación a SUNAT...",
                70.0
            )
            
            # Llamar al servicio RVIE para aceptar
            response = await self.rvie_service.aceptar_propuesta(ruc, periodo)
            
            if not response or not response.get('success'):
                await self.ticket_repo.set_ticket_error(
                    ticket.ticket_id,
                    "RVIE_ACCEPT_FAILED",
                    "SUNAT rechazó la aceptación de propuesta"
                )
                return
            
            # Procesar respuesta de aceptación
            confirmation_data = response.get('data', '')
            if confirmation_data:
                # Guardar archivo de confirmación
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                file_name = f"RVIE_ACEPTACION_{ruc}_{periodo}_{timestamp}.txt"
                file_path = os.path.join(self.file_storage_path, file_name)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(confirmation_data)
                
                file_size = os.path.getsize(file_path)
                file_hash = self._calculate_file_hash(file_path)
                
                await self.ticket_repo.set_ticket_completed(
                    ticket.ticket_id,
                    file_name,
                    file_size,
                    "txt",
                    file_hash
                )
            else:
                await self.ticket_repo.set_ticket_error(
                    ticket.ticket_id,
                    "NO_CONFIRMATION_DATA",
                    "SUNAT no devolvió datos de confirmación"
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
                return None, None
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            return ticket.output_file_name, file_content
            
        except Exception as e:
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
            
            return deleted_count
            
        except Exception as e:
            return 0
