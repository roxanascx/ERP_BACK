"""
Modelos específicos para tickets según Manual SUNAT SIRE v25
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class SunatTicketStatus(str, Enum):
    """Estados oficiales de tickets según SUNAT"""
    PENDIENTE = "0"      # Ticket en cola de procesamiento
    PROCESANDO = "1"     # Ticket en proceso de ejecución  
    TERMINADO = "2"      # Ticket completado exitosamente
    ERROR = "3"          # Ticket falló con error
    CANCELADO = "4"      # Ticket cancelado


class SunatOperationType(str, Enum):
    """Tipos de operación que generan tickets en SUNAT"""
    # RVIE - Registro de Ventas e Ingresos
    RVIE_DESCARGAR_PROPUESTA = "RVIE_PROPUESTA_DESCARGA"
    RVIE_ACEPTAR_PROPUESTA = "RVIE_PROPUESTA_ACEPTAR"
    RVIE_REEMPLAZAR_PROPUESTA = "RVIE_PROPUESTA_REEMPLAZAR"
    RVIE_REGISTRAR_PRELIMINAR = "RVIE_PRELIMINAR_REGISTRAR"
    RVIE_DESCARGAR_INCONSISTENCIAS = "RVIE_INCONSISTENCIAS_DESCARGA"
    
    # RCE - Registro de Compras Electrónico  
    RCE_DESCARGAR_PROPUESTA = "RCE_PROPUESTA_DESCARGA"
    RCE_RESUMEN_CONSOLIDADO = "RCE_RESUMEN_CONSOLIDADO"
    RCE_INCONSISTENCIAS_MONTOS = "RCE_INCONSISTENCIAS_MONTOS"
    RCE_INCONSISTENCIAS_COMPROBANTES = "RCE_INCONSISTENCIAS_COMPROBANTES"


class SunatTicketRequest(BaseModel):
    """Request para crear ticket en SUNAT según manual"""
    ruc: str = Field(..., description="RUC del contribuyente", min_length=11, max_length=11)
    periodo: str = Field(..., description="Período YYYYMM", min_length=6, max_length=6)
    operacion: SunatOperationType = Field(..., description="Tipo de operación")
    parametros: Dict[str, Any] = Field(default_factory=dict, description="Parámetros específicos")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ruc": "20100070970",
                "periodo": "202412", 
                "operacion": "RVIE_PROPUESTA_DESCARGA",
                "parametros": {
                    "incluir_detalle": True,
                    "formato": "TXT"
                }
            }
        }


class SunatTicketResponse(BaseModel):
    """Respuesta de SUNAT al crear ticket"""
    ticket: str = Field(..., description="ID del ticket generado por SUNAT")
    fecha_generacion: datetime = Field(..., description="Fecha de generación del ticket")
    estado: SunatTicketStatus = Field(..., description="Estado inicial del ticket")
    mensaje: str = Field(default="", description="Mensaje descriptivo")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticket": "TKT20241214120000123456",
                "fecha_generacion": "2024-12-14T12:00:00Z",
                "estado": "0",
                "mensaje": "Ticket creado exitosamente"
            }
        }


class SunatTicketStatusResponse(BaseModel):
    """Respuesta de consulta de estado de ticket SUNAT"""
    ticket: str = Field(..., description="ID del ticket")
    estado: SunatTicketStatus = Field(..., description="Estado actual")
    fecha_actualizacion: datetime = Field(..., description="Última actualización")
    porcentaje_avance: Optional[float] = Field(None, description="Porcentaje de avance (0-100)")
    mensaje: str = Field(default="", description="Mensaje del estado")
    
    # Información del archivo (cuando estado = TERMINADO)
    nombre_archivo: Optional[str] = Field(None, description="Nombre del archivo generado")
    tamaño_archivo: Optional[int] = Field(None, description="Tamaño en bytes")
    hash_archivo: Optional[str] = Field(None, description="Hash MD5 del archivo")
    
    # Información de error (cuando estado = ERROR)
    codigo_error: Optional[str] = Field(None, description="Código de error SUNAT")
    detalle_error: Optional[str] = Field(None, description="Detalle del error")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticket": "TKT20241214120000123456",
                "estado": "2",
                "fecha_actualizacion": "2024-12-14T12:05:00Z",
                "porcentaje_avance": 100.0,
                "mensaje": "Archivo generado exitosamente",
                "nombre_archivo": "RVIE_202412_20100070970.zip",
                "tamaño_archivo": 1024000,
                "hash_archivo": "d41d8cd98f00b204e9800998ecf8427e"
            }
        }


class SunatFileDownloadRequest(BaseModel):
    """Request para descargar archivo generado por ticket"""
    ticket: str = Field(..., description="ID del ticket")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticket": "TKT20241214120000123456"
            }
        }


class SunatErrorResponse(BaseModel):
    """Respuesta de error estándar de SUNAT"""
    codigo: str = Field(..., description="Código de error")
    mensaje: str = Field(..., description="Mensaje de error")
    detalle: Optional[str] = Field(None, description="Detalle adicional del error")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp del error")
    
    class Config:
        json_schema_extra = {
            "example": {
                "codigo": "SIRE001",
                "mensaje": "RUC no autorizado para SIRE",
                "detalle": "El RUC 20100070970 no tiene autorización para usar servicios SIRE",
                "timestamp": "2024-12-14T12:00:00Z"
            }
        }


# Mapeo de códigos de error comunes de SUNAT
SUNAT_ERROR_CODES = {
    "SIRE001": "RUC no autorizado para SIRE",
    "SIRE002": "Período no válido",
    "SIRE003": "Token de autenticación inválido",
    "SIRE004": "Ticket no encontrado",
    "SIRE005": "Archivo no disponible",
    "SIRE006": "Operación no permitida",
    "SIRE007": "Parámetros inválidos",
    "SIRE008": "Límite de requests excedido",
    "SIRE009": "Servicio temporalmente no disponible",
    "SIRE010": "Error interno del servidor"
}


def map_sunat_error(codigo: str) -> str:
    """Mapear código de error SUNAT a mensaje descriptivo"""
    return SUNAT_ERROR_CODES.get(codigo, f"Error desconocido: {codigo}")
