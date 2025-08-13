from fastapi import APIRouter
from ..modules.companies import routes as company_routes
from ..modules.sire.routes import auth as sire_auth_routes
from ..modules.sire.routes import rvie_routes as sire_rvie_routes

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
