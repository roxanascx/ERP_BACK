"""
Servicio de autenticación SIRE
Maneja la autenticación con SUNAT y gestión de s        except SireAuthException:
            # Registrar intento fallido
            await self._register_failed_attempt(normalized_ruc)
            raise
        except Exception as e:
            await self._register_failed_attempt(normalized_ruc)
            logger.error(f"❌ [AUTH] Error inesperado en autenticación para RUC {normalized_ruc}: {e}")
            raise SireAuthException(f"Error inesperado: {str(e)}")
"""

import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from ..models.auth import SireCredentials, SireTokenData, SireAuthResponse, SireAuthError
from ..models.responses import SireStatusResponse
from ..utils.exceptions import SireAuthException, SireConfigurationException
from .api_client import SunatApiClient
from .token_manager import SireTokenManager
from .credentials_manager import credentials_manager

logger = logging.getLogger(__name__)


class SireAuthService:
    """Servicio de autenticación SIRE con SUNAT"""
    
    def __init__(self, api_client: SunatApiClient, token_manager: SireTokenManager):
        """
        Inicializar servicio de autenticación
        
        Args:
            api_client: Cliente para comunicación con SUNAT
            token_manager: Gestor de tokens JWT
        """
        self.api_client = api_client
        self.token_manager = token_manager
        
        # Cache de estados de autenticación
        self.auth_cache: Dict[str, Dict[str, Any]] = {}
        self.max_auth_attempts = 3
        self.auth_cooldown = 300  # 5 minutos
    
    def _normalize_ruc(self, ruc: str) -> str:
        """
        Normalizar RUC eliminando espacios y caracteres extra
        
        Args:
            ruc: RUC a normalizar
            
        Returns:
            str: RUC normalizado
        """
        if not ruc:
            return ruc
            
        # Limpiar espacios y caracteres especiales
        normalized = ''.join(c for c in str(ruc).strip() if c.isdigit())
        
        # Validar longitud (RUC debe tener 11 dígitos)
        if len(normalized) != 11:
            pass  # RUC no tiene 11 dígitos, pero continuamos
        
        return normalized
        
    async def authenticate(self, credentials: SireCredentials) -> SireAuthResponse:
        """
        Autenticar usuario con SUNAT SIRE
        
        Args:
            credentials: Credenciales SIRE del usuario
        
        Returns:
            SireAuthResponse: Respuesta de autenticación exitosa
        
        Raises:
            SireAuthException: Error de autenticación
        """
        try:
            # Normalizar RUC antes de cualquier operación
            normalized_ruc = self._normalize_ruc(credentials.ruc)
            
            # Validar credenciales
            await self._validate_credentials(credentials)
            
            # Verificar si ya existe una sesión válida
            existing_token = await self.token_manager.get_valid_token(normalized_ruc)
            if existing_token:
                return await self._build_auth_response(existing_token, normalized_ruc, reused=True)
            
            # Verificar cooldown de intentos fallidos
            await self._check_auth_cooldown(normalized_ruc)
            
            # Realizar autenticación con SUNAT
            token_data = await self._authenticate_with_sunat(credentials)
            
            # Almacenar token y crear sesión
            session_id = await self._store_authentication_session(credentials, token_data)
            
            # Limpiar historial de intentos fallidos
            await self._clear_failed_attempts(normalized_ruc)
            
            # Construir respuesta exitosa
            response = await self._build_auth_response(token_data.access_token, normalized_ruc)
            
            return response
            
        except SireAuthException:
            # Registrar intento fallido
            await self._register_failed_attempt(credentials.ruc)
            raise
        except Exception as e:
            await self._register_failed_attempt(credentials.ruc)
            raise SireAuthException(f"Error interno de autenticación: {e}")
    
    async def refresh_authentication(self, ruc: str, refresh_token: str) -> SireAuthResponse:
        """
        Renovar autenticación usando refresh token
        
        Args:
            ruc: RUC del contribuyente
            refresh_token: Token de renovación
        
        Returns:
            SireAuthResponse: Nueva respuesta de autenticación
        """
        try:
            # TODO: Implementar renovación con refresh token
            # Por ahora, requerimos nueva autenticación completa
            raise SireAuthException("Renovación automática no disponible, reautentique")
            
        except Exception as e:
            raise SireAuthException(f"Error renovando autenticación: {e}")
    
    async def logout(self, ruc: str) -> bool:
        """
        Cerrar sesión y revocar tokens
        
        Args:
            ruc: RUC del contribuyente
        
        Returns:
            bool: True si se cerró sesión exitosamente
        """
        try:
            # Revocar todos los tokens activos
            revoked = await self.token_manager.revoke_token(ruc)
            
            # Limpiar cache de autenticación
            self.auth_cache.pop(ruc, None)
            
            return revoked
            
        except Exception as e:
            return False
    
    async def validate_session(self, ruc: str) -> bool:
        """
        Validar si existe sesión activa válida
        
        Args:
            ruc: RUC del contribuyente
        
        Returns:
            bool: True si la sesión es válida
        """
        try:
            token = await self.token_manager.get_valid_token(ruc)
            return token is not None
            
        except Exception:
            return False
    
    async def get_auth_status(self, ruc: str) -> SireStatusResponse:
        """
        Obtener estado de autenticación SIRE
        
        Args:
            ruc: RUC del contribuyente
        
        Returns:
            SireStatusResponse: Estado actual de SIRE
        """
        try:
            # Verificar sesión activa
            token = await self.token_manager.get_valid_token(ruc)
            session_active = token is not None
            
            # Obtener información del token si existe
            token_expires_in = None
            if token:
                token_info = await self.token_manager.get_token_info(token)
                if token_info and token_info.get("expires_at"):
                    expires_at = token_info["expires_at"]
                    token_expires_in = int((expires_at - datetime.utcnow()).total_seconds())
                    if token_expires_in < 0:
                        token_expires_in = 0
            
            # Verificar disponibilidad de API SUNAT
            api_available = await self.api_client.health_check()
            
            # Servicios disponibles
            servicios_disponibles = ["RVIE", "RCE"] if api_available else []
            servicios_activos = servicios_disponibles if session_active else []
            
            return SireStatusResponse(
                ruc=ruc,
                sire_activo=True,  # Basado en configuración de empresa
                credenciales_validas=session_active,
                sesion_activa=session_active,
                token_expira_en=token_expires_in,
                servicios_disponibles=servicios_disponibles,
                servicios_activos=servicios_activos,
                version_api="1.0.0",
                servidor_region="PE-LIMA"
            )
            
        except Exception as e:
            return SireStatusResponse(
                ruc=ruc,
                sire_activo=False,
                credenciales_validas=False,
                sesion_activa=False,
                servicios_disponibles=[],
                servicios_activos=[]
            )
    
    # Métodos privados de soporte
    
    async def _validate_credentials(self, credentials: SireCredentials):
        """Validar formato y completitud de credenciales"""
        if not credentials.ruc or len(credentials.ruc) != 11:
            raise SireAuthException("RUC debe tener 11 dígitos")
        
        if not credentials.sunat_usuario:
            raise SireAuthException("Usuario SUNAT es requerido")
        
        if not credentials.sunat_clave:
            raise SireAuthException("Clave SOL es requerida")
        
        if not credentials.client_id:
            raise SireAuthException("Client ID es requerido")
        
        if not credentials.client_secret:
            raise SireAuthException("Client Secret es requerido")
        
        # Validar formato de RUC
        if not credentials.ruc.isdigit():
            raise SireAuthException("RUC debe contener solo dígitos")
    
    async def _check_auth_cooldown(self, ruc: str):
        """Verificar cooldown de intentos fallidos"""
        auth_info = self.auth_cache.get(ruc, {})
        failed_attempts = auth_info.get("failed_attempts", 0)
        last_attempt = auth_info.get("last_failed_attempt")
        
        if failed_attempts >= self.max_auth_attempts and last_attempt:
            time_since_last = (datetime.utcnow() - last_attempt).total_seconds()
            if time_since_last < self.auth_cooldown:
                remaining = int(self.auth_cooldown - time_since_last)
                raise SireAuthException(
                    f"Demasiados intentos fallidos. Intente nuevamente en {remaining} segundos"
                )
    
    async def _authenticate_with_sunat(self, credentials: SireCredentials) -> SireTokenData:
        """Realizar autenticación con API SUNAT usando credenciales correctas"""
        try:
            # NUEVO: Usar credenciales del manager que funcionan (ahora async)
            working_credentials = await credentials_manager.get_credentials(credentials.ruc)
            
            if working_credentials:
                # Usar las credenciales que sabemos que funcionan
                token_data = await self.api_client.authenticate(working_credentials)
            else:
                # Usar las credenciales proporcionadas como fallback
                token_data = await self.api_client.authenticate(credentials)
            
            return token_data
            
        except Exception as e:
            # Mapear errores comunes
            if "401" in str(e) or "unauthorized" in str(e).lower():
                raise SireAuthException("Credenciales incorrectas")
            elif "timeout" in str(e).lower():
                raise SireAuthException("Timeout de conexión con SUNAT")
            elif "connection" in str(e).lower():
                raise SireAuthException("Error de conexión con SUNAT")
            else:
                raise SireAuthException(f"Error de autenticación: {e}")
    
    async def _store_authentication_session(self, credentials: SireCredentials, token_data: SireTokenData) -> str:
        """Almacenar sesión de autenticación"""
        # Crear hash de credenciales para validación
        credentials_hash = self._hash_credentials(credentials)
        
        # Almacenar token
        session_id = await self.token_manager.store_token(
            credentials.ruc, 
            token_data, 
            credentials_hash
        )
        
        return session_id
    
    def _hash_credentials(self, credentials: SireCredentials) -> str:
        """Crear hash de credenciales para validación"""
        content = f"{credentials.ruc}:{credentials.sunat_usuario}:{credentials.client_id}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def _register_failed_attempt(self, ruc: str):
        """Registrar intento de autenticación fallido"""
        if ruc not in self.auth_cache:
            self.auth_cache[ruc] = {}
        
        self.auth_cache[ruc]["failed_attempts"] = self.auth_cache[ruc].get("failed_attempts", 0) + 1
        self.auth_cache[ruc]["last_failed_attempt"] = datetime.utcnow()
    
    async def _clear_failed_attempts(self, ruc: str):
        """Limpiar historial de intentos fallidos"""
        if ruc in self.auth_cache:
            self.auth_cache[ruc].pop("failed_attempts", None)
            self.auth_cache[ruc].pop("last_failed_attempt", None)
    
    async def _build_auth_response(self, access_token: str, ruc: str, reused: bool = False) -> SireAuthResponse:
        """Construir respuesta de autenticación"""
        # Obtener información del token
        token_info = await self.token_manager.get_token_info(access_token)
        expires_at = token_info.get("expires_at", datetime.utcnow() + timedelta(hours=1))
        
        # Construir token data
        token_data = SireTokenData(
            access_token=access_token,
            token_type="Bearer",
            expires_in=int((expires_at - datetime.utcnow()).total_seconds()),
            scope="sire"
        )
        
        # Generar session ID
        session_id = f"session_{ruc}_{int(datetime.utcnow().timestamp())}"
        
        message = "Sesión reutilizada" if reused else "Autenticación exitosa"
        
        return SireAuthResponse(
            success=True,
            message=message,
            token_data=token_data,
            session_id=session_id,
            expires_at=expires_at
        )
