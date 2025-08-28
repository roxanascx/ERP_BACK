"""
Schemas para Libro Mayor PLE 050200 - Sistema ERP
================================================

Modelos Pydantic para el Libro Mayor según especificaciones 
oficiales SUNAT PLE 050200.

El Libro Mayor registra los movimientos contables agrupados
por cuenta contable, mostrando débitos, créditos y saldos.

Campos oficiales SUNAT (9 campos):
1. Período (AAAAMM00)
2. Código de cuenta contable
3. Descripción de cuenta contable  
4. Saldo deudor inicial
5. Saldo acreedor inicial
6. Movimiento del debe
7. Movimiento del haber
8. Saldo final deudor
9. Saldo final acreedor

Basado en:
- Resolución de Superintendencia N° 286-2009/SUNAT
- PLE_SUNAT_DOCUMENTACION_COMPLETA.md

Autor: Sistema ERP - FASE 2.3
Fecha: Agosto 2025
"""

from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import date
from enum import Enum, IntEnum
from pydantic import BaseModel, Field, validator, ConfigDict


# ===================================
# ENUMS PARA CLASIFICACIÓN OFICIAL
# ===================================

class TipoCuentaContable(str, Enum):
    """Tipos de cuentas contables según plan contable"""
    ACTIVO = "1"
    PASIVO = "2" 
    PATRIMONIO = "3"
    INGRESOS = "4"
    GASTOS = "5"
    COSTOS = "6"
    CUENTAS_CONTINGENTES = "7"
    CUENTAS_ORDEN = "8"
    CUENTAS_ANALITICAS = "9"
    OTRAS = "0"


class NaturalezaCuenta(str, Enum):
    """Naturaleza de la cuenta contable"""
    DEUDORA = "D"
    ACREEDORA = "A"


class EstadoCuentaMayor(IntEnum):
    """Estados de una cuenta en el libro mayor"""
    ACTIVA = 1
    INACTIVA = 0
    CERRADA = 9


class TipoDocumentoIdentidad(str, Enum):
    """Tipos de documento de identidad según SUNAT"""
    RUC = "6"
    DNI = "1"
    CARNET_EXTRANJERIA = "4"
    PASAPORTE = "7"
    OTROS = "0"


class TipoComprobantePago(str, Enum):
    """Tipos de comprobante de pago según SUNAT"""
    FACTURA = "01"
    BOLETA = "03"
    NOTA_CREDITO = "07"
    NOTA_DEBITO = "08"
    RECIBO_HONORARIOS = "02"
    OTROS = "00"


class EstadoOperacion(str, Enum):
    """Estados de operación según SUNAT"""
    ANOTACION_VIGENTE = "1"
    ANOTACION_ANULADA = "8"
    ANOTACION_EXTORNADA = "9"


# ===================================
# MODELO PRINCIPAL PLE LIBRO MAYOR
# ===================================

