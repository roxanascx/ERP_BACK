"""
Schemas Pydantic para autenticación SIRE
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator


class SireAuthRequest(BaseModel):
    """Request de autenticación SIRE"""
    ruc: str = Field(..., description="RUC del contribuyente", min_length=11, max_length=11)
    sunat_usuario: str = Field(..., description="Usuario SUNAT principal", min_length=1)
    sunat_clave: str = Field(..., description="Clave SOL", min_length=1)
    client_id: str = Field(..., description="Client ID API SUNAT", min_length=1)
    client_secret: str = Field(..., description="Client Secret API SUNAT", min_length=1)
    
    @validator('ruc')
    def validate_ruc(cls, v):
        if not v.isdigit():
            raise ValueError('RUC debe contener solo dígitos')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "ruc": "20123456789",
                "sunat_usuario": "USUARIO01",
                "sunat_clave": "clave123",
                "client_id": "client_id_example",
                "client_secret": "client_secret_example"
            }
        }


class SireAuthResponse(BaseModel):
    """Response de autenticación exitosa"""
    success: bool = Field(default=True, description="Estado de la operación")
    message: str = Field(..., description="Mensaje descriptivo")
    
    # Datos del token
    access_token: str = Field(..., description="Token de acceso JWT")
    token_type: str = Field(default="Bearer", description="Tipo de token")
    expires_in: int = Field(..., description="Segundos hasta expiración")
    expires_at: datetime = Field(..., description="Fecha de expiración")
    
    # Datos de sesión
    session_id: str = Field(..., description="ID de sesión")
    ruc: str = Field(..., description="RUC autenticado")
    
    # Metadatos
    authenticated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Autenticación exitosa",
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 3600,
                "expires_at": "2025-08-13T15:30:00",
                "session_id": "session_20123456789_1692026400",
                "ruc": "20123456789",
                "authenticated_at": "2025-08-13T14:30:00"
            }
        }


class SireLogoutRequest(BaseModel):
    """Request de logout SIRE"""
    ruc: str = Field(..., description="RUC del contribuyente", min_length=11, max_length=11)
    session_id: Optional[str] = Field(None, description="ID de sesión específica")
    revoke_all: bool = Field(default=True, description="Revocar todas las sesiones")


class SireLogoutResponse(BaseModel):
    """Response de logout"""
    success: bool = Field(..., description="Estado de la operación")
    message: str = Field(..., description="Mensaje descriptivo")
    sessions_revoked: int = Field(..., description="Número de sesiones revocadas")
    logged_out_at: datetime = Field(default_factory=datetime.utcnow)


class SireStatusRequest(BaseModel):
    """Request de estado SIRE"""
    ruc: str = Field(..., description="RUC del contribuyente", min_length=11, max_length=11)


class SireStatusResponse(BaseModel):
    """Response de estado SIRE"""
    ruc: str = Field(..., description="RUC consultado")
    sire_activo: bool = Field(..., description="SIRE está activo")
    credenciales_validas: bool = Field(..., description="Credenciales son válidas")
    
    # Estado de sesión
    sesion_activa: bool = Field(..., description="Existe sesión activa")
    token_expira_en: Optional[int] = Field(None, description="Segundos hasta expiración del token")
    
    # Actividad
    ultima_autenticacion: Optional[datetime] = Field(None, description="Última autenticación")
    ultima_actividad: Optional[datetime] = Field(None, description="Última actividad")
    
    # Servicios
    servicios_disponibles: List[str] = Field(default_factory=list, description="Servicios disponibles")
    servicios_activos: List[str] = Field(default_factory=list, description="Servicios activos")
    
    # Metadatos
    version_api: Optional[str] = Field(None, description="Versión de la API")
    servidor_region: Optional[str] = Field(None, description="Región del servidor")
    consulta_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "ruc": "20123456789",
                "sire_activo": True,
                "credenciales_validas": True,
                "sesion_activa": True,
                "token_expira_en": 3400,
                "ultima_autenticacion": "2025-08-13T14:30:00",
                "ultima_actividad": "2025-08-13T15:25:00",
                "servicios_disponibles": ["RVIE", "RCE"],
                "servicios_activos": ["RVIE", "RCE"],
                "version_api": "1.0.0",
                "servidor_region": "PE-LIMA",
                "consulta_timestamp": "2025-08-13T15:30:00"
            }
        }


class SireRefreshTokenRequest(BaseModel):
    """Request de renovación de token"""
    ruc: str = Field(..., description="RUC del contribuyente")
    refresh_token: str = Field(..., description="Token de renovación")


class SireValidateTokenRequest(BaseModel):
    """Request de validación de token"""
    access_token: str = Field(..., description="Token a validar")


class SireValidateTokenResponse(BaseModel):
    """Response de validación de token"""
    valid: bool = Field(..., description="Token es válido")
    expired: bool = Field(..., description="Token está expirado")
    expires_at: Optional[datetime] = Field(None, description="Fecha de expiración")
    token_info: Optional[dict] = Field(None, description="Información del token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "expired": False,
                "expires_at": "2025-08-13T15:30:00",
                "token_info": {
                    "subject": "20123456789",
                    "scope": "sire",
                    "client_id": "client_example"
                }
            }
        }


class SireErrorResponse(BaseModel):
    """Response de error SIRE"""
    success: bool = Field(default=False, description="Estado de la operación")
    error_code: str = Field(..., description="Código de error")
    error_message: str = Field(..., description="Mensaje de error")
    error_type: str = Field(..., description="Tipo de error")
    
    # Detalles adicionales
    details: Optional[dict] = Field(None, description="Detalles del error")
    suggested_action: Optional[str] = Field(None, description="Acción sugerida")
    
    # Metadatos
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = Field(None, description="ID de la solicitud")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error_code": "AUTH_001",
                "error_message": "Credenciales incorrectas",
                "error_type": "AUTHENTICATION_ERROR",
                "details": {
                    "field": "sunat_clave",
                    "reason": "Clave SOL inválida"
                },
                "suggested_action": "Verifique sus credenciales SUNAT",
                "timestamp": "2025-08-13T15:30:00",
                "request_id": "req_12345"
            }
        }
