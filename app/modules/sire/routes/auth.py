"""
Rutas de autenticación SIRE
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime
import logging

from ..schemas.auth_schemas import (
    SireAuthRequest,
    SireAuthResponse,
    SireLogoutRequest,
    SireLogoutResponse,
    SireStatusRequest,
    SireStatusResponse,
    SireValidateTokenRequest,
    SireValidateTokenResponse,
    SireErrorResponse
)
from ..services.auth_service import SireAuthService
from ..services.api_client import SunatApiClient
from ..services.token_manager import SireTokenManager
from ..utils.exceptions import SireAuthException, SireException
from ...companies.services import CompanyService
from ...companies.models import CompanyModel

logger = logging.getLogger(__name__)

# Router para autenticación SIRE
router = APIRouter(prefix="/sire/auth", tags=["SIRE Authentication"])

# Security scheme
security = HTTPBearer()

# Dependencias
async def get_auth_service() -> SireAuthService:
    """Obtener instancia del servicio de autenticación"""
    # TODO: Implementar inyección de dependencias correcta
    api_client = SunatApiClient()
    token_manager = SireTokenManager()
    return SireAuthService(api_client, token_manager)

async def get_company_service() -> CompanyService:
    """Obtener servicio de empresas"""
    # TODO: Implementar inyección de dependencias
    from ...companies.services import CompanyService
    return CompanyService()


@router.post("/login", response_model=SireAuthResponse, responses={
    400: {"model": SireErrorResponse},
    401: {"model": SireErrorResponse},
    500: {"model": SireErrorResponse}
})
async def login(
    auth_request: SireAuthRequest,
    auth_service: SireAuthService = Depends(get_auth_service),
    company_service: CompanyService = Depends(get_company_service)
):
    """
    Autenticar usuario con SUNAT SIRE
    
    Este endpoint realiza la autenticación completa con SUNAT:
    1. Valida las credenciales proporcionadas
    2. Se autentica con la API de SUNAT
    3. Almacena el token JWT obtenido
    4. Retorna los datos de sesión
    
    **Credenciales requeridas:**
    - RUC: Número de 11 dígitos
    - Usuario SUNAT: Usuario principal (NO SIRE_SOL)
    - Clave SOL: Clave de SUNAT Operaciones en Línea
    - Client ID: Obtenido desde SUNAT Virtual
    - Client Secret: Obtenido desde SUNAT Virtual
    """
    try:
        logger.info(f"🔐 [API] Solicitud de login para RUC {auth_request.ruc}")
        
        # Verificar que la empresa existe y tiene SIRE configurado
        company = await company_service.get_company(auth_request.ruc)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa no encontrada"
            )
        
        if not company.sire_activo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SIRE no está activo para esta empresa"
            )
        
        # Convertir request a modelo de credenciales
        from ..models.auth import SireCredentials
        credentials = SireCredentials(
            ruc=auth_request.ruc,
            sunat_usuario=auth_request.sunat_usuario,
            sunat_clave=auth_request.sunat_clave,
            client_id=auth_request.client_id,
            client_secret=auth_request.client_secret
        )
        
        # Realizar autenticación
        auth_response = await auth_service.authenticate(credentials)
        
        # Convertir a schema de respuesta
        return SireAuthResponse(
            success=auth_response.success,
            message=auth_response.message,
            access_token=auth_response.token_data.access_token,
            token_type=auth_response.token_data.token_type,
            expires_in=auth_response.token_data.expires_in,
            expires_at=auth_response.expires_at,
            session_id=auth_response.session_id,
            ruc=auth_request.ruc
        )
        
    except SireAuthException as e:
        logger.error(f"❌ [API] Error de autenticación: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"❌ [API] Error interno en login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


@router.post("/logout", response_model=SireLogoutResponse)
async def logout(
    logout_request: SireLogoutRequest,
    auth_service: SireAuthService = Depends(get_auth_service)
):
    """
    Cerrar sesión SIRE
    
    Revoca todos los tokens activos para el RUC especificado.
    """
    try:
        logger.info(f"🚪 [API] Solicitud de logout para RUC {logout_request.ruc}")
        
        # Realizar logout
        success = await auth_service.logout(logout_request.ruc)
        
        sessions_revoked = 1 if success else 0
        message = "Sesión cerrada exitosamente" if success else "No había sesiones activas"
        
        return SireLogoutResponse(
            success=success,
            message=message,
            sessions_revoked=sessions_revoked
        )
        
    except Exception as e:
        logger.error(f"❌ [API] Error en logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cerrando sesión"
        )


@router.get("/status/{ruc}", response_model=SireStatusResponse)
async def get_status(
    ruc: str,
    auth_service: SireAuthService = Depends(get_auth_service)
):
    """
    Obtener estado de autenticación SIRE
    
    Retorna el estado actual de la sesión SIRE para el RUC especificado.
    """
    try:
        logger.info(f"📊 [API] Consulta de estado para RUC {ruc}")
        
        # Validar formato de RUC
        if not ruc.isdigit() or len(ruc) != 11:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="RUC debe tener 11 dígitos numéricos"
            )
        
        # Obtener estado
        status_response = await auth_service.get_auth_status(ruc)
        
        return status_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [API] Error obteniendo estado: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo estado"
        )


@router.post("/validate", response_model=SireValidateTokenResponse)
async def validate_token(
    validate_request: SireValidateTokenRequest,
    auth_service: SireAuthService = Depends(get_auth_service)
):
    """
    Validar token JWT SIRE
    
    Verifica si un token es válido y retorna información sobre el mismo.
    """
    try:
        logger.info(f"🔍 [API] Validación de token")
        
        # Validar token
        is_valid = await auth_service.token_manager.validate_token(validate_request.access_token)
        
        # Obtener información del token
        token_info = None
        expires_at = None
        expired = True
        
        if is_valid:
            token_info = await auth_service.token_manager.get_token_info(validate_request.access_token)
            if token_info:
                expires_at = token_info.get("expires_at")
                expired = expires_at < datetime.utcnow() if expires_at else True
        
        return SireValidateTokenResponse(
            valid=is_valid and not expired,
            expired=expired,
            expires_at=expires_at,
            token_info=token_info
        )
        
    except Exception as e:
        logger.error(f"❌ [API] Error validando token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error validando token"
        )


@router.get("/health")
async def health_check():
    """
    Health check del módulo de autenticación SIRE
    """
    try:
        # Verificar conectividad con SUNAT
        api_client = SunatApiClient()
        sunat_available = await api_client.health_check()
        await api_client.close()
        
        return {
            "status": "healthy",
            "module": "sire_auth",
            "timestamp": datetime.utcnow(),
            "sunat_api_available": sunat_available,
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"❌ [API] Error en health check: {e}")
        return {
            "status": "unhealthy",
            "module": "sire_auth",
            "timestamp": datetime.utcnow(),
            "error": str(e)
        }


# Middleware para validar tokens en rutas protegidas
async def verify_sire_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: SireAuthService = Depends(get_auth_service)
) -> str:
    """
    Middleware para verificar tokens SIRE en rutas protegidas
    
    Returns:
        str: Token válido
    
    Raises:
        HTTPException: Si el token es inválido
    """
    try:
        token = credentials.credentials
        
        # Validar token
        is_valid = await auth_service.token_manager.validate_token(token)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return token
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [AUTH] Error verificando token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error verificando autenticación",
            headers={"WWW-Authenticate": "Bearer"}
        )
