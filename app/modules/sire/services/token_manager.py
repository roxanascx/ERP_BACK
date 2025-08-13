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
            # Calcular fecha de expiración
            expires_at = datetime.utcnow() + timedelta(seconds=token_data.expires_in)
            
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
            if self.mongo_collection:
                await self._store_in_mongo(session_id, session, credentials_hash)
            
            # Cache en memoria como fallback
            self.token_cache[session_id] = session
            
            # Limpiar cache si está muy grande
            await self._cleanup_cache()
            
            logger.info(f"✅ [TOKEN] Token almacenado para RUC {ruc}, sesión {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"❌ [TOKEN] Error almacenando token para RUC {ruc}: {e}")
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
                logger.warning(f"⚠️ [TOKEN] No se encontró sesión activa para RUC {ruc}")
                return None
            
            # Verificar si el token está próximo a expirar
            if self._is_token_expiring_soon(session):
                logger.info(f"🔄 [TOKEN] Token próximo a expirar para RUC {ruc}, renovando...")
                
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
            
            logger.debug(f"🎯 [TOKEN] Token válido obtenido para RUC {ruc}")
            return session.access_token
            
        except Exception as e:
            logger.error(f"❌ [TOKEN] Error obteniendo token válido para RUC {ruc}: {e}")
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
            if self.mongo_collection:
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
            
            logger.info(f"🚫 [TOKEN] {revoked_count} tokens revocados para RUC {ruc}")
            return revoked_count > 0
            
        except Exception as e:
            logger.error(f"❌ [TOKEN] Error revocando tokens para RUC {ruc}: {e}")
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
            logger.error(f"❌ [TOKEN] Error obteniendo info del token: {e}")
            return None
    
    # Métodos privados de soporte
    
    async def _store_in_redis(self, session_id: str, session: SireSession, ttl: int):
        """Almacenar sesión en Redis"""
        try:
            session_data = session.model_dump_json()
            await self.redis_client.setex(session_id, ttl, session_data)
        except Exception as e:
            logger.warning(f"⚠️ [TOKEN] Error almacenando en Redis: {e}")
    
    async def _store_in_mongo(self, session_id: str, session: SireSession, credentials_hash: str):
        """Almacenar sesión en MongoDB"""
        try:
            session_doc = session.model_dump()
            session_doc["_id"] = session_id
            session_doc["credentials_hash"] = credentials_hash
            
            await self.mongo_collection.insert_one(session_doc)
        except Exception as e:
            logger.warning(f"⚠️ [TOKEN] Error almacenando en MongoDB: {e}")
    
    async def _find_active_session(self, ruc: str) -> Optional[SireSession]:
        """Buscar sesión activa para RUC"""
        # Buscar en Redis primero
        if self.redis_client:
            keys = await self.redis_client.keys(f"sire_session_{ruc}_*")
            for key in keys:
                session_data = await self.redis_client.get(key)
                if session_data:
                    session = SireSession.model_validate_json(session_data)
                    if session.is_active and session.expires_at > datetime.utcnow():
                        return session
        
        # Buscar en MongoDB
        if self.mongo_collection:
            session_doc = await self.mongo_collection.find_one({
                "ruc": ruc,
                "is_active": True,
                "expires_at": {"$gt": datetime.utcnow()}
            }, sort=[("created_at", -1)])
            
            if session_doc:
                return SireSession(**session_doc)
        
        # Buscar en cache de memoria
        for session in self.token_cache.values():
            if (session.ruc == ruc and session.is_active and 
                session.expires_at > datetime.utcnow()):
                return session
        
        return None
    
    def _is_token_expiring_soon(self, session: SireSession) -> bool:
        """Verificar si el token expira pronto"""
        buffer_time = datetime.utcnow() + timedelta(seconds=self.default_expiry_buffer)
        return session.expires_at <= buffer_time
    
    async def _refresh_token_if_possible(self, session: SireSession) -> Optional[str]:
        """Intentar renovar token si es posible"""
        # Esta funcionalidad se implementaría con el refresh token
        # Por ahora retornamos None indicando que no se puede renovar
        # TODO: Implementar renovación automática de tokens
        logger.warning(f"⚠️ [TOKEN] Renovación automática no implementada aún")
        return None
    
    async def _deactivate_session(self, session: SireSession):
        """Desactivar sesión"""
        session.is_active = False
        
        # Actualizar en todos los stores
        if self.mongo_collection:
            await self.mongo_collection.update_one(
                {"ruc": session.ruc, "access_token": session.access_token},
                {"$set": {"is_active": False}}
            )
    
    async def _update_session_usage(self, session: SireSession):
        """Actualizar último uso de sesión"""
        if self.mongo_collection:
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
            
            logger.info(f"🧹 [TOKEN] Cache limpiado, manteniendo {keep_count} sesiones")
