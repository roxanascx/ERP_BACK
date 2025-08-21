"""
Módulo SIRE - Sistema Integrado de Registros Electrónicos
Integración con API SUNAT para RVIE y RCE - Solo servicios oficiales
"""

__version__ = "2.0.0"
__author__ = "ERP Team"

# Importaciones principales del módulo - Solo servicios oficiales del manual SUNAT
from .services.auth_service import SireAuthService
from .services.rvie_ventas_service import RvieVentasService
from .services.token_manager import SireTokenManager
from .services.api_client import SunatApiClient

# Importar las rutas oficiales
from .routes.rvie_ventas_routes import router as rvie_ventas_router
from .routes.rce_comprobante_bd import router as rce_bd_router

__all__ = [
    "SireAuthService",
    "RvieVentasService", 
    "SireTokenManager",
    "SunatApiClient",
    "rvie_ventas_router",
    "rce_bd_router"
]
