"""
Schemas Pydantic para RVIE - Registro de Ventas e Ingresos Electrónico
"""

from datetime import datetime, date
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from enum import Enum


class RvieConsultarInconsistenciasRequest(BaseModel):
    """Request para consultar inconsistencias RVIE"""
    ruc: str = Field(..., description="RUC del contribuyente", min_length=11, max_length=11)
    periodo: str = Field(..., description="Periodo YYYYMM", pattern="^\\d{6}$")
    fase: str = Field(default="propuesta", description="Fase del proceso", pattern="^(propuesta|preliminar)$")
    
    @validator('ruc')
    def validate_ruc(cls, v):
        if not v.isdigit():
            raise ValueError('RUC debe contener solo dígitos')
        return v
from typing import List, Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, validator


class RvieDescargarPropuestaRequest(BaseModel):
    """Request para descargar propuesta RVIE"""
    ruc: str = Field(..., description="RUC del contribuyente", min_length=11, max_length=11)
    periodo: str = Field(..., description="Periodo YYYYMM", min_length=6, max_length=6)
    
    @validator('ruc')
    def validate_ruc(cls, v):
        if not v.isdigit():
            raise ValueError('RUC debe contener solo dígitos')
        return v
    
    @validator('periodo')
    def validate_periodo(cls, v):
        if not v.isdigit():
            raise ValueError('Periodo debe contener solo dígitos')
        try:
            year = int(v[:4])
            month = int(v[4:])
            if year < 2000 or year > 2030 or month < 1 or month > 12:
                raise ValueError('Periodo fuera de rango válido')
        except:
            raise ValueError('Formato de periodo inválido')
        return v


class RvieAceptarPropuestaRequest(BaseModel):
    """Request para aceptar propuesta RVIE"""
    ruc: str = Field(..., description="RUC del contribuyente", min_length=11, max_length=11)
    periodo: str = Field(..., description="Periodo YYYYMM", min_length=6, max_length=6)
    confirmacion: bool = Field(default=True, description="Confirmación de aceptación")
    
    @validator('ruc')
    def validate_ruc(cls, v):
        if not v.isdigit():
            raise ValueError('RUC debe contener solo dígitos')
        return v


class RvieReemplazarPropuestaRequest(BaseModel):
    """Request para reemplazar propuesta RVIE"""
    ruc: str = Field(..., description="RUC del contribuyente", min_length=11, max_length=11)
    periodo: str = Field(..., description="Periodo YYYYMM", min_length=6, max_length=6)
    archivo_contenido: str = Field(..., description="Contenido del archivo TXT en base64")
    nombre_archivo: Optional[str] = Field(None, description="Nombre del archivo original")
    
    @validator('ruc')
    def validate_ruc(cls, v):
        if not v.isdigit():
            raise ValueError('RUC debe contener solo dígitos')
        return v


class RvieComprobanteRequest(BaseModel):
    """Request de comprobante RVIE"""
    correlativo: str = Field(..., description="Número correlativo")
    fecha_emision: date = Field(..., description="Fecha de emisión")
    tipo_comprobante: str = Field(..., description="Tipo de comprobante")
    serie: str = Field(..., description="Serie del comprobante")
    numero: str = Field(..., description="Número del comprobante")
    
    # Datos del cliente
    tipo_documento_cliente: str = Field(..., description="Tipo documento cliente")
    numero_documento_cliente: str = Field(..., description="Número documento cliente")
    razon_social_cliente: str = Field(..., description="Razón social cliente")
    
    # Montos
    base_imponible: Decimal = Field(..., description="Base imponible", ge=0)
    igv: Decimal = Field(..., description="IGV", ge=0)
    otros_tributos: Decimal = Field(default=Decimal("0.00"), description="Otros tributos", ge=0)
    importe_total: Decimal = Field(..., description="Importe total", ge=0)
    
    # Datos adicionales
    moneda: str = Field(default="PEN", description="Código de moneda")
    tipo_cambio: Optional[Decimal] = Field(None, description="Tipo de cambio", gt=0)
    observaciones: Optional[str] = Field(None, description="Observaciones")


