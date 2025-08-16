from fastapi import APIRouter
from ..modules.companies import routes as company_routes
from ..modules.sire.routes import auth as sire_auth_routes
from ..modules.sire.routes import rvie_routes as sire_rvie_routes
from ..modules.sire.routes import maintenance as sire_maintenance_routes
from ..modules.sire.routes import auto_auth as sire_auto_auth_routes

# Router principal que incluye todos los módulos
api_router = APIRouter(prefix="/api/v1")

# Incluir rutas del módulo de empresas
api_router.include_router(
    company_routes.router,
    prefix="/companies",
    tags=["Companies"]
)

# Incluir rutas del módulo SIRE - Autenticación
api_router.include_router(
    sire_auth_routes.router,
    prefix="/sire",
    tags=["SIRE"]
)

# Incluir rutas del módulo SIRE - RVIE
api_router.include_router(
    sire_rvie_routes.router,
    prefix="/sire/rvie",
    tags=["SIRE-RVIE"]
)

# Incluir rutas del módulo SIRE - Mantenimiento
api_router.include_router(
    sire_maintenance_routes.router,
    prefix="/sire/maintenance",
    tags=["SIRE-Maintenance"]
)

# Incluir rutas del módulo SIRE - Autenticación Automática
api_router.include_router(
    sire_auto_auth_routes.router,
    prefix="/sire/auto-auth",
    tags=["SIRE-AutoAuth"]
)
