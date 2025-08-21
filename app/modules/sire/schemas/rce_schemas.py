"""
Schemas RCE - Request/Response para API
Basado en Manual SUNAT SIRE Compras v27.0
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union
from decimal import Decimal
from pydantic import BaseModel, Field, validator

from ..models.rce import (
    RceEstadoProceso, RceTipoComprobante, RceTipoDocumento, RceMoneda,
    RceComprobante, RcePropuesta, RceInconsistencia, RceProcesoResult
)


# =======================================
# SCHEMAS DE REQUEST (INPUT)
# =======================================

class RceComprobanteCreateRequest(BaseModel):
    """Request para crear/actualizar comprobante RCE"""
    # Campos básicos obligatorios
    periodo: str = Field(..., description="Periodo YYYYMM", pattern=r"^\d{6}$")
    correlativo: str = Field(..., description="Número correlativo único")
    fecha_emision: date = Field(..., description="Fecha de emisión")
    fecha_vencimiento: Optional[date] = Field(None, description="Fecha de vencimiento")
    
    # Tipo de comprobante
    tipo_comprobante: RceTipoComprobante = Field(..., description="Tipo de comprobante")
    serie: str = Field(..., description="Serie del comprobante")
    numero: str = Field(..., description="Número del comprobante")
    numero_final: Optional[str] = Field(None, description="Número final (para rangos)")
    
    # Proveedor
    tipo_documento_proveedor: RceTipoDocumento = Field(..., description="Tipo documento proveedor")
    numero_documento_proveedor: str = Field(..., description="Número documento proveedor")
    razon_social_proveedor: str = Field(..., description="Razón social proveedor")
    
    # Montos principales
    moneda: RceMoneda = Field(default=RceMoneda.PEN, description="Código de moneda")
    tipo_cambio: Optional[Decimal] = Field(None, description="Tipo de cambio")
    base_imponible_operaciones_gravadas: Decimal = Field(default=Decimal("0.00"))
    igv: Decimal = Field(default=Decimal("0.00"))
    importe_total: Decimal = Field(..., description="Importe total")
    
    # Campos opcionales específicos RCE
    sustenta_credito_fiscal: bool = Field(default=True)
    sustenta_costo_gasto: bool = Field(default=True)
    
    # Detracción/Retención/Percepción (simplificado para request)
    monto_detraccion: Optional[Decimal] = Field(None, description="Monto detraído")
    monto_retencion: Optional[Decimal] = Field(None, description="Monto retenido")
    monto_percepcion: Optional[Decimal] = Field(None, description="Monto percibido")
    
    # Observaciones
    observaciones: Optional[str] = Field(None, description="Observaciones")


class RcePropuestaGenerarRequest(BaseModel):
    """Request para generar propuesta RCE"""
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo: str = Field(..., description="Periodo YYYYMM", pattern=r"^\d{6}$")
    comprobantes: List[RceComprobanteCreateRequest] = Field(..., description="Comprobantes a incluir")
    
    # Opciones de generación
    validar_duplicados: bool = Field(default=True, description="Validar comprobantes duplicados")
    incluir_observaciones: bool = Field(default=True, description="Incluir observaciones en propuesta")
    formato_salida: str = Field(default="TXT", description="Formato: TXT, EXCEL")


class RceProcesoEnviarRequest(BaseModel):
    """Request para enviar proceso RCE"""
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo: str = Field(..., description="Periodo YYYYMM")
    tipo_envio: str = Field(default="PROPUESTA", description="PROPUESTA, DEFINITIVO")
    
    # Opciones de envío
    confirmar_envio: bool = Field(default=False, description="Confirmar envío definitivo")
    observaciones_envio: Optional[str] = Field(None, description="Observaciones del envío")


class RceConsultaRequest(BaseModel):
    """Request para consultar comprobantes RCE"""
    ruc: str = Field(..., description="RUC del contribuyente")
    
    # Filtros básicos
    periodo: Optional[str] = Field(None, description="Periodo YYYYMM")
    periodo_inicio: Optional[str] = Field(None, description="Periodo inicio")
    periodo_fin: Optional[str] = Field(None, description="Periodo fin")
    
    # Filtros de comprobante
    tipo_comprobante: Optional[List[RceTipoComprobante]] = Field(None)
    serie: Optional[str] = Field(None)
    numero: Optional[str] = Field(None)
    numero_documento_proveedor: Optional[str] = Field(None)
    
    # Filtros de fecha
    fecha_emision_inicio: Optional[date] = Field(None)
    fecha_emision_fin: Optional[date] = Field(None)
    
    # Filtros específicos
    solo_con_credito_fiscal: Optional[bool] = Field(None)
    con_detraccion: Optional[bool] = Field(None)
    estado: Optional[str] = Field(None)
    
    # Paginación
    pagina: int = Field(default=1, ge=1)
    registros_por_pagina: int = Field(default=100, ge=1, le=1000)


class RceDescargaMasivaRequest(BaseModel):
    """Request para descarga masiva RCE"""
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo_inicio: str = Field(..., description="Periodo inicio YYYYMM")
    periodo_fin: str = Field(..., description="Periodo fin YYYYMM")
    
    # Filtros de descarga
    tipo_comprobante: Optional[List[RceTipoComprobante]] = Field(None)
    formato: str = Field(default="TXT", description="TXT, EXCEL")
    solo_con_credito_fiscal: Optional[bool] = Field(None)
    incluir_anulados: bool = Field(default=False)
    
    # Opciones de contenido
    incluir_detalle: bool = Field(default=True)
    incluir_resumen: bool = Field(default=True)
    incluir_inconsistencias: bool = Field(default=False)


class RceTicketConsultaRequest(BaseModel):
    """Request para consultar ticket RCE"""
    ticket_id: str = Field(..., description="ID del ticket")
    incluir_detalle: bool = Field(default=True, description="Incluir detalle del proceso")


class RceConsultaAvanzadaRequest(BaseModel):
    """Request para consulta avanzada RCE"""
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo: str = Field(..., description="Periodo YYYYMM", pattern=r"^\d{6}$")
    
    # Filtros opcionales
    tipo_comprobante: Optional[List[RceTipoComprobante]] = Field(None, description="Tipos de comprobante")
    estado_comprobante: Optional[List[str]] = Field(None, description="Estados de comprobante")
    fecha_inicio: Optional[date] = Field(None, description="Fecha inicio")
    fecha_fin: Optional[date] = Field(None, description="Fecha fin")
    proveedor_ruc: Optional[str] = Field(None, description="RUC del proveedor")
    numero_serie: Optional[str] = Field(None, description="Serie del comprobante")
    numero_documento: Optional[str] = Field(None, description="Número del documento")
    
    # Opciones de consulta
    incluir_detalle: bool = Field(default=True, description="Incluir detalle de comprobantes")
    incluir_inconsistencias: bool = Field(default=False, description="Incluir inconsistencias")
    limite: int = Field(default=100, ge=1, le=1000, description="Límite de resultados")
    offset: int = Field(default=0, ge=0, description="Desplazamiento")


class RceReporteRequest(BaseModel):
    """Request para generar reportes RCE"""
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo: str = Field(..., description="Periodo YYYYMM", pattern=r"^\d{6}$")
    tipo_reporte: str = Field(..., description="Tipo de reporte: RESUMEN, DETALLADO, INCONSISTENCIAS")
    
    # Filtros opcionales
    fecha_inicio: Optional[date] = Field(None, description="Fecha inicio")
    fecha_fin: Optional[date] = Field(None, description="Fecha fin")
    tipo_comprobante: Optional[List[RceTipoComprobante]] = Field(None, description="Tipos de comprobante")
    estado_comprobante: Optional[List[str]] = Field(None, description="Estados de comprobante")
    
    # Opciones de formato
    formato: str = Field(default="EXCEL", description="Formato: EXCEL, CSV, PDF")
    incluir_graficos: bool = Field(default=False, description="Incluir gráficos en reporte")
    agrupar_por: Optional[str] = Field(None, description="Agrupar por: TIPO, PROVEEDOR, FECHA")


class RceResumenRequest(BaseModel):
    """Request para obtener resumen RCE"""
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo: str = Field(..., description="Periodo YYYYMM", pattern=r"^\d{6}$")
    
    # Opciones de resumen
    incluir_estadisticas: bool = Field(default=True, description="Incluir estadísticas generales")
    incluir_comparativo: bool = Field(default=False, description="Incluir comparativo con periodo anterior")
    incluir_tendencias: bool = Field(default=False, description="Incluir análisis de tendencias")
    agrupar_por_tipo: bool = Field(default=True, description="Agrupar por tipo de comprobante")
    agrupar_por_estado: bool = Field(default=True, description="Agrupar por estado")


# =======================================
# SCHEMAS DE RESPONSE (OUTPUT)
# =======================================

class RceComprobanteResponse(BaseModel):
    """Response de comprobante RCE"""
    # Campos del modelo completo (para response)
    periodo: str
    correlativo: str
    fecha_emision: date
    fecha_vencimiento: Optional[date]
    
    tipo_comprobante: RceTipoComprobante
    serie: str
    numero: str
    
    # Proveedor
    tipo_documento_proveedor: RceTipoDocumento
    numero_documento_proveedor: str
    razon_social_proveedor: str
    
    # Montos
    moneda: RceMoneda
    tipo_cambio: Optional[Decimal]
    base_imponible_operaciones_gravadas: Decimal
    igv: Decimal
    importe_total: Decimal
    
    # Estado y control
    sustenta_credito_fiscal: bool
    estado: str
    fecha_registro: datetime
    observaciones: Optional[str]
    
    # Campos calculados/adicionales para response
    credito_fiscal_calculado: Optional[Decimal] = Field(None, description="Crédito fiscal calculado")
    monto_detraccion: Optional[Decimal] = Field(None, description="Monto detraído")
    
    class Config:
        from_attributes = True


class RcePropuestaResponse(BaseModel):
    """Response de propuesta RCE"""
    ruc: str
    periodo: str
    estado: RceEstadoProceso
    
    # Información de generación
    fecha_generacion: datetime
    correlativo_propuesta: Optional[str]
    
    # Estadísticas
    cantidad_comprobantes: int
    total_importe: Decimal
    total_igv: Decimal
    total_credito_fiscal: Decimal
    
    # Control
    ticket_id: Optional[str]
    numero_orden: Optional[str]
    fecha_aceptacion: Optional[datetime]
    
    # Archivos
    archivos_disponibles: List[str] = Field(default_factory=list)
    observaciones_sunat: Optional[str]
    
    class Config:
        from_attributes = True


class RceProcesoResponse(BaseModel):
    """Response de proceso RCE"""
    ruc: str
    periodo: str
    operacion: str
    estado: RceEstadoProceso
    
    # Resultado
    exitoso: bool
    codigo_respuesta: Optional[str]
    mensaje: str
    
    # Control
    ticket_id: Optional[str]
    numero_orden: Optional[str]
    
    # Estadísticas
    comprobantes_procesados: int = Field(default=0)
    comprobantes_aceptados: int = Field(default=0)
    comprobantes_rechazados: int = Field(default=0)
    
    # Totales
    total_credito_fiscal: Optional[Decimal]
    total_importe_procesado: Optional[Decimal]
    
    # Tiempo
    fecha_inicio: datetime
    fecha_fin: Optional[datetime]
    tiempo_procesamiento_segundos: Optional[int]
    
    # Errores
    inconsistencias_criticas: int = Field(default=0)
    errores_criticos: List[str] = Field(default_factory=list)
    archivos_respuesta: List[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class RceConsultaResponse(BaseModel):
    """Response de consulta RCE con paginación"""
    comprobantes: List[RceComprobanteResponse] = Field(default_factory=list)
    
    # Información de paginación
    total_registros: int = Field(default=0)
    total_paginas: int = Field(default=0)
    pagina_actual: int = Field(default=1)
    registros_por_pagina: int = Field(default=100)
    
    # Totales de la consulta
    total_importe: Decimal = Field(default=Decimal("0.00"))
    total_igv: Decimal = Field(default=Decimal("0.00"))
    total_credito_fiscal: Decimal = Field(default=Decimal("0.00"))
    
    # Resumen por tipo
    resumen_por_tipo: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Metadatos
    fecha_consulta: datetime = Field(default_factory=datetime.utcnow)
    filtros_aplicados: Dict[str, Any] = Field(default_factory=dict)


class RceResumenResponse(BaseModel):
    """Response de resumen consolidado RCE"""
    ruc: str
    periodo: str
    estado_periodo: RceEstadoProceso
    fecha_generacion: datetime
    
    # Totales generales
    total_comprobantes: int
    total_proveedores: int
    total_importe: Decimal
    total_igv: Decimal
    total_credito_fiscal: Decimal
    
    # Distribución por tipo de comprobante
    resumen_por_tipo: Dict[str, Dict[str, Any]]
    
    # Análisis adicional
    porcentaje_credito_fiscal: Optional[Decimal]
    comparacion_periodo_anterior: Optional[Dict[str, Decimal]]
    
    # Archivos disponibles
    archivos_disponibles: List[str] = Field(default_factory=list)


class RceTicketResponse(BaseModel):
    """Response de consulta de ticket RCE"""
    ticket_id: str
    estado: str
    descripcion_estado: Optional[str]
    
    # Progreso
    porcentaje_avance: Optional[int]
    fecha_inicio: Optional[datetime]
    fecha_estimada_fin: Optional[datetime]
    fecha_vencimiento: Optional[datetime]
    
    # Resultados
    resultados_disponibles: bool
    archivos_disponibles: List[str] = Field(default_factory=list)
    url_descarga: Optional[str]
    
    # Información del proceso
    comprobantes_procesados: Optional[int]
    errores_encontrados: Optional[int]
    mensaje_usuario: Optional[str]
    observaciones: Optional[str]


class RceInconsistenciaResponse(BaseModel):
    """Response de inconsistencia RCE"""
    linea: int
    correlativo: Optional[str]
    campo: str
    codigo_error: str
    descripcion_error: str
    valor_encontrado: str
    valor_esperado: Optional[str]
    
    tipo_error: str
    severidad: str
    afecta_credito_fiscal: bool
    requiere_correccion: bool
    
    accion_recomendada: Optional[str]
    referencia_manual: Optional[str]
    
    class Config:
        from_attributes = True


# =======================================
# SCHEMAS DE RESPUESTA ESTÁNDAR
# =======================================

class RceApiResponse(BaseModel):
    """Response estándar para operaciones RCE"""
    exitoso: bool = Field(..., description="Indica si la operación fue exitosa")
    mensaje: str = Field(..., description="Mensaje descriptivo")
    codigo: Optional[str] = Field(None, description="Código de respuesta")
    
    # Datos específicos según la operación
    datos: Optional[Union[
        RceComprobanteResponse,
        RcePropuestaResponse,
        RceProcesoResponse,
        RceConsultaResponse,
        RceResumenResponse,
        RceTicketResponse,
        List[RceInconsistenciaResponse]
    ]] = Field(None, description="Datos de respuesta")
    
    # Metadatos
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version_api: str = Field(default="v27.0")


class RceErrorResponse(BaseModel):
    """Response de error para operaciones RCE"""
    exitoso: bool = Field(default=False)
    error: str = Field(..., description="Tipo de error")
    mensaje: str = Field(..., description="Mensaje de error")
    codigo_error: Optional[str] = Field(None, description="Código de error")
    
    # Detalles adicionales
    detalles: Optional[List[str]] = Field(None, description="Detalles del error")
    sugerencias: Optional[List[str]] = Field(None, description="Sugerencias de solución")
    
    # Contexto
    operacion: Optional[str] = Field(None, description="Operación que falló")
    parametros: Optional[Dict[str, Any]] = Field(None, description="Parámetros que causaron el error")
    
    # Metadatos
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: Optional[str] = Field(None, description="ID de trazabilidad")


# =======================================
# UTILITIES DE VALIDACIÓN
# =======================================

class RceValidationUtils:
    """Utilidades de validación para RCE"""
    
    @staticmethod
    def validate_periodo(periodo: str) -> str:
        """Validar formato de periodo YYYYMM"""
        if not periodo or len(periodo) != 6 or not periodo.isdigit():
            raise ValueError('Periodo debe tener formato YYYYMM')
        
        año = int(periodo[:4])
        mes = int(periodo[4:])
        
        if año < 2000 or año > 2050:
            raise ValueError('Año debe estar entre 2000 y 2050')
        
        if mes < 1 or mes > 12:
            raise ValueError('Mes debe estar entre 01 y 12')
        
        return periodo
    
    @staticmethod
    def validate_importe_total(importe: Optional[Decimal]) -> Optional[Decimal]:
        """Validar importe total"""
        if importe is not None and importe < 0:
            raise ValueError('Importe total no puede ser negativo')
        return importe
    
    @staticmethod
    def validate_numero_documento(numero: str, tipo: RceTipoDocumento) -> str:
        """Validar número de documento según tipo"""
        if tipo == RceTipoDocumento.RUC:
            if not numero or len(numero) != 11 or not numero.isdigit():
                raise ValueError('RUC debe tener 11 dígitos')
        
        elif tipo == RceTipoDocumento.DNI:
            if not numero or len(numero) != 8 or not numero.isdigit():
                raise ValueError('DNI debe tener 8 dígitos')
        
        return numero


# =======================================
# SCHEMAS PARA COMPROBANTES DETALLADOS
# =======================================

class RceComprobanteDetallado(BaseModel):
    """Comprobante detallado desde propuesta SUNAT"""
    # Información del proveedor
    ruc_proveedor: str = Field(..., description="RUC del proveedor")
    razon_social_proveedor: str = Field(..., description="Razón social del proveedor")
    
    # Información del comprobante
    tipo_documento: str = Field(..., description="Tipo de documento")
    serie_comprobante: str = Field(..., description="Serie del comprobante")
    numero_comprobante: str = Field(..., description="Número del comprobante")
    fecha_emision: str = Field(..., description="Fecha de emisión")
    fecha_vencimiento: Optional[str] = Field(None, description="Fecha de vencimiento")
    
    # Montos
    moneda: str = Field(..., description="Código de moneda")
    tipo_cambio: Optional[Decimal] = Field(None, description="Tipo de cambio")
    base_imponible_gravada: Decimal = Field(default=Decimal("0.00"), description="Base imponible gravada")
    igv: Decimal = Field(default=Decimal("0.00"), description="IGV")
    valor_adquisicion_no_gravada: Decimal = Field(default=Decimal("0.00"), description="Valor adquisición no gravada")
    isc: Decimal = Field(default=Decimal("0.00"), description="ISC")
    icbper: Decimal = Field(default=Decimal("0.00"), description="ICBPER")
    otros_tributos: Decimal = Field(default=Decimal("0.00"), description="Otros tributos")
    importe_total: Decimal = Field(..., description="Importe total")
    
    # Información adicional
    periodo: str = Field(..., description="Período tributario")
    car_sunat: Optional[str] = Field(None, description="CAR SUNAT")
    numero_dua: Optional[str] = Field(None, description="Número DUA")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)  # Convertir Decimal a float para JSON
        }


class RceComprobantesDetalladosResponse(BaseModel):
    """Response para lista de comprobantes detallados"""
    exitoso: bool = Field(..., description="Operación exitosa")
    mensaje: str = Field(..., description="Mensaje descriptivo")
    total_comprobantes: int = Field(..., description="Total de comprobantes")
    periodo: str = Field(..., description="Período consultado")
    ruc: str = Field(..., description="RUC consultado")
    comprobantes: List[RceComprobanteDetallado] = Field(..., description="Lista de comprobantes detallados")
    
    # Totales agregados
    total_base_imponible: Decimal = Field(default=Decimal("0.00"), description="Total base imponible")
    total_igv: Decimal = Field(default=Decimal("0.00"), description="Total IGV")
    total_general: Decimal = Field(default=Decimal("0.00"), description="Total general")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }
