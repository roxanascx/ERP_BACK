"""
Cliente HTTP para API SUNAT SIRE
"""

import httpx
import asyncio
import json
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
import logging
from ..models.auth import SireCredentials, SireTokenData
from ..models.responses import SireApiResponse, SireErrorResponse
from ..utils.exceptions import SireApiException, SireAuthException, SireTimeoutException

logger = logging.getLogger(__name__)


class SunatApiClient:
    """Cliente HTTP para comunicación con API SUNAT SIRE"""
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Inicializar cliente API
        
        Args:
            base_url: URL base de la API SUNAT (usar prod o testing)
            timeout: Timeout para requests en segundos
        """
        # URLs de SUNAT según Manual v25 (corregidas según documentación oficial)
        # Producción: https://api-sire.sunat.gob.pe/v1
        self.base_url = base_url or "https://api-sire.sunat.gob.pe/v1"
        self.auth_url = "https://api-seguridad.sunat.gob.pe/v1/clientessol"
        
        # Endpoints específicos según manual SUNAT OFICIAL v25
        self.endpoints = {
            # Autenticación
            "auth_token": "/clientessol/{client_id}/oauth2/token",
            
            # RVIE - Registro de Ventas e Ingresos Electrónico (URLs OFICIALES según Manual v25)
            "rvie_consultar_periodos": "/contribuyente/migeigv/libros/rvierce/padron/web/omisos/140000/periodos",  # 5.2 según Manual v25
            "rvie_descargar_propuesta": "/contribuyente/migeigv/libros/rvie/propuesta/web/propuesta/{periodo}/exportapropuesta",  # URL CORRECTA línea 2893
            "rvie_aceptar_propuesta": "/contribuyente/migeigv/libros/rvie/propuesta/web/propuesta/{periodo}/aceptapropuesta",
            "rvie_reemplazar_propuesta": "/contribuyente/migeigv/libros/rvie/propuesta/web/reemplazarpropuesta", 
            "rvie_registrar_preliminar": "/contribuyente/migeigv/libros/rvie/preliminar/web/preliminarregistrado",
            "rvie_inconsistencias": "/contribuyente/migeigv/libros/rvie/inconsistencias/web/inconsistenciascomprobantes",
            "rvie_resumen": "/contribuyente/migeigv/libros/rvie/resumen/web/resumencomprobantes/{periodo}/{codTipoResumen}/{codTipoArchivo}",
            
            # Gestión de Tickets (URLs OFICIALES según Manual v25)
            "consultar_ticket": "/contribuyente/migeigv/ticket/{ticket_id}/estado",
            "descargar_archivo": "/contribuyente/migeigv/ticket/{ticket_id}/archivo/{nombre_archivo}",
            
            # RCE - Registro de Compras Electrónico (URLs OFICIALES)
            "rce_descargar_propuesta": "/contribuyente/migeigv/libros/rce/propuesta/web/propuesta/{periodo}/exportacioncomprobantepropuesta/{codTipoArchivo}",
            "rce_aceptar_propuesta": "/contribuyente/migeigv/libros/rce/propuesta/web/aceptarpropuesta",
            "rce_resumen_consolidado": "/contribuyente/migeigv/libros/rce/resumen/web/resumencomprobantes/{periodo}/{codTipoResumen}/{codTipoArchivo}",
            "rce_inconsistencias_montos": "/contribuyente/migeigv/libros/rce/inconsistencias/web/inconsistenciasmontostotales",
            "rce_inconsistencias_comprobantes": "/contribuyente/migeigv/libros/rce/inconsistencias/web/inconsistenciascomprobantes"
        }
        
        self.timeout = timeout
        self.max_retries = 3
        self.retry_delay = 1  # segundos
        
        # Headers por defecto
        self.default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ERP-SIRE-Client/1.0.0"
        }
        
        # Cliente HTTP con configuración
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=100)
        )
    
    async def close(self):
        """Cerrar cliente HTTP"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def _build_headers(self, token: Optional[str] = None, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Construir headers para request"""
        headers = self.default_headers.copy()
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        if extra_headers:
            headers.update(extra_headers)
        
        return headers
    
    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None,
        retry_count: int = 0
    ) -> httpx.Response:
        """
        Realizar request HTTP con reintentos
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            url: URL completa del endpoint
            headers: Headers adicionales
            data: Datos del body (para POST/PUT)
            params: Parámetros de query
            token: Token de autenticación
            retry_count: Contador de reintentos
        
        Returns:
            httpx.Response: Respuesta HTTP
        
        Raises:
            SireApiException: Error de API
            SireTimeoutException: Timeout
        """
        # Construir headers
        request_headers = self._build_headers(token, headers)
        
        # Preparar datos
        json_data = json.dumps(data, default=str) if data else None
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=request_headers,
                json=data,
                params=params
            )
            
            # Verificar si es un error de autenticación
            if response.status_code == 401:
                raise SireAuthException("Token de autenticación inválido o expirado")
            
            # Verificar otros errores HTTP
            if response.status_code >= 400:
                error_msg = f"Error HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", error_msg)
                except:
                    error_msg = response.text or error_msg
                
                raise SireApiException(f"{error_msg}", status_code=response.status_code)
            
            return response
            
        except httpx.TimeoutException:
            if retry_count < self.max_retries:
                await asyncio.sleep(self.retry_delay * (retry_count + 1))
                return await self._make_request(method, url, headers, data, params, token, retry_count + 1)
            else:
                raise SireTimeoutException(f"Timeout después de {self.max_retries} reintentos")
        
        except httpx.RequestError as e:
            if retry_count < self.max_retries:
                await asyncio.sleep(self.retry_delay * (retry_count + 1))
                return await self._make_request(method, url, headers, data, params, token, retry_count + 1)
            else:
                raise SireApiException(f"Error de conexión después de {self.max_retries} reintentos: {e}")
    
    async def authenticate(self, credentials: SireCredentials) -> SireTokenData:
        """
        Autenticar con SUNAT y obtener token JWT
        
        Args:
            credentials: Credenciales SIRE
        
        Returns:
            SireTokenData: Datos del token
        
        Raises:
            SireAuthException: Error de autenticación
        """
        auth_data = {
            "grant_type": "password",
            "scope": "https://api-sire.sunat.gob.pe",
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "username": f"{credentials.ruc}{credentials.sunat_usuario}",  # ✅ FORMATO CORRECTO: RUC+Usuario SIN ESPACIOS
            "password": credentials.sunat_clave
        }
        
        # Headers específicos para autenticación
        auth_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        try:
            # URL específica con client_id (formato confirmado que funciona)
            auth_url = f"{self.auth_url}/{credentials.client_id}/oauth2/token/"
            
            response = await self.client.request(
                method="POST",
                url=auth_url,
                headers=auth_headers,
                data=auth_data  # Usar data en lugar de json para form-urlencoded
            )
            
            # Verificar si es un error de autenticación
            if response.status_code == 401:
                error_details = "Credenciales inválidas"
                try:
                    error_data = response.json()
                    error_details = error_data.get("error_description", error_details)
                except:
                    pass
                raise SireAuthException(f"Token de autenticación inválido o expirado: {error_details}")
            
            # Verificar otros errores HTTP
            if response.status_code >= 400:
                error_msg = f"Error HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error_description", error_msg)
                except:
                    error_msg = response.text or error_msg
                raise SireAuthException(f"Error en autenticación: {error_msg}")
            
            token_data = response.json()
            
            return SireTokenData(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data["expires_in"],
                refresh_token=token_data.get("refresh_token"),
                scope=token_data.get("scope")
            )
            
        except Exception as e:
            raise SireAuthException(f"Error de autenticación: {e}")
    
    async def refresh_token(self, refresh_token: str, client_id: str, client_secret: str) -> SireTokenData:
        """
        Renovar token JWT
        
        Args:
            refresh_token: Token de renovación
            client_id: Client ID
            client_secret: Client Secret
        
        Returns:
            SireTokenData: Nuevos datos del token
        """
        refresh_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        try:
            response = await self._make_request(
                method="POST",
                url=f"{self.auth_url}/oauth2/token",
                data=refresh_data
            )
            
            token_data = response.json()
            
            return SireTokenData(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data["expires_in"],
                refresh_token=token_data.get("refresh_token", refresh_token),
                scope=token_data.get("scope")
            )
            
        except Exception as e:
            raise SireAuthException(f"Error renovando token: {e}")
    
    async def get_with_auth(self, endpoint: str, token: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        GET request con autenticación JWT
        
        Args:
            endpoint: Endpoint relativo (ej: /rvie/propuesta)
            token: Token de acceso
            params: Parámetros de query
        
        Returns:
            Dict con respuesta JSON
        """
        url = f"{self.base_url}{endpoint}"
        response = await self._make_request("GET", url, token=token, params=params)
        return response.json()
    
    async def post_with_auth(
        self, 
        endpoint: str, 
        token: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        POST request con autenticación JWT
        
        Args:
            endpoint: Endpoint relativo
            token: Token de acceso
            data: Datos del body
            params: Parámetros de query
        
        Returns:
            Dict con respuesta JSON
        """
        url = f"{self.base_url}{endpoint}"
        response = await self._make_request("POST", url, token=token, data=data, params=params)
        return response.json()
    
    async def put_with_auth(
        self, 
        endpoint: str, 
        token: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        PUT request con autenticación JWT
        """
        url = f"{self.base_url}{endpoint}"
        response = await self._make_request("PUT", url, token=token, data=data)
        return response.json()
    
    async def delete_with_auth(self, endpoint: str, token: str) -> Dict[str, Any]:
        """
        DELETE request con autenticación JWT
        """
        url = f"{self.base_url}{endpoint}"
        response = await self._make_request("DELETE", url, token=token)
        return response.json()
    
    async def download_file(self, endpoint: str, token: str) -> bytes:
        """
        Descargar archivo con autenticación
        
        Args:
            endpoint: Endpoint de descarga
            token: Token de acceso
        
        Returns:
            bytes: Contenido del archivo
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._build_headers(token)
        headers["Accept"] = "*/*"  # Aceptar cualquier tipo de archivo
        
        response = await self._make_request("GET", url, headers=headers)
        return response.content
    
    async def health_check(self) -> bool:
        """
        Verificar estado de la API SUNAT
        
        Returns:
            bool: True si la API está disponible
            
        Nota: SUNAT no tiene endpoint de health público, 
        verificamos con el endpoint de autenticación
        """
        try:
            # En lugar de /health, verificamos que la URL base responda
            # Hacemos una llamada mínima que no requiere autenticación
            response = await self._make_request("GET", f"{self.base_url}")
            return response.status_code in [200, 401, 403]  # 401/403 indican que el servidor responde
        except Exception as e:
            return False
