"""
Dependencias de base de datos
"""

from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..database import get_database_connection


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
