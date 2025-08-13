"""
Modelos de respuesta comunes SIRE
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class SireOperationStatus(str, Enum):
    """Estados de operación SIRE"""
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TicketStatus(str, Enum):
    """Estados de ticket SUNAT"""
    PENDIENTE = "PENDIENTE"
    PROCESANDO = "PROCESANDO"
    TERMINADO = "TERMINADO"
    ERROR = "ERROR"
    EXPIRADO = "EXPIRADO"


class SireApiResponse(BaseModel):
    """Respuesta base de API SIRE"""
    success: bool = Field(..., description="Indica si la operación fue exitosa")
    status: SireOperationStatus = Field(..., description="Estado de la operación")
    message: str = Field(..., description="Mensaje descriptivo")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Datos específicos de la respuesta
    data: Optional[Dict[str, Any]] = Field(None, description="Datos de respuesta")
    
    # Información de errores
    error_code: Optional[str] = Field(None, description="Código de error")
    error_details: Optional[List[str]] = Field(None, description="Detalles del error")
    
    # Metadatos
    request_id: Optional[str] = Field(None, description="ID de la solicitud")
    processing_time: Optional[float] = Field(None, description="Tiempo de procesamiento en segundos")


class TicketResponse(BaseModel):
    """Respuesta de ticket SUNAT"""
    ticket_id: str = Field(..., description="ID del ticket")
    status: TicketStatus = Field(..., description="Estado del ticket")
    descripcion: str = Field(..., description="Descripción del estado")
    
    # Información del proceso
    fecha_creacion: datetime = Field(..., description="Fecha de creación del ticket")
    fecha_actualizacion: datetime = Field(..., description="Última actualización")
    
    # Archivo generado (si está terminado)
    archivo_nombre: Optional[str] = Field(None, description="Nombre del archivo generado")
    archivo_url: Optional[str] = Field(None, description="URL de descarga")
    archivo_tamaño: Optional[int] = Field(None, description="Tamaño del archivo en bytes")
    
    # Progreso (si está en proceso)
    progreso_porcentaje: Optional[float] = Field(None, description="Porcentaje de progreso")
    progreso_mensaje: Optional[str] = Field(None, description="Mensaje de progreso")
    
    # Errores (si falló)
    error_mensaje: Optional[str] = Field(None, description="Mensaje de error")
    error_detalle: Optional[List[str]] = Field(None, description="Detalles del error")


class FileDownloadResponse(BaseModel):
    """Respuesta de descarga de archivo"""
    filename: str = Field(..., description="Nombre del archivo")
    content_type: str = Field(..., description="Tipo de contenido")
    file_size: int = Field(..., description="Tamaño del archivo")
    download_url: Optional[str] = Field(None, description="URL de descarga directa")
    
    # Metadatos del archivo
    created_at: datetime = Field(..., description="Fecha de creación")
    expires_at: Optional[datetime] = Field(None, description="Fecha de expiración")
    
    # Hash para verificación
    file_hash: Optional[str] = Field(None, description="Hash del archivo para verificación")


class SireStatusResponse(BaseModel):
    """Respuesta de estado SIRE"""
    ruc: str = Field(..., description="RUC del contribuyente")
    sire_activo: bool = Field(..., description="SIRE activo")
    credenciales_validas: bool = Field(..., description="Credenciales válidas")
    
    # Estado de autenticación
    sesion_activa: bool = Field(default=False)
    token_expira_en: Optional[int] = Field(None, description="Segundos hasta expiración del token")
    
    # Últimas operaciones
    ultima_operacion_rvie: Optional[datetime] = Field(None)
    ultima_operacion_rce: Optional[datetime] = Field(None)
    
    # Estado de servicios
    servicios_disponibles: List[str] = Field(default_factory=list)
    servicios_activos: List[str] = Field(default_factory=list)
    
    # Información adicional
    version_api: Optional[str] = Field(None, description="Versión de la API")
    servidor_region: Optional[str] = Field(None, description="Región del servidor")


class ValidationError(BaseModel):
    """Error de validación"""
    field: str = Field(..., description="Campo con error")
    message: str = Field(..., description="Mensaje de error")
    value: Optional[Any] = Field(None, description="Valor que causó el error")
    rule: Optional[str] = Field(None, description="Regla de validación violada")


class SireErrorResponse(BaseModel):
    """Respuesta de error SIRE"""
    success: bool = Field(default=False)
    status: SireOperationStatus = Field(default=SireOperationStatus.ERROR)
    error_code: str = Field(..., description="Código de error")
    error_message: str = Field(..., description="Mensaje de error")
    
    # Detalles del error
    error_type: str = Field(..., description="Tipo de error")
    error_details: Optional[List[str]] = Field(None, description="Detalles adicionales")
    validation_errors: Optional[List[ValidationError]] = Field(None, description="Errores de validación")
    
    # Información contextual
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = Field(None, description="ID de la solicitud")
    endpoint: Optional[str] = Field(None, description="Endpoint que causó el error")
    
    # Sugerencias para resolución
    suggested_action: Optional[str] = Field(None, description="Acción sugerida")
    documentation_url: Optional[str] = Field(None, description="URL de documentación")


class SirePaginatedResponse(BaseModel):
    """Respuesta paginada SIRE"""
    success: bool = Field(default=True)
    data: List[Dict[str, Any]] = Field(..., description="Datos de la página actual")
    
    # Información de paginación
    page: int = Field(..., description="Página actual")
    per_page: int = Field(..., description="Elementos por página")
    total_pages: int = Field(..., description="Total de páginas")
    total_items: int = Field(..., description="Total de elementos")
    
    # Enlaces de navegación
    has_previous: bool = Field(..., description="Tiene página anterior")
    has_next: bool = Field(..., description="Tiene página siguiente")
    previous_page: Optional[int] = Field(None, description="Número de página anterior")
    next_page: Optional[int] = Field(None, description="Número de página siguiente")
    
    # Metadatos
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time: Optional[float] = Field(None, description="Tiempo de procesamiento")
