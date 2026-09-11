from pydantic import BaseModel, Field, field_validator, validator
from typing import Optional, List, Dict, Any
from datetime import date, datetime
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
    # Acepta "YYYY" (ejercicio completo), "YYYYMM" o "YYYY-MM" (mes concreto,
    # formato SUNAT) - el formulario de alta invita a las tres formas.
    periodo: str = Field(..., pattern=r"^\d{4}(-\d{2}|\d{2})?$")
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

    @field_validator("fecha", mode="before")
    @classmethod
    def fecha_como_texto(cls, v):
        """
        Aceptar tambien `datetime` y `date`.

        No es una comodidad: el libro diario se lee entero de una vez, asi que
        **una sola linea con la fecha mal tipada devolvia un 404 para todo el
        libro**, incluidos los asientos correctos. Normalizar aqui hace que el
        peor caso sea una fila rara, no un libro inaccesible.
        """
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%d")
        if isinstance(v, date):
            return v.isoformat()
        return v
    glosa: str = Field(..., max_length=500)
    codigoLibro: str = Field(default="5.1")  # Libro Diario por defecto
    numeroDocumento: str = Field(..., max_length=50)
    cuentaContable: Dict[str, str]  # {codigo: str, denominacion: str}
    debe: float = Field(ge=0)
    haber: float = Field(ge=0)

    # Identificador de la operación/asiento padre. El modelo guarda cada
    # movimiento de cuenta como un documento independiente ("plano"), así
    # que varias líneas (debe/haber de una misma operación) comparten este
    # valor para poder reconstruir el asiento agrupado y, en la exportación
    # PLE a SUNAT, asignarles un mismo CUO con correlativo local por línea
    # (ver ple_formatter_sunat_v3.formatear_lote_asientos).
    numeroAsiento: Optional[str] = Field(None, max_length=50)
    
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
    numeroAsiento: Optional[str] = None


class AsientoContableResponse(AsientoContableBase):
    """Schema para respuesta de asientos contables"""
    id: str
    empresaId: str
    usuarioCreacion: Optional[str] = None
    fechaCreacion: Optional[datetime] = None
    fechaModificacion: Optional[datetime] = None

    # Trazabilidad de la contabilizacion automatica. Se guardaba pero no se
    # exponia, asi que en la pantalla del libro no habia forma de saber si un
    # asiento venia de ventas o de compras, ni a que lote pertenecia para
    # poder deshacerlo.
    codigoLibroOrigen: Optional[str] = Field(
        None, description="Codigo del subdiario que origino el asiento (PLE 5.1)"
    )
    lote_contabilizacion: Optional[str] = None
    origen: Optional[str] = None

    class Config:
        from_attributes = True


class LibroDiarioBase(BaseModel):
    """Schema base para libro diario"""
    descripcion: str = Field(..., max_length=200)
    # Acepta "YYYY" (ejercicio completo), "YYYYMM" o "YYYY-MM" (mes concreto,
    # formato SUNAT) - el formulario de alta invita a las tres formas.
    periodo: str = Field(..., pattern=r"^\d{4}(-\d{2}|\d{2})?$")
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
    # En el listado los asientos no se cargan (serian miles de lineas por
    # libro), pero la tarjeta necesita saber cuantos hay. Se cuenta aparte,
    # agrupando por numeroAsiento: la coleccion guarda una fila por linea,
    # asi que contar documentos daria un numero inflado.
    totalAsientos: int = 0
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


# ================================
# SCHEMAS SUNAT V3 - CUMPLIMIENTO COMPLETO
# ================================

class TipoAsientoSunat(str, Enum):
    """Tipos de asientos según SUNAT"""
    APERTURA = "A"      # Asiento de apertura
    OPERACION = "M"     # Asiento por operaciones diversas
    AJUSTE = "J"        # Asiento de ajuste
    CIERRE = "C"        # Asiento de cierre
    DESTINO = "D"       # Asiento de destino
    TRANSFERENCIA = "T" # Asiento de transferencia


