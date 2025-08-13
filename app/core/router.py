from fastapi import APIRouter
from ..modules.accounting import routes as accounting_routes
from ..modules.users import routes as user_routes  
from ..modules.customers import routes as customer_routes

# Router principal que incluye todos los módulos
api_router = APIRouter(prefix="/api/v1")

# Incluir rutas de cada módulo
api_router.include_router(
    user_routes.router,
    prefix="/users", 
    tags=["Users"]
)

api_router.include_router(
    customer_routes.router,
    prefix="/customers",
    tags=["Customers"]
)

api_router.include_router(
    accounting_routes.router,
    prefix="/accounting",
    tags=["Accounting"]
)
