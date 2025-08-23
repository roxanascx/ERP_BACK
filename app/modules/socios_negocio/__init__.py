"""
Módulo Socios de Negocio - Gestión unificada de proveedores y clientes
Incluye consulta RUC integrada con SUNAT
"""

from .models import SocioNegocioModel
from .schemas import (
    SocioNegocioCreate,
    SocioNegocioUpdate, 
    SocioNegocioResponse,
    SocioListResponse,
    ConsultaRucRequest,
    ConsultaRucResponse
)
from .services import SocioNegocioService
from .repositories import SocioNegocioRepository
from .routes import router

__all__ = [
    "SocioNegocioModel",
    "SocioNegocioCreate",
    "SocioNegocioUpdate",
    "SocioNegocioResponse",
    "SocioListResponse", 
    "ConsultaRucRequest",
    "ConsultaRucResponse",
    "SocioNegocioService",
    "SocioNegocioRepository",
    "router"
]