class RvieRegistrarPreliminarRequest(BaseModel):
    """Request para registrar preliminar RVIE"""
    ruc: str = Field(..., description="RUC del contribuyente", min_length=11, max_length=11)
    periodo: str = Field(..., description="Periodo YYYYMM", min_length=6, max_length=6)
    comprobantes: List[RvieComprobanteRequest] = Field(..., description="Lista de comprobantes")
    
    @validator('ruc')
    def validate_ruc(cls, v):
        if not v.isdigit():
            raise ValueError('RUC debe contener solo dígitos')
        return v
    
    @validator('comprobantes')
    def validate_comprobantes(cls, v):
        if not v:
            raise ValueError('Debe incluir al menos un comprobante')
        if len(v) > 10000:  # Límite razonable
            raise ValueError('Demasiados comprobantes en una sola operación')
        return v


class RvieConsultarInconsistenciasRequest(BaseModel):
    """Request para consultar inconsistencias RVIE"""
    ruc: str = Field(..., description="RUC del contribuyente", min_length=11, max_length=11)
    periodo: str = Field(..., description="Periodo YYYYMM", min_length=6, max_length=6)
    fase: str = Field(default="propuesta", description="Fase del proceso", pattern="^(propuesta|preliminar)$")
    
    @validator('ruc')
    def validate_ruc(cls, v):
        if not v.isdigit():
            raise ValueError('RUC debe contener solo dígitos')
        return v


class RvieGenerarTicketRequest(BaseModel):
    """Request para generar ticket RVIE"""
    ruc: str = Field(..., description="RUC del contribuyente", min_length=11, max_length=11)
    periodo: str = Field(..., description="Periodo YYYYMM", min_length=6, max_length=6)
    operacion: str = Field(..., description="Tipo de operación", pattern="^(descargar-propuesta|aceptar-propuesta|reemplazar-propuesta)$")
    
    @validator('ruc')
    def validate_ruc(cls, v):
        if not v.isdigit():
            raise ValueError('RUC debe contener solo dígitos')
        return v
    
    @validator('periodo')
    def validate_periodo(cls, v):
        if not v.isdigit():
            raise ValueError('Periodo debe contener solo dígitos')
        try:
            year = int(v[:4])
            month = int(v[4:])
            if year < 2000 or year > 2030 or month < 1 or month > 12:
                raise ValueError('Periodo fuera de rango válido')
        except:
            raise ValueError('Formato de periodo inválido')
        return v


class RvieConsultarTicketRequest(BaseModel):
    """Request para consultar estado de ticket RVIE"""
    ruc: str = Field(..., description="RUC del contribuyente", min_length=11, max_length=11)
    ticket_id: str = Field(..., description="ID del ticket", min_length=1)
    
    @validator('ruc')
    def validate_ruc(cls, v):
        if not v.isdigit():
            raise ValueError('RUC debe contener solo dígitos')
        return v


class RvieDescargarArchivoRequest(BaseModel):
    """Request para descargar archivo de ticket RVIE"""
    ruc: str = Field(..., description="RUC del contribuyente", min_length=11, max_length=11)
    ticket_id: str = Field(..., description="ID del ticket", min_length=1)
    
    @validator('ruc')
    def validate_ruc(cls, v):
        if not v.isdigit():
            raise ValueError('RUC debe contener solo dígitos')
        return v


# Responses

class RvieComprobanteResponse(BaseModel):
    """Response de comprobante RVIE"""
    correlativo: str
    fecha_emision: date
    tipo_comprobante: str
    serie: str
    numero: str
    razon_social_cliente: str
    base_imponible: Decimal
    igv: Decimal
    importe_total: Decimal
    estado: str = "PROCESADO"


class RviePropuestaResponse(BaseModel):
    """Response de propuesta RVIE"""
    ruc: str
    periodo: str
    estado: str
    fecha_generacion: datetime
    cantidad_comprobantes: int
    total_base_imponible: Decimal
    total_igv: Decimal
    total_importe: Decimal
    comprobantes: List[RvieComprobanteResponse] = Field(default_factory=list)
    ticket_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "ruc": "20123456789",
                "periodo": "202408",
                "estado": "PROPUESTA",
                "fecha_generacion": "2024-08-13T15:30:00",
                "cantidad_comprobantes": 150,
                "total_base_imponible": 125000.00,
                "total_igv": 22500.00,
                "total_importe": 147500.00,
                "comprobantes": [],
                "ticket_id": "TKT123456789"
            }
        }


