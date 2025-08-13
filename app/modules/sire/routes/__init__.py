"""
Inicializador de rutas SIRE
"""

from .auth import router as auth_router
from .rvie_routes import router as rvie_router

# Lista de todos los routers del módulo SIRE
sire_routers = [
    auth_router,
    rvie_router,
    # rce_router,   # Se agregará en la siguiente fase
]

__all__ = ["sire_routers", "auth_router"]
