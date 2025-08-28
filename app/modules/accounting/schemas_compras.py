"""
Schemas Pydantic para Registro de Compras PLE 080000
===================================================

Esquemas de validación para el Registro de Compras según especificaciones
SUNAT PLE 080000. Incluye validaciones específicas para IGV, proveedores
y todos los campos obligatorios de los 32 campos oficiales.

Basado en:
- PLE_SUNAT_DOCUMENTACION_COMPLETA.md
- Resolución de Superintendencia N° 286-2009/SUNAT

Estructura PLE 080000: 32 campos obligatorios
Autor: Sistema ERP - FASE 2.1
Fecha: Agosto 2025
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP


class TipoDocumentoProveedor(str, Enum):
    """Tipos de documento de identidad del proveedor según SUNAT"""
    SIN_DOCUMENTO = "0"
    DNI = "1"
    CARNET_EXTRANJERIA = "4"
    RUC = "6"
    PASAPORTE = "7"
    CEDULA_DIPLOMATICA = "A"


class TipoComprobantePago(str, Enum):
    """Tipos de comprobante de pago según SUNAT"""
    FACTURA = "01"
    BOLETA = "03"
    NOTA_CREDITO = "07"
    NOTA_DEBITO = "08"
    GUIA_REMISION = "09"
    RECIBO_HONORARIOS = "12"
    DOCUMENTO_BANCO = "13"
    RECIBO_SERVICIOS_PUBLICOS = "14"
    BOLETO_AEREO = "15"
    BOLETO_VIAJE_TERRESTRE = "16"
    DOCUMENTO_IGLESIA = "17"
    DOCUMENTO_AFP = "18"
    BOLETO_ESPECTACULO = "19"
    COMPROBANTE_RETENCION = "20"
    CONOCIMIENTO_EMBARQUE = "21"
    COMPROBANTE_SCOP = "22"


class EstadoOperacion(str, Enum):
    """Estados de operación según SUNAT"""
    ACTIVO = "1"
    ANULADO = "9"


class RegistroCompraBase(BaseModel):
    """Schema base para registro de compras PLE 080000"""
    
    # ===== DATOS BÁSICOS DEL COMPROBANTE =====
    periodo: str = Field(
        ..., 
        pattern=r"^\d{6}$", 
        description="Período AAAAMM"
    )
    fecha_emision: str = Field(
        ..., 
        pattern=r"^\d{2}/\d{2}/\d{4}$",
        description="Fecha emisión DD/MM/YYYY"
    )
    fecha_vencimiento: Optional[str] = Field(
        None,
        pattern=r"^\d{2}/\d{2}/\d{4}$",
        description="Fecha vencimiento DD/MM/YYYY"
    )
    tipo_comprobante: TipoComprobantePago = Field(
        ...,
        description="Tipo de comprobante de pago"
    )
    serie_comprobante: Optional[str] = Field(
        None,
        max_length=20,
        description="Serie del comprobante"
    )
    numero_comprobante: str = Field(
        ...,
        max_length=20,
        description="Número del comprobante"
    )
    numero_final_rango: Optional[str] = Field(
        None,
        max_length=20,
        description="Número final para comprobantes en rango"
    )
    
    # ===== DATOS DEL PROVEEDOR =====
    tipo_documento_proveedor: TipoDocumentoProveedor = Field(
        ...,
        description="Tipo de documento del proveedor"
    )
    numero_documento_proveedor: str = Field(
        ...,
        max_length=15,
        description="Número de documento del proveedor"
    )
    razon_social_proveedor: str = Field(
        ...,
        max_length=100,
        description="Apellidos y nombres o razón social del proveedor"
    )
    
    # ===== IMPORTES TRIBUTARIOS (CAMPOS 14-23) =====
    base_imponible_gravada: Decimal = Field(
        ...,
        ge=0,
        description="Base imponible de adquisiciones gravadas"
    )
    igv: Decimal = Field(
        ...,
        ge=0,
        description="Impuesto General a las Ventas"
    )
    base_imponible_gravada_operaciones_mixtas: Decimal = Field(
        default=Decimal('0.00'),
        ge=0,
        description="Base imponible gravadas destinadas a operaciones gravadas y exoneradas"
    )
    igv_operaciones_mixtas: Decimal = Field(
        default=Decimal('0.00'),
        ge=0,
        description="IGV de adquisiciones gravadas destinadas a operaciones gravadas y exoneradas"
    )
    base_imponible_gravada_exportacion: Decimal = Field(
        default=Decimal('0.00'),
        ge=0,
        description="Base imponible de adquisiciones gravadas destinadas a operaciones de exportación"
    )
    igv_exportacion: Decimal = Field(
        default=Decimal('0.00'),
        ge=0,
        description="IGV de adquisiciones gravadas destinadas a operaciones de exportación"
    )
    base_imponible_no_gravada: Decimal = Field(
        default=Decimal('0.00'),
        ge=0,
        description="Base imponible de adquisiciones no gravadas"
    )
    isc: Decimal = Field(
        default=Decimal('0.00'),
        ge=0,
        description="Impuesto Selectivo al Consumo"
    )
    otros_tributos: Decimal = Field(
        default=Decimal('0.00'),
        ge=0,
        description="Otros tributos y cargos"
    )
    importe_total: Decimal = Field(
        ...,
        gt=0,
        description="Importe total del comprobante"
    )
    
    # ===== DATOS DE MONEDA =====
    codigo_moneda: str = Field(
        default="PEN",
        max_length=3,
        description="Código de la moneda"
    )
    tipo_cambio: Decimal = Field(
        default=Decimal('1.000'),
        gt=0,
        description="Tipo de cambio"
    )
    
    # ===== DATOS ADICIONALES SUNAT =====
    fecha_emision_detraccion: Optional[str] = Field(
        None,
        pattern=r"^\d{2}/\d{2}/\d{4}$",
        description="Fecha emisión constancia depósito detracción"
    )
    numero_constancia_detraccion: Optional[str] = Field(
        None,
        max_length=23,
        description="Número constancia depósito detracción"
    )
    marca_comprobante_retencion: Optional[str] = Field(
        None,
        pattern=r"^[01]$",
        description="Marca del comprobante sujeto a retención"
    )
    clasificacion_bienes_servicios: Optional[str] = Field(
        None,
        max_length=30,
        description="Clasificación de bienes y servicios"
    )
    identificacion_contrato: Optional[str] = Field(
        None,
        max_length=30,
        description="Identificación del contrato"
    )
    indicador_error: str = Field(
        default="0",
        pattern=r"^[0-4]$",
        description="Error tipo 1, 2, 3 y 4"
    )
    medio_pago: Optional[str] = Field(
        None,
        max_length=3,
        description="Medio de pago"
    )
    estado_operacion: EstadoOperacion = Field(
        default=EstadoOperacion.ACTIVO,
        description="Estado de la operación"
    )
    
    # ===== VALIDADORES =====
    
    @validator('numero_documento_proveedor')
    def validar_numero_documento_proveedor(cls, v, values):
        """Validar número de documento según tipo"""
        tipo_doc = values.get('tipo_documento_proveedor')
        
        if tipo_doc == TipoDocumentoProveedor.RUC:
            if len(v) != 11:
                raise ValueError('RUC debe tener 11 dígitos')
            if not v.isdigit():
                raise ValueError('RUC debe contener solo números')
        elif tipo_doc == TipoDocumentoProveedor.DNI:
            if len(v) != 8:
                raise ValueError('DNI debe tener 8 dígitos')
            if not v.isdigit():
                raise ValueError('DNI debe contener solo números')
        
        return v
    
    @validator('tipo_cambio')
    def validar_tipo_cambio(cls, v):
        """Validar tipo de cambio con 3 decimales"""
        return Decimal(str(v)).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
    
    @validator('base_imponible_gravada', 'igv', 'importe_total', pre=True)
    def formatear_decimales_principales(cls, v):
        """Formatear decimales principales a 2 posiciones"""
        if v is None:
            return Decimal('0.00')
        return Decimal(str(v)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @root_validator
    def validar_balance_tributario(cls, values):
        """Validar que la suma de bases + tributos = importe total"""
        base_gravada = values.get('base_imponible_gravada', Decimal('0'))
        igv = values.get('igv', Decimal('0'))
        base_mixtas = values.get('base_imponible_gravada_operaciones_mixtas', Decimal('0'))
        igv_mixtas = values.get('igv_operaciones_mixtas', Decimal('0'))
        base_export = values.get('base_imponible_gravada_exportacion', Decimal('0'))
        igv_export = values.get('igv_exportacion', Decimal('0'))
        base_no_gravada = values.get('base_imponible_no_gravada', Decimal('0'))
        isc = values.get('isc', Decimal('0'))
        otros_tributos = values.get('otros_tributos', Decimal('0'))
        importe_total = values.get('importe_total', Decimal('0'))
        
        suma_calculada = (
            base_gravada + igv + base_mixtas + igv_mixtas + 
            base_export + igv_export + base_no_gravada + isc + otros_tributos
        )
        
        # Tolerancia de 1 centavo por redondeos
        if abs(suma_calculada - importe_total) > Decimal('0.01'):
            raise ValueError(
                f'Error en balance tributario. '
                f'Suma calculada: {suma_calculada}, '
                f'Importe total: {importe_total}'
            )
        
        return values
    
    @root_validator
    def validar_coherencia_igv(cls, values):
        """Validar coherencia entre base imponible e IGV"""
        base_gravada = values.get('base_imponible_gravada', Decimal('0'))
        igv = values.get('igv', Decimal('0'))
        
        if base_gravada > 0 and igv == 0:
            raise ValueError('Si hay base imponible gravada, debe haber IGV')
        
        if base_gravada == 0 and igv > 0:
            raise ValueError('No puede haber IGV sin base imponible gravada')
        
        # Validar tasa de IGV (18% estándar)
        if base_gravada > 0 and igv > 0:
            tasa_calculada = (igv / base_gravada) * 100
            if not (17.5 <= tasa_calculada <= 18.5):  # Tolerancia para redondeos
                raise ValueError(
                    f'Tasa de IGV fuera de rango estándar: {tasa_calculada:.2f}%'
                )
        
        return values


class RegistroCompraCreate(RegistroCompraBase):
    """Schema para crear registro de compra"""
    
    empresa_id: str = Field(
        ...,
        description="ID de la empresa"
    )
    usuario_creacion: Optional[str] = Field(
        None,
        description="Usuario que crea el registro"
    )
    
    # Campos opcionales para integración
    asiento_contable_id: Optional[str] = Field(
        None,
        description="ID del asiento contable relacionado"
    )
    orden_compra_id: Optional[str] = Field(
        None,
        description="ID de la orden de compra relacionada"
    )
    observaciones: Optional[str] = Field(
        None,
        max_length=500,
        description="Observaciones adicionales"
    )


class RegistroCompraResponse(RegistroCompraBase):
    """Schema para respuesta de registro de compra"""
    
    id: str
    empresa_id: str
    fecha_creacion: datetime
    fecha_modificacion: Optional[datetime] = None
    usuario_creacion: Optional[str] = None
    usuario_modificacion: Optional[str] = None
    
    # Datos de validación
    validaciones_sunat: Optional[Dict[str, Any]] = None
    errores_validacion: List[str] = Field(default_factory=list)
    advertencias_validacion: List[str] = Field(default_factory=list)
    
    # Datos de auditoría
    asiento_contable_id: Optional[str] = None
    orden_compra_id: Optional[str] = None
    observaciones: Optional[str] = None
    
    # Campos calculados
    tasa_igv_calculada: Optional[float] = None
    total_tributos: Optional[Decimal] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class RegistroCompraUpdate(BaseModel):
    """Schema para actualizar registro de compra"""
    
    # Solo campos que se pueden modificar después de la creación
    observaciones: Optional[str] = Field(None, max_length=500)
    clasificacion_bienes_servicios: Optional[str] = Field(None, max_length=30)
    identificacion_contrato: Optional[str] = Field(None, max_length=30)
    indicador_error: Optional[str] = Field(None, pattern=r"^[0-4]$")
    estado_operacion: Optional[EstadoOperacion] = None


class RegistroCompraFiltros(BaseModel):
    """Schema para filtros de búsqueda de registros de compra"""
    
    empresa_id: str
    periodo: Optional[str] = Field(None, pattern=r"^\d{6}$")
    fecha_inicio: Optional[str] = Field(None, pattern=r"^\d{2}/\d{2}/\d{4}$")
    fecha_fin: Optional[str] = Field(None, pattern=r"^\d{2}/\d{2}/\d{4}$")
    tipo_comprobante: Optional[TipoComprobantePago] = None
    numero_documento_proveedor: Optional[str] = None
    estado_operacion: Optional[EstadoOperacion] = None
    importe_minimo: Optional[Decimal] = None
    importe_maximo: Optional[Decimal] = None


class RegistroCompraResumen(BaseModel):
    """Schema para resumen de registros de compra"""
    
    periodo: str
    total_registros: int
    total_base_imponible: Decimal
    total_igv: Decimal
    total_importe: Decimal
    registros_activos: int
    registros_anulados: int
    proveedores_unicos: int
    fecha_generacion: datetime


# ===== SCHEMAS PARA EXPORTACIÓN PLE =====

class PLEComprasExportOptions(BaseModel):
    """Opciones para exportación PLE 080000"""
    
    empresa_id: str
    periodo: str = Field(..., pattern=r"^\d{6}$")
    incluir_anulados: bool = Field(default=False)
    validar_antes_exportar: bool = Field(default=True)
    generar_zip: bool = Field(default=True)
    incluir_metadatos: bool = Field(default=True)
    filtros_adicionales: Optional[RegistroCompraFiltros] = None


class PLEComprasExportResult(BaseModel):
    """Resultado de exportación PLE 080000"""
    
    exito: bool
    nombre_archivo: str
    contenido_txt: Optional[str] = None
    contenido_zip: Optional[bytes] = None
    total_registros: int
    periodo: str
    empresa_ruc: str
    empresa_razon_social: str
    fecha_generacion: datetime
    errores: List[str] = Field(default_factory=list)
    advertencias: List[str] = Field(default_factory=list)
    
    # Estadísticas
    total_base_imponible: Decimal
    total_igv: Decimal  
    total_importe: Decimal
    resumen_por_tipo_comprobante: Dict[str, int] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }
