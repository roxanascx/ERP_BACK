"""
Modelos de autenticación SIRE
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SireCredentials(BaseModel):
    """Credenciales para autenticación SIRE"""
    ruc: str = Field(..., description="RUC del contribuyente")
    sunat_usuario: str = Field(..., description="Usuario SUNAT principal")
    sunat_clave: str = Field(..., description="Clave SOL")
    client_id: str = Field(..., description="Client ID API SUNAT")
    client_secret: str = Field(..., description="Client Secret API SUNAT")


class SireTokenData(BaseModel):
    """Datos del token JWT SIRE"""
    access_token: str = Field(..., description="Token de acceso JWT")
    token_type: str = Field(default="Bearer", description="Tipo de token")
    expires_in: int = Field(..., description="Tiempo de expiración en segundos")
    refresh_token: Optional[str] = Field(None, description="Token de renovación")
    scope: Optional[str] = Field(None, description="Alcance del token")


class SireSession(BaseModel):
    """Sesión activa SIRE"""
    ruc: str = Field(..., description="RUC del contribuyente")
    access_token: str = Field(..., description="Token de acceso")
    refresh_token: Optional[str] = Field(None, description="Token de renovación")
    expires_at: datetime = Field(..., description="Fecha de expiración")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True, description="Estado de la sesión")


class SireAuthResponse(BaseModel):
    """Respuesta de autenticación exitosa"""
    success: bool = Field(default=True)
    message: str = Field(default="Autenticación exitosa")
    token_data: SireTokenData
    session_id: str = Field(..., description="ID de sesión")
    expires_at: datetime = Field(..., description="Fecha de expiración")


class SireAuthError(BaseModel):
    """Error de autenticación SIRE"""
    success: bool = Field(default=False)
    error_code: str = Field(..., description="Código de error")
    error_message: str = Field(..., description="Mensaje de error")
    details: Optional[dict] = Field(None, description="Detalles adicionales del error")
