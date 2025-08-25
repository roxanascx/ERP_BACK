"""
Módulo de Consultas API
======================
Servicios para consultas de documentos peruanos y tipos de cambio:
- RUC (SUNAT)
- DNI (RENIEC)
- CE (Carnet de Extranjería)
- Tipos de cambio diarios (eApiPeru)
"""

__version__ = "1.1.0"
__author__ = "ERP Backend Team"

from .services import SunatService, ReniecService, ExchangeRateService
from .repositories import ExchangeRateRepository

__all__ = [
    "SunatService", 
    "ReniecService", 
    "ExchangeRateService",
    "ExchangeRateRepository"
]
