"""
Esquemas para Gestión de Ventas RVIE
Modelos para consulta directa a SUNAT
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class RvieComprobanteVentaResponse(BaseModel):
    """Comprobante de venta procesado"""
    # Datos básicos del comprobante
    ruc_emisor: str = Field(..., description="RUC del emisor")
    tipo_comprobante: str = Field(..., description="Tipo de comprobante (01, 03, 07, 08, etc.)")
    serie: str = Field(..., description="Serie del comprobante")
    numero: str = Field(..., description="Número del comprobante")
    fecha_emision: str = Field(..., description="Fecha de emisión")
    
    # Datos económicos
    moneda: Optional[str] = Field(None, description="Moneda del comprobante")
    importe_total: float = Field(0.0, description="Importe total del comprobante")
    base_imponible: Optional[float] = Field(None, description="Base imponible gravada")
    igv: Optional[float] = Field(None, description="Monto del IGV")
    exonerado: Optional[float] = Field(None, description="Importe exonerado")
    inafecto: Optional[float] = Field(None, description="Importe inafecto")
    
    # Metadatos
    estado: Optional[str] = Field(None, description="Estado del comprobante")
    observaciones: Optional[str] = Field(None, description="Observaciones")
    fecha_consulta: Optional[datetime] = Field(None, description="Fecha de última consulta")

class RvieResumenSunatRequest(BaseModel):
    """Request para consultar resumen desde SUNAT"""
    periodo: str = Field(..., description="Período en formato YYYYMM")
    tipos_resumen: List[int] = Field(
        default=[1, 4, 5], 
        description="Tipos de resumen a consultar (1=Propuesta, 4=Registro, 5=Preliminar)"
    )
    formato: int = Field(default=0, description="Formato de archivo (0=TXT, 1=CSV)")
    forzar_actualizacion: bool = Field(
        default=False, 
        description="Forzar nueva consulta aunque existan datos recientes"
    )

class RvieResumenSunatResponse(BaseModel):
    """Response del resumen consultado desde SUNAT"""
    # Metadatos de la consulta
    ruc: str = Field(..., description="RUC consultado")
    periodo: str = Field(..., description="Período consultado")
    tipo_resumen: int = Field(..., description="Tipo de resumen consultado")
    fecha_consulta: datetime = Field(..., description="Fecha y hora de la consulta")
    
    # Datos del resumen
    total_comprobantes: int = Field(0, description="Total de comprobantes encontrados")
    comprobantes: List[RvieComprobanteVentaResponse] = Field(
        default=[], 
        description="Lista de comprobantes encontrados"
    )
    
    # Totales consolidados
    totales: Dict[str, Any] = Field(
        default={},
        description="Totales consolidados por tipo de operación"
    )
    
    # Estado de la consulta
    estado_consulta: str = Field(..., description="Estado de la consulta (EXITOSO, SIN_DATOS, ERROR)")
    mensaje: Optional[str] = Field(None, description="Mensaje adicional sobre la consulta")
    
    # Archivos generados (si aplica)
    archivos_descargados: List[str] = Field(
        default=[],
        description="Lista de archivos descargados desde SUNAT"
    )

class RvieVentasEstadisticasResponse(BaseModel):
    """Estadísticas de ventas para el dashboard"""
    periodo: str = Field(..., description="Período analizado")
    total_comprobantes: int = Field(0, description="Total de comprobantes")
    total_facturado: float = Field(0.0, description="Total facturado")
    total_igv: float = Field(0.0, description="Total IGV")
    
    # Distribución por tipo de comprobante
    por_tipo_comprobante: Dict[str, Dict[str, Any]] = Field(
        default={},
        description="Estadísticas por tipo de comprobante"
    )
    
    # Distribución mensual (si el período abarca varios meses)
    distribucion_mensual: List[Dict[str, Any]] = Field(
        default=[],
        description="Distribución de ventas por mes"
    )
    
    fecha_ultima_actualizacion: Optional[datetime] = Field(
        None,
        description="Fecha de última actualización de datos"
    )

class RvieComprobanteDetalleResponse(BaseModel):
    """Detalle completo de un comprobante de venta"""
    # Datos básicos (heredados)
    comprobante: RvieComprobanteVentaResponse
    
    # Datos adicionales del detalle
    lineas_detalle: List[Dict[str, Any]] = Field(
        default=[],
        description="Líneas de detalle del comprobante"
    )
    
    # Información de la consulta
    fuente_datos: str = Field(..., description="Origen de los datos (SUNAT, CACHE, PROPUESTA)")
    disponible_en_sunat: bool = Field(True, description="Si está disponible en SUNAT")
    requiere_actualizacion: bool = Field(False, description="Si requiere actualización")

class RvieVentasResponse(BaseModel):
    """Response principal para consultas de ventas RVIE"""
    # Metadatos básicos
    ruc: str = Field(..., description="RUC consultado")
    periodo: str = Field(..., description="Período consultado en formato YYYYMM")
    fecha_consulta: datetime = Field(..., description="Fecha y hora de la consulta")
    
    # Datos de comprobantes
    total_comprobantes: int = Field(0, description="Total de comprobantes encontrados")
    comprobantes: List[Dict[str, Any]] = Field(default=[], description="Lista de comprobantes")
    
    # Totales financieros
    totales: Dict[str, float] = Field(
        default={},
        description="Totales por tipo (ventas, igv, base_imponible, etc.)"
    )
    
    # Estado de la consulta
    mensaje: str = Field(..., description="Mensaje descriptivo del resultado")
    estado_consulta: str = Field(default="exitoso", description="Estado de la consulta")
    
    # Metadatos opcionales
    fuente_datos: str = Field(default="SUNAT", description="Fuente de los datos")
    tiempo_respuesta: Optional[float] = Field(None, description="Tiempo de respuesta en segundos")