class EstadoOperacionSunat(str, Enum):
    """Estados de operación según SUNAT"""
    ACTIVO = "1"
    ANULADO = "8"
    AJUSTE = "9"


class DetalleAsientoSunatV3(BaseModel):
    """Schema extendido para cumplir estructura SUNAT 24 campos"""
    # Campos actuales mantenidos para compatibilidad
    codigoCuenta: str = Field(..., min_length=3, max_length=24)
    denominacionCuenta: str = Field(..., max_length=100)
    descripcion: str = Field(..., max_length=200)
    debe: Optional[float] = Field(default=0.0, ge=0)
    haber: Optional[float] = Field(default=0.0, ge=0)
    
    # NUEVOS CAMPOS SUNAT OBLIGATORIOS
    codigoUnidadOperacion: Optional[str] = Field(None, max_length=24)
    codigoCentroCosto: Optional[str] = Field(None, max_length=24)
    tipoMonedaOrigen: str = Field(default="PEN", max_length=3)
    tipoDocumentoIdentidad: Optional[str] = Field(None, max_length=2)
    numeroDocumentoIdentidad: Optional[str] = Field(None, max_length=15)
    tipoComprobantePago: Optional[str] = Field(None, max_length=2)
    numeroSerieComprobante: Optional[str] = Field(None, max_length=20)
    numeroComprobantePago: Optional[str] = Field(None, max_length=20)
    fechaContable: Optional[str] = Field(None, pattern=r"^\d{2}/\d{2}/\d{4}$")
    fechaVencimiento: Optional[str] = Field(None, pattern=r"^\d{2}/\d{2}/\d{4}$")
    fechaOperacion: Optional[str] = Field(None, pattern=r"^\d{2}/\d{2}/\d{4}$")
    glosaReferencial: Optional[str] = Field(None, max_length=200)
    debeMonedaOrigen: Optional[float] = Field(default=0.0, ge=0)
    haberMonedaOrigen: Optional[float] = Field(default=0.0, ge=0)
    tipoCambio: Optional[float] = Field(default=1.0, gt=0)
    
    @validator('codigoCuenta')
    def validate_codigo_cuenta_sunat(cls, v):
        """Validar código de cuenta según PCGR"""
        import re
        # Validar formato: solo números y punto como separador opcional
        if not re.match(r'^[0-9]+(\.[0-9]+)*$', v):
            raise ValueError(f'Código cuenta {v} no cumple formato PCGR (solo números y puntos)')
        return v

    @validator('debe', 'haber')
    def validate_debe_haber_exclusivo(cls, v, values):
        """Validar que debe y haber sean mutuamente exclusivos"""
        # Al menos uno debe tener valor mayor a cero
        if 'debe' in values and 'haber' in values:
            debe_val = values.get('debe', 0) or 0
            haber_val = values.get('haber', 0) or 0
            
            if debe_val == 0 and haber_val == 0:
                raise ValueError('Debe especificar un valor en Debe o Haber')
            if debe_val > 0 and haber_val > 0:
                raise ValueError('No puede tener valores en Debe y Haber al mismo tiempo')
        return v


class AsientoContableSunatV3(BaseModel):
    """Schema completo SUNAT para asientos contables"""
    # Campos actuales mantenidos para compatibilidad
    numero: str = Field(..., pattern=r"^[0-9]{1,10}$")
    fecha: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    descripcion: str = Field(..., max_length=200)
    detalles: List[DetalleAsientoSunatV3] = Field(..., min_items=2)
    
    # NUEVOS CAMPOS SUNAT OBLIGATORIOS
    tipoAsiento: TipoAsientoSunat = Field(default=TipoAsientoSunat.OPERACION)
    codigoLibroOrigen: Optional[str] = Field(None, pattern=r"^[0-9]{2}$")
    numeroCorrelativoOrigen: Optional[str] = Field(None, max_length=10)
    numeroDocumentoSustentatorio: Optional[str] = Field(None, max_length=20)
    estadoOperacion: EstadoOperacionSunat = Field(default=EstadoOperacionSunat.ACTIVO)
    
    @validator('detalles')
    def validate_detalles_sunat(cls, v):
        """Validación extendida para SUNAT"""
        # 1. Validar balance
        total_debe = sum(detalle.debe or 0 for detalle in v)
        total_haber = sum(detalle.haber or 0 for detalle in v)
        
        if abs(total_debe - total_haber) > 0.01:
            raise ValueError(f'Asiento desbalanceado. Debe: {total_debe}, Haber: {total_haber}')
        
        # 2. Validar que al menos una cuenta sea de nivel hoja (con punto)
        cuentas_hoja = [d for d in v if '.' in d.codigoCuenta]
        if len(cuentas_hoja) == 0:
            raise ValueError('Al menos una cuenta debe ser de nivel hoja (subcuenta con punto)')
        
        # 3. Validar códigos únicos en el asiento
        codigos_cuenta = [d.codigoCuenta for d in v]
        if len(codigos_cuenta) != len(set(codigos_cuenta)):
            raise ValueError('No se permiten códigos de cuenta duplicados en el mismo asiento')
        
        return v


