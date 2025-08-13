"""
Modelos RVIE - Registro de Ventas e Ingresos Electrónico
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field
from enum import Enum


class RvieEstadoProceso(str, Enum):
    """Estados del proceso RVIE"""
    PENDIENTE = "PENDIENTE"
    PROPUESTA = "PROPUESTA"
    ACEPTADO = "ACEPTADO"
    PRELIMINAR = "PRELIMINAR"
    FINALIZADO = "FINALIZADO"
    ERROR = "ERROR"


class RvieTipoComprobante(str, Enum):
    """Tipos de comprobante RVIE"""
    FACTURA = "01"
    BOLETA = "03"
    NOTA_CREDITO = "07"
    NOTA_DEBITO = "08"
    GUIA_REMISION = "09"
    RECIBO_HONORARIOS = "12"
    DOCUMENTO_RETENCION = "20"
    DOCUMENTO_PERCEPCION = "40"


class RvieComprobante(BaseModel):
    """Modelo de comprobante RVIE"""
    periodo: str = Field(..., description="Periodo YYYYMM")
    correlativo: str = Field(..., description="Número correlativo")
    fecha_emision: date = Field(..., description="Fecha de emisión")
    tipo_comprobante: RvieTipoComprobante = Field(..., description="Tipo de comprobante")
    serie: str = Field(..., description="Serie del comprobante")
    numero: str = Field(..., description="Número del comprobante")
    
    # Datos del cliente
    tipo_documento_cliente: str = Field(..., description="Tipo documento cliente")
    numero_documento_cliente: str = Field(..., description="Número documento cliente")
    razon_social_cliente: str = Field(..., description="Razón social cliente")
    
    # Montos
    base_imponible: Decimal = Field(..., description="Base imponible")
    igv: Decimal = Field(..., description="IGV")
    otros_tributos: Decimal = Field(default=Decimal("0.00"), description="Otros tributos")
    importe_total: Decimal = Field(..., description="Importe total")
    
    # Datos adicionales
    moneda: str = Field(default="PEN", description="Código de moneda")
    tipo_cambio: Optional[Decimal] = Field(None, description="Tipo de cambio")
    estado: str = Field(default="EMITIDO", description="Estado del comprobante")
    
    # Metadatos
    fecha_registro: datetime = Field(default_factory=datetime.utcnow)
    observaciones: Optional[str] = Field(None, description="Observaciones")


class RviePropuesta(BaseModel):
    """Propuesta RVIE de SUNAT"""
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo: str = Field(..., description="Periodo YYYYMM")
    estado: RvieEstadoProceso = Field(default=RvieEstadoProceso.PROPUESTA)
    
    # Datos de la propuesta
    fecha_generacion: datetime = Field(..., description="Fecha de generación")
    cantidad_comprobantes: int = Field(..., description="Cantidad de comprobantes")
    total_base_imponible: Decimal = Field(..., description="Total base imponible")
    total_igv: Decimal = Field(..., description="Total IGV")
    total_otros_tributos: Decimal = Field(default=Decimal("0.00"))
    total_importe: Decimal = Field(..., description="Total importe")
    
    # Comprobantes de la propuesta
    comprobantes: List[RvieComprobante] = Field(default_factory=list)
    
    # Archivos asociados
    archivo_propuesta: Optional[str] = Field(None, description="Nombre archivo propuesta")
    archivo_inconsistencias: Optional[str] = Field(None, description="Nombre archivo inconsistencias")
    
    # Control
    ticket_id: Optional[str] = Field(None, description="ID del ticket SUNAT")
    fecha_aceptacion: Optional[datetime] = Field(None, description="Fecha de aceptación")
    fecha_actualizacion: datetime = Field(default_factory=datetime.utcnow)


class RvieInconsistencia(BaseModel):
    """Inconsistencia encontrada en RVIE"""
    linea: int = Field(..., description="Número de línea")
    campo: str = Field(..., description="Campo con inconsistencia")
    valor_encontrado: str = Field(..., description="Valor encontrado")
    valor_esperado: str = Field(..., description="Valor esperado")
    descripcion_error: str = Field(..., description="Descripción del error")
    tipo_error: str = Field(..., description="Tipo de error")
    severidad: str = Field(default="ERROR", description="Severidad: ERROR, WARNING")


class RvieProcesoResult(BaseModel):
    """Resultado de proceso RVIE"""
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo: str = Field(..., description="Periodo procesado")
    operacion: str = Field(..., description="Operación realizada")
    estado: RvieEstadoProceso = Field(..., description="Estado del proceso")
    
    # Resultados
    exitoso: bool = Field(..., description="Si el proceso fue exitoso")
    mensaje: str = Field(..., description="Mensaje del resultado")
    ticket_id: Optional[str] = Field(None, description="ID del ticket generado")
    
    # Estadísticas
    comprobantes_procesados: int = Field(default=0)
    comprobantes_exitosos: int = Field(default=0)
    comprobantes_con_errores: int = Field(default=0)
    
    # Errores e inconsistencias
    inconsistencias: List[RvieInconsistencia] = Field(default_factory=list)
    errores: List[str] = Field(default_factory=list)
    
    # Metadatos
    fecha_inicio: datetime = Field(default_factory=datetime.utcnow)
    fecha_fin: Optional[datetime] = Field(None)
    tiempo_procesamiento: Optional[int] = Field(None, description="Tiempo en segundos")


class RvieResumen(BaseModel):
    """Resumen de RVIE por periodo"""
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo: str = Field(..., description="Periodo YYYYMM")
    
    # Totales
    total_comprobantes: int = Field(default=0)
    total_base_imponible: Decimal = Field(default=Decimal("0.00"))
    total_igv: Decimal = Field(default=Decimal("0.00"))
    total_otros_tributos: Decimal = Field(default=Decimal("0.00"))
    total_importe: Decimal = Field(default=Decimal("0.00"))
    
    # Por tipo de comprobante
    resumen_por_tipo: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Estado del proceso
    estado_actual: RvieEstadoProceso = Field(default=RvieEstadoProceso.PENDIENTE)
    fecha_ultimo_proceso: Optional[datetime] = Field(None)
    
    # Archivos generados
    archivos_disponibles: List[str] = Field(default_factory=list)
