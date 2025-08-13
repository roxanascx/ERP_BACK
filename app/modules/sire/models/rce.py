"""
Modelos RCE - Registro de Compras Electrónico
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum


class RceEstadoProceso(str, Enum):
    """Estados del proceso RCE"""
    PENDIENTE = "PENDIENTE"
    PROPUESTA = "PROPUESTA"
    ACEPTADO = "ACEPTADO"
    PRELIMINAR = "PRELIMINAR"
    FINALIZADO = "FINALIZADO"
    ERROR = "ERROR"


class RceTipoComprobante(str, Enum):
    """Tipos de comprobante RCE"""
    FACTURA = "01"
    BOLETA = "03"
    NOTA_CREDITO = "07"
    NOTA_DEBITO = "08"
    GUIA_REMISION = "09"
    RECIBO_HONORARIOS = "12"
    DOCUMENTO_RETENCION = "20"
    DOCUMENTO_PERCEPCION = "40"
    COMPROBANTE_NO_DOMICILIADO = "91"
    OTROS_DOCUMENTOS = "99"


class RceComprobante(BaseModel):
    """Modelo de comprobante RCE"""
    periodo: str = Field(..., description="Periodo YYYYMM")
    correlativo: str = Field(..., description="Número correlativo")
    fecha_emision: date = Field(..., description="Fecha de emisión")
    fecha_vencimiento: Optional[date] = Field(None, description="Fecha de vencimiento")
    tipo_comprobante: RceTipoComprobante = Field(..., description="Tipo de comprobante")
    serie: str = Field(..., description="Serie del comprobante")
    numero: str = Field(..., description="Número del comprobante")
    
    # Datos del proveedor
    tipo_documento_proveedor: str = Field(..., description="Tipo documento proveedor")
    numero_documento_proveedor: str = Field(..., description="Número documento proveedor")
    razon_social_proveedor: str = Field(..., description="Razón social proveedor")
    
    # Montos
    base_imponible: Decimal = Field(..., description="Base imponible")
    igv: Decimal = Field(..., description="IGV")
    otros_tributos: Decimal = Field(default=Decimal("0.00"), description="Otros tributos")
    importe_total: Decimal = Field(..., description="Importe total")
    
    # Datos específicos RCE
    derecho_credito_fiscal: bool = Field(default=True, description="Derecho a crédito fiscal")
    detraccion: Optional[Decimal] = Field(None, description="Monto detracción")
    retencion: Optional[Decimal] = Field(None, description="Monto retención")
    percepcion: Optional[Decimal] = Field(None, description="Monto percepción")
    
    # Datos adicionales
    moneda: str = Field(default="PEN", description="Código de moneda")
    tipo_cambio: Optional[Decimal] = Field(None, description="Tipo de cambio")
    estado: str = Field(default="RECIBIDO", description="Estado del comprobante")
    
    # Metadatos
    fecha_registro: datetime = Field(default_factory=datetime.utcnow)
    observaciones: Optional[str] = Field(None, description="Observaciones")


class RcePropuesta(BaseModel):
    """Propuesta RCE de SUNAT"""
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo: str = Field(..., description="Periodo YYYYMM")
    estado: RceEstadoProceso = Field(default=RceEstadoProceso.PROPUESTA)
    
    # Datos de la propuesta
    fecha_generacion: datetime = Field(..., description="Fecha de generación")
    cantidad_comprobantes: int = Field(..., description="Cantidad de comprobantes")
    total_base_imponible: Decimal = Field(..., description="Total base imponible")
    total_igv: Decimal = Field(..., description="Total IGV")
    total_otros_tributos: Decimal = Field(default=Decimal("0.00"))
    total_importe: Decimal = Field(..., description="Total importe")
    
    # Totales específicos RCE
    total_detraccion: Decimal = Field(default=Decimal("0.00"))
    total_retencion: Decimal = Field(default=Decimal("0.00"))
    total_percepcion: Decimal = Field(default=Decimal("0.00"))
    
    # Comprobantes de la propuesta
    comprobantes: List[RceComprobante] = Field(default_factory=list)
    
    # Archivos asociados
    archivo_propuesta: Optional[str] = Field(None, description="Nombre archivo propuesta")
    archivo_inconsistencias: Optional[str] = Field(None, description="Nombre archivo inconsistencias")
    archivo_resumen: Optional[str] = Field(None, description="Nombre archivo resumen")
    
    # Control
    ticket_id: Optional[str] = Field(None, description="ID del ticket SUNAT")
    fecha_aceptacion: Optional[datetime] = Field(None, description="Fecha de aceptación")
    fecha_actualizacion: datetime = Field(default_factory=datetime.utcnow)


class RceInconsistencia(BaseModel):
    """Inconsistencia encontrada en RCE"""
    linea: int = Field(..., description="Número de línea")
    campo: str = Field(..., description="Campo con inconsistencia")
    valor_encontrado: str = Field(..., description="Valor encontrado")
    valor_esperado: str = Field(..., description="Valor esperado")
    descripcion_error: str = Field(..., description="Descripción del error")
    tipo_error: str = Field(..., description="Tipo de error")
    severidad: str = Field(default="ERROR", description="Severidad: ERROR, WARNING")
    
    # Específico para RCE
    afecta_credito_fiscal: bool = Field(default=False, description="Afecta crédito fiscal")


class RceResumenConsolidado(BaseModel):
    """Resumen consolidado RCE"""
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo: str = Field(..., description="Periodo YYYYMM")
    fecha_generacion: datetime = Field(..., description="Fecha de generación")
    
    # Totales por tipo de comprobante
    resumen_por_tipo: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Totales generales
    total_comprobantes: int = Field(default=0)
    total_base_imponible: Decimal = Field(default=Decimal("0.00"))
    total_igv: Decimal = Field(default=Decimal("0.00"))
    total_otros_tributos: Decimal = Field(default=Decimal("0.00"))
    total_importe: Decimal = Field(default=Decimal("0.00"))
    
    # Totales específicos RCE
    total_credito_fiscal: Decimal = Field(default=Decimal("0.00"))
    total_detraccion: Decimal = Field(default=Decimal("0.00"))
    total_retencion: Decimal = Field(default=Decimal("0.00"))
    total_percepcion: Decimal = Field(default=Decimal("0.00"))


class RceProcesoResult(BaseModel):
    """Resultado de proceso RCE"""
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo: str = Field(..., description="Periodo procesado")
    operacion: str = Field(..., description="Operación realizada")
    estado: RceEstadoProceso = Field(..., description="Estado del proceso")
    
    # Resultados
    exitoso: bool = Field(..., description="Si el proceso fue exitoso")
    mensaje: str = Field(..., description="Mensaje del resultado")
    ticket_id: Optional[str] = Field(None, description="ID del ticket generado")
    
    # Estadísticas
    comprobantes_procesados: int = Field(default=0)
    comprobantes_exitosos: int = Field(default=0)
    comprobantes_con_errores: int = Field(default=0)
    
    # Totales
    total_credito_fiscal: Optional[Decimal] = Field(None)
    total_detraccion: Optional[Decimal] = Field(None)
    total_retencion: Optional[Decimal] = Field(None)
    
    # Errores e inconsistencias
    inconsistencias: List[RceInconsistencia] = Field(default_factory=list)
    errores: List[str] = Field(default_factory=list)
    
    # Metadatos
    fecha_inicio: datetime = Field(default_factory=datetime.utcnow)
    fecha_fin: Optional[datetime] = Field(None)
    tiempo_procesamiento: Optional[int] = Field(None, description="Tiempo en segundos")


class RceResumen(BaseModel):
    """Resumen de RCE por periodo"""
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo: str = Field(..., description="Periodo YYYYMM")
    
    # Totales
    total_comprobantes: int = Field(default=0)
    total_base_imponible: Decimal = Field(default=Decimal("0.00"))
    total_igv: Decimal = Field(default=Decimal("0.00"))
    total_credito_fiscal: Decimal = Field(default=Decimal("0.00"))
    total_otros_tributos: Decimal = Field(default=Decimal("0.00"))
    total_importe: Decimal = Field(default=Decimal("0.00"))
    
    # Totales específicos
    total_detraccion: Decimal = Field(default=Decimal("0.00"))
    total_retencion: Decimal = Field(default=Decimal("0.00"))
    total_percepcion: Decimal = Field(default=Decimal("0.00"))
    
    # Por tipo de comprobante
    resumen_por_tipo: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Estado del proceso
    estado_actual: RceEstadoProceso = Field(default=RceEstadoProceso.PENDIENTE)
    fecha_ultimo_proceso: Optional[datetime] = Field(None)
    
    # Archivos generados
    archivos_disponibles: List[str] = Field(default_factory=list)