class LibroDiarioSunatV3(BaseModel):
    """Schema completo SUNAT para libro diario"""
    # Campos actuales mantenidos para compatibilidad
    descripcion: str = Field(..., max_length=200)
    periodo: str = Field(..., pattern=r"^\d{4}(-\d{2})?$")
    estado: EstadoLibroDiario = EstadoLibroDiario.BORRADOR
    moneda: str = Field(default="PEN")
    tipoLibro: str = Field(default="5.1")
    empresaId: str
    
    # NUEVOS CAMPOS SUNAT
    fechaInicioOperaciones: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    ingresosBrutosAnteriores: Optional[float] = Field(None, ge=0)
    minDigitosCuenta: int = Field(default=3, ge=3, le=24)
    formatoPLE: str = Field(default="5.1")
    requiereValidacionSunat: bool = Field(default=True)
    
    @validator('minDigitosCuenta')
    def validate_min_digitos_por_ingresos(cls, v, values):
        """Validar mínimo dígitos según ingresos UIT anteriores"""
        ingresos = values.get('ingresosBrutosAnteriores', 0)
        uit_2024 = 4950.0  # UIT 2024
        
        if ingresos and ingresos >= (100 * uit_2024):
            if v < 4:
                raise ValueError('Empresas con ingresos ≥100 UIT requieren mínimo 4 dígitos en códigos de cuenta')
        
        return v


# Schemas para respuesta con datos SUNAT
class AsientoContableSunatResponseV3(AsientoContableSunatV3):
    """Schema para respuesta de asientos SUNAT V3"""
    id: str
    empresaId: str
    libroId: str
    usuarioCreacion: Optional[str] = None
    fechaCreacion: Optional[datetime] = None
    fechaModificacion: Optional[datetime] = None
    
    # Campos calculados para SUNAT
    numeroCorrelativoFormateado: Optional[str] = None  # M000000001 formato
    codigoUnicoOperacion: Optional[str] = None         # Para campo 2 PLE
    validacionSunat: Optional[Dict[str, Any]] = None   # Resultado validación
    
    class Config:
        from_attributes = True


class LibroDiarioSunatResponseV3(LibroDiarioSunatV3):
    """Schema para respuesta de libro diario SUNAT V3"""
    id: str
    ruc: str
    razonSocial: str
    asientos: List[AsientoContableSunatResponseV3] = []
    totalDebe: float = 0.0
    totalHaber: float = 0.0
    fechaCreacion: Optional[datetime] = None
    fechaModificacion: Optional[datetime] = None
    usuarioCreacion: Optional[str] = None
    usuarioModificacion: Optional[str] = None
    
    # Campos específicos SUNAT
    configuracionSunat: Optional[Dict[str, Any]] = None
    estadoValidacionSunat: Optional[str] = None  # "conforme", "observado", "no_validado"
    ultimaValidacionSunat: Optional[datetime] = None
    nombreArchivoPLE: Optional[str] = None
    
    class Config:
        from_attributes = True


# ================================
# SCHEMAS PLE SUNAT V3 - FASE 3
# ================================

