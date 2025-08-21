"""
Models para RCE - Registro de Compras Electrónico
Modelos de datos para MongoDB con gestión completa de comprobantes de compra
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field
from bson import ObjectId


class RceTipoDocumento(str, Enum):
    """Tipos de documento según SUNAT"""
    FACTURA = "01"
    BOLETA = "03"
    NOTA_CREDITO = "07" 
    NOTA_DEBITO = "08"
    RECIBO_HONORARIOS = "02"
    GUIA_REMISION = "09"
    COMPROBANTE_RETENCION = "20"
    COMPROBANTE_PERCEPCION = "40"


class RceEstadoComprobante(str, Enum):
    """Estados de un comprobante RCE"""
    REGISTRADO = "registrado"
    VALIDADO = "validado"
    OBSERVADO = "observado"
    ANULADO = "anulado"
    INCLUIDO = "incluido"
    EXCLUIDO = "excluido"


class RceMoneda(str, Enum):
    """Monedas permitidas"""
    PEN = "PEN"  # Soles
    USD = "USD"  # Dólares
    EUR = "EUR"  # Euros


# ========================================
# MODELOS DE DATOS PRINCIPALES
# ========================================

class RceProveedor(BaseModel):
    """Datos del proveedor/emisor del comprobante"""
    tipo_documento: str = Field(..., description="Tipo documento: 6=RUC, 1=DNI, etc")
    numero_documento: str = Field(..., description="RUC o número de documento")
    razon_social: str = Field(..., description="Razón social o apellidos y nombres")
    
    class Config:
        schema_extra = {
            "example": {
                "tipo_documento": "6",
                "numero_documento": "20123456789",
                "razon_social": "EMPRESA PROVEEDORA SAC"
            }
        }


class RceComprobante(BaseModel):
    """Modelo principal para comprobantes de compra RCE"""
    # Identificadores únicos
    id: Optional[str] = Field(None, description="ID interno del documento")
    ruc_adquiriente: str = Field(..., description="RUC de la empresa que compra")
    
    # Datos temporales
    periodo: str = Field(..., description="Período YYYYMM")
    correlativo: int = Field(..., description="Número correlativo interno")
    
    # Datos del comprobante
    fecha_emision: date = Field(..., description="Fecha de emisión")
    fecha_vencimiento: Optional[date] = Field(None, description="Fecha de vencimiento")
    tipo_comprobante: RceTipoDocumento = Field(..., description="Tipo de comprobante")
    serie: str = Field(..., description="Serie del comprobante")
    numero: str = Field(..., description="Número del comprobante")
    numero_final: Optional[str] = Field(None, description="Número final (para rangos)")
    
    # Datos del proveedor
    proveedor: RceProveedor = Field(..., description="Información del proveedor")
    
    # Datos monetarios
    moneda: RceMoneda = Field(default=RceMoneda.PEN, description="Tipo de moneda")
    tipo_cambio: Optional[Decimal] = Field(None, description="Tipo de cambio si no es PEN")
    
    # Importes base
    base_imponible_gravada: Decimal = Field(default=Decimal("0"), description="Base imponible gravada")
    base_imponible_exonerada: Decimal = Field(default=Decimal("0"), description="Base imponible exonerada") 
    base_imponible_inafecta: Decimal = Field(default=Decimal("0"), description="Base imponible inafecta")
    
    # Tributos
    igv: Decimal = Field(default=Decimal("0"), description="IGV")
    isc: Decimal = Field(default=Decimal("0"), description="ISC")
    otros_tributos: Decimal = Field(default=Decimal("0"), description="Otros tributos")
    
    # Totales
    valor_adquisicion_no_gravada: Decimal = Field(default=Decimal("0"), description="Valor de adquisición no gravada")
    importe_total: Decimal = Field(..., description="Importe total del comprobante")
    
    # Indicadores de negocio
    sustenta_credito_fiscal: bool = Field(default=True, description="Si sustenta crédito fiscal")
    sustenta_costo_gasto: bool = Field(default=True, description="Si sustenta costo o gasto")
    
    # Control y auditoría
    estado: RceEstadoComprobante = Field(default=RceEstadoComprobante.REGISTRADO)
    fecha_registro: datetime = Field(default_factory=datetime.now, description="Fecha de registro en sistema")
    fecha_modificacion: Optional[datetime] = Field(None, description="Última modificación")
    usuario_registro: Optional[str] = Field(None, description="Usuario que registró")
    
    # Campos opcionales adicionales
    observaciones: Optional[str] = Field(None, description="Observaciones adicionales")
    referencia_adicional: Optional[str] = Field(None, description="Referencias adicionales")
    
    # Campos específicos SUNAT
    numero_documento_identidad_adquiriente: Optional[str] = Field(None, description="DNI/RUC del adquiriente")
    apellidos_nombres_adquiriente: Optional[str] = Field(None, description="Apellidos y nombres del adquiriente")
    
    # Para documentos relacionados
    documento_relacionado_tipo: Optional[str] = Field(None, description="Tipo de documento relacionado")
    documento_relacionado_serie: Optional[str] = Field(None, description="Serie del documento relacionado")
    documento_relacionado_numero: Optional[str] = Field(None, description="Número del documento relacionado")
    
    class Config:
        # Configuración para trabajar con MongoDB
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }
        
        schema_extra = {
            "example": {
                "ruc_adquiriente": "20612969125",
                "periodo": "202507",
                "correlativo": 1,
                "fecha_emision": "2025-07-15",
                "tipo_comprobante": "01",
                "serie": "F001",
                "numero": "00000123",
                "proveedor": {
                    "tipo_documento": "6",
                    "numero_documento": "20123456789",
                    "razon_social": "PROVEEDOR EJEMPLO SAC"
                },
                "moneda": "PEN",
                "base_imponible_gravada": 100.00,
                "igv": 18.00,
                "importe_total": 118.00,
                "sustenta_credito_fiscal": True,
                "sustenta_costo_gasto": True,
                "estado": "registrado"
            }
        }


# ========================================
# MODELOS AUXILIARES
# ========================================

class RceResumenPeriodo(BaseModel):
    """Resumen de comprobantes por período"""
    ruc: str = Field(..., description="RUC de la empresa")
    periodo: str = Field(..., description="Período YYYYMM")
    
    # Contadores
    total_comprobantes: int = Field(default=0)
    total_facturas: int = Field(default=0)
    total_boletas: int = Field(default=0)
    total_notas_credito: int = Field(default=0)
    total_notas_debito: int = Field(default=0)
    
    # Importes totales
    total_importe_periodo: Decimal = Field(default=Decimal("0"))
    total_igv_periodo: Decimal = Field(default=Decimal("0"))
    total_base_imponible: Decimal = Field(default=Decimal("0"))
    total_credito_fiscal: Decimal = Field(default=Decimal("0"))
    
    # Fechas de control
    fecha_calculo: datetime = Field(default_factory=datetime.now)
    fecha_primer_comprobante: Optional[date] = Field(None)
    fecha_ultimo_comprobante: Optional[date] = Field(None)
    
    # Distribución por estado
    comprobantes_registrados: int = Field(default=0)
    comprobantes_validados: int = Field(default=0)
    comprobantes_observados: int = Field(default=0)
    comprobantes_anulados: int = Field(default=0)


class RceEstadisticasProveedor(BaseModel):
    """Estadísticas por proveedor"""
    ruc_proveedor: str = Field(..., description="RUC del proveedor")
    razon_social: str = Field(..., description="Razón social del proveedor")
    
    # Contadores
    total_comprobantes: int = Field(default=0)
    total_importe: Decimal = Field(default=Decimal("0"))
    
    # Distribución por tipo
    facturas: int = Field(default=0)
    boletas: int = Field(default=0)
    notas_credito: int = Field(default=0)
    notas_debito: int = Field(default=0)
    
    # Fechas
    primer_comprobante: Optional[date] = Field(None)
    ultimo_comprobante: Optional[date] = Field(None)


class RceConfiguracionPeriodo(BaseModel):
    """Configuración específica por período"""
    ruc: str = Field(..., description="RUC de la empresa")
    periodo: str = Field(..., description="Período YYYYMM")
    
    # Estado del período
    estado_periodo: str = Field(default="abierto", description="abierto, cerrado, enviado")
    fecha_cierre: Optional[datetime] = Field(None)
    fecha_envio_sunat: Optional[datetime] = Field(None)
    
    # Configuraciones
    correlativo_actual: int = Field(default=0, description="Último correlativo usado")
    auto_validar: bool = Field(default=False, description="Auto validar comprobantes")
    incluir_no_domiciliados: bool = Field(default=True, description="Incluir proveedores no domiciliados")
    
    # Metadatos
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    usuario_configuracion: Optional[str] = Field(None)


# ========================================
# MODELOS DE CONTROL Y AUDITORÍA
# ========================================

class RceLogOperacion(BaseModel):
    """Log de operaciones sobre comprobantes"""
    ruc: str = Field(..., description="RUC de la empresa")
    periodo: str = Field(..., description="Período afectado")
    
    # Operación realizada
    tipo_operacion: str = Field(..., description="crear, modificar, eliminar, validar, etc")
    comprobante_id: Optional[str] = Field(None, description="ID del comprobante afectado")
    comprobante_serie: Optional[str] = Field(None)
    comprobante_numero: Optional[str] = Field(None)
    
    # Datos de la operación
    detalle_operacion: str = Field(..., description="Descripción de lo realizado")
    datos_anteriores: Optional[Dict[str, Any]] = Field(None, description="Datos antes del cambio")
    datos_nuevos: Optional[Dict[str, Any]] = Field(None, description="Datos después del cambio")
    
    # Auditoría
    fecha_operacion: datetime = Field(default_factory=datetime.now)
    usuario_operacion: Optional[str] = Field(None)
    ip_usuario: Optional[str] = Field(None)
    
    # Resultado
    exitoso: bool = Field(default=True)
    mensaje_error: Optional[str] = Field(None)


# ========================================
# ÍNDICES Y VALIDACIONES
# ========================================

class RceIndexes:
    """Definición de índices para optimización de consultas"""
    
    # Índices para colección rce_comprobantes
    COMPROBANTES_INDEXES = [
        # Índice principal por empresa y período
        ("ruc_adquiriente", "periodo"),
        
        # Índice único para evitar duplicados
        ("ruc_adquiriente", "periodo", "serie", "numero", "proveedor.numero_documento"),
        
        # Índices para consultas frecuentes
        ("fecha_emision",),
        ("tipo_comprobante",),
        ("estado",),
        ("proveedor.numero_documento",),
        ("proveedor.razon_social",),
        
        # Índices para reportes
        ("fecha_registro",),
        ("importe_total",),
        
        # Índice para búsquedas de texto
        ("proveedor.razon_social", "text"),
    ]
    
    # Índices para colección rce_resumenes
    RESUMENES_INDEXES = [
        ("ruc", "periodo"),
        ("fecha_calculo",),
    ]
    
    # Índices para colección rce_logs
    LOGS_INDEXES = [
        ("ruc", "fecha_operacion"),
        ("tipo_operacion",),
        ("usuario_operacion",),
    ]
