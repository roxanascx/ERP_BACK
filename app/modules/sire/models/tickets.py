"""
Modelos para el sistema de tickets SIRE
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum
import uuid


class TicketOperationType(str, Enum):
    """Tipos de operación que generan tickets"""
    DESCARGAR_PROPUESTA = "DESCARGAR_PROPUESTA"
    ACEPTAR_PROPUESTA = "ACEPTAR_PROPUESTA"
    REEMPLAZAR_PROPUESTA = "REEMPLAZAR_PROPUESTA"
    REGISTRAR_PRELIMINAR = "REGISTRAR_PRELIMINAR"
    DESCARGAR_INCONSISTENCIAS = "DESCARGAR_INCONSISTENCIAS"
    GENERAR_RESUMEN = "GENERAR_RESUMEN"


class TicketStatus(str, Enum):
    """Estados del ticket durante su ciclo de vida"""
    PENDIENTE = "PENDIENTE"          # Recién creado, en cola
    PROCESANDO = "PROCESANDO"        # En proceso de ejecución
    TERMINADO = "TERMINADO"          # Completado exitosamente
    ERROR = "ERROR"                  # Falló durante el procesamiento
    EXPIRADO = "EXPIRADO"           # Expiró sin completarse
    CANCELADO = "CANCELADO"         # Cancelado por el usuario


class TicketPriority(str, Enum):
    """Prioridad del ticket"""
    BAJA = "BAJA"
    NORMAL = "NORMAL"
    ALTA = "ALTA"
    URGENTE = "URGENTE"


class SireTicket(BaseModel):
    """Modelo principal de ticket SIRE"""
    # Identificación
    ticket_id: str = Field(..., description="ID único del ticket")
    ruc: str = Field(..., description="RUC del contribuyente")
    
    # Información de la operación
    operation_type: TicketOperationType = Field(..., description="Tipo de operación")
    operation_params: Dict[str, Any] = Field(..., description="Parámetros de la operación")
    
    # Estado del ticket
    status: TicketStatus = Field(default=TicketStatus.PENDIENTE, description="Estado actual")
    priority: TicketPriority = Field(default=TicketPriority.NORMAL, description="Prioridad")
    
    # Información temporal
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Fecha de creación")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Última actualización")
    expires_at: datetime = Field(..., description="Fecha de expiración")
    
    # Progreso y mensajes
    progress_percentage: float = Field(default=0.0, description="Porcentaje de progreso (0-100)")
    status_message: str = Field(default="", description="Mensaje descriptivo del estado")
    detailed_message: Optional[str] = Field(None, description="Mensaje detallado")
    
    # Tiempo estimado
    estimated_duration: Optional[int] = Field(None, description="Duración estimada en segundos")
    processing_start: Optional[datetime] = Field(None, description="Inicio del procesamiento")
    processing_end: Optional[datetime] = Field(None, description="Fin del procesamiento")
    
    # Archivo generado
    output_file_name: Optional[str] = Field(None, description="Nombre del archivo generado")
    output_file_size: Optional[int] = Field(None, description="Tamaño del archivo en bytes")
    output_file_type: Optional[str] = Field(None, description="Tipo de archivo (txt, xlsx, pdf)")
    output_file_url: Optional[str] = Field(None, description="URL temporal de descarga")
    output_file_hash: Optional[str] = Field(None, description="Hash del archivo para verificación")
    
    # Errores
    error_code: Optional[str] = Field(None, description="Código de error si falló")
    error_message: Optional[str] = Field(None, description="Mensaje de error")
    error_details: Optional[List[str]] = Field(None, description="Detalles del error")
    retry_count: int = Field(default=0, description="Número de reintentos")
    
    # Metadatos
    user_id: Optional[str] = Field(None, description="ID del usuario que creó el ticket")
    session_id: Optional[str] = Field(None, description="ID de sesión")
    request_ip: Optional[str] = Field(None, description="IP de la solicitud")
    user_agent: Optional[str] = Field(None, description="User agent del cliente")

    @classmethod
    def create_new(cls, 
                   ruc: str, 
                   operation_type: TicketOperationType,
                   operation_params: Dict[str, Any],
                   priority: TicketPriority = TicketPriority.NORMAL,
                   user_id: Optional[str] = None) -> "SireTicket":
        """Crear un nuevo ticket"""
        ticket_id = f"TKT_{operation_type.value}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8].upper()}"
        
        # Calcular tiempo de expiración según el tipo de operación
        expiration_hours = {
            TicketOperationType.DESCARGAR_PROPUESTA: 2,  # 2 horas
            TicketOperationType.ACEPTAR_PROPUESTA: 1,    # 1 hora
            TicketOperationType.REEMPLAZAR_PROPUESTA: 4, # 4 horas
            TicketOperationType.REGISTRAR_PRELIMINAR: 3, # 3 horas
            TicketOperationType.DESCARGAR_INCONSISTENCIAS: 1, # 1 hora
            TicketOperationType.GENERAR_RESUMEN: 1       # 1 hora
        }
        
        expires_at = datetime.utcnow() + timedelta(hours=expiration_hours.get(operation_type, 2))
        
        return cls(
            ticket_id=ticket_id,
            ruc=ruc,
            operation_type=operation_type,
            operation_params=operation_params,
            priority=priority,
            expires_at=expires_at,
            status_message=f"Ticket creado para {operation_type.value}",
            user_id=user_id
        )

    def update_status(self, 
                     new_status: TicketStatus,
                     message: str = "",
                     progress: Optional[float] = None,
                     detailed_message: Optional[str] = None):
        """Actualizar estado del ticket"""
        self.status = new_status
        self.status_message = message
        self.updated_at = datetime.utcnow()
        
        if progress is not None:
            self.progress_percentage = min(100.0, max(0.0, progress))
        
        if detailed_message:
            self.detailed_message = detailed_message
        
        # Marcar tiempos según el estado
        if new_status == TicketStatus.PROCESANDO and not self.processing_start:
            self.processing_start = datetime.utcnow()
        elif new_status in [TicketStatus.TERMINADO, TicketStatus.ERROR, TicketStatus.CANCELADO]:
            self.processing_end = datetime.utcnow()
            if new_status == TicketStatus.TERMINADO:
                self.progress_percentage = 100.0

    def set_error(self, error_code: str, error_message: str, error_details: Optional[List[str]] = None):
        """Marcar ticket como error"""
        self.update_status(TicketStatus.ERROR, f"Error: {error_message}")
        self.error_code = error_code
        self.error_message = error_message
        self.error_details = error_details or []

    def set_completed(self, file_name: str, file_size: int, file_type: str, file_hash: str):
        """Marcar ticket como completado con archivo"""
        self.update_status(TicketStatus.TERMINADO, f"Archivo generado: {file_name}", 100.0)
        self.output_file_name = file_name
        self.output_file_size = file_size
        self.output_file_type = file_type
        self.output_file_hash = file_hash

    def is_expired(self) -> bool:
        """Verificar si el ticket ha expirado"""
        return datetime.utcnow() > self.expires_at and self.status not in [
            TicketStatus.TERMINADO, TicketStatus.ERROR, TicketStatus.CANCELADO
        ]

    def can_retry(self) -> bool:
        """Verificar si se puede reintentar"""
        return self.status == TicketStatus.ERROR and self.retry_count < 3

    def get_elapsed_time(self) -> Optional[int]:
        """Obtener tiempo transcurrido en segundos"""
        if not self.processing_start:
            return None
        
        end_time = self.processing_end or datetime.utcnow()
        return int((end_time - self.processing_start).total_seconds())

    def get_remaining_time(self) -> Optional[int]:
        """Obtener tiempo restante estimado en segundos"""
        if not self.estimated_duration or not self.processing_start:
            return None
        
        elapsed = self.get_elapsed_time()
        if elapsed is None:
            return self.estimated_duration
        
        remaining = self.estimated_duration - elapsed
        return max(0, remaining)


class TicketSummary(BaseModel):
    """Resumen de ticket para listados"""
    ticket_id: str
    operation_type: TicketOperationType
    status: TicketStatus
    created_at: datetime
    progress_percentage: float
    status_message: str
    output_file_name: Optional[str] = None


class TicketFilter(BaseModel):
    """Filtros para consulta de tickets"""
    ruc: Optional[str] = None
    operation_type: Optional[TicketOperationType] = None
    status: Optional[TicketStatus] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = Field(default=50, le=100)
    offset: int = Field(default=0, ge=0)


class TicketOperationRequest(BaseModel):
    """Request base para operaciones que generan tickets"""
    ruc: str = Field(..., description="RUC del contribuyente")
    priority: TicketPriority = Field(default=TicketPriority.NORMAL, description="Prioridad del ticket")
    notification_email: Optional[str] = Field(None, description="Email para notificaciones")


class TicketResponse(BaseModel):
    """Respuesta de ticket para API"""
    ticket_id: str
    operation_type: TicketOperationType
    status: TicketStatus
    progress_percentage: float
    status_message: str
    detailed_message: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    
    estimated_duration: Optional[int] = None
    elapsed_time: Optional[int] = None
    remaining_time: Optional[int] = None
    
    output_file_name: Optional[str] = None
    output_file_size: Optional[int] = None
    output_file_type: Optional[str] = None
    
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[List[str]] = None
    
    can_retry: bool = False
    is_expired: bool = False

    @classmethod
    def from_ticket(cls, ticket: SireTicket) -> "TicketResponse":
        """Crear respuesta desde modelo de ticket"""
        return cls(
            ticket_id=ticket.ticket_id,
            operation_type=ticket.operation_type,
            status=ticket.status,
            progress_percentage=ticket.progress_percentage,
            status_message=ticket.status_message,
            detailed_message=ticket.detailed_message,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            expires_at=ticket.expires_at,
            estimated_duration=ticket.estimated_duration,
            elapsed_time=ticket.get_elapsed_time(),
            remaining_time=ticket.get_remaining_time(),
            output_file_name=ticket.output_file_name,
            output_file_size=ticket.output_file_size,
            output_file_type=ticket.output_file_type,
            error_code=ticket.error_code,
            error_message=ticket.error_message,
            error_details=ticket.error_details,
            can_retry=ticket.can_retry(),
            is_expired=ticket.is_expired()
        )
