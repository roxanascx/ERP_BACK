"""
Dependencias centralizadas de la aplicación
"""

from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import Header, Depends, HTTPException

# Importar dependencia de base de datos desde archivo separado
from .database_deps import get_database


def get_auth_service():
    """
    Dependencia para obtener el servicio de autenticación SIRE
    Usar lazy import para evitar circular imports
    """
    from ..modules.sire.services.auth_service import SireAuthService
    return SireAuthService()


def get_api_client():
    """
    Dependencia para obtener el cliente API de SUNAT
    Usar lazy import para evitar circular imports
    """
    from ..modules.sire.services.api_client import SunatApiClient
    return SunatApiClient()


async def get_current_empresa(
    clerk_user_id: str = Header(None, alias="X-Clerk-User-Id"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Dependencia para obtener empresa actual basada en autenticación Clerk
    Obtiene la empresa asociada al usuario autenticado via Clerk
    """
    if not clerk_user_id:
        raise HTTPException(
            status_code=401, 
            detail="No se encontró ID de usuario en headers de Clerk"
        )
    
    # Obtener usuario desde MongoDB
    user = await db.users.find_one({"clerk_id": clerk_user_id})
    if not user:
        raise HTTPException(
            status_code=404, 
            detail="Usuario no encontrado en la base de datos"
        )
    
    # Obtener empresa del usuario
    if not user.get("empresa_id"):
        # Si no tiene empresa asignada, obtener la primera empresa disponible
        # (lógica temporal hasta que se implemente asignación de empresas)
        empresa = await db.empresas.find_one({})
        if not empresa:
            raise HTTPException(
                status_code=404, 
                detail="No hay empresas configuradas en el sistema"
            )
    else:
        # Obtener empresa específica del usuario
        from bson import ObjectId
        empresa = await db.empresas.find_one({"_id": ObjectId(user["empresa_id"])})
        if not empresa:
            raise HTTPException(
                status_code=404, 
                detail="Empresa del usuario no encontrada"
            )
    
    # Convertir ObjectId a string para JSON
    empresa["id"] = str(empresa["_id"])
    del empresa["_id"]
    
    return empresa
