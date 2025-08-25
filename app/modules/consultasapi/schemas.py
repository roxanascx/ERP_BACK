"""
Esquemas de request y response para las consultas API y tipos de cambio
"""

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator

class RucConsultaRequest(BaseModel):
    """Request para consulta de RUC"""
    ruc: str = Field(..., description="RUC de 11 dígitos", min_length=11, max_length=11)
    
    @validator('ruc')
    def validate_ruc(cls, v):
        if not v.isdigit():
            raise ValueError('RUC debe contener solo números')
        if len(v) != 11:
            raise ValueError('RUC debe tener exactamente 11 dígitos')
        # Validar que empiece con 10, 15, 17, 20
        if not v.startswith(('10', '15', '17', '20')):
            raise ValueError('RUC debe empezar con 10, 15, 17 o 20')
        return v

class DniConsultaRequest(BaseModel):
    """Request para consulta de DNI"""
    dni: str = Field(..., description="DNI de 8 dígitos", min_length=8, max_length=8)
    
    @validator('dni')
    def validate_dni(cls, v):
        if not v.isdigit():
            raise ValueError('DNI debe contener solo números')
        if len(v) != 8:
            raise ValueError('DNI debe tener exactamente 8 dígitos')
        return v

class ConsultaEstadoResponse(BaseModel):
    """Response para el estado de los servicios de consulta"""
    servicio_sunat: bool = Field(..., description="Estado del servicio SUNAT")
    servicio_reniec: bool = Field(..., description="Estado del servicio RENIEC")
    apis_disponibles: dict = Field(..., description="APIs disponibles por servicio")
    version: str = Field(..., description="Versión del módulo")
    endpoints_activos: list = Field(..., description="Endpoints activos")


# ===========================================
# SCHEMAS PARA TIPOS DE CAMBIO
# ===========================================

class ExchangeRateRequest(BaseModel):
    """Request para consulta de tipo de cambio"""
    fecha: date = Field(..., description="Fecha para consultar tipo de cambio")
    moneda_origen: Optional[str] = Field(default="USD", description="Moneda origen (ISO 4217)")
    moneda_destino: Optional[str] = Field(default="PEN", description="Moneda destino (ISO 4217)")
    
    @validator('fecha')
    def validate_fecha(cls, v):
        if v > date.today():
            raise ValueError('No se puede consultar tipo de cambio de fechas futuras')
        return v
    
    @validator('moneda_origen', 'moneda_destino')
    def validate_moneda(cls, v):
        if v and len(v) != 3:
            raise ValueError('Código de moneda debe tener 3 caracteres')
        return v.upper() if v else v


class ExchangeRateCreate(BaseModel):
    """Schema para crear tipo de cambio"""
    fecha: date = Field(..., description="Fecha del tipo de cambio")
    moneda_origen: str = Field(default="USD", description="Moneda origen")
    moneda_destino: str = Field(default="PEN", description="Moneda destino")
    compra: Decimal = Field(..., description="Tipo de cambio compra", ge=0)
    venta: Decimal = Field(..., description="Tipo de cambio venta", ge=0)
    oficial: Optional[Decimal] = Field(None, description="Tipo de cambio oficial", ge=0)
    fuente: str = Field(default="eApiPeru", description="Fuente de datos")
    es_oficial: bool = Field(default=True, description="Si es oficial")
    notas: Optional[str] = Field(None, description="Notas adicionales")
    
    @validator('venta')
    def validate_venta_mayor_compra(cls, v, values):
        if 'compra' in values and v < values['compra']:
            raise ValueError('Tipo de cambio venta debe ser mayor o igual al de compra')
        return v


class ExchangeRateUpdate(BaseModel):
    """Schema para actualizar tipo de cambio"""
    compra: Optional[Decimal] = Field(None, description="Tipo de cambio compra", ge=0)
    venta: Optional[Decimal] = Field(None, description="Tipo de cambio venta", ge=0)
    oficial: Optional[Decimal] = Field(None, description="Tipo de cambio oficial", ge=0)
    fuente: Optional[str] = Field(None, description="Fuente de datos")
    es_oficial: Optional[bool] = Field(None, description="Si es oficial")
    es_activo: Optional[bool] = Field(None, description="Si está activo")
    notas: Optional[str] = Field(None, description="Notas adicionales")


