"""
Dependencias centralizadas de la aplicación
"""

from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..database import get_database_connection
from ..modules.sire.services.auth_service import SireAuthService
from ..modules.sire.services.api_client import SunatApiClient


async def get_database() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """
    Dependencia para obtener la conexión a la base de datos
    """
    db = await get_database_connection()
    try:
        yield db
    finally:
        # La conexión se cierra automáticamente con el pool
        pass


def get_auth_service() -> SireAuthService:
    """
    Dependencia para obtener el servicio de autenticación SIRE
    """
    return SireAuthService()


def get_api_client() -> SunatApiClient:
    """
    Dependencia para obtener el cliente API de SUNAT
    """
    return SunatApiClient()