class RvieProcesoResponse(BaseModel):
    """Response de proceso RVIE"""
    ruc: str
    periodo: str
    operacion: str
    estado: str
    exitoso: bool
    mensaje: str
    ticket_id: Optional[str] = None
    comprobantes_procesados: int = 0
    errores: List[str] = Field(default_factory=list)
    fecha_proceso: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "ruc": "20123456789",
                "periodo": "202408",
                "operacion": "ACEPTAR_PROPUESTA",
                "estado": "FINALIZADO",
                "exitoso": True,
                "mensaje": "Propuesta aceptada exitosamente",
                "ticket_id": "TKT123456789",
                "comprobantes_procesados": 150,
                "errores": [],
                "fecha_proceso": "2024-08-13T15:30:00"
            }
        }


class RvieInconsistenciaResponse(BaseModel):
    """Response de inconsistencia RVIE"""
    linea: int
    campo: str
    valor_encontrado: str
    valor_esperado: str
    descripcion_error: str
    tipo_error: str
    severidad: str


class RvieInconsistenciasResponse(BaseModel):
    """Response de lista de inconsistencias RVIE"""
    ruc: str
    periodo: str
    fase: str
    cantidad_inconsistencias: int
    inconsistencias: List[RvieInconsistenciaResponse]
    fecha_consulta: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "ruc": "20123456789",
                "periodo": "202408",
                "fase": "propuesta",
                "cantidad_inconsistencias": 5,
                "inconsistencias": [
                    {
                        "linea": 1,
                        "campo": "base_imponible",
                        "valor_encontrado": "1000.00",
                        "valor_esperado": "1180.00",
                        "descripcion_error": "Base imponible no coincide",
                        "tipo_error": "MONTO",
                        "severidad": "ERROR"
                    }
                ],
                "fecha_consulta": "2024-08-13T15:30:00"
            }
        }


class RvieTicketResponse(BaseModel):
    """Response de estado de ticket RVIE"""
    ticket_id: str
    estado: str
    descripcion: str
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    archivo_nombre: Optional[str] = None
    archivo_disponible: bool = False
    progreso_porcentaje: Optional[float] = None
    error_mensaje: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": "TKT123456789",
                "estado": "TERMINADO",
                "descripcion": "Proceso completado exitosamente",
                "fecha_creacion": "2024-08-13T15:30:00",
                "fecha_actualizacion": "2024-08-13T15:35:00",
                "archivo_nombre": "rvie_202408.zip",
                "archivo_disponible": True,
                "progreso_porcentaje": 100.0,
                "error_mensaje": None
            }
        }


class RvieArchivoResponse(BaseModel):
    """Response de archivo descargado RVIE"""
    ticket_id: str
    nombre_archivo: str
    tamaño_archivo: int
    tipo_contenido: str
    fecha_generacion: datetime
    url_descarga: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": "TKT123456789",
                "nombre_archivo": "rvie_202408.zip",
                "tamaño_archivo": 524288,
                "tipo_contenido": "application/zip",
                "fecha_generacion": "2024-08-13T15:35:00",
                "url_descarga": "/api/sire/rvie/download/TKT123456789"
            }
        }


class RvieResumenResponse(BaseModel):
    """Response de resumen RVIE"""
    ruc: str
    periodo: str
    total_comprobantes: int
    total_base_imponible: Decimal
    total_igv: Decimal
    total_importe: Decimal
    estado_actual: str
    fecha_ultimo_proceso: Optional[datetime] = None
    resumen_por_tipo: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    archivos_disponibles: List[str] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "ruc": "20123456789",
                "periodo": "202408",
                "total_comprobantes": 150,
                "total_base_imponible": 125000.00,
                "total_igv": 22500.00,
                "total_importe": 147500.00,
                "estado_actual": "FINALIZADO",
                "fecha_ultimo_proceso": "2024-08-13T15:30:00",
                "resumen_por_tipo": {
                    "01": {"cantidad": 100, "importe": 100000.00},
                    "03": {"cantidad": 50, "importe": 47500.00}
                },
                "archivos_disponibles": ["propuesta.txt", "inconsistencias.txt"]
            }
        }
