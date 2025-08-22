from fastapi import APIRouter
from ..modules.companies import routes as company_routes
from ..modules.sire.routes import auth as sire_auth_routes
from ..modules.sire.routes import rvie_routes as sire_rvie_routes
from ..modules.sire.routes import rvie_ventas_routes as sire_rvie_ventas_routes
from ..modules.sire.routes import maintenance as sire_maintenance_routes
from ..modules.sire.routes import auto_auth as sire_auto_auth_routes

# Importar nuevas rutas RCE
from ..modules.sire.routes import rce_comprobantes_routes as sire_rce_comprobantes_routes
from ..modules.sire.routes import rce_propuestas_routes as sire_rce_propuestas_routes
from ..modules.sire.routes import rce_resumen_routes as sire_rce_resumen_routes
from ..modules.sire.routes import rce_procesos_routes as sire_rce_procesos_routes
from ..modules.sire.routes import rce_consultas_routes as sire_rce_consultas_routes
from ..modules.sire.routes import rce_data_routes as sire_rce_data_routes
from ..modules.sire.routes import rce_comprobante_bd as sire_rce_bd_routes

# Importar nuevas rutas RVIE BD
from ..modules.sire.routes import rvie_comprobante_bd as sire_rvie_bd_routes

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

# Incluir rutas del módulo SIRE - RVIE Ventas
api_router.include_router(
    sire_rvie_ventas_routes.router,
    prefix="/sire/rvie/ventas",
    tags=["SIRE-RVIE-Ventas"]
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

# Incluir rutas del módulo SIRE - RCE (Registro de Compras Electrónico)
api_router.include_router(
    sire_rce_comprobantes_routes.router,
    prefix="/sire/rce/comprobantes",
    tags=["SIRE-RCE-Comprobantes"]
)

api_router.include_router(
    sire_rce_propuestas_routes.router,
    prefix="/sire/rce/propuestas",
    tags=["SIRE-RCE-Propuestas"]
)

api_router.include_router(
    sire_rce_resumen_routes.router,
    prefix="/sire/rce/resumen",
    tags=["SIRE-RCE-Resumen"]
)

api_router.include_router(
    sire_rce_procesos_routes.router,
    prefix="/sire/rce/procesos",
    tags=["SIRE-RCE-Procesos"]
)

api_router.include_router(
    sire_rce_consultas_routes.router,
    prefix="/sire/rce/consultas",
    tags=["SIRE-RCE-Consultas"]
)

# Incluir rutas del módulo SIRE - RCE Data Management
api_router.include_router(
    sire_rce_data_routes.router,
    prefix="/sire",
    tags=["SIRE-RCE-DataManagement"]
)

# Incluir rutas del módulo SIRE - RCE Base de Datos
api_router.include_router(
    sire_rce_bd_routes.router,
    prefix="/sire/rce",
    tags=["SIRE-RCE-BD"]
)

# Incluir rutas del módulo SIRE - RVIE Base de Datos
api_router.include_router(
    sire_rvie_bd_routes.router,
    prefix="/sire/rvie",
    tags=["SIRE-RVIE-BD"]
)
