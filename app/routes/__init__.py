"""
Rutas principales del sistema ERP.

Este módulo exporta todos los routers de la aplicación.
"""

from .users import router as users_router
from .auth import router as auth_router

# Módulos de contabilidad - Comentados porque ahora se usan desde core/router.py
# from app.modules.accounting.routes.mayor_routes import router as mayor_router
# from app.modules.accounting.routes.filtrado_avanzado_routes import router_filtrado
# from app.modules.accounting.routes.diario_routes import router as diario_router

# Exportar todos los routers
__all__ = [
    "users_router",
    "auth_router", 
    # "mayor_router",
    # "router_filtrado",
    # "diario_router"
]