class ExchangeRateResponse(BaseModel):
    """Schema de respuesta para tipo de cambio"""
    id: str = Field(..., description="ID único")
    fecha: date = Field(..., description="Fecha")
    moneda_origen: str = Field(..., description="Moneda origen")
    moneda_destino: str = Field(..., description="Moneda destino")
    compra: Decimal = Field(..., description="Tipo de cambio compra")
    venta: Decimal = Field(..., description="Tipo de cambio venta")
    oficial: Optional[Decimal] = Field(None, description="Tipo de cambio oficial")
    fuente: str = Field(..., description="Fuente de datos")
    es_oficial: bool = Field(..., description="Si es oficial")
    es_activo: bool = Field(..., description="Si está activo")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")
    notas: Optional[str] = Field(None, description="Notas adicionales")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


class ExchangeRateQuery(BaseModel):
    """Schema para filtros de consulta de tipos de cambio"""
    fecha_desde: Optional[date] = Field(None, description="Fecha desde")
    fecha_hasta: Optional[date] = Field(None, description="Fecha hasta")
    moneda_origen: Optional[str] = Field(None, description="Filtrar por moneda origen")
    moneda_destino: Optional[str] = Field(None, description="Filtrar por moneda destino")
    fuente: Optional[str] = Field(None, description="Filtrar por fuente")
    es_oficial: Optional[bool] = Field(None, description="Filtrar por oficiales")
    es_activo: Optional[bool] = Field(None, description="Filtrar por activos")


class ExchangeRateListResponse(BaseModel):
    """Schema de respuesta para lista de tipos de cambio"""
    tipos_cambio: List[ExchangeRateResponse] = Field(..., description="Lista de tipos de cambio")
    total: int = Field(..., description="Total de registros")
    page: int = Field(..., description="Página actual")
    size: int = Field(..., description="Tamaño de página")
    total_pages: int = Field(..., description="Total de páginas")


class ExchangeRateCalculationRequest(BaseModel):
    """Schema para cálculo de conversión de moneda"""
    cantidad: Decimal = Field(..., description="Cantidad a convertir", gt=0)
    moneda_origen: str = Field(..., description="Moneda origen")
    moneda_destino: str = Field(..., description="Moneda destino")
    fecha: Optional[date] = Field(None, description="Fecha específica (por defecto hoy)")
    tipo_cambio: Optional[str] = Field(default="venta", description="Usar 'compra' o 'venta'")
    
    @validator('tipo_cambio')
    def validate_tipo_cambio(cls, v):
        if v not in ['compra', 'venta']:
            raise ValueError('tipo_cambio debe ser "compra" o "venta"')
        return v


class ExchangeRateCalculationResponse(BaseModel):
    """Schema de respuesta para cálculo de conversión"""
    cantidad_original: Decimal = Field(..., description="Cantidad original")
    moneda_origen: str = Field(..., description="Moneda origen")
    cantidad_convertida: Decimal = Field(..., description="Cantidad convertida")
    moneda_destino: str = Field(..., description="Moneda destino")
    tipo_cambio_usado: Decimal = Field(..., description="Tipo de cambio utilizado")
    fecha_tipo_cambio: date = Field(..., description="Fecha del tipo de cambio")
    tipo: str = Field(..., description="Tipo usado (compra/venta)")
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


class ActualizarTiposCambioRequest(BaseModel):
    """Schema para solicitud de actualización de tipos de cambio"""
    fecha_desde: Optional[date] = Field(None, description="Fecha desde (por defecto hoy)")
    fecha_hasta: Optional[date] = Field(None, description="Fecha hasta (por defecto hoy)")
    forzar_actualizacion: bool = Field(default=False, description="Forzar actualización de existentes")
    
    @validator('fecha_hasta')
    def validate_fecha_hasta(cls, v, values):
        if v and 'fecha_desde' in values and values['fecha_desde'] and v < values['fecha_desde']:
            raise ValueError('fecha_hasta debe ser mayor o igual a fecha_desde')
        return v


class ActualizarTiposCambioResponse(BaseModel):
    """Schema de respuesta para actualización de tipos de cambio"""
    success: bool = Field(..., description="Si la actualización fue exitosa")
    message: str = Field(..., description="Mensaje descriptivo")
    registros_procesados: int = Field(..., description="Registros procesados")
    registros_creados: int = Field(..., description="Registros creados")
    registros_actualizados: int = Field(..., description="Registros actualizados")
    registros_error: int = Field(..., description="Registros con error")
    fecha_desde: date = Field(..., description="Fecha desde procesada")
    fecha_hasta: date = Field(..., description="Fecha hasta procesada")
    detalles: List[str] = Field(default_factory=list, description="Detalles del proceso")
