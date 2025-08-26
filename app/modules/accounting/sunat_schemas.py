"""
Schemas Pydantic para las tablas SUNAT
=====================================

Esquemas de validación para las tablas de códigos SUNAT
utilizadas en la generación de archivos PLE.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# No importamos los enums restrictivos para permitir flexibilidad
# from app.modules.accounting.sunat_tables import (
#     TipoDocumentoIdentidad,
#     TipoComprobantePago, 
#     TipoLibroRegistro,
#     TipoMoneda
# )


# ================================
# SCHEMAS BASE PARA TABLAS SUNAT
# ================================

class TablaSUNATBase(BaseModel):
    """Schema base para tablas SUNAT"""
    tabla: str = Field(..., description="Nombre de la tabla")
    codigo: str = Field(..., description="Código de la tabla según SUNAT")
    descripcion: str = Field(..., description="Descripción de la tabla")
    activa: bool = Field(default=True, description="Si la tabla está activa")


class TablaSUNATResponse(TablaSUNATBase):
    """Schema para respuesta de tabla SUNAT"""
    id: str
    data: Dict[str, str] = Field(..., description="Datos código-descripción")
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    class Config:
        from_attributes = True


class TablaSUNATCreate(TablaSUNATBase):
    """Schema para crear tabla SUNAT"""
    data: Dict[str, str] = Field(..., description="Datos código-descripción")


class TablaSUNATUpdate(BaseModel):
    """Schema para actualizar tabla SUNAT"""
    descripcion: Optional[str] = None
    activa: Optional[bool] = None
    data: Optional[Dict[str, str]] = None


# ================================
# SCHEMAS PARA BÚSQUEDAS Y CONSULTAS
# ================================

class BusquedaCodigoRequest(BaseModel):
    """Schema para búsqueda de códigos"""
    tabla: str = Field(..., description="Nombre de la tabla")
    codigo: str = Field(..., description="Código a buscar")


class BusquedaCodigoResponse(BaseModel):
    """Schema para respuesta de búsqueda de código"""
    tabla: str
    codigo: str
    descripcion: Optional[str]
    encontrado: bool


class BusquedaDescripcionRequest(BaseModel):
    """Schema para búsqueda por descripción"""
    tabla: str = Field(..., description="Nombre de la tabla")
    descripcion: str = Field(..., min_length=3, description="Descripción parcial a buscar")


class BusquedaDescripcionResponse(BaseModel):
    """Schema para respuesta de búsqueda por descripción"""
    tabla: str
    descripcion_buscada: str
    resultados: List[Dict[str, str]] = Field(default_factory=list)
    total_encontrados: int = 0


class ValidacionCodigoRequest(BaseModel):
    """Schema para validación de códigos"""
    tabla: str = Field(..., description="Nombre de la tabla")
    codigo: str = Field(..., description="Código a validar")


class ValidacionCodigoResponse(BaseModel):
    """Schema para respuesta de validación"""
    tabla: str
    codigo: str
    valido: bool
    descripcion: Optional[str] = None
    mensaje: Optional[str] = None


# ================================
# SCHEMAS PARA ESTADÍSTICAS
# ================================

class EstadisticasTablaDetalle(BaseModel):
    """Schema para estadísticas detalladas de una tabla"""
    tabla: str
    descripcion: str
    total_codigos: int
    fecha_actualizacion: Optional[datetime]


class EstadisticasTablasResponse(BaseModel):
    """Schema para estadísticas generales de tablas"""
    total_tablas: int
    tablas_activas: int
    tablas_detalle: List[EstadisticasTablaDetalle]
    fecha_consulta: datetime


# ================================
# SCHEMAS ESPECÍFICOS POR TABLA
# ================================

class DocumentoIdentidadItem(BaseModel):
    """Schema para item de documento de identidad"""
    codigo: str = Field(..., description="Código del documento")
    descripcion: str = Field(..., description="Descripción del documento")


class ComprobantePagoItem(BaseModel):
    """Schema para item de comprobante de pago"""
    codigo: str = Field(..., description="Código del comprobante")
    descripcion: str = Field(..., description="Descripción del comprobante")


class LibroRegistroItem(BaseModel):
    """Schema para item de libro/registro"""
    codigo: str = Field(..., description="Código del libro")
    descripcion: str = Field(..., description="Descripción del libro")


class MonedaItem(BaseModel):
    """Schema para item de moneda"""
    codigo: str = Field(..., description="Código de moneda")
    descripcion: str = Field(..., description="Descripción de la moneda")


# ================================
# SCHEMAS PARA LISTADOS COMPLETOS
# ================================

class ListadoDocumentosResponse(BaseModel):
    """Schema para listado completo de documentos de identidad"""
    tabla: str = "tipos_documento_identidad"
    items: List[DocumentoIdentidadItem]
    total: int


class ListadoComprobantesResponse(BaseModel):
    """Schema para listado completo de comprobantes de pago"""
    tabla: str = "tipos_comprobantes_pago"
    items: List[ComprobantePagoItem]
    total: int


class ListadoLibrosResponse(BaseModel):
    """Schema para listado completo de libros y registros"""
    tabla: str = "codigos_libros_registros" 
    items: List[LibroRegistroItem]
    total: int


class ListadoMonedasResponse(BaseModel):
    """Schema para listado completo de monedas"""
    tabla: str = "tipos_moneda"
    items: List[MonedaItem]
    total: int


# ================================
# SCHEMAS PARA INICIALIZACIÓN
# ================================

class InicializacionTablasSUNATRequest(BaseModel):
    """Schema para solicitud de inicialización"""
    forzar_reinicio: bool = Field(default=False, description="Forzar reinicio de tablas existentes")
    tablas_especificas: Optional[List[str]] = Field(default=None, description="Inicializar solo tablas específicas")


class InicializacionTablasSUNATResponse(BaseModel):
    """Schema para respuesta de inicialización"""
    exitoso: bool
    mensaje: str
    tablas_inicializadas: List[str]
    total_tablas: int
    errores: List[str] = Field(default_factory=list)
    fecha_inicializacion: datetime


# ================================
# SCHEMAS PARA EXPORTACIÓN
# ================================

class ExportacionTablasRequest(BaseModel):
    """Schema para solicitud de exportación"""
    tablas: Optional[List[str]] = Field(default=None, description="Tablas específicas a exportar")
    formato: str = Field(default="json", pattern="^(json|csv|excel)$")
    incluir_metadatos: bool = Field(default=True)


class ExportacionTablasResponse(BaseModel):
    """Schema para respuesta de exportación"""
    formato: str
    nombre_archivo: str
    tamaño_bytes: int
    tablas_incluidas: List[str]
    fecha_exportacion: datetime
    url_descarga: Optional[str] = None


# ================================
# SCHEMAS PARA VALIDACIONES MASIVAS
# ================================

class ValidacionMasivaRequest(BaseModel):
    """Schema para validación masiva de códigos"""
    validaciones: List[ValidacionCodigoRequest]


class ValidacionMasivaResponse(BaseModel):
    """Schema para respuesta de validación masiva"""
    total_validaciones: int
    validaciones_exitosas: int
    validaciones_fallidas: int
    resultados: List[Dict[str, Any]]
    fecha_validacion: datetime


# ================================
# SCHEMAS PARA RESPUESTAS ACTUALIZADAS
# ================================

class InicializacionResponse(BaseModel):
    """Schema actualizado para respuesta de inicialización"""
    exitoso: bool
    mensaje: str
    total_tablas: int
    tablas_creadas: int = 0
    tablas_actualizadas: int = 0
    fecha_inicializacion: datetime


class BusquedaDescripcionResponse(BaseModel):
    """Schema actualizado para respuesta de búsqueda por descripción"""
    tabla: str
    descripcion: str
    resultados: List[Dict[str, str]] = Field(default_factory=list)
    total_encontrados: int = 0


# ================================
# SCHEMAS PARA AUTOCOMPLETE
# ================================

class AutocompleteRequest(BaseModel):
    """Schema para solicitud de autocompletado"""
    tabla: str = Field(..., description="Nombre de la tabla")
    termino: str = Field(..., min_length=1, max_length=50, description="Término de búsqueda")
    limite: int = Field(default=10, ge=1, le=50, description="Límite de resultados")


class AutocompleteItem(BaseModel):
    """Schema para item de autocompletado"""
    codigo: str
    descripcion: str
    coincidencia: str  # Parte que coincide con la búsqueda


class AutocompleteResponse(BaseModel):
    """Schema para respuesta de autocompletado"""
    tabla: str
    termino: str
    resultados: List[Dict[str, str]]
    total_encontrados: int
    limite: int


# ================================
# SCHEMAS PARA AUDITORÍA
# ================================

class RegistroAuditoriaTabla(BaseModel):
    """Schema para registro de auditoría de cambios en tablas"""
    tabla: str
    operacion: str = Field(..., pattern="^(create|update|delete|read)$")
    usuario: Optional[str] = None
    ip_address: Optional[str] = None
    datos_anteriores: Optional[Dict[str, Any]] = None
    datos_nuevos: Optional[Dict[str, Any]] = None
    fecha_operacion: datetime = Field(default_factory=datetime.utcnow)


class ConsultaAuditoriaRequest(BaseModel):
    """Schema para consulta de auditoría"""
    tabla: Optional[str] = None
    operacion: Optional[str] = None
    usuario: Optional[str] = None
    fecha_desde: Optional[datetime] = None
    fecha_hasta: Optional[datetime] = None
    limite: int = Field(default=100, ge=1, le=1000)


class ConsultaAuditoriaResponse(BaseModel):
    """Schema para respuesta de consulta de auditoría"""
    registros: List[RegistroAuditoriaTabla]
    total_registros: int
    pagina: int = 1
    limite: int
    total_paginas: int


# ================================
# SCHEMAS PARA CONFIGURACIÓN
# ================================

class ConfiguracionTablasRequest(BaseModel):
    """Schema para configuración de tablas"""
    cache_habilitado: bool = Field(default=True)
    tiempo_cache_minutos: int = Field(default=60, ge=1, le=1440)
    log_consultas: bool = Field(default=False)
    validacion_estricta: bool = Field(default=True)


class ConfiguracionTablasResponse(BaseModel):
    """Schema para respuesta de configuración"""
    configuracion_aplicada: bool
    configuracion_actual: Dict[str, Any]
    mensaje: str
    fecha_actualizacion: datetime


# ================================
# FUNCIONES DE VALIDACIÓN CUSTOMIZADAS
# ================================

def validar_nombre_tabla(nombre_tabla: str) -> bool:
    """Validar que el nombre de tabla sea válido"""
    tablas_validas = [
        "tipos_documento_identidad",
        "tipos_comprobantes_pago",
        "codigos_libros_registros",
        "tipos_moneda",
        "tipos_medio_pago",
        "cuentas_contables",
        "codigos_pais",
        "tipos_documento",
        "estados_contribuyente",
        "condicion_domicilio",
        "tipos_operacion",
        "clasificacion_bienes_servicios"
    ]
    return nombre_tabla in tablas_validas


# Validator personalizado para schemas
@field_validator("tabla")
@classmethod
def validate_tabla_name(cls, v):
    if not validar_nombre_tabla(v):
        raise ValueError(f"Nombre de tabla inválido: {v}")
    return v


# Los validadores ya están aplicados a través de field_validator decorators
# AutocompleteRequest ya tiene el validador aplicado
