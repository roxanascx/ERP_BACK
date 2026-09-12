"""
Conexión a MongoDB.

El cliente de Motor queda ligado al bucle de eventos en el que se crea. Antes se
cacheaba en una global y se reutilizaba siempre: con uvicorn hay un único bucle
y funcionaba, pero en cuanto algo creaba otro —`fastapi.testclient.TestClient`
abre uno por petición— la segunda llamada moría con `RuntimeError: Event loop is
closed`. Eso hacía imposible cualquier test de integración con más de una
petición, en todo el backend.

La solución es recordar también el bucle: si cambia, se construye un cliente
nuevo. En producción eso ocurre una sola vez; en los tests, tantas como haga
falta.
"""

import asyncio
import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import settings

logger = logging.getLogger(__name__)

MONGODB_URL = settings.MONGODB_URL
DATABASE_NAME = settings.DATABASE_NAME

#: Cliente activo y bucle en el que se creó. Van siempre juntos.
_client: Optional[AsyncIOMotorClient] = None
_loop: Optional[asyncio.AbstractEventLoop] = None


def _bucle_actual() -> Optional[asyncio.AbstractEventLoop]:
    """El bucle en ejecución, o None si se llama desde código síncrono."""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


def _esta_obsoleto(cliente: AsyncIOMotorClient, bucle) -> bool:
    """
    ¿Este cliente sirve todavía?

    Se le pregunta al propio cliente por su bucle en vez de mirar el del
    contexto de llamada, porque FastAPI ejecuta las dependencias síncronas en un
    hilo del pool, donde no hay ningún bucle en ejecución y no habría forma de
    detectar el cambio.
    """
    try:
        suyo = cliente.io_loop
    except Exception:
        return True

    if suyo is None or suyo.is_closed():
        return True

    return bucle is not None and suyo is not bucle


def _obtener_cliente() -> AsyncIOMotorClient:
    """
    Cliente de Mongo válido para el bucle actual.

    Se reconstruye si no hay ninguno, si el suyo se cerró, o si estamos en otro
    bucle: un cliente de Motor no se puede compartir entre bucles.
    """
    global _client, _loop

    bucle = _bucle_actual()

    if _client is None or _esta_obsoleto(_client, bucle):
        if _client is not None:
            # El anterior pertenece a un bucle que ya no existe: cerrarlo evita
            # que queden sockets colgando.
            try:
                _client.close()
            except Exception:
                pass
        _client = AsyncIOMotorClient(MONGODB_URL)
        _loop = bucle

    return _client


def get_database() -> AsyncIOMotorDatabase:
    """La base de datos, lista para usar desde el bucle actual."""
    return _obtener_cliente()[DATABASE_NAME]


async def connect_to_mongo() -> None:
    """Abrir la conexión al arrancar la aplicación."""
    _obtener_cliente()
    logger.info(f"Conectado a MongoDB (base de datos: {DATABASE_NAME})")


async def close_mongo_connection() -> None:
    """Cerrar la conexión al apagar la aplicación."""
    global _client, _loop
    if _client is not None:
        _client.close()
        _client = None
        _loop = None
        logger.info("Conexión a MongoDB cerrada")


# ---------------------------------------------------------------------------
# Variantes asíncronas, por compatibilidad con los módulos que ya las usan.
# Todas resuelven a lo mismo: `get_database()` ya no necesita await.
# ---------------------------------------------------------------------------

async def get_database_async() -> AsyncIOMotorDatabase:
    """Igual que `get_database()`. Se mantiene por los módulos que la esperan."""
    return get_database()


async def get_database_connection() -> AsyncIOMotorDatabase:
    """Dependencia de FastAPI que devuelve la base de datos."""
    return get_database()


async def get_db() -> AsyncIOMotorDatabase:
    """Nombre estándar de la dependencia, para `Depends(get_db)`."""
    return get_database()
