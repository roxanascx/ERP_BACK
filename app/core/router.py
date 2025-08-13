from fastapi import APIRouter
from ..modules.companies import routes as company_routes

# Router principal que incluye todos los módulos
api_router = APIRouter(prefix="/api/v1")

# Incluir rutas del módulo de empresas
api_router.include_router(
    company_routes.router,
    prefix="/companies",
    tags=["Companies"]
)
