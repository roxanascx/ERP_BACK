"""
Gestor de credenciales SIRE
Maneja las credenciales específicas para cada RUC desde MongoDB
"""

from typing import Dict, Optional
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from ....database import get_database
from ..models.auth import SireCredentials

logger = logging.getLogger(__name__)


class SireCredentialsManager:
    """Gestor de credenciales SIRE por RUC desde MongoDB"""
    
    def __init__(self):
        """Inicializar gestor con acceso a MongoDB"""
        self.db: AsyncIOMotorDatabase = get_database()
        
        # Fallback hardcoded para casos específicos (mantener como backup)
        self._fallback_credentials: Dict[str, Dict[str, str]] = {
            # RUC de prueba exitoso del script token_simple.py
            "20612969125": {
                "sunat_usuario": "THENTHIP",
                "sunat_clave": "enteatell", 
                "sire_client_id": "aa3f9b5c-7013-4ded-a63a-5ee658ce3530",
                "sire_client_secret": "MOIzbzE3lAj/W5EkokXEbA=="
            }
        }
    
    async def get_credentials(self, ruc: str) -> Optional[SireCredentials]:
        """
        Obtener credenciales para un RUC específico desde MongoDB
        
        Args:
            ruc: RUC del contribuyente
            
        Returns:
            SireCredentials si existen para el RUC, None si no
        """
        try:
            # Primero buscar en MongoDB
            empresa = await self.db.companies.find_one({"ruc": ruc})
            
            if empresa and empresa.get("sire_activo"):
                # Verificar que tenga todas las credenciales necesarias
                required_fields = ["sunat_usuario", "sunat_clave", "sire_client_id", "sire_client_secret"]
                
                if all(empresa.get(field) for field in required_fields):
                    return SireCredentials(
                        ruc=ruc,
                        sunat_usuario=empresa["sunat_usuario"],
                        sunat_clave=empresa["sunat_clave"],
                        client_id=empresa["sire_client_id"],
                        client_secret=empresa["sire_client_secret"]
                    )
                else:
                    missing_fields = [field for field in required_fields if not empresa.get(field)]
                    pass  # Faltan campos, continuar con fallback
            
            # Fallback a credenciales hardcoded
            if ruc in self._fallback_credentials:
                cred_data = self._fallback_credentials[ruc]
                
                return SireCredentials(
                    ruc=ruc,
                    sunat_usuario=cred_data["sunat_usuario"],
                    sunat_clave=cred_data["sunat_clave"],
                    client_id=cred_data["sire_client_id"],
                    client_secret=cred_data["sire_client_secret"]
                )
            
            return None
            
        except Exception as e:
            return None
    
    def get_credentials_sync(self, ruc: str) -> Optional[SireCredentials]:
        """
        Versión síncrona para compatibilidad - solo usa fallback
        DEPRECATED: Usar get_credentials() async
        """
        if ruc in self._fallback_credentials:
            cred_data = self._fallback_credentials[ruc]
            
            return SireCredentials(
                ruc=ruc,
                sunat_usuario=cred_data["sunat_usuario"],
                sunat_clave=cred_data["sunat_clave"],
                client_id=cred_data["sire_client_id"],
                client_secret=cred_data["sire_client_secret"]
            )
        
        return None


# Crear instancia global del gestor
credentials_manager = SireCredentialsManager()