class LibroMayorPLE(BaseModel):
    """
    Modelo principal para registro PLE Libro Mayor (050200)
    Según especificaciones oficiales SUNAT
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True
    )
    
    # Campo 1: Período
    periodo: str = Field(
        ...,
        pattern=r'^\d{8}$',
        description="Período en formato YYYYMM00"
    )
    
    # Campo 2: Código Único de Operación
    codigo_unico_operacion: str = Field(
        ...,
        min_length=1,
        max_length=40,
        description="Código único de operación"
    )
    
    # Campo 3: Número correlativo
    numero_correlativo: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Número correlativo del asiento"
    )
    
    # Campo 4: Código de cuenta contable
    codigo_cuenta_contable: str = Field(
        ...,
        min_length=2,
        max_length=24,
        description="Código de cuenta contable"
    )
    
    # Campo 5: Código de unidad de operación
    codigo_unidad_operacion: str = Field(
        default="",
        max_length=20,
        description="Código de unidad de operación"
    )
    
    # Campo 6: Código de centro de costos
    codigo_centro_costos: str = Field(
        default="",
        max_length=20,
        description="Código de centro de costos"
    )
    
    # Campo 7: Tipo de moneda
    tipo_moneda: str = Field(
        default="PEN",
        pattern=r'^[A-Z]{3}$',
        description="Tipo de moneda (ISO 4217)"
    )
    
    # Campo 8: Tipo de documento de identidad
    tipo_documento_identidad: TipoDocumentoIdentidad = Field(
        ...,
        description="Tipo de documento de identidad"
    )
    
    # Campo 9: Número de documento de identidad
    numero_documento_identidad: str = Field(
        ...,
        min_length=8,
        max_length=15,
        description="Número de documento de identidad"
    )
    
    # Campo 10: Tipo de comprobante de pago
    tipo_comprobante_pago: TipoComprobantePago = Field(
        ...,
        description="Tipo de comprobante de pago"
    )
    
    # Campo 11: Número de serie del comprobante
    numero_serie_comprobante: str = Field(
        default="",
        max_length=20,
        description="Número de serie del comprobante"
    )
    
    # Campo 12: Número del comprobante de pago
    numero_comprobante_pago: str = Field(
        default="",
        max_length=20,
        description="Número del comprobante de pago"
    )
    
    # Campo 13: Fecha contable
    fecha_contable: date = Field(
        ...,
        description="Fecha de la operación contable"
    )
    
    # Campo 14: Fecha de vencimiento
    fecha_vencimiento: date = Field(
        ...,
        description="Fecha de vencimiento"
    )
    
    # Campo 15: Fecha de operación
    fecha_operacion: date = Field(
        ...,
        description="Fecha de la operación"
    )
    
    # Campo 16: Glosa o descripción
    glosa_descripcion: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Glosa o descripción de la operación"
    )
    
    # Campo 17: Glosa referencial
    glosa_referencial: str = Field(
        default="",
        max_length=200,
        description="Glosa referencial"
    )
    
    # Campo 18: Movimiento del debe
    movimiento_debe: Decimal = Field(
        default=Decimal('0.00'),
        ge=0,
        description="Importe del movimiento debe"
    )
    
    # Campo 19: Movimiento del haber
    movimiento_haber: Decimal = Field(
        default=Decimal('0.00'),
        ge=0,
        description="Importe del movimiento haber"
    )
    
    # Campo 20: Saldo deudor
    saldo_deudor: Decimal = Field(
        default=Decimal('0.00'),
        ge=0,
        description="Saldo deudor"
    )
    
    # Campo 21: Saldo acreedor
    saldo_acreedor: Decimal = Field(
        default=Decimal('0.00'),
        ge=0,
        description="Saldo acreedor"
    )
    
    # Campo 22: Datos de la estructura
    datos_estructura: str = Field(
        default="1",
        description="Datos de la estructura del libro"
    )
    
    # Campo 23: Estado de la operación
    estado_operacion: EstadoOperacion = Field(
        default=EstadoOperacion.ANOTACION_VIGENTE,
        description="Estado de la operación"
    )


# ===================================
# MODELOS COMPLEMENTARIOS
# ===================================

class LibroMayorRequest(BaseModel):
    """Modelo para crear/actualizar registro del Libro Mayor"""
    
    # Información de la cuenta contable
    codigo_cuenta_contable: str = Field(
        ..., 
        min_length=2, 
        max_length=24,
        description="Código de cuenta contable según plan contable"
    )
    descripcion_cuenta: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Descripción completa de la cuenta contable"
    )
    
    # Saldos iniciales del período
    saldo_deudor_inicial: Decimal = Field(
        default=Decimal('0.00'),
        ge=0,
        description="Saldo deudor al inicio del período"
    )
    saldo_acreedor_inicial: Decimal = Field(
        default=Decimal('0.00'),
        ge=0,
        description="Saldo acreedor al inicio del período"
    )
    
    # Movimientos del período
    movimiento_debe: Decimal = Field(
        default=Decimal('0.00'),
        ge=0,
        description="Total de movimientos en el debe"
    )
    movimiento_haber: Decimal = Field(
        default=Decimal('0.00'),
        ge=0,
        description="Total de movimientos en el haber"
    )
    
    # Saldos finales del período
    saldo_final_deudor: Decimal = Field(
        default=Decimal('0.00'),
        ge=0,
        description="Saldo deudor al final del período"
    )
    saldo_final_acreedor: Decimal = Field(
        default=Decimal('0.00'),
        ge=0,
        description="Saldo acreedor al final del período"
    )
    
    # Metadatos adicionales
    naturaleza_cuenta: Optional[NaturalezaCuenta] = Field(
        None,
        description="Naturaleza de la cuenta (Deudora/Acreedora)"
    )
    tipo_cuenta: Optional[TipoCuentaContable] = Field(
        None,
        description="Tipo de cuenta según clasificación"
    )
    estado_cuenta: EstadoCuentaMayor = Field(
        default=EstadoCuentaMayor.ACTIVA,
        description="Estado de la cuenta en el período"
    )
    
    # Información adicional para auditoría
    numero_asientos_debe: Optional[int] = Field(
        default=0,
        ge=0,
        description="Cantidad de asientos en el debe"
    )
    numero_asientos_haber: Optional[int] = Field(
        default=0,
        ge=0,
        description="Cantidad de asientos en el haber"
    )
    observaciones: Optional[str] = Field(
        None,
        max_length=500,
        description="Observaciones sobre la cuenta"
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True
    )

    @validator('codigo_cuenta_contable')
    def validar_codigo_cuenta(cls, v):
        """Validar formato del código de cuenta contable"""
        if not v:
            raise ValueError("Código de cuenta contable es obligatorio")
        
        # Debe ser numérico o alfanumérico según plan contable
        if not v.replace('.', '').replace('-', '').isalnum():
            raise ValueError("Código de cuenta contable debe ser alfanumérico")
        
        return v.upper().strip()

    @validator('saldo_final_deudor', 'saldo_final_acreedor')
    def validar_saldos_finales_exclusivos(cls, v, values):
        """Validar que no existan saldos deudor y acreedor simultáneamente"""
        if 'saldo_final_deudor' in values and 'saldo_final_acreedor' in values:
            saldo_deudor = values.get('saldo_final_deudor', Decimal('0.00'))
            saldo_acreedor = v if cls.__name__ == 'saldo_final_acreedor' else values.get('saldo_final_acreedor', Decimal('0.00'))
            
            if saldo_deudor > 0 and saldo_acreedor > 0:
                raise ValueError("Una cuenta no puede tener saldo deudor y acreedor simultáneamente")
        
        return v

    def calcular_saldos_finales(self) -> tuple[Decimal, Decimal]:
        """Calcular saldos finales basados en saldos iniciales y movimientos"""
        # Saldo neto inicial
        saldo_inicial_neto = self.saldo_deudor_inicial - self.saldo_acreedor_inicial
        
        # Saldo neto de movimientos
        movimiento_neto = self.movimiento_debe - self.movimiento_haber
        
        # Saldo final neto
        saldo_final_neto = saldo_inicial_neto + movimiento_neto
        
        if saldo_final_neto >= 0:
            return saldo_final_neto, Decimal('0.00')  # (deudor, acreedor)
        else:
            return Decimal('0.00'), abs(saldo_final_neto)  # (deudor, acreedor)


class LibroMayorResponse(LibroMayorRequest):
    """Modelo de respuesta para registro del Libro Mayor"""
    
    id: str = Field(..., description="ID único del registro")
    empresa_id: str = Field(..., description="ID de la empresa")
    periodo: str = Field(..., description="Período AAAAMM")
    fecha_creacion: str = Field(..., description="Fecha de creación del registro")
    fecha_actualizacion: Optional[str] = Field(None, description="Fecha de última actualización")
    
    # Campos calculados adicionales
    saldo_inicial_neto: Optional[Decimal] = Field(
        None,
        description="Saldo inicial neto (deudor - acreedor)"
    )
    saldo_final_neto: Optional[Decimal] = Field(
        None,
        description="Saldo final neto (deudor - acreedor)"
    )
    variacion_periodo: Optional[Decimal] = Field(
        None,
        description="Variación del saldo en el período"
    )


# ===================================
# MODELOS PARA CONSULTAS Y FILTROS
# ===================================

class LibroMayorFiltros(BaseModel):
    """Modelo para filtros de consulta del Libro Mayor"""
    
    codigo_cuenta_desde: Optional[str] = Field(None, description="Código de cuenta desde")
    codigo_cuenta_hasta: Optional[str] = Field(None, description="Código de cuenta hasta")
    descripcion_contiene: Optional[str] = Field(None, description="Filtro por descripción")
    tipo_cuenta: Optional[TipoCuentaContable] = Field(None, description="Filtro por tipo de cuenta")
    naturaleza_cuenta: Optional[NaturalezaCuenta] = Field(None, description="Filtro por naturaleza")
    estado_cuenta: Optional[EstadoCuentaMayor] = Field(None, description="Filtro por estado")
    saldo_minimo: Optional[Decimal] = Field(None, ge=0, description="Saldo mínimo")
    saldo_maximo: Optional[Decimal] = Field(None, ge=0, description="Saldo máximo")
    solo_con_movimientos: bool = Field(default=False, description="Solo cuentas con movimientos")
    solo_con_saldo: bool = Field(default=False, description="Solo cuentas con saldo")


# ===================================
# MODELOS PARA EXPORTACIÓN PLE
# ===================================

class PLELibroMayorExportOptions(BaseModel):
    """Opciones para exportación de Libro Mayor PLE 050200"""
    
    empresa_id: str = Field(..., description="ID de la empresa")
    periodo_inicio: str = Field(
        ..., 
        pattern=r"^\d{6}$",
        description="Período inicio AAAAMM"
    )
    periodo_fin: str = Field(
        ..., 
        pattern=r"^\d{6}$", 
        description="Período fin AAAAMM"
    )
    
    # Filtros opcionales
    filtros: Optional[LibroMayorFiltros] = Field(None, description="Filtros adicionales")
    
    # Opciones de exportación
    incluir_cuentas_sin_movimiento: bool = Field(
        default=False,
        description="Incluir cuentas sin movimientos en el período"
    )
    incluir_cuentas_cerradas: bool = Field(
        default=False,
        description="Incluir cuentas cerradas"
    )
    solo_errores: bool = Field(
        default=False,
        description="Exportar solo registros con errores"
    )
    
    # Configuración del archivo
    correlativo_archivo: str = Field(
        default="001",
        pattern=r"^\d{3}$",
        description="Correlativo del archivo (001-999)"
    )
    generar_resumen: bool = Field(
        default=True,
        description="Generar resumen ejecutivo"
    )

    @validator('periodo_fin')
    def validar_periodo_fin(cls, v, values):
        """Validar que período fin sea mayor o igual a período inicio"""
        if 'periodo_inicio' in values and v < values['periodo_inicio']:
            raise ValueError("Período fin debe ser mayor o igual a período inicio")
        return v


class PLELibroMayorExportResult(BaseModel):
    """Resultado de exportación de Libro Mayor PLE 050200"""
    
    # Información del archivo generado
    nombre_archivo: str = Field(..., description="Nombre del archivo PLE generado")
    contenido_archivo: str = Field(..., description="Contenido del archivo en formato PLE")
    tamaño_archivo: int = Field(..., description="Tamaño del archivo en bytes")
    
    # Estadísticas de procesamiento
    total_cuentas: int = Field(..., description="Total de cuentas procesadas")
    cuentas_exportadas: int = Field(..., description="Cuentas incluidas en el archivo")
    cuentas_excluidas: int = Field(..., description="Cuentas excluidas por filtros")
    cuentas_con_errores: int = Field(..., description="Cuentas con errores")
    
    # Metadatos
    fecha_generacion: str = Field(..., description="Fecha y hora de generación")
    periodo_procesado: str = Field(..., description="Período(s) procesado(s)")
    empresa_id: str = Field(..., description="ID de la empresa")
    
    # Resumen financiero
    resumen_saldos: Dict[str, Any] = Field(
        default_factory=dict,
        description="Resumen de saldos por tipo de cuenta"
    )
    
    # Control de calidad
    errores_encontrados: List[str] = Field(
        default_factory=list,
        description="Lista de errores encontrados"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Lista de advertencias"
    )
    
    # Validación contable
    validacion_contable: Dict[str, Any] = Field(
        default_factory=dict,
        description="Resultado de validaciones contables (partida doble, etc.)"
    )


# ===================================
# MODELOS PARA REPORTES Y ANÁLISIS
# ===================================

class ResumenLibroMayor(BaseModel):
    """Resumen ejecutivo del Libro Mayor"""
    
    periodo: str = Field(..., description="Período del resumen")
    empresa_id: str = Field(..., description="ID de la empresa")
    
    # Totales por naturaleza
    total_cuentas_deudoras: int = Field(..., description="Cantidad de cuentas deudoras")
    total_cuentas_acreedoras: int = Field(..., description="Cantidad de cuentas acreedoras")
    
    # Saldos por tipo de cuenta
    saldos_activo: Decimal = Field(..., description="Total saldos de activo")
    saldos_pasivo: Decimal = Field(..., description="Total saldos de pasivo")
    saldos_patrimonio: Decimal = Field(..., description="Total saldos de patrimonio")
    saldos_ingresos: Decimal = Field(..., description="Total saldos de ingresos")
    saldos_gastos: Decimal = Field(..., description="Total saldos de gastos")
    
    # Movimientos del período
    total_movimientos_debe: Decimal = Field(..., description="Total movimientos debe")
    total_movimientos_haber: Decimal = Field(..., description="Total movimientos haber")
    
    # Validaciones
    balance_partida_doble: bool = Field(..., description="Balance de partida doble correcto")
    diferencia_balance: Decimal = Field(..., description="Diferencia en balance si existe")
    
    # Análisis
    cuentas_con_mayor_movimiento: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Top cuentas con mayor movimiento"
    )
    cuentas_sin_movimiento: int = Field(..., description="Cantidad de cuentas sin movimiento")


class AnalisisCuentaMayor(BaseModel):
    """Análisis detallado de una cuenta del Libro Mayor"""
    
    codigo_cuenta: str = Field(..., description="Código de cuenta analizada")
    descripcion_cuenta: str = Field(..., description="Descripción de la cuenta")
    
    # Evolución histórica
    saldos_historicos: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Evolución de saldos por período"
    )
    
    # Estadísticas
    promedio_movimientos_debe: Decimal = Field(..., description="Promedio movimientos debe")
    promedio_movimientos_haber: Decimal = Field(..., description="Promedio movimientos haber")
    
    # Tendencias
    tendencia_saldo: str = Field(..., description="Tendencia del saldo (creciente/decreciente/estable)")
    variabilidad: str = Field(..., description="Nivel de variabilidad (alta/media/baja)")
    
    # Alertas
    alertas: List[str] = Field(
        default_factory=list,
        description="Alertas detectadas en la cuenta"
    )


# ===================================
# FUNCIONES DE UTILIDAD
# ===================================

def validar_codigo_plan_contable(codigo: str, plan_contable: Dict[str, Any]) -> bool:
    """Validar que el código de cuenta existe en el plan contable"""
    # Esta función se integraría con el servicio de plan contable
    return True  # Implementación pendiente


def determinar_naturaleza_cuenta(codigo: str) -> NaturalezaCuenta:
    """Determinar la naturaleza de una cuenta basada en su código"""
    if codigo.startswith(('1', '5')):  # Activo y Gastos
        return NaturalezaCuenta.DEUDORA
    elif codigo.startswith(('2', '3', '4')):  # Pasivo, Patrimonio e Ingresos
        return NaturalezaCuenta.ACREEDORA
    else:
        return NaturalezaCuenta.DEUDORA  # Por defecto


def determinar_tipo_cuenta(codigo: str) -> TipoCuentaContable:
    """Determinar el tipo de cuenta basada en su código"""
    primer_digito = codigo[0] if codigo else '0'
    
    mapping = {
        '1': TipoCuentaContable.ACTIVO,
        '2': TipoCuentaContable.PASIVO,
        '3': TipoCuentaContable.PATRIMONIO,
        '4': TipoCuentaContable.INGRESOS,
        '5': TipoCuentaContable.GASTOS,
        '0': TipoCuentaContable.CUENTAS_ORDEN
    }
    
    return mapping.get(primer_digito, TipoCuentaContable.ACTIVO)
