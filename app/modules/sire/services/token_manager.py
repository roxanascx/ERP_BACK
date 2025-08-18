"""
Gestor de tokens JWT SIRE
Maneja el almacenamiento, validación y renovación de tokens
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError
import logging

from ..models.auth import SireTokenData, SireSession
from ..utils.exceptions import SireTokenException, SireAuthException

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SireTokenManager:
    """Gestión centralizada de tokens JWT SIRE"""
    
    def __init__(self, redis_client=None, mongo_collection=None):
        """
        Inicializar gestor de tokens
        
        Args:
            redis_client: Cliente Redis para cache (opcional)
            mongo_collection: Colección MongoDB para persistencia
        """
        self.redis_client = redis_client
        self.mongo_collection = mongo_collection
        self.token_cache: Dict[str, SireSession] = {}  # Cache en memoria como fallback
        
        # Configuración de tokens
        self.default_expiry_buffer = 300  # 5 minutos antes de expiración
        self.max_cache_size = 1000
        
    async def store_token(self, ruc: str, token_data: SireTokenData, credentials_hash: str) -> str:
        """
        Almacenar token con metadatos de sesión
        
        Args:
            ruc: RUC del contribuyente
            token_data: Datos del token JWT
            credentials_hash: Hash de las credenciales para validación
        
        Returns:
            str: ID de sesión generado
        """
        try:
            # Calcular fecha de expiración (CORREGIDO: usar timezone de Perú)
            from zoneinfo import ZoneInfo
            import pytz
            
            # SUNAT opera en timezone de Perú (UTC-5)
            peru_tz = pytz.timezone('America/Lima')
            now_utc = datetime.utcnow()
            now_peru = now_utc.replace(tzinfo=pytz.UTC).astimezone(peru_tz)
            
            # El token expira en X segundos desde AHORA (en tiempo de Perú)
            expires_at_peru = now_peru + timedelta(seconds=token_data.expires_in)
            expires_at = expires_at_peru.astimezone(pytz.UTC).replace(tzinfo=None)
            
            # Generar ID de sesión único
            session_id = f"sire_session_{ruc}_{int(datetime.utcnow().timestamp())}"
            
            # Crear sesión
            session = SireSession(
                ruc=ruc,
                access_token=token_data.access_token,
                refresh_token=token_data.refresh_token,
                expires_at=expires_at,
                created_at=datetime.utcnow(),
                last_used=datetime.utcnow(),
                is_active=True
            )
            
            # Almacenar en Redis si está disponible
            if self.redis_client:
                await self._store_in_redis(session_id, session, token_data.expires_in)
            
            # Almacenar en MongoDB para persistencia
            if self.mongo_collection is not None:
                await self._store_in_mongo(session_id, session, credentials_hash)
            
            # Cache en memoria como fallback
            self.token_cache[session_id] = session
            
            # Limpiar cache si está muy grande
            await self._cleanup_cache()
            
            return session_id
            
        except Exception as e:
            raise SireTokenException(f"Error almacenando token: {e}")
    
    async def get_valid_token(self, ruc: str) -> Optional[str]:
        """
        Obtener token válido para RUC (renovar si es necesario)
        
        Args:
            ruc: RUC del contribuyente
        
        Returns:
            str: Token válido o None si no existe/no se puede renovar
        """
        try:
            # Buscar sesión activa
            session = await self._find_active_session(ruc)
            if not session:
                return None
            
            # Verificar si el token está próximo a expirar
            if self._is_token_expiring_soon(session):
                
                # Intentar renovar token
                new_token = await self._refresh_token_if_possible(session)
                if new_token:
                    return new_token
                else:
                    # No se pudo renovar, marcar sesión como inactiva
                    await self._deactivate_session(session)
                    return None
            
            # Actualizar último uso
            session.last_used = datetime.utcnow()
            await self._update_session_usage(session)
            
            return session.access_token
            
        except Exception as e:
            return None

    async def get_active_session_token(self, ruc: str) -> Optional[str]:
        """
        Obtener token de sesión activa SIN intentar renovación
        
        Este método es más rápido y seguro para operaciones que necesitan
        usar una sesión ya autenticada sin riesgo de colgarse en renovación.
        
        Args:
            ruc: RUC del contribuyente
        
        Returns:
            str: Token de sesión activa o None si no existe
        """
        try:
            # Buscar sesión activa (método corregido)
            session = await self._find_active_session_corrected(ruc)
            if not session:
                return None
            
            # Verificar que no esté expirada (sin renovar)
            if session.expires_at <= datetime.utcnow():
                # Limpiar sesión expirada
                await self._cleanup_expired_session(session)
                return None
                
            # Actualizar último uso
            session.last_used = datetime.utcnow()
            await self._update_session_usage(session)
            
            return session.access_token
            
        except Exception as e:
            return None
    
    async def revoke_token(self, ruc: str) -> bool:
        """
        Revocar todos los tokens activos para un RUC
        
        Args:
            ruc: RUC del contribuyente
        
        Returns:
            bool: True si se revocaron tokens
        """
        try:
            revoked_count = 0
            
            # Revocar en Redis
            if self.redis_client:
                keys = await self.redis_client.keys(f"sire_session_*_{ruc}_*")
                for key in keys:
                    await self.redis_client.delete(key)
                    revoked_count += 1
            
            # Revocar en MongoDB
            if self.mongo_collection is not None:
                result = await self.mongo_collection.update_many(
                    {"ruc": ruc, "is_active": True},
                    {"$set": {"is_active": False, "revoked_at": datetime.utcnow()}}
                )
                revoked_count += result.modified_count
            
            # Revocar en cache de memoria
            for session_id, session in list(self.token_cache.items()):
                if session.ruc == ruc and session.is_active:
                    session.is_active = False
                    revoked_count += 1
            
            return revoked_count > 0
            
        except Exception as e:
            return False
    
    async def validate_token(self, token: str) -> bool:
        """
        Validar si un token es válido (formato y expiración)
        
        Args:
            token: Token JWT a validar
        
        Returns:
            bool: True si es válido
        """
        try:
            # Validar formato JWT (sin verificar signature porque no tenemos la clave)
            payload = jwt.get_unverified_claims(token)
            
            # Verificar expiración
            exp = payload.get('exp')
            if exp:
                exp_datetime = datetime.fromtimestamp(exp)
                if exp_datetime <= datetime.utcnow():
                    return False
            
            return True
            
        except JWTError:
            return False
        except Exception:
            return False
    
    async def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Obtener información de un token JWT
        
        Args:
            token: Token JWT
        
        Returns:
            Dict con información del token
        """
        try:
            payload = jwt.get_unverified_claims(token)
            
            # Extraer información útil
            info = {
                "subject": payload.get("sub"),
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp"),
                "scope": payload.get("scope"),
                "client_id": payload.get("client_id")
            }
            
            # Convertir timestamps a datetime
            if info["issued_at"]:
                info["issued_at"] = datetime.fromtimestamp(info["issued_at"])
            if info["expires_at"]:
                info["expires_at"] = datetime.fromtimestamp(info["expires_at"])
            
            return info
            
        except Exception as e:
            return None
    
    # Métodos privados de soporte
    
    async def _store_in_redis(self, session_id: str, session: SireSession, ttl: int):
        """Almacenar sesión en Redis"""
        try:
            session_data = session.model_dump_json()
            await self.redis_client.setex(session_id, ttl, session_data)
        except Exception as e:
            pass
    
    async def _store_in_mongo(self, session_id: str, session: SireSession, credentials_hash: str):
        """Almacenar sesión en MongoDB"""
        try:
            session_doc = session.model_dump()
            session_doc["_id"] = session_id
            session_doc["credentials_hash"] = credentials_hash
            
            await self.mongo_collection.insert_one(session_doc)
        except Exception as e:
            pass
    
    async def _find_active_session(self, ruc: str) -> Optional[SireSession]:
        """Buscar sesión activa para RUC"""
        
        # Buscar en Redis primero
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(f"sire_session_{ruc}_*")
                for key in keys:
                    session_data = await self.redis_client.get(key)
                    if session_data:
                        session = SireSession.model_validate_json(session_data)
                        if session.is_active and session.expires_at > datetime.utcnow():
                            return session
            except Exception as e:
                pass
        
        # Buscar en MongoDB
        if self.mongo_collection is not None:
            try:
                session_doc = await self.mongo_collection.find_one({
                    "ruc": ruc,
                    "is_active": True,
                    "expires_at": {"$gt": datetime.utcnow()}
                }, sort=[("created_at", -1)])
                
                if session_doc:
                    return SireSession(**session_doc)
            except Exception as e:
                pass
        
        # Buscar en cache de memoria
        for session_id, session in self.token_cache.items():
            if (session.ruc == ruc and session.is_active and 
                session.expires_at > datetime.utcnow()):
                return session
                return session
        
        return None
    
    async def _find_active_session_corrected(self, ruc: str) -> Optional[SireSession]:
        """
        Buscar sesión activa corregida - versión que funciona
        INCLUYE LIMPIEZA AUTOMÁTICA DE TOKENS EXPIRADOS
        
        Args:
            ruc: RUC del contribuyente
            
        Returns:
            SireSession activa o None
        """
        try:
            # CRÍTICO: Limpiar RUC para evitar errores de formato
            ruc_clean = str(ruc).strip()
            
            # 1. Primero limpiar tokens expirados automáticamente
            await self._cleanup_expired_tokens(ruc_clean)
            
            # 2. Buscar en cache de memoria (más rápido)
            for session_id, session in self.token_cache.items():
                if (session.ruc == ruc_clean and 
                    session.is_active and 
                    session.expires_at > datetime.utcnow()):
                    return session
            
            # 3. Buscar en Redis si está disponible
            if self.redis_client:
                try:
                    # Buscar todas las sesiones que coincidan con el patrón
                    keys = await self.redis_client.keys(f"sire_session_{ruc_clean}_*")
                    for key in keys:
                        session_data = await self.redis_client.get(key)
                        if session_data:
                            session_dict = json.loads(session_data)
                            session = SireSession(**session_dict)
                            
                            if (session.is_active and 
                                session.expires_at > datetime.utcnow()):
                                # También guardarlo en cache para próximas consultas
                                self.token_cache[key] = session
                                return session
                except Exception as e:
                    pass
            
            # 4. Buscar en MongoDB como último recurso
            if self.mongo_collection is not None:
                try:
                    session_doc = await self.mongo_collection.find_one({
                        "ruc": ruc_clean,
                        "is_active": True,
                        "expires_at": {"$gt": datetime.utcnow()}
                    })
                    
                    if session_doc:
                        session = SireSession(**session_doc)
                        # Guardarlo en cache para próximas consultas
                        session_id = f"sire_session_{ruc_clean}_{int(session.created_at.timestamp())}"
                        self.token_cache[session_id] = session
                        return session
                except Exception as e:
                    pass
            
            return None
            
        except Exception as e:
            return None
    
    async def _cleanup_expired_session(self, session: SireSession):
        """Limpiar sesión expirada de todos los stores"""
        try:
            # Limpiar de cache
            keys_to_remove = []
            for session_id, cached_session in self.token_cache.items():
                if cached_session.ruc == session.ruc and cached_session.access_token == session.access_token:
                    keys_to_remove.append(session_id)
            
            for key in keys_to_remove:
                del self.token_cache[key]
            
            # Limpiar de Redis
            if self.redis_client:
                keys = await self.redis_client.keys(f"sire_session_{session.ruc}_*")
                for key in keys:
                    await self.redis_client.delete(key)
            
            # Marcar como inactiva en MongoDB
            if self.mongo_collection is not None:
                await self.mongo_collection.update_one(
                    {"ruc": session.ruc, "access_token": session.access_token},
                    {"$set": {"is_active": False}}
                )
                
        except Exception as e:
            pass
    
    async def _cleanup_expired_tokens(self, ruc: str):
        """
        Limpiar automáticamente todos los tokens expirados para un RUC específico
        
        Args:
            ruc: RUC del contribuyente
        """
        try:
            now = datetime.utcnow()
            cleaned_count = 0
            
            # 1. Limpiar cache de memoria
            keys_to_remove = []
            for session_id, session in self.token_cache.items():
                if session.ruc == ruc and (not session.is_active or session.expires_at <= now):
                    keys_to_remove.append(session_id)
            
            for key in keys_to_remove:
                del self.token_cache[key]
                cleaned_count += 1
            
            # 2. Limpiar Redis
            if self.redis_client:
                try:
                    keys = await self.redis_client.keys(f"sire_session_{ruc}_*")
                    for key in keys:
                        session_data = await self.redis_client.get(key)
                        if session_data:
                            session_dict = json.loads(session_data)
                            expires_at = datetime.fromisoformat(session_dict.get('expires_at', '1970-01-01'))
                            
                            if expires_at <= now:
                                await self.redis_client.delete(key)
                                cleaned_count += 1
                except Exception as e:
                    pass
            
            # 3. Marcar como inactivos en MongoDB (no eliminar, solo marcar)
            if self.mongo_collection is not None:
                try:
                    result = await self.mongo_collection.update_many(
                        {
                            "ruc": ruc,
                            "$or": [
                                {"expires_at": {"$lte": now}},
                                {"is_active": False}
                            ]
                        },
                        {"$set": {"is_active": False}}
                    )
                    cleaned_count += result.modified_count
                except Exception as e:
                    pass
            
        except Exception as e:
            pass
    
    async def cleanup_all_expired_tokens(self):
        """
        Limpiar todos los tokens expirados del sistema (método de mantenimiento)
        
        Returns:
            int: Cantidad de tokens limpiados
        """
        try:
            now = datetime.utcnow()
            total_cleaned = 0
            
            # 1. Limpiar cache de memoria
            keys_to_remove = []
            for session_id, session in self.token_cache.items():
                if not session.is_active or session.expires_at <= now:
                    keys_to_remove.append(session_id)
            
            for key in keys_to_remove:
                del self.token_cache[key]
                total_cleaned += 1
            
            # 2. Limpiar Redis globalmente
            if self.redis_client:
                try:
                    keys = await self.redis_client.keys("sire_session_*")
                    for key in keys:
                        session_data = await self.redis_client.get(key)
                        if session_data:
                            session_dict = json.loads(session_data)
                            expires_at = datetime.fromisoformat(session_dict.get('expires_at', '1970-01-01'))
                            
                            if expires_at <= now:
                                await self.redis_client.delete(key)
                                total_cleaned += 1
                except Exception as e:
                    pass
            
            # 3. Marcar como inactivos en MongoDB globalmente
            if self.mongo_collection is not None:
                try:
                    result = await self.mongo_collection.update_many(
                        {
                            "$or": [
                                {"expires_at": {"$lte": now}},
                                {"is_active": False}
                            ]
                        },
                        {"$set": {"is_active": False}}
                    )
                    total_cleaned += result.modified_count
                except Exception as e:
                    pass
            
            return total_cleaned
            
        except Exception as e:
            return 0
    
    def _is_token_expiring_soon(self, session: SireSession) -> bool:
        """Verificar si el token expira pronto (CORREGIDO: considerar timezone)"""
        import pytz
        
        # Usar tiempo actual en UTC (como almacenamos expires_at)
        now_utc = datetime.utcnow()
        buffer_time = now_utc + timedelta(seconds=self.default_expiry_buffer)
        
        is_expiring = session.expires_at <= buffer_time
        
        return is_expiring
    
    async def _refresh_token_if_possible(self, session: SireSession) -> Optional[str]:
        """Intentar renovar token si es posible"""
        # Esta funcionalidad se implementaría con el refresh token
        # Por ahora retornamos None indicando que no se puede renovar
        # TODO: Implementar renovación automática de tokens
        return None
    
    async def _deactivate_session(self, session: SireSession):
        """Desactivar sesión"""
        session.is_active = False
        
        # Actualizar en todos los stores
        if self.mongo_collection is not None:
            await self.mongo_collection.update_one(
                {"ruc": session.ruc, "access_token": session.access_token},
                {"$set": {"is_active": False}}
            )
    
    async def _update_session_usage(self, session: SireSession):
        """Actualizar último uso de sesión"""
        if self.mongo_collection is not None:
            await self.mongo_collection.update_one(
                {"ruc": session.ruc, "access_token": session.access_token},
                {"$set": {"last_used": session.last_used}}
            )
    
    async def _cleanup_cache(self):
        """Limpiar cache en memoria si está muy grande"""
        if len(self.token_cache) > self.max_cache_size:
            # Eliminar las sesiones más antiguas
            sorted_sessions = sorted(
                self.token_cache.items(),
                key=lambda x: x[1].last_used
            )
            
            # Mantener solo las más recientes
            keep_count = int(self.max_cache_size * 0.8)
            new_cache = dict(sorted_sessions[-keep_count:])
            self.token_cache = new_cache
            
