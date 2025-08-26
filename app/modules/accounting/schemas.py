from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CuentaContableCreate(BaseModel):
    codigo: str
    descripcion: str
    nivel: int
    clase_contable: int
    cuenta_padre: Optional[str] = None
    es_hoja: bool = True
    acepta_movimiento: bool = True
    naturaleza: str = "DEUDORA"
    moneda: str = "MN"
    tipo_plan: str = "estandar"
    empresa_id: Optional[str] = None
    archivo_origen: Optional[str] = None


class CuentaContableResponse(BaseModel):
    id: Optional[str]
    codigo: str
    descripcion: str
    nivel: int
    clase_contable: int
    cuenta_padre: Optional[str]
    es_hoja: bool
    acepta_movimiento: bool
    naturaleza: str
    moneda: str
    activa: bool
    tipo_plan: str = "estandar"
    empresa_id: Optional[str] = None
    archivo_origen: Optional[str] = None
    fecha_creacion: datetime


# Schemas para importación de planes personalizados
class ValidationResult(BaseModel):
    """Resultado de la validación de un archivo de plan contable"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    total_lines: int
    valid_accounts: int
    preview_data: List[Dict[str, Any]]


class ImportResult(BaseModel):
    """Resultado de la importación de un plan contable"""
    success: bool
    imported_count: int
    errors: List[str]
    warnings: List[str]
    backup_created: bool


class PlanContableInfo(BaseModel):
    """Información sobre un plan contable disponible"""
    tipo: str  # "estandar" | "personalizado"
    nombre: str
    descripcion: str
    total_cuentas: int
    fecha_creacion: Optional[datetime] = None
    archivo_origen: Optional[str] = None
    activo: bool = False


class SwitchPlanRequest(BaseModel):
    """Request para cambiar tipo de plan contable"""
    tipo_plan: str  # "estandar" | "personalizado"
    empresa_id: str


class ImportFileRequest(BaseModel):
    """Request para importar archivo de plan contable"""
    empresa_id: str
    filename: str
    content: str  # Contenido del archivo en base64 o texto plano
    fecha_modificacion: Optional[datetime]


# ================================
# SCHEMAS PARA LIBRO DIARIO V2 (FRONTEND-ALIGNED)
# ================================

class EstadoLibroDiario(str, Enum):
    BORRADOR = "borrador"
    FINALIZADO = "finalizado"
    ENVIADO = "enviado"


class CuentaContableLookup(BaseModel):
    """Schema para el autocompletado de cuentas contables"""
    codigo: str
    denominacion: str
    naturaleza: str = Field(..., pattern="^(DEUDORA|ACREEDORA|DEUDORA/ACREEDORA)$")
    nivel: int
    activa: bool


class DetalleAsientoBase(BaseModel):
    """Schema para detalle de asiento contable (línea individual)"""
    codigoCuenta: str
    denominacionCuenta: str
    descripcion: str
    debe: Optional[float] = Field(default=0.0, ge=0)
    haber: Optional[float] = Field(default=0.0, ge=0)
    
    @validator('debe', 'haber')
    def validate_debe_haber(cls, v, values):
        # Al menos uno debe tener valor
        if 'debe' in values and 'haber' in values:
            if values.get('debe', 0) == 0 and values.get('haber', 0) == 0:
                raise ValueError('Debe especificar un valor en Debe o Haber')
            if values.get('debe', 0) > 0 and values.get('haber', 0) > 0:
                raise ValueError('No puede tener valores en Debe y Haber al mismo tiempo')
        return v


class AsientoContableBaseV2(BaseModel):
    """Schema base para asientos contables v2 (alineado con frontend)"""
    numero: str  # Número correlativo del asiento
    fecha: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD
    descripcion: str = Field(..., max_length=500)  # Glosa o descripción
    detalles: List[DetalleAsientoBase] = Field(..., min_items=2)  # Al menos 2 líneas
    
    @validator('detalles')
    def validate_detalles_balanceados(cls, v):
        total_debe = sum(detalle.debe or 0 for detalle in v)
        total_haber = sum(detalle.haber or 0 for detalle in v)
        
        if abs(total_debe - total_haber) > 0.01:  # Tolerancia de 1 centavo
            raise ValueError(f'El asiento debe estar balanceado. Debe: {total_debe}, Haber: {total_haber}')
        
        return v


class AsientoContableCreateV2(AsientoContableBaseV2):
    """Schema para crear asientos contables v2"""
    empresaId: Optional[str] = None
    libroId: Optional[str] = None


class AsientoContableResponseV2(AsientoContableBaseV2):
    """Schema para respuesta de asientos contables v2"""
    id: str
    empresaId: Optional[str] = None
    libroId: Optional[str] = None
    usuarioCreacion: Optional[str] = None
    fechaCreacion: Optional[datetime] = None  # Cambiar a datetime
    fechaModificacion: Optional[datetime] = None  # Cambiar a datetime

    class Config:
        from_attributes = True


class LibroDiarioBaseV2(BaseModel):
    """Schema base para libro diario v2"""
    descripcion: str = Field(..., max_length=200)
    periodo: str = Field(..., pattern=r"^\d{4}(-\d{2})?$")  # YYYY o YYYY-MM
    estado: EstadoLibroDiario = EstadoLibroDiario.BORRADOR
    moneda: str = Field(default="PEN")
    tipoLibro: str = Field(default="5.1")


class LibroDiarioCreateV2(LibroDiarioBaseV2):
    """Schema para crear libro diario v2"""
    empresaId: str
    ruc: Optional[str] = None
    razonSocial: Optional[str] = None


class LibroDiarioResponseV2(LibroDiarioBaseV2):
    """Schema para respuesta de libro diario v2 (alineado con frontend)"""
    id: str
    empresaId: str
    ruc: str
    razonSocial: str
    asientos: List[AsientoContableResponseV2] = []
    totalDebe: float = 0.0
    totalHaber: float = 0.0
    fechaCreacion: Optional[datetime] = None  # Cambiar a datetime
    fechaModificacion: Optional[datetime] = None  # Cambiar a datetime
    usuarioCreacion: Optional[str] = None
    usuarioModificacion: Optional[str] = None

    class Config:
        from_attributes = True


# ================================
# SCHEMAS LEGACY (MANTENER COMPATIBILIDAD)
# ================================

class AsientoContableBase(BaseModel):
    """Schema base para asientos contables"""
    numeroCorrelativo: str
    fecha: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD
    glosa: str = Field(..., max_length=500)
    codigoLibro: str = Field(default="5.1")  # Libro Diario por defecto
    numeroDocumento: str = Field(..., max_length=50)
    cuentaContable: Dict[str, str]  # {codigo: str, denominacion: str}
    debe: float = Field(ge=0)
    haber: float = Field(ge=0)
    
    @validator('cuentaContable')
    def validate_cuenta_contable(cls, v):
        if not isinstance(v, dict):
            raise ValueError('cuentaContable debe ser un diccionario')
        if 'codigo' not in v or 'denominacion' not in v:
            raise ValueError('cuentaContable debe tener codigo y denominacion')
        return v
    
    @validator('debe', 'haber')
    def validate_debe_haber(cls, v, values):
        if 'debe' in values and 'haber' in values:
            if values['debe'] > 0 and values['haber'] > 0:
                raise ValueError('No puede tener valores en Debe y Haber al mismo tiempo')
            if values['debe'] == 0 and values['haber'] == 0:
                raise ValueError('Debe especificar un valor en Debe o Haber')
        return v


class AsientoContableCreate(AsientoContableBase):
    """Schema para crear asientos contables"""
    empresaId: Optional[str] = None


class AsientoContableUpdate(BaseModel):
    """Schema para actualizar asientos contables"""
    numeroCorrelativo: Optional[str] = None
    fecha: Optional[str] = None
    glosa: Optional[str] = None
    codigoLibro: Optional[str] = None
    numeroDocumento: Optional[str] = None
    cuentaContable: Optional[Dict[str, str]] = None
    debe: Optional[float] = None
    haber: Optional[float] = None


class AsientoContableResponse(AsientoContableBase):
    """Schema para respuesta de asientos contables"""
    id: str
    empresaId: str
    usuarioCreacion: Optional[str] = None
    fechaCreacion: Optional[datetime] = None
    fechaModificacion: Optional[datetime] = None

    class Config:
        from_attributes = True


class LibroDiarioBase(BaseModel):
    """Schema base para libro diario"""
    descripcion: str = Field(..., max_length=200)
    periodo: str = Field(..., pattern=r"^\d{4}(-\d{2})?$")  # YYYY o YYYY-MM
    estado: EstadoLibroDiario = EstadoLibroDiario.BORRADOR
    moneda: str = Field(default="PEN")
    tipoLibro: str = Field(default="5.1")


class LibroDiarioCreate(LibroDiarioBase):
    """Schema para crear libro diario"""
    empresaId: str
    ruc: Optional[str] = None
    razonSocial: Optional[str] = None


class LibroDiarioUpdate(BaseModel):
    """Schema para actualizar libro diario"""
    descripcion: Optional[str] = None
    periodo: Optional[str] = None
    estado: Optional[EstadoLibroDiario] = None


class LibroDiarioResponse(LibroDiarioBase):
    """Schema para respuesta de libro diario"""
    id: str
    empresaId: str
    ruc: str
    razonSocial: str
    asientos: List[AsientoContableResponse] = []
    totalDebe: float = 0.0
    totalHaber: float = 0.0
    fechaCreacion: Optional[datetime] = None
    fechaModificacion: Optional[datetime] = None
    usuarioCreacion: Optional[str] = None
    usuarioModificacion: Optional[str] = None

    class Config:
        from_attributes = True


class FiltrosLibroDiario(BaseModel):
    """Schema para filtros de búsqueda"""
    empresaId: Optional[str] = None
    periodo: Optional[str] = None
    fechaDesde: Optional[str] = None
    fechaHasta: Optional[str] = None
    estado: Optional[EstadoLibroDiario] = None
    busqueda: Optional[str] = None
    cuentaContable: Optional[str] = None


class ResumenLibroDiario(BaseModel):
    """Schema para resumen estadístico"""
    totalLibros: int
    totalAsientos: int
    totalDebe: float
    totalHaber: float
    diferencia: float
    balanceado: bool
    periodos: List[str]
    ultimaModificacion: datetime
    asientosPorEstado: Dict[str, int]
    ultimoLibro: Optional[Dict[str, Any]] = None


class ValidationResult(BaseModel):
    """Schema para resultados de validación"""
    isValid: bool
    errors: List[str] = []
    warnings: List[str] = []
    asientosSinBalancear: List[str] = []  # números correlativos


class ExportOptions(BaseModel):
    """Schema para opciones de exportación"""
    formato: str = Field(..., pattern="^(excel|pdf|txt)$")
    incluirTotales: bool = True
    incluirResumen: bool = True
    fechaDesde: Optional[str] = None
    fechaHasta: Optional[str] = None


# =====================================
# SCHEMAS PARA PLE (PROGRAMA DE LIBROS ELECTRÓNICOS)
# =====================================

class PLEExportOptions(BaseModel):
    """Schema para opciones de exportación PLE"""
    incluir_asientos_cero: bool = True
    validar_antes_generar: bool = True
    generar_zip: bool = True
    incluir_metadatos: bool = True
    formato_fecha: str = "DD/MM/YYYY"
    precision_montos: int = 2
    validar_con_sunat: bool = True
    validar_plan_contable: bool = True
    validar_tipos_documento: bool = True
    enriquecer_con_sunat: bool = True
    permitir_cuentas_personalizadas: bool = True
    fallar_en_errores_criticos: bool = True
    incluir_reporte_validacion: bool = True


class PLEValidationError(BaseModel):
    """Schema para errores de validación PLE"""
    codigo: str
    tabla: str
    campo: str
    valor: str
    mensaje: str
    critico: bool
    sugerencia: Optional[str] = None


class PLEValidationWarning(BaseModel):
    """Schema para warnings de validación PLE"""
    codigo: str
    tabla: str
    campo: str
    valor: str
    mensaje: str
    sugerencia: Optional[str] = None


class PLEValidationStats(BaseModel):
    """Schema para estadísticas de validación PLE"""
    total_errores: int
    total_warnings: int
    errores_criticos: int
    porcentaje_validado: float
    cuentas_validadas: int
    tiempo_validacion: float


class PLEValidationBasic(BaseModel):
    """Schema para validación básica PLE"""
    valido: bool
    total_asientos: int
    total_debe: str
    total_haber: str
    balanceado: bool
    errores: List[str]
    warnings: List[str]


class PLEValidationSunat(BaseModel):
    """Schema para validación SUNAT PLE"""
    valido: bool
    total_registros: int
    registros_validados: int
    errores: List[PLEValidationError]
    warnings: List[PLEValidationWarning]
    datos_enriquecidos: int
    estadisticas: PLEValidationStats
    tiempo_validacion: float


class PLEValidationResult(BaseModel):
    """Schema para resultado completo de validación PLE"""
    exito: bool
    libro_id: str
    valido: bool
    validacion_basica: PLEValidationBasic
    validacion_sunat: PLEValidationSunat
    error: Optional[str] = None


class PLEExportResult(BaseModel):
    """Schema para resultado de exportación PLE"""
    exito: bool
    libro_id: str
    nombre_archivo: str
    tamaño_txt: int
    tamaño_zip: Optional[int] = None
    total_lineas: int
    contenido_txt: str
    contenido_zip: Optional[bytes] = None
    fecha_generacion: str
    errores: List[str]
    warnings: List[str]
    metadatos: Dict[str, Any]
    validacion_sunat: Optional[Dict[str, Any]] = None
    datos_enriquecidos: bool
    reporte_validacion: Optional[str] = None
    error: Optional[str] = None


class PLEPreviewResult(BaseModel):
    """Schema para vista previa PLE"""
    exito: bool
    libro_id: str
    nombre_archivo: str
    total_lineas: int
    lineas_mostradas: int
    preview_lineas: List[str]
    muestra_completa: bool
    estadisticas: Dict[str, Any]
    error: Optional[str] = None


class PLEStatsResult(BaseModel):
    """Schema para estadísticas PLE"""
    exito: bool
    libro_id: str
    estadisticas: Dict[str, Any]
    error: Optional[str] = None


class PLEReportResult(BaseModel):
    """Schema para reporte de validación PLE"""
    exito: bool
    libro_id: str
    reporte_texto: str
    resumen: Dict[str, Any]
    validacion_completa: PLEValidationResult
    error: Optional[str] = None
