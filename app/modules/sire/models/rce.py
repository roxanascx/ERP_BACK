"""
Modelos RCE - Registro de Compras Electrónico
Basado en Manual SUNAT SIRE Compras v27.0
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from enum import Enum


class RceEstadoProceso(str, Enum):
    """Estados del proceso RCE según manual v27.0"""
    PENDIENTE = "PENDIENTE"
    PROPUESTA = "PROPUESTA"
    ACEPTADO = "ACEPTADO"
    PRELIMINAR = "PRELIMINAR"
    FINALIZADO = "FINALIZADO"
    ERROR = "ERROR"
    CANCELADO = "CANCELADO"


class RceEstadoComprobante(str, Enum):
    """Estados de comprobante RCE según manual v27.0"""
    VALIDO = "VALIDO"
    OBSERVADO = "OBSERVADO"
    RECHAZADO = "RECHAZADO"
    ANULADO = "ANULADO"
    PENDIENTE = "PENDIENTE"
    PROCESADO = "PROCESADO"


class RceTipoComprobante(str, Enum):
    """Tipos de comprobante RCE según tabla 10 SUNAT"""
    FACTURA = "01"
    BOLETA = "03"
    NOTA_CREDITO = "07"
    NOTA_DEBITO = "08"
    GUIA_REMISION = "09"
    RECIBO_HONORARIOS = "12"
    BOLETO_TRANSPORTE_PASAJEROS = "13"
    BOLETO_VIAJE_TRANSPORTE_PUBLICO = "16"
    DOCUMENTO_RETENCION = "20"
    COMPROBANTE_NO_DOMICILIADO = "91"
    OTROS_DOCUMENTOS = "99"


class RceTipoDocumento(str, Enum):
    """Tipos de documento de identidad según tabla 2 SUNAT"""
    DOC_TRIB_NO_DOM_SIN_RUC = "0"
    DNI = "1"
    CARNET_EXTRANJERIA = "4"
    RUC = "6"
    PASAPORTE = "7"
    CEDULA_DIPLOMATICA = "A"


class RceMoneda(str, Enum):
    """Códigos de moneda según ISO 4217"""
    PEN = "PEN"  # Soles
    USD = "USD"  # Dólares
    EUR = "EUR"  # Euros


class RceDetraccion(BaseModel):
    """Detalle de detracción"""
    sujeto_detraccion: bool = Field(default=False, description="Sujeto a detracción")
    porcentaje: Optional[Decimal] = Field(None, description="Porcentaje de detracción")
    monto: Optional[Decimal] = Field(None, description="Monto detraído")
    bien_servicio: Optional[str] = Field(None, description="Código bien/servicio")
    numero_operacion: Optional[str] = Field(None, description="Número de operación")
    fecha_deposito: Optional[date] = Field(None, description="Fecha de depósito")


class RceRetencion(BaseModel):
    """Detalle de retención"""
    sujeto_retencion: bool = Field(default=False, description="Sujeto a retención")
    porcentaje: Optional[Decimal] = Field(None, description="Porcentaje de retención")
    monto: Optional[Decimal] = Field(None, description="Monto retenido")
    regimen: Optional[str] = Field(None, description="Régimen de retención")


class RcePercepcion(BaseModel):
    """Detalle de percepción"""
    sujeto_percepcion: bool = Field(default=False, description="Sujeto a percepción")
    porcentaje: Optional[Decimal] = Field(None, description="Porcentaje de percepción")
    monto: Optional[Decimal] = Field(None, description="Monto percibido")
    regimen: Optional[str] = Field(None, description="Régimen de percepción")


class RceProveedor(BaseModel):
    """Información del proveedor"""
    tipo_documento: RceTipoDocumento = Field(..., description="Tipo de documento")
    numero_documento: str = Field(..., description="Número de documento")
    razon_social: str = Field(..., description="Razón social o nombre")
    apellido_paterno: Optional[str] = Field(None, description="Apellido paterno (persona natural)")
    apellido_materno: Optional[str] = Field(None, description="Apellido materno (persona natural)")
    nombres: Optional[str] = Field(None, description="Nombres (persona natural)")
    es_no_domiciliado: bool = Field(default=False, description="Es no domiciliado")
    pais_residencia: Optional[str] = Field(None, description="País de residencia (no domiciliado)")


class RceGuiaRemision(BaseModel):
    """Información de guía de remisión"""
    serie: str = Field(..., description="Serie de la guía")
    numero: str = Field(..., description="Número de la guía")
    tipo_documento_emisor: RceTipoDocumento = Field(..., description="Tipo documento emisor")
    numero_documento_emisor: str = Field(..., description="Número documento emisor")


class RceComprobante(BaseModel):
    """Modelo de comprobante RCE según manual v27.0"""
    # Campos obligatorios básicos
    periodo: str = Field(..., description="Periodo YYYYMM", pattern=r"^\d{6}$")
    correlativo: str = Field(..., description="Número correlativo único")
    fecha_emision: date = Field(..., description="Fecha de emisión")
    fecha_vencimiento: Optional[date] = Field(None, description="Fecha de vencimiento")
    
    # Tipo de comprobante
    tipo_comprobante: RceTipoComprobante = Field(..., description="Tipo de comprobante")
    serie: str = Field(..., description="Serie del comprobante")
    numero: str = Field(..., description="Número del comprobante")
    numero_final: Optional[str] = Field(None, description="Número final (rango)")
    
    # Información del proveedor
    proveedor: RceProveedor = Field(..., description="Datos del proveedor")
    
    # Información del adquiriente (nosotros)
    tipo_documento_adquiriente: RceTipoDocumento = Field(default=RceTipoDocumento.RUC)
    numero_documento_adquiriente: str = Field(..., description="RUC del adquiriente")
    
    # Montos en moneda original
    moneda: RceMoneda = Field(default=RceMoneda.PEN, description="Código de moneda")
    tipo_cambio: Optional[Decimal] = Field(None, description="Tipo de cambio a soles")
    
    # Valores y tributos
    base_imponible_operaciones_gravadas: Decimal = Field(default=Decimal("0.00"))
    base_imponible_operaciones_gravadas_con_derecho: Decimal = Field(default=Decimal("0.00"))
    base_imponible_operaciones_gravadas_sin_derecho: Decimal = Field(default=Decimal("0.00"))
    base_imponible_operaciones_no_gravadas: Decimal = Field(default=Decimal("0.00"))
    base_imponible_operaciones_exoneradas: Decimal = Field(default=Decimal("0.00"))
    base_imponible_operaciones_inafectas: Decimal = Field(default=Decimal("0.00"))
    
    # IGV e impuestos
    igv: Decimal = Field(default=Decimal("0.00"), description="IGV")
    igv_no_domiciliado: Decimal = Field(default=Decimal("0.00"), description="IGV no domiciliado")
    impuesto_consumo: Decimal = Field(default=Decimal("0.00"), description="Impuesto al consumo")
    otros_tributos: Decimal = Field(default=Decimal("0.00"), description="Otros tributos/cargos")
    importe_total: Decimal = Field(..., description="Importe total del comprobante")
    
    # Información adicional
    clasifica_gasto: Optional[str] = Field(None, description="Clasificación del gasto")
    sustenta_costo_gasto: bool = Field(default=True, description="Sustenta costo o gasto")
    sustenta_credito_fiscal: bool = Field(default=True, description="Sustenta crédito fiscal")
    
    # Detracción, retención y percepción
    detraccion: Optional[RceDetraccion] = Field(None, description="Información de detracción")
    retencion: Optional[RceRetencion] = Field(None, description="Información de retención")
    percepcion: Optional[RcePercepcion] = Field(None, description="Información de percepción")
    
    # Guías de remisión asociadas
    guias_remision: List[RceGuiaRemision] = Field(default_factory=list, description="Guías asociadas")
    
    # Referencia a otros documentos
    tipo_comprobante_modificado: Optional[RceTipoComprobante] = Field(None, description="Tipo doc. modificado")
    serie_comprobante_modificado: Optional[str] = Field(None, description="Serie doc. modificado")
    numero_comprobante_modificado: Optional[str] = Field(None, description="Número doc. modificado")
    fecha_comprobante_modificado: Optional[date] = Field(None, description="Fecha doc. modificado")
    
    # Estado y control
    estado: str = Field(default="RECIBIDO", description="Estado del comprobante")
    fecha_registro: datetime = Field(default_factory=datetime.utcnow)
    observaciones: Optional[str] = Field(None, description="Observaciones")
    
    @validator('periodo')
    def validate_periodo(cls, v):
        if not v or len(v) != 6 or not v.isdigit():
            raise ValueError('Periodo debe tener formato YYYYMM')
        return v
    
    @validator('importe_total')
    def validate_importe_total(cls, v, values):
        # Validar que el importe total sea coherente con los subtotales
        if v < 0:
            raise ValueError('Importe total no puede ser negativo')
        return v



class RcePropuesta(BaseModel):
    """Propuesta RCE de SUNAT según manual v27.0"""
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo: str = Field(..., description="Periodo YYYYMM", pattern=r"^\d{6}$")
    estado: RceEstadoProceso = Field(default=RceEstadoProceso.PROPUESTA)
    
    # Información de generación
    fecha_generacion: datetime = Field(..., description="Fecha de generación")
    correlativo_propuesta: Optional[str] = Field(None, description="Correlativo de la propuesta")
    
    # Estadísticas de comprobantes
    cantidad_comprobantes: int = Field(..., description="Cantidad total de comprobantes")
    cantidad_facturas: int = Field(default=0)
    cantidad_boletas: int = Field(default=0)
    cantidad_notas_credito: int = Field(default=0)
    cantidad_notas_debito: int = Field(default=0)
    cantidad_otros: int = Field(default=0)
    
    # Totales en soles
    total_base_imponible_gravada: Decimal = Field(default=Decimal("0.00"))
    total_base_imponible_gravada_con_derecho: Decimal = Field(default=Decimal("0.00"))
    total_base_imponible_gravada_sin_derecho: Decimal = Field(default=Decimal("0.00"))
    total_base_imponible_no_gravada: Decimal = Field(default=Decimal("0.00"))
    total_base_imponible_exonerada: Decimal = Field(default=Decimal("0.00"))
    total_base_imponible_inafecta: Decimal = Field(default=Decimal("0.00"))
    
    total_igv: Decimal = Field(default=Decimal("0.00"))
    total_igv_no_domiciliado: Decimal = Field(default=Decimal("0.00"))
    total_impuesto_consumo: Decimal = Field(default=Decimal("0.00"))
    total_otros_tributos: Decimal = Field(default=Decimal("0.00"))
    total_importe: Decimal = Field(..., description="Total general")
    
    # Totales específicos RCE
    total_credito_fiscal: Decimal = Field(default=Decimal("0.00"))
    total_detraccion: Decimal = Field(default=Decimal("0.00"))
    total_retencion: Decimal = Field(default=Decimal("0.00"))
    total_percepcion: Decimal = Field(default=Decimal("0.00"))
    
    # Comprobantes de la propuesta
    comprobantes: List[RceComprobante] = Field(default_factory=list)
    
    # Archivos asociados
    archivo_propuesta_txt: Optional[str] = Field(None, description="Archivo propuesta .txt")
    archivo_propuesta_excel: Optional[str] = Field(None, description="Archivo propuesta .xlsx")
    archivo_inconsistencias: Optional[str] = Field(None, description="Archivo inconsistencias")
    archivo_resumen: Optional[str] = Field(None, description="Archivo resumen")
    
    # Control y seguimiento
    ticket_id: Optional[str] = Field(None, description="ID del ticket SUNAT")
    numero_orden: Optional[str] = Field(None, description="Número de orden SUNAT")
    fecha_aceptacion: Optional[datetime] = Field(None, description="Fecha de aceptación")
    fecha_rechazo: Optional[datetime] = Field(None, description="Fecha de rechazo")
    fecha_actualizacion: datetime = Field(default_factory=datetime.utcnow)
    
    # Observaciones de SUNAT
    observaciones_sunat: Optional[str] = Field(None, description="Observaciones de SUNAT")
    motivo_rechazo: Optional[str] = Field(None, description="Motivo de rechazo")


class RceInconsistencia(BaseModel):
    """Inconsistencia encontrada en RCE según manual v27.0"""
    # Identificación del registro
    linea: int = Field(..., description="Número de línea en archivo")
    correlativo: Optional[str] = Field(None, description="Correlativo del comprobante")
    
    # Detalle del error
    campo: str = Field(..., description="Campo con inconsistencia")
    codigo_error: str = Field(..., description="Código de error SUNAT")
    descripcion_error: str = Field(..., description="Descripción del error")
    valor_encontrado: str = Field(..., description="Valor encontrado")
    valor_esperado: Optional[str] = Field(None, description="Valor esperado")
    
    # Clasificación
    tipo_error: str = Field(..., description="Tipo de error: CRITICO, ADVERTENCIA")
    severidad: str = Field(default="ERROR", description="Severidad: ERROR, WARNING, INFO")
    categoria: Optional[str] = Field(None, description="Categoría del error")
    
    # Impacto
    afecta_credito_fiscal: bool = Field(default=False, description="Afecta crédito fiscal")
    afecta_procesamiento: bool = Field(default=True, description="Impide procesamiento")
    requiere_correccion: bool = Field(default=True, description="Requiere corrección")
    
    # Sugerencias
    accion_recomendada: Optional[str] = Field(None, description="Acción recomendada")
    referencia_manual: Optional[str] = Field(None, description="Referencia al manual")


class RceResumenConsolidado(BaseModel):
    """Resumen consolidado RCE por periodo"""
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo: str = Field(..., description="Periodo YYYYMM")
    fecha_generacion: datetime = Field(..., description="Fecha de generación")
    estado_periodo: RceEstadoProceso = Field(..., description="Estado del periodo")
    
    # Resumen por tipo de comprobante
    resumen_por_tipo: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Totales generales
    total_comprobantes: int = Field(default=0)
    total_proveedores: int = Field(default=0)
    
    # Bases imponibles
    total_base_imponible_gravada: Decimal = Field(default=Decimal("0.00"))
    total_base_imponible_gravada_con_derecho: Decimal = Field(default=Decimal("0.00"))
    total_base_imponible_gravada_sin_derecho: Decimal = Field(default=Decimal("0.00"))
    total_base_imponible_no_gravada: Decimal = Field(default=Decimal("0.00"))
    total_base_imponible_exonerada: Decimal = Field(default=Decimal("0.00"))
    total_base_imponible_inafecta: Decimal = Field(default=Decimal("0.00"))
    
    # Tributos
    total_igv: Decimal = Field(default=Decimal("0.00"))
    total_igv_no_domiciliado: Decimal = Field(default=Decimal("0.00"))
    total_impuesto_consumo: Decimal = Field(default=Decimal("0.00"))
    total_otros_tributos: Decimal = Field(default=Decimal("0.00"))
    total_importe: Decimal = Field(default=Decimal("0.00"))
    
    # Específicos RCE
    total_credito_fiscal: Decimal = Field(default=Decimal("0.00"))
    total_credito_fiscal_utilizable: Decimal = Field(default=Decimal("0.00"))
    total_detraccion: Decimal = Field(default=Decimal("0.00"))
    total_retencion: Decimal = Field(default=Decimal("0.00"))
    total_percepcion: Decimal = Field(default=Decimal("0.00"))
    
    # Análisis adicional
    porcentaje_credito_fiscal: Optional[Decimal] = Field(None, description="% crédito fiscal/IGV")
    variacion_periodo_anterior: Optional[Decimal] = Field(None, description="Variación vs periodo anterior")


class RceProcesoResult(BaseModel):
    """Resultado de proceso RCE según respuestas API v27.0"""
    # Identificación
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo: str = Field(..., description="Periodo procesado")
    operacion: str = Field(..., description="Operación realizada")
    
    # Estado del proceso
    estado: RceEstadoProceso = Field(..., description="Estado del proceso")
    exitoso: bool = Field(..., description="Si el proceso fue exitoso")
    codigo_respuesta: Optional[str] = Field(None, description="Código de respuesta SUNAT")
    mensaje: str = Field(..., description="Mensaje del resultado")
    descripcion_detallada: Optional[str] = Field(None, description="Descripción detallada")
    
    # Control de tickets
    ticket_id: Optional[str] = Field(None, description="ID del ticket generado")
    numero_orden: Optional[str] = Field(None, description="Número de orden SUNAT")
    estado_ticket: Optional[str] = Field(None, description="Estado del ticket")
    
    # Estadísticas de procesamiento
    comprobantes_enviados: int = Field(default=0)
    comprobantes_procesados: int = Field(default=0)
    comprobantes_aceptados: int = Field(default=0)
    comprobantes_rechazados: int = Field(default=0)
    comprobantes_con_observaciones: int = Field(default=0)
    
    # Totales financieros
    total_credito_fiscal: Optional[Decimal] = Field(None)
    total_detraccion: Optional[Decimal] = Field(None)
    total_retencion: Optional[Decimal] = Field(None)
    total_importe_procesado: Optional[Decimal] = Field(None)
    
    # Errores e inconsistencias
    inconsistencias: List[RceInconsistencia] = Field(default_factory=list)
    errores_criticos: List[str] = Field(default_factory=list)
    advertencias: List[str] = Field(default_factory=list)
    
    # Archivos generados
    archivos_respuesta: List[str] = Field(default_factory=list)
    url_descarga: Optional[str] = Field(None, description="URL de descarga (si aplica)")
    
    # Metadatos de tiempo
    fecha_inicio: datetime = Field(default_factory=datetime.utcnow)
    fecha_fin: Optional[datetime] = Field(None)
    tiempo_procesamiento_segundos: Optional[int] = Field(None)
    fecha_vencimiento_ticket: Optional[datetime] = Field(None)


class RceTicketConsulta(BaseModel):
    """Consulta de estado de ticket RCE"""
    ticket_id: str = Field(..., description="ID del ticket")
    estado: str = Field(..., description="Estado del ticket")
    descripcion_estado: Optional[str] = Field(None, description="Descripción del estado")
    
    # Progreso
    porcentaje_avance: Optional[int] = Field(None, description="Porcentaje de avance (0-100)")
    fecha_inicio: Optional[datetime] = Field(None, description="Fecha de inicio del proceso")
    fecha_estimada_fin: Optional[datetime] = Field(None, description="Fecha estimada de finalización")
    fecha_vencimiento: Optional[datetime] = Field(None, description="Fecha de vencimiento")
    
    # Resultados disponibles
    archivos_disponibles: List[str] = Field(default_factory=list)
    resultados_disponibles: bool = Field(default=False)
    url_descarga: Optional[str] = Field(None, description="URL de descarga")
    
    # Información adicional
    mensaje_usuario: Optional[str] = Field(None, description="Mensaje para el usuario")
    observaciones: Optional[str] = Field(None, description="Observaciones del proceso")


class RceDescargaMasiva(BaseModel):
    """Solicitud de descarga masiva RCE"""
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo_inicio: str = Field(..., description="Periodo inicio YYYYMM")
    periodo_fin: str = Field(..., description="Periodo fin YYYYMM")
    
    # Filtros de descarga
    tipo_comprobante: Optional[List[RceTipoComprobante]] = Field(None, description="Tipos de comprobante")
    solo_con_credito_fiscal: Optional[bool] = Field(None, description="Solo con derecho a crédito fiscal")
    incluir_anulados: bool = Field(default=False, description="Incluir comprobantes anulados")
    
    # Formato de descarga
    formato: str = Field(default="TXT", description="Formato: TXT, EXCEL")
    incluir_detalle: bool = Field(default=True, description="Incluir detalle de comprobantes")
    incluir_resumen: bool = Field(default=True, description="Incluir resumen consolidado")
    
    # Control
    ticket_generado: Optional[str] = Field(None, description="Ticket generado")
    fecha_solicitud: datetime = Field(default_factory=datetime.utcnow)
    estado_solicitud: str = Field(default="SOLICITADO")


class RceConsultaAvanzada(BaseModel):
    """Parámetros para consulta avanzada de comprobantes RCE"""
    ruc: str = Field(..., description="RUC del contribuyente")
    
    # Filtros de periodo
    periodo_inicio: Optional[str] = Field(None, description="Periodo inicio YYYYMM")
    periodo_fin: Optional[str] = Field(None, description="Periodo fin YYYYMM")
    fecha_emision_inicio: Optional[date] = Field(None, description="Fecha emisión desde")
    fecha_emision_fin: Optional[date] = Field(None, description="Fecha emisión hasta")
    
    # Filtros de comprobante
    tipo_comprobante: Optional[List[RceTipoComprobante]] = Field(None)
    serie: Optional[str] = Field(None, description="Serie específica")
    numero_inicio: Optional[str] = Field(None, description="Número desde")
    numero_fin: Optional[str] = Field(None, description="Número hasta")
    
    # Filtros de proveedor
    tipo_documento_proveedor: Optional[RceTipoDocumento] = Field(None)
    numero_documento_proveedor: Optional[str] = Field(None)
    razon_social_proveedor: Optional[str] = Field(None)
    
    # Filtros de montos
    monto_minimo: Optional[Decimal] = Field(None, description="Importe mínimo")
    monto_maximo: Optional[Decimal] = Field(None, description="Importe máximo")
    moneda: Optional[RceMoneda] = Field(None)
    
    # Filtros específicos RCE
    solo_con_credito_fiscal: Optional[bool] = Field(None)
    con_detraccion: Optional[bool] = Field(None)
    con_retencion: Optional[bool] = Field(None)
    con_percepcion: Optional[bool] = Field(None)
    
    # Paginación
    pagina: int = Field(default=1, ge=1)
    registros_por_pagina: int = Field(default=100, ge=1, le=1000)
    
    # Ordenamiento
    campo_orden: str = Field(default="fecha_emision")
    orden_descendente: bool = Field(default=True)


# ========================================
# MODELOS DE RESUMEN Y ESTADÍSTICAS
# ========================================

class RceResumen(BaseModel):
    """Resumen estadístico del RCE"""
    # Información del periodo
    ruc: str = Field(..., description="RUC del contribuyente")
    periodo: str = Field(..., description="Periodo YYYYMM")
    
    # Contadores
    total_comprobantes: int = Field(default=0, description="Total de comprobantes")
    total_validados: int = Field(default=0, description="Comprobantes validados")
    total_observados: int = Field(default=0, description="Comprobantes observados")
    total_rechazados: int = Field(default=0, description="Comprobantes rechazados")
    
    # Importes
    importe_total: Decimal = Field(default=Decimal("0.00"), description="Importe total")
    importe_validado: Decimal = Field(default=Decimal("0.00"), description="Importe validado")
    importe_observado: Decimal = Field(default=Decimal("0.00"), description="Importe observado")
    importe_rechazado: Decimal = Field(default=Decimal("0.00"), description="Importe rechazado")
    
    # IGV
    igv_total: Decimal = Field(default=Decimal("0.00"), description="IGV total")
    igv_no_gravado: Decimal = Field(default=Decimal("0.00"), description="IGV no gravado")
    igv_exonerado: Decimal = Field(default=Decimal("0.00"), description="IGV exonerado")
    
    # Detracciones y retenciones
    detraccion_total: Decimal = Field(default=Decimal("0.00"), description="Total detracciones")
    retencion_total: Decimal = Field(default=Decimal("0.00"), description="Total retenciones")
    percepcion_total: Decimal = Field(default=Decimal("0.00"), description="Total percepciones")
    
    # Metadatos
    fecha_generacion: datetime = Field(default_factory=datetime.utcnow)
    ultima_actualizacion: Optional[datetime] = Field(None)
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }
