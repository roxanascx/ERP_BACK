from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum

# ============ ENUMS ============

class SireMethod(str, Enum):
    """Métodos de autenticación SIRE"""
    ORIGINAL = "original"
    MIGRADO = "migrado"

# ============ SCHEMAS DE ENTRADA (REQUEST) ============

class CompanyCreate(BaseModel):
    """Schema para crear una nueva empresa"""
    ruc: str = Field(..., description="RUC de la empresa", min_length=11, max_length=11)
    razon_social: str = Field(..., description="Razón social de la empresa", min_length=1)
    direccion: Optional[str] = Field("", description="Dirección de la empresa")
    telefono: Optional[str] = Field("", description="Teléfono de la empresa")
    email: Optional[str] = Field("", description="Email de la empresa")
    activa: bool = Field(True, description="Si la empresa está activa")

class CompanyUpdate(BaseModel):
    """Schema para actualizar una empresa existente"""
    razon_social: Optional[str] = Field(None, description="Razón social de la empresa")
    direccion: Optional[str] = Field(None, description="Dirección de la empresa")
    telefono: Optional[str] = Field(None, description="Teléfono de la empresa")
    email: Optional[str] = Field(None, description="Email de la empresa")
    activa: Optional[bool] = Field(None, description="Si la empresa está activa")
    notas_internas: Optional[str] = Field(None, description="Notas internas")

class SireConfigRequest(BaseModel):
    """Schema para configurar credenciales SIRE (según manual SUNAT)"""
    client_id: str = Field(..., description="Client ID de SIRE")
    client_secret: str = Field(..., description="Client Secret de SIRE")
    sunat_usuario: str = Field(..., description="Usuario SUNAT principal")
    sunat_clave: str = Field(..., description="Clave SUNAT principal")

class AdditionalCredentialsUpdate(BaseModel):
    """Schema para actualizar credenciales adicionales"""
    # SUNAT adicionales
    sunat_usuario_secundario: Optional[str] = Field(None, description="Usuario SUNAT secundario")
    sunat_clave_secundaria: Optional[str] = Field(None, description="Clave SUNAT secundaria")
    
    # Bancarias
    sistema_bancario: Optional[str] = Field(None, description="Sistema bancario")
    banco_usuario: Optional[str] = Field(None, description="Usuario del banco")
    banco_clave: Optional[str] = Field(None, description="Clave del banco")
    
    # PDT
    pdt_usuario: Optional[str] = Field(None, description="Usuario PDT")
    pdt_clave: Optional[str] = Field(None, description="Clave PDT")
    
    # PLAME
    plame_usuario: Optional[str] = Field(None, description="Usuario PLAME")
    plame_clave: Optional[str] = Field(None, description="Clave PLAME")

# ============ SCHEMAS DE RESPUESTA (RESPONSE) ============

class CompanyResponse(BaseModel):
    """Schema de respuesta para empresa"""
    id: Optional[str] = Field(None, description="ID de la empresa")
    ruc: str = Field(..., description="RUC de la empresa")
    razon_social: str = Field(..., description="Razón social")
    direccion: str = Field(..., description="Dirección")
    telefono: str = Field(..., description="Teléfono")
    email: str = Field(..., description="Email")
    activa: bool = Field(..., description="Estado activo")
    sire_activo: bool = Field(..., description="SIRE habilitado")
    tiene_sire: bool = Field(..., description="Tiene credenciales SIRE configuradas")
    fecha_registro: datetime = Field(..., description="Fecha de registro")
    fecha_actualizacion: datetime = Field(..., description="Fecha de actualización")

class CompanyDetailResponse(CompanyResponse):
    """Schema de respuesta detallada para empresa (incluye más campos)"""
    sire_client_id: Optional[str] = Field(None, description="Client ID de SIRE")
    sunat_usuario: Optional[str] = Field(None, description="Usuario SUNAT principal")
    sunat_usuario_secundario: Optional[str] = Field(None, description="Usuario SUNAT secundario")
    sistema_bancario: Optional[str] = Field(None, description="Sistema bancario")
    banco_usuario: Optional[str] = Field(None, description="Usuario del banco")
    pdt_usuario: Optional[str] = Field(None, description="Usuario PDT")
    plame_usuario: Optional[str] = Field(None, description="Usuario PLAME")
    configuraciones: Dict[str, Any] = Field(default_factory=dict, description="Configuraciones")
    notas_internas: Optional[str] = Field(None, description="Notas internas")

class SireCredentialsResponse(BaseModel):
    """Schema de respuesta para credenciales SIRE"""
    ruc: str = Field(..., description="RUC de la empresa")
    client_id: str = Field(..., description="Client ID")
    username: str = Field(..., description="Username para autenticación")
    endpoint_url: str = Field(..., description="URL del endpoint")
    metodo: str = Field(..., description="Método de autenticación")

class SireInfoResponse(BaseModel):
    """Schema de respuesta para información de SIRE"""
    ruc: str = Field(..., description="RUC de la empresa")
    razon_social: str = Field(..., description="Razón social")
    sire_activo: bool = Field(..., description="SIRE activo")
    tiene_credenciales: bool = Field(..., description="Tiene credenciales configuradas")
    client_id: Optional[str] = Field(None, description="Client ID")
    sunat_usuario: Optional[str] = Field(None, description="Usuario SUNAT principal")
    fecha_actualizacion: datetime = Field(..., description="Fecha de actualización")

class CompanySummaryResponse(BaseModel):
    """Schema de respuesta resumida para listado de empresas"""
    ruc: str = Field(..., description="RUC de la empresa")
    razon_social: str = Field(..., description="Razón social")
    direccion: str = Field(default="", description="Dirección")
    telefono: str = Field(default="", description="Teléfono")
    email: str = Field(default="", description="Email")
    activa: bool = Field(..., description="Estado activo")
    sire_activo: bool = Field(..., description="SIRE activo")
    tiene_sire: bool = Field(..., description="Tiene credenciales SIRE")
    es_actual: bool = Field(False, description="Es la empresa actual seleccionada")
    notas_internas: Optional[str] = Field(None, description="Notas internas")

class CompanyListResponse(BaseModel):
    """Schema de respuesta para lista de empresas con metadatos"""
    companies: List[CompanySummaryResponse] = Field(..., description="Lista de empresas")
    total: int = Field(..., description="Total de empresas")
    total_con_sire: int = Field(..., description="Total con SIRE configurado")
    empresa_actual: Optional[str] = Field(None, description="RUC de la empresa actual")

# ============ SCHEMAS DE ESTADO ============

class CurrentCompanyResponse(BaseModel):
    """Schema de respuesta para la empresa actual"""
    empresa_seleccionada: bool = Field(..., description="Hay empresa seleccionada")
    ruc: Optional[str] = Field(None, description="RUC de la empresa actual")
    razon_social: Optional[str] = Field(None, description="Razón social")
    sire_activo: bool = Field(False, description="SIRE activo")
    tiene_sire: bool = Field(False, description="Tiene credenciales SIRE")

class OperationResponse(BaseModel):
    """Schema de respuesta para operaciones generales"""
    success: bool = Field(..., description="Operación exitosa")
    message: str = Field(..., description="Mensaje de la operación")
    data: Optional[Dict[str, Any]] = Field(None, description="Datos adicionales")
