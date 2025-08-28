"""
Esquemas Pydantic para el Registro de Compras (PLE 080000) - FIXED.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


# Enums para valores específicos
class TipoComprobanteCompra(str, Enum):
    """Tipos de comprobante de compra válidos."""
    FACTURA = "01"
    BOLETA = "03"
    NOTA_CREDITO = "07"
    NOTA_DEBITO = "08"
    GUIA_REMISION = "09"
    RECIBO_SERVICIOS = "12"
    DOCUMENTO_EXTERIOR = "91"


class TipoDocumentoIdentidad(str, Enum):
    """Tipos de documento de identidad."""
    DNI = "1"
    EXTRANJERIA = "4"
    RUC = "6"
    PASAPORTE = "7"
    CEDULA_DIPLOMATICA = "A"


class EstadoOperacion(str, Enum):
    """Estados de operación."""
    VIGENTE = "1"
    ANULADO = "2"
    MODIFICADO = "9"


class RegistroCompra(BaseModel):
    """Schema base para registro de compras."""
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[str] = Field(None, description="ID único del registro")
    empresa_id: str = Field(..., description="ID de la empresa")
    periodo: str = Field(..., min_length=6, max_length=6, description="Periodo AAAAMM")
    fecha_comprobante: date = Field(..., description="Fecha del comprobante de pago")
    tipo_comprobante: str = Field(..., description="Tipo de comprobante de pago")
    serie_comprobante: Optional[str] = Field(None, description="Serie del comprobante")
    numero_comprobante: str = Field(..., description="Número del comprobante")
    fecha_vencimiento: Optional[date] = Field(None, description="Fecha de vencimiento")
    tipo_documento_proveedor: str = Field(..., description="Tipo de documento del proveedor")
    numero_documento_proveedor: str = Field(..., description="Número de documento del proveedor")
    razon_social_proveedor: str = Field(..., description="Razón social del proveedor")
    base_imponible_gravada: Decimal = Field(..., ge=0, description="Base imponible gravada")
    igv: Decimal = Field(..., ge=0, description="IGV")
    base_imponible_exonerada: Decimal = Field(default=Decimal("0.00"), ge=0, description="Base imponible exonerada")
    base_imponible_inafecta: Decimal = Field(default=Decimal("0.00"), ge=0, description="Base imponible inafecta")
    isc: Decimal = Field(default=Decimal("0.00"), ge=0, description="ISC")
    otros_tributos: Decimal = Field(default=Decimal("0.00"), ge=0, description="Otros tributos")
    importe_total: Decimal = Field(..., gt=0, description="Importe total del comprobante")
    moneda: str = Field(default="PEN", description="Código de moneda")
    tipo_cambio: Decimal = Field(default=Decimal("1.0000"), gt=0, description="Tipo de cambio")
    fecha_emision_documento_modificado: Optional[date] = Field(None, description="Fecha de emisión del documento modificado")
    tipo_comprobante_modificado: Optional[str] = Field(None, description="Tipo de comprobante modificado")
    serie_comprobante_modificado: Optional[str] = Field(None, description="Serie del comprobante modificado")
    numero_comprobante_modificado: Optional[str] = Field(None, description="Número del comprobante modificado")
    clasificacion_bienes_servicios: str = Field(..., description="Clasificación de bienes y servicios")
    estado_operacion: str = Field(default="1", description="Estado de la operación")
    created_at: Optional[datetime] = Field(None, description="Fecha de creación")
    updated_at: Optional[datetime] = Field(None, description="Fecha de actualización")


class RegistroCompraRequest(BaseModel):
    """Schema para request de registro de compras."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    empresa_id: str = Field(..., description="ID de la empresa")
    periodo: str = Field(..., min_length=6, max_length=6, description="Periodo AAAAMM")
    fecha_comprobante: date = Field(..., description="Fecha del comprobante de pago")
    tipo_comprobante: str = Field(..., description="Tipo de comprobante de pago")
    serie_comprobante: Optional[str] = Field(None, description="Serie del comprobante")
    numero_comprobante: str = Field(..., description="Número del comprobante")
    fecha_vencimiento: Optional[date] = Field(None, description="Fecha de vencimiento")
    tipo_documento_proveedor: str = Field(..., description="Tipo de documento del proveedor")
    numero_documento_proveedor: str = Field(..., description="Número de documento del proveedor")
    razon_social_proveedor: str = Field(..., description="Razón social del proveedor")
    base_imponible_gravada: Decimal = Field(..., ge=0, description="Base imponible gravada")
    igv: Decimal = Field(..., ge=0, description="IGV")
    base_imponible_exonerada: Decimal = Field(default=Decimal("0.00"), ge=0)
    base_imponible_inafecta: Decimal = Field(default=Decimal("0.00"), ge=0)
    isc: Decimal = Field(default=Decimal("0.00"), ge=0)
    otros_tributos: Decimal = Field(default=Decimal("0.00"), ge=0)
    importe_total: Decimal = Field(..., gt=0, description="Importe total del comprobante")
    moneda: str = Field(default="PEN", description="Código de moneda")
    tipo_cambio: Decimal = Field(default=Decimal("1.0000"), gt=0)
    clasificacion_bienes_servicios: str = Field(..., description="Clasificación de bienes y servicios")
    estado_operacion: str = Field(default="1", description="Estado de la operación")


