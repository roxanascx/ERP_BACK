"""
Modelos de datos para consultas de documentos y tipos de cambio
"""

from datetime import datetime, date
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal

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


# ===========================================
# MODELOS PARA TIPOS DE CAMBIO
# ===========================================

class ExchangeRate(BaseModel):
    """Modelo para tipos de cambio diarios"""
    
    # Identificación única
    id: Optional[str] = Field(None, description="ID único del registro")
    
    # Información de la moneda
    fecha: date = Field(..., description="Fecha del tipo de cambio")
    moneda_origen: str = Field(default="USD", description="Código de moneda origen (ISO 4217)")
    moneda_destino: str = Field(default="PEN", description="Código de moneda destino (ISO 4217)")
    
    # Valores del tipo de cambio
    compra: Decimal = Field(..., description="Tipo de cambio para compra", ge=0)
    venta: Decimal = Field(..., description="Tipo de cambio para venta", ge=0)
    oficial: Optional[Decimal] = Field(None, description="Tipo de cambio oficial SUNAT", ge=0)
    
    # Metadatos
    fuente: str = Field(default="eApiPeru", description="Fuente de datos del tipo de cambio")
    es_oficial: bool = Field(default=True, description="Si es tipo de cambio oficial")
    es_activo: bool = Field(default=True, description="Si el registro está activo")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Fecha de creación")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Fecha de actualización")
    
    # Información adicional
    notas: Optional[str] = Field(None, description="Notas adicionales sobre el tipo de cambio")
    
    class Config:
        """Configuración del modelo"""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }
        schema_extra = {
            "example": {
                "fecha": "2025-08-24",
                "moneda_origen": "USD",
                "moneda_destino": "PEN",
                "compra": 3.5180,
                "venta": 3.5260,
                "oficial": 3.5220,
                "fuente": "eApiPeru",
                "es_oficial": True,
                "es_activo": True
            }
        }


class ExchangeRateData(BaseModel):
    """Datos básicos de tipo de cambio obtenidos de API externa"""
    fecha: date = Field(..., description="Fecha del tipo de cambio")
    compra: Decimal = Field(..., description="Tipo de cambio compra")
    venta: Decimal = Field(..., description="Tipo de cambio venta")
    sunat: Optional[Decimal] = Field(None, description="Tipo de cambio oficial SUNAT")
    moneda_origen: str = Field(default="USD", description="Moneda origen")
    moneda_destino: str = Field(default="PEN", description="Moneda destino")


class ExchangeRateConsultaResponse(ConsultaResponse):
    """Respuesta específica para consulta de tipo de cambio"""
    data: Optional[ExchangeRateData] = Field(None, description="Datos del tipo de cambio")
