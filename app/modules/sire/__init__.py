"""
Módulo SIRE - Sistema Integrado de Registros Electrónicos
Integración con API SUNAT para RVIE y RCE
"""

__version__ = "1.0.0"
__author__ = "ERP Team"

# Importaciones principales del módulo (solo los implementados)
from .services.auth_service import SireAuthService
from .services.api_client import SunatApiClient
from .services.token_manager import SireTokenManager

__all__ = [
    "SireAuthService",
    "SunatApiClient",
    "SireTokenManager"
]
