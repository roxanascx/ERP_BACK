"""
Inicializador de rutas SIRE
"""

from .auth import router as auth_router
from .rvie_routes import router as rvie_router
from .rvie_ventas_routes import router as rvie_ventas_router
from .ticket_routes import router as ticket_router
from .diagnostico_routes import router as diagnostico_router

# Importar nuevas rutas RCE
from .rce_comprobantes_routes import router as rce_comprobantes_router
from .rce_propuestas_routes import router as rce_propuestas_router
from .rce_procesos_routes import router as rce_procesos_router
from .rce_consultas_routes import router as rce_consultas_router
from .rce_data_routes import router as rce_data_router

# Lista de todos los routers del módulo SIRE
sire_routers = [
    auth_router,
    rvie_router,
    rvie_ventas_router,
    ticket_router,
    diagnostico_router,
    # Rutas RCE - Fase 3 completada
    rce_comprobantes_router,
    rce_propuestas_router,
    rce_procesos_router,
    rce_consultas_router,
    # Rutas RCE Data Management - Gestión avanzada de datos
    rce_data_router,
]

__all__ = [
    "sire_routers", 
    "auth_router", 
    "rvie_router", 
    "rvie_ventas_router", 
    "ticket_router", 
    "diagnostico_router",
    "rce_comprobantes_router",
    "rce_propuestas_router", 
    "rce_procesos_router",
    "rce_consultas_router"
]