class PLEGenerarZipV3Request(BaseModel):
    """Request para generar archivo PLE en formato ZIP SUNAT V3"""
    libro_diario_id: str = Field(..., description="ID del libro diario")
    validar_antes_generar: bool = Field(True, description="Validar datos antes de generar")
    incluir_metadatos: bool = Field(True, description="Incluir metadatos en la respuesta")
    directorio_salida: Optional[str] = Field(None, description="Directorio de salida (opcional)")


class PLEPreviewV3Request(BaseModel):
    """Request para generar preview del archivo PLE SUNAT V3"""
    libro_diario_id: str = Field(..., description="ID del libro diario")
    cantidad_lineas: int = Field(10, description="Cantidad de líneas para preview", ge=1, le=100)


class PLEZipMetadataResponse(BaseModel):
    """Metadatos del archivo ZIP generado"""
    nombre_archivo_zip: str
    nombre_archivo_txt_interno: str
    tamaño_txt_bytes: int
    tamaño_zip_bytes: int
    ratio_compresion: float
    hash_md5_txt: str
    hash_md5_zip: str
    fecha_creacion: datetime
    metodo_compresion: str
    nivel_compresion: int
    es_valido: bool
    errores: List[str]


class PLEArchivoResponse(BaseModel):
    """Información del archivo PLE generado"""
    nombre_archivo: str
    tamaño_txt: int
    tamaño_zip: Optional[int]
    total_lineas: int
    fecha_generacion: datetime
    errores: List[str]
    resumen_validacion: Dict[str, Any]
    metadatos: Dict[str, Any]


class PLEGenerarZipV3Response(BaseModel):
    """Response completa para generación de archivo PLE ZIP V3"""
    success: bool
    archivo_ple: PLEArchivoResponse
    metadata_zip: PLEZipMetadataResponse
    mensaje: str


class PLEPreviewResponse(BaseModel):
    """Response para preview de archivo PLE"""
    success: bool
    preview: Dict[str, Any]
    informacion: Dict[str, Any]


class PLEValidacionResult(BaseModel):
    """Resultado de validación de datos para PLE"""
    es_valido: bool
    errores: List[str]
    advertencias: List[str]
    estadisticas: Dict[str, Any]


class PLEValidacionResponse(BaseModel):
    """Response para validación de datos PLE"""
    success: bool
    validacion: PLEValidacionResult


class PLEEstadisticas(BaseModel):
    """Estadísticas generales de archivos PLE"""
    total_archivos: int = 0
    total_lineas: int = 0
    total_debe: float = 0.0
    total_haber: float = 0.0
    ultimo_periodo: Optional[str] = None
    archivos_ultimo_mes: int = 0
    tamaño_total_mb: float = 0.0


class PLEArchivoModel(BaseModel):
    """Modelo para archivos PLE almacenados"""
    id: Optional[str] = Field(None, alias="_id")
    empresa_id: str
    nombre_archivo: str
    tipo_archivo: str = "PLE_LIBRO_DIARIO"
    periodo: str  # YYYYMM
    ruc_empresa: str
    
    # Metadatos del archivo
    tamaño_txt_bytes: int
    tamaño_zip_bytes: int
    total_lineas: int
    total_debe: float
    total_haber: float
    
    # Metadatos de generación
    fecha_generacion: datetime
    metadatos_zip: Dict[str, Any]
    opciones_generacion: Dict[str, Any]
    
    # Estado y validación
    estado: str = "generado"  # generado, error, eliminado
    validacion_sunat: Dict[str, Any] = {}
    errores: List[str] = []
    
    # Archivos en disco
    ruta_archivo_txt: Optional[str] = None
    ruta_archivo_zip: Optional[str] = None
    hash_md5_zip: str
    
    class Config:
        populate_by_name = True


class PLEDashboardResponse(BaseModel):
    """Response del dashboard PLE"""
    archivos_recientes: List[PLEArchivoModel]
    estadisticas: PLEEstadisticas
    configuracion_sunat: Dict[str, Any]
    ultima_actualizacion: datetime
