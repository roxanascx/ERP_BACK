"""
Schemas Pydantic para Registro de Ventas PLE 140000
===================================================

Esquemas de validación para el Registro de Ventas según especificaciones
SUNAT oficiales. Implementa los 34 campos oficiales del PLE 140000.

Basado en:
- PLE_SUNAT_DOCUMENTACION_COMPLETA.md
- Resolución de Superintendencia N° 286-2009/SUNAT

Campos oficiales PLE 140000 (Registro de Ventas):
1. Período                    2. Código único operación (CUO)
3. Correlativo asiento        4. Fecha emisión comprobante  
5. Fecha vencimiento          6. Tipo comprobante pago
7. Serie comprobante          8. Número comprobante
9. Número final (rangos)      10. Tipo documento cliente
11. Número documento cliente  12. Apellidos/razón social cliente
13. Valor facturado exportación  14. Base imponible gravadas
15. Descuento base imponible  16. IGV/IPM
17. Descuento IGV/IPM        18. Importe exonerado
19. Importe inafecto         20. ISC
21. Base imponible IVAP      22. IVAP
23. Otros tributos/cargos    24. Importe total
25. Código moneda            26. Tipo cambio
27. Fecha constancia detracción  28. Número constancia detracción
29. Indicador servicio gravado SPOT  30. Otros conceptos tributos
31. Base imponible ICBPER    32. ICBPER
33. Error tipo 1,2,3,4       34. Estado operación

Autor: Sistema ERP - FASE 2.2
Fecha: Agosto 2025
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from decimal import Decimal
from enum import Enum, IntEnum
from pydantic import BaseModel, Field


# ===================================
# ENUMS PARA CLASIFICACIÓN OFICIAL
# ===================================

class TipoComprobanteVenta(str, Enum):
    """Tipos de comprobantes de pago oficiales SUNAT para ventas"""
    FACTURA = "01"
    BOLETA = "03"
    LIQUIDACION_COMPRA = "04"
    TICKET = "05"
    NOTA_CREDITO = "07"
    NOTA_DEBITO = "08"
    GUIA_REMISION = "09"
    COMPROBANTE_PERCEPCION = "11"
    COMPROBANTE_DETRACCION = "12"
    BOLETO_AVIACION_COMERCIAL = "13"
    COMPROBANTE_SCOP = "14"
    POLIZA_SEGURO = "19"
    COMPROBANTE_RETENCION = "20"


class TipoDocumentoCliente(str, Enum):
    """Tipos de documento de identidad oficiales SUNAT para clientes"""
    SIN_DOCUMENTO = "0"
    DNI = "1"
    CARNET_EXTRANJERIA = "4"
    RUC = "6"
    PASAPORTE = "7"
    CEDULA_DIPLOMATICA = "11"
    DOCUMENTO_TRIBUTARIO = "A"


class EstadoOperacionVenta(IntEnum):
    """Estados de operación según SUNAT para ventas"""
    VIGENTE = 1
    ANULADO = 8
    ANULADO_POR_OTRO_DOCUMENTO = 9


# ===================================
# MODELOS PRINCIPALES DE VENTAS
# ===================================

class RegistroVentaRequest(BaseModel):
    """Modelo para crear/actualizar registro de venta"""
    
    # Información del cliente
    tipo_documento_cliente: TipoDocumentoCliente
    numero_documento_cliente: str = Field(..., min_length=1, max_length=15)
    razon_social_cliente: str = Field(..., min_length=1, max_length=100)
    
    # Información del comprobante
    tipo_comprobante: TipoComprobanteVenta
    serie_comprobante: Optional[str] = Field(None, max_length=20)
    numero_comprobante: str = Field(..., min_length=1, max_length=20)
    numero_final_rango: Optional[str] = Field(None, max_length=20)
    fecha_emision: str = Field(...)
    fecha_vencimiento: Optional[str] = Field(None)
    
    # Montos específicos para ventas (34 campos PLE 140000)
    valor_facturado_exportacion: Decimal = Field(default=Decimal('0.00'))
    base_imponible_gravada: Decimal = Field(...)
    descuento_base_imponible: Decimal = Field(default=Decimal('0.00'))
    igv_ipm: Decimal = Field(...)
    descuento_igv_ipm: Decimal = Field(default=Decimal('0.00'))
    importe_exonerado: Decimal = Field(default=Decimal('0.00'))
    importe_inafecto: Decimal = Field(default=Decimal('0.00'))
    isc: Decimal = Field(default=Decimal('0.00'))
    base_imponible_ivap: Decimal = Field(default=Decimal('0.00'))
    ivap: Decimal = Field(default=Decimal('0.00'))
    otros_tributos_cargos: Decimal = Field(default=Decimal('0.00'))
    importe_total: Decimal = Field(...)
    
    # Datos adicionales específicos de ventas
    codigo_moneda: str = Field(default="PEN", min_length=3, max_length=3)
    tipo_cambio: Decimal = Field(default=Decimal('1.000'))
    fecha_emision_detraccion: Optional[str] = Field(None)
    numero_constancia_detraccion: Optional[str] = Field(None, max_length=23)
    indicador_servicio_gravado_spot: Optional[str] = Field(None, max_length=1)
    otros_conceptos_tributos: Decimal = Field(default=Decimal('0.00'))
    base_imponible_icbper: Decimal = Field(default=Decimal('0.00'))
    icbper: Decimal = Field(default=Decimal('0.00'))
    indicador_error: str = Field(default="0", max_length=1)
    estado_operacion: EstadoOperacionVenta = Field(default=EstadoOperacionVenta.VIGENTE)


class RegistroVentaResponse(RegistroVentaRequest):
    """Modelo de respuesta para registro de venta"""
    id: str = Field(..., description="ID único del registro")
    empresa_id: str = Field(..., description="ID de la empresa")
    periodo: str = Field(..., description="Período AAAAMM")
    fecha_creacion: datetime = Field(..., description="Fecha de creación")
    fecha_actualizacion: Optional[datetime] = Field(None, description="Fecha de última actualización")

    # Trazabilidad del puente SIRE -> contabilidad. Sin estos campos, la
    # pantalla no puede distinguir un comprobante ya contabilizado de uno
    # pendiente, ni saber de dónde salió.
    origen: Optional[str] = Field(None, description="SIRE o MANUAL")
    subdiario: Optional[str] = Field(None, description="Código del subdiario asignado")
    asiento_numero: Optional[str] = Field(None, description="Asiento que generó, si ya se contabilizó")
    car_sunat: Optional[str] = Field(None, description="Identificador del comprobante en SUNAT")
    
    class Config:
        from_attributes = True


# ===================================
# MODELOS PARA EXPORTACIÓN PLE
# ===================================

class PLEVentasExportOptions(BaseModel):
    """Opciones para exportar PLE de ventas"""
    
    # Filtros principales
    empresa_id: str = Field(..., description="ID de la empresa")
    periodo_inicio: str = Field(..., description="Período inicio AAAAMM")
    periodo_fin: str = Field(..., description="Período fin AAAAMM")
    
    # Filtros opcionales
    tipo_comprobante: Optional[TipoComprobanteVenta] = None
    tipo_documento_cliente: Optional[TipoDocumentoCliente] = None
    estado_operacion: Optional[EstadoOperacionVenta] = None
    
    # Opciones de exportación
    incluir_anulados: bool = Field(default=False, description="Incluir registros anulados")
    solo_errores: bool = Field(default=False, description="Solo registros con errores")
    formato_fecha: str = Field(default="DD/MM/YYYY", description="Formato de fechas")
    
    # Metadatos del archivo
    correlativo_archivo: str = Field(default="0001", description="Correlativo del archivo")
    generar_nombre_automatico: bool = Field(default=True, description="Generar nombre automático")


class PLEVentasExportResult(BaseModel):
    """Resultado de la exportación PLE de ventas"""
    
    # Información del archivo
    nombre_archivo: str = Field(..., description="Nombre del archivo generado")
    contenido_archivo: str = Field(..., description="Contenido del archivo PLE")
    tamaño_archivo: int = Field(..., description="Tamaño del archivo en bytes")
    
    # Estadísticas de la exportación
    total_registros: int = Field(..., description="Total de registros procesados")
    registros_exportados: int = Field(..., description="Registros incluidos en el PLE")
    registros_excluidos: int = Field(..., description="Registros excluidos")
    registros_con_errores: int = Field(..., description="Registros con errores")
    
    # Metadatos
    fecha_generacion: datetime = Field(..., description="Fecha de generación")
    periodo_procesado: str = Field(..., description="Período procesado")
    empresa_id: str = Field(..., description="ID de la empresa")
    usuario_generacion: Optional[str] = Field(None, description="Usuario que generó")
    
    # Información adicional
    resumen_montos: Dict[str, Decimal] = Field(default_factory=dict, description="Resumen de montos")
    errores_encontrados: List[str] = Field(default_factory=list, description="Lista de errores")
    warnings: List[str] = Field(default_factory=list, description="Advertencias")
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda dt: dt.isoformat()
        }


# ===================================
# MODELOS ESPECÍFICOS DE VENTAS
# ===================================

class ClienteBase(BaseModel):
    """Información básica del cliente"""
    tipo_documento: TipoDocumentoCliente
    numero_documento: str = Field(..., min_length=1, max_length=15)
    razon_social: str = Field(..., min_length=1, max_length=100)


class ComprobanteVentaBase(BaseModel):
    """Información básica del comprobante de venta"""
    tipo_comprobante: TipoComprobanteVenta
    serie_comprobante: Optional[str] = Field(None, max_length=20)
    numero_comprobante: str = Field(..., min_length=1, max_length=20)
    numero_final_rango: Optional[str] = Field(None, max_length=20)
    fecha_emision: str = Field(...)
    fecha_vencimiento: Optional[str] = Field(None)


class MontosVentaPLE(BaseModel):
    """Montos detallados para PLE según estructura oficial SUNAT para ventas"""
    
    # Campos específicos PLE 140000 (34 campos)
    valor_facturado_exportacion: Decimal = Field(default=Decimal('0.00'))
    base_imponible_gravada: Decimal = Field(default=Decimal('0.00'))
    descuento_base_imponible: Decimal = Field(default=Decimal('0.00'))
    igv_ipm: Decimal = Field(default=Decimal('0.00'))
    descuento_igv_ipm: Decimal = Field(default=Decimal('0.00'))
    importe_exonerado: Decimal = Field(default=Decimal('0.00'))
    importe_inafecto: Decimal = Field(default=Decimal('0.00'))
    isc: Decimal = Field(default=Decimal('0.00'))
    base_imponible_ivap: Decimal = Field(default=Decimal('0.00'))
    ivap: Decimal = Field(default=Decimal('0.00'))
    otros_tributos_cargos: Decimal = Field(default=Decimal('0.00'))
    importe_total: Decimal = Field(...)
    
    # Campos adicionales específicos ventas
    otros_conceptos_tributos: Decimal = Field(default=Decimal('0.00'))
    base_imponible_icbper: Decimal = Field(default=Decimal('0.00'))
    icbper: Decimal = Field(default=Decimal('0.00'))


class DatosAdicionalesVenta(BaseModel):
    """Datos adicionales específicos PLE ventas"""
    
    codigo_moneda: str = Field(default="PEN", min_length=3, max_length=3)
    tipo_cambio: Decimal = Field(default=Decimal('1.000'))
    fecha_emision_detraccion: Optional[str] = Field(None)
    numero_constancia_detraccion: Optional[str] = Field(None, max_length=23)
    indicador_servicio_gravado_spot: Optional[str] = Field(None, max_length=1)
    indicador_error: str = Field(default="0", max_length=1)
    estado_operacion: EstadoOperacionVenta = Field(default=EstadoOperacionVenta.VIGENTE)


# ===================================
# MODELOS PARA FILTROS Y ESTADÍSTICAS
# ===================================

class FiltroVentas(BaseModel):
    """Filtros para consultar ventas"""
    
    # Filtros básicos
    empresa_id: Optional[str] = None
    periodo_inicio: Optional[str] = None
    periodo_fin: Optional[str] = None
    
    # Filtros por cliente
    numero_documento_cliente: Optional[str] = None
    razon_social_cliente: Optional[str] = None
    tipo_documento_cliente: Optional[TipoDocumentoCliente] = None
    
    # Filtros por comprobante
    tipo_comprobante: Optional[TipoComprobanteVenta] = None
    serie_comprobante: Optional[str] = None
    numero_comprobante: Optional[str] = None
    
    # Filtros por fechas
    fecha_emision_inicio: Optional[str] = None
    fecha_emision_fin: Optional[str] = None
    
    # Filtros por montos
    importe_minimo: Optional[Decimal] = None
    importe_maximo: Optional[Decimal] = None
    
    # Filtros por estado
    estado_operacion: Optional[EstadoOperacionVenta] = None
    solo_errores: bool = Field(default=False)
    incluir_anulados: bool = Field(default=False)
    
    # Paginación
    pagina: int = Field(default=1, ge=1)
    limite: int = Field(default=50, ge=1, le=1000)


class EstadisticasVentas(BaseModel):
    """Estadísticas de registros de ventas"""
    
    total_registros: int
    total_importe: Decimal
    total_igv: Decimal
    total_base_gravada: Decimal
    total_exportaciones: Decimal
    
    por_tipo_comprobante: Dict[str, int]
    por_estado: Dict[str, int]
    por_periodo: Dict[str, int]
    
    registros_con_errores: int
    registros_anulados: int
    
    class Config:
        json_encoders = {
            Decimal: str
        }