class RegistroCompraCreate(BaseModel):
    """Schema para crear un nuevo registro de compras."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    empresa_id: str = Field(..., description="ID de la empresa")
    periodo: str = Field(..., min_length=6, max_length=6, description="Periodo AAAAMM")
    fecha_comprobante: date = Field(..., description="Fecha del comprobante de pago")
    tipo_comprobante: str = Field(..., description="Tipo de comprobante de pago")
    serie_comprobante: Optional[str] = Field(None, description="Serie del comprobante")
    numero_comprobante: str = Field(..., description="Número del comprobante")
    fecha_vencimiento: Optional[date] = Field(None, description="Fecha de vencimiento")
    tipo_documento_proveedor: str = Field(..., description="Tipo de documento del proveedor")
    numero_documento_proveedor: str = Field(..., description="Número de documento del proveedor")
    razon_social_proveedor: str = Field(..., description="Razón social del proveedor")
    base_imponible_gravada: Decimal = Field(..., ge=0, description="Base imponible gravada")
    igv: Decimal = Field(..., ge=0, description="IGV")
    base_imponible_exonerada: Decimal = Field(default=Decimal("0.00"), ge=0)
    base_imponible_inafecta: Decimal = Field(default=Decimal("0.00"), ge=0)
    isc: Decimal = Field(default=Decimal("0.00"), ge=0)
    otros_tributos: Decimal = Field(default=Decimal("0.00"), ge=0)
    importe_total: Decimal = Field(..., gt=0, description="Importe total del comprobante")
    moneda: str = Field(default="PEN", description="Código de moneda")
    tipo_cambio: Decimal = Field(default=Decimal("1.0000"), gt=0)
    clasificacion_bienes_servicios: str = Field(..., description="Clasificación de bienes y servicios")
    estado_operacion: str = Field(default="1", description="Estado de la operación")


class RegistroCompraUpdate(BaseModel):
    """Schema para actualizar un registro de compras."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    fecha_comprobante: Optional[date] = None
    tipo_comprobante: Optional[str] = None
    serie_comprobante: Optional[str] = None
    numero_comprobante: Optional[str] = None
    fecha_vencimiento: Optional[date] = None
    tipo_documento_proveedor: Optional[str] = None
    numero_documento_proveedor: Optional[str] = None
    razon_social_proveedor: Optional[str] = None
    base_imponible_gravada: Optional[Decimal] = None
    igv: Optional[Decimal] = None
    base_imponible_exonerada: Optional[Decimal] = None
    base_imponible_inafecta: Optional[Decimal] = None
    isc: Optional[Decimal] = None
    otros_tributos: Optional[Decimal] = None
    importe_total: Optional[Decimal] = None
    moneda: Optional[str] = None
    tipo_cambio: Optional[Decimal] = None
    clasificacion_bienes_servicios: Optional[str] = None
    estado_operacion: Optional[str] = None


class RegistroCompraResponse(BaseModel):
    """Schema para respuesta de registro de compras."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    empresa_id: str
    periodo: str
    fecha_comprobante: date
    tipo_comprobante: str
    serie_comprobante: Optional[str] = None
    numero_comprobante: str
    fecha_vencimiento: Optional[date] = None
    tipo_documento_proveedor: str
    numero_documento_proveedor: str
    razon_social_proveedor: str
    base_imponible_gravada: Decimal
    igv: Decimal
    base_imponible_exonerada: Optional[Decimal] = Decimal('0.00')
    base_imponible_inafecta: Optional[Decimal] = Decimal('0.00')
    isc: Optional[Decimal] = Decimal('0.00')
    otros_tributos: Optional[Decimal] = Decimal('0.00')
    importe_total: Decimal
    moneda: Optional[str] = "PEN"
    tipo_cambio: Optional[Decimal] = Decimal('1.00')
    clasificacion_bienes_servicios: Optional[str] = "1"
    estado_operacion: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RegistroCompraFilter(BaseModel):
    """Schema para filtros de búsqueda."""
    model_config = ConfigDict()
    
    periodo: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    tipo_comprobante: Optional[str] = None
    numero_documento_proveedor: Optional[str] = None
    razon_social_proveedor: Optional[str] = None
    monto_minimo: Optional[Decimal] = None
    monto_maximo: Optional[Decimal] = None


class PLEComprasMetadata(BaseModel):
    """Schema para metadatos de archivo PLE."""
    model_config = ConfigDict()
    
    empresa_id: str
    periodo: str
    total_registros: int
    fecha_generacion: datetime
    version_formato: str = "27.0"


class RegistroCompraResumen(BaseModel):
    """Schema para resumen de registros."""
    model_config = ConfigDict()
    
    total_registros: int
    total_base_imponible: Decimal
    total_igv: Decimal
    total_importe: Decimal


class ValidationResult(BaseModel):
    """Schema para resultado de validación."""
    model_config = ConfigDict()
    
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class PLEFileInfo(BaseModel):
    """Schema para información de archivo PLE."""
    model_config = ConfigDict()
    
    nombre: str
    tamaño: int
    fecha_creacion: datetime
    hash_md5: str
    ruta_archivo: str


class PLEComprasExportOptions(BaseModel):
    """Schema para opciones de exportación PLE."""
    model_config = ConfigDict()
    
    formato: str = "txt"
    incluir_cabecera: bool = True
    separador: str = "|"
    codificacion: str = "utf-8"


class PLEComprasExportResult(BaseModel):
    """Schema para resultado de exportación PLE."""
    model_config = ConfigDict()
    
    archivo_generado: str
    total_registros: int
    tamaño_archivo: int
    fecha_generacion: datetime
    hash_md5: str
