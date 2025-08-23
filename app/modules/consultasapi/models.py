"""
Modelos de datos para consultas de documentos
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class RucData(BaseModel):
    """Datos de empresa obtenidos de SUNAT"""
    ruc: str = Field(..., description="RUC de 11 dígitos")
    razon_social: str = Field(..., description="Razón social de la empresa")
    nombre_comercial: Optional[str] = Field(None, description="Nombre comercial")
    estado: str = Field(..., description="Estado del contribuyente")
    tipo_empresa: Optional[str] = Field(None, description="Tipo de empresa")
    direccion: Optional[str] = Field(None, description="Dirección fiscal")
    ubigeo: Optional[str] = Field(None, description="Código ubigeo")
    departamento: Optional[str] = Field(None, description="Departamento")
    provincia: Optional[str] = Field(None, description="Provincia")
    distrito: Optional[str] = Field(None, description="Distrito")
    fecha_inscripcion: Optional[str] = Field(None, description="Fecha de inscripción")
    actividad_economica: Optional[str] = Field(None, description="Actividad económica")
    sistema_contabilidad: Optional[str] = Field(None, description="Sistema de contabilidad")
    tipo_facturacion: Optional[str] = Field(None, description="Tipo de facturación")
    comercio_exterior: Optional[str] = Field(None, description="Comercio exterior")
    telefono: Optional[str] = Field(None, description="Teléfono")
    email: Optional[str] = Field(None, description="Email")
    representante_legal: Optional[str] = Field(None, description="Representante legal")
    trabajadores: Optional[int] = Field(None, description="Número de trabajadores")

class DniData(BaseModel):
    """Datos de persona obtenidos de RENIEC"""
    dni: str = Field(..., description="DNI de 8 dígitos")
    nombres: str = Field(..., description="Nombres de la persona")
    apellido_paterno: str = Field(..., description="Apellido paterno")
    apellido_materno: str = Field(..., description="Apellido materno")
    apellidos: str = Field(..., description="Apellidos completos")
    fecha_nacimiento: Optional[str] = Field(None, description="Fecha de nacimiento")
    estado_civil: Optional[str] = Field(None, description="Estado civil")
    ubigeo: Optional[str] = Field(None, description="Código ubigeo")
    direccion: Optional[str] = Field(None, description="Dirección")
    restricciones: Optional[str] = Field(None, description="Restricciones")

class ConsultaResponse(BaseModel):
    """Respuesta genérica para consultas"""
    success: bool = Field(..., description="Si la consulta fue exitosa")
    message: str = Field(..., description="Mensaje descriptivo")
    data: Optional[Dict[str, Any]] = Field(None, description="Datos obtenidos")
    fuente: Optional[str] = Field(None, description="Fuente de los datos")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp de la consulta")

class RucConsultaResponse(ConsultaResponse):
    """Respuesta específica para consulta RUC"""
    data: Optional[RucData] = Field(None, description="Datos del RUC")

class DniConsultaResponse(ConsultaResponse):
    """Respuesta específica para consulta DNI"""
    data: Optional[DniData] = Field(None, description="Datos del DNI")
